import json
import tempfile
from typing import Any, Dict, List
from unittest.mock import patch

import pytest

from app.core.ontology_cache import (
    OntologyCache,
    get_ontology_cache,
    get_extraction_properties,
    get_extraction_classes,
)

# Minimal mock ontology cache data
MOCK_CACHE = {
    "classes": ["ClassA", "ClassB"],
    "object_properties": ["objProp1"],
    "data_properties": ["dataProp1"],
    "annotation_properties": ["annProp1"],
}

class DummyWDOOntology:
    def get_property(self, name):
        return f"Property:{name}"
    def get_class(self, name):
        return f"Class:{name}"

@patch("app.ontology.wdo.WDOOntology", DummyWDOOntology)
def test_load_cache_and_accessors(tmp_path):
    """Test OntologyCache loads cache and exposes properties correctly."""
    cache_path = tmp_path / "ontology_cache.json"
    cache_path.write_text(json.dumps(MOCK_CACHE))
    cache = OntologyCache(str(cache_path))
    assert cache.classes == ["ClassA", "ClassB"]
    assert cache.object_properties == ["objProp1"]
    assert cache.data_properties == ["dataProp1"]
    assert cache.annotation_properties == ["annProp1"]
    assert cache.all_properties == ["objProp1", "dataProp1", "annProp1"]

@patch("app.ontology.wdo.WDOOntology", DummyWDOOntology)
def test_get_property_cache_and_class_cache(tmp_path):
    """Test get_property_cache and get_class_cache methods."""
    cache_path = tmp_path / "ontology_cache.json"
    cache_path.write_text(json.dumps(MOCK_CACHE))
    cache = OntologyCache(str(cache_path))
    prop_cache = cache.get_property_cache(["objProp1", "notAProp"])
    assert prop_cache == {"objProp1": "Property:objProp1"}
    class_cache = cache.get_class_cache(["ClassA", "notAClass"])
    assert class_cache == {"ClassA": "Class:ClassA"}

@patch("app.ontology.wdo.WDOOntology", DummyWDOOntology)
def test_validate_properties_and_classes(tmp_path):
    """Test validate_properties and validate_classes methods."""
    cache_path = tmp_path / "ontology_cache.json"
    cache_path.write_text(json.dumps(MOCK_CACHE))
    cache = OntologyCache(str(cache_path))
    prop_result = cache.validate_properties(["objProp1", "foo"])
    assert prop_result == {"objProp1": True, "foo": False}
    class_result = cache.validate_classes(["ClassA", "bar"])
    assert class_result == {"ClassA": True, "bar": False}

@patch("app.ontology.wdo.WDOOntology", DummyWDOOntology)
def test_global_cache_and_extraction_functions(tmp_path, monkeypatch):
    """Test get_ontology_cache, get_extraction_properties, and get_extraction_classes."""
    cache_path = tmp_path / "ontology_cache.json"
    cache_path.write_text(json.dumps(MOCK_CACHE))
    # Patch the default path function to use our temp file
    monkeypatch.setattr("app.core.paths.get_ontology_cache_path", lambda: str(cache_path))
    # Clear global cache using monkeypatch
    monkeypatch.setattr("app.core.ontology_cache._ontology_cache", None)
    # Reload the ontology_cache module to ensure monkeypatch is in effect
    import importlib
    import app.core.ontology_cache as oc_mod
    importlib.reload(oc_mod)
    # Import after monkeypatching and reload
    get_ontology_cache = oc_mod.get_ontology_cache
    get_extraction_properties = oc_mod.get_extraction_properties
    get_extraction_classes = oc_mod.get_extraction_classes
    cache = get_ontology_cache()
    assert cache.classes == ["ClassA", "ClassB"]
    assert get_extraction_properties() == ["objProp1", "dataProp1"]
    assert get_extraction_classes() == ["ClassA", "ClassB"]

@patch("app.ontology.wdo.WDOOntology", DummyWDOOntology)
def test_load_cache_file_not_found(tmp_path):
    """Test OntologyCache raises FileNotFoundError if file is missing."""
    missing_path = tmp_path / "missing.json"
    with pytest.raises(FileNotFoundError):
        OntologyCache(str(missing_path))

@patch("app.ontology.wdo.WDOOntology", DummyWDOOntology)
def test_load_cache_invalid_json(tmp_path):
    """Test OntologyCache raises ValueError if JSON is invalid."""
    bad_path = tmp_path / "bad.json"
    bad_path.write_text("not a json")
    with pytest.raises(ValueError):
        OntologyCache(str(bad_path)) 