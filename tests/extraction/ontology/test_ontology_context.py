from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from rdflib import Graph, Namespace

from app.extraction.ontology import ontology_context


def test_create_ontology_context():
    g = Graph()
    class_cache = {"A": 1}
    prop_cache = {"B": 2}
    INST = Namespace("http://example.org/inst/")
    WDO = Namespace("http://example.org/wdo/")
    uri_safe_string = lambda s: s.replace(" ", "_")
    TTL_PATH = Path("/tmp/test.ttl")
    ctx = ontology_context.create_ontology_context(
        g=g,
        class_cache=class_cache,
        prop_cache=prop_cache,
        INST=INST,
        WDO=WDO,
        uri_safe_string=uri_safe_string,
        uri_safe_file_path=lambda s: s.replace(" ", "_"),
        TTL_PATH=TTL_PATH,
    )
    assert ctx.g is g
    assert ctx.class_cache == class_cache
    assert ctx.prop_cache == prop_cache
    assert ctx.INST == INST
    assert ctx.WDO == WDO
    assert ctx.uri_safe_string("a b") == "a_b"
    assert ctx.TTL_PATH == TTL_PATH


def test_initialize_graph_and_cache(tmp_path):
    fake_ttl = tmp_path / "test.ttl"
    fake_ttl.write_text("")
    with patch(
        "app.extraction.ontology.ontology_context.get_ontology_cache"
    ) as mock_cache:
        mock_cache.return_value.get_property_cache.return_value = {"p": 1}
        mock_cache.return_value.get_class_cache.return_value = {"c": 2}
        g, class_cache, prop_cache = ontology_context.initialize_graph_and_cache(
            fake_ttl
        )
        assert isinstance(g, Graph)
        assert class_cache == {"c": 2}
        assert prop_cache == {"p": 1}


def test_ontology_context_dataclass_fields():
    g = Graph()
    ctx = ontology_context.OntologyContext(
        g=g,
        class_cache={},
        prop_cache={},
        INST=Namespace("http://example.org/inst/"),
        WDO=Namespace("http://example.org/wdo/"),
        uri_safe_string=lambda s: s,
        uri_safe_file_path=lambda s: s,
        TTL_PATH=Path("/tmp/test.ttl"),
    )
    assert hasattr(ctx, "g")
    assert hasattr(ctx, "class_cache")
    assert hasattr(ctx, "prop_cache")
    assert hasattr(ctx, "INST")
    assert hasattr(ctx, "WDO")
    assert hasattr(ctx, "uri_safe_string")
    assert hasattr(ctx, "TTL_PATH")
