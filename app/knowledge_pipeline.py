"""Pipeline script to run extraction, annotation, and upload ontology TTL to AllegroGraph triplestore."""

import os
import subprocess
import sys
from typing import List

from app.triplestore.agraph_connection import AllegroGraphRESTClient

# Paths
EXTRACTION_CMD = [sys.executable, "-m", "app.extraction.main_extractor"]
ANNOTATION_CMD = [sys.executable, "-m", "app.annotation.semantic_annotator"]
TTL_PATH = os.path.join("output", "web_development_ontology.ttl")


def run_cmd(cmd: List[str], desc: str) -> None:
    """Run a subprocess command and exit on failure."""
    print(f"\n[STEP] {desc}...")
    result = subprocess.run(cmd)
    if result.returncode != 0:
        print(f"[ERROR] {desc} failed.")
        sys.exit(1)
    print(f"[OK] {desc} complete.")


def upload_ttl_to_allegrograph(ttl_path: str) -> None:
    """Upload the TTL file to the configured AllegroGraph triplestore."""
    print("\n[STEP] Uploading TTL to AllegroGraph...")
    with AllegroGraphRESTClient() as client:
        success = client.upload_ttl_file(ttl_path)
    if not success:
        print("[ERROR] Upload to AllegroGraph failed.")
        sys.exit(1)
    print("[OK] TTL uploaded to AllegroGraph.")


def main():
    """Run the full extraction, annotation, and upload pipeline."""
    run_cmd(EXTRACTION_CMD, "Run Extraction Pipeline")
    run_cmd(ANNOTATION_CMD, "Run Semantic Annotation")
    upload_ttl_to_allegrograph(TTL_PATH)
    print("\n[ALL DONE] Full pipeline complete.")


if __name__ == "__main__":
    main()
