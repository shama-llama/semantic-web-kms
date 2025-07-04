import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import pytest
from app.core import paths

def test_get_output_path():
    filename = "test.txt"
    result = paths.get_output_path(filename)
    assert result.endswith(os.path.join("output", filename))

def test_get_log_path():
    filename = "log.txt"
    result = paths.get_log_path(filename)
    assert result.endswith(os.path.join("logs", filename))

def test_uri_safe_string():
    assert paths.uri_safe_string("hello world") == "hello_world"
    assert paths.uri_safe_string("foo/bar:baz") == "foo_bar_baz"
    assert paths.uri_safe_string("  weird__name!!  ") == "weird_name"
    assert paths.uri_safe_string("") == "" 