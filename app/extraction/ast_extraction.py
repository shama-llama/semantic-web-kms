import ast
import logging
from typing import Any, Dict, Optional, Union

from tree_sitter_languages import get_language

logger = logging.getLogger("ast_extraction")

# --- AST Extraction Functions ---


def extract_access_modifier(
    entity_info: Dict[str, Any], raw_code: str
) -> Optional[str]:
    """Extract access modifier from code construct."""
    if not raw_code:
        return None
    access_modifiers = ["public", "private", "protected", "internal", "package"]
    for modifier in access_modifiers:
        if modifier in raw_code.lower():
            return modifier
    name = entity_info.get("name", "")
    if name.startswith("_"):
        return "private"
    return None


def extract_python_entities(
    node: ast.AST, summary: Dict[str, Any], *, parent_class: Optional[str] = None
) -> None:
    """Recursively extract Python entities from AST node and update summary."""
    for key in [
        "classes",
        "extends",
        "methods",
        "functions",
        "imports",
        "parameters",
        "variables",
        "fields",
        "decorators",
        "calls",
        "types",
        "EnumDeclaration",
        "VariableDeclaration",
    ]:
        summary.setdefault(key, [])
    if isinstance(node, ast.ClassDef):
        handle_classdef(node, summary, parent_class=parent_class)
    elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        handle_functiondef(node, summary, parent_class=parent_class)
    elif isinstance(node, ast.Import):
        handle_import(node, summary)
    elif isinstance(node, ast.ImportFrom):
        handle_importfrom(node, summary)
    elif isinstance(node, ast.Assign) and parent_class is None:
        handle_global_variable(node, summary)
    elif isinstance(node, ast.AnnAssign) and parent_class is None:
        handle_global_ann_assign(node, summary)
    for child in ast.iter_child_nodes(node):
        extract_python_entities(child, summary, parent_class=parent_class)


def extract_tree_sitter_entities(
    lang_name: str,
    tree_root: Any,
    code_bytes: bytes,
    queries: Dict[str, Any],
    summary: Dict[str, Any],
) -> None:
    """Extract entities from tree-sitter AST using language-specific queries."""
    language = get_language(lang_name)
    if not language:
        return
    capture_to_key = {
        "class": "ClassDefinition",
        "struct": "StructDefinition",
        "interface": "InterfaceDefinition",
        "enum": "EnumDefinition",
        "trait": "TraitDefinition",
        "type": "ClassDefinition",
        "object": "VariableDeclaration",
        "protocol": "InterfaceDefinition",
        "function": "FunctionDefinition",
        "method": "FunctionDefinition",
        "constructor": "FunctionDefinition",
        "param": "Parameter",
        "parameter": "Parameter",
        "attr": "AttributeDeclaration",
        "field": "AttributeDeclaration",
        "variable": "VariableDeclaration",
        "import": "ImportDeclaration",
        "func": "FunctionCall",
        "call": "FunctionCall",
        "comment": "CodeComment",
        "module": "PackageDeclaration",
    }
    query_results = _run_tree_sitter_queries(
        language, tree_root, code_bytes, queries, lang_name
    )
    for captures, query_name in query_results:
        _extract_tree_sitter_entities_from_captures(
            captures, code_bytes, capture_to_key, summary
        )


def extract_function_calls(node, summary):
    calls = []
    for subnode in ast.walk(node):
        if isinstance(subnode, ast.Call):
            if isinstance(subnode.func, ast.Name):
                call_name = subnode.func.id
            elif isinstance(subnode.func, ast.Attribute):
                call_name = ast.unparse(subnode.func) if hasattr(ast, "unparse") else ""
            else:
                call_name = ""
            if call_name:
                args = []
                for arg in subnode.args:
                    if isinstance(arg, ast.Name):
                        args.append(arg.id)
                    elif hasattr(ast, "unparse"):
                        args.append(ast.unparse(arg))
                    else:
                        args.append(str(arg))
                call_info = {"name": call_name, "arguments": args}
                calls.append(call_info)
                summary.setdefault("calls", []).append(call_info)
    return calls


def calculate_cyclomatic_complexity(raw_code: str) -> int:
    """Calculate cyclomatic complexity of a code construct."""
    if not raw_code:
        return 1
    complexity = 1
    decision_keywords = [
        "if",
        "elif",
        "else",
        "for",
        "while",
        "case",
        "catch",
        "except",
        "&&",
        "||",
        "and",
        "or",
        "?",
        ":",
        "switch",
        "try",
    ]
    for keyword in decision_keywords:
        complexity += raw_code.lower().count(keyword)
    return complexity


