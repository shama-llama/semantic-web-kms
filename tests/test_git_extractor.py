import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import pytest
from app.extraction import git_extractor
from rdflib import URIRef
import app.extraction.git_extractor as ge

def test_get_repo_uri():
    uri = ge.get_repo_uri('myrepo')
    assert 'myrepo' in str(uri)

def test_get_file_uri():
    uri = ge.get_file_uri('myrepo', 'src/file.py')
    assert 'myrepo' in str(uri) and 'src' in str(uri) and 'file.py' in str(uri)

def test_get_repo_uri_from_git_extractor():
    repo_name = "my-repo"
    uri = git_extractor.get_repo_uri(repo_name)
    assert isinstance(uri, URIRef)
    assert "my-repo" in str(uri)

def test_get_file_uri_from_git_extractor():
    repo_name = "my-repo"
    rel_path = "src/main.py"
    uri = git_extractor.get_file_uri(repo_name, rel_path)
    assert isinstance(uri, URIRef)
    assert "my-repo" in str(uri)
    assert "src" in str(uri)
    assert "main.py" in str(uri) 