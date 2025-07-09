from unittest import mock

import pytest

from app.extraction.writers import entity_writers


def make_prop_cache(*keys):
    # Helper to create a prop_cache with all needed keys
    return {k: mock.Mock() for k in keys}


def test_write_classes_runs():
    g = mock.Mock()
    constructs = {"ClassDefinition": [{"name": "TestClass"}]}
    file_uri = "file://test.py"
    class_cache = {"ClassDefinition": mock.Mock()}
    prop_cache = make_prop_cache("hasSimpleName", "hasCanonicalName")
    uri_safe_string = lambda s: s
    result = entity_writers.write_classes(
        g, constructs, file_uri, class_cache, prop_cache, uri_safe_string
    )
    assert isinstance(result, dict)


def test_write_classes_empty_constructs():
    g = mock.Mock()
    constructs = {"ClassDefinition": []}
    file_uri = "file://test.py"
    class_cache = {"ClassDefinition": mock.Mock()}
    prop_cache = make_prop_cache("hasSimpleName", "hasCanonicalName")
    uri_safe_string = lambda s: s
    result = entity_writers.write_classes(
        g, constructs, file_uri, class_cache, prop_cache, uri_safe_string
    )
    assert result == {}


def test_write_enums_runs():
    g = mock.Mock()
    constructs = {"EnumDefinition": [{"name": "TestEnum"}]}
    file_uri = "file://test.py"
    class_cache = {"EnumDefinition": mock.Mock(), "ClassDefinition": mock.Mock()}
    prop_cache = make_prop_cache(
        "hasSimpleName",
        "isElementOf",
        "hasSourceCodeSnippet",
        "startsAtLine",
        "endsAtLine",
        "hasTextValue",
    )
    uri_safe_string = lambda s: s
    result = entity_writers.write_enums(
        g, constructs, file_uri, class_cache, prop_cache, uri_safe_string
    )
    assert isinstance(result, dict)


def test_write_enums_missing_name():
    g = mock.Mock()
    constructs = {"EnumDefinition": [{"not_name": "nope"}]}
    file_uri = "file://test.py"
    class_cache = {"EnumDefinition": mock.Mock(), "ClassDefinition": mock.Mock()}
    prop_cache = make_prop_cache(
        "hasSimpleName",
        "isElementOf",
        "hasSourceCodeSnippet",
        "startsAtLine",
        "endsAtLine",
        "hasTextValue",
    )
    uri_safe_string = lambda s: s
    result = entity_writers.write_enums(
        g, constructs, file_uri, class_cache, prop_cache, uri_safe_string
    )
    assert result == {}


def test_write_enums_with_decorators_and_lines():
    g = mock.Mock()
    constructs = {
        "EnumDefinition": [
            {
                "name": "TestEnum",
                "raw": "enum code",
                "start_line": 1,
                "end_line": 2,
                "decorators": ["@dec"],
            }
        ]
    }
    file_uri = "file://test.py"
    class_cache = {"EnumDefinition": mock.Mock(), "ClassDefinition": mock.Mock()}
    prop_cache = make_prop_cache(
        "hasSimpleName",
        "isElementOf",
        "hasSourceCodeSnippet",
        "startsAtLine",
        "endsAtLine",
        "hasTextValue",
    )
    uri_safe_string = lambda s: s
    result = entity_writers.write_enums(
        g, constructs, file_uri, class_cache, prop_cache, uri_safe_string
    )
    assert "TestEnum" in result


def test_write_enums_with_all_optional_fields():
    g = mock.Mock()
    constructs = {
        "EnumDefinition": [
            {
                "name": "Color",
                "raw": "enum Color { RED, GREEN, BLUE }",
                "start_line": 1,
                "end_line": 3,
                "decorators": ["@enumDec"],
            }
        ]
    }
    file_uri = "file://test.py"
    class_cache = {"EnumDefinition": "EnumClass", "ClassDefinition": "ClassClass"}
    prop_cache = {
        "isElementOf": "isElementOf",
        "hasSimpleName": "hasSimpleName",
        "hasSourceCodeSnippet": "hasSourceCodeSnippet",
        "startsAtLine": "startsAtLine",
        "endsAtLine": "endsAtLine",
        "hasTextValue": "hasTextValue",
    }
    uri_safe_string = lambda s: s
    entity_writers.write_enums(
        g, constructs, file_uri, class_cache, prop_cache, uri_safe_string
    )
    assert g.add.call_count >= 6


