import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import pytest
import json
from unittest.mock import patch, mock_open
from app.core.ontology_cache import OntologyCache

def fake_cache():
    return json.dumps({
        "classes": ["ClassA", "ClassB"],
        "object_properties": ["prop1"],
        "data_properties": ["prop2"],
        "annotation_properties": ["prop3"]
    })

@patch("builtins.open", new_callable=mock_open, read_data=fake_cache())
@patch("os.path.join", return_value="fake_path.json")
def test_ontology_cache_load(mock_join, mock_file):
    cache = OntologyCache("fake_path.json")
    assert "ClassA" in cache.classes
    assert "prop1" in cache.object_properties
    assert "prop2" in cache.data_properties
    assert "prop3" in cache.annotation_properties
    assert set(cache.all_properties) == {"prop1", "prop2", "prop3"}

@patch("builtins.open", new_callable=mock_open, read_data=fake_cache())
@patch("os.path.join", return_value="fake_path.json")
def test_ontology_cache_validation(mock_join, mock_file):
    cache = OntologyCache("fake_path.json")
    result = cache.validate_classes(["ClassA", "ClassX"])
    assert result["ClassA"] is True
    assert result["ClassX"] is False
    result2 = cache.validate_properties(["prop1", "propX"])
    assert result2["prop1"] is True
    assert result2["propX"] is False 