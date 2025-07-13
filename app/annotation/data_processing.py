"""Data processing utilities for annotation pipeline."""

import logging
import re
from typing import Any, Dict, List

from rdflib import Graph, Literal, URIRef
from rdflib.namespace import RDF, SKOS

from app.annotation.utils import convert_property_to_snake_case

logger = logging.getLogger("annotation_data_processing")


def extract_instance_properties(graph: Graph, instance: URIRef) -> Dict[str, Any]:
    """
    Extract and convert properties for an instance to snake_case format.

    Args:
        graph: RDF graph containing the instance
        instance: Instance URI to extract properties for

    Returns:
        Dictionary of properties in snake_case format
    """
    properties = {
        convert_property_to_snake_case(str(p)): (
            v.toPython() if isinstance(v, Literal) else str(v)
        )
        for p, v in graph.predicate_objects(instance)
    }

    # Add contextual analysis
    from app.annotation.generate_class_templates import analyze_property_context

    context = analyze_property_context(graph, instance, properties)
    properties.update(context)

    return properties


def get_all_instances(graph: Graph, templates: Dict) -> List[tuple]:
    """
    Get all instances that need annotation, grouped by class.

    Args:
        graph: RDF graph to search
        templates: Dictionary mapping class URIs to templates

    Returns:
        List of (instance, template, class_name) tuples
    """
    instances: List[tuple] = []
    for class_uri, template in templates.items():
        class_name = class_uri.split("#")[-1]
        class_instances = graph.triples((None, RDF.type, URIRef(class_uri)))
        instances.extend(
            (instance, template, class_name) for instance, _, _ in class_instances
        )
    return instances


def process_single_instance(
    graph: Graph,
    instance: URIRef,
    template: str,
    label_to_uri_map: Dict[str, URIRef],
    class_name: str,
    nlp=None,
    optimized: bool = False,
) -> bool:
    """
    Process a single instance for annotation.

    Args:
        graph: RDF graph containing the instance
        instance: Instance URI to process
        template: Template to use for annotation
        label_to_uri_map: Pre-computed label lookup map
        class_name: Name of the class for logging
        nlp: Pre-loaded spaCy model for performance
        optimized: Whether to use optimized processing (faster but less comprehensive)

    Returns:
        True if annotation was successful, False otherwise
    """
    logger.debug(f"Annotating instance {instance} (class: {class_name})")

    # Extract properties using dictionary comprehension
    properties = extract_instance_properties(graph, instance)

    logger.debug(
        f"Instance {instance} has {len(properties)} properties: {list(properties.keys())}"
    )

    # Render template with error handling
    try:
        from app.annotation.utils import render_template_with_jinja2

        summary = render_template_with_jinja2(
            template, {**properties, "items": properties}
        )
        logger.debug(f"Successfully rendered template for instance {instance}")
    except Exception as e:
        logger.error(f"Failed to render template for instance {instance}: {e}")
        summary = f"Error rendering template: {e}"
        return False

    # Post-processing based on optimization mode
    if optimized:
        # Optimized post-processing: skip expensive operations for speed
        logger.debug(f"Running optimized post-processing for instance {instance}")
        from app.annotation.postprocessing import enrich_description_with_links

        enriched_summary = enrich_description_with_links(
            graph, summary, label_to_uri_map, nlp
        )

        # Validate and improve quality
        plaintext_summary = validate_editorial_note_quality(summary)
        enriched_summary = validate_editorial_note_quality(enriched_summary)

        logger.debug(f"Optimized post-processing complete for instance {instance}")
    else:
        # Full post-processing: enrichment and validation
        logger.debug(f"Running full post-processing for instance {instance}")
        from app.annotation.postprocessing import enrich_and_validate_summary

        enriched_summary, quality_metrics = enrich_and_validate_summary(
            graph, instance, summary, label_to_uri_map
        )
        plaintext_summary = validate_editorial_note_quality(summary)
        logger.debug(f"Post-processing complete for instance {instance}")
        logger.debug(f"Quality metrics: {quality_metrics}")

    # Store annotation in skos:editorialNote (for SKOS compliance)
    graph.set((instance, SKOS.editorialNote, Literal(plaintext_summary)))

    return True


