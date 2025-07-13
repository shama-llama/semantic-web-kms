import os
import sys

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../"))
)
from unittest import mock

import pytest
from rdflib import URIRef

import app.core.paths as core_paths
from app.extraction.extractors import doc_extractor

# Example: test a pure helper function if available
# Replace 'some_helper_function' with actual helper names from doc_extractor


def test_uri_safe_string():
    s = "My Document: 2024/07/09"
    safe = doc_extractor.uri_safe_string(s)
    assert isinstance(safe, str)
    assert ":" not in safe  # Colons should be replaced
    # Note: Forward slashes are now preserved for file paths


# Add more tests for other helpers or pure functions as discovered


def test_get_doc_type_from_json():
    # Should match known doc types from patterns
    assert doc_extractor.get_doc_type_from_json("README.md") == "Readme"
    assert (
        doc_extractor.get_doc_type_from_json("CHANGELOG.txt") == "Changelog"
        or doc_extractor.get_doc_type_from_json("CHANGELOG.txt") == "Documentation"
    )
    # Should fallback to Documentation
    assert doc_extractor.get_doc_type_from_json("randomfile.unknown") == "Documentation"


def test_extract_python_comments():
    code = """
# This is a comment
def foo():
    '''Docstring'''
    pass
"""
    comments = doc_extractor.extract_python_comments(code)
    assert any("comment" in c["raw"] or "Docstring" in c["raw"] for c in comments)


def test_extract_heading_level():
    class DummyToken:
        def __init__(self, type_, tag):
            self.type = type_
            self.tag = tag

    token = DummyToken("heading_open", "h2")
    assert doc_extractor.extract_heading_level(token) == 2
    token2 = DummyToken("heading_open", "hX")
    assert doc_extractor.extract_heading_level(token2) is None
    token3 = DummyToken("not_heading", "h1")
    assert doc_extractor.extract_heading_level(token3) is None


def test_is_helpers():
    assert doc_extractor._is_textual_element("Paragraph")
    assert not doc_extractor._is_textual_element("NotAClass")
    assert doc_extractor._is_heading("Heading")
    assert not doc_extractor._is_heading("Paragraph")
    assert doc_extractor._is_software_code("PythonCode")
    assert not doc_extractor._is_software_code("Paragraph")
    assert doc_extractor._is_documentation("Readme")
    assert not doc_extractor._is_documentation("Paragraph")


def test_parse_markdown():
    md = """
# Heading 1\n\nSome paragraph text.\n\n## Heading 2\n\n- List item 1\n- List item 2\n"""
    root = doc_extractor.parse_markdown(md)
    # The root should have children (heading, paragraph, heading, list)
    assert root.type == "document"
    assert any(child.type == "heading_open" for child in root.children)
    assert any(child.type == "paragraph_open" for child in root.children)
    assert any(child.type == "bullet_list_open" for child in root.children)


def test_extract_code_comments():
    code = """
# Top-level comment
def foo():
    '''Docstring'''
    pass
"""
    comments = doc_extractor.extract_code_comments(code, ".py")
    assert any("comment" in c["raw"] or "Docstring" in c["raw"] for c in comments)


def test_add_triples_from_markdown(monkeypatch):
    from rdflib import Graph, URIRef

    from app.extraction.extractors.doc_extractor import (
        DocExtractionContext,
        MarkdownElement,
    )

    class_cache = {
        "Heading": URIRef("http://example.org/Heading"),
        "Paragraph": URIRef("http://example.org/Paragraph"),
    }
    prop_cache = {
        "hasDocumentComponent": URIRef("http://example.org/hasDocumentComponent"),
        "isDocumentComponentOf": URIRef("http://example.org/isDocumentComponentOf"),
        "startsAtLine": URIRef("http://example.org/startsAtLine"),
        "hasHeadingLevel": URIRef("http://example.org/hasHeadingLevel"),
        "hasTextValue": URIRef("http://example.org/hasTextValue"),
    }
    context = DocExtractionContext(
        ontology=None,
        ontology_cache=None,
        class_cache=class_cache,
        prop_cache=prop_cache,
        excluded_dirs=set(),
        input_dir="",
        ttl_path="",
        log_path="",
        console=None,
    )
    g = Graph()
    parent_uri = URIRef("http://example.org/parent")
    file_enc = "file"
    heading = MarkdownElement(
        type="heading_open",
        children=[],
        content=None,
        start_line=1,
        end_line=2,
        level=1,
        token_index=0,
        tag="h1",
    )
    para = MarkdownElement(
        type="paragraph_open",
        children=[],
        content=None,
        start_line=3,
        end_line=4,
        token_index=1,
        tag="p",
    )
    root = MarkdownElement(type="document", children=[heading, para])
    doc_extractor.add_triples_from_markdown(
        root, g, context, parent_uri, file_enc, "repo1"
    )
    assert len(g) > 0


