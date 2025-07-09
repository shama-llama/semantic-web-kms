from unittest import mock

import pytest

from app.extraction.writers import relationship_writers


def test_write_inheritance_runs():
    g = mock.Mock()
    constructs = {"extends": [{"class": "A", "base": "B"}]}
    class_uris = {"A": mock.Mock(), "B": mock.Mock()}
    prop_cache = {"extendsType": mock.Mock(), "isExtendedBy": mock.Mock()}
    # Should not raise
    relationship_writers.write_inheritance(g, constructs, class_uris, prop_cache)


def test_write_implements_interface_runs():
    g = mock.Mock()
    constructs = {"implements": [{"class": "A", "interface": "I"}]}
    class_uris = {"A": mock.Mock()}
    interface_uris = {"I": mock.Mock()}
    prop_cache = {"implementsInterface": mock.Mock(), "isImplementedBy": mock.Mock()}
    # Should not raise
    relationship_writers.write_implements_interface(
        g, constructs, class_uris, interface_uris, prop_cache
    )


def test_write_declaration_usage_relationships_runs():
    g = mock.Mock()
    constructs = {
        "declaration_usage": {"variable_usages": [{"declaration": "x", "usage": "y"}]}
    }
    file_uri = "file://test.py"
    prop_cache = {"isDeclarationUsedBy": mock.Mock(), "usesDeclaration": mock.Mock()}
    uri_safe_string = lambda s: s
    # Should not raise
    relationship_writers.write_declaration_usage_relationships(
        g, constructs, file_uri, prop_cache, uri_safe_string
    )


def test_write_access_relationships_runs():
    g = mock.Mock()
    constructs = {"access_relationships": [{"function": "foo", "attribute": "bar"}]}
    file_uri = "file://test.py"
    prop_cache = {"accesses": mock.Mock(), "isAccessedBy": mock.Mock()}
    uri_safe_string = lambda s: s
    # Should not raise
    relationship_writers.write_access_relationships(
        g, constructs, file_uri, prop_cache, uri_safe_string
    )


def test_write_type_relationships_runs():
    g = mock.Mock()
    constructs = {"type_relationships": [{"construct": "foo", "type": "bar"}]}
    file_uri = "file://test.py"
    prop_cache = {"hasType": mock.Mock()}
    uri_safe_string = lambda s: s
    # Should not raise
    relationship_writers.write_type_relationships(
        g, constructs, file_uri, prop_cache, uri_safe_string
    )


def test_write_embedding_relationships_runs():
    g = mock.Mock()
    constructs = {"embedding_relationships": [{"container": "foo", "containee": "bar"}]}
    file_uri = "file://test.py"
    prop_cache = {"embeds": mock.Mock(), "isEmbeddedBy": mock.Mock()}
    uri_safe_string = lambda s: s
    # Should not raise
    relationship_writers.write_embedding_relationships(
        g, constructs, file_uri, prop_cache, uri_safe_string
    )


def test_write_manipulation_relationships_runs():
    g = mock.Mock()
    constructs = {
        "manipulation_relationships": [{"manipulator": "foo", "manipulatee": "bar"}]
    }
    file_uri = "file://test.py"
    prop_cache = {"manipulates": mock.Mock(), "isManipulatedBy": mock.Mock()}
    uri_safe_string = lambda s: s
    # Should not raise
    relationship_writers.write_manipulation_relationships(
        g, constructs, file_uri, prop_cache, uri_safe_string
    )


def test_write_styling_relationships_runs():
    g = mock.Mock()
    constructs = {"styling_relationships": [{"styler": "foo", "stylee": "bar"}]}
    file_uri = "file://test.py"
    prop_cache = {"styles": mock.Mock(), "isStyledBy": mock.Mock()}
    uri_safe_string = lambda s: s
    # Should not raise
    relationship_writers.write_styling_relationships(
        g, constructs, file_uri, prop_cache, uri_safe_string
    )


