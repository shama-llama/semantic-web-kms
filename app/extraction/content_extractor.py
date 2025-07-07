"""
Content extraction and ontology population for the Semantic Web KMS system.

For automating the creation of Information Content Entities as defined in the WDO.
"""

import json
import logging
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import OWL, RDF, RDFS, SKOS, XSD
from rich.console import Console
from rich.progress import BarColumn, Progress, TextColumn, TimeElapsedColumn

try:
    from PIL import Image

    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

from app.core.paths import (
    get_content_types_path,
    get_input_path,
    get_output_path,
    get_web_dev_ontology_path,
    uri_safe_string,
)
from app.extraction.classification_utils import (
    classify_file,
    load_classifiers_from_json,
)
from app.extraction.file_utils import (
    FileRecord,
    build_file_records,
    count_total_files,
    get_repo_dirs,
)
from app.extraction.rdf_utils import (
    add_repository_metadata,
    write_ttl_with_progress,
)

logger = logging.getLogger("content_extractor")

WDO = Namespace("http://semantic-web-kms.edu.et/wdo#")
INST = Namespace("http://semantic-web-kms.edu.et/wdo/instances/")


class FrameworkRegistry:
    """Registry to manage unique framework URIs across the entire extraction process."""

    def __init__(self):
        """Initialize the framework registry with an empty dictionary."""
        self._framework_uris: Dict[str, URIRef] = {}

    def get_or_create_framework_uri(self, framework_name: str) -> URIRef:
        """
        Get existing framework URI or create a new one if it doesn't exist.

        Args:
            framework_name: The name of the software framework

        Returns:
            URIRef: The URI for the framework (either existing or newly created)
        """
        if framework_name not in self._framework_uris:
            # Create a new URI for this framework
            safe_name = uri_safe_string(framework_name)
            framework_uri = INST[f"framework_{safe_name}"]
            self._framework_uris[framework_name] = framework_uri
        else:
            pass

        return self._framework_uris[framework_name]

    def get_registered_frameworks(self) -> Dict[str, URIRef]:
        """Get all registered frameworks and their URIs."""
        return self._framework_uris.copy()

    def get_framework_count(self) -> int:
        """Get the total number of unique frameworks registered."""
        return len(self._framework_uris)

    def reset(self) -> None:
        """Reset the framework registry to empty state."""
        self._framework_uris.clear()

    def log_registered_frameworks(self) -> None:
        """Log all registered frameworks for debugging."""
        if self._framework_uris:
            logger.info(f"Registered frameworks ({len(self._framework_uris)}):")
            for name, uri in self._framework_uris.items():
                logger.info(f"  {name} -> {uri}")
        else:
            logger.info("No frameworks registered")


# Global framework registry instance
framework_registry = FrameworkRegistry()


