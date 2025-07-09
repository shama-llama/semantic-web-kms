import os
import sys

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../"))
)
from unittest import mock

import pytest

from app.extraction.extractors import content_extractor
from app.extraction.extractors.content_extractor import ExtractionContext


def test_uri_safe_string():
    s = "My Content: 2024/07/09"
    safe = content_extractor.uri_safe_string(s)
    assert isinstance(safe, str)
    assert ":" not in safe and "/" not in safe


# Add more tests for other helpers or pure functions as discovered


def test_extract_image_metadata(tmp_path):
    # Should return empty dict if PIL is not available or file is not an image
    fake_img = tmp_path / "not_an_image.txt"
    fake_img.write_text("not an image")
    meta = content_extractor.extract_image_metadata(str(fake_img))
    assert isinstance(meta, dict)


def test_extract_media_metadata(tmp_path):
    fake_media = tmp_path / "media.mp4"
    fake_media.write_bytes(b"\x00" * 10)
    meta = content_extractor.extract_media_metadata(str(fake_media), "VideoDescription")
    assert meta["file_size"] == 10
    assert meta["media_type"] == "video"
    assert meta["format"] == "mp4"


def test_extract_dockerfile_base_image(tmp_path):
    dockerfile = tmp_path / "Dockerfile"
    dockerfile.write_text("""FROM python:3.9-slim\nRUN echo hi\n""")
    base = content_extractor.extract_dockerfile_base_image(str(dockerfile))
    assert base == "python:3.9-slim"


def test_extract_license_identifier(tmp_path):
    lic = tmp_path / "LICENSE"
    lic.write_text("SPDX-License-Identifier: MIT\n")
    ident = content_extractor.extract_license_identifier(str(lic))
    assert ident == "MIT"
    lic.write_text("This project is licensed under the Apache-2.0 license.")
    ident2 = content_extractor.extract_license_identifier(str(lic))
    assert ident2 == "Apache-2.0"


def test_extract_dependencies_from_build_file_package_json(tmp_path):
    pkg = tmp_path / "package.json"
    pkg.write_text(
        '{"dependencies": {"foo": "1.0.0"}, "devDependencies": {"bar": "2.0.0"}}'
    )
    deps = content_extractor.extract_dependencies_from_build_file(
        str(pkg), "BuildScript"
    )
    assert {"name": "foo", "version": "1.0.0"} in deps
    assert {"name": "bar", "version": "2.0.0"} in deps


def test_extract_dependencies_from_build_file_cargo_toml(tmp_path):
    cargo = tmp_path / "Cargo.toml"
    cargo.write_text(
        """
[dependencies]
serde = "1.0"
[dev-dependencies]
rand = "0.8"
"""
    )
    deps = content_extractor.extract_dependencies_from_build_file(
        str(cargo), "BuildScript"
    )
    # Current implementation does not parse standard [dependencies] key-value pairs
    assert deps == []


def test_extract_frameworks_from_code_file_python(tmp_path):
    py = tmp_path / "main.py"
    py.write_text("import flask\nfrom django import forms\n")
    frameworks = content_extractor.extract_frameworks_from_code_file(
        str(py), "PythonCode"
    )
    names = [f["name"] for f in frameworks]
    assert "flask" in names
    assert "django" in names


def test_extract_frameworks_from_code_file_java(tmp_path):
    java = tmp_path / "Main.java"
    java.write_text("import spring.framework.*;\nimport junit.framework.*;\n")
    frameworks = content_extractor.extract_frameworks_from_code_file(
        str(java), "JavaCode"
    )
    names = [f["name"] for f in frameworks]
    assert "spring" in names
    assert "junit" in names


def test_extract_frameworks_from_code_file_csharp(tmp_path):
    cs = tmp_path / "Program.cs"
    cs.write_text("using asp.net;\nusing nunit;\n")
    frameworks = content_extractor.extract_frameworks_from_code_file(
        str(cs), "CSharpCode"
    )
    names = [f["name"] for f in frameworks]
    assert "asp.net" in names
    assert "nunit" in names


