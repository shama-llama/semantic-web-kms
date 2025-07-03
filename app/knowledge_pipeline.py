"""Pipeline script to run extraction, annotation, and upload ontology TTL to Fuseki triplestore."""

import os
import subprocess
import sys
from typing import List

from app.triplestore.triple_manager import RDFTripleManager

# Paths
EXTRACTION_CMD = [sys.executable, "-m", "app.extraction.main_extractor"]
ANNOTATION_CMD = [sys.executable, "-m", "app.annotation.semantic_annotator"]
TTL_PATH = os.path.join("output", "web_development_ontology.ttl")

# Triplestore config
TRIPLESTORE_URL = "http://localhost:3030"
DATASET_NAME = "semantic-web-kms"
TRIPLESTORE_TYPE = "fuseki"


def run_cmd(cmd: List[str], desc: str) -> None:
    """Run a subprocess command and exit on failure."""
    print(f"\n[STEP] {desc}...")
    result = subprocess.run(cmd)
    if result.returncode != 0:
        print(f"[ERROR] {desc} failed.")
        sys.exit(1)
    print(f"[OK] {desc} complete.")


def upload_ttl_to_fuseki(ttl_path: str) -> None:
    """Upload the TTL file to the configured Fuseki triplestore."""
    print("\n[STEP] Uploading TTL to Fuseki...")
    manager = RDFTripleManager(
        triplestore_url=TRIPLESTORE_URL, dataset_name=DATASET_NAME
    )
    success = manager.upload_ttl_to_fuseki(ttl_path)
    if not success:
        print("[ERROR] Upload to Fuseki failed.")
        sys.exit(1)
    print("[OK] TTL uploaded to Fuseki.")


def main():
    """Run the full extraction, annotation, and upload pipeline."""
    run_cmd(EXTRACTION_CMD, "Run Extraction Pipeline")
    run_cmd(ANNOTATION_CMD, "Run Semantic Annotation")
    upload_ttl_to_fuseki(TTL_PATH)
    print("\n[ALL DONE] Full pipeline complete.")


if __name__ == "__main__":
    main()
