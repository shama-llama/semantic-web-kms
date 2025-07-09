import os
import shutil
import tempfile
from unittest import mock

from app.core import paths
from app.extraction.utils import file_utils


def test_make_file_record():
    record = file_utils.make_file_record(
        file_id=1,
        repo="repo1",
        rel_path="foo/bar.py",
        abs_path="/tmp/foo/bar.py",
        fname="bar.py",
        size_bytes=123,
        extension=".py",
        ontology_class="Class",
        class_uri="http://example.org/Class",
        creation_timestamp="2024-01-01T00:00:00Z",
        modification_timestamp="2024-01-02T00:00:00Z",
    )
    assert record["id"] == 1
    assert record["repository"] == "repo1"
    assert record["filename"] == "bar.py"
    assert record["extension"] == ".py"
    assert record["size_bytes"] == 123
    assert record["ontology_class"] == "Class"
    assert record["class_uri"] == "http://example.org/Class"
    assert record["creation_timestamp"] == "2024-01-01T00:00:00Z"
    assert record["modification_timestamp"] == "2024-01-02T00:00:00Z"


def test_read_code_bytes():
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp.write(b"abc123")
        tmp_path = tmp.name
    try:
        data = file_utils.read_code_bytes(tmp_path)
        assert data == b"abc123"
        assert file_utils.read_code_bytes("/nonexistent/file") is None
    finally:
        os.remove(tmp_path)


def test_get_repo_dirs_and_count_total_files_and_get_repo_file_map():
    with tempfile.TemporaryDirectory() as tempdir:
        repo1 = os.path.join(tempdir, "repo1")
        repo2 = os.path.join(tempdir, "repo2")
        os.makedirs(repo1)
        os.makedirs(repo2)
        # Create files
        with open(os.path.join(repo1, "a.py"), "w") as f:
            f.write("print('a')")
        with open(os.path.join(repo2, "b.py"), "w") as f:
            f.write("print('b')")
        paths.set_input_dir(tempdir)
        dirs = file_utils.get_repo_dirs(set())
        assert set(dirs) == {"repo1", "repo2"}
        total = file_utils.count_total_files(["repo1", "repo2"], set())
        assert total == 2
        fmap = file_utils.get_repo_file_map(set())
        assert "repo1" in fmap and "repo2" in fmap
        assert any("a.py" in t for t in fmap["repo1"])
        assert any("b.py" in t for t in fmap["repo2"])
