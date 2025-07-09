import ast

import pytest

from app.extraction.utils import ast_extraction


def test_extract_access_modifier_basic():
    # Test with explicit modifier in code
    entity = {"name": "foo"}
    assert (
        ast_extraction.extract_access_modifier(entity, "public class Foo") == "public"
    )
    assert ast_extraction.extract_access_modifier(entity, "private int x") == "private"
    assert (
        ast_extraction.extract_access_modifier(entity, "protected void bar()")
        == "protected"
    )
    assert (
        ast_extraction.extract_access_modifier(entity, "internal class Bar")
        == "internal"
    )
    assert (
        ast_extraction.extract_access_modifier(entity, "package class Baz") == "package"
    )

    # Test with underscore name (should return None if raw_code is empty)
    entity = {"name": "_hidden"}
    assert ast_extraction.extract_access_modifier(entity, "") is None

    # Test with no modifier
    entity = {"name": "visible"}
    assert ast_extraction.extract_access_modifier(entity, "def visible(): pass") is None


def test_extract_python_entities_simple():
    code = """
class MyClass(Base):
    x = 1
    def foo(self):
        pass

def bar():
    return 42
"""
    tree = ast.parse(code)
    summary = {}
    ast_extraction.extract_python_entities(tree, summary)
    # Check that class and function are extracted
    class_names = [c["name"] for c in summary["classes"]]
    function_names = [f["name"] for f in summary["functions"]]
    assert "MyClass" in class_names
    assert "bar" in function_names
    # Check that method is extracted
    method_names = [m["name"] for m in summary["methods"]]
    assert "foo" in method_names
    # Check that field is extracted
    field_names = [f["name"] for c in summary["classes"] for f in c["fields"]]
    assert "x" in field_names


def test_extract_python_entities_nested_enum_decorator_annassign_import():
    code = """
import os
from math import sqrt

class Outer:
    class Inner:
        pass
    @staticmethod
    def static_method():
        pass
    y: int = 5

class Color(enum.Enum):
    RED = 1
    GREEN = 2
    BLUE = 3
"""
    tree = ast.parse(code)
    summary = {}
    ast_extraction.extract_python_entities(tree, summary)
    # Imports
    import_raws = [i["raw"] for i in summary["imports"]]
    assert any("import os" in r for r in import_raws)
    assert any("from math import sqrt" in r for r in import_raws)
    # Nested class Outer is present, Inner is not extracted
    class_names = [c["name"] for c in summary["classes"]]
    assert "Outer" in class_names
    # Static method with decorator
    static = [m for m in summary["methods"] if m["name"] == "static_method"]
    assert static and any("staticmethod" in d for d in static[0]["decorators"])
    # Annotated assignment
    fields = [
        f for c in summary["classes"] if c["name"] == "Outer" for f in c["fields"]
    ]
    assert any(f["name"] == "y" and f["type"] == "int" for f in fields)
    # Enum
    enums = summary.get("EnumDeclaration", [])
    assert any(e["name"] == "Color" for e in enums)


def test_extract_python_entities_global_vars_and_importfrom():
    code = """
from sys import path, version
x = 10
y: float = 2.5
"""
    tree = ast.parse(code)
    summary = {}
    ast_extraction.extract_python_entities(tree, summary)
    # Check import-from
    importfroms = [i["raw"] for i in summary["imports"]]
    assert any("from sys import path" in r for r in importfroms)
    assert any("from sys import version" in r for r in importfroms)
    # Check global variable
    var_names = [v["name"] for v in summary["VariableDeclaration"]]
    assert "x" in var_names
    # Check global annotated variable
    assert "y" in var_names


# Tree-sitter based tests would require a tree-sitter parser and queries, so are omitted here.


def test_extract_python_entities_async_and_multiple_inheritance():
    code = """
class Base1: pass
class Base2: pass
class MyInterface: pass
class Child(Base1, Base2, MyInterface):
    async def afunc(self):
        pass
"""
    tree = ast.parse(code)
    summary = {}
    ast_extraction.extract_python_entities(tree, summary)
    # Multiple inheritance
    extends = summary["extends"]
    child_bases = [e["base"] for e in extends if e["class"] == "Child"]
    assert set(child_bases) == {"Base1", "Base2", "MyInterface"}
    # Implements (interface)
    implements = summary.get("implements", [])
    assert any(
        i["class"] == "Child" and i["interface"] == "MyInterface" for i in implements
    )
    # Async method
    method_names = [m["name"] for m in summary["methods"]]
    assert "afunc" in method_names


def test_extract_python_entities_global_var_multiple_targets_and_decorators():
    code = """
a = b = 1

@decorator1
@decorator2
class Decorated:
    @classmethod
    @staticmethod
    def m(cls): pass
"""
    tree = ast.parse(code)
    summary = {}
    ast_extraction.extract_python_entities(tree, summary)
    # Multiple global variables
    var_names = [v["name"] for v in summary["VariableDeclaration"]]
    assert "a" in var_names and "b" in var_names
    # Class with multiple decorators
    class_decorators = [
        c["decorators"] for c in summary["classes"] if c["name"] == "Decorated"
    ]
    assert class_decorators and any("decorator1" in d for d in class_decorators[0])
    assert any("decorator2" in d for d in class_decorators[0])
    # Method with multiple decorators
    method_decorators = [
        m["decorators"] for m in summary["methods"] if m["name"] == "m"
    ]
    assert method_decorators and any("classmethod" in d for d in method_decorators[0])
    assert any("staticmethod" in d for d in method_decorators[0])