def test_write_enums_missing_name_optional():
    g = mock.Mock()
    constructs = {"EnumDefinition": [{"raw": "enum {}"}]}
    file_uri = "file://test.py"
    class_cache = {"EnumDefinition": "EnumClass", "ClassDefinition": "ClassClass"}
    prop_cache = {"isElementOf": "isElementOf", "hasSimpleName": "hasSimpleName"}
    uri_safe_string = lambda s: s
    result = entity_writers.write_enums(
        g, constructs, file_uri, class_cache, prop_cache, uri_safe_string
    )
    assert result == {}
    g.add.assert_not_called()


def test_write_comments_runs():
    g = mock.Mock()
    constructs = {"CodeComment": [{"raw": "comment1"}]}
    file_uri = "file://test.py"
    class_cache = {"CodeComment": mock.Mock()}
    prop_cache = make_prop_cache("isElementOf", "hasTextValue")
    uri_safe_string = lambda s: s
    result = entity_writers.write_comments(
        g, constructs, file_uri, class_cache, prop_cache, uri_safe_string
    )
    assert isinstance(result, dict)


def test_write_comments_empty():
    g = mock.Mock()
    constructs = {"CodeComment": []}
    file_uri = "file://test.py"
    class_cache = {"CodeComment": mock.Mock()}
    prop_cache = make_prop_cache("isElementOf", "hasTextValue")
    uri_safe_string = lambda s: s
    result = entity_writers.write_comments(
        g, constructs, file_uri, class_cache, prop_cache, uri_safe_string
    )
    assert result == {}


def test_write_functions_runs():
    g = mock.Mock()
    constructs = {"FunctionDefinition": [{"name": "func1"}]}
    file_uri = "file://test.py"
    class_cache = {"FunctionDefinition": mock.Mock()}
    prop_cache = make_prop_cache("hasSimpleName", "hasCanonicalName")
    uri_safe_string = lambda s: s
    class_uris = {"TestClass": mock.Mock()}
    type_uris = {"TestType": mock.Mock()}
    result = entity_writers.write_functions(
        g,
        constructs,
        file_uri,
        class_cache,
        prop_cache,
        uri_safe_string,
        class_uris,
        type_uris,
    )
    assert isinstance(result, dict)


def test_write_functions_missing_name():
    g = mock.Mock()
    constructs = {"FunctionDefinition": [{"not_name": "nope"}]}
    file_uri = "file://test.py"
    class_cache = {"FunctionDefinition": mock.Mock()}
    prop_cache = make_prop_cache("hasSimpleName", "hasCanonicalName")
    uri_safe_string = lambda s: s
    class_uris = {"TestClass": mock.Mock()}
    type_uris = {"TestType": mock.Mock()}
    result = entity_writers.write_functions(
        g,
        constructs,
        file_uri,
        class_cache,
        prop_cache,
        uri_safe_string,
        class_uris,
        type_uris,
    )
    assert result == {}


def test_write_interfaces_runs():
    g = mock.Mock()
    constructs = {"InterfaceDefinition": [{"name": "TestInterface"}]}
    file_uri = "file://test.py"
    class_cache = {"InterfaceDefinition": mock.Mock(), "ClassDefinition": mock.Mock()}
    prop_cache = make_prop_cache(
        "hasSimpleName",
        "isElementOf",
        "hasSourceCodeSnippet",
        "startsAtLine",
        "endsAtLine",
        "hasTextValue",
    )
    uri_safe_string = lambda s: s
    result = entity_writers.write_interfaces(
        g, constructs, file_uri, class_cache, prop_cache, uri_safe_string
    )
    assert isinstance(result, dict)