class OntologyWrapper:
    """Ontology wrapper that loads classes from JSON configuration files."""

    def __init__(self, ontology_path: str):
        """Initialize by loading classes from JSON configuration files."""
        self.graph = Graph()
        self._load_classes_from_json(ontology_path)

    def _load_classes_from_json(self, ontology_path: str) -> None:
        """Load classes from JSON configuration files instead of hardcoded lists."""
        if not os.path.exists(ontology_path):
            return

        # Parse the ontology file
        temp_graph = Graph()
        temp_graph.parse(ontology_path, format="xml")

        # Load ontology cache for validation
        cache_path = os.path.join(os.path.dirname(ontology_path), "ontology_cache.json")
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
        carrier_types_path = os.path.join(
            os.path.dirname(content_types_path), "carrier_types.json"
        )
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
        """Find a class URI by name (label or local part)."""
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
        """Find a property URI by name (label or local part)."""
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
        """Return the URI for a class by name, or raise KeyError if not found."""
        uri = self._find_class_by_name(self.graph, class_name)
        if uri:
            return uri
        raise KeyError(f"Class '{class_name}' not found in ontology.")

    def get_superclass_chain(self, class_uri: str) -> List[str]:
        """Return the full superclass chain for a class URI, up to the root."""
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

    Used for code metrics in the ontology.
    """
    try:
        with open(abs_path, "r", encoding="utf-8", errors="ignore") as f:
            return sum(1 for _ in f)
    except Exception:
        return 0


@dataclass
class ExtractionContext:
    """Context object for passing extraction configuration and classifiers to helper functions."""

    extractor: Any
    content_classifiers: List[Tuple[str, re.Pattern]]
    content_ignore_patterns: List[re.Pattern]


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

    Handles content-specific properties, programming language, asset metadata, and relationships.
    """
    content_uri = INST[f"content_{repo_enc}_{path_enc}"]
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
        language_name = class_name.replace("Code", "")
        g.add(
            (
                content_uri,
                WDO.programmingLanguage,
                Literal(language_name, datatype=XSD.string),
            )
        )
    if class_name in ["ConfigurationSetting", "CommitMessage", "Log"]:
        try:
            with open(record.abs_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read(1000)
            g.add((content_uri, WDO.hasContent, Literal(content, datatype=XSD.string)))
        except Exception:
            pass
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
    """
    content_class, content_class_uri, _ = classify_file(
        record.filename,
        context.content_classifiers,
        context.content_ignore_patterns,
        context.extractor.ontology,
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
    path_enc = uri_safe_string(path_clean)
    file_uri = INST[f"file_{repo_enc}_{path_enc}"]
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
    """Extract metadata from image files using PIL."""
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
        pass

    return metadata


def extract_media_metadata(file_path: str, file_type: str) -> Dict[str, Any]:
    """Extract basic metadata from media files."""
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
        pass

    return metadata


def add_asset_metadata_triples(
    g: Graph, content_uri: URIRef, file_path: str, class_name: str
):
    """
    Add asset-specific metadata triples based on file type, strictly following ontology domain/range.

    Responsible for extracting and adding metadata for images, video, audio, and fonts.
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
    """Extract dependencies from build files with version information."""
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
        pass

    return dependencies


def extract_frameworks_from_code_file(
    file_path: str, file_type: str
) -> List[Dict[str, str]]:
    """Extract frameworks from code files based on imports and patterns with version info."""
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
        pass

    return frameworks


def add_dependency_and_framework_triples(
    g: Graph, content_uri: URIRef, file_path: str, class_name: str
):
    """
    Add dependency and framework triples based on file type, strictly following ontology domain/range.

    Dependencies and frameworks are only added where allowed by the ontology.
    """
    # Only BuildScript or SoftwarePackage can specify dependencies
    if class_name == "BuildScript":
        dependencies = extract_dependencies_from_build_file(file_path, class_name)
        for dep in dependencies:
            dep_uri = URIRef(f"{content_uri}_dep_{uri_safe_string(dep['name'])}")
            g.add((dep_uri, RDF.type, WDO.SoftwarePackage))
            g.add(
                (dep_uri, WDO.hasSimpleName, Literal(dep["name"], datatype=XSD.string))
            )
            g.add((dep_uri, RDFS.label, Literal(dep["name"], datatype=XSD.string)))
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
            if not (framework_uri, RDF.type, WDO.SoftwareFramework) in g:
                g.add((framework_uri, RDF.type, WDO.SoftwareFramework))
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
    """Extract the base image from a Dockerfile."""
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
        pass
    return ""


def extract_license_identifier(file_path: str) -> str:
    """Extract SPDX license identifier from a license file (best effort)."""
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
        pass
    return ""


def add_special_content_triples(
    g: Graph, content_uri: URIRef, file_path: str, class_name: str
):
    """Add special triples for Dockerfile base image and License identifier."""
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


def main():
    """
    Run content extraction.

    Loads configuration, scans repositories, classifies files, and writes RDF triples to output.
    """
    ontology_path = get_web_dev_ontology_path()
    input_dir = get_input_path("")
    console = Console()
    excluded_dirs_path = os.path.join(
        os.path.dirname(__file__), "../../model/excluded_directories.json"
    )
    with open(excluded_dirs_path, "r") as f:
        excluded_dirs = set(json.load(f))
    logger.info(
        "Starting content extraction process (ontology load, mapping, file scan, and RDF output)..."
    )
    repo_dirs = get_repo_dirs(input_dir, excluded_dirs)
    total_files = count_total_files(repo_dirs, input_dir, excluded_dirs)
    content_type_path = get_content_types_path()
    content_classifiers, content_ignore_patterns = load_classifiers_from_json(
        content_type_path
    )
    # Use the data-driven ontology wrapper instead of loading the full ontology
    extractor = type("Extractor", (), {"ontology": OntologyWrapper(ontology_path)})
    ttl_path = get_output_path("web_development_ontology.ttl")
    with Progress(
        TextColumn("[bold blue]{task.description}"),
        BarColumn(),
        "[progress.percentage]{task.percentage:>3.0f}%",
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        extract_task = progress.add_task(
            "[blue]Extracting contents...", total=total_files
        )
        file_records = build_file_records(
            repo_dirs, input_dir, excluded_dirs, progress, extract_task
        )
        logger.info(
            f"Content extraction: {len(file_records)} files found in {len(repo_dirs)} repositories"
        )
        ttl_task = progress.add_task("[blue]Writing TTL...", total=len(file_records))
        g = Graph()
        if os.path.exists(ttl_path):
            g.parse(ttl_path, format="turtle")
        g.bind("wdo", WDO)
        g.bind("inst", INST)
        g.bind("skos", SKOS)
        processed_repos: set[str] = set()
        write_ttl_with_progress(
            file_records,
            lambda g, r, *a, **kw: add_content_only_triples(
                g,
                r,
                ExtractionContext(
                    extractor, content_classifiers, content_ignore_patterns
                ),
                input_dir,
                processed_repos,
            ),
            g,
            ttl_path,
            progress,
            ttl_task,
        )
    console.print(
        f"[bold green]Content extraction complete:[/bold green] {len(file_records)} files processed"
    )
    console.print(
        f"[bold green]Ontology updated and saved to:[/bold green] [cyan]{ttl_path}[/cyan]"
    )
    # Log registered frameworks for debugging
    framework_registry.log_registered_frameworks()


if __name__ == "__main__":
    main()
