import os
import sys

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../"))
)
import json
import re
import tempfile
from typing import Any, Dict, List, Set, Tuple
from unittest import mock

import pytest

import app.core.paths as core_paths
from app.extraction.extractors import file_extractor


@pytest.fixture
def mock_ontology():
    class DummyOntology:
        def __init__(self):
            self.lookup = {}

    return DummyOntology()


@pytest.fixture
def mock_classifiers():
    return [
        ("TestClass", mock.Mock(spec=os.PathLike)),
    ], [mock.Mock(spec=os.PathLike)]


@pytest.fixture
def mock_ontology_class_cache():
    return {"TestClass"}


@pytest.fixture
def mock_file_record():
    return {
        "id": 1,
        "repository": "repo1",
        "path": "file1.py",
        "abs_path": "/tmp/repo1/file1.py",
        "filename": "file1.py",
        "size_bytes": 123,
        "extension": ".py",
        "ontology_class": "TestClass",
        "class_uri": "http://example.org/TestClass",
        "creation_timestamp": 0,
        "modification_timestamp": 0,
    }


def test_extract_files_minimal(
    monkeypatch, mock_ontology, mock_classifiers, mock_ontology_class_cache
):
    # Patch get_repo_file_map to return a fake repo with one file
    monkeypatch.setattr(
        file_extractor,
        "get_repo_file_map",
        lambda excl: {"repo1": [("file1.py", "/tmp/repo1/file1.py", "file1.py")]},
    )
    monkeypatch.setattr(
        file_extractor,
        "make_file_record",
        lambda *a, **kw: {
            "id": 1,
            "repository": "repo1",
            "path": "file1.py",
            "abs_path": "/tmp/repo1/file1.py",
            "filename": "file1.py",
            "size_bytes": 123,
            "extension": ".py",
            "ontology_class": "TestClass",
            "class_uri": "http://example.org/TestClass",
            "creation_timestamp": 0,
            "modification_timestamp": 0,
        },
    )
    monkeypatch.setattr(
        file_extractor,
        "classify_file",
        lambda *a, **kw: ("TestClass", "http://example.org/TestClass", None),
    )
    monkeypatch.setattr(os.path, "getsize", lambda path: 123)
    files = file_extractor.extract_files(
        excluded_dirs=set(),
        file_classifiers=mock_classifiers[0],
        file_ignore_patterns=mock_classifiers[1],
        ontology=mock_ontology,
        ontology_class_cache=mock_ontology_class_cache,
        progress=None,
        extract_task=None,
    )
    assert isinstance(files, list)
    assert files[0]["ontology_class"] == "TestClass"
    assert files[0]["class_uri"] == "http://example.org/TestClass"


def test_build_granular_carrier_type_map(monkeypatch):
    # Patch load_classifiers_from_json to return dummy data
    monkeypatch.setattr(
        file_extractor,
        "load_classifiers_from_json",
        lambda path: ([("A", re.compile(r".*"))], [re.compile(r".*")]),
    )
    monkeypatch.setattr(file_extractor, "get_carrier_types_path", lambda: "dummy.json")
    classifiers, ignore_patterns = file_extractor.build_granular_carrier_type_map()
    assert isinstance(classifiers, list)
    assert isinstance(ignore_patterns, list)


