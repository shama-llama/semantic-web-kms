"""File extraction module for Semantic Web KMS."""

import datetime
import json
import logging
import os
import re
from typing import Any, Dict, List, Optional, Set, Tuple

from rdflib import Graph
from rdflib.namespace import RDF, RDFS, XSD
from rdflib.term import Literal
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
from app.core.progress_tracker import get_current_tracker
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
    Extract file records from all repositories, including timestamps.

    Classifies each file according to the provided classifiers and ontology.
    Extracts creation and modification timestamps for each file.

    Args:
        excluded_dirs (Set[str]): Directories to exclude from extraction.
        file_classifiers (List[Tuple[str, re.Pattern]]): List of (class_name, regex) pairs for classification.
        file_ignore_patterns (List[re.Pattern]): List of regex patterns for files to ignore.
        ontology (WDOOntology): Ontology object for class URI lookup.
        ontology_class_cache (Set[str]): Set of valid ontology class names.
        progress (Optional[Progress]): Rich Progress object for tracking extraction progress.
        extract_task (Optional[TaskID]): Task ID for progress tracking.

    Returns:
        List[Dict[str, Any]]: List of file record dictionaries, each including classification info and timestamps.

    Raises:
        OSError: If a file's size cannot be determined.
        Exception: Propagates exceptions from classifier or ontology lookup.
    """
    repo_file_map = get_repo_file_map(excluded_dirs)
    file_records = []
    file_id = 1
    total_files = sum(len(files) for files in repo_file_map.values())
    processed_files = 0

    # Get progress tracker for frontend reporting
    tracker = get_current_tracker()

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
            # Extract timestamps (platform-dependent)
            try:
                stat = os.stat(abs_path)
                modification_timestamp = datetime.datetime.fromtimestamp(
                    stat.st_mtime
                ).isoformat()
                try:
                    creation_timestamp = datetime.datetime.fromtimestamp(
                        getattr(stat, "st_birthtime", stat.st_ctime)
                    ).isoformat()
                except AttributeError:
                    creation_timestamp = datetime.datetime.fromtimestamp(
                        stat.st_ctime
                    ).isoformat()
            except Exception:
                creation_timestamp = ""
                modification_timestamp = ""
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
                    creation_timestamp,
                    modification_timestamp,
                )
            )
            file_id += 1
            processed_files += 1

            # Update progress for both Rich Progress and frontend tracker
            if progress and extract_task is not None:
                progress.advance(extract_task)

            # Update frontend progress tracker periodically (every 10 files or at 100%)
            if tracker and (
                processed_files % 10 == 0 or processed_files == total_files
            ):
                progress_percentage = int(
                    (processed_files / total_files) * 40
                )  # Use 40% of total stage progress
                tracker.update_stage(
                    "fileExtraction",
                    "processing",
                    progress_percentage,
                    f"Processing files: {processed_files}/{total_files}",
                )

    return file_records


def _truncate_label(text: str, max_length: int = 60) -> str:
    """Truncate a string to a maximum length, cutting at the last space before the limit if possible.

    Args:
        text: The string to truncate.
        max_length: The maximum allowed length.

    Returns:
        Truncated string, not cutting words in half.
    """
    if len(text) <= max_length:
        return text
    cutoff = text.rfind(" ", 0, max_length)
    if cutoff == -1:
        return text[:max_length].rstrip() + "..."
    return text[:cutoff].rstrip() + "..."


def write_file_entity(g, file_uri, file_name, class_cache, prop_cache):
    """
    Add a file entity to the ontology graph, including an rdfs:label with 'file: <name>' (truncated).

    Args:
        g: RDFLib Graph to add triples to.
        file_uri: URIRef for the file entity.
        file_name: Name or path of the file.
        class_cache: Dict of ontology class URIs.
        prop_cache: Dict of ontology property URIs.
    Returns:
        None
    """
    g.add((file_uri, RDF.type, class_cache["DigitalInformationCarrier"]))
    label = f"file: {_truncate_label(file_name)}"
    g.add((file_uri, RDFS.label, Literal(label, datatype=XSD.string)))
    # ... existing code for other properties ...


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

    # Get progress tracker for frontend reporting
    tracker = get_current_tracker()

    # Define custom progress bar with green completion styling
    bar_column = BarColumn(
        bar_width=30,  # Thinner bar width
        style="blue",  # Style for the incomplete part of the bar
        complete_style="bold blue",  # Style for the completed part
        finished_style="bold green",  # Style when task is 100% complete
    )

    with Progress(
        TextColumn("[bold blue]{task.description}"),
        bar_column,  # Use custom bar column
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

        # Update progress tracker if available
        if tracker:
            tracker.update_stage(
                "fileExtraction", "processing", 0, "Starting file extraction..."
            )

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

        # Update progress tracker with extraction completion
        if tracker:
            tracker.update_stage(
                "fileExtraction",
                "processing",
                50,
                f"Extracted {len(file_records)} files. Writing to ontology...",
            )

        logger.info(
            f"File extraction complete. {len(file_records)} files processed. Populating ontology..."
        )
        ttl_path = get_output_path("wdkb.ttl")
        ttl_task = progress.add_task("[blue]Writing TTL...", total=len(file_records))
        extractor = type("Extractor", (), {"ontology": ontology})
        g = Graph()
        if os.path.exists(ontology_path):
            g.parse(ontology_path, format="xml")
        if os.path.exists(ttl_path):
            try:
                g.parse(ttl_path, format="turtle")
            except Exception as e:
                logger.warning(
                    f"Could not parse existing TTL file {ttl_path}: {e}. Starting with empty graph."
                )
                # Remove the corrupted file so it doesn't cause issues in future runs
                try:
                    os.remove(ttl_path)
                except Exception as cleanup_error:
                    logger.warning(
                        f"Failed to remove corrupted TTL file {ttl_path}: {cleanup_error}"
                    )
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

        # Create a custom progress wrapper that updates both Rich Progress and the tracker
        class ProgressWrapper:
            def __init__(self, rich_progress, rich_task, tracker):
                self.rich_progress = rich_progress
                self.rich_task = rich_task
                self.tracker = tracker
                self.processed = 0
                self.total = len(file_record_objs)
                # Use the actual task object from Rich Progress instead of creating a mock one
                self.tasks = {rich_task: rich_progress._tasks[rich_task]}

            def advance(self, task):
                self.rich_progress.advance(self.rich_task)
                self.processed += 1

                # Update tracker every 10 records or at completion
                if self.tracker and (
                    self.processed % 10 == 0 or self.processed == self.total
                ):
                    # TTL writing is the second half of the stage (50-100%)
                    progress_percentage = 50 + int((self.processed / self.total) * 50)
                    self.tracker.update_stage(
                        "fileExtraction",
                        "processing",
                        progress_percentage,
                        f"Writing ontology: {self.processed}/{self.total} files",
                    )

            def update(self, task, **kwargs):
                # Forward all parameters to the underlying Rich Progress object
                self.rich_progress.update(self.rich_task, **kwargs)

        # Use the progress wrapper for TTL writing
        progress_wrapper = ProgressWrapper(progress, ttl_task, tracker)

        write_ttl_with_progress(
            file_record_objs,
            add_file_triples,
            g,
            ttl_path,
            progress_wrapper,
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