def test_handle_special_doc_types(monkeypatch):
    # Patch the special parsing functions to just record calls
    called = {}
    monkeypatch.setattr(
        doc_extractor,
        "parse_api_documentation",
        lambda text, doc_uri, g, prop_cache: called.setdefault("api", True),
    )
    monkeypatch.setattr(
        doc_extractor,
        "parse_adr_documentation",
        lambda text, doc_uri, g, prop_cache, class_cache: called.setdefault(
            "adr", True
        ),
    )
    monkeypatch.setattr(
        doc_extractor,
        "parse_guideline_documentation",
        lambda text, doc_uri, g, prop_cache, class_cache: called.setdefault(
            "guideline", True
        ),
    )

    class DummyContext:
        def __init__(self):
            self.class_cache = {
                "APIDocumentation": "api_class",
                "ArchitecturalDecisionRecord": "adr_class",
                "BestPracticeGuideline": "guideline_class",
            }
            self.prop_cache = {}

    context = DummyContext()
    g = object()
    doc_uri = object()
    # Test API branch
    doc_extractor.handle_special_doc_types("api_class", "text", doc_uri, g, context)
    assert called.get("api")
    # Test ADR branch
    called.clear()
    doc_extractor.handle_special_doc_types("adr_class", "text", doc_uri, g, context)
    assert called.get("adr")
    # Test Guideline branch
    called.clear()
    doc_extractor.handle_special_doc_types(
        "guideline_class", "text", doc_uri, g, context
    )
    assert called.get("guideline")


def test_process_doc_files_with_context_integration(tmp_path):
    from rdflib import Graph, URIRef

    from app.extraction.extractors.doc_extractor import (
        DocExtractionContext,
        MarkdownElement,
    )
    from app.extraction.utils.file_utils import FileRecord

    # Create a temporary markdown file
    md_content = """# Title\n\nSome text."""
    md_file = tmp_path / "README.md"
    md_file.write_text(md_content)
    # Minimal FileRecord
    file_rec = FileRecord(
        id=1,
        repository="repo1",
        path="README.md",
        abs_path=str(md_file),
        filename="README.md",
        size_bytes=md_file.stat().st_size,
        extension=".md",
        ontology_class="",
        class_uri="",
        creation_timestamp=None,
        modification_timestamp=None,
    )
    # Minimal context
    from app.extraction.extractors import doc_extractor

    class_cache = {
        "Heading": URIRef("http://example.org/Heading"),
        "Documentation": URIRef("http://example.org/Documentation"),
        "DocumentationFile": URIRef("http://example.org/DocumentationFile"),
    }
    prop_cache = {
        "hasDocumentComponent": URIRef("http://example.org/hasDocumentComponent"),
        "isDocumentComponentOf": URIRef("http://example.org/isDocumentComponentOf"),
        "startsAtLine": URIRef("http://example.org/startsAtLine"),
        "hasHeadingLevel": URIRef("http://example.org/hasHeadingLevel"),
        "hasTextValue": URIRef("http://example.org/hasTextValue"),
        "bearerOfInformation": URIRef("http://example.org/bearerOfInformation"),
        "informationBorneBy": URIRef("http://example.org/informationBorneBy"),
        "hasSimpleName": URIRef("http://example.org/hasSimpleName"),
    }
    context = DocExtractionContext(
        ontology=None,
        ontology_cache=None,
        class_cache=class_cache,
        prop_cache=prop_cache,
        excluded_dirs=set(),
        input_dir=str(tmp_path),
        ttl_path=str(tmp_path / "out.ttl"),
        log_path=str(tmp_path / "log.txt"),
        console=None,
    )
    g = Graph()
    # Run the function
    progress = list(
        doc_extractor.process_doc_files_with_context([file_rec], g, context)
    )
    # Should yield once per file
    assert progress == [1]
    # Should add at least one triple
    assert len(g) > 0


