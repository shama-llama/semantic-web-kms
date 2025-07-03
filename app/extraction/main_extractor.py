import logging
import os
import sys
from typing import Any, List, Optional

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from app.core.paths import get_log_path, get_output_path
from app.extraction import (
    code_extractor,
    doc_extractor,
    file_extractor,
    git_extractor,
)

# Setup logging
log_path = get_log_path("main_extractor.log")
os.makedirs(os.path.dirname(log_path), exist_ok=True)
LOGFORMAT_FILE = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
logging.basicConfig(
    level=logging.INFO,
    format=LOGFORMAT_FILE,
    datefmt="[%Y-%m-%d %H:%M:%S]",
    handlers=[logging.FileHandler(log_path)],
)
logger = logging.getLogger("main_extractor")

# Output file path
TTL_PATH = get_output_path("web_development_ontology.ttl")


class ExtractionResult:
    """Represent the result of an extraction step."""

    def __init__(self, name: str, success: bool, error: Optional[str] = None):
        """Initialize ExtractionResult with name, success, and optional error message."""
        self.name = name
        self.success = success
        self.error = error


def run_extractor(
    extractor_name: str, extractor_module: Any, console: Console
) -> ExtractionResult:
    """Run a single extractor and return the result."""
    try:
        logger.info(f"Starting {extractor_name}...")
        console.print(f"[bold blue]Running {extractor_name}...[/bold blue]")

        # Ensure the extractor module has a main() method
        if not hasattr(extractor_module, "main"):
            raise AttributeError(
                f"Extractor module '{extractor_name}' does not have a main() method."
            )
        extractor_module.main()

        logger.info(f"{extractor_name} completed successfully")
        console.print(f"[bold green]✓ {extractor_name} completed[/bold green]")
        return ExtractionResult(extractor_name, True)

    except Exception as e:
        error_msg = f"Error in {extractor_name}: {str(e)}"
        logger.error(error_msg, exc_info=True)
        console.print(f"[bold red]✗ {extractor_name} failed: {str(e)}[/bold red]")
        return ExtractionResult(extractor_name, False, str(e))


def display_summary(results: List[ExtractionResult], console: Console) -> None:
    """Display a summary of all extraction results."""
    table = Table(title="Extraction Pipeline Summary")
    table.add_column("Extractor", style="cyan", no_wrap=True)
    table.add_column("Status", style="bold")
    table.add_column("Details", style="dim")

    for result in results:
        status = "[green]✓ PASSED[/green]" if result.success else "[red]✗ FAILED[/red]"
        details = result.error if result.error else "Completed successfully"
        table.add_row(result.name, status, details)

    console.print(table)

    # Overall status
    passed = sum(1 for r in results if r.success)
    total = len(results)

    if passed == total:
        console.print(
            Panel(
                f"[bold green]All {total} extractors completed successfully![/bold green]\n"
                f"Ontology saved to: [cyan]{TTL_PATH}[/cyan]",
                title="🎉 Pipeline Complete",
                border_style="green",
            )
        )
    else:
        failed = total - passed
        console.print(
            Panel(
                f"[bold red]{failed} extractor(s) failed out of {total}[/bold red]\n"
                f"Check the logs for details: [cyan]{log_path}[/cyan]",
                title="⚠️ Pipeline Incomplete",
                border_style="red",
            )
        )


def main() -> None:
    """Run the extraction pipeline orchestrator."""
    console = Console()

    # Welcome message
    console.print(
        Panel(
            "[bold blue]Semantic Web Knowledge Management System[/bold blue]\n"
            "Extraction Pipeline Orchestrator",
            title="🚀 Starting Extraction Pipeline",
            border_style="blue",
        )
    )

    logger.info("Starting extraction pipeline orchestration")

    # Define the extraction sequence
    extractors = [
        ("File Extractor", file_extractor),
        ("Code Extractor", code_extractor),
        ("Documentation Extractor", doc_extractor),
        ("Git Extractor", git_extractor),
    ]

    results: List[ExtractionResult] = []

    # Run each extractor in sequence
    for extractor_name, extractor_module in extractors:
        result = run_extractor(extractor_name, extractor_module, console)
        results.append(result)

        # If an extractor fails, we can choose to continue or stop
        # For now, we'll continue to see all results
        if not result.success:
            console.print("[yellow]Continuing with remaining extractors...[/yellow]")

    # Display final summary
    console.print("\n" + "=" * 60)
    display_summary(results, console)

    # Exit with appropriate code
    all_success = all(r.success for r in results)
    sys.exit(0 if all_success else 1)


if __name__ == "__main__":
    main()