def test_write_testing_relationships_runs():
    g = mock.Mock()
    constructs = {"testing_relationships": [{"tester": "foo", "testee": "bar"}]}
    file_uri = "file://test.py"
    prop_cache = {"tests": mock.Mock(), "isTestedBy": mock.Mock()}
    uri_safe_string = lambda s: s
    # Should not raise
    relationship_writers.write_testing_relationships(
        g, constructs, file_uri, prop_cache, uri_safe_string
    )


def test_write_module_import_relationships_runs():
    g = mock.Mock()
    constructs = {"module_imports": [{"importer": "foo", "importee": "bar"}]}
    file_uri = "file://test.py"
    prop_cache = {"imports": mock.Mock(), "isImportedBy": mock.Mock()}
    uri_safe_string = lambda s: s
    module_uris = {"foo": mock.Mock(), "bar": mock.Mock()}
    # Should not raise
    relationship_writers.write_module_import_relationships(
        g, constructs, file_uri, prop_cache, uri_safe_string, module_uris
    )


def test_write_inheritance_empty():
    g = mock.Mock()
    constructs = {"extends": []}
    class_uris = {"A": mock.Mock(), "B": mock.Mock()}
    prop_cache = {"extendsType": mock.Mock(), "isExtendedBy": mock.Mock()}
    relationship_writers.write_inheritance(g, constructs, class_uris, prop_cache)


def test_write_implements_interface_empty():
    g = mock.Mock()
    constructs = {"implements": []}
    class_uris = {"A": mock.Mock()}
    interface_uris = {"I": mock.Mock()}
    prop_cache = {"implementsInterface": mock.Mock(), "isImplementedBy": mock.Mock()}
    relationship_writers.write_implements_interface(
        g, constructs, class_uris, interface_uris, prop_cache
    )


def test_write_declaration_usage_relationships_empty():
    g = mock.Mock()
    constructs = {"declaration_usage": {}}
    file_uri = "file://test.py"
    prop_cache = {"isDeclarationUsedBy": mock.Mock(), "usesDeclaration": mock.Mock()}
    uri_safe_string = lambda s: s
    relationship_writers.write_declaration_usage_relationships(
        g, constructs, file_uri, prop_cache, uri_safe_string
    )


def test_write_access_relationships_empty():
    g = mock.Mock()
    constructs = {"access_relationships": []}
    file_uri = "file://test.py"
    prop_cache = {"accesses": mock.Mock(), "isAccessedBy": mock.Mock()}
    uri_safe_string = lambda s: s
    relationship_writers.write_access_relationships(
        g, constructs, file_uri, prop_cache, uri_safe_string
    )


def test_write_type_relationships_empty():
    g = mock.Mock()
    constructs = {"type_relationships": []}
    file_uri = "file://test.py"
    prop_cache = {"hasType": mock.Mock()}
    uri_safe_string = lambda s: s
    relationship_writers.write_type_relationships(
        g, constructs, file_uri, prop_cache, uri_safe_string
    )


def test_write_declaration_usage_relationships_function_usages():
    g = mock.Mock()
    constructs = {
        "declaration_usage": {"function_usages": [{"usage": "foo"}]},
        "functions": [{"name": "foo"}],
    }
    file_uri = "file://test.py"
    prop_cache = {"callsFunction": mock.Mock(), "isCalledByFunctionAt": mock.Mock()}
    uri_safe_string = lambda s: s
    relationship_writers.write_declaration_usage_relationships(
        g, constructs, file_uri, prop_cache, uri_safe_string
    )


def test_write_declaration_usage_relationships_class_usages():
    g = mock.Mock()
    constructs = {
        "declaration_usage": {"class_usages": [{"usage": "Bar"}]},
        "classes": [{"name": "Bar"}],
    }
    file_uri = "file://test.py"
    prop_cache = {"extendsType": mock.Mock()}
    uri_safe_string = lambda s: s
    relationship_writers.write_declaration_usage_relationships(
        g, constructs, file_uri, prop_cache, uri_safe_string
    )


