from unittest import mock

import pytest

from app.extraction.writers import ontology_writer


def make_ctx():
    ctx = mock.Mock()
    ctx.uri_safe_string = lambda s: s
    ctx.class_cache = {
        "FunctionDefinition": mock.Mock(),
        "AttributeDeclaration": mock.Mock(),
    }
    ctx.prop_cache = {"hasSimpleName": mock.Mock(), "hasCanonicalName": mock.Mock()}
    ctx.WDO = mock.Mock()
    ctx.INST = {
        "repo1/file1.py": "file://repo1/file1.py",
        "file:": "file://repo1/file1.py",
    }
    ctx.g = mock.Mock()
    return ctx


def test_process_file_for_ontology_runs():
    ctx = make_ctx()
    rec = {"repository": "repo1", "path": "file1.py"}
    summary_data = {"repo1/file1.py": {}}
    global_type_uris = {}
    language_mapping = {".py": "python"}
    # Should not raise
    ontology_writer.process_file_for_ontology(
        ctx=ctx,
        rec=rec,
        summary_data=summary_data,
        global_type_uris=global_type_uris,
        language_mapping=language_mapping,
    )


def test_write_fields_runs():
    g = mock.Mock()
    constructs = {"fields": [{"name": "field1"}]}
    file_uri = "file://test.py"
    class_cache = {"AttributeDeclaration": mock.Mock()}
    prop_cache = {"hasSimpleName": mock.Mock()}
    uri_safe_string = lambda s: s
    class_uris = {"TestClass": mock.Mock()}
    type_uris = {"TestType": mock.Mock()}
    # Should not raise
    ontology_writer.write_fields(
        g,
        constructs,
        file_uri,
        class_cache,
        prop_cache,
        uri_safe_string,
        class_uris,
        type_uris,
    )


def test_write_all_entities_for_file_runs():
    ctx = make_ctx()
    constructs = {"FunctionDefinition": [{"name": "func1"}]}
    file_uri = "file://test.py"
    all_entity_uris = {"func1": mock.Mock()}
    interface_uris = {}
    module_uris = {}
    global_type_uris = {}
    language = "python"
    result = ontology_writer.write_all_entities_for_file(
        ctx,
        constructs,
        file_uri,
        all_entity_uris,
        interface_uris,
        module_uris,
        global_type_uris,
        language,
    )
    assert isinstance(result, dict)


def test_write_all_relationships_runs():
    ctx = make_ctx()
    constructs = {}
    file_uri = "file://test.py"
    all_entity_uris = {}
    interface_uris = {}
    module_uris = {}
    func_uris = {}
    global_type_uris = {}
    # Should not raise
    ontology_writer.write_all_relationships(
        ctx,
        constructs,
        file_uri,
        all_entity_uris,
        interface_uris,
        module_uris,
        func_uris,
        global_type_uris,
    )


def test_finalize_and_serialize_graph_runs():
    ctx = make_ctx()
    # Should not raise
    ontology_writer.finalize_and_serialize_graph(ctx)
