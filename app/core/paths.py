from app.core.config import (
    OUTPUT_DIR, LOG_DIR, MODEL_DIR, LANGUAGE_MAPPING_PATH, CODE_QUERIES_PATH, 
    FILE_EXTENSIONS_PATH, EXCLUDED_DIRECTORIES_PATH, CONTENT_TYPES_PATH,
    WEB_DEV_ONTOLOGY_PATH, BASIC_FORMAL_ONTOLOGY_PATH, DEFAULT_INPUT_DIR
)
import os
import re


def get_output_path(filename):
    """Return the absolute path for a file in the output directory."""
    return os.path.join(OUTPUT_DIR, filename)


def get_log_path(filename):
    """Return the absolute path for a file in the logs directory."""
    return os.path.join(LOG_DIR, filename)


def get_language_mapping_path():
    """Return the path to language_mapping.json."""
    return LANGUAGE_MAPPING_PATH


def get_code_queries_path():
    """Return the path to code_queries.json."""
    return CODE_QUERIES_PATH


def get_file_extensions_path():
    """Return the path to file_extensions.json."""
    return FILE_EXTENSIONS_PATH


def get_excluded_directories_path():
    """Return the path to excluded_directories.json."""
    return EXCLUDED_DIRECTORIES_PATH


def get_content_types_path():
    """Return the path to content_types.json."""
    return CONTENT_TYPES_PATH


def get_web_dev_ontology_path():
    """Return the path to web_development_ontology.owl."""
    return WEB_DEV_ONTOLOGY_PATH


def get_basic_formal_ontology_path():
    """Return the path to basic_formal_ontology.owl."""
    return BASIC_FORMAL_ONTOLOGY_PATH


def get_model_path(filename):
    """Return the absolute path for a file in the model directory."""
    return os.path.join(MODEL_DIR, filename)


def get_input_path(filename):
    """Return the absolute path for a file in the input directory."""
    return os.path.join(DEFAULT_INPUT_DIR, filename)


def uri_safe_string(text):
    """
    Convert a string to URI-safe format by replacing problematic characters with underscores.
    This replaces URL encoding with a more readable underscore-based approach.
    
    Args:
        text (str): The input string to make URI-safe
        
    Returns:
        str: URI-safe string with problematic characters replaced by underscores
    """
    if not text:
        return ""
    
    # Replace spaces and other problematic characters with underscores
    # This includes: spaces, tabs, newlines, and other whitespace
    # Also includes: /, \, :, *, ?, ", <, >, |, and other filesystem-incompatible chars
    uri_safe = re.sub(r'[^\w\-_.]', '_', str(text))
    
    # Replace multiple consecutive underscores with a single one
    uri_safe = re.sub(r'_+', '_', uri_safe)
    
    # Remove leading/trailing underscores
    uri_safe = uri_safe.strip('_')
    
    return uri_safe