def validate_editorial_note_quality(note: str) -> str:
    """
    Validate and improve the quality of generated editorial notes.

    Args:
        note: The original editorial note

    Returns:
        Improved editorial note
    """
    if not note or len(note.strip()) < 10:
        return note

    # Remove code blocks (triple backticks)
    note = re.sub(r"```.*?```", "", note, flags=re.DOTALL)
    # Remove inline code (single backticks)
    note = re.sub(r"`[^`]+`", "", note)
    note = note.strip()

    # Remove specific code patterns that might have slipped through
    note = re.sub(r"class\s+[a-zA-Z_][a-zA-Z0-9_]*\s*\{[^}]*\}", "", note)
    note = re.sub(r"def\s+[a-zA-Z_][a-zA-Z0-9_]*\s*\([^)]*\)\s*:[^:]*:", "", note)
    note = re.sub(
        r"function\s+[a-zA-Z_][a-zA-Z0-9_]*\s*\([^)]*\)\s*\{[^}]*\}", "", note
    )
    note = re.sub(r"import\s+[^;]+;", "", note)
    note = re.sub(r"from\s+[^;]+;", "", note)

    # Check for repetitive phrases and replace them
    repetitive_phrases = {
        "is a fundamental component within the codebase": "contributes to the codebase",
        "is intrinsically linked to": "is part of",
        "plays a crucial role": "serves a purpose",
        "fundamental component": "component",
        "essential functionality": "functionality",
        "necessary code elements": "code elements",
        "available for execution": "available",
        "overall structure and organization": "system structure",
        "proper functionality and system coherence": "system functionality",
        "vital role in the codebase": "role in the codebase",
        "important component within the codebase": "component in the codebase",
        "provides essential functionality and structure": "provides functionality",
        "crucial for maintaining proper structure": "helps maintain structure",
        "ensures proper functionality": "supports functionality",
        "is a core element within the codebase": "is part of the codebase",
        "specifically representing the act of": "represents",
        "core component within": "component in",
        "a core component within": "a component in",
        "represents the entity named": "represents",
        "with a canonical name of": "with canonical name",
        "and a simple name of": "with simple name",
        "While its canonical name is": "Its canonical name is",
        "it can also be described by its text value": "it has text value",
        "written in": "implemented in",
        "has a canonical name of": "has canonical name",
    }

    improved_note = note
    for old_phrase, new_phrase in repetitive_phrases.items():
        improved_note = improved_note.replace(old_phrase, new_phrase)

    # Remove redundant sentences
    sentences = improved_note.split(". ")
    unique_sentences: List[str] = []
    for sentence in sentences:
        sentence = sentence.strip()
        if sentence and sentence not in unique_sentences:
            # Check if this sentence is too similar to existing ones
            is_redundant = False
            for existing in unique_sentences:
                if (
                    len(set(sentence.lower().split()) & set(existing.lower().split()))
                    > 3
                ):
                    is_redundant = True
                    break
            if not is_redundant:
                unique_sentences.append(sentence)

    # Reconstruct the note
    improved_note = ". ".join(unique_sentences)
    if improved_note and not improved_note.endswith("."):
        improved_note += "."

    # Ensure the note is not too long (max 300 characters)
    if len(improved_note) > 300:
        sentences = improved_note.split(". ")
        if len(sentences) > 2:
            improved_note = ". ".join(sentences[:2]) + "."

    # Remove excessive backticks and formatting
    improved_note = improved_note.replace("`", "")

    # Clean up excessive whitespace
    improved_note = " ".join(improved_note.split())

    return improved_note