def test_write_interfaces_with_decorators_and_lines():
    g = mock.Mock()
    constructs = {
        "InterfaceDefinition": [
            {
                "name": "TestInterface",
                "raw": "iface code",
                "start_line": 1,
                "end_line": 2,
                "decorators": ["@dec"],
            }
        ]
    }
    file_uri = "file://test.py"
    class_cache = {"InterfaceDefinition": mock.Mock(), "ClassDefinition": mock.Mock()}
    prop_cache = make_prop_cache(
        "hasSimpleName",
        "isElementOf",
        "hasSourceCodeSnippet",
        "startsAtLine",
        "endsAtLine",
        "hasTextValue",
    )
    uri_safe_string = lambda s: s
    result = entity_writers.write_interfaces(
        g, constructs, file_uri, class_cache, prop_cache, uri_safe_string
    )
    assert "TestInterface" in result


def test_write_interfaces_with_all_optional_fields():
    g = mock.Mock()
    constructs = {
        "InterfaceDefinition": [
            {
                "name": "MyInterface",
                "raw": "interface MyInterface {}",
                "start_line": 10,
                "end_line": 12,
                "decorators": ["@ifaceDec"],
            }
        ]
    }
    file_uri = "file://test.py"
    class_cache = {"InterfaceDefinition": "IfaceClass", "ClassDefinition": "ClassClass"}
    prop_cache = {
        "isElementOf": "isElementOf",
        "hasSimpleName": "hasSimpleName",
        "hasSourceCodeSnippet": "hasSourceCodeSnippet",
        "startsAtLine": "startsAtLine",
        "endsAtLine": "endsAtLine",
        "hasTextValue": "hasTextValue",
    }
    uri_safe_string = lambda s: s
    entity_writers.write_interfaces(
        g, constructs, file_uri, class_cache, prop_cache, uri_safe_string
    )
    assert g.add.call_count >= 6


def test_write_interfaces_missing_name():
    g = mock.Mock()
    constructs = {"InterfaceDefinition": [{"raw": "interface {}"}]}
    file_uri = "file://test.py"
    class_cache = {"InterfaceDefinition": "IfaceClass", "ClassDefinition": "ClassClass"}
    prop_cache = {"isElementOf": "isElementOf", "hasSimpleName": "hasSimpleName"}
    uri_safe_string = lambda s: s
    result = entity_writers.write_interfaces(
        g, constructs, file_uri, class_cache, prop_cache, uri_safe_string
    )
    assert result == {}
    g.add.assert_not_called()


def test_write_structs_runs():
    g = mock.Mock()
    constructs = {"StructDefinition": [{"name": "TestStruct"}]}
    file_uri = "file://test.py"
    class_cache = {"StructDefinition": mock.Mock(), "ClassDefinition": mock.Mock()}
    prop_cache = make_prop_cache(
        "hasSimpleName",
        "isElementOf",
        "hasSourceCodeSnippet",
        "startsAtLine",
        "endsAtLine",
        "hasTextValue",
    )
    uri_safe_string = lambda s: s
    result = entity_writers.write_structs(
        g, constructs, file_uri, class_cache, prop_cache, uri_safe_string
    )
    assert isinstance(result, dict)


def test_write_structs_with_raw_and_lines():
    g = mock.Mock()
    constructs = {
        "StructDefinition": [
            {"name": "TestStruct", "raw": "struct code", "start_line": 1, "end_line": 2}
        ]
    }
    file_uri = "file://test.py"
    class_cache = {"StructDefinition": mock.Mock(), "ClassDefinition": mock.Mock()}
    prop_cache = make_prop_cache(
        "hasSimpleName",
        "isElementOf",
        "hasSourceCodeSnippet",
        "startsAtLine",
        "endsAtLine",
        "hasTextValue",
    )
    uri_safe_string = lambda s: s
    result = entity_writers.write_structs(
        g, constructs, file_uri, class_cache, prop_cache, uri_safe_string
    )
    assert "TestStruct" in result