def handle_classdef(
    node: ast.ClassDef, summary: Dict[str, Any], *, parent_class: Optional[str] = None
):
    """Extract class definition info from Python AST node."""
    class_info: dict[str, Any] = {
        "raw": f"class {node.name}(...):",
        "name": node.name,
        "start_line": node.lineno,
        "end_line": getattr(node, "end_lineno", node.lineno),
        "bases": [
            getattr(base, "id", getattr(base, "attr", str(base))) for base in node.bases
        ],
        "methods": [],
        "fields": [],
        "decorators": [
            ast.unparse(dec) if hasattr(ast, "unparse") else ""
            for dec in node.decorator_list
        ],
    }
    is_enum = False
    for base in node.bases:
        base_name = getattr(base, "id", "")
        if "enum" in base_name.lower():
            is_enum = True
            break
        if isinstance(base, ast.Attribute):
            if (
                hasattr(base, "value")
                and isinstance(base.value, ast.Name)
                and base.value.id == "enum"
                and hasattr(base, "attr")
                and base.attr == "Enum"
            ):
                is_enum = True
                break
    for base in node.bases:
        base_name = getattr(base, "id", getattr(base, "attr", str(base)))
        if base_name.lower().endswith("interface"):
            summary.setdefault("implements", []).append(
                {"class": node.name, "interface": base_name}
            )
    for body_item in node.body:
        if isinstance(body_item, ast.Assign):
            for target in body_item.targets:
                if isinstance(target, ast.Name):
                    field_info = {
                        "name": target.id,
                        "start_line": body_item.lineno,
                        "end_line": getattr(body_item, "end_lineno", body_item.lineno),
                        "type": (
                            ast.unparse(body_item.value)
                            if hasattr(ast, "unparse")
                            else type(body_item.value).__name__
                        ),
                    }
                    class_info["fields"].append(field_info)
        elif isinstance(body_item, ast.AnnAssign):
            if isinstance(body_item.target, ast.Name):
                field_info = {
                    "name": body_item.target.id,
                    "start_line": body_item.lineno,
                    "end_line": getattr(body_item, "end_lineno", body_item.lineno),
                    "type": (
                        ast.unparse(body_item.annotation)
                        if hasattr(ast, "unparse")
                        else str(body_item.annotation)
                    ),
                }
                class_info["fields"].append(field_info)
    for body_item in node.body:
        if isinstance(body_item, (ast.FunctionDef, ast.AsyncFunctionDef)):
            handle_functiondef(body_item, summary, parent_class=node.name)
    if parent_class:
        summary["methods"].append(class_info)
    elif is_enum:
        summary.setdefault("EnumDeclaration", []).append(class_info)
        logger.info(f"Extracted enum (python): {class_info}")
    else:
        summary["classes"].append(class_info)
        logger.info(f"Extracted class (python): {class_info}")
    for base in class_info["bases"]:
        summary["extends"].append({"class": node.name, "base": base})


def handle_functiondef(
    node: Union[ast.FunctionDef, ast.AsyncFunctionDef],
    summary: Dict[str, Any],
    *,
    parent_class: Optional[str] = None,
):
    """Extract function definition info from Python AST node."""
    func_info: dict[str, Any] = {
        "raw": f"def {node.name}(...):",
        "name": node.name,
        "start_line": node.lineno,
        "end_line": getattr(node, "end_lineno", node.lineno),
        "parameters": [],
        "variables": [],
        "calls": extract_function_calls(node, summary),
        "decorators": [
            ast.unparse(dec) if hasattr(ast, "unparse") else ""
            for dec in node.decorator_list
        ],
        "returns": (
            ast.unparse(node.returns)
            if node.returns and hasattr(ast, "unparse")
            else (str(node.returns) if node.returns else None)
        ),
        "parent_class": parent_class,
    }
    if parent_class:
        summary["methods"].append(func_info)
    else:
        summary["functions"].append(func_info)
    logger.info(f"Extracted function (python): {func_info}")


def handle_import(node: ast.Import, summary: Dict[str, Any]):
    for alias in node.names:
        import_info = {"raw": f"import {alias.name}"}
        summary["imports"].append(import_info)
        logger.info(f"Extracted import (python): {import_info}")


def handle_importfrom(node: ast.ImportFrom, summary: Dict[str, Any]):
    module = node.module or "."
    for alias in node.names:
        import_info = {"raw": f"from {module} import {alias.name}"}
        summary["imports"].append(import_info)
        logger.info(f"Extracted import-from (python): {import_info}")


