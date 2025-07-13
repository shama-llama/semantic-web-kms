import os
import sys

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../"))
)
from unittest import mock

import pytest

from app.extraction.extractors import code_extractor

# Example: test a pure helper function if available
# Replace 'some_helper_function' with actual helper names from code_extractor


def test_uri_safe_string():
    s = "My Code: 2024/07/09"
    safe = code_extractor.uri_safe_string(s)
    assert isinstance(safe, str)
    assert ":" not in safe  # Colons should be replaced
    # Note: Forward slashes are now preserved for file paths


# Add more tests for other helpers or pure functions as discovered


def test_extract_type_relationships():
    summary = {
        "variables": [
            {"name": "x", "type": "int", "start_line": 1},
            {"name": "y", "type": "str", "start_line": 2},
        ],
        "functions": [
            {
                "name": "foo",
                "parameters": [{"name": "a", "type": "int"}],
                "returns": "str",
                "start_line": 3,
            },
        ],
        "classes": [
            {
                "name": "Bar",
                "fields": [{"name": "f", "type": "float"}],
                "start_line": 4,
            },
        ],
    }
    code_extractor.extract_type_relationships(summary)
    rels = summary["type_relationships"]
    assert any(r["construct"] == "x" and r["type"] == "int" for r in rels)
    assert any(r["construct"] == "foo.a" and r["type"] == "int" for r in rels)
    assert any(r["construct"] == "foo" and r["type"] == "str" for r in rels)
    assert any(r["construct"] == "Bar.f" and r["type"] == "float" for r in rels)


def test_extract_access_relationships():
    summary = {
        "functions": [
            {
                "name": "foo",
                "raw": "self.x = 1",
                "parent_class": "Bar",
                "start_line": 1,
                "variables": [{"name": "v"}],
            },
        ]
    }
    code_extractor.extract_access_relationships(summary)
    rels = summary["access_relationships"]
    assert any(r["function"] == "foo" and r["attribute"] == "x" for r in rels)
    assert any(r["function"] == "foo" and r["attribute"] == "v" for r in rels)


def test_main_integration(tmp_path, monkeypatch):
    import json
    import os
    from pathlib import Path

    # Prepare a minimal language mapping and queries
    lang_map = {".py": "python"}
    queries = {"python": {}}
    # Write language mapping and queries to temp files
    lang_map_path = tmp_path / "language_mapping.json"
    queries_path = tmp_path / "code_queries.json"
    lang_map_path.write_text(json.dumps(lang_map))
    queries_path.write_text(json.dumps(queries))
    # Patch config path functions
    monkeypatch.setattr(
        code_extractor, "get_language_mapping_path", lambda: str(lang_map_path)
    )
    monkeypatch.setattr(
        code_extractor, "get_code_queries_path", lambda: str(queries_path)
    )
    # Create a sample Python file in a repo dir
    repo_dir = tmp_path / "repo1"
    repo_dir.mkdir(exist_ok=True)
    py_file = repo_dir / "main.py"
    py_file.write_text(
        """
def foo(x):
    return x + 1
"""
    )
    # Patch file discovery to only use our temp repo
    monkeypatch.setattr(
        code_extractor,
        "load_and_discover_files",
        lambda mapping: (
            [
                {
                    "repository": "repo1",
                    "path": "main.py",
                    "abs_path": str(py_file),
                    "extension": ".py",
                }
            ],
            [str(repo_dir)],
            str(tmp_path),
            str(tmp_path / "out.ttl"),
        ),
    )
    # Patch initialize_context_and_graph to use a dummy graph/context
    from rdflib import Graph

    class DummyCtx1:
        pass

    monkeypatch.setattr(
        code_extractor,
        "initialize_context_and_graph",
        lambda ttl_path, INST, WDO, uri_safe_string, uri_safe_file_path: (
            Graph(),
            {},
            {},
            DummyCtx1(),
        ),
    )
    # Patch finalize_and_serialize_graph to do nothing
    monkeypatch.setattr(
        code_extractor, "finalize_and_serialize_graph", lambda ctx: None
    )
    # Patch write_ontology_progress to just check it is called with expected files
    called = {}

    def fake_write_ontology_progress(
        ctx, supported_files, summary_data, language_mapping, progress, ttl_task
    ):
        called["files"] = supported_files

    monkeypatch.setattr(
        code_extractor, "write_ontology_progress", fake_write_ontology_progress
    )

    # Patch extract_ast_entities_progress to simulate extraction
    def fake_extract_ast_entities_progress1(
        supported_files, language_mapping, queries, summary_data, progress, extract_task
    ):
        for rec in supported_files:
            summary_data[f"{rec['repository']}/{rec['path']}"] = {"entities": ["foo"]}

    monkeypatch.setattr(
        code_extractor,
        "extract_ast_entities_progress",
        fake_extract_ast_entities_progress1,
    )
    # Run main
    code_extractor.main()
    # Assert that our file was processed
    assert (
        called["files"][0]["filename"]
        if "filename" in called["files"][0]
        else called["files"][0]["path"] == "main.py"
    )

    # Patch file discovery to return no files
    monkeypatch.setattr(
        code_extractor,
        "load_and_discover_files",
        lambda mapping: ([], [], "/tmp", "/tmp/out.ttl"),
    )
    # Patch initialize_context_and_graph to dummy
    from rdflib import Graph

    class DummyCtx2:
        pass

    monkeypatch.setattr(
        code_extractor,
        "initialize_context_and_graph",
        lambda ttl_path, INST, WDO, uri_safe_string, uri_safe_file_path: (
            Graph(),
            {},
            {},
            DummyCtx2(),
        ),
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

    class DummyCtx3:
        pass

    monkeypatch.setattr(
        code_extractor,
        "initialize_context_and_graph",
        lambda ttl_path, INST, WDO, uri_safe_string, uri_safe_file_path: (
            Graph(),
            {},
            {},
            DummyCtx3(),
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

    # Create a file with non-UTF-8 bytes
    repo_dir = tmp_path / "repo1"
    repo_dir.mkdir(exist_ok=True)
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

    class DummyCtx4:
        pass

    monkeypatch.setattr(
        code_extractor,
        "initialize_context_and_graph",
        lambda ttl_path, INST, WDO, uri_safe_string, uri_safe_file_path: (
            Graph(),
            {},
            {},
            DummyCtx4(),
        ),
    )
    monkeypatch.setattr(
        code_extractor, "finalize_and_serialize_graph", lambda ctx: None
    )
    monkeypatch.setattr(
        code_extractor, "write_ontology_progress", lambda *a, **kw: None
    )

    # Patch extract_ast_entities_progress to simulate UnicodeDecodeError
    def fake_extract_ast_entities_progress2(
        supported_files, language_mapping, queries, summary_data, progress, extract_task
    ):
        for rec in supported_files:
            summary_data[f"{rec['repository']}/{rec['path']}"] = {
                "errors": ["UnicodeDecodeError"]
            }

    monkeypatch.setattr(
        code_extractor,
        "extract_ast_entities_progress",
        fake_extract_ast_entities_progress2,
    )
    # Should not raise
    code_extractor.main()
