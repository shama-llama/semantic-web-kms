"""Configuration constants and paths for Semantic Web KMS."""

import os

# Always resolve project root as the parent of the 'app' directory
APP_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if os.path.basename(APP_ROOT) == "app":
    APP_ROOT = os.path.dirname(APP_ROOT)
OUTPUT_DIR = os.path.join(APP_ROOT, "output")
LOGS_DIR = os.path.join(APP_ROOT, "logs")

# Main directories
MAPPINGS_DIR = os.path.join(APP_ROOT, "mappings")
ONTOLOGIES_DIR = os.path.join(APP_ROOT, "ontologies")

# Mapping/config files
LANGUAGE_MAPPING_PATH = os.path.join(MAPPINGS_DIR, "language_mapping.json")
CODE_QUERIES_PATH = os.path.join(MAPPINGS_DIR, "code_queries.json")
CARRIER_TYPES_PATH = os.path.join(MAPPINGS_DIR, "carrier_types.json")
EXCLUDED_DIRECTORIES_PATH = os.path.join(MAPPINGS_DIR, "excluded_directories.json")
CONTENT_TYPES_PATH = os.path.join(MAPPINGS_DIR, "content_types.json")
WEB_DEV_ONTOLOGY_PATH = os.path.join(ONTOLOGIES_DIR, "wdo.owl")
BASIC_FORMAL_ONTOLOGY_PATH = os.path.join(ONTOLOGIES_DIR, "bfo.owl")

# Ontology cache filename (for use in paths)
ONTOLOGY_CACHE_FILENAME = "ontology_cache.json"
