from unittest.mock import MagicMock, patch

import pytest
from rdflib import URIRef

from app.extraction.ontology.ontology_lookup import CommonOntology


@patch(
    "app.extraction.ontology.ontology_lookup.BaseOntology.__init__", return_value=None
)
def test_common_ontology_init_and_available_classes(mock_base_init, tmp_path):
    # Test with cache file
    cache_path = tmp_path / "cache.json"
    cache_path.write_text('{"classes": ["A", "B"]}')
    ont = CommonOntology("ontology.owl", str(cache_path))
    assert ont.available_classes == {"A", "B"}
    # Test without cache file
    ont2 = CommonOntology("ontology.owl")
    assert ont2.available_classes == set()


@patch(
    "app.extraction.ontology.ontology_lookup.BaseOntology.__init__", return_value=None
)
def test_get_class_and_property_success(mock_base_init):
    ont = CommonOntology("ontology.owl")
    ont.get_class_uri = MagicMock(return_value=URIRef("http://example.org/Class"))
    ont.get_property_uri = MagicMock(return_value=URIRef("http://example.org/prop"))
    assert isinstance(ont.get_class("Class"), URIRef)
    assert isinstance(ont.get_property("prop"), URIRef)


@patch(
    "app.extraction.ontology.ontology_lookup.BaseOntology.__init__", return_value=None
)
def test_get_class_and_property_failure(mock_base_init):
    ont = CommonOntology("ontology.owl")
    ont.get_class_uri = MagicMock(return_value=None)
    ont.get_property_uri = MagicMock(return_value=None)
    with pytest.raises(KeyError):
        ont.get_class("MissingClass")
    with pytest.raises(KeyError):
        ont.get_property("MissingProp")
