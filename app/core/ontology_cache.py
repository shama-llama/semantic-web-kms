import json
import os
from typing import Any, Dict, List, Optional, cast

from app.core.paths import get_web_dev_ontology_path


class OntologyCache:
    """A cache for WDO ontology classes and properties loaded from the JSON file."""

    def __init__(self, cache_path: Optional[str] = None):
        """Initialize the ontology cache.

        Args:
            cache_path: Path to the ontology cache JSON file. If None, uses default path.
        """
        if cache_path is None:
            # Get the ontology path and construct cache path
            ontology_path = get_web_dev_ontology_path()
            cache_path = os.path.join(
                os.path.dirname(ontology_path), "ontology_cache.json"
            )

        self.cache_path = cache_path
        self._cache: Dict[str, Any] = {}
        self._load_cache()

    def _load_cache(self):
        """Load the ontology cache from JSON file."""
        try:
            with open(self.cache_path, "r") as f:
                self._cache = json.load(f)
        except FileNotFoundError:
            raise FileNotFoundError(f"Ontology cache file not found: {self.cache_path}")
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in ontology cache file: {e}")

    @property
    def classes(self) -> List[str]:
        """Get all class names from the ontology."""
        val = self._cache.get("classes", [])
        return cast(List[str], val if isinstance(val, list) else [])

    @property
    def object_properties(self) -> List[str]:
        """Get all object property names from the ontology."""
        val = self._cache.get("object_properties", [])
        return cast(List[str], val if isinstance(val, list) else [])

    @property
    def data_properties(self) -> List[str]:
        """Get all data property names from the ontology."""
        val = self._cache.get("data_properties", [])
        return cast(List[str], val if isinstance(val, list) else [])

    @property
    def annotation_properties(self) -> List[str]:
        """Get all annotation property names from the ontology."""
        val = self._cache.get("annotation_properties", [])
        return cast(List[str], val if isinstance(val, list) else [])

    @property
    def all_properties(self) -> List[str]:
        """Get all property names (object, data, and annotation) from the ontology."""
        return (
            self.object_properties + self.data_properties + self.annotation_properties
        )

    def get_property_cache(self, property_names: List[str]) -> Dict[str, Any]:
        """Create a property cache for the given property names.

        Args:
            property_names: List of property names to include in the cache

        Returns:
            Dictionary mapping property names to their ontology objects
        """
        from app.ontology.wdo import WDOOntology

        ontology = WDOOntology()
        cache: Dict[str, Any] = {}

        for prop_name in property_names:
            if prop_name in self.all_properties:
                prop_obj = ontology.get_property(prop_name)
                cache[prop_name] = prop_obj

        return cache

    def get_class_cache(self, class_names: List[str]) -> Dict[str, Any]:
        """Create a class cache for the given class names.

        Args:
            class_names: List of class names to include in the cache

        Returns:
            Dictionary mapping class names to their ontology objects
        """
        from app.ontology.wdo import WDOOntology

        ontology = WDOOntology()
        cache: Dict[str, Any] = {}

        for class_name in class_names:
            if class_name in self.classes:
                class_obj = ontology.get_class(class_name)
                cache[class_name] = class_obj

        return cache

    def validate_properties(self, property_names: List[str]) -> Dict[str, bool]:
        """Validate that the given property names exist in the ontology.

        Args:
            property_names: List of property names to validate

        Returns:
            Dictionary mapping property names to their validation status
        """
        validation: Dict[str, bool] = {}
        all_props = self.all_properties

        for prop_name in property_names:
            validation[prop_name] = prop_name in all_props

        return validation

    def validate_classes(self, class_names: List[str]) -> Dict[str, bool]:
        """Validate that the given class names exist in the ontology.

        Args:
            class_names: List of class names to validate

        Returns:
            Dictionary mapping class names to their validation status
        """
        validation: Dict[str, bool] = {}

        for class_name in class_names:
            validation[class_name] = class_name in self.classes

        return validation


