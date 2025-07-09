import pytest
from rdflib.namespace import SKOS as RDFlibSKOS

from app.core import namespaces


def test_wdo_namespace():
    """Test that WDO namespace is defined correctly."""
    assert str(namespaces.WDO) == "http://semantic-web-kms.edu.et/wdo#"


def test_inst_namespace():
    """Test that INST namespace is defined correctly."""
    assert str(namespaces.INST) == "http://semantic-web-kms.edu.et/wdo/instances/"


def test_skos_namespace():
    """Test that SKOS namespace is the standard rdflib SKOS namespace."""
    assert namespaces.SKOS is RDFlibSKOS


def test_dcterms_namespace():
    """Test that DCTERMS namespace is defined correctly."""
    assert str(namespaces.DCTERMS) == "http://purl.org/dc/terms/"
