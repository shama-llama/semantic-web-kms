"""Content extraction module for Semantic Web KMS."""

import json
import logging
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from rdflib import Graph, Literal, URIRef
from rdflib.namespace import OWL, RDF, RDFS, SKOS, XSD
from rich.console import Console
from rich.progress import BarColumn, Progress, TextColumn, TimeElapsedColumn

try:
    from PIL import Image

    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

from app.core.namespaces import INST, WDO
from app.core.paths import (
    get_carrier_types_path,
    get_content_types_path,
    get_excluded_directories_path,
    get_input_dir,
    get_ontology_cache_path,
    get_output_path,
    get_web_dev_ontology_path,
    uri_safe_file_path,
    uri_safe_string,
)
from app.core.progress_tracker import get_current_tracker
from app.extraction.utils.classification_utils import (
    classify_file,
    load_classifiers_from_json,
)
from app.extraction.utils.file_utils import (
    FileRecord,
    build_file_records,
    count_total_files,
    get_repo_dirs,
)
from app.extraction.utils.rdf_utils import (
    add_repository_metadata,
    write_ttl_with_progress,
)

logger = logging.getLogger("content_extractor")


class FrameworkRegistry:
    """Registry to manage unique framework URIs across the entire extraction process."""

    def __init__(self):
        """Initialize the framework registry with an empty dictionary."""
        self._framework_uris: Dict[str, URIRef] = {}

    def get_or_create_framework_uri(self, framework_name: str) -> URIRef:
        """
        Get existing framework URI or create a new one if it doesn't exist.

        Args:
            framework_name: The name of the software framework.

        Returns:
            URIRef: The URI for the framework (either existing or newly created).
        """
        if framework_name not in self._framework_uris:
            # Create a new URI for this framework
            safe_name = uri_safe_string(framework_name)
            framework_uri = INST[f"framework_{safe_name}"]
            self._framework_uris[framework_name] = framework_uri
        return self._framework_uris[framework_name]

    def get_registered_frameworks(self) -> Dict[str, URIRef]:
        """
        Get all registered frameworks and their URIs.

        Returns:
            Dict[str, URIRef]: A copy of the internal framework URI mapping.
        """
        return self._framework_uris.copy()

    def get_framework_count(self) -> int:
        """
        Get the total number of unique frameworks registered.

        Returns:
            int: The number of unique frameworks registered.
        """
        return len(self._framework_uris)

    def reset(self) -> None:
        """Reset the framework registry to empty state."""
        self._framework_uris.clear()

    def log_registered_frameworks(self) -> None:
        """Log all registered frameworks."""
        if self._framework_uris:
            logger.info(f"Registered frameworks ({len(self._framework_uris)}):")
            for name, uri in self._framework_uris.items():
                logger.info(f"  {name} -> {uri}")
        else:
            logger.info("No frameworks registered")


# Global framework registry instance
framework_registry = FrameworkRegistry()


class ContentRegistry:
    """Registry to manage unique content URIs across the entire extraction process."""

    def __init__(self):
        """Initialize the content registry with an empty dictionary."""
        self._content_uris: Dict[str, URIRef] = {}

    def get_or_create_content_uri(self, repo_enc: str, path_enc: str) -> URIRef:
        """
        Get existing content URI or create a new one if it doesn't exist.

        Args:
            repo_enc: URI-safe encoded repository name.
            path_enc: URI-safe encoded file path.

        Returns:
            URIRef: The URI for the content (either existing or newly created).
        """
        content_key = f"{repo_enc}/{path_enc}_content"
        if content_key not in self._content_uris:
            # Create a new URI for this content
            content_uri = INST[content_key]
            self._content_uris[content_key] = content_uri
        return self._content_uris[content_key]

    def get_registered_contents(self) -> Dict[str, URIRef]:
        """
        Get all registered contents and their URIs.

        Returns:
            Dict[str, URIRef]: A copy of the internal content URI mapping.
        """
        return self._content_uris.copy()

    def get_content_count(self) -> int:
        """
        Get the total number of unique contents registered.

        Returns:
            int: The number of unique contents registered.
        """
        return len(self._content_uris)

    def reset(self) -> None:
        """Reset the content registry to empty state."""
        self._content_uris.clear()

    def log_registered_contents(self) -> None:
        """Log all registered contents."""
        if self._content_uris:
            logger.info(f"Registered contents ({len(self._content_uris)}):")
            for key, uri in self._content_uris.items():
                logger.info(f"  {key} -> {uri}")
        else:
            logger.info("No contents registered")


# Global content registry instance
content_registry = ContentRegistry()


class SoftwarePackageRegistry:
    """Registry to manage unique software package URIs across the entire extraction process."""

    def __init__(self):
        """Initialize the software package registry with an empty dictionary."""
        self._package_uris: Dict[str, URIRef] = {}

    def get_or_create_package_uri(self, package_name: str) -> URIRef:
        """
        Get existing software package URI or create a new one if it doesn't exist.

        Args:
            package_name: The name of the software package.

        Returns:
            URIRef: The URI for the software package (either existing or newly created).
        """
        if package_name not in self._package_uris:
            # Create a new URI for this software package
            safe_name = uri_safe_string(package_name)
            package_uri = INST[f"package_{safe_name}"]
            self._package_uris[package_name] = package_uri
        return self._package_uris[package_name]

    def get_registered_packages(self) -> Dict[str, URIRef]:
        """
        Get all registered software packages and their URIs.

        Returns:
            Dict[str, URIRef]: A copy of the internal software package URI mapping.
        """
        return self._package_uris.copy()

    def get_package_count(self) -> int:
        """
        Get the total number of unique software packages registered.

        Returns:
            int: The number of unique software packages registered.
        """
        return len(self._package_uris)

    def reset(self) -> None:
        """Reset the software package registry to empty state."""
        self._package_uris.clear()

    def log_registered_packages(self) -> None:
        """Log all registered software packages."""
        if self._package_uris:
            logger.info(f"Registered software packages ({len(self._package_uris)}):")
            for name, uri in self._package_uris.items():
                logger.info(f"  {name} -> {uri}")
        else:
            logger.info("No software packages registered")


