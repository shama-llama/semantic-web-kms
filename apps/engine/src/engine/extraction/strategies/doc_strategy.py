import logging
from pathlib import Path

from engine.extraction.context import ExtractionContext
from engine.extraction.models.doc import CodeComment
from engine.extraction.parsers.comment_parser import CommentParser
from engine.extraction.parsers.specialized_doc_parser import SpecializedDocParser
from engine.extraction.strategies.base import BaseExtractorStrategy

# Documentation-related ontology classes (should match those in content_types.json)
DOC_CLASSES = {
    "Documentation",
    "Readme",
    "UserGuide",
    "Tutorial",
    "APIDocumentation",
    "Changelog",
    "ContributionGuide",
    "ArchitecturalDecisionRecord",
    "BestPracticeGuideline",
}

logger = logging.getLogger("DocStrategy")


class DocStrategy(BaseExtractorStrategy):
    """
    Extraction strategy for discovering and modeling documentation entities (documents, headings, etc.).
    """

    @property
    def name(self) -> str:
        return "Documentation Extractor"

    def extract(self, context: ExtractionContext, progress, task_id):
        """
        Processes files to extract documentation and code comments.
        Uses incremental serialization and batch processing to prevent memory buildup.

        Args:
            context (ExtractionContext): The shared pipeline context.
            progress: The rich progress bar instance.
            task_id: The ID of the task for this strategy.
        """
        # Get file metadata instead of full file objects
        file_metadata = getattr(context, "file_metadata", [])
        doc_files = [
            f
            for f in file_metadata
            if f["ontology_class"] in DOC_CLASSES
            or f["extension"] in {".md", ".markdown", ".rst", ".txt", ".adoc"}
        ]

        progress.update(task_id, total=len(doc_files))

        # Load parsers
        comment_parser = CommentParser()
        specialized_parser = SpecializedDocParser()

        # Process documentation files in batches
        batch_size = getattr(context, "batch_size", 500)

        def process_doc_batch(batch_files, progress, task_id):
            """Process a batch of documentation files."""
            from engine.extraction.rdf.serializer import RdfSerializer

            serializer = RdfSerializer(context)

            for file_meta in batch_files:
                try:
                    file_path = Path(file_meta["path"])
                    # Use lazy loading if available, otherwise fallback to direct read
                    if hasattr(file_meta, "get_content"):
                        content_bytes = file_meta.get_content()
                    else:
                        with open(file_path, "rb") as f:
                            content_bytes = f.read()
                    content = content_bytes.decode("utf-8", errors="ignore")

                    # Check if this is a documentation file
                    if file_meta["ontology_class"] in DOC_CLASSES:
                        doc_uri = f"doc:{file_path.stem}"

                        # Parse specialized documentation types
                        from rdflib import URIRef

                        doc_uri_ref = URIRef(doc_uri)
                        if file_meta["ontology_class"] == "APIDocumentation":
                            specialized_parser.parse_api_documentation(
                                content, doc_uri_ref, context.graph, context.prop_cache
                            )
                        elif (
                            file_meta["ontology_class"] == "ArchitecturalDecisionRecord"
                        ):
                            specialized_parser.parse_adr_documentation(
                                content,
                                doc_uri_ref,
                                context.graph,
                                context.prop_cache,
                                context.class_cache,
                            )
                        elif file_meta["ontology_class"] == "BestPracticeGuideline":
                            specialized_parser.parse_guideline_documentation(
                                content,
                                doc_uri_ref,
                                context.graph,
                                context.prop_cache,
                                context.class_cache,
                            )
                    else:
                        # Not a documentation file, but may be code: extract comments
                        comments = comment_parser.extract_comments(
                            content, file_meta["extension"]
                        )
                        for comment in comments:
                            doc_comment = CodeComment(
                                file_path=str(file_path),
                                comment=comment["raw"],
                                start_line=comment["start_line"],
                                end_line=comment["end_line"],
                            )
                            serializer.serialize(doc_comment)
                except Exception as e:
                    logger.error(
                        f"Error processing {file_meta['path']}: {e}", exc_info=True
                    )
                    continue

        # Use batch processing from pipeline
        pipeline = getattr(context, "_pipeline", None)

        if pipeline and hasattr(pipeline, "process_batch"):
            pipeline.process_batch(
                doc_files, process_doc_batch, progress, task_id, "documentation files"
            )
        else:
            # Fallback to processing all files at once
            process_doc_batch(doc_files, progress, task_id)
