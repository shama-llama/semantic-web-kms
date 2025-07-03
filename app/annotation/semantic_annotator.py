import logging
import os

from rdflib import Graph, Literal
from rdflib.namespace import RDF, RDFS
from rich.console import Console
from rich.panel import Panel
from rich.progress import BarColumn, Progress, TextColumn, TimeElapsedColumn
from rich.table import Table

from app.core.paths import get_log_path, get_output_path

# Setup logging to file only
log_path = get_log_path("annotation_extractor.log")
os.makedirs(os.path.dirname(log_path), exist_ok=True)
LOGFORMAT_FILE = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
logging.basicConfig(
    level=logging.INFO,
    format=LOGFORMAT_FILE,
    datefmt="[%Y-%m-%d %H:%M:%S]",
    handlers=[logging.FileHandler(log_path)],
)
logger = logging.getLogger("annotation_extractor")

# --- Ontology and File Paths ---
TTL_PATH = get_output_path("web_development_ontology.ttl")


def main() -> None:
    """Main function for annotation and enrichment."""
    console = Console()
    console.print(
        Panel(
            "[bold blue]Semantic Web Knowledge Management System[/bold blue]\nSemantic Annotation Pipeline",
            title="🧩 Starting Annotation",
            border_style="blue",
        )
    )
    logger.info("Starting annotation/enrichment process...")

    # Load the existing TTL graph
    g = Graph()
    if os.path.exists(TTL_PATH):
        g.parse(TTL_PATH, format="turtle")
        logger.info(f"Loaded existing TTL graph from {TTL_PATH}")
    else:
        logger.warning(f"TTL file not found at {TTL_PATH}, starting with empty graph.")

    # --- Annotating Progress Bar ---
    entities = list(g.triples((None, RDF.type, None)))
    num_entities = len(entities)
    num_annotated = 0

    with Progress(
        TextColumn("[bold blue]{task.description}"),
        BarColumn(),
        "[progress.percentage]{task.percentage:>3.0f}%",
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        annotate_task = progress.add_task("Annotating entities...", total=num_entities)
        for s, _, _ in entities:
            g.add((s, RDFS.comment, Literal("Annotated by annotation_extractor")))
            num_annotated += 1
            progress.advance(annotate_task)

        # --- Writing Progress Bar ---
        write_task = progress.add_task("Writing TTL...", total=1)
        g.serialize(destination=TTL_PATH, format="turtle")
        progress.advance(write_task)

    logger.info(
        f"Annotation complete. Annotated {num_annotated} entities. Saved to {TTL_PATH}"
    )

    # Print annotation summary line (like git_extractor) BEFORE the summary table and panel
    console.print(
        f"[bold green]Annotation complete:[/bold green] {num_annotated} entities annotated"
    )
    console.print(
        f"[bold green]Ontology updated and saved to:[/bold green] [cyan]{TTL_PATH}[/cyan]"
    )
    console.print("[bold green]\u2713 Annotation Extractor completed[/bold green]")

    # Pretty summary output (matching main_extractor.py style exactly)
    table = Table(title="Annotation Pipeline Summary")
    table.add_column("Extractor", style="cyan", no_wrap=True)
    table.add_column("Status", style="bold")
    table.add_column("Details", style="dim")

    # Always assume success unless an exception is raised
    status = "[green]✓ PASSED[/green]"
    details = "Completed successfully"
    table.add_row("Annotation Extractor", status, details)
    console.print("\n" + "=" * 60)
    console.print(table)

    console.print(
        Panel(
            f"[bold green]Annotation complete![/bold green]\nOntology updated and saved to: [cyan]{TTL_PATH}[/cyan]",
            title="🎉 Annotation Complete",
            border_style="green",
        )
    )


if __name__ == "__main__":
    main()
