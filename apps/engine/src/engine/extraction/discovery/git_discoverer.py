"""Defines the GitDiscoverer class for discovering git repositories and commits."""

import datetime
import re
from pathlib import Path

from git import InvalidGitRepositoryError, Repo

from engine.extraction.models.core import Repository
from engine.extraction.models.git import Commit


def extract_issue_references(message: str) -> list[str]:
    """
    Extract referenced issue numbers from a commit message.
    """
    issue_pattern = r"#(\d+)"
    return re.findall(issue_pattern, message)


class GitDiscoverer:
    """
    Discovers git repositories and their commits in the given root directory.
    """

    def __init__(self, root_dir: Path):
        self.root_dir = root_dir

    def discover(self) -> list[Repository]:
        """
        Discovers all git repositories and their commits.

        Returns:
            List[Repository]: List of discovered Repository models.
        """
        repositories = []
        for repo_dir in self.root_dir.iterdir():
            if not repo_dir.is_dir() or not (repo_dir / ".git").is_dir():
                continue
            repo_name = repo_dir.name
            try:
                repo = Repo(str(repo_dir))
                remote_url = None
                if repo.remotes:
                    try:
                        remote_url = repo.remotes.origin.url
                    except Exception:
                        remote_url = None
                commits = []
                for commit in repo.iter_commits():
                    files_changed = []
                    for parent in commit.parents or []:
                        diff = commit.diff(parent, create_patch=False)
                        for d in diff:
                            file_path = d.b_path if d.b_path else d.a_path
                            if file_path is not None:
                                files_changed.append(Path(file_path))
                    if not commit.parents:
                        for obj in commit.tree.traverse():
                            if (
                                hasattr(obj, "type")
                                and hasattr(obj, "path")
                                and getattr(obj, "type", None) == "blob"
                            ):
                                obj_path = getattr(obj, "path", None)
                                if obj_path is not None:
                                    files_changed.append(Path(obj_path))
                    message = str(commit.message.strip())
                    issue_refs = extract_issue_references(message)
                    # Ensure xsd:dateTime format (with timezone)
                    authored_date = (
                        datetime.datetime.fromtimestamp(
                            commit.authored_date, tz=datetime.UTC
                        )
                        .isoformat()
                        .replace("+00:00", "Z")
                    )
                    committed_date = (
                        datetime.datetime.fromtimestamp(
                            commit.committed_date, tz=datetime.UTC
                        )
                        .isoformat()
                        .replace("+00:00", "Z")
                    )
                    commits.append(
                        Commit(
                            commit_hash=commit.hexsha,
                            message=message,
                            author_name=str(commit.author.name or ""),
                            author_email=str(getattr(commit.author, "email", "") or ""),
                            authored_date=authored_date,
                            committer_name=str(commit.committer.name or ""),
                            committer_email=str(
                                getattr(commit.committer, "email", "") or ""
                            ),
                            committed_date=committed_date,
                            repository_name=repo_name,
                            files_changed=files_changed,
                            issue_references=issue_refs,
                        )
                    )
                repositories.append(
                    Repository(
                        name=repo_name,
                        path=repo_dir.resolve(),
                        remote_url=remote_url,
                        commits=commits,
                    )
                )
            except (InvalidGitRepositoryError, Exception):
                continue
        return repositories
