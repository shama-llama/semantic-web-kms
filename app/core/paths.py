from app.core.config import OUTPUT_DIR, LOG_DIR, MODEL_DIR, EXCLUDED_DIRS_PATH, LANGUAGE_MAPPING_PATH, CODE_QUERIES_PATH, WEB_DEV_EXTENSIONS_PATH
import os

# Centralized file extensions and supported types
SUPPORTED_DOC_EXTENSIONS = ['.md', '.markdown', '.rst', '.txt', '.pdf', '.html', '.htm']
SUPPORTED_CODE_EXTENSIONS = ['.py', '.js', '.ts', '.java', '.cpp', '.c', '.cs', '.go', '.rb', '.php', '.rs', '.swift', '.kt', '.scala', '.m', '.h', '.sh', '.pl', '.lua', '.r', '.jl', '.dart', '.sql', '.json', '.xml', '.yml', '.yaml', '.ini', '.cfg', '.toml']

def get_output_path(filename):
    """Return the absolute path for a file in the output directory."""
    return os.path.join(OUTPUT_DIR, filename)

def get_log_path(filename):
    """Return the absolute path for a file in the logs directory."""
    return os.path.join(LOG_DIR, filename)

def get_model_path(filename):
    """Return the absolute path for a file in the model directory."""
    return os.path.join(MODEL_DIR, filename)

def get_excluded_dirs_path():
    """Return the path to excluded_dirs.json."""
    return EXCLUDED_DIRS_PATH

def get_language_mapping_path():
    """Return the path to language_mapping.json."""
    return LANGUAGE_MAPPING_PATH

def get_code_queries_path():
    """Return the path to code_queries.json."""
    return CODE_QUERIES_PATH

def get_web_dev_extensions_path():
    """Return the path to web_development_extensions.json."""
    return WEB_DEV_EXTENSIONS_PATH 