def test_write_structs_with_all_optional_fields():
    g = mock.Mock()
    constructs = {
        "StructDefinition": [
            {
                "name": "MyStruct",
                "raw": "struct MyStruct {}",
                "start_line": 20,
                "end_line": 22,
                "decorators": ["@structDec"],
            }
        ]
    }
    file_uri = "file://test.py"
    class_cache = {"StructDefinition": "StructClass", "ClassDefinition": "ClassClass"}
    prop_cache = {
        "isElementOf": "isElementOf",
        "hasSimpleName": "hasSimpleName",
        "hasSourceCodeSnippet": "hasSourceCodeSnippet",
        "startsAtLine": "startsAtLine",
        "endsAtLine": "endsAtLine",
        "hasTextValue": "hasTextValue",
    }
    uri_safe_string = lambda s: s
    entity_writers.write_structs(
        g, constructs, file_uri, class_cache, prop_cache, uri_safe_string
    )
    assert g.add.call_count >= 6


def test_write_structs_missing_name():
    g = mock.Mock()
    constructs = {"StructDefinition": [{"raw": "struct {}"}]}
    file_uri = "file://test.py"
    class_cache = {"StructDefinition": "StructClass", "ClassDefinition": "ClassClass"}
    prop_cache = {"isElementOf": "isElementOf", "hasSimpleName": "hasSimpleName"}
    uri_safe_string = lambda s: s
    result = entity_writers.write_structs(
        g, constructs, file_uri, class_cache, prop_cache, uri_safe_string
    )
    assert result == {}
    g.add.assert_not_called()


def test_write_traits_runs():
    g = mock.Mock()
    constructs = {"TraitDefinition": [{"name": "TestTrait"}]}
    file_uri = "file://test.py"
    class_cache = {"TraitDefinition": mock.Mock(), "ClassDefinition": mock.Mock()}
    prop_cache = make_prop_cache(
        "hasSimpleName",
        "isElementOf",
        "hasSourceCodeSnippet",
        "startsAtLine",
        "endsAtLine",
        "hasTextValue",
    )
    uri_safe_string = lambda s: s
    result = entity_writers.write_traits(
        g, constructs, file_uri, class_cache, prop_cache, uri_safe_string
    )
    assert isinstance(result, dict)


def test_write_traits_with_all_optional_fields():
    g = mock.Mock()
    constructs = {
        "TraitDefinition": [
            {
                "name": "MyTrait",
                "raw": "trait MyTrait {}",
                "start_line": 30,
                "end_line": 32,
                "decorators": ["@traitDec"],
            }
        ]
    }
    file_uri = "file://test.py"
    class_cache = {
        "TraitDefinition": "TraitClass",
        "InterfaceDefinition": "IfaceClass",
        "ClassDefinition": "ClassClass",
    }
    prop_cache = {
        "isElementOf": "isElementOf",
        "hasSimpleName": "hasSimpleName",
        "hasSourceCodeSnippet": "hasSourceCodeSnippet",
        "startsAtLine": "startsAtLine",
        "endsAtLine": "endsAtLine",
        "hasTextValue": "hasTextValue",
    }
    uri_safe_string = lambda s: s
    entity_writers.write_traits(
        g, constructs, file_uri, class_cache, prop_cache, uri_safe_string
    )
    assert g.add.call_count >= 6


def test_write_traits_missing_name():
    g = mock.Mock()
    constructs = {"TraitDefinition": [{"raw": "trait {}"}]}
    file_uri = "file://test.py"
    class_cache = {
        "TraitDefinition": "TraitClass",
        "InterfaceDefinition": "IfaceClass",
        "ClassDefinition": "ClassClass",
    }
    prop_cache = {"isElementOf": "isElementOf", "hasSimpleName": "hasSimpleName"}
    uri_safe_string = lambda s: s
    result = entity_writers.write_traits(
        g, constructs, file_uri, class_cache, prop_cache, uri_safe_string
    )
    assert result == {}
    g.add.assert_not_called()


