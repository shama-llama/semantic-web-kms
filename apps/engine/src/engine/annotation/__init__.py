"""Semantic annotation package for Semantic Web KMS."""

from engine.annotation.semantic_annotator import SemanticAnnotationPipeline, main

MESSAGES = {
    "annotation_start": "Starting semantic annotation pipeline.",
    "annotation_complete": "Annotation pipeline completed successfully.",
    "annotation_failed": "Annotation failed: {error}",
    "entity_annotated": "Entity {entity} annotated with description.",
    "ontology_updated": "Ontology updated and saved to {path}.",
}

__all__ = ["SemanticAnnotationPipeline", "main", "MESSAGES"]
