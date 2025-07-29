"""Stub for the CodeStrategy extraction strategy."""

import logging
from pathlib import Path

import logging
from pathlib import Path

from engine.extraction.context import ExtractionContext
from engine.extraction.parsers.parser_factory import ParserFactory
from engine.extraction.strategies.base import BaseExtractorStrategy

logger = logging.getLogger(__name__)


class CodeStrategy(BaseExtractorStrategy):
    """
    Extraction strategy for discovering and modeling code entities (functions, classes, etc.).
    """

    @property
    def name(self) -> str:
        return "Code Entity Extractor"

    def extract(self, context: ExtractionContext, progress, task_id):
        """
        Parses code files using the appropriate parser and collects code entities.
        Uses incremental serialization and batch processing to prevent memory buildup.

        Args:
            context (ExtractionContext): The shared pipeline context.
            progress: The rich progress bar instance.
            task_id: The ID of the task for this strategy.
        """
        # Get file metadata instead of full file objects
        file_metadata = getattr(context, "file_metadata", [])

        # Only process files that have a corresponding parser and a non-None language
        code_files = [
            f for f in file_metadata
            if f.get("language") and ParserFactory.get_parser(f["language"])
        ]

        logger.info(f"Found {len(code_files)} code files to parse.")
        if not code_files:
            logger.warning("No code files found to parse. Check file metadata and language mappings.")
            return

        progress.update(task_id, total=len(code_files))

        # Process code files in batches
        batch_size = getattr(context, "batch_size", 500)

        def process_code_batch(batch_files, progress, task_id):
            """Process a batch of code files."""
            from engine.extraction.rdf.serializer import RdfSerializer

            serializer = RdfSerializer(context)
            parser_cache = {}

            for file_meta in batch_files:
                file_path = Path(file_meta["path"])
                language = file_meta.get("language")

                if not language:
                    logger.warning(f"Skipping file {file_path} due to missing language mapping.")
                    progress.update(task_id, advance=1)
                    continue

                # Get parser from cache or factory
                if language not in parser_cache:
                    ParserClass = ParserFactory.get_parser(language)
                    if ParserClass:
                        parser_cache[language] = ParserClass()
                    else:
                        parser_cache[language] = None
                parser = parser_cache[language]
                if not parser:
                    logger.warning(f"No parser for language {language} ({file_path})")
                    progress.update(task_id, advance=1)
                    continue
                try:
                    logger.info(f"Parsing file: {file_path} with parser: {parser.__class__.__name__}")
                    content_bytes = file_path.read_bytes()
                    content = content_bytes.decode("utf-8", errors="ignore")
                    constructs = parser.parse(content, str(file_path))
                    if constructs:
                        logger.info(f"  - Found {len(constructs)} constructs in {file_path}")
                        # Add metadata needed for serialization
                        for construct in constructs:
                            construct.organization_name = file_meta["organization_name"]
                            construct.repository_name = file_meta["repository_name"]
                            construct.relative_path = file_meta["relative_path"]
                        serializer.serialize(constructs)
                    else:
                        logger.warning(f"  - No constructs found in {file_path}")
                except Exception as e:
                    logger.error(f"Error parsing {file_path}: {e}", exc_info=True)
                finally:
                    progress.update(task_id, advance=1)

        # Use batch processing from pipeline
        pipeline = getattr(context, "_pipeline", None)

        if pipeline and hasattr(pipeline, "process_batch"):
            pipeline.process_batch(
                code_files, process_code_batch, progress, task_id, "code files"
            )
        else:
            # Fallback to processing all files at once
            process_code_batch(code_files, progress, task_id)
