import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import RDF, RDFS, SKOS, XSD
from rich.console import Console
from rich.progress import BarColumn, Progress, TextColumn, TimeElapsedColumn

from app.core.ontology_cache import get_file_extraction_properties, get_ontology_cache
from app.core.paths import (
    get_content_types_path,
    get_excluded_directories_path,
    get_file_extensions_path,
    get_input_path,
    get_log_path,
    get_output_path,
    get_web_dev_ontology_path,
    uri_safe_string,
)
from app.ontology.wdo import WDOOntology

# Setup logging to file only
log_path = get_log_path("file_extractor.log")
os.makedirs(os.path.dirname(log_path), exist_ok=True)
LOGFORMAT_FILE = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
logging.basicConfig(
    level=logging.INFO,
    format=LOGFORMAT_FILE,
    datefmt="[%Y-%m-%d %H:%M:%S]",
    handlers=[logging.FileHandler(log_path)],
)
logger = logging.getLogger("file_extractor")

# --- Ontology and File Paths ---
WDO = Namespace("http://semantic-web-kms.edu.et/wdo#")
INST = Namespace("http://semantic-web-kms.edu.et/wdo/instances/")


class OntologyDrivenExtractor:
    """Ontology-driven extractor for files.

    Extract file-level metadata and structure for the semantic knowledge graph.
    """

    def __init__(self, ontology_path: str):
        """Initialize the ontology-driven extractor."""
        self.ontology_path = ontology_path
        self.ontology = WDOOntology(ontology_path)
        logger.info(f"Loaded ontology from {ontology_path}")
        # Build granular extension/class mapping from ontology
        self._build_granular_filetype_map()
        # Load excluded directories
        excluded_dirs_path = get_excluded_directories_path()
        with open(excluded_dirs_path, "r") as f:
            self.excluded_dirs = set(json.load(f))
        # Property cache using ontology cache system
        ontology_cache = get_ontology_cache()
        self.prop_cache = ontology_cache.get_property_cache(
            get_file_extraction_properties()
        )

    def _build_granular_filetype_map(self):
        """Build a mapping from extension/filename to the most specific ontology class using the updated JSON."""
        # Load the updated JSON mapping using get_file_extensions_path
        ext_json_path = get_file_extensions_path()
        with open(ext_json_path, "r") as f:
            self.class_to_exts = json.load(f)
        # Build reverse mapping: ext -> class
        self.ext_to_class: Dict[str, str] = {}
        self.name_to_class: Dict[str, str] = {}
        for class_name, exts in self.class_to_exts.items():
            for ext in exts:
                ext_l = ext.lower()
                if ext_l.startswith("."):
                    self.ext_to_class[ext_l] = class_name
                else:
                    self.name_to_class[ext_l] = class_name

    def categorize_file(self, file_path: str, filename: str) -> Dict[str, Any]:
        """Categorize a file based on its extension and filename."""
        ext = Path(filename).suffix.lower()
        filename_lower = filename.lower()
        # Try exact filename match for special files (e.g., LICENSE, README)
        for key, class_name in self.name_to_class.items():
            if key in filename_lower:
                try:
                    class_uri = str(self.ontology.get_class(class_name))
                except Exception:
                    class_uri = str(
                        self.ontology.get_class("DigitalInformationCarrier")
                    )
                return {
                    "ontology_class": class_name,
                    "class_uri": class_uri,
                    "description": f"A file of type {class_name}",
                    "confidence": "high",
                }
        # Try extension match for granular class
        if ext in self.ext_to_class:
            class_name = self.ext_to_class[ext]
            try:
                class_uri = str(self.ontology.get_class(class_name))
            except Exception:
                class_uri = str(self.ontology.get_class("DigitalInformationCarrier"))
            return {
                "ontology_class": class_name,
                "class_uri": class_uri,
                "description": f"A file of type {class_name}",
                "confidence": "high",
            }
        # Fallback: try to find any subclass with a matching extension in its label
        digital_info_carrier_uri = str(
            self.ontology.get_class("DigitalInformationCarrier")
        )
        subclasses = self.ontology.get_subclasses(
            digital_info_carrier_uri, direct_only=False
        )
        for class_uri in subclasses:
            class_name = (
                class_uri.split("#")[-1]
                if "#" in class_uri
                else class_uri.split("/")[-1]
            )
            if ext in class_name.lower():
                return {
                    "ontology_class": class_name,
                    "class_uri": class_uri,
                    "description": f"A file of type {class_name}",
                    "confidence": "medium",
                }
        # Fallback to DigitalInformationCarrier
        return {
            "ontology_class": "DigitalInformationCarrier",
            "class_uri": digital_info_carrier_uri,
            "description": "A file that carries digital information",
            "confidence": "low",
        }

    def extract_files(
        self, root_dir: str, progress: Optional[Progress] = None
    ) -> List[Dict[str, Any]]:
        """Extract file information from the given root directory."""
        file_records: List[Dict[str, Any]] = []
        file_id = 1
        repo_dirs = [
            d
            for d in os.listdir(root_dir)
            if os.path.isdir(os.path.join(root_dir, d)) and d not in self.excluded_dirs
        ]
        total_files = 0
        repo_file_map: Dict[str, List[Tuple[str, str, str]]] = {}
        for repo in repo_dirs:
            repo_path = os.path.join(root_dir, repo)
            repo_file_map[repo] = []
            for dirpath, dirnames, filenames in os.walk(repo_path):
                # Exclude directories in-place at every level
                dirnames[:] = [d for d in dirnames if d not in self.excluded_dirs]
                for fname in filenames:
                    abs_path = os.path.join(dirpath, fname)
                    rel_path = os.path.relpath(abs_path, repo_path)
                    repo_file_map[repo].append((rel_path, abs_path, fname))
                    total_files += 1
        logger.info(
            f"Starting ontology-driven file extraction for {total_files} files in {len(repo_dirs)} repositories"
        )
        task = None
        if progress:
            task = progress.add_task("[blue]Processing files...", total=total_files)
        for repo, files in repo_file_map.items():
            for rel_path, abs_path, fname in files:
                categorization = self.categorize_file(abs_path, fname)
                file_record = {
                    "id": file_id,
                    "repository": repo,
                    "path": rel_path,
                    "filename": fname,
                    "ontology_class": categorization["ontology_class"],
                    "class_uri": categorization["class_uri"],
                    "description": categorization["description"],
                    "confidence": categorization["confidence"],
                    "extension": Path(fname).suffix,
                    "size_bytes": os.path.getsize(abs_path),
                    "abs_path": abs_path,  # Store absolute path for later use
                }
                file_records.append(file_record)
                file_id += 1
                if progress and task:
                    progress.advance(task)
        return file_records


