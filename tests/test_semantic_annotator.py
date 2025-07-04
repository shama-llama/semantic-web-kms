import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import pytest
from unittest.mock import patch, MagicMock
from app.annotation import semantic_annotator

def test_main_annotation_logic():
    with patch("app.annotation.semantic_annotator.Graph") as MockGraph, \
         patch("app.annotation.semantic_annotator.os.path.exists", return_value=True):
        mock_graph = MagicMock()
        MockGraph.return_value = mock_graph
        # Simulate some entities
        mock_graph.triples.return_value = [("s1", "type", "o1"), ("s2", "type", "o2")]
        # Patch serialize to do nothing
        mock_graph.serialize.return_value = None
        # Run main (should annotate entities)
        semantic_annotator.main()
        # Check that annotation was added for each entity
        assert mock_graph.add.call_count == 2
        # Check that serialize was called
        mock_graph.serialize.assert_called_once() 