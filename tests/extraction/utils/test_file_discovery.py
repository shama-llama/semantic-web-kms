import json
import os
import tempfile
from pathlib import Path
from unittest import mock

from app.core import paths
from app.extraction.utils import file_discovery


def test_discover_supported_files():
    with tempfile.TemporaryDirectory() as tempdir:
        paths.set_input_dir(tempdir)
        repo1 = Path(tempdir) / "repo1"
        repo2 = Path(tempdir) / "repo2"
        repo1.mkdir()
        repo2.mkdir()
        (repo1 / "a.py").write_text("print('a')")
        (repo2 / "b.js").write_text("console.log('b')")
        (repo2 / "c.txt").write_text("not code")
        language_mapping = {".py": "Python", ".js": "JavaScript"}
        files, repos = file_discovery.discover_supported_files(set(), language_mapping)
        assert set(repos) == {"repo1", "repo2"}
        found = {(f["repository"], f["extension"]) for f in files}
        assert ("repo1", ".py") in found
        assert ("repo2", ".js") in found
        assert all(f["extension"] in language_mapping for f in files)


def test_load_excluded_dirs():
    data = [".git", "__pycache__"]
    with tempfile.NamedTemporaryFile(mode="w+", delete=False) as tmp:
        json.dump(data, tmp)
        tmp_path = tmp.name
    try:
        with mock.patch(
            "app.core.paths.get_excluded_directories_path", return_value=tmp_path
        ):
            result = file_discovery.load_excluded_dirs()
            # Check that all expected items are in the result
            assert set(data).issubset(result)
    finally:
        os.remove(tmp_path)


def test_get_input_and_output_paths():
    with tempfile.TemporaryDirectory() as tempdir:
        paths.set_input_dir(tempdir)
        input_dir, ttl_path = file_discovery.get_input_and_output_paths()
        assert str(input_dir) == tempdir
        assert str(ttl_path).endswith("web_development_ontology.ttl")


def test_load_and_discover_files():
    with tempfile.TemporaryDirectory() as tempdir, tempfile.NamedTemporaryFile(
        mode="w+", delete=False
    ) as excl:
        paths.set_input_dir(tempdir)
        # Excluded dirs config
        json.dump([".git"], excl)
        excl_path = excl.name
        # Repo and files
        repo = Path(tempdir) / "repo1"
        repo.mkdir()
        (repo / "a.py").write_text("print('a')")
        language_mapping = {".py": "Python"}
        with mock.patch(
            "app.core.paths.get_excluded_directories_path", return_value=excl_path
        ):
            files, repos, input_dir, ttl_path = file_discovery.load_and_discover_files(
                language_mapping
            )
            assert any(f["extension"] == ".py" for f in files)
            assert "repo1" in repos
            assert str(input_dir) == tempdir
            assert str(ttl_path).endswith("web_development_ontology.ttl")
    os.remove(excl_path)
