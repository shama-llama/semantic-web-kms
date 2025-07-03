import ast
import json
import logging
import os
import warnings
from pathlib import Path
from typing import Any, Dict, List, Optional, cast

from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import RDF, RDFS, XSD
from rich.console import Console
from rich.progress import BarColumn, Progress, TextColumn, TimeElapsedColumn
from tree_sitter_languages import get_language, get_parser

from app.core.ontology_cache import (
    get_code_extraction_classes,
    get_code_extraction_properties,
    get_ontology_cache,
)
from app.core.paths import (
    get_code_queries_path,
    get_excluded_directories_path,
    get_input_path,
    get_language_mapping_path,
    get_log_path,
    get_output_path,
    uri_safe_string,
)

# Suppress the FutureWarning from tree_sitter about deprecated Language constructor
warnings.filterwarnings("ignore", category=FutureWarning, module="tree_sitter")

# Setup logging to file only
log_path = get_log_path("code_extractor.log")
os.makedirs(os.path.dirname(log_path), exist_ok=True)
LOGFORMAT_FILE = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
logging.basicConfig(
    level=logging.INFO,
    format=LOGFORMAT_FILE,
    datefmt="[%Y-%m-%d %H:%M:%S]",
    handlers=[logging.FileHandler(log_path)],
)
logger = logging.getLogger("code_extractor")

# --- Ontology and File Paths ---
WDO = Namespace("http://semantic-web-kms.edu.et/wdo#")
INST = Namespace("http://semantic-web-kms.edu.et/wdo/instances/")

TTL_PATH = get_output_path("web_development_ontology.ttl")
INPUT_DIR = get_input_path("")

# --- Load Configuration from JSON ---
try:
    with open(get_language_mapping_path(), "r") as f:
        language_mapping = json.load(f)
except Exception:
    language_mapping = {}

try:
    with open(get_code_queries_path(), "r") as f:
        queries = json.load(f)
except Exception:
    queries = {}

# --- AST Extraction Functions ---


def extract_tree_sitter_entities(
    lang_name: str,
    tree_root: Any,
    code_bytes: bytes,
    queries: Dict[str, Any],
    summary: Dict[str, Any],
) -> None:
    """Extract entities from tree-sitter AST using language-specific queries, covering all ontology-relevant entities and relationships."""
    language = get_language(lang_name)
    if not language:
        return

    # Helper to decode node text
    def node_text(node):  # type: ignore
        return code_bytes[node.start_byte : node.end_byte].decode("utf-8", errors="ignore").strip()  # type: ignore

    # Map capture names to summary keys
    capture_to_key = {
        # Entity types
        "class": "classes",
        "struct": "classes",
        "interface": "classes",
        "enum": "classes",
        "trait": "classes",
        "type": "classes",
        "function": "functions",
        "method": "functions",
        "constructor": "functions",
        "param": "parameters",
        "parameter": "parameters",
        "attr": "fields",
        "field": "fields",
        "variable": "variables",
        "import": "imports",
        "func": "calls",
        "call": "calls",
        "decorator": "decorators",
        "annotation": "decorators",
        "type_annotation": "types",
        "annotation_type": "types",
        # Add more as needed
    }

    for query_name, query_list in queries.get(lang_name, {}).items():
        for query_str in query_list:
            try:
                logger.info(
                    f"Running query for {lang_name} - {query_name}: {query_str}"
                )
                query = language.query(query_str)
                captures = query.captures(tree_root)
                for node, capture_name in captures:
                    start_line = node.start_point[0] + 1
                    end_line = node.end_point[0] + 1
                    text = node_text(node)
                    entity_info = {
                        "raw": text,
                        "start_line": start_line,
                        "end_line": end_line,
                    }
                    key = capture_to_key.get(capture_name)
                    if key:
                        if key not in summary:
                            summary[key] = []
                        summary[key].append(entity_info)
                        logger.info(f"Extracted {key} (tree-sitter): {entity_info}")
            except Exception as e:
                logger.warning(f"Query {query_name} failed for {lang_name}: {e}")


