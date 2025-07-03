import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import pytest
from unittest.mock import MagicMock, patch
from rdflib import URIRef
from app.ontology.bfo import BFOOntology

@patch("app.ontology.bfo.Graph")
def test_is_bfo_class(mock_graph_cls):
    bfo = BFOOntology(owl_path="fake.owl")
    assert bfo.is_bfo_class("http://purl.obolibrary.org/obo/BFO_0000001")
    assert not bfo.is_bfo_class("http://example.org/Other")

@patch("app.ontology.bfo.Graph")
def test_get_label(mock_graph_cls):
    mock_graph = MagicMock()
    mock_graph_cls.return_value = mock_graph
    mock_graph.value.return_value = "Entity Label"
    bfo = BFOOntology(owl_path="fake.owl")
    label = bfo.get_label("http://purl.obolibrary.org/obo/BFO_0000001")
    assert label == "Entity Label"

@patch("app.ontology.bfo.Graph")
def test_get_top_level_classes(mock_graph_cls):
    mock_graph = MagicMock()
    mock_graph_cls.return_value = mock_graph
    # Simulate one top-level class
    mock_graph.subjects.return_value = iter([URIRef("http://purl.obolibrary.org/obo/BFO_0000002")])
    mock_graph.__contains__.return_value = True
    bfo = BFOOntology(owl_path="fake.owl")
    with patch.object(bfo, "get_label", return_value="Top Level"):
        top = bfo.get_top_level_classes()
        assert ("http://purl.obolibrary.org/obo/BFO_0000002", "Top Level") in top 