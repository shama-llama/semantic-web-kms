import os

APP_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))

# Main directories
LOG_DIR = os.path.join(APP_ROOT, 'logs')
OUTPUT_DIR = os.path.join(APP_ROOT, 'output')
MODEL_DIR = os.path.join(APP_ROOT, 'model')

# Model/config files
LANGUAGE_MAPPING_PATH = os.path.join(MODEL_DIR, 'language_mapping.json')
CODE_QUERIES_PATH = os.path.join(MODEL_DIR, 'code_queries.json')
FILE_EXTENSIONS_PATH = os.path.join(MODEL_DIR, 'file_extensions.json')
EXCLUDED_DIRECTORIES_PATH = os.path.join(MODEL_DIR, 'excluded_directories.json')
CONTENT_TYPES_PATH = os.path.join(MODEL_DIR, 'content_types.json')
WEB_DEV_ONTOLOGY_PATH = os.path.join(MODEL_DIR, 'web_development_ontology.owl')
BASIC_FORMAL_ONTOLOGY_PATH = os.path.join(MODEL_DIR, 'basic_formal_ontology.owl')

# Default input directory for extractors
DEFAULT_INPUT_DIR = os.path.expanduser("~/downloads/repos/Thinkster")
