import os
import sys
from unittest import mock

import pytest
from rdflib import URIRef

from app.extraction.extractors import git_extractor

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../"))
)


# --- URI construction helpers ---
def test_get_repo_uri():
    repo_name = "my-repo"
    uri = git_extractor.get_repo_uri(repo_name)
    assert isinstance(uri, URIRef)
    assert repo_name.replace("/", "_") in str(uri)


def test_get_file_uri():
    repo_name = "repo"
    file_path = "src/main.py"
    uri = git_extractor.get_file_uri(repo_name, file_path)
    assert isinstance(uri, URIRef)
    assert "repo" in str(uri)
    assert "src_main.py" in str(uri)


def test_get_commit_uri():
    repo_name = "repo"
    commit_hash = "abc123"
    uri = git_extractor.get_commit_uri(repo_name, commit_hash)
    assert isinstance(uri, URIRef)
    assert "commit" in str(uri)
    assert commit_hash in str(uri)


def test_get_commit_message_uri():
    repo_name = "repo"
    commit_hash = "abc123"
    uri = git_extractor.get_commit_message_uri(repo_name, commit_hash)
    assert isinstance(uri, URIRef)
    assert "_msg" in str(uri)


def test_get_issue_uri():
    repo_name = "repo"
    issue_id = "42"
    uri = git_extractor.get_issue_uri(repo_name, issue_id)
    assert isinstance(uri, URIRef)
    assert "issue" in str(uri)
    assert issue_id in str(uri)


def test_extract_issue_references():
    msg = "Fixes #123 and closes #456. See also #789."
    refs = git_extractor.extract_issue_references(msg)
    assert set(refs) == {"123", "456", "789"}

    msg2 = "No issues referenced."
    refs2 = git_extractor.extract_issue_references(msg2)
    assert refs2 == []


def test_setup_logging_creates_log_dir_and_file(monkeypatch):
    # Patch os.makedirs and logging.basicConfig to check they are called
    with mock.patch("os.makedirs") as makedirs, mock.patch(
        "logging.basicConfig"
    ) as basicConfig, mock.patch(
        "app.extraction.extractors.git_extractor.get_log_path",
        return_value="/tmp/fakepath/git_extractor.log",
    ):
        git_extractor.setup_logging()
        makedirs.assert_called()
        basicConfig.assert_called()


def test_load_ontology_and_cache_calls_dependencies(monkeypatch):
    # Patch ontology cache and property/class cache methods
    fake_cache = mock.Mock()
    fake_cache.get_property_cache.return_value = {"foo": "bar"}
    fake_cache.get_class_cache.return_value = {"baz": "qux"}
    monkeypatch.setattr(git_extractor, "get_ontology_cache", lambda: fake_cache)
    monkeypatch.setattr(git_extractor, "get_extraction_properties", lambda: ["foo"])
    monkeypatch.setattr(git_extractor, "get_extraction_classes", lambda: ["baz"])
    ontology_cache, prop_cache, class_cache = git_extractor.load_ontology_and_cache()
    assert ontology_cache is fake_cache
    assert prop_cache == {"foo": "bar"}
    assert class_cache == {"baz": "qux"}


def test_scan_repositories_handles_invalid_and_valid(monkeypatch):
    # Patch get_input_dir, os.listdir, os.path.isdir, Repo, and iter_commits
    monkeypatch.setattr(git_extractor, "get_input_dir", lambda: "/tmp/repos")
    monkeypatch.setattr(os, "listdir", lambda d: ["repo1", "repo2"])
    monkeypatch.setattr(os.path, "isdir", lambda p: True)
    fake_commit = mock.Mock()
    fake_commit.hexsha = "abc"
    fake_commit.message = "msg"
    fake_commit.committed_date = 1234567890
    fake_commit.author.name = "author"
    fake_commit.parents = []
    fake_commit.tree.traverse.return_value = []

    class FakeRepo:
        def __init__(self, path):
            if "repo2" in path:
                raise git_extractor.InvalidGitRepositoryError()

        def iter_commits(self):
            return [fake_commit]

    monkeypatch.setattr(git_extractor, "Repo", FakeRepo)
    result = git_extractor.scan_repositories()
    assert "repo_commit_map" in result
    assert result["total_repos"] == 1
    assert result["total_commits"] == 1


def test_extract_commit_data_simple(monkeypatch):
    # Prepare a fake commit object
    fake_commit = mock.Mock()
    fake_commit.hexsha = "abc123"
    fake_commit.message = "Initial commit"
    fake_commit.committed_date = 1234567890
    fake_commit.author.name = "Alice"
    fake_commit.parents = []
    fake_commit.tree.traverse.return_value = [mock.Mock(type="blob", path="file1.py")]
    repo_commit_map = {"repo1": [fake_commit]}

    # Mock progress
    class DummyProgress:
        def advance(self, task):
            self.advanced = True

    progress = DummyProgress()
    # Call the function
    result = git_extractor.extract_commit_data(
        repo_commit_map, "/tmp/repos", progress, overall_task=1
    )
    assert isinstance(result, list)
    assert len(result) == 1
    commit_data = result[0]
    assert commit_data["repo_name"] == "repo1"
    assert commit_data["commit_hash"] == "abc123"
    assert commit_data["commit_message"] == "Initial commit"
    assert commit_data["commit_author"] == "Alice"
    assert commit_data["modified_files"] == ["file1.py"]
    assert commit_data["issue_references"] == []


