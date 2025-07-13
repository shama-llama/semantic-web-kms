"""Efficient similarity calculation for RDF graph instances."""

import logging
from typing import Any, Dict, List, Tuple

import networkx as nx
import numpy as np
from rdflib import Graph, Node, URIRef
from rdflib.namespace import RDF, RDFS, SKOS
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

logger = logging.getLogger("similarity_calculator")


def extract_instance_features(graph: Graph, instance: Node) -> Dict[str, Any]:
    """
    Extract features from an instance for similarity calculation.

    Args:
        graph: RDF graph containing the instance
        instance: Instance URI to extract features for

    Returns:
        Dictionary of features for similarity calculation
    """
    features: Dict[str, Any] = {
        "uri": str(instance),
        "type": None,
        "label": "",
        "editorial_note": "",
        "properties": {},
        "relationships": set(),
        "text_content": "",
    }

    # Type the properties as Dict[str, List[str]] for better type safety
    properties: Dict[str, List[str]] = {}
    features["properties"] = properties

    # Extract all properties
    for predicate, obj in graph.predicate_objects(instance):
        pred_str = str(predicate)

        if predicate == RDF.type:
            features["type"] = str(obj)
        elif predicate == RDFS.label:
            features["label"] = str(obj)
        elif predicate == SKOS.editorialNote:
            features["editorial_note"] = str(obj)
        else:
            # Store other properties
            if pred_str not in properties:
                properties[pred_str] = []
            properties[pred_str].append(str(obj))

    # Extract relationships (outgoing edges)
    for _, predicate, obj in graph.triples((instance, None, None)):
        if isinstance(obj, URIRef):
            features["relationships"].add(str(predicate))

    # Combine text content for TF-IDF
    text_parts = []
    if features["label"]:
        text_parts.append(features["label"])
    if features["editorial_note"]:
        text_parts.append(features["editorial_note"])

    # Add property values as text
    for prop_values in properties.values():
        text_parts.extend(str(val) for val in prop_values)

    features["text_content"] = " ".join(text_parts)

    return features


def calculate_similarity_matrix(instances: List[Dict[str, Any]]) -> np.ndarray:
    """
    Calculate similarity matrix using TF-IDF and cosine similarity.

    Args:
        instances: List of instance feature dictionaries

    Returns:
        Similarity matrix (n x n)
    """
    # Extract text content for TF-IDF
    texts = [inst["text_content"] for inst in instances]

    # Use TF-IDF for text similarity
    vectorizer = TfidfVectorizer(
        max_features=1000,
        stop_words="english",
        ngram_range=(1, 2),
        min_df=2,
        max_df=0.8,
    )

    try:
        tfidf_matrix = vectorizer.fit_transform(texts)
        text_similarity = cosine_similarity(tfidf_matrix)
    except ValueError:
        # Fallback if TF-IDF fails (e.g., no common terms)
        logger.warning("TF-IDF calculation failed, using fallback similarity")
        n = len(instances)
        text_similarity = np.eye(n)

    # Calculate type similarity (same type = higher similarity)
    type_similarity = np.zeros((len(instances), len(instances)))
    for i, inst1 in enumerate(instances):
        for j, inst2 in enumerate(instances):
            if inst1["type"] == inst2["type"]:
                type_similarity[i, j] = 1.0
            elif inst1["type"] and inst2["type"]:
                # Partial similarity for related types
                type1 = inst1["type"].split("#")[-1].lower()
                type2 = inst2["type"].split("#")[-1].lower()
                if any(word in type1 for word in type2.split()) or any(
                    word in type2 for word in type1.split()
                ):
                    type_similarity[i, j] = 0.5

    # Calculate relationship similarity
    rel_similarity = np.zeros((len(instances), len(instances)))
    for i, inst1 in enumerate(instances):
        for j, inst2 in enumerate(instances):
            if i != j:
                common_rels = len(inst1["relationships"] & inst2["relationships"])
                total_rels = len(inst1["relationships"] | inst2["relationships"])
                if total_rels > 0:
                    rel_similarity[i, j] = common_rels / total_rels

    # Combine similarities with weights
    combined_similarity = (
        0.5 * text_similarity + 0.3 * type_similarity + 0.2 * rel_similarity
    )

    # Ensure diagonal is 1.0 (self-similarity)
    np.fill_diagonal(combined_similarity, 1.0)

    return combined_similarity.astype(np.float64)  # type: ignore[no-any-return]