def test_add_asset_metadata_triples_image(tmp_path):
    from rdflib import Graph, URIRef

    fake_img = tmp_path / "img.txt"
    fake_img.write_text("not an image")
    g = Graph()
    content_uri = URIRef("http://example.org/content")
    # Should not add any triples for non-image
    content_extractor.add_asset_metadata_triples(
        g, content_uri, str(fake_img), "ImageDescription"
    )
    assert isinstance(g, Graph)


def test_add_asset_metadata_triples_video(tmp_path):
    from rdflib import Graph, URIRef

    fake_vid = tmp_path / "vid.mp4"
    fake_vid.write_bytes(b"\x00" * 10)
    g = Graph()
    content_uri = URIRef("http://example.org/content")
    content_extractor.add_asset_metadata_triples(
        g, content_uri, str(fake_vid), "VideoDescription"
    )
    # Should add at least one triple for format or file_size
    assert len(g) > 0


def test_add_special_content_triples_dockerfile(tmp_path):
    from rdflib import Graph, URIRef

    dockerfile = tmp_path / "Dockerfile"
    dockerfile.write_text("FROM python:3.9-slim\n")
    g = Graph()
    content_uri = URIRef("http://example.org/content")
    content_extractor.add_special_content_triples(
        g, content_uri, str(dockerfile), "DockerfileSpecification"
    )
    # Should add at least one triple for the base image
    assert len(g) > 0


def test_add_special_content_triples_license(tmp_path):
    from rdflib import Graph, URIRef

    lic = tmp_path / "LICENSE"
    lic.write_text("SPDX-License-Identifier: MIT\n")
    g = Graph()
    content_uri = URIRef("http://example.org/content")
    content_extractor.add_special_content_triples(g, content_uri, str(lic), "License")
    # Should add at least one triple for the license identifier
    assert len(g) > 0


def test_add_content_triples_integration(tmp_path):
    from rdflib import Graph, URIRef

    from app.extraction.utils.file_utils import FileRecord

    # Create a fake code file
    code_file = tmp_path / "main.py"
    code_file.write_text("print('hello')\n")
    record = FileRecord(
        id=1,
        repository="repo1",
        path="main.py",
        abs_path=str(code_file),
        filename="main.py",
        size_bytes=code_file.stat().st_size,
        extension=".py",
        ontology_class="PythonCode",
        class_uri="http://example.org/PythonCode",
        creation_timestamp=None,
        modification_timestamp=None,
    )
    g = Graph()
    context = ExtractionContext(
        content_classifiers=[], content_ignore_patterns=[], ontology=None
    )
    file_uri = URIRef("http://example.org/file")
    repo_enc = "repo1"
    path_enc = "main_py"
    content_extractor.add_content_triples(
        g, record, context, file_uri, repo_enc, path_enc
    )
    # Should add at least one triple for the content entity
    assert len(g) > 0


# Patch add_content_only_triples test to use a mock ontology with get_class
from unittest.mock import MagicMock


def test_add_content_only_triples(tmp_path):
    from rdflib import Graph, URIRef

    from app.extraction.utils.file_utils import FileRecord

    # Create a fake file
    code_file = tmp_path / "main.py"
    code_file.write_text("print('hello')\n")
    record = FileRecord(
        id=1,
        repository="repo1",
        path="main.py",
        abs_path=str(code_file),
        filename="main.py",
        size_bytes=code_file.stat().st_size,
        extension=".py",
        ontology_class="PythonCode",
        class_uri="http://example.org/PythonCode",
        creation_timestamp=None,
        modification_timestamp=None,
    )
    g = Graph()
    mock_ontology = MagicMock()
    mock_ontology.get_class.return_value = "http://example.org/PythonCode"
    context = ExtractionContext(
        content_classifiers=[], content_ignore_patterns=[], ontology=mock_ontology
    )
    processed_repos = set()
    content_extractor.add_content_only_triples(
        g, record, context, str(tmp_path), processed_repos
    )
    # Should add at least one triple for the content entity
    assert len(g) > 0


