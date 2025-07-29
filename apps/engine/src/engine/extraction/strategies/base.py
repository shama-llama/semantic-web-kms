"""Defines the abstract base class for all extraction strategies in the pipeline."""

from abc import ABC, abstractmethod

from engine.extraction.context import ExtractionContext


class BaseExtractorStrategy(ABC):
    """
    Abstract base class for all extraction strategies.

    Each strategy implements a specific extraction concern (e.g., code, git, content).
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """
        Returns a human-readable name for the extractor (e.g., 'Git Commit Extractor').
        """

    @abstractmethod
    def extract(self, context: ExtractionContext, progress, task_id):
        """
        Executes the extraction logic for this strategy.
        This method should discover items, parse them, model them, and
        request their serialization, updating the shared context as needed.

        Args:
            context (ExtractionContext): The shared pipeline context.
            progress: The rich progress bar instance.
            task_id: The ID of the task for this strategy.
        """
