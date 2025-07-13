"""Complete knowledge pipeline script to run extraction, annotation, and upload to AllegroGraph triplestore."""

import argparse
import logging
import os
import subprocess  # nosec: B404 - usage is safe, see run_cmd below
import sys
from typing import List

# Load environment variables from .env if present
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass  # python-dotenv not installed; skip loading .env

# Parse --input-dir and set input dir before any other imports
from app.core.paths import set_input_dir

parser = argparse.ArgumentParser(description="Run the complete knowledge pipeline.")
parser.add_argument(
    "--input-dir",
    type=str,
    default=None,
    help="Root directory to analyze (overrides default in config)",
)
parser.add_argument(
    "--skip-extraction",
    action="store_true",
    help="Skip the extraction phase (useful for re-annotation)",
)
parser.add_argument(
    "--skip-annotation",
    action="store_true",
    help="Skip the annotation phase",
)
parser.add_argument(
    "--skip-upload",
    action="store_true",
    help="Skip the upload to AllegroGraph",
)
parser.add_argument(
    "--generate-templates",
    action="store_true",
    help="Generate class templates for annotation",
)
parser.add_argument(
    "--log-level",
    choices=["DEBUG", "INFO", "WARNING", "ERROR"],
    default="INFO",
    help="Set logging level",
)
args, unknown = parser.parse_known_args()
if args.input_dir:
    set_input_dir(args.input_dir)

# Now import the rest
# Remove: from typing import List (duplicate)

# Import progress tracking
from app.core.progress_tracker import get_current_tracker
from app.triplestore.agraph_connection import AllegroGraphRESTClient

# Paths
EXTRACTION_CMD = [sys.executable, "-m", "app.extraction.main_extractor"]
ANNOTATION_CMD = [sys.executable, "-m", "app.annotation.semantic_annotator"]
TEMPLATE_GENERATION_CMD = [
    sys.executable,
    "-m",
    "app.annotation.generate_class_templates",
]
TTL_PATH = os.path.join("output", "wdkb.ttl")

# If input_dir is set, add it to the subprocess commands
if args.input_dir:
    EXTRACTION_CMD += ["--input-dir", args.input_dir]
    ANNOTATION_CMD += ["--input-dir", args.input_dir]

# Setup complete logging
log_path = os.path.join("logs", "knowledge_pipeline.log")
os.makedirs(os.path.dirname(log_path), exist_ok=True)
logging.basicConfig(
    level=getattr(logging, args.log_level),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(log_path),
        (
            logging.StreamHandler(sys.stdout)
            if args.log_level == "DEBUG"
            else logging.NullHandler()
        ),
    ],
)
logger = logging.getLogger("knowledge_pipeline")


def run_cmd(cmd: List[str], desc: str) -> None:
    """
    Run a subprocess command and exit on failure.

    Args:
        cmd: The command to run as a list of strings (e.g., ["python", "script.py"]).
        desc: A description of the step for logging purposes.

    Returns:
        None

    Raises:
        SystemExit: If the subprocess returns a non-zero exit code, the function prints an error and exits the program.
    """
    # Security note: cmd is a predefined list of commands, not user input
    logger.info(f"Starting {desc}...")
    print(f"\n[STEP] {desc}...")
    result = subprocess.run(
        cmd, check=False
    )  # nosec: B603 - cmd is trusted, shell=False
    if result.returncode != 0:
        error_msg = f"{desc} failed with return code {result.returncode}"
        logger.error(error_msg)
        print(f"[ERROR] {error_msg}")
        if result.stderr:
            print(f"Error output: {result.stderr.decode()}")
        sys.exit(1)
    logger.info(f"{desc} completed successfully")
    print(f"[OK] {desc} complete.")


def run_extraction_with_progress() -> None:
    """Run the extraction pipeline with progress tracking."""
    tracker = get_current_tracker()

    if tracker:
        # Update extraction stage to processing
        tracker.update_stage(
            "extraction", "processing", 0, "Starting extraction pipeline..."
        )

    try:
        # Import and run the main extractor directly
        from app.extraction.main_extractor import main as run_extraction

        # Pass input_dir if available and set exit_on_completion=False for pipeline use
        input_dir = (
            args.input_dir if hasattr(args, "input_dir") and args.input_dir else None
        )
        run_extraction(input_dir, exit_on_completion=False)

        if tracker:
            # Update extraction stage to completed
            tracker.update_stage(
                "extraction",
                "completed",
                100,
                "Extraction pipeline completed successfully",
            )

    except Exception as e:
        logger.error(f"Extraction pipeline failed: {str(e)}", exc_info=True)
        if tracker:
            tracker.update_stage(
                "extraction",
                "error",
                0,
                f"Extraction pipeline failed: {str(e)}",
            )
        raise


