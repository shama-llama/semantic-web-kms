"""Data processing utilities for the annotation pipeline."""

import logging
from typing import Any

from rdflib import Graph, Literal, URIRef
from rdflib.namespace import RDF, SKOS

from engine.annotation.postprocessing import (
    enrich_and_validate_summary,
    enrich_description_with_links,
)
from engine.annotation.text import validate_editorial_note_quality
from engine.annotation.utils import (
    convert_property_to_snake_case,
    render_template_with_jinja2,
)

logger = logging.getLogger(__name__)


def extract_instance_properties(graph: Graph, instance: URIRef) -> dict[str, Any]:
    """
    Extracts and converts properties for an instance to snake_case format.
    NOTE: The contextual analysis part is removed. The orchestrator will call
    analysis.analyze_property_context and pass the results to the template.
    """
    return {
        convert_property_to_snake_case(str(p)): (
            v.toPython() if isinstance(v, Literal) else str(v)
        )
        for p, v in graph.predicate_objects(instance)
    }


def _process_instance_common(
    graph: Graph,
    instance: URIRef,
    template: str,
    class_name: str,
) -> tuple[dict[str, Any], str | None]:
    """Shared logic for processing an instance before post-processing."""
    logger.debug(f"Annotating instance {instance} (class: {class_name})")
    properties = extract_instance_properties(graph, instance)
    logger.debug(f"Instance {instance} has {len(properties)} properties.")
    try:
        summary = render_template_with_jinja2(template, properties)
        return properties, summary
    except Exception as e:
        logger.error(f"Failed to render template for instance {instance}: {e}")
        return properties, None


def process_single_instance_optimized(
    graph: Graph,
    instance: URIRef,
    template: str,
    label_to_uri_map: dict[str, URIRef],
    class_name: str,
    nlp,
) -> bool:
    """Processes a single instance with optimized (faster) post-processing."""
    _properties, summary = _process_instance_common(
        graph, instance, template, class_name
    )
    if summary is None:
        return False

    enriched_summary = enrich_description_with_links(
        graph, summary, label_to_uri_map, nlp
    )
    plaintext_summary = validate_editorial_note_quality(enriched_summary)
    graph.set((instance, SKOS.editorialNote, Literal(plaintext_summary)))
    return True


def process_single_instance_full(
    graph: Graph,
    instance: URIRef,
    template: str,
    label_to_uri_map: dict[str, URIRef],
    class_name: str,
) -> bool:
    """Processes a single instance with full (comprehensive) post-processing."""
    _properties, summary = _process_instance_common(
        graph, instance, template, class_name
    )
    if summary is None:
        return False

    enriched_summary, _quality_metrics = enrich_and_validate_summary(
        graph, instance, summary, label_to_uri_map
    )
    plaintext_summary = validate_editorial_note_quality(enriched_summary)
    graph.set((instance, SKOS.editorialNote, Literal(plaintext_summary)))
    return True


def get_all_instances(graph: Graph, templates: dict) -> list[tuple]:
    instances: list[tuple] = []
    for class_uri, template in templates.items():
        class_name = class_uri.split("#")[-1]
        class_instances = graph.triples((None, RDF.type, URIRef(class_uri)))
        instances.extend(
            (instance, template, class_name) for instance, _, _ in class_instances
        )
    return instances
