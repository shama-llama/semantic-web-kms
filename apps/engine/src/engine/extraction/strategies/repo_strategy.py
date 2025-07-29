
from engine.extraction.context import ExtractionContext
from engine.extraction.models.core import Repository
from engine.extraction.rdf.writers import (
    write_organization,
    write_repository,
)
from engine.extraction.strategies.base import BaseExtractorStrategy


class RepoStrategy(BaseExtractorStrategy):
    """
    Extraction strategy for discovering and serializing organizations and repositories.
    """

    @property
    def name(self) -> str:
        return "Repository & Organization Extractor"

    def extract(self, context: ExtractionContext, progress, task_id):
        input_dir = context.input_dir
        org_name = input_dir.name
        repos = []
        for repo_dir in input_dir.iterdir():
            if not repo_dir.is_dir() or repo_dir.name in getattr(
                context, "excluded_dirs", set()
            ):
                continue
            repo_name = repo_dir.name
            remote_url = None
            repo = Repository(name=repo_name, path=repo_dir, remote_url=remote_url)
            repos.append(repo)
        progress.update(task_id, total=1 + len(repos))
        # Serialize organization
        write_organization(context.graph, org_name)
        progress.advance(task_id)
        # Serialize repositories
        for repo in repos:
            write_repository(context.graph, org_name, repo.name, repo.remote_url)
            context.repositories[f"{org_name}/{repo.name}"] = repo
            progress.advance(task_id)
