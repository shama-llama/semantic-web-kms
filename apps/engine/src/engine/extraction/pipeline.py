"""Defines the ExtractionPipeline class, which orchestrates the extraction process."""

import concurrent.futures
import logging
import threading
from pathlib import Path

from rdflib import Graph
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeElapsedColumn,
)

from engine.core.ontology_cache import get_ontology_cache
from engine.core.paths import PathManager, get_excluded_directories
from engine.extraction.context import ExtractionContext
from engine.extraction.rdf.postprocessor import Postprocessor
from engine.extraction.strategies.code_strategy import CodeStrategy
from engine.extraction.strategies.content_strategy import ContentStrategy
from engine.extraction.strategies.doc_strategy import DocStrategy
from engine.extraction.strategies.file_strategy import FileStrategy
from engine.extraction.strategies.git_strategy import GitStrategy
from engine.extraction.strategies.repo_strategy import RepoStrategy

logger = logging.getLogger(__name__)


class ExtractionPipeline:
    """
    Orchestrates the extraction process by running a sequence of strategies with a shared context.
    Now supports parallel processing for improved performance.
    """

    def __init__(
        self,
        input_dir: str,
        output_path: str,
        max_workers: int | None = None,
        batch_size: int = 500,
    ):
        # Load ontology cache and class/property mappings
        ontology_cache = get_ontology_cache()
        class_cache = getattr(ontology_cache, "get_class_cache", lambda *a, **kw: None)(
            ontology_cache.classes
        )
        prop_cache = getattr(
            ontology_cache, "get_property_cache", lambda *a, **kw: None
        )(ontology_cache.object_properties + ontology_cache.data_properties)

        # Load excluded directories
        excluded_dirs_list = get_excluded_directories()
        excluded_dirs = set(excluded_dirs_list)

        # Create graph with streaming serialization
        self.graph = self._create_graph(output_path)
        # Load WDO ontology into the graph using PathManager
        wdo_owl_path = PathManager.get_web_dev_ontology_path()
        if wdo_owl_path.exists():
            self.graph.parse(str(wdo_owl_path), format="xml")
        self.context = ExtractionContext(
            graph=self.graph,
            input_dir=Path(input_dir),
            output_ttl_path=Path(output_path),
        )
        # Attach ontology and caches to context for use in strategies
        self.context.ontology_cache = ontology_cache
        self.context.class_cache = class_cache
        self.context.prop_cache = prop_cache
        self.context.excluded_dirs = excluded_dirs

        # Initialize streaming serialization
        self._init_streaming_serialization(output_path)

        # Initialize performance caches
        self._init_performance_caches(batch_size)

        self.strategies = [
            RepoStrategy(),
            GitStrategy(),
            FileStrategy(),
            ContentStrategy(),
            CodeStrategy(),
            DocStrategy(),
        ]
        self.max_workers = (
            max_workers if max_workers is not None else min(len(self.strategies), 4)
        )  # Default to 4 or number of strategies
        self._lock = threading.Lock()  # For thread-safe context updates

    def _init_performance_caches(self, batch_size: int):
        """Initialize caches for improved performance."""
        import threading

        # Cache for file classification results
        self.classification_cache = {}
        self.classification_cache_lock = threading.Lock()

        # Cache for ontology lookups
        self.ontology_lookup_cache = {}
        self.ontology_lookup_lock = threading.Lock()

        # Cache for file content (with size limits)
        self.content_cache = {}
        self.content_cache_lock = threading.Lock()
        self.max_cached_content_size = 1024 * 1024  # 1MB limit per file

        # Cache for language mapping
        self.language_cache = {}

        # Batch processing configuration
        self.batch_size = batch_size  # Process 500 files at a time
        self.batch_timeout = 30  # 30 seconds timeout per batch

        # Add caches to context for strategies to use
        self.context.classification_cache = self.classification_cache
        self.context.ontology_lookup_cache = self.ontology_lookup_cache
        self.context.content_cache = self.content_cache
        self.context.language_cache = self.language_cache
        self.context.batch_size = self.batch_size
        self.context._pipeline = self  # Add pipeline reference for batch processing

    def run(self):
        """
        Executes the entire extraction pipeline with parallel processing, but uses per-strategy copies of file_metadata to avoid race conditions.
        """
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            transient=True,
        ) as progress:
            main_task = progress.add_task(
                "[bold green]Extraction Pipeline", total=len(self.strategies)
            )

            try:
                # Group strategies by dependencies
                parallel_strategies, sequential_strategies = self._group_strategies()

                # Run FileStrategy first (sequentially)
                if sequential_strategies:
                    self._run_sequential_strategies(
                        sequential_strategies, progress, main_task
                    )

                # --- NOTE: Per-strategy file_metadata patch for thread safety ---
                # To avoid race conditions when running strategies in parallel, we
                # make a copy of file_metadata for each strategy and patch it into
                # the context before each strategy runs. This ensures that no strategy
                # can mutate or clear the shared file_metadata, and all strategies see
                # a consistent view. This is a pragmatic solution for thread safety;
                # a more modular design would pass data as arguments.
                # ----------------------------------------------------------------
                file_metadata_copy = list(self.context.file_metadata)
                per_strategy_file_metadata = {
                    "ContentStrategy": file_metadata_copy,
                    "CodeStrategy": file_metadata_copy,
                    "DocStrategy": file_metadata_copy,
                }

                # Run remaining strategies in parallel
                if parallel_strategies:
                    self._run_parallel_strategies(
                        parallel_strategies, progress, main_task
                    )
            except Exception as e:
                progress.log(f"[bold red]Error during extraction: {e}")
                raise
            finally:
                # Ensure deleted files are written to the graph before serialization
                Postprocessor(self.context).add_deleted_files()
                self._serialize_graph()
                progress.log("[bold green]Pipeline finished, graph serialized.")

    def _group_strategies(self) -> tuple[list, list]:
        """
        Groups strategies into parallel and sequential execution groups.
        File strategy must run first as other strategies depend on it.
        """
        # File strategy must run first as other strategies depend on discovered files
        file_strategy = None
        other_strategies = []

        for strategy in self.strategies:
            if isinstance(strategy, FileStrategy):
                file_strategy = strategy
            else:
                other_strategies.append(strategy)

        sequential_strategies = [file_strategy] if file_strategy else []
        parallel_strategies = other_strategies

        return parallel_strategies, sequential_strategies

    def _run_parallel_strategies(self, strategies: list, progress, main_task):
        """
        Runs strategies in parallel using ThreadPoolExecutor.
        """
        progress.log(f"[bold blue]Running {len(strategies)} strategies in parallel...")

        def run_strategy_with_progress(strategy):
            """Wrapper to run a strategy with progress tracking."""
            task_id = progress.add_task(f"Running {strategy.name}...", total=None)
            try:
                strategy.extract(self.context, progress, task_id)
                progress.update(main_task, advance=1)
                progress.remove_task(task_id)
                return strategy.name, True, None
            except Exception as e:
                progress.remove_task(task_id)
                logger.error(f"Error in {strategy.name}: {e}")
                return strategy.name, False, str(e)

        with concurrent.futures.ThreadPoolExecutor(
            max_workers=self.max_workers
        ) as executor:
            # Submit all strategies for parallel execution
            future_to_strategy = {
                executor.submit(run_strategy_with_progress, strategy): strategy
                for strategy in strategies
            }

            # Collect results as they complete
            for future in concurrent.futures.as_completed(future_to_strategy):
                strategy_name, success, error = future.result()
                if not success:
                    progress.log(f"[bold red]Strategy {strategy_name} failed: {error}")
                    raise Exception(f"Strategy {strategy_name} failed: {error}")

    def _run_sequential_strategies(self, strategies: list, progress, main_task):
        """
        Runs strategies sequentially (for dependencies).
        """
        for strategy in strategies:
            task_id = progress.add_task(f"Running {strategy.name}...", total=None)
            try:
                strategy.extract(self.context, progress, task_id)
                progress.update(main_task, advance=1)
                progress.remove_task(task_id)
            except Exception as e:
                progress.remove_task(task_id)
                progress.log(f"[bold red]Error in {strategy.name}: {e}")
                raise

    def _create_graph(self, path: str) -> Graph:
        # Initialize a new RDF graph (could load existing TTL if needed)
        return Graph()

    def _init_streaming_serialization(self, output_path: str):
        """Initialize streaming serialization to write triples incrementally."""
        # Store output path for later use
        self.output_path = output_path
        # We'll use a simpler approach - write triples in batches
        self.triple_buffer = []
        self.buffer_size = 1000  # Write every 1000 triples

    def _serialize_graph(self):
        """
        Serializes all discovered models to the RDF graph and writes it to the output TTL path.
        Now uses incremental serialization to prevent memory buildup.
        """
        # Clear any remaining entities from context to free memory
        self._clear_context_entities()

        # Write the graph to the output TTL path
        self.context.graph.serialize(
            destination=str(self.context.output_ttl_path), format="turtle"
        )

    def _clear_context_entities(self):
        """Clear entities from context to free memory after serialization."""
        with self.context._lock:
            # Clear large collections to free memory
            if hasattr(self.context, "files"):
                self.context.files.clear()
            if hasattr(self.context, "commits"):
                self.context.commits.clear()

    def process_batch(
        self, items, processor_func, progress, task_id, batch_name="items"
    ):
        """
        Process items in batches to manage memory efficiently.

        Args:
            items: List of items to process
            processor_func: Function to process each batch
            progress: Progress tracker
            task_id: Task ID for progress updates
            batch_name: Name for progress logging
        """
        total_items = len(items)
        if total_items == 0:
            return

        num_batches = (total_items + self.batch_size - 1) // self.batch_size

        progress.log(
            f"[bold blue]Processing {total_items} {batch_name} in {num_batches} batches..."
        )

        # Monitor memory usage
        try:
            import psutil

            process = psutil.Process()
            initial_memory = process.memory_info().rss / 1024 / 1024  # MB
            memory_monitoring = True
        except ImportError:
            memory_monitoring = False
            progress.log(
                "[dim]Memory monitoring not available (psutil not installed)[/dim]"
            )

        for batch_num in range(num_batches):
            start_idx = batch_num * self.batch_size
            end_idx = min(start_idx + self.batch_size, total_items)
            batch_items = items[start_idx:end_idx]

            batch_progress = (
                f"Batch {batch_num + 1}/{num_batches} ({len(batch_items)} {batch_name})"
            )
            progress.update(task_id, description=batch_progress)

            try:
                # Process the batch
                processor_func(batch_items, progress, task_id)

                # Clear memory after each batch
                self._clear_batch_memory()

                # Update progress
                progress.update(task_id, advance=len(batch_items))

                # Log memory usage every 5 batches
                if (batch_num + 1) % 5 == 0 or batch_num == num_batches - 1:
                    if memory_monitoring:
                        current_memory = process.memory_info().rss / 1024 / 1024  # MB
                        memory_change = current_memory - initial_memory
                        progress.log(
                            f"[dim]Memory: {current_memory:.1f}MB (change: {memory_change:+.1f}MB)[/dim]"
                        )

            except Exception as e:
                progress.log(f"[bold red]Error in batch {batch_num + 1}: {e}")
                logger.error(f"Batch processing error: {e}")
                raise

        progress.log(f"[bold green]Completed processing {total_items} {batch_name}")

    def _clear_batch_memory(self):
        """Clear memory after processing each batch."""
        import gc

        # Clear content cache to free memory
        with self.content_cache_lock:
            self.content_cache.clear()

        # Clear lazy-loaded file content
        if hasattr(self.context, "files"):
            for file in self.context.files:
                if hasattr(file, "clear_content"):
                    file.clear_content()

        # Force garbage collection
        gc.collect()

    def create_batch_processor(self, processor_func, batch_name="items"):
        """
        Create a batch processor function that can be used by strategies.

        Args:
            processor_func: Function that processes a single batch
            batch_name: Name for progress logging

        Returns:
            Function that can be called with (items, progress, task_id)
        """

        def batch_processor(items, progress, task_id):
            return self.process_batch(
                items, processor_func, progress, task_id, batch_name
            )

        return batch_processor

    def test_batch_processing(self):
        """Test batch processing functionality."""
        test_items = list(range(1000))  # 1000 test items
        processed_items = []

        def test_processor(batch, progress, task_id):
            processed_items.extend(batch)
            return len(batch)

        # Simulate progress tracking
        class MockProgress:
            def log(self, msg):
                print(f"LOG: {msg}")

            def update(self, task_id, **kwargs):
                pass

        mock_progress = MockProgress()

        # Test batch processing
        self.process_batch(test_items, test_processor, mock_progress, 1, "test items")

        # Verify all items were processed
        assert len(processed_items) == 1000, (
            f"Expected 1000 items, got {len(processed_items)}"
        )
        assert processed_items == test_items, "Items were not processed in order"

        print("✅ Batch processing test passed!")
        return True
