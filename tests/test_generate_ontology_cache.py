import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import pytest
from app.utils import generate_ontology_cache

def test_get_local_name():
    assert generate_ontology_cache.get_local_name("http://example.org/foo#Bar") == "Bar"
    assert generate_ontology_cache.get_local_name("http://example.org/foo/Bar") == "Bar"
    assert generate_ontology_cache.get_local_name("http://example.org/foo/Bar/") == "Bar"
    assert generate_ontology_cache.get_local_name("Bar") == "Bar" 