def find_top_similar_instances(
    similarity_matrix: np.ndarray,
    instance_uris: List[str],
    top_k: int = 3,
    min_similarity: float = 0.1,
) -> Dict[str, List[Tuple[str, float]]]:
    """
    Find top-k most similar instances for each instance.

    Args:
        similarity_matrix: Similarity matrix
        instance_uris: List of instance URIs
        top_k: Number of similar instances to find
        min_similarity: Minimum similarity threshold

    Returns:
        Dictionary mapping instance URI to list of (similar_uri, similarity_score) tuples
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


def add_similarity_relationships(
    graph: Graph, max_instances: int = 1000, top_k: int = 3, min_similarity: float = 0.1
) -> int:
    """
    Add rdfs:seeAlso relationships between similar instances.

    Args:
        graph: RDF graph to modify
        max_instances: Maximum number of instances to process (for performance)
        top_k: Number of similar instances to link
        min_similarity: Minimum similarity threshold

    Returns:
        Number of seeAlso relationships added
    """
    logger.info("Starting similarity relationship calculation")

    # Get all instances with editorial notes (these are the ones we want to link)
    instances_with_notes = []
    for instance, _, note in graph.triples((None, SKOS.editorialNote, None)):
        instances_with_notes.append(instance)

    if len(instances_with_notes) > max_instances:
        logger.info(f"Limiting to {max_instances} instances for performance")
        instances_with_notes = instances_with_notes[:max_instances]

    logger.info(f"Processing {len(instances_with_notes)} instances for similarity")

    # Extract features for all instances
    instance_features = []
    instance_uris = []

    for instance in instances_with_notes:
        features = extract_instance_features(graph, instance)
        instance_features.append(features)
        instance_uris.append(str(instance))

    # Calculate similarity matrix
    logger.info("Calculating similarity matrix")
    similarity_matrix = calculate_similarity_matrix(instance_features)

    # Find similar instances
    logger.info("Finding similar instances")
    similar_instances = find_top_similar_instances(
        similarity_matrix, instance_uris, top_k, min_similarity
    )

    # Add seeAlso relationships (limit to exactly 3 outgoing per instance)
    relationships_added = 0
    for instance_uri, similar_list in similar_instances.items():
        instance_ref = URIRef(instance_uri)

        # Limit to exactly 3 outgoing relationships per instance
        for similar_uri, similarity_score in similar_list[:3]:
            similar_ref = URIRef(similar_uri)

            # Add unidirectional seeAlso relationship (only outgoing)
            graph.add((instance_ref, RDFS.seeAlso, similar_ref))
            relationships_added += 1

            logger.debug(
                f"Added seeAlso: {instance_uri} -> {similar_uri} (sim: {similarity_score:.3f})"
            )

    logger.info(f"Added {relationships_added} seeAlso relationships")
    return relationships_added


def calculate_graph_centrality(graph: Graph) -> Dict[str, float]:
    """
    Calculate centrality measures for instances to enhance similarity.

    Args:
        graph: RDF graph

    Returns:
        Dictionary mapping instance URI to centrality score
    """
    # Create NetworkX graph for centrality calculation
    nx_graph = nx.Graph()

    # Add nodes and edges from RDF graph
    for subject, predicate, obj in graph:
        if isinstance(obj, URIRef):
            nx_graph.add_edge(str(subject), str(obj))

    # Calculate centrality
    centrality = nx.betweenness_centrality(nx_graph, k=min(100, len(nx_graph)))

    # Convert numpy floats to Python floats
    return {node: float(score) for node, score in centrality.items()}


def enhanced_similarity_calculation(
    graph: Graph, use_centrality: bool = True, max_instances: int = 1000
) -> int:
    """
    Enhanced similarity calculation with centrality weighting.

    Args:
        graph: RDF graph to modify
        use_centrality: Whether to use centrality weighting
        max_instances: Maximum number of instances to process

    Returns:
        Number of seeAlso relationships added
    """
    logger.info("Starting enhanced similarity calculation")

    # Get instances with editorial notes
    instances_with_notes = []
    for instance, _, note in graph.triples((None, SKOS.editorialNote, None)):
        instances_with_notes.append(instance)

    if len(instances_with_notes) > max_instances:
        logger.info(f"Limiting to {max_instances} instances for performance")
        instances_with_notes = instances_with_notes[:max_instances]

    # Calculate centrality if requested
    centrality_scores = {}
    if use_centrality and len(instances_with_notes) > 10:
        logger.info("Calculating centrality scores")
        centrality_scores = calculate_graph_centrality(graph)

    # Extract features
    instance_features = []
    instance_uris = []

    for instance in instances_with_notes:
        features = extract_instance_features(graph, instance)

        # Add centrality score if available
        if use_centrality:
            features["centrality"] = centrality_scores.get(str(instance), 0.0)
        else:
            features["centrality"] = 0.0

        instance_features.append(features)
        instance_uris.append(str(instance))

    # Calculate similarity matrix
    similarity_matrix = calculate_similarity_matrix(instance_features)

    # Apply centrality weighting if available
    if use_centrality and centrality_scores:
        for i, features in enumerate(instance_features):
            centrality = features["centrality"]
            # Boost similarity for high-centrality instances
            similarity_matrix[i] *= 1 + centrality * 0.5

    # Find similar instances
    similar_instances = find_top_similar_instances(
        similarity_matrix, instance_uris, top_k=3, min_similarity=0.1
    )

    # Add seeAlso relationships (limit to exactly 3 outgoing per instance)
    relationships_added = 0
    for instance_uri, similar_list in similar_instances.items():
        instance_ref = URIRef(instance_uri)

        # Limit to exactly 3 outgoing relationships per instance
        for similar_uri, similarity_score in similar_list[:3]:
            similar_ref = URIRef(similar_uri)

            # Add unidirectional seeAlso relationship (only outgoing)
            graph.add((instance_ref, RDFS.seeAlso, similar_ref))
            relationships_added += 1

    logger.info(f"Added {relationships_added} enhanced seeAlso relationships")
    return relationships_added
