"""File extraction module for Semantic Web KMS."""

import json
import logging
import os
import re
from typing import Any, Dict, List, Optional, Set, Tuple

from rdflib import Graph
from rich.console import Console
from rich.progress import BarColumn, Progress, TaskID, TextColumn, TimeElapsedColumn

from app.core.namespaces import INST, SKOS, WDO
from app.core.paths import (
    get_carrier_types_path,
    get_excluded_directories_path,
    get_input_path,
    get_ontology_cache_path,
    get_output_path,
    get_web_dev_ontology_path,
)
from app.extraction.utils.classification_utils import (
    classify_file,
    load_classifiers_from_json,
)
from app.extraction.utils.file_utils import (
    FileRecord,
    count_total_files,
    get_repo_file_map,
    make_file_record,
)
from app.extraction.utils.rdf_utils import (
    add_file_triples,
    write_ttl_with_progress,
)
from app.ontology.wdo import WDOOntology

logger = logging.getLogger("file_extractor")


def build_granular_carrier_type_map() -> (
    Tuple[List[Tuple[str, re.Pattern]], List[re.Pattern]]
):
    """
    Load classifier-based mappings for carrier types only.

    Returns:
        Tuple[List[Tuple[str, re.Pattern]], List[re.Pattern]]: A tuple containing a list of
        (class_name, regex pattern) pairs for carrier type classification and a list of
        regex patterns for files to ignore.

    Raises:
        FileNotFoundError: If the carrier types JSON file does not exist.
        json.JSONDecodeError: If the JSON file is malformed.
    """
    carrier_json_path = get_carrier_types_path()
    return load_classifiers_from_json(carrier_json_path)


def extract_files(
    excluded_dirs: Set[str],
    file_classifiers: List[Tuple[str, re.Pattern]],
    file_ignore_patterns: List[re.Pattern],
    ontology: WDOOntology,
    ontology_class_cache: Set[str],
    progress: Optional[Progress] = None,
    extract_task: Optional[TaskID] = None,
) -> List[Dict[str, Any]]:
    """
    Extract file records from all repositories.

    Classifies each file according to the provided classifiers and ontology.

    Args:
        excluded_dirs (Set[str]): Directories to exclude from extraction.
        file_classifiers (List[Tuple[str, re.Pattern]]): List of (class_name, regex) pairs for classification.
        file_ignore_patterns (List[re.Pattern]): List of regex patterns for files to ignore.
        ontology (WDOOntology): Ontology object for class URI lookup.
        ontology_class_cache (Set[str]): Set of valid ontology class names.
        progress (Optional[Progress]): Rich Progress object for tracking extraction progress.
        extract_task (Optional[TaskID]): Task ID for progress tracking.

    Returns:
        List[Dict[str, Any]]: List of file record dictionaries, each including classification info.

    Raises:
        OSError: If a file's size cannot be determined.
        Exception: Propagates exceptions from classifier or ontology lookup.
    """
    repo_file_map = get_repo_file_map(excluded_dirs)
    file_records = []
    file_id = 1
    for repo, files in repo_file_map.items():
        for rel_path, abs_path, fname in files:
            size_bytes = os.path.getsize(abs_path)
            extension = os.path.splitext(fname)[1]
            class_name, class_uri, _ = classify_file(
                rel_path,
                file_classifiers,
                file_ignore_patterns,
                ontology,
                ontology_class_cache,
                "DigitalInformationCarrier",
            )
            file_records.append(
                make_file_record(
                    file_id,
                    repo,
                    rel_path,
                    abs_path,
                    fname,
                    size_bytes,
                    extension,
                    class_name or "",
                    class_uri or "",
                )
            )
            file_id += 1
            if progress and extract_task is not None:
                progress.advance(extract_task)
    return file_records


def main() -> None:
    """
    Run the file extraction and ontology population pipeline.

    Returns:
        None
    Raises:
        FileNotFoundError: If required configuration or ontology files are missing.
        json.JSONDecodeError: If configuration files are malformed.
        Exception: Propagates any other exceptions encountered during extraction or serialization.
    """
    ontology_path = get_web_dev_ontology_path()
    input_dir = get_input_path("")
    console = Console()
    excluded_dirs_path = get_excluded_directories_path()
    with open(excluded_dirs_path, "r") as f:
        excluded_dirs = set(json.load(f))
    with Progress(
        TextColumn("[bold blue]{task.description}"),
        BarColumn(),
        "[progress.percentage]{task.percentage:>3.0f}%",
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        ontology = WDOOntology(ontology_path)
        carrier_classifiers, carrier_ignore_patterns = build_granular_carrier_type_map()
        cache_path = get_ontology_cache_path()
        with open(cache_path, "r") as f:
            ontology_class_cache = set(json.load(f)["classes"])
        repo_file_map = get_repo_file_map(excluded_dirs)
        repo_dirs = list(repo_file_map.keys())
        total_files = count_total_files(repo_dirs, excluded_dirs)
        extract_task: TaskID = progress.add_task(
            "[blue]Extracting files...", total=total_files
        )
        file_records = extract_files(
            excluded_dirs,
            carrier_classifiers,
            carrier_ignore_patterns,
            ontology,
            ontology_class_cache,
            progress,
            extract_task,
        )
        logger.info(
            f"File extraction complete. {len(file_records)} files processed. Populating ontology..."
        )
        ttl_path = get_output_path("web_development_ontology.ttl")
        ttl_task = progress.add_task("[blue]Writing TTL...", total=len(file_records))
        extractor = type("Extractor", (), {"ontology": ontology})
        g = Graph()
        if os.path.exists(ontology_path):
            g.parse(ontology_path, format="xml")
        if os.path.exists(ttl_path):
            g.parse(ttl_path, format="turtle")
        g.bind("wdo", WDO)
        g.bind("inst", INST)
        g.bind("skos", SKOS)
        processed_repos: Set[str] = set()
        file_record_objs = [
            FileRecord(
                **{
                    k: v
                    for k, v in rec.items()
                    if k
                    in [
                        "id",
                        "repository",
                        "path",
                        "filename",
                        "extension",
                        "size_bytes",
                        "abs_path",
                        "ontology_class",
                        "class_uri",
                        "creation_timestamp",
                        "modification_timestamp",
                    ]
                }
            )
            for rec in file_records
            if rec.get("class_uri")
        ]
        write_ttl_with_progress(
            file_record_objs,
            add_file_triples,
            g,
            ttl_path,
            progress,
            ttl_task,
            extractor,
            input_dir,
            processed_repos,
        )
    console.print(
        f"[bold green]File extraction complete:[/bold green] {len(file_records)} files processed"
    )
    console.print(
        f"[bold green]Ontology updated and saved to:[/bold green] [cyan]{ttl_path}[/cyan]"
    )


if __name__ == "__main__":
    main()