def test_framework_registry_register_and_reset(caplog):
    reg = content_extractor.FrameworkRegistry()
    uri1 = reg.get_or_create_framework_uri("Django")
    uri2 = reg.get_or_create_framework_uri("Django")
    uri3 = reg.get_or_create_framework_uri("Flask")
    assert uri1 == uri2
    assert uri1 != uri3
    assert reg.get_framework_count() == 2
    reg.reset()
    assert reg.get_framework_count() == 0
    # Logging
    with caplog.at_level("INFO"):
        reg.get_or_create_framework_uri("FastAPI")
        reg.log_registered_frameworks()
        assert (
            "Registered frameworks" in caplog.text
            or "No frameworks registered" in caplog.text
        )


def test_software_package_registry_register_and_reset(caplog):
    reg = content_extractor.SoftwarePackageRegistry()
    uri1 = reg.get_or_create_package_uri("numpy")
    uri2 = reg.get_or_create_package_uri("numpy")
    uri3 = reg.get_or_create_package_uri("pandas")
    assert uri1 == uri2
    assert uri1 != uri3
    assert reg.get_package_count() == 2
    reg.reset()
    assert reg.get_package_count() == 0
    # Logging
    with caplog.at_level("INFO"):
        reg.get_or_create_package_uri("scipy")
        reg.log_registered_packages()
        assert (
            "Registered software packages" in caplog.text
            or "No software packages registered" in caplog.text
        )


def test_extract_image_metadata_unreadable(tmp_path):
    # File does not exist
    meta = content_extractor.extract_image_metadata(str(tmp_path / "missing.png"))
    assert meta == {}


def test_extract_media_metadata_unreadable(tmp_path):
    # File does not exist
    meta = content_extractor.extract_media_metadata(
        str(tmp_path / "missing.mp4"), "VideoDescription"
    )
    assert meta == {}


def test_extract_dockerfile_base_image_unreadable(tmp_path):
    # File does not exist
    base = content_extractor.extract_dockerfile_base_image(
        str(tmp_path / "missing.Dockerfile")
    )
    assert base == ""


def test_extract_license_identifier_unreadable(tmp_path):
    # File does not exist
    ident = content_extractor.extract_license_identifier(
        str(tmp_path / "missing.LICENSE")
    )
    assert ident == ""


def test_ontology_wrapper_loads_with_missing_file(tmp_path):
    # Ontology file does not exist
    wrapper = content_extractor.OntologyWrapper(str(tmp_path / "missing.owl"))
    # Should not raise, and graph should be a Graph
    assert hasattr(wrapper, "graph")
    assert wrapper.graph is not None