def test_write_declaration_usage_relationships_import_usages():
    g = mock.Mock()
    constructs = {
        "declaration_usage": {"import_usages": [{"import": "os"}]},
        "imports": [{"raw": "import os"}],
    }
    file_uri = "file://test.py"
    prop_cache = {"imports": mock.Mock()}
    uri_safe_string = lambda s: s
    relationship_writers.write_declaration_usage_relationships(
        g, constructs, file_uri, prop_cache, uri_safe_string
    )


def test_write_access_relationships_multiple():
    g = mock.Mock()
    constructs = {
        "access_relationships": [
            {"function": "foo", "attribute": "bar"},
            {"function": "baz", "attribute": "qux"},
        ]
    }
    file_uri = "file://test.py"
    prop_cache = {"accesses": mock.Mock(), "isAccessedBy": mock.Mock()}
    uri_safe_string = lambda s: s
    relationship_writers.write_access_relationships(
        g, constructs, file_uri, prop_cache, uri_safe_string
    )


def test_write_type_relationships_multiple():
    g = mock.Mock()
    constructs = {
        "type_relationships": [
            {"construct": "foo", "type": "int"},
            {"construct": "bar", "type": "str"},
        ]
    }
    file_uri = "file://test.py"
    prop_cache = {"hasType": mock.Mock()}
    uri_safe_string = lambda s: s
    relationship_writers.write_type_relationships(
        g, constructs, file_uri, prop_cache, uri_safe_string
    )


def test_write_embedding_relationships_with_calls():
    g = mock.Mock()
    constructs = {
        "functions": [{"name": "foo", "calls": [{"name": "bar"}, {"name": "baz"}]}],
        "FunctionDefinition": [],
    }
    file_uri = "file://test.py"
    prop_cache = {"embeds": mock.Mock()}
    uri_safe_string = lambda s: s
    relationship_writers.write_embedding_relationships(
        g, constructs, file_uri, prop_cache, uri_safe_string
    )


def test_write_styling_relationships_with_keywords_and_element():
    g = mock.Mock()
    constructs = {
        "functions": [{"name": "styleFunc", "raw": "element.style = 'color: red'"}],
        "variables": [{"name": "elementDiv"}],
    }
    file_uri = "file://test.py"
    prop_cache = {"styles": mock.Mock(), "isStyledBy": mock.Mock()}
    uri_safe_string = lambda s: s
    relationship_writers.write_styling_relationships(
        g, constructs, file_uri, prop_cache, uri_safe_string
    )
    assert g.add.called


def test_write_styling_relationships_no_keywords():
    g = mock.Mock()
    constructs = {
        "functions": [{"name": "noStyleFunc", "raw": "print('hello')"}],
        "variables": [{"name": "elementDiv"}],
    }
    file_uri = "file://test.py"
    prop_cache = {"styles": mock.Mock(), "isStyledBy": mock.Mock()}
    uri_safe_string = lambda s: s
    relationship_writers.write_styling_relationships(
        g, constructs, file_uri, prop_cache, uri_safe_string
    )
    # Should not call g.add since no styling keywords
    g.add.assert_not_called()


def test_extract_test_relationships_adds_relationships():
    g = mock.Mock()
    constructs = {
        "functions": [
            {"name": "test_func", "raw": "assert foo()"},
            {"name": "foo", "raw": "pass"},
        ]
    }
    file_uri = "file://test.py"
    prop_cache = {"tests": mock.Mock(), "isTestedBy": mock.Mock()}
    uri_safe_string = lambda s: s
    relationship_writers.extract_test_relationships(
        constructs, file_uri, prop_cache, uri_safe_string, g
    )
    assert g.add.called


def test_extract_test_relationships_no_test_keywords():
    g = mock.Mock()
    constructs = {
        "functions": [
            {"name": "foo", "raw": "bar()"},
            {"name": "bar", "raw": "pass"},
        ]
    }
    file_uri = "file://test.py"
    prop_cache = {"tests": mock.Mock(), "isTestedBy": mock.Mock()}
    uri_safe_string = lambda s: s
    relationship_writers.extract_test_relationships(
        constructs, file_uri, prop_cache, uri_safe_string, g
    )
    g.add.assert_not_called()