def handle_global_variable(node: ast.Assign, summary: Dict[str, Any]):
    for target in node.targets:
        if isinstance(target, ast.Name):
            var_info = {
                "name": target.id,
                "start_line": node.lineno,
                "end_line": getattr(node, "end_lineno", node.lineno),
                "type": (
                    ast.unparse(node.value)
                    if hasattr(ast, "unparse")
                    else type(node.value).__name__
                ),
            }
            summary.setdefault("VariableDeclaration", []).append(var_info)
            logger.info(f"Extracted global variable (python): {var_info}")


def handle_global_ann_assign(node: ast.AnnAssign, summary: Dict[str, Any]):
    if isinstance(node.target, ast.Name):
        var_info = {
            "name": node.target.id,
            "start_line": node.lineno,
            "end_line": getattr(node, "end_lineno", node.lineno),
            "type": (
                ast.unparse(node.annotation)
                if hasattr(ast, "unparse")
                else str(node.annotation)
            ),
        }
        summary.setdefault("VariableDeclaration", []).append(var_info)
        logger.info(f"Extracted global annotated variable (python): {var_info}")


def _run_tree_sitter_queries(language, tree_root, code_bytes, queries, lang_name):
    results = []
    for query_name, query_list in queries.get(lang_name, {}).items():
        for query_str in query_list:
            try:
                logger.info(
                    f"Running query for {lang_name} - {query_name}: {query_str}"
                )
                query = language.query(query_str)
                captures = query.captures(tree_root)
                results.append((captures, query_name))
            except Exception as e:
                logger.warning(f"Query {query_name} failed for {lang_name}: {e}")
                continue
    return results


def _node_text(node, code_bytes):
    """Extract text from a tree-sitter node."""
    return (
        code_bytes[node.start_byte : node.end_byte]
        .decode("utf-8", errors="ignore")
        .strip()
    )


def _extract_tree_sitter_entities_from_captures(
    captures, code_bytes, capture_to_key, summary
):
    """Extract entities from tree-sitter captures and update summary."""
    from collections import defaultdict

    node_captures = defaultdict(list)
    for node, capture_name in captures:
        node_captures[id(node)].append((node, capture_name))
    container_captures = []
    container_types = {
        "function",
        "class",
        "method",
        "type",
        "struct",
        "interface",
        "enum",
        "trait",
        "module",
        "object",
        "protocol",
    }
    for node, capture_name in captures:
        if capture_name in container_types:
            container_captures.append((node, capture_name))
    for node, capture_name in container_captures:
        entity_info = {
            "raw": _node_text(node, code_bytes),
            "start_line": node.start_point[0] + 1,
            "end_line": node.end_point[1] + 1,
        }

        def walk_subtree(n):
            for child in n.children:
                for cnode, cname in captures:
                    if cnode == child:
                        yield (child, cname)
                yield from walk_subtree(child)

        for child, child_capture in walk_subtree(node):
            text = _node_text(child, code_bytes)
            if child_capture == "name":
                entity_info["name"] = text
            elif child_capture == "param":
                entity_info.setdefault("parameters", []).append(text)
            elif child_capture == "attr":
                entity_info.setdefault("fields", []).append(text)
            elif child_capture == "decorator":
                entity_info.setdefault("decorators", []).append(text)
            elif child_capture == "type":
                entity_info.setdefault("types", []).append(text)
            elif child_capture == "func":
                entity_info.setdefault("calls", []).append(text)
            elif child_capture == "comment":
                entity_info.setdefault("comments", []).append(text)
        key = capture_to_key.get(capture_name)
        if key and (
            key
            in {
                "ClassDefinition",
                "StructDefinition",
                "InterfaceDefinition",
                "EnumDefinition",
                "TraitDefinition",
                "PackageDeclaration",
            }
        ):
            name = entity_info.get("name")
            if not name:
                continue
        if key:
            summary.setdefault(key, []).append(entity_info)
            logger.info(f"Extracted {key} (tree-sitter, improved): {entity_info}")
    non_container_types = {
        "import": "ImportDeclaration",
        "variable": "VariableDeclaration",
        "param": "Parameter",
        "attr": "AttributeDeclaration",
        "func": "FunctionCall",
        "call": "FunctionCall",
        "comment": "CodeComment",
    }
    for node, capture_name in captures:
        if capture_name in non_container_types:
            key = non_container_types[capture_name]
            entity_info = {
                "raw": _node_text(node, code_bytes),
                "start_line": node.start_point[0] + 1,
                "end_line": node.end_point[1] + 1,
            }
            if capture_name == "name":
                entity_info["name"] = _node_text(node, code_bytes)
            summary.setdefault(key, []).append(entity_info)
            logger.info(f"Extracted {key} (tree-sitter, improved): {entity_info}")
