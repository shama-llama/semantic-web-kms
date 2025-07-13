import json
import os
import tempfile
from unittest.mock import MagicMock, patch

import pytest

from app.utils import generate_ontology_cache as gen_cache


def mock_get_all_classes() -> list[str]:
    return [
        "http://example.org/ontology#ValidClass",
        "http://example.org/ontology#Nabcdef0123456789abcdef0123456789",  # hash-like
        "http://example.org/ontology#AnotherClass",
    ]


def mock_subjects(predicate=None, object=None):
    # Simulate rdflib's .subjects() generator
    if object == "ObjectProperty":
        return iter(["http://example.org/ontology#relatesTo"])
    if object == "DatatypeProperty":
        return iter(["http://example.org/ontology#hasValue"])
    if object == "AnnotationProperty":
        return iter(["http://example.org/ontology#label"])
    return iter([])


@patch("app.utils.generate_ontology_cache.WDOOntology")
@patch("app.utils.generate_ontology_cache.get_web_dev_ontology_path")
def test_main_creates_expected_cache(mock_get_path, mock_wdo):
    """Test that main() creates a cache file with the expected structure."""
    with tempfile.TemporaryDirectory() as tmpdir:
        fake_onto_path = os.path.join(tmpdir, "wdo.owl")
        fake_cache_path = os.path.join(tmpdir, "ontology_cache.json")
        mock_get_path.return_value = fake_onto_path
        # Patch constants in the module
        gen_cache.ONTOLOGY_PATH = fake_onto_path
        gen_cache.CACHE_PATH = fake_cache_path
        # Mock WDOOntology instance
        mock_instance = MagicMock()
        mock_instance.get_all_classes.side_effect = mock_get_all_classes
        # Patch .graph.subjects to our mock_subjects
        mock_instance.graph.subjects.side_effect = lambda predicate=None, object=None: (
            mock_subjects(predicate, getattr(object, "__name__", object))
        )
        mock_wdo.return_value = mock_instance

        # Patch rdflib.namespace.OWL to provide .ObjectProperty, etc.
        class DummyOWL:
            ObjectProperty = "ObjectProperty"
            DatatypeProperty = "DatatypeProperty"
            AnnotationProperty = "AnnotationProperty"

        with patch("rdflib.namespace.OWL", DummyOWL):
            gen_cache.main()
        # Check file exists and structure
        assert os.path.exists(fake_cache_path)
        with open(fake_cache_path) as f:
            data = json.load(f)
        assert set(data.keys()) == {
            "classes",
            "object_properties",
            "data_properties",
            "annotation_properties",
        }
        # Only valid classes should be present
        assert data["classes"] == ["AnotherClass", "ValidClass"]
        assert data["object_properties"] == ["relatesTo"]
        assert data["data_properties"] == ["hasValue"]
        assert data["annotation_properties"] == ["label"]