# Global software package registry instance
software_package_registry = SoftwarePackageRegistry()


class OntologyWrapper:
    """Ontology wrapper that loads classes from JSON configuration files."""

    def __init__(self, ontology_path: str):
        """
        Initialize by loading classes from JSON configuration files.

        Args:
            ontology_path: Path to the ontology OWL file.
        """
        self.graph = Graph()
        self._load_classes_from_json(ontology_path)

    def _load_classes_from_json(self, ontology_path: str) -> None:
        """
        Load classes from JSON configuration files instead of hardcoded lists.

        Args:
            ontology_path: Path to the ontology OWL file.
        """
        if not os.path.exists(ontology_path):
            return
        # Parse the ontology file
        temp_graph = Graph()
        temp_graph.parse(ontology_path, format="xml")

        # Load ontology cache for validation
        cache_path = get_ontology_cache_path()
        if os.path.exists(cache_path):
            with open(cache_path, "r") as f:
                ontology_cache = json.load(f)
                available_classes = set(ontology_cache.get("classes", []))
        else:
            available_classes = set()

        # Load classes from content_types.json
        content_types_path = get_content_types_path()
        if os.path.exists(content_types_path):
            with open(content_types_path, "r") as f:
                content_data = json.load(f)
                content_classes = {
                    c["class"] for c in content_data.get("classifiers", [])
                }
        else:
            content_classes = set()

        # Load classes from carrier_types.json
        carrier_types_path = get_carrier_types_path()
        if os.path.exists(carrier_types_path):
            with open(carrier_types_path, "r") as f:
                carrier_data = json.load(f)
                carrier_classes = {
                    c["class"] for c in carrier_data.get("classifiers", [])
                }
        else:
            carrier_classes = set()

        # Combine all classes and filter by what's available in ontology
        all_classes = content_classes | carrier_classes
        required_classes = {cls for cls in all_classes if cls in available_classes}

        # Add base classes that are always needed
        base_classes = {"InformationContentEntity", "Repository", "Organization"}
        required_classes.update(base_classes)

        # Extract only the required classes and their superclass relationships
        for class_name in required_classes:
            class_uri = self._find_class_by_name(temp_graph, class_name)
            if class_uri:
                # Add the class
                self.graph.add((class_uri, RDF.type, OWL.Class))

                # Add superclass relationships
                superclass = temp_graph.value(class_uri, RDFS.subClassOf)
                if superclass:
                    self.graph.add((class_uri, RDFS.subClassOf, superclass))
                    # Also add the superclass if it's not already added
                    if (superclass, RDF.type, OWL.Class) in temp_graph:
                        self.graph.add((superclass, RDF.type, OWL.Class))

        # Load all properties from the ontology instead of hardcoding them
        for s in temp_graph.subjects(RDF.type, OWL.ObjectProperty):
            self.graph.add((s, RDF.type, OWL.ObjectProperty))
        for s in temp_graph.subjects(RDF.type, OWL.DatatypeProperty):
            self.graph.add((s, RDF.type, OWL.DatatypeProperty))

    def _find_class_by_name(self, graph: Graph, class_name: str) -> Optional[URIRef]:
        """
        Find a class URI by name (label or local part).

        Args:
            graph: The RDF graph to search.
            class_name: The class name to look for.

        Returns:
            Optional[URIRef]: The URI of the class if found, else None.
        """
        for s in graph.subjects(RDF.type, OWL.Class):
            label = graph.value(s, RDFS.label)
            if label and str(label).lower() == class_name.lower():
                return URIRef(str(s))
            # fallback: match local part
            if (
                str(s).split("#")[-1] == class_name
                or str(s).split("/")[-1] == class_name
            ):
                return URIRef(str(s))
        return None

    def _find_property_by_name(self, graph: Graph, prop_name: str) -> Optional[URIRef]:
        """
        Find a property URI by name (label or local part).

        Args:
            graph: The RDF graph to search.
            prop_name: The property name to look for.

        Returns:
            Optional[URIRef]: The URI of the property if found, else None.
        """
        for s in graph.subjects(RDF.type, OWL.ObjectProperty):
            label = graph.value(s, RDFS.label)
            if label and str(label).lower() == prop_name.lower():
                return URIRef(str(s))
            if str(s).split("#")[-1] == prop_name or str(s).split("/")[-1] == prop_name:
                return URIRef(str(s))
        for s in graph.subjects(RDF.type, OWL.DatatypeProperty):
            label = graph.value(s, RDFS.label)
            if label and str(label).lower() == prop_name.lower():
                return URIRef(str(s))
            if str(s).split("#")[-1] == prop_name or str(s).split("/")[-1] == prop_name:
                return URIRef(str(s))
        return None

    def get_class(self, class_name: str) -> URIRef:
        """
        Return the URI for a class by name, or raise KeyError if not found.

        Args:
            class_name: The class name to look up.

        Returns:
            URIRef: The URI of the class.

        Raises:
            KeyError: If the class is not found in the ontology.
        """
        uri = self._find_class_by_name(self.graph, class_name)
        if uri:
            return uri
        raise KeyError(f"Class '{class_name}' not found in ontology.")

    def get_superclass_chain(self, class_uri: str) -> List[str]:
        """
        Return the full superclass chain for a class URI, up to the root.

        Args:
            class_uri: The URI of the class to trace.

        Returns:
            List[str]: List of superclass URIs up to the root.
        """
        chain: List[str] = []
        current = URIRef(class_uri)
        visited: Set[URIRef] = set()
        while True:
            superclass = self.graph.value(current, RDFS.subClassOf)
            if superclass and superclass not in visited:
                chain.append(str(superclass))
                visited.add(URIRef(str(superclass)))
                current = URIRef(str(superclass))
            else:
                break
        return chain