def extract_python_entities(
    node: ast.AST, summary: Dict[str, Any], parent_class: Optional[str] = None
) -> None:
    """Recursively extract classes, functions, attributes, parameters, variables, inheritance, decorators, and calls from a Python AST node."""
    # Help type checker: ensure summary keys are always lists where needed
    if "classes" not in summary:
        summary["classes"] = []
    if "extends" not in summary:
        summary["extends"] = []
    if "methods" not in summary:
        summary["methods"] = []
    if "functions" not in summary:
        summary["functions"] = []
    if "imports" not in summary:
        summary["imports"] = []
    if "parameters" not in summary:
        summary["parameters"] = []
    if "variables" not in summary:
        summary["variables"] = []
    if "fields" not in summary:
        summary["fields"] = []
    if "decorators" not in summary:
        summary["decorators"] = []
    if "calls" not in summary:
        summary["calls"] = []
    if "types" not in summary:
        summary["types"] = []

    if isinstance(node, ast.ClassDef):
        class_info: dict[str, Any] = {
            "raw": f"class {node.name}(...):",
            "name": node.name,
            "start_line": node.lineno,
            "end_line": getattr(node, "end_lineno", node.lineno),
            "bases": [
                getattr(base, "id", getattr(base, "attr", str(base)))
                for base in node.bases
            ],
            "methods": [],
            "fields": [],
            "decorators": [
                ast.unparse(dec) if hasattr(ast, "unparse") else ""
                for dec in node.decorator_list
            ],
        }
        # Class-level attributes (fields)
        for body_item in node.body:
            if isinstance(body_item, ast.FunctionDef) or isinstance(
                body_item, ast.AsyncFunctionDef
            ):
                # Methods will be handled below
                pass
            elif isinstance(body_item, ast.Assign):
                for target in body_item.targets:
                    if isinstance(target, ast.Name):
                        field_info = {
                            "name": target.id,
                            "start_line": body_item.lineno,
                            "end_line": getattr(
                                body_item, "end_lineno", body_item.lineno
                            ),
                            "type": (
                                ast.unparse(body_item.value)
                                if hasattr(ast, "unparse")
                                else type(body_item.value).__name__
                            ),
                        }
                        cast(list[dict[str, Any]], class_info["fields"]).append(field_info)  # type: ignore
            elif isinstance(body_item, ast.AnnAssign):
                # Annotated assignment
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
                    cast(list[dict[str, Any]], class_info["fields"]).append(field_info)  # type: ignore
        # Methods
        for body_item in node.body:
            if isinstance(body_item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                extract_python_entities(body_item, summary, parent_class=node.name)
                # Methods are added to summary in the function handler
        if parent_class:
            if "methods" not in summary:
                summary["methods"] = []
            summary["methods"].append(class_info)  # type: ignore
        else:
            if "classes" not in summary:
                summary["classes"] = []
            cast(list[dict[str, Any]], summary["classes"]).append(class_info)  # type: ignore
        # Record inheritance relationships
        if class_info["bases"]:
            if "extends" not in summary:
                summary["extends"] = []
            for base in class_info["bases"]:
                cast(list[dict[str, Any]], summary["extends"]).append({"class": node.name, "base": base})  # type: ignore
        logger.info(f"Extracted class (python): {class_info}")
    elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        func_info: dict[str, Any] = {
            "raw": f"def {node.name}(...):",
            "name": node.name,
            "start_line": node.lineno,
            "end_line": getattr(node, "end_lineno", node.lineno),
            "parameters": [],
            "variables": [],
            "calls": [],
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
        # Parameters
        for arg in node.args.args:
            param_info = {
                "name": arg.arg,
                "type": (
                    ast.unparse(arg.annotation)
                    if arg.annotation and hasattr(ast, "unparse")
                    else (str(arg.annotation) if arg.annotation else None)
                ),
            }
            cast(list[dict[str, Any]], func_info["parameters"]).append(param_info)  # type: ignore
        # Local variables and function calls
        for subnode in ast.walk(node):
            # Local variable assignments
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
                        cast(list[dict[str, Any]], func_info["variables"]).append(var_info)  # type: ignore
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
                    cast(list[dict[str, Any]], func_info["variables"]).append(var_info)  # type: ignore
            # Function calls
            elif isinstance(subnode, ast.Call):
                if isinstance(subnode.func, ast.Name):
                    call_name = subnode.func.id
                elif isinstance(subnode.func, ast.Attribute):
                    call_name = (
                        ast.unparse(subnode.func) if hasattr(ast, "unparse") else ""
                    )
                else:
                    call_name = ""
                if call_name:
                    cast(list[str], func_info["calls"]).append(call_name)  # type: ignore
        if parent_class:
            if "methods" not in summary:
                summary["methods"] = []
            summary["methods"].append(func_info)  # type: ignore
        else:
            if "functions" not in summary:
                summary["functions"] = []
            cast(list[dict[str, Any]], summary["functions"]).append(func_info)  # type: ignore
        logger.info(f"Extracted function (python): {func_info}")
    elif isinstance(node, ast.Import):
        for alias in node.names:
            if "imports" not in summary:
                summary["imports"] = []
            import_info = {"raw": f"import {alias.name}"}
            cast(list[dict[str, Any]], summary["imports"]).append(import_info)  # type: ignore
            logger.info(f"Extracted import (python): {import_info}")
    elif isinstance(node, ast.ImportFrom):
        module = node.module or "."
        for alias in node.names:
            if "imports" not in summary:
                summary["imports"] = []
            import_info = {"raw": f"from {module} import {alias.name}"}
            cast(list[dict[str, Any]], summary["imports"]).append(import_info)  # type: ignore
            logger.info(f"Extracted import-from (python): {import_info}")
    # Recurse into all child nodes
    for child in ast.iter_child_nodes(node):
        extract_python_entities(child, summary, parent_class=parent_class)


# --- Main Processing Logic ---


def main() -> None:
    """Run the code extraction process."""
    console = Console()

    logger.info("Starting code extraction process...")

    # Load excluded directories
    excluded_dirs_path = get_excluded_directories_path()
    with open(excluded_dirs_path, "r") as f:
        excluded_dirs = set(json.load(f))

    # Scan input directory directly for supported files
    supported_files: List[Dict[str, Any]] = []
    repo_dirs = [
        d
        for d in os.listdir(INPUT_DIR)
        if os.path.isdir(os.path.join(INPUT_DIR, d)) and d not in excluded_dirs
    ]

    for repo in repo_dirs:
        repo_path = os.path.join(INPUT_DIR, repo)
        for dirpath, dirnames, filenames in os.walk(repo_path):
            # Exclude directories in-place at every level
            dirnames[:] = [d for d in dirnames if d not in excluded_dirs]
            for fname in filenames:
                ext = Path(fname).suffix.lower()
                if ext in language_mapping:
                    abs_path = os.path.join(dirpath, fname)
                    rel_path = os.path.relpath(abs_path, repo_path)
                    supported_files.append(
                        {
                            "repository": repo,
                            "path": rel_path,
                            "extension": ext,
                            "abs_path": abs_path,
                        }
                    )

    logger.info(
        f"Found {len(supported_files)} supported files in {len(repo_dirs)} repositories"
    )

    # Load ontology and cache
    ontology_cache = get_ontology_cache()
    prop_cache = ontology_cache.get_property_cache(get_code_extraction_properties())
    class_cache = ontology_cache.get_class_cache(get_code_extraction_classes())

    g = Graph()
    if os.path.exists(TTL_PATH):
        g.parse(TTL_PATH, format="turtle")

    summary_data: Dict[str, Dict[str, Any]] = {}

    with Progress(
        TextColumn("[bold blue]{task.description}"),
        BarColumn(),
        "[progress.percentage]{task.percentage:>3.0f}%",
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        # AST extraction progress
        extract_task = progress.add_task(
            "[blue]Extracting AST entities...", total=len(supported_files)
        )

        for rec in supported_files:
            repo = rec["repository"]
            rel_path = rec["path"]
            abs_path = rec["abs_path"]
            ext = rec["extension"]
            lang_name = language_mapping.get(ext)  # type: ignore

            if not lang_name:
                progress.advance(extract_task)
                continue

            try:
                with open(abs_path, "rb") as f:
                    code_bytes = f.read()
            except Exception as e:
                logger.warning(f"Could not read {abs_path}: {e}")
                progress.advance(extract_task)
                continue

            summary_key = f"{repo}/{rel_path}"
            summary_data[summary_key] = {"errors": []}

            try:
                if lang_name == "python":
                    # Use Python's native AST parser
                    code_str = code_bytes.decode("utf-8", errors="ignore")
                    tree = ast.parse(code_str)
                    extract_python_entities(tree, summary_data[summary_key])
                elif lang_name in queries:
                    # Use generic tree-sitter parser
                    parser = get_parser(lang_name)  # type: ignore
                    tree = parser.parse(code_bytes)
                    extract_tree_sitter_entities(
                        lang_name,  # type: ignore
                        tree.root_node,
                        code_bytes,
                        queries,  # type: ignore
                        summary_data[summary_key],
                    )

            except Exception as e:
                summary_data[summary_key]["errors"].append(str(e))
                logger.warning(f"AST extraction failed for {abs_path}: {e}")

            progress.advance(extract_task)

        logger.info(
            "AST extraction complete. Writing code structure entities to ontology..."
        )

        # --- Write code structure entities to TTL & RDF ---
        ttl_task = progress.add_task("[blue]Writing TTL...", total=len(supported_files))

        for rec in supported_files:
            repo = rec["repository"]
            rel_path = rec["path"]
            file_enc = uri_safe_string(rel_path)
            repo_enc = uri_safe_string(repo)
            file_uri = INST[f"{repo_enc}/{file_enc}"]
            summary_key = f"{repo}/{rel_path}"
            constructs = summary_data.get(summary_key, {})

            # --- Classes/Structs/Interfaces/Enums ---
            class_uris = {}
            for cls in constructs.get("ClassDefinition", []) + constructs.get(
                "classes", []
            ):
                class_id = cls.get("raw") or cls.get("name")
                if not class_id:
                    continue
                class_uri = URIRef(f"{file_uri}/class/{uri_safe_string(class_id)}")
                class_uris[class_id] = class_uri
                g.add((class_uri, RDF.type, class_cache["ClassDefinition"]))
                g.add((class_uri, prop_cache["isElementOf"], file_uri))
                g.add(
                    (
                        class_uri,
                        prop_cache["hasSimpleName"],
                        Literal(class_id, datatype=XSD.string),
                    )
                )
                if "start_line" in cls:
                    g.add(
                        (
                            class_uri,
                            prop_cache["startsAtLine"],
                            Literal(cls["start_line"], datatype=XSD.integer),
                        )
                    )
                if "end_line" in cls:
                    g.add(
                        (
                            class_uri,
                            prop_cache["endsAtLine"],
                            Literal(cls["end_line"], datatype=XSD.integer),
                        )
                    )
                # Decorators/annotations
                for dec in cls.get("decorators", []):
                    g.add(
                        (
                            class_uri,
                            prop_cache.get("hasDecorator", RDFS.seeAlso),
                            Literal(dec, datatype=XSD.string),
                        )
                    )

            # --- Inheritance/Extends/Implements ---
            for ext in constructs.get("extends", []):
                sub = ext.get("class")
                sup = ext.get("base")
                if sub and sup and sub in class_uris:
                    g.add((class_uris[sub], prop_cache.get("extendsType", RDFS.subClassOf), Literal(sup, datatype=XSD.string)))  # type: ignore

            # --- Fields/Attributes ---
            for field in constructs.get("fields", []):
                field_id = field.get("raw") or field.get("name")
                if not field_id:
                    continue
                field_uri = URIRef(f"{file_uri}/field/{uri_safe_string(field_id)}")
                g.add((field_uri, RDF.type, class_cache["AttributeDeclaration"]))
                g.add((field_uri, prop_cache["isElementOf"], file_uri))
                g.add(
                    (
                        field_uri,
                        prop_cache["hasSimpleName"],
                        Literal(field_id, datatype=XSD.string),
                    )
                )
                if "type" in field:
                    g.add(
                        (
                            field_uri,
                            prop_cache.get("hasType", RDFS.seeAlso),
                            Literal(field["type"], datatype=XSD.string),
                        )
                    )
                if "start_line" in field:
                    g.add(
                        (
                            field_uri,
                            prop_cache["startsAtLine"],
                            Literal(field["start_line"], datatype=XSD.integer),
                        )
                    )
                if "end_line" in field:
                    g.add(
                        (
                            field_uri,
                            prop_cache["endsAtLine"],
                            Literal(field["end_line"], datatype=XSD.integer),
                        )
                    )
                # Link to class if possible
                for cls in class_uris.values():  # type: ignore
                    g.add((cls, prop_cache.get("hasField", RDFS.member), field_uri))  # type: ignore

            # --- Functions/Methods/Constructors ---
            func_uris = {}
            for func in constructs.get("FunctionDefinition", []) + constructs.get(
                "functions", []
            ):
                func_id = func.get("raw") or func.get("name")
                if not func_id:
                    continue
                func_uri = URIRef(f"{file_uri}/function/{uri_safe_string(func_id)}")
                func_uris[func_id] = func_uri
                g.add((func_uri, RDF.type, class_cache["FunctionDefinition"]))
                g.add((func_uri, prop_cache["isElementOf"], file_uri))
                g.add(
                    (
                        func_uri,
                        prop_cache["hasSimpleName"],
                        Literal(func_id, datatype=XSD.string),
                    )
                )
                if "start_line" in func:
                    g.add(
                        (
                            func_uri,
                            prop_cache["startsAtLine"],
                            Literal(func["start_line"], datatype=XSD.integer),
                        )
                    )
                if "end_line" in func:
                    g.add(
                        (
                            func_uri,
                            prop_cache["endsAtLine"],
                            Literal(func["end_line"], datatype=XSD.integer),
                        )
                    )
                # Decorators/annotations
                for dec in func.get("decorators", []):
                    g.add(
                        (
                            func_uri,
                            prop_cache.get("hasDecorator", RDFS.seeAlso),
                            Literal(dec, datatype=XSD.string),
                        )
                    )
                # Return type
                if "returns" in func and func["returns"]:
                    g.add(
                        (
                            func_uri,
                            prop_cache.get("hasReturnType", RDFS.seeAlso),
                            Literal(func["returns"], datatype=XSD.string),
                        )
                    )
                # Parent class (for methods)
                if func.get("parent_class") and func["parent_class"] in class_uris:
                    g.add((class_uris[func["parent_class"]], prop_cache.get("hasMethod", RDFS.member), func_uri))  # type: ignore

            # --- Parameters ---
            for param in constructs.get("parameters", []):
                param_id = param.get("raw") or param.get("name")
                if not param_id:
                    continue
                param_uri = URIRef(f"{file_uri}/param/{uri_safe_string(param_id)}")
                g.add((param_uri, RDF.type, class_cache["Parameter"]))
                g.add((param_uri, prop_cache["isElementOf"], file_uri))
                g.add(
                    (
                        param_uri,
                        prop_cache["hasSimpleName"],
                        Literal(param_id, datatype=XSD.string),
                    )
                )
                if "type" in param:
                    g.add(
                        (
                            param_uri,
                            prop_cache.get("hasType", RDFS.seeAlso),
                            Literal(param["type"], datatype=XSD.string),
                        )
                    )
                # Link to function if possible
                for func in func_uris.values():  # type: ignore
                    g.add((func, prop_cache.get("hasParameter", RDFS.member), param_uri))  # type: ignore

            # --- Variables ---
            for var in constructs.get("variables", []):
                var_id = var.get("raw") or var.get("name")
                if not var_id:
                    continue
                var_uri = URIRef(f"{file_uri}/var/{uri_safe_string(var_id)}")
                g.add((var_uri, RDF.type, class_cache["VariableDeclaration"]))
                g.add((var_uri, prop_cache["isElementOf"], file_uri))
                g.add(
                    (
                        var_uri,
                        prop_cache["hasSimpleName"],
                        Literal(var_id, datatype=XSD.string),
                    )
                )
                if "type" in var:
                    g.add(
                        (
                            var_uri,
                            prop_cache.get("hasType", RDFS.seeAlso),
                            Literal(var["type"], datatype=XSD.string),
                        )
                    )
                # Link to function if possible
                for func in func_uris.values():  # type: ignore
                    g.add((func, prop_cache.get("declaresVariable", RDFS.member), var_uri))  # type: ignore

            # --- Function Calls ---
            for call in constructs.get("calls", []):
                call_id = call.get("raw") or call.get("name")
                if not call_id:
                    continue
                call_uri = URIRef(f"{file_uri}/call/{uri_safe_string(call_id)}")
                g.add(
                    (
                        call_uri,
                        RDF.type,
                        class_cache.get(
                            "FunctionCallSite", class_cache["FunctionDefinition"]
                        ),
                    )
                )
                g.add((call_uri, prop_cache["isElementOf"], file_uri))
                g.add(
                    (
                        call_uri,
                        prop_cache["hasSimpleName"],
                        Literal(call_id, datatype=XSD.string),
                    )
                )
                # Link to function if possible
                for func in func_uris.values():  # type: ignore
                    g.add((func, prop_cache.get("invokes", RDFS.seeAlso), call_uri))  # type: ignore

            # --- Decorators/Annotations (as standalone if not already linked) ---
            for dec in constructs.get("decorators", []):
                dec_id = dec.get("raw") or dec.get("name") or dec
                if not dec_id:
                    continue
                dec_uri = URIRef(f"{file_uri}/decorator/{uri_safe_string(str(dec_id))}")
                g.add((dec_uri, RDF.type, class_cache.get("Decorator", RDFS.seeAlso)))
                g.add((dec_uri, prop_cache["isElementOf"], file_uri))
                g.add(
                    (
                        dec_uri,
                        prop_cache["hasSimpleName"],
                        Literal(str(dec_id), datatype=XSD.string),
                    )
                )

            # --- Types/Type Annotations ---
            for typ in constructs.get("types", []):
                typ_id = typ.get("raw") or typ.get("name") or typ
                if not typ_id:
                    continue
                typ_uri = URIRef(f"{file_uri}/type/{uri_safe_string(str(typ_id))}")
                g.add((typ_uri, RDF.type, class_cache.get("Type", RDFS.seeAlso)))
                g.add((typ_uri, prop_cache["isElementOf"], file_uri))
                g.add(
                    (
                        typ_uri,
                        prop_cache["hasSimpleName"],
                        Literal(str(typ_id), datatype=XSD.string),
                    )
                )

            # --- Imports ---
            for imp in constructs.get("imports", []):
                imp_id = imp.get("raw")
                if not imp_id:
                    continue
                imp_uri = URIRef(f"{file_uri}/import/{uri_safe_string(imp_id)}")
                g.add((imp_uri, RDF.type, class_cache["ImportDeclaration"]))
                g.add((imp_uri, prop_cache["isElementOf"], file_uri))
                g.add(
                    (
                        imp_uri,
                        prop_cache["hasTextValue"],
                        Literal(imp_id, datatype=XSD.string),
                    )
                )

            # Use wdo:hasFile to link repository to file (membership)
            g.add((INST[repo_enc], WDO.hasFile, file_uri))

            progress.advance(ttl_task)

    g.serialize(destination=TTL_PATH, format="turtle")

    logger.info(
        f"Code extraction complete: {len(supported_files)} files processed and ontology updated"
    )
    console.print(
        f"[bold green]Code extraction complete:[/bold green] {len(supported_files)} files processed"
    )
    console.print(
        f"[bold green]Ontology updated and saved to:[/bold green] [cyan]{TTL_PATH}[/cyan]"
    )


if __name__ == "__main__":
    main()