def test_main_integration(tmp_path, monkeypatch):
    import json
    import os
    from pathlib import Path

    # Patch get_web_dev_ontology_path to a dummy file
    ontology_path = tmp_path / "ontology.owl"
    ontology_path.write_text("")
    monkeypatch.setattr(
        doc_extractor, "get_web_dev_ontology_path", lambda: str(ontology_path)
    )
    # Patch get_excluded_directories_path to a dummy file
    excluded_path = tmp_path / "excluded.json"
    excluded_path.write_text(json.dumps([]))
    monkeypatch.setattr(
        doc_extractor, "get_excluded_directories_path", lambda: str(excluded_path)
    )
    # Patch get_output_path to a dummy output file
    output_path = tmp_path / "wdkb.ttl"
    monkeypatch.setattr(doc_extractor, "get_output_path", lambda _: str(output_path))
    # Patch get_log_path to a dummy log file
    log_path = tmp_path / "log.txt"
    monkeypatch.setattr(doc_extractor, "get_log_path", lambda *a, **kw: str(log_path))
    # Create a sample markdown file in a repo dir
    repo_dir = tmp_path / "repo1"
    repo_dir.mkdir()
    md_file = repo_dir / "README.md"
    md_file.write_text("""# Title\n\nSome text.""")
    # Patch get_repo_dirs to only use our temp repo
    monkeypatch.setattr(
        doc_extractor, "get_repo_dirs", lambda excluded: [str(repo_dir)]
    )
    # Patch build_file_records to return our file
    from app.extraction.utils.file_utils import FileRecord

    def fake_build_file_records(repo_dirs, excluded_dirs, progress, extract_task):
        return [
            FileRecord(
                id=1,
                repository="repo1",
                path="README.md",
                abs_path=str(md_file),
                filename="README.md",
                size_bytes=md_file.stat().st_size,
                extension=".md",
                ontology_class="DocumentationFile",
                class_uri="http://example.org/DocumentationFile",
                creation_timestamp=None,
                modification_timestamp=None,
            )
        ]

    monkeypatch.setattr(doc_extractor, "build_file_records", fake_build_file_records)

    # Patch WDOOntology and get_ontology_cache to dummies
    class DummyOntology:
        def __init__(self, *args, **kwargs):
            pass

        def get_class(self, k):
            return URIRef(f"http://example.org/{k}")

    class DummyCache:
        def get_property_cache(self, props):
            return {
                "bearerOfInformation": URIRef("http://example.org/bearerOfInformation"),
                "informationBorneBy": URIRef("http://example.org/informationBorneBy"),
                "hasSimpleName": URIRef("http://example.org/hasSimpleName"),
            }

    monkeypatch.setattr(doc_extractor, "WDOOntology", DummyOntology)
    monkeypatch.setattr(doc_extractor, "get_ontology_cache", lambda: DummyCache())
    # Patch write_ttl_with_progress to just check it is called
    called = {}

    def fake_write_ttl_with_progress(*args, **kwargs):
        called["written"] = True

    monkeypatch.setattr(
        doc_extractor, "write_ttl_with_progress", fake_write_ttl_with_progress
    )
    # Set input directory
    core_paths.set_input_dir(str(tmp_path))
    # Run main
    doc_extractor.main()
    # Assert that output was produced
    assert called.get("written") is True
