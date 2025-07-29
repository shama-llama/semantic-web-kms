"""Stub for the FileStrategy extraction strategy."""

import logging

from engine.core.paths import get_carrier_types
from engine.extraction.context import ExtractionContext
from engine.extraction.discovery.file_discoverer import FileDiscoverer
from engine.extraction.strategies.base import BaseExtractorStrategy
from engine.extraction.utils.classification_utils import (
    classify_file,
    load_classifiers_from_dict,
)
from engine.ontology.wdo import WDOOntology

logger = logging.getLogger("FileStrategy")


class FileStrategy(BaseExtractorStrategy):
    """
    Extraction strategy for discovering and modeling DigitalInformationCarrier files.
    Handles file metadata (size, path, timestamps) and DigitalInformationCarrier classification.
    """

    @property
    def name(self) -> str:
        return "File Extractor"

    def extract(self, context: ExtractionContext, progress, task_id):
        """
        Discovers files using FileDiscoverer and populates context.files with DigitalInformationCarrier classification.
        Uses incremental serialization and batch processing to prevent memory buildup.

        Args:
            context (ExtractionContext): The shared pipeline context.
            progress: The rich progress bar instance.
            task_id: The ID of the task for this strategy.
        """
        excluded_dirs = getattr(context, "excluded_dirs", set())
        discoverer = FileDiscoverer(context.input_dir, excluded_dirs)
        # Use carrier_types.json for DigitalInformationCarrier classification
        carrier_types_data = get_carrier_types()
        classifiers, ignore_patterns = load_classifiers_from_dict(carrier_types_data)
        ontology = WDOOntology()

        # Discover files
        files = discoverer.discover()
        progress.update(task_id, total=len(files))

        # Process files in batches
        batch_size = getattr(context, "batch_size", 500)

        def process_file_batch(batch_files, progress, task_id):
            """Process a batch of files."""
            from engine.extraction.rdf.serializer import RdfSerializer

            serializer = RdfSerializer(context)

            for file in batch_files:
                # Classify the file as DigitalInformationCarrier
                class_name, class_uri, _ = classify_file(
                    file.path.name,
                    classifiers,
                    ignore_patterns,
                    ontology,
                    default_class="DigitalInformationCarrier",
                )

                # Update file with ontology classification
                file.ontology_class = class_name
                file.class_uri = class_uri

                # Serialize file immediately instead of storing in memory
                serializer.serialize(file)

        # Use batch processing from pipeline
        pipeline = getattr(context, "_pipeline", None)

        if pipeline and hasattr(pipeline, "process_batch"):
            pipeline.process_batch(
                files, process_file_batch, progress, task_id, "files"
            )
        else:
            # Fallback to processing all files at once
            process_file_batch(files, progress, task_id)

        from engine.core.paths import get_language_mapping
        language_mapping = get_language_mapping()

        # Store only essential file metadata in context (not full file objects)
        file_metadata = [
            {
                "path": str(f.path),
                "relative_path": str(f.relative_path),
                "organization_name": f.organization_name,
                "repository_name": f.repository_name,
                "extension": f.extension,
                "language": language_mapping.get(f.extension),
                "ontology_class": f.ontology_class,
                "class_uri": f.class_uri,
            }
            for f in files
        ]

        # Use thread-safe method to store minimal file metadata
        with context._lock:
            context.file_metadata = file_metadata
