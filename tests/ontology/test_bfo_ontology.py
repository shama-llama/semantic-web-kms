import os
import sys

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))
)
import pytest
from rdflib import OWL, RDF, RDFS, Graph, Literal, Namespace, URIRef

from app.ontology.bfo import BFOOntology


def make_test_bfo_graph() -> Graph:
    """Create a minimal in-memory BFO ontology graph for testing."""
    g = Graph()
    BFO = Namespace("http://purl.obolibrary.org/obo/")
    g.bind("bfo", BFO)
    # Entity class
    entity = BFO.BFO_0000001
    g.add((entity, RDF.type, OWL.Class))
    g.add((entity, RDFS.label, Literal("entity")))
    # Top-level subclasses
    cont = BFO.BFO_0000002
    occ = BFO.BFO_0000003
    g.add((cont, RDF.type, OWL.Class))
    g.add((cont, RDFS.label, Literal("continuant")))
    g.add((cont, RDFS.subClassOf, entity))
    g.add((occ, RDF.type, OWL.Class))
    g.add((occ, RDFS.label, Literal("occurrent")))
    g.add((occ, RDFS.subClassOf, entity))
    return g


def test_init_and_namespace(monkeypatch):
    """Test BFOOntology initialization and namespace assignment."""
    g = make_test_bfo_graph()

    # Patch Graph.parse to load our in-memory graph
    def fake_parse(self, path):
        for triple in g:
            self.add(triple)
        return self

    monkeypatch.setattr("rdflib.Graph.parse", fake_parse)
    onto = BFOOntology(owl_path="dummy.owl")
    assert str(onto.namespace) == "http://purl.obolibrary.org/obo/"
    assert onto.graph is not None


def test_is_bfo_class(monkeypatch):
    """Test is_bfo_class returns True for BFO URIs and False otherwise."""
    g = make_test_bfo_graph()

    def fake_parse(self, path):
        for triple in g:
            self.add(triple)
        return self

    monkeypatch.setattr("rdflib.Graph.parse", fake_parse)
    onto = BFOOntology(owl_path="dummy.owl")
    assert onto.is_bfo_class("http://purl.obolibrary.org/obo/BFO_0000001")
    assert not onto.is_bfo_class("http://example.org/Other")


def test_get_label(monkeypatch):
    """Test get_label returns the correct rdfs:label for a BFO class URI."""
    g = make_test_bfo_graph()

    def fake_parse(self, path):
        for triple in g:
            self.add(triple)
        return self

    monkeypatch.setattr("rdflib.Graph.parse", fake_parse)
    onto = BFOOntology(owl_path="dummy.owl")
    entity_uri = "http://purl.obolibrary.org/obo/BFO_0000001"
    assert onto.get_label(entity_uri) == "entity"
    assert onto.get_label("http://purl.obolibrary.org/obo/Nonexistent") is None


def test_get_top_level_classes(monkeypatch):
    """Test get_top_level_classes returns all direct subclasses of entity."""
    g = make_test_bfo_graph()

    def fake_parse(self, path):
        for triple in g:
            self.add(triple)
        return self

    monkeypatch.setattr("rdflib.Graph.parse", fake_parse)
    onto = BFOOntology(owl_path="dummy.owl")
    tops = onto.get_top_level_classes()
    uris = [uri for uri, label in tops]
    labels = [label for uri, label in tops]
    assert any("BFO_0000002" in uri for uri in uris)
    assert any("continuant" == label for label in labels)
    assert any("BFO_0000003" in uri for uri in uris)
    assert any("occurrent" == label for label in labels)
