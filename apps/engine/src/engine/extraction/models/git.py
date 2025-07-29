"""Defines data models for git entities used in the extraction pipeline."""

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Contributor:
    """
    Represents a code contributor (author or committer).

    Attributes:
        name (str): Contributor's name.
        email (str): Contributor's email address.
        commits (List['Commit']): List of commits authored by this contributor.
    """

    name: str
    email: str
    commits: list["Commit"] = field(default_factory=list)


@dataclass
class Commit:
    """
    Represents a git commit.

    Attributes:
        commit_hash (str): The commit hash (SHA).
        message (str): Commit message.
        author_name (str): Name of the author.
        author_email (str): Email of the author.
        authored_date (str): ISO 8601 date when authored.
        committer_name (str): Name of the committer.
        committer_email (str): Email of the committer.
        committed_date (str): ISO 8601 date when committed.
        repository_name (str): Name of the repository this commit belongs to.
        files_changed (List[Path]): List of file paths changed in this commit.
    """

    commit_hash: str
    message: str
    author_name: str
    author_email: str
    authored_date: str
    committer_name: str
    committer_email: str
    committed_date: str
    repository_name: str
    files_changed: list[Path] = field(default_factory=list)
    issue_references: list[str] = field(default_factory=list)
