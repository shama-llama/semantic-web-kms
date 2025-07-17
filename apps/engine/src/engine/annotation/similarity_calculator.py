"""Efficient similarity calculation for RDF graph instances."""

import logging
from typing import Any

import networkx as nx
import numpy as np
from rdflib import Graph, Node, URIRef
from rdflib.namespace import RDF, RDFS, SKOS
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from engine.annotation.constants import (
    CENTRALITY_BOOST_FACTOR,
    SIMILARITY_MAX_INSTANCES,
    SIMILARITY_MIN_SCORE,
    SIMILARITY_TOP_K,
    SIMILARITY_WEIGHTS,
)

logger = logging.getLogger("similarity_calculator")


def _extract_properties(
    graph: Graph, instance: Node
) -> tuple[dict[str, list[str]], dict[str, Any]]:
    """
    Extract properties and main features from an instance.

    Args:
        graph: RDF graph containing the instance
        instance: Instance URI to extract features for

    Returns:
        Tuple containing:
            - Dictionary of properties (predicate URI to list of values)
            - Dictionary with keys 'type', 'label', 'editorial_note'
    """
    properties: dict[str, list[str]] = {}
    features = {
        "type": None,
        "label": "",
        "editorial_note": "",
    }
    for predicate, obj in graph.predicate_objects(instance):
        pred_str = str(predicate)
        if predicate == RDF.type:
            features["type"] = str(obj)
        elif predicate == RDFS.label:
            features["label"] = str(obj)
        elif predicate == SKOS.editorialNote:
            features["editorial_note"] = str(obj)
        else:
            if pred_str not in properties:
                properties[pred_str] = []
            properties[pred_str].append(str(obj))
    return properties, features


def _extract_relationships(graph: Graph, instance: Node) -> set[str]:
    """
    Extract outgoing relationships (predicates) for an instance.

    Args:
        graph: RDF graph containing the instance
        instance: Instance URI to extract relationships for

    Returns:
        Set of predicate URIs for outgoing relationships
    """
    relationships = set()
    for _, predicate, obj in graph.triples((instance, None, None)):
        if isinstance(obj, URIRef):
            relationships.add(str(predicate))
    return relationships


def _assemble_text_content(
    label: str, editorial_note: str, properties: dict[str, list[str]]
) -> str:
    """
    Assemble text content for TF-IDF from label, editorial note, and property values.

    Args:
        label: The label of the instance
        editorial_note: The editorial note of the instance
        properties: Dictionary of property values

    Returns:
        Combined string of all text content for TF-IDF
    """
    text_parts = []
    if label:
        text_parts.append(label)
    if editorial_note:
        text_parts.append(editorial_note)
    for prop_values in properties.values():
        text_parts.extend(str(val) for val in prop_values)
    return " ".join(text_parts)


def extract_instance_features(graph: Graph, instance: Node) -> dict[str, Any]:
    """Extract features from an instance for similarity calculation.

    Args:
        graph: RDF graph containing the instance
        instance: Instance URI to extract features for

    Returns:
        Dictionary of features for similarity calculation
    """
    features: dict[str, Any] = {
        "uri": str(instance),
        "type": None,
        "label": "",
        "editorial_note": "",
        "properties": {},
        "relationships": set(),
        "text_content": "",
    }
    properties, main_features = _extract_properties(graph, instance)
    features["type"] = main_features["type"]
    features["label"] = main_features["label"]
    features["editorial_note"] = main_features["editorial_note"]
    features["properties"] = properties
    features["relationships"] = _extract_relationships(graph, instance)
    features["text_content"] = _assemble_text_content(
        features["label"], features["editorial_note"], properties
    )
    return features


def _calculate_text_similarity(instances: list[dict[str, Any]]) -> np.ndarray:
    texts = [inst["text_content"] for inst in instances]
    vectorizer = TfidfVectorizer(
        max_features=1000,
        stop_words="english",
        ngram_range=(1, 2),
        min_df=2,
        max_df=0.8,
    )
    try:
        tfidf_matrix = vectorizer.fit_transform(texts)
        return cosine_similarity(tfidf_matrix)
    except ValueError:
        logger.warning("TF-IDF calculation failed, using fallback similarity")
        n = len(instances)
        return np.eye(n)


