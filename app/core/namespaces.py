"""Namespace definitions for Semantic Web KMS ontologies."""

from rdflib import Namespace
from rdflib.namespace import SKOS as RDFlibSKOS

# Web Development Ontology namespace
WDO = Namespace("http://web-development-ontology.netlify.app/wdo#")
# Instance namespace
INST = Namespace("http://web-development-ontology.netlify.app/wdo/instances/")
# SKOS namespace (standard)
SKOS = RDFlibSKOS
# Dublin Core Terms namespace
DCTERMS = Namespace("http://purl.org/dc/terms/")
# FOAF namespace (Friend of a Friend)
FOAF = Namespace("http://xmlns.com/foaf/0.1/")
FOAF_PERSON_URI = FOAF.Person

__all__ = ["WDO", "INST", "SKOS", "FOAF", "FOAF_PERSON_URI"]
