import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import pytest
from unittest.mock import MagicMock, patch
from rdflib import URIRef
from app.ontology.base import BaseOntology

@patch("app.ontology.base.Graph")
def test_get_class_uri(mock_graph_cls):
    mock_graph = MagicMock()
    mock_graph_cls.return_value = mock_graph
    # Simulate OWL.Class subjects
    mock_graph.subjects.return_value = iter([URIRef("http://example.org/ClassA")])
    mock_graph.value.return_value = "ClassA"
    ont = BaseOntology()
    uri = ont.get_class_uri("ClassA")
    assert uri == URIRef("http://example.org/ClassA")

@patch("app.ontology.base.Graph")
def test_get_property_uri(mock_graph_cls):
    mock_graph = MagicMock()
    mock_graph_cls.return_value = mock_graph
    # Simulate OWL.ObjectProperty subjects
    mock_graph.subjects.side_effect = [iter([URIRef("http://example.org/propA")]), iter([])]
    mock_graph.value.return_value = "propA"
    ont = BaseOntology()
    uri = ont.get_property_uri("propA")
    assert uri == URIRef("http://example.org/propA")

@patch("app.ontology.base.Graph")
def test_get_superclass_chain(mock_graph_cls):
    mock_graph = MagicMock()
    mock_graph_cls.return_value = mock_graph
    # Simulate a chain: ClassA -> ClassB -> ClassC
    def value_side_effect(current, pred):
        if str(current) == "http://example.org/ClassA":
            return URIRef("http://example.org/ClassB")
        if str(current) == "http://example.org/ClassB":
            return URIRef("http://example.org/ClassC")
        return None
    mock_graph.value.side_effect = value_side_effect
    ont = BaseOntology()
    chain = ont.get_superclass_chain("http://example.org/ClassA")
    assert chain == ["http://example.org/ClassB", "http://example.org/ClassC"]

@patch("app.ontology.base.Graph")
def test_get_all_classes_and_properties(mock_graph_cls):
    mock_graph = MagicMock()
    mock_graph_cls.return_value = mock_graph
    mock_graph.subjects.side_effect = [iter([URIRef("http://example.org/ClassA")]), iter([URIRef("http://example.org/propA")]), iter([URIRef("http://example.org/propB")])]
    ont = BaseOntology()
    classes = ont.get_all_classes()
    props = ont.get_all_properties()
    assert "http://example.org/ClassA" in classes
    assert "http://example.org/propA" in props or "http://example.org/propB" in props

@patch("app.ontology.base.Graph")
def test_get_subclasses(mock_graph_cls):
    mock_graph = MagicMock()
    mock_graph_cls.return_value = mock_graph
    # Simulate subclass relationships
    mock_graph.subjects.return_value = iter([URIRef("http://example.org/SubA")])
    mock_graph.__contains__.return_value = True
    ont = BaseOntology()
    subclasses = ont.get_subclasses("http://example.org/ClassA")
    assert "http://example.org/SubA" in subclasses 