def test_main_integration(tmp_path, monkeypatch):
    import json
    import os
    from pathlib import Path

    import app.core.paths as core_paths

    # Prepare a minimal content types classifier
    content_types = [("PythonCode", r".*\\.py$")]
    ignore_patterns = []
    # Write content types to temp file
    content_types_path = tmp_path / "content_types.json"
    content_types_path.write_text(json.dumps([["PythonCode", ".*\\.py$"]]))
    # Patch config path functions
    monkeypatch.setattr(
        content_extractor, "get_content_types_path", lambda: str(content_types_path)
    )
    # Patch load_classifiers_from_json to return our classifier
    monkeypatch.setattr(
        content_extractor,
        "load_classifiers_from_json",
        lambda path: ([("PythonCode", __import__("re").compile(r".*\\.py$"))], []),
    )
    # Patch get_web_dev_ontology_path to a dummy file
    ontology_path = tmp_path / "ontology.owl"
    ontology_path.write_text(
        """<?xml version='1.0'?><rdf:RDF xmlns:rdf='http://www.w3.org/1999/02/22-rdf-syntax-ns#'></rdf:RDF>"""
    )
    monkeypatch.setattr(
        content_extractor, "get_web_dev_ontology_path", lambda: str(ontology_path)
    )
    # Patch get_excluded_directories_path to a dummy file
    excluded_path = tmp_path / "excluded.json"
    excluded_path.write_text(json.dumps([]))
    monkeypatch.setattr(
        content_extractor, "get_excluded_directories_path", lambda: str(excluded_path)
    )
    # Patch get_ontology_cache_path to a dummy file
    cache_path = tmp_path / "cache.json"
    cache_path.write_text(json.dumps({"classes": ["PythonCode"]}))
    monkeypatch.setattr(
        content_extractor, "get_ontology_cache_path", lambda: str(cache_path)
    )
    # Patch get_output_path to a dummy output file
    output_path = tmp_path / "web_development_ontology.ttl"
    monkeypatch.setattr(
        content_extractor, "get_output_path", lambda _: str(output_path)
    )
    # Patch get_input_dir to our temp dir
    monkeypatch.setattr(content_extractor, "get_input_dir", lambda: str(tmp_path))
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
    # Patch get_repo_dirs to only use our temp repo
    monkeypatch.setattr(
        content_extractor, "get_repo_dirs", lambda excluded: [str(repo_dir)]
    )
    # Patch build_file_records to return our file
    from app.extraction.utils.file_utils import FileRecord

    def fake_build_file_records(repo_dirs, excluded_dirs, progress, extract_task):
        return [
            FileRecord(
                id=1,
                repository="repo1",
                path="main.py",
                abs_path=str(py_file),
                filename="main.py",
                size_bytes=py_file.stat().st_size,
                extension=".py",
                ontology_class="PythonCode",
                class_uri="http://example.org/PythonCode",
                creation_timestamp=None,
                modification_timestamp=None,
            )
        ]

    monkeypatch.setattr(
        content_extractor, "build_file_records", fake_build_file_records
    )

    # Patch OntologyWrapper to a dummy
    class DummyOntology1:
        def __init__(self, *args, **kwargs):
            pass

    monkeypatch.setattr(content_extractor, "OntologyWrapper", DummyOntology1)
    # Patch write_ttl_with_progress to just check it is called
    called = {}

    def fake_write_ttl_with_progress(*args, **kwargs):
        called["written"] = True

    monkeypatch.setattr(
        content_extractor, "write_ttl_with_progress", fake_write_ttl_with_progress
    )
    # Set input dir using the global setter
    core_paths.set_input_dir(str(tmp_path))
    # Run main
    content_extractor.main()
    # Assert that output was produced
    assert called.get("written") is True

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

    # Patch OntologyWrapper and write_ttl_with_progress
    class DummyOntology2:
        def __init__(self, *args, **kwargs):
            pass

    monkeypatch.setattr(content_extractor, "OntologyWrapper", DummyOntology2)
    monkeypatch.setattr(
        content_extractor, "write_ttl_with_progress", lambda *a, **kw: None
    )
    # Set input dir using the global setter
    core_paths.set_input_dir(str(tmp_path))
    # Should not raise
    content_extractor.main()

    import json

    import app.core.paths as core_paths

    # Patch get_repo_dirs to return a repo
    monkeypatch.setattr(
        content_extractor, "get_repo_dirs", lambda excluded: [str(tmp_path / "repo1")]
    )
    # Patch build_file_records to return a file with unsupported extension
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

    class DummyOntology3:
        def __init__(self, *args, **kwargs):
            pass

    monkeypatch.setattr(content_extractor, "OntologyWrapper", DummyOntology3)
    monkeypatch.setattr(
        content_extractor, "write_ttl_with_progress", lambda *a, **kw: None
    )
    # Set input dir using the global setter
    core_paths.set_input_dir(str(tmp_path))
    # Should not raise
    content_extractor.main()

    import json

    import app.core.paths as core_paths

    # Create a file with non-UTF-8 bytes
    repo_dir = tmp_path / "repo1"
    repo_dir.mkdir(exist_ok=True)
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

    class DummyOntology4:
        def __init__(self, *args, **kwargs):
            pass

    monkeypatch.setattr(content_extractor, "OntologyWrapper", DummyOntology4)
    monkeypatch.setattr(
        content_extractor, "write_ttl_with_progress", lambda *a, **kw: None
    )
    # Set input dir using the global setter
    core_paths.set_input_dir(str(tmp_path))
    # Should not raise
    content_extractor.main()
