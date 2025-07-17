"""Code analysis and AST utility functions for code extraction."""

import ast
from typing import Any, Dict, List, Optional


def generate_canonical_name(
    entity_info: Dict[str, Any], *, parent_context: Optional[str] = None
) -> str:
    """
    Generate a canonical name for a code construct.

    Args:
        entity_info: Dictionary with entity info.
        parent_context: Optional parent context (e.g., class name).

    Returns:
        Canonical name string.
    """
    name = entity_info.get("name", "")
    if not name:
        return ""
    if parent_context:
        return f"{parent_context}.{name}"
    return str(name)


def calculate_cyclomatic_complexity(raw_code: str) -> int:
    """
    Calculate cyclomatic complexity of code.

    Args:
        raw_code: Raw source code.

    Returns:
        Cyclomatic complexity value.
    """
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


def extract_access_modifier(
    entity_info: Dict[str, Any], raw_code: str
) -> Optional[str]:
    """
    Extract access modifier from code construct.

    Args:
        entity_info: Dictionary with entity info.
        raw_code: Raw source code.

    Returns:
        Access modifier string or None.
    """
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


def extract_boolean_modifiers(
    entity_info: Dict[str, Any], raw_code: str
) -> Dict[str, bool]:
    """
    Extract boolean modifiers from code constructs.

    Args:
        entity_info: Dictionary with entity info.
        raw_code: Raw source code.

    Returns:
        Dict of boolean modifiers.
    """
    if not raw_code:
        return {}
    modifiers = {"isAsynchronous": False, "isFinal": False, "isStatic": False}
    if "async" in raw_code.lower() or "await" in raw_code.lower():
        modifiers["isAsynchronous"] = True
    if "final" in raw_code.lower() or "const" in raw_code.lower():
        modifiers["isFinal"] = True
    if "static" in raw_code.lower():
        modifiers["isStatic"] = True
    return modifiers


def extract_function_parameters(node: ast.AST) -> List[Dict[str, Any]]:
    """
    Extract parameters from a function AST node.

    Args:
        node: AST node (FunctionDef or similar).

    Returns:
        List of parameter info dicts.
    """
    params = []
    args_obj = getattr(node, "args", None)
    if args_obj and hasattr(args_obj, "args"):
        for arg in args_obj.args:
            param_info = {
                "name": arg.arg,
                "type": (
                    ast.unparse(arg.annotation)
                    if hasattr(arg, "annotation")
                    and arg.annotation
                    and hasattr(ast, "unparse")
                    else (
                        str(arg.annotation)
                        if hasattr(arg, "annotation") and arg.annotation
                        else None
                    )
                ),
            }
            params.append(param_info)
    return params


def extract_function_variables(node: ast.AST) -> List[Dict[str, Any]]:
    """
    Extract variable assignments from a function AST node.

    Args:
        node: AST node.

    Returns:
        List of variable info dicts.
    """
    variables = []
    for subnode in ast.walk(node):
        if isinstance(subnode, ast.Assign):
            for target in subnode.targets:
                if isinstance(target, ast.Name):
                    var_info = {
                        "name": target.id,
                        "start_line": subnode.lineno,
                        "end_line": getattr(subnode, "end_lineno", subnode.lineno),
                        "type": (
                            ast.unparse(subnode.value)
                            if hasattr(ast, "unparse")
                            else type(subnode.value).__name__
                        ),
                    }
                    variables.append(var_info)
        elif isinstance(subnode, ast.AnnAssign):
            if isinstance(subnode.target, ast.Name):
                var_info = {
                    "name": subnode.target.id,
                    "start_line": subnode.lineno,
                    "end_line": getattr(subnode, "end_lineno", subnode.lineno),
                    "type": (
                        ast.unparse(subnode.annotation)
                        if hasattr(ast, "unparse")
                        else str(subnode.annotation)
                    ),
                }
                variables.append(var_info)
    return variables


def extract_function_calls(
    node: ast.AST, summary: Dict[str, Any], code: str = ""
) -> List[Dict[str, Any]]:
    """
    Extract function calls from a function AST node.

    Args:
        node: AST node.
        summary: Summary dict to append call info.
        code: Source code string for extracting raw call text.
    Returns:
        List of call info dicts.
    """
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
                prefixed_call_name = f"callsite: {call_name}"
                args = []
                for arg in subnode.args:
                    if isinstance(arg, ast.Name):
                        args.append(arg.id)
                    elif hasattr(ast, "unparse"):
                        args.append(ast.unparse(arg))
                    else:
                        args.append(str(arg))
                # Try to get the raw source code for the call
                try:
                    raw = (
                        ast.get_source_segment(code, subnode)
                        if code and hasattr(ast, "get_source_segment")
                        else None
                    )
                except Exception:
                    raw = None
                call_info = {
                    "name": prefixed_call_name,
                    "arguments": args,
                    "start_line": getattr(subnode, "lineno", None),
                    "end_line": getattr(subnode, "end_lineno", None),
                    "raw": raw,
                }
                calls.append(call_info)
                summary.setdefault("calls", []).append(call_info)
    return calls


def build_declaration_usage_summary(summary: Dict[str, Any]) -> None:
    """Build the 'declaration_usage' summary for variable, function, class, and import usages."""
    variable_usages = []
    function_usages = []
    class_usages = []
    import_usages = []
    for call in summary.get("calls", []):
        call_name = call.get("name", "")
        if call_name:
            function_usages.append(
                {
                    "usage": call_name,
                    "context": "function_call",
                    "location": call.get("start_line", 0),
                }
            )
    for var in summary.get("variables", []):
        var_name = var.get("name", "")
        if var_name:
            for call in summary.get("calls", []):
                call_args = call.get("arguments", [])
                if var_name in call_args:
                    variable_usages.append(
                        {
                            "declaration": var_name,
                            "usage": call.get("name", ""),
                            "context": "function_argument",
                            "location": call.get("start_line", 0),
                        }
                    )
    for cls in summary.get("classes", []):
        class_name = cls.get("name", "")
        bases = cls.get("bases", [])
        for base in bases:
            class_usages.append(
                {
                    "usage": base,
                    "context": "inheritance",
                    "location": cls.get("start_line", 0),
                }
            )
    for imp in summary.get("imports", []):
        import_text = imp.get("raw", "")
        if import_text:
            from app.extraction.utils.string_utils import extract_imported_names

            import_names = extract_imported_names(import_text)
            for name in import_names:
                import_usages.append(
                    {
                        "import": name,
                        "context": "import_usage",
                        "location": imp.get("start_line", 0),
                    }
                )
    summary["declaration_usage"] = {
        "variable_usages": variable_usages,
        "function_usages": function_usages,
        "class_usages": class_usages,
        "import_usages": import_usages,
    }