def main() -> None:
    """Run the file extraction process."""
    ontology_path = get_web_dev_ontology_path()
    input_dir = get_input_path("")  # Passes the input directory root
    console = Console()

    # Load excluded directories
    excluded_dirs_path = get_excluded_directories_path()
    with open(excluded_dirs_path, "r") as f:
        excluded_dirs = set(json.load(f))

    logger.info(
        "Starting full extraction process (ontology load, mapping, file scan, and RDF output)..."
    )
    with Progress(
        TextColumn("[bold blue]{task.description}"),
        BarColumn(),
        "[progress.percentage]{task.percentage:>3.0f}%",
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        # Extraction progress bar
        extractor = OntologyDrivenExtractor(ontology_path)
        # Pre-scan to count total files for extraction
        repo_dirs = [
            d
            for d in os.listdir(input_dir)
            if os.path.isdir(os.path.join(input_dir, d)) and d not in excluded_dirs
        ]
        total_files = 0
        repo_file_map: Dict[str, List[Tuple[str, str, str]]] = {}
        for repo in repo_dirs:
            repo_path = os.path.join(input_dir, repo)
            repo_file_map[repo] = []
            for dirpath, dirnames, filenames in os.walk(repo_path):
                # Exclude directories in-place at every level
                dirnames[:] = [d for d in dirnames if d not in excluded_dirs]
                for fname in filenames:
                    abs_path = os.path.join(dirpath, fname)
                    rel_path = os.path.relpath(abs_path, repo_path)
                    repo_file_map[repo].append((rel_path, abs_path, fname))
                    total_files += 1
        extract_task = progress.add_task("[blue]Extracting files...", total=total_files)
        file_records: List[Dict[str, Any]] = []
        file_id = 1
        for repo, files in repo_file_map.items():
            for rel_path, abs_path, fname in files:
                categorization = extractor.categorize_file(abs_path, fname)
                file_record = {
                    "id": file_id,
                    "repository": repo,
                    "path": rel_path,
                    "filename": fname,
                    "ontology_class": categorization["ontology_class"],
                    "class_uri": categorization["class_uri"],
                    "description": categorization["description"],
                    "confidence": categorization["confidence"],
                    "extension": Path(fname).suffix,
                    "size_bytes": os.path.getsize(abs_path),
                    "abs_path": abs_path,  # Store absolute path for later use
                }
                file_records.append(file_record)
                file_id += 1
                progress.advance(extract_task)
        logger.info(
            f"File extraction complete. {len(file_records)} files processed. Populating ontology..."
        )

        # Load content type mapping
        content_type_path = get_content_types_path()
        with open(content_type_path, "r") as f:
            content_type_map = json.load(f)
        # Build reverse mapping for content types
        ext_to_content_class: Dict[str, str] = {}
        name_to_content_class: Dict[str, str] = {}
        for class_name, exts in content_type_map.items():
            for ext in exts:
                ext_l = ext.lower()
                if ext_l.startswith("."):
                    ext_to_content_class[ext_l] = class_name
                else:
                    name_to_content_class[ext_l] = class_name

        # --- Write code structure entities to TTL & RDF ---
        g = Graph()
        ttl_path = get_output_path("web_development_ontology.ttl")
        if os.path.exists(ontology_path):
            g.parse(ontology_path, format="xml")
        g.bind("wdo", WDO)
        g.bind("inst", INST)
        g.bind("skos", SKOS)

        # Track repositories to avoid duplicates
        processed_repos: set[str] = set()

        ttl_task = progress.add_task("[blue]Writing TTL...", total=len(file_records))
        for record in file_records:
            repo_name = record["repository"]
            repo_clean = repo_name.replace(" ", "_")
            path_clean = record["path"].replace(" ", "_")
            repo_enc = uri_safe_string(repo_clean)
            path_enc = uri_safe_string(path_clean)
            file_uri = INST[f"{repo_enc}/{path_enc}"]
            wdo_class_uri = record["class_uri"]

            # Define repository entity if not already processed
            if repo_enc not in processed_repos:
                repo_uri = INST[repo_enc]
                g.add((repo_uri, RDF.type, WDO.Repository))
                # --- NEW: Create repository metadata as InformationContentEntity ---
                repo_metadata_uri = INST[f"{repo_enc}_metadata"]
                g.add((repo_metadata_uri, RDF.type, WDO.InformationContentEntity))
                g.add(
                    (
                        repo_metadata_uri,
                        WDO.hasSimpleName,
                        Literal(repo_name, datatype=XSD.string),
                    )
                )
                # Link metadata to repository using isAbout
                is_about_uri = URIRef(str(WDO) + "isAbout")
                g.add((repo_metadata_uri, is_about_uri, repo_uri))
                # Link repository as asset/resource for the organization
                org_name = os.path.basename(os.path.abspath(input_dir))
                org_uri = INST[uri_safe_string(org_name)]
                g.add((org_uri, RDFS.member, repo_uri))
                g.add((org_uri, RDF.type, WDO.Organization))
                g.add((org_uri, SKOS.prefLabel, Literal(org_name, datatype=XSD.string)))
                processed_repos.add(repo_enc)

            # 1. File as DigitalInformationCarrier (most specific class)
            g.add((file_uri, RDF.type, URIRef(wdo_class_uri)))
            superclass_chain = [
                str(s) for s in extractor.ontology.get_superclass_chain(wdo_class_uri)
            ]
            for superclass_uri in superclass_chain:
                g.add((file_uri, RDF.type, URIRef(superclass_uri)))
            g.add(
                (
                    file_uri,
                    WDO.hasRelativePath,
                    Literal(record["path"], datatype=XSD.string),
                )
            )
            g.add(
                (
                    file_uri,
                    WDO.hasSizeInBytes,
                    Literal(record["size_bytes"], datatype=XSD.integer),
                )
            )
            # Use wdo:hasFile to link repository to file (membership)
            g.add((INST[repo_enc], WDO.hasFile, file_uri))
            g.add(
                (
                    file_uri,
                    WDO.fileExtension,
                    Literal(record["extension"], datatype=XSD.string),
                )
            )
            # 2. Content as InformationContentEntity (most specific class)
            content_uri = INST[f"{repo_enc}/{path_enc}_content"]
            # Determine the most specific content class
            content_class_uri = None
            fname_lower = record["filename"].lower()
            ext = Path(record["filename"]).suffix.lower()
            # Try exact filename match for special content files
            for key, class_name in name_to_content_class.items():
                if fname_lower == key:
                    try:
                        content_class_uri = str(
                            extractor.ontology.get_class(class_name)
                        )
                    except Exception:
                        content_class_uri = str(WDO.InformationContentEntity)
                    break
            # Try extension match for granular content class
            if not content_class_uri and ext in ext_to_content_class:
                class_name = ext_to_content_class[ext]
                try:
                    content_class_uri = str(extractor.ontology.get_class(class_name))
                except Exception:
                    content_class_uri = str(WDO.InformationContentEntity)
            # Fallback to InformationContentEntity
            if not content_class_uri:
                content_class_uri = str(WDO.InformationContentEntity)
            g.add((content_uri, RDF.type, URIRef(content_class_uri)))
            g.add(
                (
                    content_uri,
                    WDO.hasSimpleName,
                    Literal(record["filename"], datatype=XSD.string),
                )
            )
            g.add(
                (
                    content_uri,
                    WDO.programmingLanguage,
                    Literal(
                        record["ontology_class"].replace("Code", ""),
                        datatype=XSD.string,
                    ),
                )
            )
            # Compute actual line count
            abs_path = record["abs_path"]  # Use the correct file path
            try:
                with open(abs_path, "r", encoding="utf-8", errors="ignore") as f:
                    line_count = sum(1 for _ in f)
            except Exception:
                line_count = 0
            g.add(
                (
                    content_uri,
                    WDO.hasLineCount,
                    Literal(line_count, datatype=XSD.integer),
                )
            )
            # 3. Link file and content
            g.add((file_uri, WDO.bearerOfInformation, content_uri))
            g.add((content_uri, WDO.informationBorneBy, file_uri))
            progress.advance(ttl_task)
        g.serialize(destination=ttl_path, format="turtle")
        logger.info(f"Ontology updated and saved to {ttl_path}")

    console.print(
        f"[bold green]File extraction complete:[/bold green] {len(file_records)} files processed"
    )
    console.print(
        f"[bold green]Ontology updated and saved to:[/bold green] [cyan]{ttl_path}[/cyan]"
    )


if __name__ == "__main__":
    main()