# Global cache instance
_ontology_cache: Optional[OntologyCache] = None


def get_ontology_cache() -> OntologyCache:
    """Get the global ontology cache instance.

    Returns:
        OntologyCache instance
    """
    global _ontology_cache
    if _ontology_cache is None:
        _ontology_cache = OntologyCache()
    return _ontology_cache


def get_code_extraction_properties() -> List[str]:
    """Get the list of properties used by the code extractor."""
    return [
        # Object Properties
        "declaresCode",
        "hasMethod",
        "hasField",
        "hasParameter",
        "hasArgument",
        "hasReturnType",
        "hasType",
        "callsFunction",
        "invokes",
        "accesses",
        "extendsType",
        "implementsInterface",
        "imports",
        "isMethodOf",
        "hasDocumentComponent",
        "isElementOf",
        "bearerOfInformation",
        "informationBorneBy",
        # Data Properties
        "hasSourceCodeSnippet",
        "hasSimpleName",
        "hasCanonicalName",
        "hasLineCount",
        "startsAtLine",
        "endsAtLine",
        "hasCyclomaticComplexity",
        "isAsynchronous",
        "hasAccessModifier",
        "hasContent",
        "hasTextValue",
    ]


def get_code_extraction_classes() -> List[str]:
    """Get the list of classes used by the code extractor."""
    return [
        "ClassDefinition",
        "FunctionDefinition",
        "AttributeDeclaration",
        "Parameter",
        "VariableDeclaration",
        "FunctionCallSite",
        "ImportDeclaration",
        "CodeComment",
        "Type",
        "ComplexType",
        "PrimitiveType",
        "InterfaceDefinition",
        "EnumDefinition",
        "StructDefinition",
        "SourceCodeFile",
        "SoftwareCode",
        "InformationContentEntity",
        "DigitalInformationCarrier",
    ]


def get_file_extraction_properties() -> List[str]:
    """Get the list of properties used by the file extractor."""
    return [
        # Object Properties
        "hasRelativePath",
        "hasExtension",
        "hasSimpleName",
        "bearerOfInformation",
        "informationBorneBy",
        "hasDocumentComponent",
        "hasContent",
        "hasSizeInBytes",
        "hasCategory",
        "hasCanonicalName",
        "hasLineCount",
        "hasType",
        "hasField",
        "hasMethod",
        "hasParameter",
        "hasProjectOutput",
        "hasRepository",
        "hasReturnType",
        "hasSoftwareLicense",
        "hasSpecificLicense",
        "hasArgument",
        "hasCommit",
        "hasTextValue",
        "isElementOf",
        "startsAtLine",
        "endsAtLine",
        "hasResource",
        "modifies",
        "isAbout",
        # Data Properties
        "hasCreationTimestamp",
        "hasModificationTimestamp",
    ]


def get_git_extraction_properties() -> List[str]:
    """Get the list of properties used by the git extractor."""
    return [
        # Object Properties
        "hasCommit",
        "modifies",
        "isAbout",
        "hasSimpleName",
        "hasRepository",
        "hasCommitMessage",
        # Data Properties
        "hasCommitHash",
        "hasContent",
    ]


def get_git_extraction_classes() -> List[str]:
    """Get the list of classes used by the git extractor."""
    return [
        "Repository",
        "Commit",
        "InformationContentEntity",
        "DigitalInformationCarrier",
    ]


def get_doc_extraction_properties() -> List[str]:
    """Get the list of properties used by the doc extractor."""
    return [
        # Object Properties
        "hasRelativePath",
        "hasExtension",
        "hasSimpleName",
        "bearerOfInformation",
        "informationBorneBy",
        "hasDocumentComponent",
        "isElementOf",
        # Data Properties
        "hasContent",
        "hasTextValue",
        "startsAtLine",
        "endsAtLine",
    ]
