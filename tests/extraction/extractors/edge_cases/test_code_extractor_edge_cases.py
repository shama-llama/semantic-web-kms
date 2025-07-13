import os
import sys

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../"))
)
from unittest import mock

import pytest

from app.extraction.extractors import code_extractor


def test_empty_input_directory(monkeypatch):
    # Patch file discovery to return no files
    monkeypatch.setattr(
        code_extractor,
        "load_and_discover_files",
        lambda mapping: ([], [], "/tmp", "/tmp/out.ttl"),
    )
    # Patch initialize_context_and_graph to dummy
    from rdflib import Graph

    class DummyCtx:
        pass

    monkeypatch.setattr(
        code_extractor,
        "initialize_context_and_graph",
        lambda ttl_path, INST, WDO, uri_safe_string: (Graph(), {}, {}, DummyCtx()),
    )
    # Patch finalize_and_serialize_graph to do nothing
    monkeypatch.setattr(
        code_extractor, "finalize_and_serialize_graph", lambda ctx: None
    )
    # Patch write_ontology_progress to do nothing
    monkeypatch.setattr(
        code_extractor, "write_ontology_progress", lambda *a, **kw: None
    )
    # Patch extract_ast_entities_progress to do nothing
    monkeypatch.setattr(
        code_extractor, "extract_ast_entities_progress", lambda *a, **kw: None
    )
    # Should not raise
    code_extractor.main()


def test_unsupported_file_type(monkeypatch):
    # Patch file discovery to return a file with unsupported extension
    files = [
        {
            "repository": "repo1",
            "path": "main.unknown",
            "abs_path": "/tmp/main.unknown",
            "extension": ".unknown",
        }
    ]
    monkeypatch.setattr(
        code_extractor,
        "load_and_discover_files",
        lambda mapping: (files, ["/tmp/repo1"], "/tmp", "/tmp/out.ttl"),
    )
    from rdflib import Graph

    class DummyCtx:
        pass

    monkeypatch.setattr(
        code_extractor,
        "initialize_context_and_graph",
        lambda ttl_path, INST, WDO, uri_safe_string, uri_safe_file_path: (
            Graph(),
            {},
            {},
            DummyCtx(),
        ),
    )
    monkeypatch.setattr(
        code_extractor, "finalize_and_serialize_graph", lambda ctx: None
    )
    monkeypatch.setattr(
        code_extractor, "write_ontology_progress", lambda *a, **kw: None
    )
    # Patch extract_ast_entities_progress to do nothing
    monkeypatch.setattr(
        code_extractor, "extract_ast_entities_progress", lambda *a, **kw: None
    )
    # Should not raise
    code_extractor.main()


def test_file_with_unusual_encoding(tmp_path, monkeypatch):
    # Create a file with non-UTF-8 bytes
    repo_dir = tmp_path / "repo1"
    repo_dir.mkdir()
    weird_file = repo_dir / "main.py"
    weird_file.write_bytes(b"\xff\xfe\xfd\xfc\xfb")
    files = [
        {
            "repository": "repo1",
            "path": "main.py",
            "abs_path": str(weird_file),
            "extension": ".py",
        }
    ]
    monkeypatch.setattr(
        code_extractor,
        "load_and_discover_files",
        lambda mapping: (
            files,
            [str(repo_dir)],
            str(tmp_path),
            str(tmp_path / "out.ttl"),
        ),
    )
    from rdflib import Graph

    class DummyCtx:
        pass

    monkeypatch.setattr(
        code_extractor,
        "initialize_context_and_graph",
        lambda ttl_path, INST, WDO, uri_safe_string, uri_safe_file_path: (
            Graph(),
            {},
            {},
            DummyCtx(),
        ),
    )
    monkeypatch.setattr(
        code_extractor, "finalize_and_serialize_graph", lambda ctx: None
    )
    monkeypatch.setattr(
        code_extractor, "write_ontology_progress", lambda *a, **kw: None
    )

    # Patch extract_ast_entities_progress to simulate UnicodeDecodeError
    def fake_extract_ast_entities_progress(
        supported_files, language_mapping, queries, summary_data, progress, extract_task
    ):
        for rec in supported_files:
            summary_data[f"{rec['repository']}/{rec['path']}"] = {
                "errors": ["UnicodeDecodeError"]
            }

    monkeypatch.setattr(
        code_extractor,
        "extract_ast_entities_progress",
        fake_extract_ast_entities_progress,
    )
    # Should not raise
    code_extractor.main()
