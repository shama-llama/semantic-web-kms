import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import pytest
from unittest.mock import patch, MagicMock
from app.ontology.wdo import WDOOntology

@patch.object(WDOOntology, "get_class_uri", return_value="http://example.org/ClassA")
def test_get_class_success(mock_get_class_uri):
    wdo = WDOOntology(owl_path=None, bfo_ontology=MagicMock())
    uri = wdo.get_class("ClassA")
    assert uri == "http://example.org/ClassA"

@patch.object(WDOOntology, "get_class_uri", return_value=None)
def test_get_class_not_found(mock_get_class_uri):
    wdo = WDOOntology(owl_path=None, bfo_ontology=MagicMock())
    with pytest.raises(KeyError):
        wdo.get_class("MissingClass")

@patch.object(WDOOntology, "get_property_uri", return_value="http://example.org/propA")
def test_get_property_success(mock_get_property_uri):
    wdo = WDOOntology(owl_path=None, bfo_ontology=MagicMock())
    uri = wdo.get_property("propA")
    assert uri == "http://example.org/propA"

@patch.object(WDOOntology, "get_property_uri", return_value=None)
def test_get_property_not_found(mock_get_property_uri):
    wdo = WDOOntology(owl_path=None, bfo_ontology=MagicMock())
    with pytest.raises(KeyError):
        wdo.get_property("MissingProp")

@patch.object(WDOOntology, "get_superclass_chain", return_value=["http://bfo.org/Top"])
def test_get_top_level_bfo_ancestor_found(mock_chain):
    mock_bfo = MagicMock()
    mock_bfo.is_bfo_class.side_effect = lambda uri: uri == "http://bfo.org/Top"
    wdo = WDOOntology(owl_path=None, bfo_ontology=mock_bfo)
    ancestor = wdo.get_top_level_bfo_ancestor("http://example.org/ClassA")
    assert ancestor == "http://bfo.org/Top"

@patch.object(WDOOntology, "get_superclass_chain", return_value=["http://notbfo.org/Other"])
def test_get_top_level_bfo_ancestor_none(mock_chain):
    mock_bfo = MagicMock()
    mock_bfo.is_bfo_class.return_value = False
    wdo = WDOOntology(owl_path=None, bfo_ontology=mock_bfo)
    ancestor = wdo.get_top_level_bfo_ancestor("http://example.org/ClassA")
    assert ancestor is None 