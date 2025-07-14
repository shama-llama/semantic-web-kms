import os
import re
import tempfile

import pytest

import app.core.paths as paths


def test_get_output_path():
    """Test get_output_path returns correct path."""
    filename = "test.txt"
    result = paths.get_output_path(filename)
    assert result.endswith(os.path.join(paths.OUTPUT_DIR, filename))


def test_get_log_path():
    """Test get_log_path returns correct path."""
    filename = "log.txt"
    result = paths.get_log_path(filename)
    assert result.endswith(os.path.join(paths.LOGS_DIR, filename))


def test_get_language_mapping_path():
    """Test get_language_mapping_path returns correct path."""
    assert paths.get_language_mapping_path() == paths.LANGUAGE_MAPPING_PATH


def test_get_code_queries_path():
    """Test get_code_queries_path returns correct path."""
    assert paths.get_code_queries_path() == paths.CODE_QUERIES_PATH


def test_get_file_extensions_path():
    """Test get_file_extensions_path returns correct path."""
    assert paths.get_carrier_extensions_path() == paths.CARRIER_TYPES_PATH


def test_get_excluded_directories_path():
    """Test get_excluded_directories_path returns correct path."""
    assert paths.get_excluded_directories_path() == paths.EXCLUDED_DIRECTORIES_PATH


def test_get_content_types_path():
    """Test get_content_types_path returns correct path."""
    assert paths.get_content_types_path() == paths.CONTENT_TYPES_PATH


def test_get_web_dev_ontology_path():
    """Test get_web_dev_ontology_path returns correct path."""
    assert paths.get_web_dev_ontology_path() == paths.WEB_DEV_ONTOLOGY_PATH


def test_get_basic_formal_ontology_path():
    """Test get_basic_formal_ontology_path returns correct path."""
    assert paths.get_basic_formal_ontology_path() == paths.BASIC_FORMAL_ONTOLOGY_PATH


def test_get_input_path(tmp_path):
    """Test get_input_path returns correct path after setting input dir."""
    filename = "input.txt"
    test_dir = str(tmp_path)
    paths.set_input_dir(test_dir)
    result = paths.get_input_path(filename)
    assert result.endswith(os.path.join(test_dir, filename))


def test_uri_safe_string():
    """Test uri_safe_string handles various edge cases."""
    assert paths.uri_safe_string("") == ""
    assert paths.uri_safe_string("abc") == "abc"
    assert (
        paths.uri_safe_string(r"a b/c:d*e?f\ng<h>i|j\tk\l\m\n")
        == "a_b/c_d_e_f_ng_h_i_j_tk_l_m_n"
    )
    assert paths.uri_safe_string("__a__b__") == "a_b"
    assert paths.uri_safe_string("a   b") == "a_b"
    assert paths.uri_safe_string("a---b") == "a---b"
    assert paths.uri_safe_string("a__b__c") == "a_b_c"
    assert paths.uri_safe_string("a__b__c!!") == "a_b_c"


def test_get_carrier_types_path():
    """Test get_carrier_types_path returns correct path."""
    result = paths.get_carrier_types_path()
    assert result.endswith(os.path.join("mappings", "carrier_types.json"))


def test_get_ontology_cache_path():
    """Test get_ontology_cache_path returns correct path."""
    result = paths.get_ontology_cache_path()
    assert result.endswith(paths.ONTOLOGY_CACHE_FILENAME)


def test_set_and_get_input_dir(tmp_path):
    """Test set_input_dir and get_input_dir work as expected."""
    test_dir = str(tmp_path)
    paths.set_input_dir(test_dir)
    assert paths.get_input_dir() == test_dir


def test_get_input_dir_not_set(monkeypatch):
    """Test get_input_dir raises RuntimeError if not set."""
    monkeypatch.setattr(paths, "_current_input_dir", None)
    with pytest.raises(RuntimeError):
        paths.get_input_dir()


def test_get_input_path_raises_if_input_dir_not_set(monkeypatch):
    """Test get_input_path raises RuntimeError if input dir not set."""
    monkeypatch.setattr(paths, "_current_input_dir", None)
    with pytest.raises(RuntimeError):
        paths.get_input_path("foo.txt")
