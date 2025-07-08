import os
import tempfile
from typing import Any

import pytest
from rdflib import Namespace, URIRef

from app.core.graph_manager import GraphManager

class DummyOntology:
    """A minimal ontology mock with namespaces for testing."""
    namespaces = {
        "ex": Namespace("http://example.org/")
    }

def test_add_triple_and_stats():
    """Test adding a triple and retrieving graph statistics."""
    ontology = DummyOntology()
    gm = GraphManager(ontology)
    s = URIRef("http://example.org/subject")
    p = URIRef("http://example.org/predicate")
    o = URIRef("http://example.org/object")
    gm.add_triple(s, p, o)
    stats = gm.stats()
    assert stats["total_triples"] == 1
    assert stats["subjects"] == 1
    assert stats["predicates"] == 1
    assert stats["objects"] == 1

def test_serialize(tmp_path):
    """Test serializing the graph to a Turtle file."""
    ontology = DummyOntology()
    gm = GraphManager(ontology)
    s = URIRef("http://example.org/subject")
    p = URIRef("http://example.org/predicate")
    o = URIRef("http://example.org/object")
    gm.add_triple(s, p, o)
    out_path = tmp_path / "graph.ttl"
    gm.serialize(str(out_path))
    assert out_path.exists()
    content = out_path.read_text()
    assert "@prefix ex:" in content or "http://example.org/" in content
    assert "subject" in content and "predicate" in content and "object" in content 

def test_empty_graph_stats():
    """Test stats on an empty graph."""
    ontology = DummyOntology()
    gm = GraphManager(ontology)
    stats = gm.stats()
    assert stats["total_triples"] == 0
    assert stats["subjects"] == 0
    assert stats["predicates"] == 0
    assert stats["objects"] == 0


def test_serialize_empty_graph(tmp_path):
    """Test serializing an empty graph."""
    ontology = DummyOntology()
    gm = GraphManager(ontology)
    out_path = tmp_path / "empty_graph.ttl"
    gm.serialize(str(out_path))
    assert out_path.exists()


def test_add_duplicate_triple():
    """Test adding the same triple twice does not increase triple count."""
    ontology = DummyOntology()
    gm = GraphManager(ontology)
    s = URIRef("http://example.org/subject")
    p = URIRef("http://example.org/predicate")
    o = URIRef("http://example.org/object")
    gm.add_triple(s, p, o)
    gm.add_triple(s, p, o)
    stats = gm.stats()
    assert stats["total_triples"] == 1


def test_serialize_invalid_format(tmp_path):
    """Test serializing with an invalid format raises an exception."""
    ontology = DummyOntology()
    gm = GraphManager(ontology)
    out_path = tmp_path / "graph.invalid"
    with pytest.raises(Exception):
        gm.serialize(str(out_path), fmt="invalidformat") 