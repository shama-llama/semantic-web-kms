"""Centralized constants and configuration for the annotation pipeline."""

from rdflib.namespace import RDFS

from engine.core.namespaces import DCTERMS

# --- Shared Properties ---

ANNOTATION_PROPERTIES = {
    RDFS.label,
    RDFS.comment,
    DCTERMS.description,
    DCTERMS.type,
    RDFS.seeAlso,
}

# --- URI / URL Configuration ---

ENTITY_BASE_URL = "https://knowledge-graph.org/entity/"

# --- Gemini model ---

GEMINI_DEFAULT_MODEL = "gemini-2.5-flash-lite-preview-06-17"

# --- Similarity Calculation Configuration ---

SIMILARITY_WEIGHTS = {
    "text": 0.5,
    "type": 0.3,
    "relationship": 0.2,
}
SIMILARITY_TOP_K = 3
SIMILARITY_MIN_SCORE = 0.1
SIMILARITY_MAX_INSTANCES = 1000
CENTRALITY_BOOST_FACTOR = 0.5  # How much to boost similarity for high-centrality nodes

# --- Text Processing Configuration ---

NOTE_MIN_LENGTH = 10
NOTE_MAX_LENGTH = 300
NOTE_MAX_SENTENCES = 2

REPETITIVE_PHRASES_MAP = {
    "is a fundamental component within the codebase": "contributes to the codebase",
    "is intrinsically linked to": "is part of",
    "plays a crucial role": "serves a purpose",
    "fundamental component": "component",
    "essential functionality": "functionality",
    "necessary code elements": "code elements",
    "available for execution": "available",
    "overall structure and organization": "system structure",
    "proper functionality and system coherence": "system functionality",
    "vital role in the codebase": "role in the codebase",
    "important component within the codebase": "component in the codebase",
    "provides essential functionality and structure": "provides functionality",
    "crucial for maintaining proper structure": "helps maintain structure",
    "ensures proper functionality": "supports functionality",
    "is a core element within the codebase": "is part of the codebase",
    "specifically representing the act of": "represents",
    "core component within": "component in",
    "a core component within": "a component in",
    "represents the entity named": "represents",
    "with a canonical name of": "with canonical name",
    "and a simple name of": "with simple name",
    "While its canonical name is": "Its canonical name is",
    "it can also be described by its text value": "it has text value",
    "written in": "implemented in",
    "has a canonical name of": "has canonical name",
}
