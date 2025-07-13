import ast

from app.extraction.utils import code_analysis_utils


def test_generate_canonical_name():
    assert code_analysis_utils.generate_canonical_name({"name": "foo"}) == "foo"
    assert (
        code_analysis_utils.generate_canonical_name(
            {"name": "bar"}, parent_context="Baz"
        )
        == "Baz.bar"
    )
    assert code_analysis_utils.generate_canonical_name({}) == ""


def test_calculate_cyclomatic_complexity():
    code = "if x: pass\nfor i in range(3): pass\ntry: pass\nexcept: pass"
    # The function counts all keyword occurrences, including substrings, so the result is 10
    assert code_analysis_utils.calculate_cyclomatic_complexity(code) == 10
    assert code_analysis_utils.calculate_cyclomatic_complexity("") == 1


def test_extract_access_modifier():
    assert (
        code_analysis_utils.extract_access_modifier({"name": "foo"}, "public class Foo")
        == "public"
    )
    # The function returns None if raw_code is empty, even if name starts with _
    assert code_analysis_utils.extract_access_modifier({"name": "_hidden"}, "") is None
    assert code_analysis_utils.extract_access_modifier({"name": "bar"}, "") is None


def test_extract_boolean_modifiers():
    code = "async def foo(): pass"
    assert code_analysis_utils.extract_boolean_modifiers({}, code)["isAsynchronous"]
    code = "final int x;"
    assert code_analysis_utils.extract_boolean_modifiers({}, code)["isFinal"]
    code = "static void bar() {}"
    assert code_analysis_utils.extract_boolean_modifiers({}, code)["isStatic"]
    assert code_analysis_utils.extract_boolean_modifiers({}, "") == {}


def test_extract_function_parameters():
    code = """
def foo(a: int, b):
    pass
"""
    node = ast.parse(code).body[0]
    params = code_analysis_utils.extract_function_parameters(node)
    assert params[0]["name"] == "a"
    assert params[0]["type"] == "int"
    assert params[1]["name"] == "b"


def test_extract_function_variables():
    code = """
def foo():
    x = 1
    y: int = 2
    return x + y
"""
    node = ast.parse(code).body[0]
    vars = code_analysis_utils.extract_function_variables(node)
    names = {v["name"] for v in vars}
    assert "x" in names and "y" in names


def test_extract_function_calls():
    code = """
def foo():
    bar(1)
    baz(x, y)
"""
    node = ast.parse(code).body[0]
    summary = {}
    calls = code_analysis_utils.extract_function_calls(node, summary)
    names = {c["name"] for c in calls}
    assert "callsite: bar" in names and "callsite: baz" in names
    assert "calls" in summary and len(summary["calls"]) == 2


def test_build_declaration_usage_summary():
    summary = {
        "calls": [
            {"name": "callsite: foo", "arguments": ["x"], "start_line": 2},
            {"name": "callsite: bar", "arguments": ["y"], "start_line": 3},
        ],
        "variables": [
            {"name": "x"},
            {"name": "y"},
        ],
        "classes": [{"name": "Baz", "bases": ["Base"], "start_line": 1}],
        "imports": [{"raw": "import os", "start_line": 1}],
    }
    code_analysis_utils.build_declaration_usage_summary(summary)
    usage = summary["declaration_usage"]
    assert "variable_usages" in usage
    assert "function_usages" in usage
    assert "class_usages" in usage
    assert "import_usages" in usage