def test_write_modules_runs():
    g = mock.Mock()
    constructs = {"ModuleDefinition": [{"name": "TestModule"}]}
    file_uri = "file://test.py"
    class_cache = {"ModuleDefinition": mock.Mock(), "ClassDefinition": mock.Mock()}
    prop_cache = make_prop_cache(
        "hasSimpleName",
        "isElementOf",
        "hasSourceCodeSnippet",
        "startsAtLine",
        "endsAtLine",
        "hasTextValue",
    )
    uri_safe_string = lambda s: s
    result = entity_writers.write_modules(
        g, constructs, file_uri, class_cache, prop_cache, uri_safe_string
    )
    assert isinstance(result, dict)


def test_write_modules_with_all_optional_fields():
    g = mock.Mock()
    constructs = {
        "PackageDeclaration": [
            {
                "name": "MyModule",
                "raw": "module MyModule {}",
                "start_line": 40,
                "end_line": 42,
            }
        ]
    }
    file_uri = "file://test.py"
    class_cache = {"PackageDeclaration": "PkgClass"}
    prop_cache = {
        "isElementOf": "isElementOf",
        "hasSimpleName": "hasSimpleName",
        "hasSourceCodeSnippet": "hasSourceCodeSnippet",
        "startsAtLine": "startsAtLine",
        "endsAtLine": "endsAtLine",
    }
    uri_safe_string = lambda s: s
    entity_writers.write_modules(
        g, constructs, file_uri, class_cache, prop_cache, uri_safe_string
    )
    assert g.add.call_count >= 5


def test_write_modules_missing_name():
    g = mock.Mock()
    constructs = {"modules": [{"raw": "module {}"}]}
    file_uri = "file://test.py"
    class_cache = {"PackageDeclaration": "PkgClass"}
    prop_cache = {"isElementOf": "isElementOf", "hasSimpleName": "hasSimpleName"}
    uri_safe_string = lambda s: s
    result = entity_writers.write_modules(
        g, constructs, file_uri, class_cache, prop_cache, uri_safe_string
    )
    assert result == {}
    g.add.assert_not_called()


def test_write_decorators_runs():
    g = mock.Mock()
    constructs = {"DecoratorDefinition": [{"name": "TestDecorator"}]}
    file_uri = "file://test.py"
    class_cache = {"DecoratorDefinition": mock.Mock()}
    prop_cache = make_prop_cache("hasSimpleName", "isElementOf", "hasTextValue")
    uri_safe_string = lambda s: s
    # Should not raise (returns None)
    entity_writers.write_decorators(
        g, constructs, file_uri, class_cache, prop_cache, uri_safe_string
    )


def test_write_types_runs():
    g = mock.Mock()
    constructs = {"TypeDefinition": [{"name": "TestType"}]}
    file_uri = "file://test.py"
    class_cache = {"TypeDefinition": mock.Mock()}
    prop_cache = make_prop_cache("hasSimpleName", "isElementOf", "hasTextValue")
    uri_safe_string = lambda s: s
    # Should not raise (returns None)
    entity_writers.write_types(
        g, constructs, file_uri, class_cache, prop_cache, uri_safe_string
    )


def test_write_imports_runs():
    g = mock.Mock()
    constructs = {"ImportDeclaration": [{"raw": "import os"}]}
    file_uri = "file://test.py"
    class_cache = {"ImportDeclaration": mock.Mock()}
    prop_cache = make_prop_cache("imports", "hasTextValue")
    uri_safe_string = lambda s: s
    # Should not raise (returns None)
    entity_writers.write_imports(
        g, constructs, file_uri, class_cache, prop_cache, uri_safe_string
    )


def test_write_imports_empty():
    g = mock.Mock()
    constructs = {"ImportDeclaration": []}
    file_uri = "file://test.py"
    class_cache = {"ImportDeclaration": mock.Mock()}
    prop_cache = make_prop_cache("imports", "hasTextValue")
    uri_safe_string = lambda s: s
    # Should not raise
    entity_writers.write_imports(
        g, constructs, file_uri, class_cache, prop_cache, uri_safe_string
    )