def run_annotation_with_progress() -> None:
    """Run the annotation pipeline with progress tracking."""
    tracker = get_current_tracker()

    if tracker:
        # Update semantic annotation stage to processing
        tracker.update_stage(
            "semanticAnnotation", "processing", 50, "Starting semantic annotation..."
        )

    try:
        # Import and run the semantic annotator directly
        from app.annotation.semantic_annotator import main as run_annotation

        # Pass input_dir if available
        input_dir = (
            args.input_dir if hasattr(args, "input_dir") and args.input_dir else None
        )
        # Run annotation with efficient postprocessing
        run_annotation(input_dir)

        if tracker:
            # Update semantic annotation stage to completed
            tracker.update_stage(
                "semanticAnnotation",
                "completed",
                100,
                "Semantic annotation completed successfully",
            )

    except Exception as e:
        logger.error(f"Annotation pipeline failed: {str(e)}", exc_info=True)
        if tracker:
            tracker.update_stage(
                "semanticAnnotation",
                "error",
                0,
                f"Annotation pipeline failed: {str(e)}",
            )
        raise


def run_template_generation() -> None:
    """Run the template generation step."""
    logger.info("Starting class template generation...")
    print("\n[STEP] Generating class templates...")

    try:
        # Run the template generation script directly
        run_cmd(TEMPLATE_GENERATION_CMD, "Class template generation")

        logger.info("Class template generation completed successfully")
        print("[OK] Class template generation complete.")

    except Exception as e:
        logger.error(f"Template generation failed: {str(e)}", exc_info=True)
        print(f"[ERROR] Template generation failed: {str(e)}")
        raise


def upload_ttl_to_allegrograph(ttl_path: str) -> None:
    """
    Upload the TTL file to the configured AllegroGraph triplestore.

    Args:
        ttl_path: The path to the Turtle (.ttl) file to upload.

    Returns:
        None

    Raises:
        SystemExit: If the upload fails, prints an error and exits the program.
        ValueError: If AllegroGraphRESTClient initialization fails due to missing environment variables.
    """
    logger.info("Starting TTL upload to AllegroGraph...")
    print("\n[STEP] Uploading TTL to AllegroGraph...")

    try:
        with AllegroGraphRESTClient() as client:
            success = client.upload_ttl_file(ttl_path)

        if not success:
            error_msg = "Upload to AllegroGraph failed"
            logger.error(error_msg)
            print(f"[ERROR] {error_msg}")
            sys.exit(1)

        logger.info("TTL uploaded to AllegroGraph successfully")
        print("[OK] TTL uploaded to AllegroGraph.")

    except Exception as e:
        logger.error(f"AllegroGraph upload failed: {str(e)}", exc_info=True)
        print(f"[ERROR] Upload to AllegroGraph failed: {str(e)}")
        sys.exit(1)


def print_pipeline_summary() -> None:
    """Print a complete summary of the pipeline execution."""
    from rich.console import Console
    from rich.rule import Rule

    console = Console()

    console.print()
    console.print(
        Rule("[bold blue]KNOWLEDGE PIPELINE SUMMARY[/bold blue]", style="bold blue")
    )
    console.print()

    # Check if TTL file exists and get its size
    if os.path.exists(TTL_PATH):
        size_mb = os.path.getsize(TTL_PATH) / (1024 * 1024)
        print(f"✓ Knowledge graph generated: {TTL_PATH}")
        print(f"  Size: {size_mb:.2f} MB")
    else:
        print("✗ Knowledge graph file not found")

    console.print()


def main() -> None:
    """
    Run the complete knowledge pipeline.

    This function sequentially runs the extraction pipeline, semantic annotation,
    and uploads the resulting TTL file to AllegroGraph. Exits the program
    if any step fails.

    Returns:
        None

    Raises:
        SystemExit: If any step in the pipeline fails.
    """
    # Print a visually centered banner at the start
    from rich.console import Console
    from rich.rule import Rule

    console = Console()

    console.print()
    console.print(
        Rule("[bold blue]KNOWLEDGE PIPELINE START[/bold blue]", style="bold blue")
    )
    console.print()

    logger.info("Starting complete knowledge pipeline")

    try:
        # Step 1: Extraction (unless skipped)
        if not args.skip_extraction:
            logger.info("Phase 1: Knowledge Extraction")
            run_extraction_with_progress()
        else:
            logger.info("Skipping extraction phase as requested")
            print("[SKIP] Extraction phase skipped")

        # Step 2: Template Generation (if requested)
        if args.generate_templates:
            logger.info("Phase 2: Class Template Generation")
            run_template_generation()

        # Step 3: Annotation (unless skipped)
        if not args.skip_annotation:
            logger.info("Phase 3: Semantic Annotation")
            run_annotation_with_progress()
        else:
            logger.info("Skipping annotation phase as requested")
            print("[SKIP] Annotation phase skipped")

        # Step 4: Upload to AllegroGraph (unless skipped)
        if not args.skip_upload:
            logger.info("Phase 4: Upload to AllegroGraph")
            upload_ttl_to_allegrograph(TTL_PATH)
        else:
            logger.info("Skipping upload phase as requested")
            print("[SKIP] Upload phase skipped")

        # Print complete summary
        print_pipeline_summary()

        # Print completion panel for the entire pipeline
        from rich.panel import Panel

        console.print(
            Panel(
                f"[bold green]Complete knowledge pipeline finished successfully![/bold green]\n"
                f"All phases completed and knowledge graph saved to: [cyan]{TTL_PATH}[/cyan]",
                title="🎉 Pipeline Complete",
                border_style="green",
            )
        )

        logger.info("Complete knowledge pipeline completed successfully")

    except Exception as e:
        logger.error(f"Pipeline failed: {str(e)}", exc_info=True)
        print(f"\n[ERROR] Pipeline failed: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