def test_extract_commit_data_with_parent_and_diff(monkeypatch):
    # Prepare a fake commit with a parent and a diff
    fake_commit = mock.Mock()
    fake_commit.hexsha = "def456"
    fake_commit.message = "Fixes #42"
    fake_commit.committed_date = 1234567891
    fake_commit.author.name = "Bob"
    fake_parent = mock.Mock()
    fake_commit.parents = [fake_parent]
    fake_diff = [mock.Mock(a_path="changed.py")]
    fake_commit.diff.return_value = fake_diff
    fake_commit.tree.traverse.return_value = []
    repo_commit_map = {"repo2": [fake_commit]}

    class DummyProgress:
        def advance(self, task):
            self.advanced = True

    progress = DummyProgress()
    result = git_extractor.extract_commit_data(
        repo_commit_map, "/tmp/repos", progress, overall_task=2
    )
    assert len(result) == 1
    commit_data = result[0]
    assert commit_data["repo_name"] == "repo2"
    assert commit_data["commit_hash"] == "def456"
    assert commit_data["commit_author"] == "Bob"
    assert commit_data["modified_files"] == ["changed.py"]
    assert commit_data["issue_references"] == ["42"]


def test_write_ttl_minimal(monkeypatch):
    # Prepare minimal commit data
    all_commit_data = [
        {
            "repo_name": "repo1",
            "commit_hash": "abc123",
            "commit_message": "Initial commit",
            "commit_timestamp": 1234567890,
            "commit_author": "Alice",
            "modified_files": ["file1.py"],
            "issue_references": ["42"],
        }
    ]
    prop_cache = {
        "hasCommitHash": "hasCommitHash",
        "hasCommitMessage": "hasCommitMessage",
        "isMessageOfCommit": "isMessageOfCommit",
        "hasCommit": "hasCommit",
        "isCommitIn": "isCommitIn",
        "addressesIssue": "addressesIssue",
        "isAddressedBy": "isAddressedBy",
        "fixesIssue": "fixesIssue",
        "isFixedBy": "isFixedBy",
        "modifies": "modifies",
        "isModifiedBy": "isModifiedBy",
        "hasFile": "hasFile",
    }
    class_cache = {
        "Repository": "Repository",
        "Commit": "Commit",
        "CommitMessage": "CommitMessage",
        "InformationContentEntity": "InformationContentEntity",
        "Issue": "Issue",
    }
    g = mock.Mock()
    g.add = mock.Mock()

    class DummyProgress:
        def advance(self, task):
            self.advanced = True

    progress = DummyProgress()
    repos_added, commits_added, issues_added, file_mod_count = git_extractor.write_ttl(
        all_commit_data,
        prop_cache,
        class_cache,
        "/tmp/repos",
        progress,
        ttl_task=1,
        g=g,
    )
    assert repos_added == 1
    assert commits_added == 1
    assert issues_added == 1
    assert file_mod_count == 1
    # Check that add was called
    assert g.add.call_count > 0


def test_write_ttl_multiple_commits(monkeypatch):
    all_commit_data = [
        {
            "repo_name": "repo1",
            "commit_hash": "abc123",
            "commit_message": "Initial commit",
            "commit_timestamp": 1234567890,
            "commit_author": "Alice",
            "modified_files": ["file1.py", "file2.py"],
            "issue_references": [],
        },
        {
            "repo_name": "repo1",
            "commit_hash": "def456",
            "commit_message": "Fixes #99",
            "commit_timestamp": 1234567891,
            "commit_author": "Bob",
            "modified_files": ["file3.py"],
            "issue_references": ["99"],
        },
    ]
    prop_cache = {
        "hasCommitHash": "hasCommitHash",
        "hasCommitMessage": "hasCommitMessage",
        "isMessageOfCommit": "isMessageOfCommit",
        "hasCommit": "hasCommit",
        "isCommitIn": "isCommitIn",
        "addressesIssue": "addressesIssue",
        "isAddressedBy": "isAddressedBy",
        "fixesIssue": "fixesIssue",
        "isFixedBy": "isFixedBy",
        "modifies": "modifies",
        "isModifiedBy": "isModifiedBy",
        "hasFile": "hasFile",
    }
    class_cache = {
        "Repository": "Repository",
        "Commit": "Commit",
        "CommitMessage": "CommitMessage",
        "InformationContentEntity": "InformationContentEntity",
        "Issue": "Issue",
    }
    g = mock.Mock()
    g.add = mock.Mock()

    class DummyProgress:
        def advance(self, task):
            self.advanced = True

    progress = DummyProgress()
    repos_added, commits_added, issues_added, file_mod_count = git_extractor.write_ttl(
        all_commit_data,
        prop_cache,
        class_cache,
        "/tmp/repos",
        progress,
        ttl_task=1,
        g=g,
    )
    assert repos_added == 1
    assert commits_added == 2
    assert issues_added == 1
    assert file_mod_count == 3
    assert g.add.call_count > 0
