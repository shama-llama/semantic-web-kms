"""Ontology cache utilities for loading and accessing WDO ontology data."""

import json
from typing import Any, Dict, List, Optional, cast

from app.core.paths import get_ontology_cache_path


class OntologyCache:
    """A cache for WDO ontology classes and properties loaded from the JSON file."""

    def __init__(self, cache_path: Optional[str] = None):
        """
        Initialize the ontology cache and load data from a JSON file.

        Args:
            cache_path (Optional[str]): Path to the ontology cache JSON file. If None, uses default path.
        Raises:
            FileNotFoundError: If the cache file does not exist.
            ValueError: If the cache file contains invalid JSON.
        """
        if cache_path is None:
            # Use the function from paths.py to get the ontology cache path
            cache_path = get_ontology_cache_path()

        self.cache_path = cache_path
        self._cache: Dict[str, Any] = {}
        self._load_cache()

    def _load_cache(self):
        """
        Load the ontology cache from JSON file.

        Raises:
            FileNotFoundError: If the cache file does not exist.
            ValueError: If the cache file contains invalid JSON.
        """
        try:
            with open(self.cache_path, "r") as f:
                self._cache = json.load(f)
        except FileNotFoundError:
            raise FileNotFoundError(f"Ontology cache file not found: {self.cache_path}")
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in ontology cache file: {e}")

    @property
    def classes(self) -> List[str]:
        """
        Get all class names from the ontology.

        Returns:
            List[str]: List of class names.
        """
        val = self._cache.get("classes", [])
        return cast(List[str], val if isinstance(val, list) else [])

    @property
    def object_properties(self) -> List[str]:
        """
        Get all object property names from the ontology.

        Returns:
            List[str]: List of object property names.
        """
        val = self._cache.get("object_properties", [])
        return cast(List[str], val if isinstance(val, list) else [])

    @property
    def data_properties(self) -> List[str]:
        """
        Get all data property names from the ontology.

        Returns:
            List[str]: List of data property names.
        """
        val = self._cache.get("data_properties", [])
        return cast(List[str], val if isinstance(val, list) else [])

    @property
    def annotation_properties(self) -> List[str]:
        """
        Get all annotation property names from the ontology.

        Returns:
            List[str]: List of annotation property names.
        """
        val = self._cache.get("annotation_properties", [])
        return cast(List[str], val if isinstance(val, list) else [])

    @property
    def all_properties(self) -> List[str]:
        """
        Get all property names (object, data, and annotation) from the ontology.

        Returns:
            List[str]: List of all property names.
        """
        return (
            self.object_properties + self.data_properties + self.annotation_properties
        )

    def get_property_cache(self, property_names: List[str]) -> Dict[str, Any]:
        """
        Create a property cache for the given property names.

        Args:
            property_names (List[str]): List of property names to include in the cache.
        Returns:
            Dict[str, Any]: Dictionary mapping property names to their ontology objects.
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
        """
        Create a class cache for the given class names.

        Args:
            class_names (List[str]): List of class names to include in the cache.
        Returns:
            Dict[str, Any]: Dictionary mapping class names to their ontology objects.
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
        """
        Validate that the given property names exist in the ontology.

        Args:
            property_names (List[str]): List of property names to validate.
        Returns:
            Dict[str, bool]: Dictionary mapping property names to their validation status (True if exists).
        """
        validation: Dict[str, bool] = {}
        all_props = self.all_properties

        for prop_name in property_names:
            validation[prop_name] = prop_name in all_props

        return validation

    def validate_classes(self, class_names: List[str]) -> Dict[str, bool]:
        """
        Validate that the given class names exist in the ontology.

        Args:
            class_names (List[str]): List of class names to validate.
        Returns:
            Dict[str, bool]: Dictionary mapping class names to their validation status (True if exists).
        """
        validation: Dict[str, bool] = {}

        for class_name in class_names:
            validation[class_name] = class_name in self.classes

        return validation


# Global cache instance
_ontology_cache: Optional[OntologyCache] = None


def get_ontology_cache() -> OntologyCache:
    """
    Get the global ontology cache instance, creating it if necessary.

    Returns:
        OntologyCache: The global ontology cache instance.
    """
    global _ontology_cache
    if _ontology_cache is None:
        _ontology_cache = OntologyCache()
    return _ontology_cache


def get_extraction_properties() -> List[str]:
    """
    Return all object and data properties from the ontology cache.

    Returns:
        List[str]: List of all object and data property names.
    """
    cache = get_ontology_cache()
    return cache.object_properties + cache.data_properties


def get_extraction_classes() -> List[str]:
    """
    Return all classes from the ontology cache.

    Returns:
        List[str]: List of all class names.
    """
    cache = get_ontology_cache()
    return cache.classes
