"""Pipeline script to run extraction, annotation, and upload ontology TTL to AllegroGraph triplestore."""

import argparse
import os
import subprocess  # nosec: B404 - usage is safe, see run_cmd below
import sys

# Parse --input-dir and set input dir before any other imports
from app.core.paths import set_input_dir

parser = argparse.ArgumentParser(description="Run the full pipeline.")
parser.add_argument(
    "--input-dir",
    type=str,
    default=None,
    help="Root directory to analyze (overrides default in config)",
)
args, unknown = parser.parse_known_args()
if args.input_dir:
    set_input_dir(args.input_dir)

# Now import the rest
from typing import List

from app.triplestore.agraph_connection import AllegroGraphRESTClient

# Paths
EXTRACTION_CMD = [sys.executable, "-m", "app.extraction.pipeline.main_extractor"]
ANNOTATION_CMD = [sys.executable, "-m", "app.annotation.semantic_annotator"]
TTL_PATH = os.path.join("output", "web_development_ontology.ttl")

# If input_dir is set, add it to the subprocess commands
if args.input_dir:
    EXTRACTION_CMD += ["--input-dir", args.input_dir]
    ANNOTATION_CMD += ["--input-dir", args.input_dir]


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
    print(f"\n[STEP] {desc}...")
    result = subprocess.run(
        cmd, check=False, capture_output=True, text=True
    )  # nosec: B603 - cmd is trusted, shell=False
    if result.returncode != 0:
        print(f"[ERROR] {desc} failed.")
        if result.stderr:
            print(f"Error output: {result.stderr}")
        sys.exit(1)
    print(f"[OK] {desc} complete.")


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
    print("\n[STEP] Uploading TTL to AllegroGraph...")
    with AllegroGraphRESTClient() as client:
        success = client.upload_ttl_file(ttl_path)
    if not success:
        print("[ERROR] Upload to AllegroGraph failed.")
        sys.exit(1)
    print("[OK] TTL uploaded to AllegroGraph.")


def main() -> None:
    """
    Run the full extraction, annotation, and upload pipeline.

    This function sequentially runs the extraction pipeline, semantic annotation, and uploads the resulting TTL file to AllegroGraph. Exits the program if any step fails.

    Returns:
        None

    Raises:
        SystemExit: If any step in the pipeline fails.
    """
    # The --input-dir argument parsing and set_input_dir() call is now at the top of the file.
    # args = parser.parse_args() if __name__ == "__main__" else argparse.Namespace(input_dir=None)
    # input_dir = args.input_dir

    # if input_dir:
    #     set_input_dir(input_dir)

    run_cmd(EXTRACTION_CMD, "Run Extraction Pipeline")
    run_cmd(ANNOTATION_CMD, "Run Semantic Annotation")
    upload_ttl_to_allegrograph(TTL_PATH)
    print("\n[ALL DONE] Full pipeline complete.")


if __name__ == "__main__":
    main()
