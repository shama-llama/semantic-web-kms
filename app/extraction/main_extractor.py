"""
Main orchestrator for the extraction pipeline in the Semantic Web Knowledge Management System.

Runs all extractors in sequence, logs results, and provides a summary for diagnostics and user feedback.
"""

import logging
import os
import sys
from dataclasses import dataclass
from typing import Any, List, Optional

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from app.core.paths import get_log_path, get_output_path
from app.extraction import (
    code_extractor,
    content_extractor,
    doc_extractor,
    file_extractor,
    git_extractor,
)

# Set up logging to file for pipeline diagnostics and debugging
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

# Output file path for the generated ontology
TTL_PATH = get_output_path("web_development_ontology.ttl")


@dataclass
class ExtractionResult:
    """Represents the result of an extraction step for summary and error reporting."""

    name: str
    success: bool
    error: Optional[str] = None

    def __repr__(self) -> str:
        """Return a developer-friendly string representation of the ExtractionResult."""
        return f"ExtractionResult(name={self.name!r}, success={self.success!r}, error={self.error!r})"

    def __str__(self) -> str:
        """Return a user-friendly string representation of the ExtractionResult."""
        status = "PASSED" if self.success else "FAILED"
        details = self.error if self.error else "Completed successfully"
        return f"{self.name}: {status} ({details})"


def run_extractor(
    extractor_name: str, extractor_module: Any, console: Console
) -> ExtractionResult:
    """
    Run a single extractor and return the result.

    Why: Centralizes error handling and logging for each extractor, so the pipeline can continue and report all failures.
    """
    try:
        logger.info(f"Starting {extractor_name}...")
        console.print(f"[bold blue]Running {extractor_name}...[/bold blue]")

        if not hasattr(extractor_module, "main"):
            raise AttributeError(
                f"Extractor module '{extractor_name}' does not have a main() method."
            )
        extractor_module.main()

        logger.info(f"{extractor_name} completed successfully")
        console.print(f"[bold green]✓ {extractor_name} completed[/bold green]")
        return ExtractionResult(extractor_name, True)

    except AttributeError as e:
        error_msg = f"Error in {extractor_name}: {e}"
        logger.error(error_msg, exc_info=True)
        console.print(f"[bold red]✗ {extractor_name} failed: {e}[/bold red]")
        return ExtractionResult(extractor_name, False, str(e))
    except Exception as e:
        # Catch all other exceptions to allow pipeline to continue
        error_msg = f"Error in {extractor_name}: {e}"
        logger.error(error_msg, exc_info=True)
        console.print(f"[bold red]✗ {extractor_name} failed: {e}[/bold red]")
        return ExtractionResult(extractor_name, False, str(e))


def display_summary(results: List[ExtractionResult], console: Console) -> None:
    """
    Display a summary of all extraction results in a table and a final status panel.

    Why: Provides a clear, user-friendly summary of pipeline status and next steps.
    """
    table = Table(title="Extraction Pipeline Summary")
    table.add_column("Extractor", style="cyan", no_wrap=True)
    table.add_column("Status", style="bold")
    table.add_column("Details", style="dim")

    for result in results:
        status = "[green]✓ PASSED[/green]" if result.success else "[red]✗ FAILED[/red]"
        details = result.error if result.error else "Completed successfully"
        table.add_row(result.name, status, details)

    console.print(table)

    passed = sum(result.success for result in results)
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
    """
    Orchestrate the extraction pipeline: run all extractors, summarize results, and exit with appropriate code.

    Why: Keeps orchestration logic in one place for clarity and maintainability.
    """
    console = Console()

    console.print(
        Panel(
            "[bold blue]Semantic Web Knowledge Management System[/bold blue]\n"
            "Extraction Pipeline Orchestrator",
            title="🚀 Starting Extraction Pipeline",
            border_style="blue",
        )
    )

    logger.info("Starting extraction pipeline orchestration")

    extractors = [
        ("File Extractor", file_extractor),
        ("Content Extractor", content_extractor),
        ("Code Extractor", code_extractor),
        ("Documentation Extractor", doc_extractor),
        ("Git Extractor", git_extractor),
    ]

    results: List[ExtractionResult] = [
        run_extractor(name, module, console) for name, module in extractors
    ]

    console.print("\n" + "=" * 60)
    display_summary(results, console)

    all_success = all(result.success for result in results)
    sys.exit(0 if all_success else 1)


if __name__ == "__main__":
    main()
