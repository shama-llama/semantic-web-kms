import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import pytest
from rdflib import URIRef, Literal, RDF, RDFS, Namespace
from app.core.graph_manager import GraphManager

class DummyOntology:
    namespaces = {"ex": Namespace("http://example.org/")}

def test_add_triple_and_stats():
    ontology = DummyOntology()
    gm = GraphManager(ontology)
    s = URIRef("http://example.org/s1")
    p = URIRef("http://example.org/p1")
    o = Literal("value")
    gm.add_triple(s, p, o)
    stats = gm.stats()
    assert stats["total_triples"] == 1
    assert stats["subjects"] == 1
    assert stats["predicates"] == 1
    assert stats["objects"] == 1

def test_get_entity_details():
    ontology = DummyOntology()
    gm = GraphManager(ontology)
    s = URIRef("http://example.org/s2")
    gm.add_triple(s, RDF.type, URIRef("http://semantic-web-kms.edu.et/wdo#TestType"))
    gm.add_triple(s, RDFS.label, Literal("Test Label"))
    gm.add_triple(s, RDFS.comment, Literal("A test entity."))
    details = gm.get_entity_details(str(s))
    assert details["uri"] == str(s)
    assert details["type"] == "TestType"
    assert details["label"] == "Test Label"
    assert details["description"] == "A test entity."

def test_get_entity_details_not_found():
    ontology = DummyOntology()
    gm = GraphManager(ontology)
    details = gm.get_entity_details("http://example.org/unknown")
    assert details["uri"] == "http://example.org/unknown"
    assert details["type"] is None
    assert details["label"] is None
    assert details["description"] is None

def test_get_entity_relationships_not_found():
    ontology = DummyOntology()
    gm = GraphManager(ontology)
    rels = gm.get_entity_relationships("http://example.org/unknown")
    assert rels["incoming"] == []
    assert rels["outgoing"] == []

def test_get_entity_neighborhood_not_found():
    ontology = DummyOntology()
    gm = GraphManager(ontology)
    result = gm.get_entity_neighborhood("http://example.org/unknown")
    assert result["center"] == "http://example.org/unknown"
    assert len(result["nodes"]) == 1
    assert result["nodes"][0]["id"] == "http://example.org/unknown"
    assert result["edges"] == []

def test_get_entity_neighborhood_empty_graph():
    ontology = DummyOntology()
    gm = GraphManager(ontology)
    result = gm.get_entity_neighborhood("http://example.org/empty")
    assert result["center"] == "http://example.org/empty"
    assert len(result["nodes"]) == 1
    assert result["edges"] == []

def test_get_graph_analytics_empty_graph():
    ontology = DummyOntology()
    gm = GraphManager(ontology)
    analytics = gm.get_graph_analytics()
    assert analytics["node_types"] == []
    assert analytics["relationship_types"] == []
    assert analytics["centrality"] == []

def test_search_entities_no_match():
    ontology = DummyOntology()
    gm = GraphManager(ontology)
    results = gm.search_entities("notfound")
    assert results == [] 