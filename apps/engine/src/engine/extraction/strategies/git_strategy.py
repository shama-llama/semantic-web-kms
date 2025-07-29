"""Stub for the GitStrategy extraction strategy."""

from engine.extraction.context import ExtractionContext
from engine.extraction.discovery.git_discoverer import GitDiscoverer
from engine.extraction.strategies.base import BaseExtractorStrategy


class GitStrategy(BaseExtractorStrategy):
    """
    Extraction strategy for discovering and modeling git commits and contributors.
    """

    @property
    def name(self) -> str:
        return "Git Commit and Contributor Extractor"

    def extract(self, context: ExtractionContext, progress, task_id):
        """
        Discovers git repositories and commits using GitDiscoverer and populates context.repositories and context.commits.
        Uses incremental serialization and batch processing to prevent memory buildup.

        Args:
            context (ExtractionContext): The shared pipeline context.
            progress: The rich progress bar instance.
            task_id: The ID of the task for this strategy.
        """
        discoverer = GitDiscoverer(context.input_dir)
        repositories = discoverer.discover()

        # Use thread-safe methods to update context
        for repo in repositories:
            context.add_repository(repo.name, repo)

        # Collect all commits for batch processing
        all_commits = []
        for repo in repositories:
            all_commits.extend(repo.commits)

        progress.update(task_id, total=len(all_commits))

        # Process commits in batches
        batch_size = getattr(context, "batch_size", 500)

        def process_commit_batch(batch_commits, progress, task_id):
            """Process a batch of commits."""
            from engine.extraction.rdf.serializer import RdfSerializer

            serializer = RdfSerializer(context)

            for commit in batch_commits:
                # Serialize immediately instead of storing in memory
                serializer.serialize(commit)

        # Use batch processing from pipeline
        pipeline = getattr(context, "_pipeline", None)

        if pipeline and hasattr(pipeline, "process_batch"):
            pipeline.process_batch(
                all_commits, process_commit_batch, progress, task_id, "commits"
            )
        else:
            # Fallback to processing all commits at once
            process_commit_batch(all_commits, progress, task_id)

        # Store only essential metadata, not full commit objects
        context.add_commits([])  # Clear commits after serialization
