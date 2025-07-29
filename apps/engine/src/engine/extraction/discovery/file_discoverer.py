"""Defines the FileDiscoverer class for discovering files in the source directory."""

import datetime
from pathlib import Path

from engine.extraction.models.core import File, LazyFileContent

CONTENT_CONFIG_PATH = "src/engine/config/content_types.json"


class FileDiscoverer:
    """
    Discovers files in the given root directory, excluding specified directories, and classifies them using ontology mapping.
    Uses lazy loading for file content to reduce memory usage.
    """

    def __init__(self, root_dir: Path, excluded_dirs: set[str]):
        self.root_dir = root_dir
        self.excluded_dirs = excluded_dirs

    def discover(self) -> list[File]:
        """
        Discovers all files, creates File models with lazy content loading.

        Returns:
            List[File]: List of discovered File models with lazy content loading.
        """
        file_models = []
        org_name = self.root_dir.name
        for repo_dir in self.root_dir.iterdir():
            if not repo_dir.is_dir() or repo_dir.name in self.excluded_dirs:
                continue
            repo_name = repo_dir.name
            for file_path in repo_dir.rglob("*"):
                if file_path.is_dir():
                    if file_path.name in self.excluded_dirs:
                        continue
                    else:
                        continue
                for parent in file_path.parents:
                    if parent.name in self.excluded_dirs:
                        break
                else:
                    lazy_content = LazyFileContent(file_path)
                    try:
                        stat = file_path.stat()
                        size_bytes = stat.st_size
                        modification_timestamp = (
                            datetime.datetime.fromtimestamp(
                                stat.st_mtime, tz=datetime.UTC
                            )
                            .isoformat()
                            .replace("+00:00", "Z")
                        )
                        try:
                            creation_timestamp = (
                                datetime.datetime.fromtimestamp(
                                    stat.st_ctime, tz=datetime.UTC
                                )
                                .isoformat()
                                .replace("+00:00", "Z")
                            )
                        except AttributeError:
                            creation_timestamp = (
                                datetime.datetime.fromtimestamp(
                                    stat.st_ctime, tz=datetime.UTC
                                )
                                .isoformat()
                                .replace("+00:00", "Z")
                            )
                    except Exception:
                        size_bytes = 0
                        creation_timestamp = ""
                        modification_timestamp = ""
                    extension = file_path.suffix
                    relative_path = file_path.relative_to(repo_dir)
                    file_model = File(
                        path=file_path,
                        relative_path=relative_path,
                        organization_name=org_name,
                        repository_name=repo_name,
                        content_bytes=lazy_content,
                        extension=extension,
                        size_bytes=size_bytes,
                        creation_timestamp=creation_timestamp,
                        modification_timestamp=modification_timestamp,
                        ontology_class="",
                        class_uri="",
                    )
                    file_models.append(file_model)
        return file_models