def test_write_repo_file_link_runs():
    g = mock.Mock()
    repo_enc = "repo1"
    WDO = mock.Mock()
    INST = {"repo1": mock.Mock()}
    file_uri = "file://test.py"
    # Should not raise
    entity_writers.write_repo_file_link(g, repo_enc, WDO, INST, file_uri)


def test_write_database_schemas_runs():
    g = mock.Mock()
    constructs = {"DatabaseSchema": [{"name": "TestSchema"}]}
    file_uri = "file://test.py"
    class_cache = {"DatabaseSchema": mock.Mock()}
    prop_cache = make_prop_cache("hasSimpleName", "isElementOf", "hasTextValue")
    uri_safe_string = lambda s: s
    # Should not raise
    entity_writers.write_database_schemas(
        g, constructs, file_uri, class_cache, prop_cache, uri_safe_string
    )


def test__add_class_basic_triples():
    g = mock.Mock()
    class_uri = "uri"
    class_id = "TestClass"
    class_cache = {"ClassDefinition": mock.Mock()}
    prop_cache = {"hasSimpleName": mock.Mock()}
    # Should not raise
    entity_writers._add_class_basic_triples(
        g, class_uri, class_id, class_cache, prop_cache
    )


def test__add_class_optional_properties():
    g = mock.Mock()
    class_uri = "uri"
    cls = {"canonical_name": "TestClass", "raw": "class code"}
    prop_cache = {
        "hasCanonicalName": mock.Mock(),
        "hasSourceCodeSnippet": mock.Mock(),
        "hasTokenCount": mock.Mock(),
        "hasAccessModifier": mock.Mock(),
        "hasLineCount": mock.Mock(),
    }
    # Should not raise
    entity_writers._add_class_optional_properties(g, class_uri, cls, prop_cache)


def test__collect_class_methods():
    cls = {"methods": [{"name": "foo"}, {"name": "bar"}]}
    result = entity_writers._collect_class_methods(cls)
    assert isinstance(result, list)
    assert result == ["foo", "bar"]


def test_write_parameters_all_fields():
    g = mock.Mock()
    constructs = {
        "Parameter": [
            {
                "name": "param1",
                "raw": "int param1",
                "type": "int",
                "start_line": 1,
                "end_line": 2,
                "parent_function": "foo",
            }
        ]
    }
    file_uri = "file://test.py"
    class_cache = {"Parameter": "ParamClass"}
    prop_cache = {
        "hasSimpleName": "hasSimpleName",
        "hasSourceCodeSnippet": "hasSourceCodeSnippet",
        "hasType": "hasType",
        "startsAtLine": "startsAtLine",
        "endsAtLine": "endsAtLine",
        "isParameterOf": "isParameterOf",
        "hasParameter": "hasParameter",
    }
    uri_safe_string = lambda s: s
    func_uris = {"foo": "foo_uri"}
    type_uris = {"int": "int_uri"}
    entity_writers.write_parameters(
        g,
        constructs,
        file_uri,
        class_cache,
        prop_cache,
        uri_safe_string,
        func_uris,
        type_uris,
    )
    assert g.add.call_count >= 8


def test_write_parameters_missing_optional_fields():
    g = mock.Mock()
    constructs = {"Parameter": [{"name": "param2"}]}
    file_uri = "file://test.py"
    class_cache = {"Parameter": "ParamClass"}
    prop_cache = {"hasSimpleName": "hasSimpleName"}
    uri_safe_string = lambda s: s
    func_uris = {}
    type_uris = {}
    entity_writers.write_parameters(
        g,
        constructs,
        file_uri,
        class_cache,
        prop_cache,
        uri_safe_string,
        func_uris,
        type_uris,
    )
    assert g.add.call_count == 2


