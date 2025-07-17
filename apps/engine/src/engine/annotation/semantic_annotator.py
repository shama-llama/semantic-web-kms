"""Orchestrator for the semantic annotation pipeline."""

import logging
from pathlib import Path

from rdflib import Graph
from rich.console import Console
from rich.panel import Panel

from engine.annotation.analysis import analyze_class_structure
from engine.annotation.data_processing import (
    get_all_instances,
    process_single_instance_optimized,
)
from engine.annotation.generate_class_templates import (
    generate_templates_from_class_stats,
)
from engine.annotation.similarity_calculator import add_similarity_links
from engine.annotation.utils import build_label_to_uri_map, get_spacy_nlp
from engine.core.config import settings
from engine.core.namespaces import WDO
from engine.core.paths import PathManager
from engine.core.progress_tracker import get_current_tracker

logger = logging.getLogger(__name__)

ttl_path = Path(PathManager.get_output_path("wdkb.ttl"))


class SemanticAnnotationPipeline:
    """Orchestrates the entire semantic annotation and enrichment process."""

    def __init__(self, use_tracker: bool = True):
        self.graph: Graph | None = None
        self.templates: dict[str, str] = {}
        self.num_annotated: int = 0
        self.tracker = get_current_tracker() if use_tracker else None
        self.console = Console()

    def _update_tracker(self, progress: int, message: str):
        if self.tracker:
            self.tracker.update_stage(
                "semanticAnnotation", "processing", progress, message
            )

    def _load_graph(self):
        self._update_tracker(10, "Loading knowledge graph...")
        g = Graph()
        if ttl_path.exists():
            g.parse(str(ttl_path), format="turtle")
            logger.info(f"Loaded existing TTL graph from {ttl_path}")
            logger.info(f"Graph contains {len(g)} triples")
        else:
            logger.warning(
                f"TTL file not found at {ttl_path}, starting with empty graph."
            )
        self.graph = g

    def _generate_templates(self):
        self._update_tracker(20, "Analyzing ontology structure...")
        if self.graph is None:
            raise RuntimeError("Graph is not loaded.")
        class_analysis = analyze_class_structure(self.graph)  # type: ignore
        wdo_classes = [
            (class_uri, props)
            for class_uri, props in class_analysis.items()
            if class_uri.startswith(str(WDO))
        ]
        self._update_tracker(30, "Generating annotation templates...")
        gemini_api_key = settings.GEMINI_API_KEY
        if not gemini_api_key:
            raise ValueError("GEMINI_API_KEY is not set.")
        self.templates = generate_templates_from_class_stats(
            wdo_classes, gemini_api_key
        )

    def _annotate_instances(self):
        self._update_tracker(40, "Preparing label lookup map...")
        if self.graph is None:
            raise RuntimeError("Graph is not loaded.")
        label_map = build_label_to_uri_map(self.graph)  # type: ignore
        self._update_tracker(50, "Annotating instances...")
        all_instances = get_all_instances(self.graph, self.templates)  # type: ignore
        total_instances = len(all_instances)
        if total_instances == 0:
            logger.info("No instances found to annotate.")
            return
        nlp = get_spacy_nlp()
        successful_annotations = 0
        for idx, (instance, template, class_name) in enumerate(all_instances):
            if process_single_instance_optimized(
                self.graph,
                instance,
                template,
                label_map,
                class_name,
                nlp,  # type: ignore
            ):
                successful_annotations += 1
            if self.tracker and (idx % 50 == 0 or idx == total_instances - 1):
                progress_percentage = 50 + int(((idx + 1) / total_instances) * 30)
                self.tracker.update_stage(
                    "semanticAnnotation",
                    "processing",
                    progress_percentage,
                    f"Annotating: {idx + 1}/{total_instances}",
                )
        self.num_annotated = successful_annotations

    def _add_similarity(self):
        self._update_tracker(80, "Calculating instance similarities...")
        if self.graph is None:
            raise RuntimeError("Graph is not loaded.")
        relationships_added = add_similarity_links(self.graph, use_centrality=True)  # type: ignore
        logger.info(f"Added {relationships_added} similarity relationships.")

    def _save_and_summarize(self):
        self._update_tracker(90, "Saving enriched knowledge graph...")
        if self.graph is None:
            raise RuntimeError("Graph is not loaded.")
        self.graph.serialize(destination=str(ttl_path), format="turtle")
        self._update_tracker(100, "Semantic annotation completed successfully.")
        summary_text = (
            f"[bold green]✅ Annotation Pipeline Completed Successfully![/bold green]\n\n"
            f"  - Annotated Instances: [bold]{self.num_annotated}[/bold]\n"
            f"  - Enriched Graph saved to: [cyan]{ttl_path}[/cyan]"
        )
        self.console.print(Panel(summary_text, title="Summary", border_style="green"))

    def run(self):
        """Executes the full annotation pipeline in sequence."""
        self.console.print(
            Panel("🚀 Starting Annotation Pipeline", border_style="blue")
        )
        try:
            self._load_graph()
            self._generate_templates()
            self._annotate_instances()
            self._add_similarity()
            self._save_and_summarize()
        except Exception as e:
            logger.critical(f"Pipeline failed: {e}", exc_info=True)
            if self.tracker:
                self.tracker.update_stage("semanticAnnotation", "failed", 100, str(e))
            self.console.print(
                Panel(
                    f"[bold red]❌ Pipeline Failed:[/bold red]\n{e}",
                    title="Error",
                    border_style="red",
                )
            )


def main():
    """Main entry point to run the annotation pipeline."""
    pipeline = SemanticAnnotationPipeline()
    pipeline.run()


if __name__ == "__main__":
    main()
