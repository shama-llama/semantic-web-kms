"""Ontology cache utilities for loading and accessing WDO ontology data."""

import json
from pathlib import Path
from typing import Any, cast

from engine.core.paths import ONTOLOGY_DIR


class OntologyCache:
    """A cache for WDO ontology classes and properties loaded from the JSON file."""

    def __init__(self, cache_path: str | None = None):
        """
        Initialize the ontology cache and load data from a JSON file.

        Args:
            cache_path (Optional[str]): Path to the ontology cache JSON file. If None,
            uses default path.

        Raises:
            FileNotFoundError: If the cache file does not exist.
            ValueError: If the cache file contains invalid JSON.
        """
        if cache_path is None:
            # Use the ontology cache path from paths.py
            cache_path = str(ONTOLOGY_DIR / "ontology_cache.json")

        self.cache_path = cache_path
        self._cache: dict[str, Any] = {}
        self._load_cache()

    def _load_cache(self):
        """
        Load the ontology cache from the JSON file.

        Args:
            cache_path (Optional[str]): Path to the ontology cache JSON file. If None,
            uses default path.

        Raises:
            FileNotFoundError: If the cache file does not exist.
            ValueError: If the cache file contains invalid JSON.
        """
        if not self.cache_path:
            raise FileNotFoundError("Ontology cache path is not set.")
        try:
            with Path(self.cache_path).open() as f:
                self._cache = json.load(f)
        except FileNotFoundError as err:
            raise FileNotFoundError(
                f"Ontology cache file not found: {self.cache_path}"
            ) from err
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in ontology cache file: {e}") from e

    @property
    def classes(self) -> list[str]:
        """
        Get all class names from the ontology.

        Returns:
            List[str]: List of class names.
        """
        val = self._cache.get("classes", [])
        return cast(list[str], val if isinstance(val, list) else [])

    @property
    def object_properties(self) -> list[str]:
        """
        Get all object property names from the ontology.

        Returns:
            List[str]: List of object property names.
        """
        val = self._cache.get("object_properties", [])
        return cast(list[str], val if isinstance(val, list) else [])

    @property
    def data_properties(self) -> list[str]:
        """
        Get all data property names from the ontology.

        Returns:
            List[str]: List of data property names.
        """
        val = self._cache.get("data_properties", [])
        return cast(list[str], val if isinstance(val, list) else [])

    @property
    def annotation_properties(self) -> list[str]:
        """
        Get all annotation property names from the ontology.

        Returns:
            List[str]: List of annotation property names.
        """
        val = self._cache.get("annotation_properties", [])
        return cast(list[str], val if isinstance(val, list) else [])

    @property
    def all_properties(self) -> list[str]:
        """
        Get all property names (object, data, and annotation) from the ontology.

        Returns:
            List[str]: List of all property names.
        """
        return (
            self.object_properties + self.data_properties + self.annotation_properties
        )

    def _build_cache(
        self, names: list[str], valid_names: list[str], get_obj_func
    ) -> dict[str, Any]:
        """
        Build a cache dictionary for the given names using the provided getter function.

        Args:
            names (list[str]): Names to include in the cache.
            valid_names (list[str]): Valid names to check against.
            get_obj_func (Callable): Function to get the object for a name.

        Returns:
            dict[str, Any]: Dictionary mapping names to their objects.
        """
        cache: dict[str, Any] = {}
        for name in names:
            if name in valid_names:
                cache[name] = get_obj_func(name)
        return cache

    def _validate_names(
        self, names: list[str], valid_names: list[str]
    ) -> dict[str, bool]:
        """
        Validate if the given names exist in the valid_names list.

        Args:
            names (list[str]): Names to validate.
            valid_names (list[str]): List of valid names.

        Returns:
            dict[str, bool]: Dictionary mapping names to their validation status.
        """
        return {name: name in valid_names for name in names}

    def get_property_cache(self, property_names: list[str]) -> dict[str, Any]:
        """
        Create a property cache for the given property names.

        Args:
            property_names (List[str]): List of property names to include in the cache.

        Returns:
            Dict[str, Any]: Dictionary mapping property names to their ontology objects.
        """
        from engine.ontology.wdo import WDOOntology

        ontology = WDOOntology()
        return self._build_cache(
            property_names, self.all_properties, ontology.get_property
        )

    def get_class_cache(self, class_names: list[str]) -> dict[str, Any]:
        """
        Create a class cache for the given class names.

        Args:
            class_names (List[str]): List of class names to include in the cache.

        Returns:
            Dict[str, Any]: Dictionary mapping class names to their ontology objects.
        """
        from engine.ontology.wdo import WDOOntology

        ontology = WDOOntology()
        return self._build_cache(class_names, self.classes, ontology.get_class)

    def validate_properties(self, properties: list[str]) -> dict[str, bool]:
        """
        Validate if the given properties exist in the ontology cache.

        Args:
            properties (list[str]): List of property names to validate.

        Returns:
            Dict[str, bool]: Dictionary mapping property names to their validation
            status (True if exists).
        """
        return self._validate_names(properties, self.all_properties)

    def validate_classes(self, classes: list[str]) -> dict[str, bool]:
        """
        Validate if the given classes exist in the ontology cache.

        Args:
            classes (list[str]): List of class names to validate.

        Returns:
            Dict[str, bool]: Dictionary mapping class names to their validation status
            (True if exists).
        """
        return self._validate_names(classes, self.classes)


# Global cache instance
_ontology_cache: OntologyCache | None = None


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


def get_extraction_properties() -> list[str]:
    """
    Return all object and data properties from the ontology cache.

    Returns:
        List[str]: List of all object and data property names.
    """
    cache = get_ontology_cache()
    return cache.object_properties + cache.data_properties


def get_extraction_classes() -> list[str]:
    """
    Return all classes from the ontology cache.

    Returns:
        List[str]: List of all class names.
    """
    cache = get_ontology_cache()
    return cache.classes
