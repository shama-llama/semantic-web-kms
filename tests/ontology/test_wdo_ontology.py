import os
import sys

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))
)
import pytest
from rdflib import OWL, RDF, RDFS, Graph, Literal, Namespace, URIRef


class DummyBFO:
    def is_bfo_class(self, uri):
        return uri == "http://bfo/entity"


def make_test_wdo_graph() -> Graph:
    """Create a minimal in-memory WDO ontology graph for testing."""
    g = Graph()
    WDO = Namespace("http://wdo/")
    g.bind("wdo", WDO)
    # Classes
    g.add((WDO.Foo, RDF.type, OWL.Class))
    g.add((WDO.Foo, RDFS.label, Literal("Foo")))
    g.add((WDO.Bar, RDF.type, OWL.Class))
    g.add((WDO.Bar, RDFS.label, Literal("Bar")))
    g.add((WDO.Bar, RDFS.subClassOf, WDO.Foo))
    # Properties
    g.add((WDO.hasValue, RDF.type, OWL.ObjectProperty))
    g.add((WDO.hasValue, RDFS.label, Literal("hasValue")))
    g.add((WDO.hasData, RDF.type, OWL.DatatypeProperty))
    g.add((WDO.hasData, RDFS.label, Literal("hasData")))
    return g


def test_init_and_integration(monkeypatch):
    """Test WDOOntology initialization and BFO integration."""
    g = make_test_wdo_graph()

    def fake_parse(self, path):
        for triple in g:
            self.add(triple)
        return self

    monkeypatch.setattr("rdflib.Graph.parse", fake_parse)
    from app.ontology.wdo import WDOOntology  # Import after monkeypatching

    onto = WDOOntology(owl_path="dummy.owl", bfo_ontology=DummyBFO())
    assert onto.graph is not None
    assert onto.bfo_ontology is not None


def test_get_class_and_property(monkeypatch):
    """Test get_class and get_property return correct URIs."""
    g = make_test_wdo_graph()

    def fake_parse(self, path):
        for triple in g:
            self.add(triple)
        return self

    monkeypatch.setattr("rdflib.Graph.parse", fake_parse)
    from app.ontology.wdo import WDOOntology  # Import after monkeypatching

    onto = WDOOntology(owl_path="dummy.owl", bfo_ontology=DummyBFO())
    onto.graph = g  # Inject the test graph directly
    try:
        foo_uri = onto.get_class("Foo")
    except KeyError:
        print("Available class URIs:", onto.get_all_classes())
        print(
            "Class labels:",
            [
                onto.graph.value(URIRef(uri), RDFS.label)
                for uri in onto.get_all_classes()
            ],
        )
        raise
    assert str(foo_uri).endswith("Foo")
    has_value_uri = onto.get_property("hasValue")
    assert str(has_value_uri).endswith("hasValue")


def test_get_class_and_property_not_found(monkeypatch):
    """Test get_class and get_property raise KeyError if not found."""
    g = make_test_wdo_graph()

    def fake_parse(self, path):
        for triple in g:
            self.add(triple)
        return self

    monkeypatch.setattr("rdflib.Graph.parse", fake_parse)
    from app.ontology.wdo import WDOOntology  # Import after monkeypatching

    onto = WDOOntology(owl_path="dummy.owl", bfo_ontology=DummyBFO())
    with pytest.raises(KeyError):
        onto.get_class("Nonexistent")
    with pytest.raises(KeyError):
        onto.get_property("Nonexistent")


def test_get_top_level_bfo_ancestor(monkeypatch):
    """Test get_top_level_bfo_ancestor returns the correct BFO ancestor URI or None."""
    g = make_test_wdo_graph()

    def fake_parse(self, path):
        for triple in g:
            self.add(triple)
        return self

    monkeypatch.setattr("rdflib.Graph.parse", fake_parse)

    class DummyBFO:
        def is_bfo_class(self, uri):
            return uri == "http://bfo/entity"

    from app.ontology.wdo import WDOOntology  # Import after monkeypatching

    onto = WDOOntology(owl_path="dummy.owl", bfo_ontology=DummyBFO())
    # Patch get_superclass_chain to simulate a BFO ancestor
    onto.get_superclass_chain = lambda class_uri: [
        "http://wdo/Foo",
        "http://bfo/entity",
    ]
    ancestor = onto.get_top_level_bfo_ancestor("http://wdo/Bar")
    assert ancestor == "http://bfo/entity"
    # No BFO ancestor
    onto.get_superclass_chain = lambda class_uri: ["http://wdo/Foo"]
    assert onto.get_top_level_bfo_ancestor("http://wdo/Bar") is None
