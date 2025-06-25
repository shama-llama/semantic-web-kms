import os

APP_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))

# Main directories
DATA_DIR = os.path.join(APP_ROOT, 'data')
LOG_DIR = os.path.join(APP_ROOT, 'logs')
OUTPUT_DIR = os.path.join(APP_ROOT, 'output')
MODEL_DIR = os.path.join(APP_ROOT, 'model')

# Model/config files
EXCLUDED_DIRS_PATH = os.path.join(MODEL_DIR, 'excluded_dirs.json')
LANGUAGE_MAPPING_PATH = os.path.join(MODEL_DIR, 'language_mapping.json')
CODE_QUERIES_PATH = os.path.join(MODEL_DIR, 'code_queries.json')
WEB_DEV_EXTENSIONS_PATH = os.path.join(MODEL_DIR, 'web_development_extensions.json')

# Default input directory for extractors
DEFAULT_INPUT_DIR = os.path.expanduser("~/downloads/documents/repos/roots")

# Batch sizes, timeouts, and limits
DEFAULT_BATCH_SIZE = 500
DEFAULT_TIMEOUT = 30  # seconds
MAX_QUERY_RESULTS = 1000

# Default formats
DEFAULT_RDF_FORMAT = 'turtle'
DEFAULT_JSON_INDENT = 2

# Default URLs and endpoints
DEFAULT_FUSEKI_URL = os.environ.get('FUSEKI_URL', 'http://localhost:3030')
DEFAULT_FUSEKI_DATASET = os.environ.get('FUSEKI_DATASET', 'semantic-web-kms')
DEFAULT_ELASTIC_URL = os.environ.get('ELASTIC_URL', 'http://localhost:9200')
DEFAULT_ELASTIC_INDEX = os.environ.get('ELASTIC_INDEX', 'assets')

# Environment variable helper
def get_env_var(name, default=None):
    """Get an environment variable with a default."""
    return os.environ.get(name, default)