def _calculate_type_similarity(instances: list[dict[str, Any]]) -> np.ndarray:
    n = len(instances)
    type_similarity = np.zeros((n, n))
    for i, inst1 in enumerate(instances):
        for j, inst2 in enumerate(instances):
            if inst1["type"] == inst2["type"]:
                type_similarity[i, j] = 1.0
            elif inst1["type"] and inst2["type"]:
                type1 = inst1["type"].split("#")[-1].lower()
                type2 = inst2["type"].split("#")[-1].lower()
                if any(word in type1 for word in type2.split()) or any(
                    word in type2 for word in type1.split()
                ):
                    type_similarity[i, j] = 0.5
    return type_similarity


def _calculate_relationship_similarity(instances: list[dict[str, Any]]) -> np.ndarray:
    n = len(instances)
    rel_similarity = np.zeros((n, n))
    for i, inst1 in enumerate(instances):
        for j, inst2 in enumerate(instances):
            if i != j:
                common_rels = len(inst1["relationships"] & inst2["relationships"])
                total_rels = len(inst1["relationships"] | inst2["relationships"])
                if total_rels > 0:
                    rel_similarity[i, j] = common_rels / total_rels
    return rel_similarity


def calculate_similarity_matrix(instances: list[dict[str, Any]]) -> np.ndarray:
    """Calculate similarity matrix using TF-IDF and cosine similarity.

    Args:
        instances: List of instance feature dictionaries

    Returns:
        Similarity matrix (n x n)
    """
    text_similarity = _calculate_text_similarity(instances)
    type_similarity = _calculate_type_similarity(instances)
    rel_similarity = _calculate_relationship_similarity(instances)
    combined_similarity = (
        SIMILARITY_WEIGHTS["text"] * text_similarity
        + SIMILARITY_WEIGHTS["type"] * type_similarity
        + SIMILARITY_WEIGHTS["relationship"] * rel_similarity
    )
    np.fill_diagonal(combined_similarity, 1.0)
    return combined_similarity.astype(np.float64)  # type: ignore[no-any-return]


def find_top_similar_instances(
    similarity_matrix: np.ndarray,
    instance_uris: list[str],
    top_k: int = 3,
    min_similarity: float = 0.1,
) -> dict[str, list[tuple[str, float]]]:
    """Find top-k most similar instances for each instance.

    Args:
        similarity_matrix: Similarity matrix
        instance_uris: List of instance URIs
        top_k: Number of similar instances to find
        min_similarity: Minimum similarity threshold

    Returns:
        Dictionary mapping instance URI to list of
        (similar_uri, similarity_score) tuples
    """
    similar_instances = {}

    for i, uri in enumerate(instance_uris):
        # Get similarities for this instance
        similarities = similarity_matrix[i]

        # Create list of (index, similarity) pairs, excluding self
        pairs = [(j, similarities[j]) for j in range(len(similarities)) if j != i]

        # Filter by minimum similarity and sort by similarity
        valid_pairs = [(j, sim) for j, sim in pairs if sim >= min_similarity]
        valid_pairs.sort(key=lambda x: x[1], reverse=True)

        # Take top-k
        top_similar = valid_pairs[:top_k]

        # Convert to (uri, similarity) format
        similar_instances[uri] = [
            (instance_uris[j], float(sim)) for j, sim in top_similar
        ]

    return similar_instances


def _collect_instances_with_notes(graph: Graph) -> list:
    instances = []
    for instance, _, _note in graph.triples((None, SKOS.editorialNote, None)):
        instances.append(instance)
    return instances


