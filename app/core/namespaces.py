"""Namespace definitions for Semantic Web KMS ontologies."""

from rdflib import Namespace
from rdflib.namespace import SKOS as RDFlibSKOS

# Web Development Ontology namespace
WDO = Namespace("http://semantic-web-kms.edu.et/wdo#")
# Instance namespace
INST = Namespace("http://semantic-web-kms.edu.et/wdo/instances/")
# SKOS namespace (standard)
SKOS = RDFlibSKOS

# Dublin Core Terms namespace
DCTERMS = Namespace("http://purl.org/dc/terms/")

__all__ = ["WDO", "INST", "SKOS"]
