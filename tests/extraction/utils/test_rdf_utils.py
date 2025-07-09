import os
import tempfile
from unittest.mock import MagicMock

import pytest
from rdflib import Graph, Literal, URIRef
from rdflib.namespace import XSD

from app.extraction.utils import rdf_utils


class DummyRecord:
    def __init__(
        self,
        repository="repo",
        path="file.py",
        size_bytes=123,
        extension=".py",
        filename="file.py",
        class_uri="http://wdo/File",
        creation_timestamp=None,
        modification_timestamp=None,
    ):
        self.repository = repository
        self.path = path
        self.size_bytes = size_bytes
        self.extension = extension
        self.filename = filename
        self.class_uri = class_uri
        self.creation_timestamp = creation_timestamp
        self.modification_timestamp = modification_timestamp


class DummyExtractor:
    class DummyOntology:
        def get_superclass_chain(self, class_uri):
            return [class_uri, "http://wdo/ParentClass"]

    ontology = DummyOntology()


def test_add_repository_metadata_adds_triples():
    """Test that add_repository_metadata adds expected triples to the graph."""
    g = Graph()
    processed = set()
    repo_enc = "repo"
    repo_name = "repo"
    input_dir = "/tmp/org"
    rdf_utils.add_repository_metadata(g, repo_enc, repo_name, input_dir, processed)
    assert (rdf_utils.INST[repo_enc], rdf_utils.RDF.type, rdf_utils.WDO.Repository) in g
    assert repo_enc in processed


def test_add_superclass_triples_adds_chain():
    """Test that add_superclass_triples adds all superclasses as RDF types."""
    g = Graph()
    file_uri = URIRef("http://inst/file")
    wdo_class_uri = "http://wdo/File"
    extractor = DummyExtractor()
    rdf_utils.add_superclass_triples(g, file_uri, wdo_class_uri, extractor)
    assert (file_uri, rdf_utils.RDF.type, URIRef(wdo_class_uri)) in g
    assert (file_uri, rdf_utils.RDF.type, URIRef("http://wdo/ParentClass")) in g


def test_add_file_metadata_triples_adds_metadata():
    """Test that add_file_metadata_triples adds all file metadata triples."""
    g = Graph()
    file_uri = URIRef("http://inst/file")
    record = DummyRecord()
    rdf_utils.add_file_metadata_triples(g, file_uri, record)
    assert (
        file_uri,
        rdf_utils.WDO.hasRelativePath,
        Literal(record.path, datatype=XSD.string),
    ) in g
    assert (
        file_uri,
        rdf_utils.WDO.hasSizeInBytes,
        Literal(record.size_bytes, datatype=XSD.integer),
    ) in g
    assert (
        file_uri,
        rdf_utils.WDO.hasExtension,
        Literal(record.extension, datatype=XSD.string),
    ) in g
    assert (
        file_uri,
        rdf_utils.RDFS.label,
        Literal(record.filename, datatype=XSD.string),
    ) in g
    # Test with timestamps
    record.creation_timestamp = "2024-01-01T00:00:00"
    record.modification_timestamp = "2024-01-02T00:00:00"
    g2 = Graph()
    rdf_utils.add_file_metadata_triples(g2, file_uri, record)
    assert (
        file_uri,
        rdf_utils.WDO.hasCreationTimestamp,
        Literal(record.creation_timestamp, datatype=XSD.dateTime),
    ) in g2
    assert (
        file_uri,
        rdf_utils.WDO.hasModificationTimestamp,
        Literal(record.modification_timestamp, datatype=XSD.dateTime),
    ) in g2


def test_add_file_triples_adds_file_and_repo():
    """Test that add_file_triples adds file and repository relationship triples."""
    g = Graph()
    record = DummyRecord()
    extractor = DummyExtractor()
    input_dir = "/tmp/org"
    processed = set()
    file_uri, repo_enc, path_enc = rdf_utils.add_file_triples(
        g, record, extractor, input_dir, processed
    )
    assert isinstance(file_uri, URIRef)
    assert isinstance(repo_enc, str)
    assert isinstance(path_enc, str)
    assert (rdf_utils.INST[repo_enc], rdf_utils.WDO.hasFile, file_uri) in g
    assert (file_uri, rdf_utils.WDO.isFileOf, rdf_utils.INST[repo_enc]) in g
    assert repo_enc in processed


def test_write_ttl_with_progress_writes_file(tmp_path):
    """Test that write_ttl_with_progress serializes records to a TTL file."""

    class DummyProgress:
        def __init__(self):
            self.advanced = 0
            self.updated = False
            self.tasks = {"task": MagicMock(total=1)}

        def advance(self, task):
            self.advanced += 1

        def update(self, task, completed=None):
            self.updated = True

    records = [DummyRecord()]
    g = Graph()
    ttl_path = tmp_path / "out.ttl"
    progress = DummyProgress()

    def add_triples(graph, record, *args, **kwargs):
        graph.add(
            (URIRef("http://inst/file"), rdf_utils.RDF.type, URIRef("http://wdo/File"))
        )

    rdf_utils.write_ttl_with_progress(
        records, add_triples, g, str(ttl_path), progress, "task"
    )
    assert ttl_path.exists()
    content = ttl_path.read_text()
    assert "@prefix" in content or "http://wdo/File" in content
    assert progress.advanced == 1
    assert progress.updated