def _extract_instance_features_list(
    graph: Graph,
    instances_with_notes: list,
    use_centrality: bool,
    centrality_scores: dict,
) -> tuple[list, list]:
    instance_features = []
    instance_uris = []
    for instance in instances_with_notes:
        features = extract_instance_features(graph, instance)
        if use_centrality:
            features["centrality"] = centrality_scores.get(str(instance), 0.0)
        else:
            features["centrality"] = 0.0
        instance_features.append(features)
        instance_uris.append(str(instance))
    return instance_features, instance_uris


def _calculate_combined_similarity(instance_features: list) -> np.ndarray:
    text_similarity = _calculate_text_similarity(instance_features)
    type_similarity = _calculate_type_similarity(instance_features)
    rel_similarity = _calculate_relationship_similarity(instance_features)
    combined_similarity = (
        SIMILARITY_WEIGHTS["text"] * text_similarity
        + SIMILARITY_WEIGHTS["type"] * type_similarity
        + SIMILARITY_WEIGHTS["relationship"] * rel_similarity
    )
    np.fill_diagonal(combined_similarity, 1.0)
    return combined_similarity


def _boost_similarity_with_centrality(
    combined_similarity: np.ndarray, instance_features: list, centrality_scores: dict
):
    for i, features in enumerate(instance_features):
        centrality = features["centrality"]
        combined_similarity[i] *= 1 + centrality * CENTRALITY_BOOST_FACTOR


def _add_see_also_relationships(
    graph: Graph, similar_instances: dict, top_k: int
) -> int:
    relationships_added = 0
    for instance_uri, similar_list in similar_instances.items():
        instance_ref = URIRef(instance_uri)
        for similar_uri, _similarity_score in similar_list[:top_k]:
            similar_ref = URIRef(similar_uri)
            graph.add((instance_ref, RDFS.seeAlso, similar_ref))
            relationships_added += 1
            logger.debug(
                f"Added seeAlso: {instance_uri} -> {similar_uri} "
                f"(sim: {_similarity_score:.3f})"
            )
    return relationships_added


def add_similarity_links(graph: Graph, use_centrality: bool = True) -> int:
    """
    Calculates instance similarity and adds rdfs:seeAlso relationships.
    This function combines the logic of the two previous functions.
    """
    logger.info("Starting similarity relationship calculation.")
    instances_with_notes = _collect_instances_with_notes(graph)
    if len(instances_with_notes) > SIMILARITY_MAX_INSTANCES:
        logger.info(f"Limiting to {SIMILARITY_MAX_INSTANCES} instances for performance")
        instances_with_notes = instances_with_notes[:SIMILARITY_MAX_INSTANCES]
    centrality_scores = {}
    if use_centrality and len(instances_with_notes) > 10:
        logger.info("Calculating centrality scores")
        centrality_scores = calculate_graph_centrality(graph)
    instance_features, instance_uris = _extract_instance_features_list(
        graph, instances_with_notes, use_centrality, centrality_scores
    )
    combined_similarity = _calculate_combined_similarity(instance_features)
    if use_centrality and centrality_scores:
        _boost_similarity_with_centrality(
            combined_similarity, instance_features, centrality_scores
        )
    similar_instances = find_top_similar_instances(
        combined_similarity, instance_uris, SIMILARITY_TOP_K, SIMILARITY_MIN_SCORE
    )
    relationships_added = _add_see_also_relationships(
        graph, similar_instances, SIMILARITY_TOP_K
    )
    logger.info(f"Added {relationships_added} seeAlso relationships")
    return relationships_added


def calculate_graph_centrality(graph: Graph) -> dict[str, float]:
    """Calculate centrality measures for instances to enhance similarity.

    Args:
        graph: RDF graph

    Returns:
        Dictionary mapping instance URI to centrality score
    """
    # Create NetworkX graph for centrality calculation
    nx_graph = nx.Graph()

    # Add nodes and edges from RDF graph
    for subject, _predicate, obj in graph:
        if isinstance(obj, URIRef):
            nx_graph.add_edge(str(subject), str(obj))

    # Calculate centrality
    centrality = nx.betweenness_centrality(nx_graph, k=min(100, len(nx_graph)))

    # Convert numpy floats to Python floats
    return {node: float(score) for node, score in centrality.items()}