def test_write_variables_all_fields():
    g = mock.Mock()
    constructs = {
        "VariableDeclaration": [
            {
                "name": "var1",
                "raw": "int var1",
                "type": "int",
                "start_line": 3,
                "end_line": 4,
            }
        ]
    }
    file_uri = "file://test.py"
    class_cache = {"VariableDeclaration": "VarClass"}
    prop_cache = {
        "hasSimpleName": "hasSimpleName",
        "hasSourceCodeSnippet": "hasSourceCodeSnippet",
        "hasType": "hasType",
        "startsAtLine": "startsAtLine",
        "endsAtLine": "endsAtLine",
    }
    uri_safe_string = lambda s: s
    func_uris = {}
    type_uris = {"int": "int_uri"}
    entity_writers.write_variables(
        g,
        constructs,
        file_uri,
        class_cache,
        prop_cache,
        uri_safe_string,
        func_uris,
        type_uris,
    )
    assert g.add.call_count >= 6


def test_write_variables_missing_optional_fields():
    g = mock.Mock()
    constructs = {"VariableDeclaration": [{"name": "var2"}]}
    file_uri = "file://test.py"
    class_cache = {"VariableDeclaration": "VarClass"}
    prop_cache = {"hasSimpleName": "hasSimpleName"}
    uri_safe_string = lambda s: s
    func_uris = {}
    type_uris = {}
    entity_writers.write_variables(
        g,
        constructs,
        file_uri,
        class_cache,
        prop_cache,
        uri_safe_string,
        func_uris,
        type_uris,
    )
    assert g.add.call_count == 2


def test_write_calls_all_fields():
    g = mock.Mock()
    constructs = {
        "FunctionCallSite": [
            {
                "name": "call1",
                "raw": "foo(1, 2)",
                "start_line": 5,
                "end_line": 6,
                "arguments": ["arg1", {"name": "arg2"}],
                "calls": ["foo"],
            }
        ]
    }
    file_uri = "file://test.py"
    class_cache = {"FunctionCallSite": "CallClass"}
    prop_cache = {
        "hasSimpleName": "hasSimpleName",
        "hasSourceCodeSnippet": "hasSourceCodeSnippet",
        "startsAtLine": "startsAtLine",
        "endsAtLine": "endsAtLine",
        "hasArgument": "hasArgument",
        "isArgumentIn": "isArgumentIn",
        "callsFunction": "callsFunction",
        "isCalledByFunctionAt": "isCalledByFunctionAt",
    }
    uri_safe_string = lambda s: s
    func_uris = {"foo": "foo_uri"}
    type_uris = {}
    entity_writers.write_calls(
        g,
        constructs,
        file_uri,
        class_cache,
        prop_cache,
        uri_safe_string,
        func_uris,
        type_uris,
    )
    assert g.add.call_count >= 11


def test_write_calls_missing_optional_fields():
    g = mock.Mock()
    constructs = {"FunctionCallSite": [{"name": "call2"}]}
    file_uri = "file://test.py"
    class_cache = {"FunctionCallSite": "CallClass"}
    prop_cache = {"hasSimpleName": "hasSimpleName"}
    uri_safe_string = lambda s: s
    func_uris = {}
    type_uris = {}
    entity_writers.write_calls(
        g,
        constructs,
        file_uri,
        class_cache,
        prop_cache,
        uri_safe_string,
        func_uris,
        type_uris,
    )
    assert g.add.call_count == 2


def test_write_decorators_all_fields():
    g = mock.Mock()
    constructs = {
        "decorators": [{"raw": "@dec", "name": "dec"}, {"name": "dec2"}, "plainstring"]
    }
    file_uri = "file://test.py"
    class_cache = {"Decorator": "DecClass"}
    prop_cache = {
        "isElementOf": "isElementOf",
        "hasSimpleName": "hasSimpleName",
        "hasSourceCodeSnippet": "hasSourceCodeSnippet",
    }
    uri_safe_string = lambda s: s
    entity_writers.write_decorators(
        g, constructs, file_uri, class_cache, prop_cache, uri_safe_string
    )
    assert g.add.call_count >= 6