def test_main_runs(monkeypatch, tmp_path):
    # Patch all file/ontology dependencies to simulate a run
    dummy_json = tmp_path / "excluded.json"
    dummy_json.write_text(json.dumps([".git"]))
    dummy_cache = tmp_path / "cache.json"
    dummy_cache.write_text(json.dumps({"classes": ["TestClass"]}))
    dummy_ontology = tmp_path / "ontology.owl"
    dummy_ontology.write_text("")
    dummy_output = tmp_path / "wdkb.ttl"
    monkeypatch.setattr(
        file_extractor, "get_web_dev_ontology_path", lambda: str(dummy_ontology)
    )
    monkeypatch.setattr(file_extractor, "get_input_path", lambda _: str(tmp_path))
    monkeypatch.setattr(
        file_extractor, "get_excluded_directories_path", lambda: str(dummy_json)
    )
    monkeypatch.setattr(
        file_extractor, "get_ontology_cache_path", lambda: str(dummy_cache)
    )
    monkeypatch.setattr(file_extractor, "get_output_path", lambda _: str(dummy_output))
    monkeypatch.setattr(file_extractor, "WDOOntology", mock.Mock())
    monkeypatch.setattr(
        file_extractor,
        "build_granular_carrier_type_map",
        lambda: ([("A", re.compile(r".*"))], [re.compile(r".*")]),
    )
    monkeypatch.setattr(
        file_extractor,
        "get_repo_file_map",
        lambda excl: {"repo1": [("file1.py", str(tmp_path / "file1.py"), "file1.py")]},
    )
    monkeypatch.setattr(
        file_extractor,
        "count_total_files",
        lambda repo_dirs, excluded_dirs: 1,
    )
    monkeypatch.setattr(
        file_extractor,
        "extract_files",
        lambda *a, **kw: [
            {
                "id": 1,
                "repository": "repo1",
                "path": "file1.py",
                "abs_path": str(tmp_path / "file1.py"),
                "filename": "file1.py",
                "size_bytes": 123,
                "extension": ".py",
                "ontology_class": "TestClass",
                "class_uri": "http://example.org/TestClass",
                "creation_timestamp": 0,
                "modification_timestamp": 0,
            }
        ],
    )
    monkeypatch.setattr(
        file_extractor, "write_ttl_with_progress", lambda *a, **kw: None
    )
    # Patch Graph to avoid actual RDF parsing
    monkeypatch.setattr(file_extractor, "Graph", mock.Mock())

    # Patch Console to avoid actual output and support context manager
    class DummyConsole:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            pass

        def print(self, *args, **kwargs):
            pass

        def clear_live(self):
            pass

        def set_live(self, live):
            pass

        def get_time(self):
            import time

            return time.time()

        def log(self, *args, **kwargs):
            pass

        def show_cursor(self, show):
            pass

        def push_render_hook(self, hook):
            pass

        def pop_render_hook(self):
            pass

        @property
        def is_terminal(self):
            return False

        @property
        def is_jupyter(self):
            return False

        @property
        def is_interactive(self):
            return False

    monkeypatch.setattr(file_extractor, "Console", DummyConsole)
    core_paths.set_input_dir(str(tmp_path))
    file_extractor.main()


def test_main_error_handling(tmp_path, monkeypatch, caplog):
    import json
    import os

    # Patch all file/ontology dependencies to simulate a run with errors
    dummy_json = tmp_path / "excluded.json"
    dummy_json.write_text(json.dumps([".git"]))
    dummy_cache = tmp_path / "cache.json"
    dummy_cache.write_text(json.dumps({"classes": ["TestClass"]}))
    dummy_ontology = tmp_path / "ontology.owl"
    dummy_ontology.write_text("")
    dummy_output = tmp_path / "wdkb.ttl"
    monkeypatch.setattr(
        file_extractor, "get_web_dev_ontology_path", lambda: str(dummy_ontology)
    )
    monkeypatch.setattr(file_extractor, "get_input_path", lambda _: str(tmp_path))
    monkeypatch.setattr(
        file_extractor, "get_excluded_directories_path", lambda: str(dummy_json)
    )
    monkeypatch.setattr(
        file_extractor, "get_ontology_cache_path", lambda: str(dummy_cache)
    )
    monkeypatch.setattr(file_extractor, "get_output_path", lambda _: str(dummy_output))
    monkeypatch.setattr(file_extractor, "WDOOntology", mock.Mock())
    monkeypatch.setattr(
        file_extractor,
        "build_granular_carrier_type_map",
        lambda: ([("A", re.compile(r".*"))], [re.compile(r".*")]),
    )
    # Simulate a repo with one file that is unreadable
    unreadable_file = tmp_path / "file1.py"
    unreadable_file.write_text("print('hello')\n")
    monkeypatch.setattr(
        file_extractor,
        "get_repo_file_map",
        lambda excl: {"repo1": [("file1.py", str(unreadable_file), "file1.py")]},
    )
    monkeypatch.setattr(
        file_extractor, "count_total_files", lambda repo_dirs, excluded_dirs: 1
    )
    # Patch os.path.getsize to raise OSError for unreadable file
    monkeypatch.setattr(
        os.path,
        "getsize",
        lambda path: (_ for _ in ()).throw(OSError("unreadable file")),
    )
    # Patch classify_file to raise an exception for missing ontology class
    monkeypatch.setattr(
        file_extractor,
        "classify_file",
        lambda *a, **kw: (_ for _ in ()).throw(Exception("missing ontology class")),
    )
    # Patch make_file_record to just return a dict
    monkeypatch.setattr(file_extractor, "make_file_record", lambda *a, **kw: {"id": 1})
    # Patch write_ttl_with_progress to do nothing
    monkeypatch.setattr(
        file_extractor, "write_ttl_with_progress", lambda *a, **kw: None
    )
    # Patch Graph to avoid actual RDF parsing
    monkeypatch.setattr(file_extractor, "Graph", mock.Mock())

    # Patch Console to avoid actual output and support context manager
    class DummyConsole:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            pass

        def print(self, *args, **kwargs):
            pass

    monkeypatch.setattr(file_extractor, "Console", DummyConsole)
    # Run main and check for error logs
    with pytest.raises(Exception):
        file_extractor.main()
