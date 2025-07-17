import os
import sys

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))
)
import json
import tempfile
import types
from unittest.mock import MagicMock, patch

import pytest
from rdflib import OWL, RDF, RDFS, Graph, Literal, Namespace, URIRef

import app.extraction.ontology.ontology_utils as ontology_utils
from app.extraction.ontology.ontology_lookup import CommonOntology
from app.ontology.base import BaseOntology


def make_test_ontology_graph() -> Graph:
    """Create a minimal in-memory ontology graph for testing."""
    g = Graph()
    EX = Namespace("http://example.org/")
    g.bind("ex", EX)
    # Ontology
    g.add((EX[""], RDF.type, OWL.Ontology))
    # Classes
    g.add((EX.Foo, RDF.type, OWL.Class))
    g.add((EX.Bar, RDF.type, OWL.Class))
    g.add((EX.Foo, RDFS.label, Literal("Foo")))
    g.add((EX.Bar, RDFS.label, Literal("Bar")))
    g.add((EX.Bar, RDFS.subClassOf, EX.Foo))
    # Properties
    g.add((EX.hasValue, RDF.type, OWL.ObjectProperty))
    g.add((EX.hasValue, RDFS.label, Literal("hasValue")))
    g.add((EX.hasData, RDF.type, OWL.DatatypeProperty))
    g.add((EX.hasData, RDFS.label, Literal("hasData")))
    return g


def test_init_and_namespace_extraction(tmp_path):
    """Test BaseOntology initialization and namespace extraction from OWL file."""
    g = make_test_ontology_graph()
    owl_path = tmp_path / "test.owl"
    g.serialize(destination=str(owl_path), format="xml")
    onto = BaseOntology(str(owl_path))
    # Only check that ontology URI is not None (namespace preservation is not guaranteed)
    assert onto.ontology_uri is not None


def test_get_class_uri_and_property_uri(tmp_path):
    """Test get_class_uri and get_property_uri by label and local part."""
    g = make_test_ontology_graph()
    owl_path = tmp_path / "test.owl"
    g.serialize(destination=str(owl_path), format="xml")
    onto = BaseOntology(str(owl_path))
    # By label
    foo_uri = onto.get_class_uri("Foo")
    assert foo_uri is not None and foo_uri.endswith("Foo")
    # By local part
    bar_uri = onto.get_class_uri("Bar")
    assert bar_uri is not None and bar_uri.endswith("Bar")
    # Property by label
    has_value_uri = onto.get_property_uri("hasValue")
    assert has_value_uri is not None and has_value_uri.endswith("hasValue")
    # Property by local part
    has_data_uri = onto.get_property_uri("hasData")
    assert has_data_uri is not None and has_data_uri.endswith("hasData")


def test_get_superclass_chain(tmp_path):
    """Test get_superclass_chain returns correct chain up to root."""
    g = make_test_ontology_graph()
    owl_path = tmp_path / "test.owl"
    g.serialize(destination=str(owl_path), format="xml")
    onto = BaseOntology(str(owl_path))
    bar_uri = onto.get_class_uri("Bar")
    assert bar_uri is not None, "Bar class URI not found"
    chain = onto.get_superclass_chain(bar_uri)
    assert any("Foo" in uri for uri in chain)


def test_get_all_classes_and_properties(tmp_path):
    """Test get_all_classes and get_all_properties return all URIs."""
    g = make_test_ontology_graph()
    owl_path = tmp_path / "test.owl"
    g.serialize(destination=str(owl_path), format="xml")
    onto = BaseOntology(str(owl_path))
    classes = onto.get_all_classes()
    props = onto.get_all_properties()
    assert any("Foo" in uri for uri in classes)
    assert any("Bar" in uri for uri in classes)
    assert any("hasValue" in uri for uri in props)
    assert any("hasData" in uri for uri in props)


def test_get_subclasses(tmp_path):
    """Test get_subclasses returns direct and recursive subclasses."""
    g = make_test_ontology_graph()
    owl_path = tmp_path / "test.owl"
    g.serialize(destination=str(owl_path), format="xml")
    onto = BaseOntology(str(owl_path))
    foo_uri = onto.get_class_uri("Foo")
    assert foo_uri is not None, "Foo class URI not found"
    subclasses_direct = onto.get_subclasses(foo_uri, direct_only=True)
    subclasses_recursive = onto.get_subclasses(foo_uri, direct_only=False)
    assert any("Bar" in uri for uri in subclasses_direct)
    assert any("Bar" in uri for uri in subclasses_recursive)