def get_line_count(abs_path):
    """
    Return the number of lines in a file, or 0 if the file cannot be read.

    Args:
        abs_path (str): Absolute path to the file.

    Returns:
        int: Number of lines in the file, or 0 if the file cannot be read.

    Raises:
        None. Any exception is caught and 0 is returned.
    """
    try:
        with open(abs_path, "r", encoding="utf-8", errors="ignore") as f:
            return sum(1 for _ in f)
    except Exception:
        return 0


@dataclass
class ExtractionContext:
    """Context object for passing extraction configuration and classifiers to helper functions."""

    content_classifiers: List[Tuple[str, re.Pattern]]
    content_ignore_patterns: List[re.Pattern]
    ontology: Any


def add_content_triples(
    g,
    record: FileRecord,
    context: ExtractionContext,
    file_uri,
    repo_enc,
    path_enc,
):
    """
    Add RDF triples for the content entity associated with a file.

    Args:
        g (Graph): The RDF graph to which triples are added.
        record (FileRecord): The file record for the content.
        context (ExtractionContext): Extraction context with classifiers.
        file_uri (URIRef): URI for the file entity.
        repo_enc (str): Encoded repository name.
        path_enc (str): Encoded file path.

    Returns:
        None. Modifies the RDF graph in place.

    Raises:
        None directly, but may propagate exceptions from called functions if not handled.
    """
    content_uri = content_registry.get_or_create_content_uri(repo_enc, path_enc)
    content_class_uri = record.class_uri
    if not content_class_uri:
        return
    g.add((content_uri, RDF.type, URIRef(content_class_uri)))
    g.add(
        (content_uri, WDO.hasSimpleName, Literal(record.filename, datatype=XSD.string))
    )
    g.add(
        (
            content_uri,
            RDFS.label,
            Literal(f"content: {record.filename}", datatype=XSD.string),
        )
    )
    class_name = record.ontology_class
    programming_language_classes = {
        "JavaScriptCode",
        "PHPCode",
        "PythonCode",
        "RubyCode",
        "GraphQLCode",
        "SQLCode",
        "CSharpCode",
        "GoCode",
        "JavaCode",
        "RustCode",
        "TypeScriptCode",
    }
    if class_name in programming_language_classes:
        # Convert tree-sitter language names to RDF-friendly names
        tree_sitter_to_rdf_mapping = {
            "c_sharp": "csharp",
            "typescript": "typescript",
            "javascript": "javascript",
            "python": "python",
            "java": "java",
            "go": "go",
            "rust": "rust",
            "ruby": "ruby",
            "php": "php",
            "scala": "scala",
            "swift": "swift",
            "lua": "lua",
        }
        language_name = class_name.replace("Code", "").lower()
        # Map tree-sitter names to RDF-friendly names
        rdf_language_name = tree_sitter_to_rdf_mapping.get(language_name, language_name)
        g.add(
            (
                content_uri,
                WDO.hasProgrammingLanguage,
                Literal(rdf_language_name, datatype=XSD.string),
            )
        )
    if class_name in ["ConfigurationSetting", "CommitMessage", "Log"]:
        try:
            with open(record.abs_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read(1000)
            g.add((content_uri, WDO.hasContent, Literal(content, datatype=XSD.string)))
        except (OSError, IOError) as e:
            # Log the error but continue processing
            print(f"Warning: Could not read content from {record.abs_path}: {e}")
    add_asset_metadata_triples(g, content_uri, record.abs_path, class_name)
    add_dependency_and_framework_triples(g, content_uri, record.abs_path, class_name)
    add_special_content_triples(g, content_uri, record.abs_path, class_name)
    if class_name.endswith("Code") or class_name in [
        "SoftwareCode",
        "ProgrammingLanguageCode",
        "QueryLanguageCode",
        "WebPresentationCode",
    ]:
        line_count = get_line_count(record.abs_path)
        g.add(
            (content_uri, WDO.hasLineCount, Literal(line_count, datatype=XSD.integer))
        )
    g.add((file_uri, WDO.bearerOfInformation, content_uri))
    g.add((content_uri, WDO.informationBorneBy, file_uri))


def add_content_only_triples(
    g,
    record: FileRecord,
    context: ExtractionContext,
    input_dir,
    processed_repos,
):
    """
    Add content-only RDF triples for a file, classifying its content type and linking to the file entity.

    Args:
        g: The RDF graph to which triples are added.
        record: The FileRecord representing the file.
        context: ExtractionContext with classifier and ignore pattern info.
        input_dir: The input directory path.
        processed_repos: Set of already processed repository names.

    Returns:
        None. Modifies the RDF graph in place.

    Raises:
        None directly, but may propagate exceptions from called functions if not handled.
    """
    content_class, content_class_uri, _ = classify_file(
        record.filename,
        context.content_classifiers,
        context.content_ignore_patterns,
        context.ontology,
        default_class="InformationContentEntity",
    )
    if not content_class_uri:
        return
    content_record = FileRecord(**{**record.__dict__})
    content_record.class_uri = content_class_uri
    content_record.ontology_class = (
        content_class_uri.split("#")[-1]
        if content_class_uri and "#" in content_class_uri
        else content_class_uri.split("/")[-1] if content_class_uri else ""
    )
    repo_name = record.repository
    repo_clean = repo_name.replace(" ", "_")
    path_clean = record.path.replace(" ", "_")
    repo_enc = uri_safe_string(repo_clean)
    path_enc = uri_safe_file_path(path_clean)
    file_uri = INST[f"{repo_enc}/{path_enc}"]
    if repo_enc not in processed_repos:
        add_repository_metadata(g, repo_enc, repo_name, input_dir, processed_repos)
    add_content_triples(
        g,
        content_record,
        context,
        file_uri,
        repo_enc,
        path_enc,
    )


def extract_image_metadata(file_path: str) -> Dict[str, Any]:
    """
    Extract metadata from image files using PIL.

    Args:
        file_path (str): Path to the image file.

    Returns:
        Dict[str, Any]: Dictionary of extracted metadata (width, height, format, mode, EXIF tags).

    Raises:
        None. Any exception is caught and an empty dict is returned.
    """
    metadata: Dict[str, Any] = {}
    if not PIL_AVAILABLE:
        return metadata

    try:
        with Image.open(file_path) as img:
            metadata["width"] = img.width
            metadata["height"] = img.height
            metadata["format"] = img.format
            metadata["mode"] = img.mode

            # Extract EXIF data if available
            try:
                exif = img._getexif()  # type: ignore
                if exif:
                    # Common EXIF tags
                    exif_tags = {
                        36867: "DateTimeOriginal",
                        271: "Make",
                        272: "Model",
                        37377: "FNumber",
                        37378: "ExposureTime",
                        37383: "ISOSpeedRatings",
                    }
                    for tag_id, tag_name in exif_tags.items():
                        if tag_id in exif:
                            metadata[tag_name] = str(exif[tag_id])
            except (AttributeError, TypeError):
                # EXIF data not available
                pass
    except Exception as e:
        # Log the error but continue processing
        print(f"Warning: Could not extract image metadata from {file_path}: {e}")

    return metadata


def extract_media_metadata(file_path: str, file_type: str) -> Dict[str, Any]:
    """
    Extract basic metadata from media files (video, audio, font).

    Args:
        file_path (str): Path to the media file.
        file_type (str): Type of the file (e.g., 'VideoDescription').

    Returns:
        Dict[str, Any]: Dictionary of extracted metadata (file size, format, media type).

    Raises:
        None. Any exception is caught and an empty dict is returned.
    """
    metadata: Dict[str, Any] = {}

    try:
        # Get file size
        file_size = os.path.getsize(file_path)
        metadata["file_size"] = file_size

        # Extract format from extension
        ext = Path(file_path).suffix.lower()
        if ext:
            metadata["format"] = ext[1:]  # Remove the dot

        # For video files, try to extract basic info
        if file_type in ["VideoDescription", "VideoFile"]:
            # This would require additional libraries like ffmpeg-python
            # For now, just set basic properties
            metadata["media_type"] = "video"

        # For audio files
        elif file_type in ["AudioDescription", "AudioFile"]:
            metadata["media_type"] = "audio"

        # For font files
        elif file_type in ["FontDescription", "FontFile"]:
            metadata["media_type"] = "font"

    except Exception as e:
        # Log the error but continue processing
        print(f"Warning: Could not extract media metadata from {file_path}: {e}")

    return metadata


def add_asset_metadata_triples(
    g: Graph, content_uri: URIRef, file_path: str, class_name: str
):
    """
    Add asset-specific metadata triples based on file type, strictly following ontology domain/range.

    Args:
        g (Graph): The RDF graph to which triples are added.
        content_uri (URIRef): URI for the content entity.
        file_path (str): Path to the file.
        class_name (str): Ontology class name for the content.

    Returns:
        None. Modifies the RDF graph in place.

    Raises:
        None directly, but may propagate exceptions from called functions if not handled.
    """
    # Only add image properties for ImageDescription (not ImageFile)
    if class_name == "ImageDescription":
        metadata = extract_image_metadata(file_path)
        if "width" in metadata:
            g.add(
                (
                    content_uri,
                    WDO.hasImageWidth,
                    Literal(metadata["width"], datatype=XSD.nonNegativeInteger),
                )
            )
        if "height" in metadata:
            g.add(
                (
                    content_uri,
                    WDO.hasImageHeight,
                    Literal(metadata["height"], datatype=XSD.nonNegativeInteger),
                )
            )
        if "format" in metadata:
            g.add(
                (
                    content_uri,
                    WDO.hasImageFormatName,
                    Literal(metadata["format"], datatype=XSD.string),
                )
            )

    # Only add video properties for VideoDescription
    elif class_name == "VideoDescription":
        metadata = extract_media_metadata(file_path, class_name)
        if "format" in metadata:
            g.add(
                (
                    content_uri,
                    WDO.hasMediaEncodingFormat,
                    Literal(metadata["format"], datatype=XSD.string),
                )
            )
        if "file_size" in metadata:
            g.add(
                (
                    content_uri,
                    WDO.hasMediaDuration,
                    Literal(metadata["file_size"], datatype=XSD.decimal),
                )
            )
        # hasFrameRate would require video analysis library - not implemented yet

    # Only add audio properties for AudioDescription
    elif class_name == "AudioDescription":
        metadata = extract_media_metadata(file_path, class_name)
        if "format" in metadata:
            g.add(
                (
                    content_uri,
                    WDO.hasMediaEncodingFormat,
                    Literal(metadata["format"], datatype=XSD.string),
                )
            )
        if "file_size" in metadata:
            g.add(
                (
                    content_uri,
                    WDO.hasSampleRate,
                    Literal(metadata["file_size"], datatype=XSD.decimal),
                )
            )

    # Only add font properties for FontDescription
    elif class_name == "FontDescription":
        metadata = extract_media_metadata(file_path, class_name)
        filename = Path(file_path).stem
        if filename:
            g.add(
                (
                    content_uri,
                    WDO.hasFontFamilyName,
                    Literal(filename, datatype=XSD.string),
                )
            )
        if "format" in metadata:
            g.add(
                (
                    content_uri,
                    WDO.hasFontStyle,
                    Literal(metadata["format"], datatype=XSD.string),
                )
            )


def extract_dependencies_from_build_file(
    file_path: str, file_type: str
) -> List[Dict[str, str]]:
    """
    Extract dependencies from build files with version information.

    Args:
        file_path (str): Path to the build file.
        file_type (str): Type of the build file (e.g., 'BuildScript').

    Returns:
        List[Dict[str, str]]: List of dependencies with 'name' and 'version' keys.

    Raises:
        None. Any exception is caught and an empty list is returned.
    """
    dependencies = []

    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()

        if file_type == "BuildScript" and "package.json" in file_path:
            # Extract dependencies from package.json
            import json

            try:
                data = json.loads(content)
                if "dependencies" in data:
                    for dep_name, dep_version in data["dependencies"].items():
                        dependencies.append(
                            {"name": dep_name, "version": str(dep_version)}
                        )
                if "devDependencies" in data:
                    for dep_name, dep_version in data["devDependencies"].items():
                        dependencies.append(
                            {"name": dep_name, "version": str(dep_version)}
                        )
            except json.JSONDecodeError:
                pass

        elif file_type == "BuildScript" and "requirements.txt" in file_path:
            # Extract dependencies from requirements.txt
            for line in content.split("\n"):
                line = line.strip()
                if line and not line.startswith("#"):
                    # Extract package name and version
                    if "==" in line:
                        package, version = line.split("==", 1)
                        dependencies.append({"name": package, "version": version})
                    elif ">=" in line:
                        package, version = line.split(">=", 1)
                        dependencies.append(
                            {"name": package, "version": f">={version}"}
                        )
                    elif "<=" in line:
                        package, version = line.split("<=", 1)
                        dependencies.append(
                            {"name": package, "version": f"<={version}"}
                        )
                    else:
                        package = (
                            line.split("==")[0]
                            .split(">=")[0]
                            .split("<=")[0]
                            .split("~=")[0]
                            .split("!=")[0]
                        )
                        if package:
                            dependencies.append({"name": package, "version": ""})

        elif file_type == "BuildScript" and "composer.json" in file_path:
            # Extract dependencies from composer.json
            import json

            try:
                data = json.loads(content)
                if "require" in data:
                    for dep_name, dep_version in data["require"].items():
                        dependencies.append(
                            {"name": dep_name, "version": str(dep_version)}
                        )
                if "require-dev" in data:
                    for dep_name, dep_version in data["require-dev"].items():
                        dependencies.append(
                            {"name": dep_name, "version": str(dep_version)}
                        )
            except json.JSONDecodeError:
                pass

        elif file_type == "BuildScript" and "Gemfile" in file_path:
            # Extract dependencies from Gemfile
            for line in content.split("\n"):
                line = line.strip()
                if line.startswith("gem "):
                    # Extract gem name and version
                    parts = line.split('"')
                    if len(parts) >= 2:
                        gem_name = parts[1]
                        version = ""
                        if len(parts) >= 4:
                            version = parts[3]
                        dependencies.append({"name": gem_name, "version": version})

        elif file_type == "BuildScript" and "go.mod" in file_path:
            # Extract dependencies from go.mod
            for line in content.split("\n"):
                line = line.strip()
                if line.startswith("require "):
                    # Extract module name and version
                    parts = line.split()
                    if len(parts) >= 3:
                        module_name = parts[1]
                        version = parts[2]
                        dependencies.append({"name": module_name, "version": version})

        elif file_type == "BuildScript" and "Cargo.toml" in file_path:
            # Extract dependencies from Cargo.toml
            for line in content.split("\n"):
                line = line.strip()
                if line.startswith("[dependencies.") or line.startswith(
                    "[dev-dependencies."
                ):
                    # Extract crate name
                    if line.startswith("[dependencies."):
                        crate_name = line[13:-1]  # Remove "[dependencies." and "]"
                    else:
                        crate_name = line[17:-1]  # Remove "[dev-dependencies." and "]"
                    dependencies.append({"name": crate_name, "version": ""})

    except Exception as e:
        # Log the error but continue processing
        print(f"Warning: Could not extract dependencies from {file_path}: {e}")

    return dependencies


def extract_frameworks_from_code_file(
    file_path: str, file_type: str
) -> List[Dict[str, str]]:
    """
    Extract frameworks from code files based on imports and patterns with version info.

    Args:
        file_path (str): Path to the code file.
        file_type (str): Type of the code file (e.g., 'JavaScriptCode').

    Returns:
        List[Dict[str, str]]: List of frameworks with 'name' and 'version' keys.

    Raises:
        None. Any exception is caught and an empty list is returned.
    """
    frameworks = []

    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()

        if file_type in ["JavaScriptCode", "TypeScriptCode"]:
            # Common JavaScript/TypeScript frameworks - look for import/require statements
            js_frameworks = [
                "react",
                "vue",
                "angular",
                "express",
                "next",
                "nuxt",
                "gatsby",
                "svelte",
                "jquery",
                "lodash",
                "moment",
                "axios",
                "redux",
                "mobx",
                "graphql",
            ]
            for framework in js_frameworks:
                # Look for import/require patterns to avoid false positives
                import_patterns = [
                    rf"import.*['\"]{framework}['\"]",
                    rf"require\(['\"]{framework}['\"]\)",
                    rf"from ['\"]{framework}['\"]",
                    rf"import.*{framework}",
                    rf"require\(['\"]{framework}",
                ]
                for pattern in import_patterns:
                    if re.search(pattern, content, re.IGNORECASE):
                        frameworks.append({"name": framework, "version": ""})
                        break

        elif file_type == "PythonCode":
            # Common Python frameworks - look for import statements
            py_frameworks = [
                "django",
                "flask",
                "fastapi",
                "tornado",
                "bottle",
                "pyramid",
                "cherrypy",
                "numpy",
                "pandas",
                "matplotlib",
                "scikit-learn",
                "tensorflow",
                "pytorch",
            ]
            for framework in py_frameworks:
                # Look for import patterns
                import_patterns = [
                    rf"import {framework}",
                    rf"from {framework}",
                    rf"import.*{framework}",
                ]
                for pattern in import_patterns:
                    if re.search(pattern, content, re.IGNORECASE):
                        frameworks.append({"name": framework, "version": ""})
                        break

        elif file_type == "JavaCode":
            # Common Java frameworks - look for import statements
            java_frameworks = [
                "spring",
                "hibernate",
                "junit",
                "mockito",
                "log4j",
                "slf4j",
                "jackson",
                "gson",
                "okhttp",
                "retrofit",
                "dagger",
                "guice",
            ]
            for framework in java_frameworks:
                # Look for import patterns
                import_patterns = [
                    rf"import.*{framework}",
                    rf"import {framework}",
                ]
                for pattern in import_patterns:
                    if re.search(pattern, content, re.IGNORECASE):
                        frameworks.append({"name": framework, "version": ""})
                        break

        elif file_type == "CSharpCode":
            # Common C# frameworks - look for using statements
            cs_frameworks = [
                "asp.net",
                "entity",
                "nhibernate",
                "nunit",
                "moq",
                "log4net",
                "serilog",
                "newtonsoft",
                "system.text.json",
                "mediatr",
                "autofac",
            ]
            for framework in cs_frameworks:
                # Look for using patterns
                import_patterns = [
                    rf"using {framework}",
                    rf"using.*{framework}",
                ]
                for pattern in import_patterns:
                    if re.search(pattern, content, re.IGNORECASE):
                        frameworks.append({"name": framework, "version": ""})
                        break

    except Exception as e:
        # Log the error but continue processing
        print(f"Warning: Could not extract frameworks from {file_path}: {e}")

    return frameworks


# Framework type mapping for ontology subclass assignment
FRAMEWORK_TYPE_MAP = {
    # JavaScript frameworks
    "react": "JavaScriptFramework",
    "vue": "JavaScriptFramework",
    "angular": "JavaScriptFramework",
    "express": "JavaScriptFramework",
    "next": "JavaScriptFramework",
    "nuxt": "JavaScriptFramework",
    "gatsby": "JavaScriptFramework",
    "svelte": "JavaScriptFramework",
    "jquery": "JavaScriptFramework",
    "lodash": "JavaScriptFramework",
    "moment": "JavaScriptFramework",
    "axios": "JavaScriptFramework",
    "redux": "JavaScriptFramework",
    "mobx": "JavaScriptFramework",
    "graphql": "JavaScriptFramework",
    # CSS frameworks
    "bootstrap": "CSSFramework",
    "tailwind": "CSSFramework",
    "bulma": "CSSFramework",
    "foundation": "CSSFramework",
    "semantic": "CSSFramework",
    "uikit": "CSSFramework",
    "materialize": "CSSFramework",
    "purecss": "CSSFramework",
    "spectre": "CSSFramework",
    "milligram": "CSSFramework",
}


def add_dependency_and_framework_triples(
    g: Graph, content_uri: URIRef, file_path: str, class_name: str
):
    """
    Add dependency and framework triples based on file type, strictly following ontology domain/range.

    Args:
        g (Graph): The RDF graph to which triples are added.
        content_uri (URIRef): URI for the content entity.
        file_path (str): Path to the file.
        class_name (str): Ontology class name for the content.

    Returns:
        None. Modifies the RDF graph in place.

    Raises:
        None directly, but may propagate exceptions from called functions if not handled.
    """
    # Only BuildScript or SoftwarePackage can specify dependencies
    if class_name == "BuildScript":
        dependencies = extract_dependencies_from_build_file(file_path, class_name)
        for dep in dependencies:
            dep_label = dep["name"]
            dep_uri = software_package_registry.get_or_create_package_uri(dep_label)
            # Only add type/label/version if this is a new package instance in the graph
            if not (dep_uri, RDF.type, WDO.SoftwarePackage) in g:
                g.add((dep_uri, RDF.type, WDO.SoftwarePackage))
                g.add(
                    (
                        dep_uri,
                        WDO.hasSimpleName,
                        Literal(dep_label, datatype=XSD.string),
                    )
                )
                g.add((dep_uri, RDFS.label, Literal(dep_label, datatype=XSD.string)))
                if dep["version"]:
                    g.add(
                        (
                            dep_uri,
                            WDO.hasVersion,
                            Literal(dep["version"], datatype=XSD.string),
                        )
                    )
            # Only BuildScript can specifyDependency
            g.add((content_uri, WDO.specifiesDependency, dep_uri))
            g.add((dep_uri, WDO.isDependencyOf, content_uri))

    # Only SoftwareCode can use frameworks
    elif class_name.endswith("Code") and class_name not in [
        "SoftwareCode",
        "ProgrammingLanguageCode",
        "QueryLanguageCode",
        "WebPresentationCode",
    ]:
        # According to ontology, only subclasses of SoftwareCode (excluding the above) can use frameworks
        frameworks = extract_frameworks_from_code_file(file_path, class_name)
        for framework in frameworks:
            framework_label = framework["name"]
            framework_uri = framework_registry.get_or_create_framework_uri(
                framework_label
            )
            # Determine ontology class for this framework
            framework_type = FRAMEWORK_TYPE_MAP.get(
                framework_label.lower(), "SoftwareFramework"
            )
            framework_class_uri = getattr(WDO, framework_type)
            if not (framework_uri, RDF.type, framework_class_uri) in g:
                g.add((framework_uri, RDF.type, framework_class_uri))
                g.add(
                    (
                        framework_uri,
                        WDO.hasSimpleName,
                        Literal(framework_label, datatype=XSD.string),
                    )
                )
                g.add(
                    (
                        framework_uri,
                        RDFS.label,
                        Literal(framework_label, datatype=XSD.string),
                    )
                )
                if framework["version"]:
                    g.add(
                        (
                            framework_uri,
                            WDO.hasVersion,
                            Literal(framework["version"], datatype=XSD.string),
                        )
                    )
            # Only SoftwareCode can useFramework
            g.add((content_uri, WDO.usesFramework, framework_uri))
            g.add((framework_uri, WDO.isFrameworkFor, content_uri))


def extract_dockerfile_base_image(file_path: str) -> str:
    """
    Extract the base image from a Dockerfile.

    Args:
        file_path (str): Path to the Dockerfile.

    Returns:
        str: Name of the base image, or an empty string if not found.

    Raises:
        None. Any exception is caught and an empty string is returned.
    """
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                line = line.strip()
                if line.upper().startswith("FROM "):
                    # Extract image name (first word after FROM)
                    parts = line.split()
                    if len(parts) >= 2:
                        return parts[1]
    except Exception as e:
        # Log the error but continue processing
        print(f"Warning: Could not extract Dockerfile base image from {file_path}: {e}")
    return ""


def extract_license_identifier(file_path: str) -> str:
    """
    Extract SPDX license identifier from a license file (best effort).

    Args:
        file_path (str): Path to the license file.

    Returns:
        str: SPDX license identifier or common license name, or an empty string if not found.

    Raises:
        None. Any exception is caught and an empty string is returned.
    """
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read(2048)
        # SPDX identifier is often in the first line or as 'SPDX-License-Identifier: ...'
        match = re.search(r"SPDX-License-Identifier:\s*([A-Za-z0-9\.-]+)", content)
        if match:
            return match.group(1)
        # Otherwise, try to match common license names
        for spdx in [
            "MIT",
            "Apache-2.0",
            "GPL-3.0",
            "BSD-3-Clause",
            "BSD-2-Clause",
            "LGPL-3.0",
            "MPL-2.0",
            "EPL-2.0",
            "Unlicense",
        ]:
            if spdx in content:
                return spdx
    except Exception as e:
        # Log the error but continue processing
        print(f"Warning: Could not extract license identifier from {file_path}: {e}")
    return ""


def add_special_content_triples(
    g: Graph, content_uri: URIRef, file_path: str, class_name: str
):
    """
    Add special triples for Dockerfile base image and License identifier.

    Args:
        g (Graph): The RDF graph to which triples are added.
        content_uri (URIRef): URI for the content entity.
        file_path (str): Path to the file.
        class_name (str): Ontology class name for the content.

    Returns:
        None. Modifies the RDF graph in place.

    Raises:
        None directly, but may propagate exceptions from called functions if not handled.
    """
    if class_name == "DockerfileSpecification":
        base_image = extract_dockerfile_base_image(file_path)
        if base_image:
            # Create a container image instance
            # Use "base_" prefix to distinguish base image instances from ontology classes
            image_uri = URIRef(f"{content_uri}_base_{uri_safe_string(base_image)}")
            g.add((image_uri, RDF.type, WDO.ContainerImage))
            g.add(
                (image_uri, WDO.hasSimpleName, Literal(base_image, datatype=XSD.string))
            )
            # Add rdfs:label for container image
            g.add((image_uri, RDFS.label, Literal(base_image, datatype=XSD.string)))
            # DockerfileSpecification isBasedOn ContainerImage
            g.add((content_uri, WDO.isBasedOn, image_uri))
            # ContainerImage isBaseFor DockerfileSpecification
            g.add((image_uri, WDO.isBaseFor, content_uri))

    elif class_name == "License":
        license_id = extract_license_identifier(file_path)
        if license_id:
            g.add(
                (
                    content_uri,
                    WDO.hasLicenseIdentifier,
                    Literal(license_id, datatype=XSD.string),
                )
            )

    elif class_name == "BuildScript":
        # Add compilation relationships for source code files
        # This would be handled when we have source code files that are compiled by this build script

        # Add packaging relationship - BuildScript packagesInto ArchiveFile
        # This would be handled when we have archive files that are created by this build script
        pass

    elif class_name.endswith("Code") and class_name not in [
        "SoftwareCode",
        "ProgrammingLanguageCode",
        "QueryLanguageCode",
        "WebPresentationCode",
    ]:
        # Add compilation relationships for source code files
        # SourceCodeFile isCompiledBy BuildScript
        # This would be handled when we have build scripts that compile this source code
        pass


def main() -> None:
    """
    Run content extraction.

    Loads configuration, scans repositories, classifies files, and writes RDF triples to output.

    Returns:
        None. Writes output to file and logs progress.

    Raises:
        Exceptions may propagate if configuration files are missing or unreadable.
    """
    ontology_path = get_web_dev_ontology_path()
    try:
        input_dir = get_input_dir()
        logger.info(f"Input directory set to: {input_dir}")
    except Exception as e:
        logger.error(f"Input directory not set or error occurred: {e}")
        raise
    excluded_dirs_path = get_excluded_directories_path()
    try:
        with open(excluded_dirs_path, "r") as f:
            excluded_dirs = set(json.load(f))
        logger.info(f"Loaded excluded directories from: {excluded_dirs_path}")
    except Exception as e:
        logger.error(f"Failed to load excluded directories: {e}")
        raise
    logger.info(
        "Starting content extraction process (ontology load, mapping, file scan, and RDF output)..."
    )
    try:
        repo_dirs = get_repo_dirs(excluded_dirs)
        total_files = count_total_files(repo_dirs, excluded_dirs)
        content_type_path = get_content_types_path()
        content_classifiers, content_ignore_patterns = load_classifiers_from_json(
            content_type_path
        )
        ontology = OntologyWrapper(ontology_path)
        context = ExtractionContext(
            content_classifiers=content_classifiers,
            content_ignore_patterns=content_ignore_patterns,
            ontology=ontology,
        )
        ttl_path = get_output_path("wdkb.ttl")
        console = Console()

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
            # Update progress tracker if available
            if tracker:
                tracker.update_stage(
                    "contentExtraction",
                    "processing",
                    0,
                    "Starting content extraction...",
                )

            extract_task = progress.add_task("Extracting content...", total=total_files)
            file_records = build_file_records(
                repo_dirs, excluded_dirs, progress, extract_task
            )
            processed_repos: Set[str] = set()
            error_count = 0
            content_records = []

            # Update progress tracker with extraction completion
            if tracker:
                tracker.update_stage(
                    "contentExtraction",
                    "processing",
                    30,
                    f"Processing {len(file_records)} files...",
                )

            processed_files = 0
            for record in file_records:
                try:
                    # Classify and prepare content record for TTL writing
                    content_class, content_class_uri, _ = classify_file(
                        record.filename,
                        content_classifiers,
                        content_ignore_patterns,
                        context.ontology,
                        default_class="InformationContentEntity",
                    )
                    if not content_class_uri:
                        continue
                    content_record = FileRecord(**{**record.__dict__})
                    content_record.class_uri = content_class_uri
                    content_record.ontology_class = (
                        content_class_uri.split("#")[-1]
                        if content_class_uri and "#" in content_class_uri
                        else (
                            content_class_uri.split("/")[-1]
                            if content_class_uri
                            else ""
                        )
                    )
                    content_records.append(content_record)
                except Exception as e:
                    logger.error(
                        f"Error processing file {getattr(record, 'abs_path', repr(record))}: {e}",
                        exc_info=True,
                    )
                    error_count += 1

                processed_files += 1
                # Update progress tracker every 10 files or at completion
                if tracker and (
                    processed_files % 10 == 0 or processed_files == len(file_records)
                ):
                    progress_percentage = 30 + int(
                        (processed_files / len(file_records)) * 30
                    )  # 30-60%
                    tracker.update_stage(
                        "contentExtraction",
                        "processing",
                        progress_percentage,
                        f"Processing content: {processed_files}/{len(file_records)} files",
                    )
            logger.info(
                f"Content extraction complete: {len(file_records)} files processed. {error_count} files failed."
            )
            # Update progress tracker for TTL writing
            if tracker:
                tracker.update_stage(
                    "contentExtraction",
                    "processing",
                    60,
                    f"Writing ontology: {len(content_records)} content records...",
                )

            # Writing TTL with progress bar
            ttl_task = progress.add_task("Writing TTL...", total=len(content_records))
            g = Graph()
            if os.path.exists(ontology_path):
                g.parse(ontology_path, format="xml")
            if os.path.exists(ttl_path):
                g.parse(ttl_path, format="turtle")
            g.bind("wdo", WDO)
            g.bind("inst", INST)
            g.bind("skos", SKOS)

            def add_content_triples_for_ttl(
                graph, record, extractor, input_dir, processed_repos, context
            ):
                repo_name = record.repository
                repo_clean = repo_name.replace(" ", "_")
                path_clean = record.path.replace(" ", "_")
                repo_enc = uri_safe_string(repo_clean)
                path_enc = uri_safe_file_path(path_clean)
                file_uri = INST[f"{repo_enc}/{path_enc}"]
                if repo_enc not in processed_repos:
                    add_repository_metadata(
                        graph, repo_enc, repo_name, input_dir, processed_repos
                    )
                add_content_triples(
                    graph,
                    record,
                    context,
                    file_uri,
                    repo_enc,
                    path_enc,
                )

            # Create a custom progress wrapper for TTL writing
            class ProgressWrapper:
                def __init__(self, rich_progress, rich_task, tracker):
                    self.rich_progress = rich_progress
                    self.rich_task = rich_task
                    self.tracker = tracker
                    self.processed = 0
                    self.total = len(content_records)
                    # Add tasks attribute to mimic Rich Progress
                    self.tasks = {rich_task: type("Task", (), {"total": self.total})()}

                def advance(self, task):
                    self.rich_progress.advance(self.rich_task)
                    self.processed += 1

                    # Update tracker every 10 records or at completion
                    if self.tracker and (
                        self.processed % 10 == 0 or self.processed == self.total
                    ):
                        # TTL writing is the second half of the stage (60-100%)
                        progress_percentage = 60 + int(
                            (self.processed / self.total) * 40
                        )
                        self.tracker.update_stage(
                            "contentExtraction",
                            "processing",
                            progress_percentage,
                            f"Writing ontology: {self.processed}/{self.total} content records",
                        )

                def update(self, task, **kwargs):
                    self.rich_progress.update(self.rich_task, **kwargs)

            # Use the progress wrapper for TTL writing
            progress_wrapper = ProgressWrapper(progress, ttl_task, tracker)

            write_ttl_with_progress(
                content_records,
                add_content_triples_for_ttl,
                g,
                ttl_path,
                progress_wrapper,
                ttl_task,
                context.ontology,
                input_dir,
                processed_repos,
                context,
            )
        console.print(
            f"[bold green]Content extraction complete:[/bold green] {len(file_records)} files processed"
        )
        console.print(
            f"[bold green]Ontology updated and saved to:[/bold green] [cyan]{ttl_path}[/cyan]"
        )
        framework_registry.log_registered_frameworks()
        software_package_registry.log_registered_packages()
        content_registry.log_registered_contents()
    except Exception as e:
        logger.error(f"Fatal error in content extraction: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    main()
