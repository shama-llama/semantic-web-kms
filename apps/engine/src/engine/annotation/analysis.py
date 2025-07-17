"""Module for analyzing graph structure and instance properties."""

import logging
from collections import Counter
from typing import Any

from rdflib import RDF, Graph, URIRef
from rdflib.term import Node

logger = logging.getLogger(__name__)


def get_classes_and_properties(graph: Graph) -> dict[str, list[str]]:
    """
    Retrieve all classes and their associated properties from the ontology graph.

    Args:
        graph: The ontology RDF graph.

    Returns:
        Dictionary mapping class URIs to a sorted list of their property URIs.
    """
    class_to_properties: dict[Node, set] = {}
    for s, _, o in graph.triples((None, RDF.type, None)):
        class_uri = o
        if class_uri not in class_to_properties:
            class_to_properties[class_uri] = set()
        for p, _ in graph.predicate_objects(s):
            class_to_properties[class_uri].add(p)

    return {
        str(cls): sorted(str(p) for p in props)
        for cls, props in class_to_properties.items()
    }


def _collect_class_instances(graph: Graph) -> dict[Node, list[Node]]:
    class_instances: dict[Node, list[Node]] = {}
    for s, _, o in graph.triples((None, RDF.type, None)):
        if isinstance(o, URIRef):
            class_instances.setdefault(o, []).append(s)
    return class_instances


def _analyze_properties(
    graph: Graph, instances: list[Node]
) -> tuple[Counter, dict[Node, str]]:
    prop_counter: Counter = Counter()
    prop_cardinality: dict[Node, str] = {}
    for instance_uri in instances:
        instance_props = {p for p, _ in graph.predicate_objects(instance_uri)}
        prop_counter.update(instance_props)
        instance_prop_counts = Counter(
            p for p, _ in graph.predicate_objects(instance_uri)
        )
        for prop, count in instance_prop_counts.items():
            if prop not in prop_cardinality:
                prop_cardinality[prop] = "single"
            if count > 1:
                prop_cardinality[prop] = "multiple"
    return prop_counter, prop_cardinality


def _format_property_stats(
    prop_counter: Counter, prop_cardinality: dict[Node, str], num_instances: int
) -> list[dict[str, str]]:
    properties_with_stats: list[dict[str, str]] = []
    for prop, count in prop_counter.most_common():
        frequency = (count / num_instances) * 100
        cardinality = prop_cardinality.get(prop, "single")
        properties_with_stats.append({
            "uri": str(prop),
            "frequency": f"{frequency:.0f}%",
            "cardinality": cardinality,
        })
    return properties_with_stats


def analyze_class_structure(graph: Graph) -> dict[str, list[dict[str, str]]]:
    """
    Analyze the graph to find classes and compute statistics about their properties.

    Args:
        graph: An RDFLib Graph containing the ontology data.

    Returns:
        Dict mapping each class URI to a list of its property statistics.
    """
    logger.info("Starting class structure analysis...")
    class_instances = _collect_class_instances(graph)
    logger.info(f"Found {len(class_instances)} classes with instances.")
    class_analysis: dict[str, list[dict[str, str]]] = {}
    for class_uri, instances in class_instances.items():
        num_instances = len(instances)
        if num_instances == 0:
            continue
        logger.info(f"Analyzing class {class_uri} with {num_instances} instances.")
        prop_counter, prop_cardinality = _analyze_properties(graph, instances)
        properties_with_stats = _format_property_stats(
            prop_counter, prop_cardinality, num_instances
        )
        class_analysis[str(class_uri)] = properties_with_stats
    logger.info(
        f"Class structure analysis complete. Analyzed {len(class_analysis)} classes."
    )
    return class_analysis


# --- Context analysis helper functions ---


def _context_from_code_snippet(code_snippet: str) -> dict[str, str]:
    context = {}
    if code_snippet.startswith(("import ", "from ")):
        context["specific_purpose"] = "enable access to external libraries and modules"
    elif code_snippet.startswith(("def ", "function ")):
        context["specific_purpose"] = "encapsulate reusable logic and operations"
    elif code_snippet.startswith(("class ",)):
        context["specific_purpose"] = "define a new class or data structure"
    elif code_snippet.startswith(("//", "#")):
        context["specific_purpose"] = "document code behavior and purpose"
    return context


def _context_from_relationship(parent_context: str) -> dict[str, str]:
    context = {}
    parent_lower = str(parent_context).lower()
    if "function" in parent_lower:
        context["specific_role"] = "as part of a function implementation"
    elif "class" in parent_lower:
        context["specific_role"] = "within a class definition"
    elif "file" in parent_lower:
        context["specific_role"] = "for file organization"
    else:
        context["specific_role"] = "as a system component"
    return context


def _context_from_label(label: str) -> dict[str, str]:
    context = {}
    label_lower = label.lower()
    if "import" in label_lower:
        context["specific_purpose"] = "enable access to external libraries"
    elif "var" in label_lower or "variable" in label_lower:
        context["specific_purpose"] = "store and manage data values"
    elif "func" in label_lower or "function" in label_lower:
        context["specific_purpose"] = "encapsulate reusable logic"
    elif "class" in label_lower:
        context["specific_purpose"] = "define object blueprints"
    elif "comment" in label_lower:
        context["specific_purpose"] = "document code behavior"
    return context


def analyze_property_context(
    properties: dict[str, Any],
    _graph: Graph | None = None,
    _instance: URIRef | None = None,
) -> dict[str, str]:
    """
    Analyze properties to provide context-aware information for template generation.

    Note: This implementation derives context solely from the `properties` dictionary.
    The `_graph` and `_instance` parameters are unused but kept for interface compatibility.

    Args:
        properties: Dictionary of instance properties (e.g., from extract_instance_properties).
        _graph: (Unused) The RDF graph containing the instance.
        _instance: (Unused) The instance URI being analyzed.

    Returns:
        A dictionary with contextual keywords for template generation.
    """
    context: dict[str, str] = {}
    if "hasSourceCodeSnippet" in properties:
        code_snippet = properties["hasSourceCodeSnippet"]
        context.update(_context_from_code_snippet(code_snippet))

    if "isCodePartOf" in properties:
        parent_context = properties["isCodePartOf"]
        context.update(_context_from_relationship(parent_context))

    if "label" in properties:
        label = properties["label"]
        context.update(_context_from_label(label))

    return context