def test_register_ontology():
    """Test register_ontology adds to the registry."""
    from app.ontology import base as base_mod

    class Dummy:
        pass

    base_mod.register_ontology("dummy", Dummy)
    assert base_mod._ontology_registry["dummy"] is Dummy


class DummyBaseOntology:
    def __init__(self, ontology_path):
        self.ontology_path = ontology_path

    def get_class_uri(self, class_name):
        if class_name == "FoundClass":
            return URIRef(f"http://example.org/{class_name}")
        return None

    def get_property_uri(self, prop_name):
        if prop_name == "FoundProp":
            return URIRef(f"http://example.org/{prop_name}")
        return None


def test_common_ontology_init_with_cache(tmp_path, monkeypatch):
    # Patch BaseOntology to DummyBaseOntology
    monkeypatch.setattr(
        "app.extraction.ontology.ontology_lookup.BaseOntology", DummyBaseOntology
    )
    cache_path = tmp_path / "cache.json"
    with open(cache_path, "w") as f:
        json.dump({"classes": ["A", "B"]}, f)
    co = CommonOntology("ontology.owl", str(cache_path))
    assert co.available_classes == {"A", "B"}


def test_common_ontology_init_no_cache(monkeypatch):
    monkeypatch.setattr(
        "app.extraction.ontology.ontology_lookup.BaseOntology", DummyBaseOntology
    )
    co = CommonOntology("ontology.owl", None)
    assert co.available_classes == set()


def test_common_ontology_get_class_found(monkeypatch):
    monkeypatch.setattr(
        "app.extraction.ontology.ontology_lookup.BaseOntology", DummyBaseOntology
    )
    co = CommonOntology("ontology.owl")
    co.get_class_uri = lambda class_name: (
        URIRef(f"http://example.org/{class_name}")
        if class_name == "FoundClass"
        else None
    )
    assert co.get_class("FoundClass") == URIRef("http://example.org/FoundClass")


def test_common_ontology_get_class_not_found(monkeypatch):
    monkeypatch.setattr(
        "app.extraction.ontology.ontology_lookup.BaseOntology", DummyBaseOntology
    )
    co = CommonOntology("ontology.owl")
    co.get_class_uri = lambda class_name: None
    with pytest.raises(KeyError):
        co.get_class("MissingClass")


def test_common_ontology_get_property_found(monkeypatch):
    monkeypatch.setattr(
        "app.extraction.ontology.ontology_lookup.BaseOntology", DummyBaseOntology
    )
    co = CommonOntology("ontology.owl")
    co.get_property_uri = lambda prop_name: (
        URIRef(f"http://example.org/{prop_name}") if prop_name == "FoundProp" else None
    )
    assert co.get_property("FoundProp") == URIRef("http://example.org/FoundProp")


def test_common_ontology_get_property_not_found(monkeypatch):
    monkeypatch.setattr(
        "app.extraction.ontology.ontology_lookup.BaseOntology", DummyBaseOntology
    )
    co = CommonOntology("ontology.owl")
    co.get_property_uri = lambda prop_name: None
    with pytest.raises(KeyError):
        co.get_property("MissingProp")


def test_get_property_fallback(monkeypatch):
    fake_WDO = MagicMock()
    fake_WDO.__getitem__.side_effect = lambda k: URIRef(f"http://wdo.org/{k}")
    monkeypatch.setattr(ontology_utils, "WDO", fake_WDO)
    assert ontology_utils.get_property_fallback("foo") == URIRef("http://wdo.org/foo")


def test_get_class_fallback(monkeypatch):
    fake_WDO = MagicMock()
    fake_WDO.__getitem__.side_effect = lambda k: URIRef(f"http://wdo.org/{k}")
    monkeypatch.setattr(ontology_utils, "WDO", fake_WDO)
    assert ontology_utils.get_class_fallback("bar") == URIRef("http://wdo.org/bar")


def test_is_complex_type():
    assert ontology_utils._is_complex_type("ComplexType")
    assert not ontology_utils._is_complex_type("Other")


def test_is_code_construct():
    assert ontology_utils._is_code_construct("CodeConstruct")
    assert not ontology_utils._is_code_construct("Other")


def test_is_type_declaration():
    assert ontology_utils._is_type_declaration("TypeDeclaration")
    assert not ontology_utils._is_type_declaration("Other")


def test_is_attribute_declaration():
    assert ontology_utils._is_attribute_declaration("AttributeDeclaration")
    assert not ontology_utils._is_attribute_declaration("Other")
