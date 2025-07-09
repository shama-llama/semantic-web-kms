import os
import sys

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../"))
)
from unittest import mock

import pytest

from app.extraction.extractors import content_extractor


def test_empty_input_directory(monkeypatch, tmp_path):
    import json

    import app.core.paths as core_paths

    # Patch get_repo_dirs to return no repos
    monkeypatch.setattr(content_extractor, "get_repo_dirs", lambda excluded: [])
    # Patch build_file_records to return no files
    monkeypatch.setattr(content_extractor, "build_file_records", lambda *a, **kw: [])
    # Create dummy config files
    (tmp_path / "content_types.json").write_text(
        json.dumps({"classifiers": [], "ignore_patterns": []})
    )
    (tmp_path / "ontology.owl").write_text(
        """<?xml version='1.0'?><rdf:RDF xmlns:rdf='http://www.w3.org/1999/02/22-rdf-syntax-ns#'></rdf:RDF>"""
    )
    (tmp_path / "excluded.json").write_text("[]")
    (tmp_path / "cache.json").write_text("{}")
    (tmp_path / "out.ttl").write_text("")
    # Patch config and output functions
    monkeypatch.setattr(
        content_extractor,
        "get_content_types_path",
        lambda: str(tmp_path / "content_types.json"),
    )
    monkeypatch.setattr(
        content_extractor,
        "get_web_dev_ontology_path",
        lambda: str(tmp_path / "ontology.owl"),
    )
    monkeypatch.setattr(
        content_extractor,
        "get_excluded_directories_path",
        lambda: str(tmp_path / "excluded.json"),
    )
    monkeypatch.setattr(
        content_extractor,
        "get_ontology_cache_path",
        lambda: str(tmp_path / "cache.json"),
    )
    monkeypatch.setattr(
        content_extractor, "get_output_path", lambda _: str(tmp_path / "out.ttl")
    )
    monkeypatch.setattr(content_extractor, "get_input_dir", lambda: str(tmp_path))

    class DummyOntology:
        def __init__(self, *args, **kwargs):
            pass

    monkeypatch.setattr(content_extractor, "OntologyWrapper", DummyOntology)
    monkeypatch.setattr(
        content_extractor, "write_ttl_with_progress", lambda *a, **kw: None
    )
    core_paths.set_input_dir(str(tmp_path))
    content_extractor.main()


def test_unsupported_file_type(monkeypatch, tmp_path):
    import json

    import app.core.paths as core_paths

    monkeypatch.setattr(
        content_extractor, "get_repo_dirs", lambda excluded: [str(tmp_path / "repo1")]
    )
    from app.extraction.utils.file_utils import FileRecord

    monkeypatch.setattr(
        content_extractor,
        "build_file_records",
        lambda *a, **kw: [
            FileRecord(
                id=1,
                repository="repo1",
                path="main.unknown",
                abs_path=str(tmp_path / "main.unknown"),
                filename="main.unknown",
                size_bytes=1,
                extension=".unknown",
                ontology_class="",
                class_uri="",
                creation_timestamp=None,
                modification_timestamp=None,
            )
        ],
    )
    (tmp_path / "content_types.json").write_text(
        json.dumps({"classifiers": [], "ignore_patterns": []})
    )
    (tmp_path / "ontology.owl").write_text(
        """<?xml version='1.0'?><rdf:RDF xmlns:rdf='http://www.w3.org/1999/02/22-rdf-syntax-ns#'></rdf:RDF>"""
    )
    (tmp_path / "excluded.json").write_text("[]")
    (tmp_path / "cache.json").write_text("{}")
    (tmp_path / "out.ttl").write_text("")
    monkeypatch.setattr(
        content_extractor,
        "get_content_types_path",
        lambda: str(tmp_path / "content_types.json"),
    )
    monkeypatch.setattr(
        content_extractor,
        "get_web_dev_ontology_path",
        lambda: str(tmp_path / "ontology.owl"),
    )
    monkeypatch.setattr(
        content_extractor,
        "get_excluded_directories_path",
        lambda: str(tmp_path / "excluded.json"),
    )
    monkeypatch.setattr(
        content_extractor,
        "get_ontology_cache_path",
        lambda: str(tmp_path / "cache.json"),
    )
    monkeypatch.setattr(
        content_extractor, "get_output_path", lambda _: str(tmp_path / "out.ttl")
    )
    monkeypatch.setattr(content_extractor, "get_input_dir", lambda: str(tmp_path))

    class DummyOntology:
        def __init__(self, *args, **kwargs):
            pass

    monkeypatch.setattr(content_extractor, "OntologyWrapper", DummyOntology)
    monkeypatch.setattr(
        content_extractor, "write_ttl_with_progress", lambda *a, **kw: None
    )
    core_paths.set_input_dir(str(tmp_path))
    content_extractor.main()


def test_file_with_unusual_encoding(tmp_path, monkeypatch):
    import json

    import app.core.paths as core_paths

    repo_dir = tmp_path / "repo1"
    repo_dir.mkdir()
    weird_file = repo_dir / "main.py"
    weird_file.write_bytes(b"\xff\xfe\xfd\xfc\xfb")
    from app.extraction.utils.file_utils import FileRecord

    monkeypatch.setattr(
        content_extractor, "get_repo_dirs", lambda excluded: [str(repo_dir)]
    )
    monkeypatch.setattr(
        content_extractor,
        "build_file_records",
        lambda *a, **kw: [
            FileRecord(
                id=1,
                repository="repo1",
                path="main.py",
                abs_path=str(weird_file),
                filename="main.py",
                size_bytes=5,
                extension=".py",
                ontology_class="PythonCode",
                class_uri="http://example.org/PythonCode",
                creation_timestamp=None,
                modification_timestamp=None,
            )
        ],
    )
    (tmp_path / "content_types.json").write_text(
        json.dumps({"classifiers": [], "ignore_patterns": []})
    )
    (tmp_path / "ontology.owl").write_text(
        """<?xml version='1.0'?><rdf:RDF xmlns:rdf='http://www.w3.org/1999/02/22-rdf-syntax-ns#'></rdf:RDF>"""
    )
    (tmp_path / "excluded.json").write_text("[]")
    (tmp_path / "cache.json").write_text("{}")
    (tmp_path / "out.ttl").write_text("")
    monkeypatch.setattr(
        content_extractor,
        "get_content_types_path",
        lambda: str(tmp_path / "content_types.json"),
    )
    monkeypatch.setattr(
        content_extractor,
        "get_web_dev_ontology_path",
        lambda: str(tmp_path / "ontology.owl"),
    )
    monkeypatch.setattr(
        content_extractor,
        "get_excluded_directories_path",
        lambda: str(tmp_path / "excluded.json"),
    )
    monkeypatch.setattr(
        content_extractor,
        "get_ontology_cache_path",
        lambda: str(tmp_path / "cache.json"),
    )
    monkeypatch.setattr(
        content_extractor, "get_output_path", lambda _: str(tmp_path / "out.ttl")
    )
    monkeypatch.setattr(content_extractor, "get_input_dir", lambda: str(tmp_path))

    class DummyOntology:
        def __init__(self, *args, **kwargs):
            pass

    monkeypatch.setattr(content_extractor, "OntologyWrapper", DummyOntology)
    monkeypatch.setattr(
        content_extractor, "write_ttl_with_progress", lambda *a, **kw: None
    )
    core_paths.set_input_dir(str(tmp_path))
    content_extractor.main()
