"""Tests for similarity calculation functionality."""

import numpy as np
import pytest
from rdflib import Graph, Literal, URIRef
from rdflib.namespace import RDF, RDFS, SKOS

from app.annotation.similarity_calculator import (
    add_similarity_relationships,
    calculate_similarity_matrix,
    enhanced_similarity_calculation,
    extract_instance_features,
    find_top_similar_instances,
)


class TestSimilarityCalculator:
    """Test the similarity calculation functionality."""

    def test_extract_instance_features(self):
        """Test feature extraction from instances."""
        g = Graph()

        # Create test instances
        inst1 = URIRef("http://example.org/instance1")
        inst2 = URIRef("http://example.org/instance2")

        # Add properties to instances
        g.add((inst1, RDF.type, URIRef("http://example.org/FunctionDefinition")))
        g.add((inst1, RDFS.label, Literal("calculate_sum")))
        g.add((inst1, SKOS.editorialNote, Literal("A function that adds two numbers")))
        g.add((inst1, URIRef("http://example.org/hasLanguage"), Literal("Python")))

        g.add((inst2, RDF.type, URIRef("http://example.org/FunctionDefinition")))
        g.add((inst2, RDFS.label, Literal("calculate_product")))
        g.add(
            (
                inst2,
                SKOS.editorialNote,
                Literal("A function that multiplies two numbers"),
            )
        )
        g.add((inst2, URIRef("http://example.org/hasLanguage"), Literal("Python")))

        # Extract features
        features1 = extract_instance_features(g, inst1)
        features2 = extract_instance_features(g, inst2)

        # Check feature extraction
        assert features1["type"] == "http://example.org/FunctionDefinition"
        assert features1["label"] == "calculate_sum"
        assert "adds two numbers" in features1["editorial_note"]
        assert "Python" in features1["text_content"]

        assert features2["type"] == "http://example.org/FunctionDefinition"
        assert features2["label"] == "calculate_product"
        assert "multiplies two numbers" in features2["editorial_note"]
        assert "Python" in features2["text_content"]

    def test_calculate_similarity_matrix(self):
        """Test similarity matrix calculation."""
        # Create test instances with features
        instances = [
            {
                "type": "http://example.org/FunctionDefinition",
                "label": "calculate_sum",
                "editorial_note": "A function that adds two numbers",
                "properties": {},
                "relationships": set(),
                "text_content": "calculate_sum A function that adds two numbers",
            },
            {
                "type": "http://example.org/FunctionDefinition",
                "label": "calculate_product",
                "editorial_note": "A function that multiplies two numbers",
                "properties": {},
                "relationships": set(),
                "text_content": "calculate_product A function that multiplies two numbers",
            },
            {
                "type": "http://example.org/ClassDefinition",
                "label": "User",
                "editorial_note": "A class representing a user",
                "properties": {},
                "relationships": set(),
                "text_content": "User A class representing a user",
            },
        ]

        # Calculate similarity matrix
        similarity_matrix = calculate_similarity_matrix(instances)

        # Check matrix properties
        assert similarity_matrix.shape == (3, 3)
        assert similarity_matrix[0, 0] == 1.0  # Self-similarity
        assert similarity_matrix[1, 1] == 1.0
        assert similarity_matrix[2, 2] == 1.0

        # Function instances should be more similar to each other than to class
        assert similarity_matrix[0, 1] > similarity_matrix[0, 2]
        assert similarity_matrix[1, 0] > similarity_matrix[1, 2]

    def test_find_top_similar_instances(self):
        """Test finding top similar instances."""
        # Create similarity matrix
        similarity_matrix = np.array(
            [
                [1.0, 0.8, 0.3, 0.1],
                [0.8, 1.0, 0.2, 0.1],
                [0.3, 0.2, 1.0, 0.9],
                [0.1, 0.1, 0.9, 1.0],
            ]
        )

        instance_uris = [
            "http://example.org/inst1",
            "http://example.org/inst2",
            "http://example.org/inst3",
            "http://example.org/inst4",
        ]

        # Find top similar instances
        similar_instances = find_top_similar_instances(
            similarity_matrix, instance_uris, top_k=2, min_similarity=0.1
        )

        # Check results
        assert len(similar_instances) == 4

        # Instance 1 should have instance 2 as most similar
        inst1_similar = similar_instances["http://example.org/inst1"]
        assert len(inst1_similar) == 2
        assert inst1_similar[0][0] == "http://example.org/inst2"
        assert inst1_similar[0][1] == 0.8

        # Instance 3 and 4 should be most similar to each other
        inst3_similar = similar_instances["http://example.org/inst3"]
        inst4_similar = similar_instances["http://example.org/inst4"]
        assert inst3_similar[0][0] == "http://example.org/inst4"
        assert inst4_similar[0][0] == "http://example.org/inst3"

    def test_add_similarity_relationships(self):
        """Test adding similarity relationships to graph."""
        g = Graph()

        # Create test instances with editorial notes
        inst1 = URIRef("http://example.org/instance1")
        inst2 = URIRef("http://example.org/instance2")
        inst3 = URIRef("http://example.org/instance3")

        # Add instances with editorial notes
        g.add((inst1, RDF.type, URIRef("http://example.org/FunctionDefinition")))
        g.add((inst1, RDFS.label, Literal("calculate_sum")))
        g.add((inst1, SKOS.editorialNote, Literal("A function that adds two numbers")))

        g.add((inst2, RDF.type, URIRef("http://example.org/FunctionDefinition")))
        g.add((inst2, RDFS.label, Literal("calculate_product")))
        g.add(
            (
                inst2,
                SKOS.editorialNote,
                Literal("A function that multiplies two numbers"),
            )
        )

        g.add((inst3, RDF.type, URIRef("http://example.org/ClassDefinition")))
        g.add((inst3, RDFS.label, Literal("User")))
        g.add((inst3, SKOS.editorialNote, Literal("A class representing a user")))

        # Add similarity relationships
        relationships_added = add_similarity_relationships(
            g, max_instances=10, top_k=2, min_similarity=0.1
        )

        # Check that relationships were added
        assert relationships_added > 0

        # Check that seeAlso relationships exist
        see_also_triples = list(g.triples((None, RDFS.seeAlso, None)))
        assert len(see_also_triples) > 0

        # Check that relationships are bidirectional
        for subject, predicate, obj in see_also_triples:
            # Should also have the reverse relationship
            reverse_exists = (obj, predicate, subject) in g
            assert reverse_exists

    def test_enhanced_similarity_calculation(self):
        """Test enhanced similarity calculation with centrality."""
        g = Graph()

        # Create a small test graph
        inst1 = URIRef("http://example.org/instance1")
        inst2 = URIRef("http://example.org/instance2")
        inst3 = URIRef("http://example.org/instance3")

        # Add instances with editorial notes
        g.add((inst1, RDF.type, URIRef("http://example.org/FunctionDefinition")))
        g.add((inst1, RDFS.label, Literal("calculate_sum")))
        g.add((inst1, SKOS.editorialNote, Literal("A function that adds two numbers")))

        g.add((inst2, RDF.type, URIRef("http://example.org/FunctionDefinition")))
        g.add((inst2, RDFS.label, Literal("calculate_product")))
        g.add(
            (
                inst2,
                SKOS.editorialNote,
                Literal("A function that multiplies two numbers"),
            )
        )

        g.add((inst3, RDF.type, URIRef("http://example.org/ClassDefinition")))
        g.add((inst3, RDFS.label, Literal("User")))
        g.add((inst3, SKOS.editorialNote, Literal("A class representing a user")))

        # Add some relationships to make the graph more interesting
        g.add((inst1, URIRef("http://example.org/calls"), inst2))
        g.add((inst2, URIRef("http://example.org/uses"), inst3))

        # Run enhanced similarity calculation
        relationships_added = enhanced_similarity_calculation(
            g, use_centrality=True, max_instances=10
        )

        # Check that relationships were added
        assert relationships_added > 0

        # Check that seeAlso relationships exist
        see_also_triples = list(g.triples((None, RDFS.seeAlso, None)))
        assert len(see_also_triples) > 0


if __name__ == "__main__":
    pytest.main([__file__])
