import ast
import json
import logging
import os
import re
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Union

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
from app.extraction.ast_extraction import (
    _extract_tree_sitter_entities_from_captures,
    _run_tree_sitter_queries,
    calculate_cyclomatic_complexity,
    extract_access_modifier,
    extract_python_entities,
    extract_tree_sitter_entities,
    handle_classdef,
    handle_functiondef,
)
from app.extraction.code_analysis_utils import (
    build_declaration_usage_summary,
    extract_boolean_modifiers,
    generate_canonical_name,
)
from app.extraction.entity_writers import (
    create_canonical_type_individuals,
    write_calls,
    write_classes,
    write_comments,
    write_decorators,
    write_enums,
    write_functions,
    write_imports,
    write_interfaces,
    write_modules,
    write_parameters,
    write_repo_file_link,
    write_structs,
    write_traits,
    write_types,
    write_variables,
)
from app.extraction.file_discovery import (
    discover_supported_files,
    get_input_and_output_paths,
    load_and_discover_files,
    load_excluded_dirs,
)
from app.extraction.file_utils import read_code_bytes
from app.extraction.ontology_context import (
    OntologyContext,
    create_ontology_context,
    get_file_entity_uris,
    initialize_context_and_graph,
    initialize_graph_and_cache,
)
from app.extraction.ontology_utils import (
    _is_attribute_declaration,
    _is_code_construct,
    _is_complex_type,
    _is_type_declaration,
    get_class_fallback,
    get_property_fallback,
)
from app.extraction.ontology_writer import write_fields
from app.extraction.relationship_writers import (
    write_access_relationships,
    write_declaration_usage_relationships,
    write_embedding_relationships,
    write_implements_interface,
    write_inheritance,
    write_manipulation_relationships,
    write_module_import_relationships,
    write_styling_relationships,
    write_testing_relationships,
    write_type_relationships,
)
from app.extraction.string_utils import (
    calculate_line_count,
    calculate_token_count,
    extract_imported_names,
)

# Suppress the FutureWarning from tree_sitter about deprecated Language constructor
warnings.filterwarnings("ignore", category=FutureWarning, module="tree_sitter")

logger = logging.getLogger("code_extractor")

# Setup logging to file only
log_path = Path(get_log_path("code_extractor.log"))
log_path.parent.mkdir(parents=True, exist_ok=True)
LOGFORMAT_FILE = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
logging.basicConfig(
    level=logging.INFO,
    format=LOGFORMAT_FILE,
    datefmt="[%Y-%m-%d %H:%M:%S]",
    handlers=[logging.FileHandler(str(log_path))],
)

# --- Ontology and File Paths ---
WDO = Namespace("http://semantic-web-kms.edu.et/wdo#")
INST = Namespace("http://semantic-web-kms.edu.et/wdo/instances/")


# --- Load Configuration from JSON ---
language_mapping = {}
queries = {}
language_mapping_path = Path(get_language_mapping_path())
if language_mapping_path.exists():
    with language_mapping_path.open("r") as f:
        language_mapping = json.load(f)
code_queries_path = Path(get_code_queries_path())
if code_queries_path.exists():
    with code_queries_path.open("r") as f:
        queries = json.load(f)


# --- Main Processing Logic ---


def extract_python_file(abs_path: str, summary: Dict[str, Any]) -> None:
    code_bytes = read_code_bytes(abs_path)
    if code_bytes is None:
        summary.setdefault("errors", []).append(f"Could not read file: {abs_path}")
        return
    try:
        code_str = code_bytes.decode("utf-8", errors="ignore")
        tree = ast.parse(code_str)
        extract_python_entities(tree, summary)
    except Exception as e:
        summary.setdefault("errors", []).append(str(e))
        logger.warning(f"AST extraction failed for {abs_path}: {e}")


def extract_tree_sitter_file(
    abs_path: str, lang_name: str, queries: Dict[str, Any], summary: Dict[str, Any]
) -> None:
    code_bytes = read_code_bytes(abs_path)
    if code_bytes is None:
        summary.setdefault("errors", []).append(f"Could not read file: {abs_path}")
        return
    try:
        parser = get_parser(lang_name)
        tree = parser.parse(code_bytes)
        extract_tree_sitter_entities(
            lang_name,
            tree.root_node,
            code_bytes,
            queries,
            summary,
        )
    except Exception as e:
        summary.setdefault("errors", []).append(str(e))
        logger.warning(f"AST extraction failed for {abs_path}: {e}")


def extract_type_relationships(summary: Dict[str, Any]) -> None:
    """Extract hasType relationships between code constructs and their types.

    This function analyzes:
    - Variable types
    - Function parameter types
    - Function return types
    - Class field types
    """
    type_relationships = []

    # Analyze variable types
    for var in summary.get("variables", []):
        var_name = var.get("name", "")
        var_type = var.get("type", "")
        if var_name and var_type:
            type_relationships.append(
                {
                    "construct": var_name,
                    "type": var_type,
                    "context": "variable_declaration",
                    "location": var.get("start_line", 0),
                }
            )

    # Analyze function parameter types
    for func in summary.get("functions", []):
        func_name = func.get("name", "")
        parameters = func.get("parameters", [])
        for param in parameters:
            param_name = param.get("name", "")
            param_type = param.get("type", "")
            if param_name and param_type:
                type_relationships.append(
                    {
                        "construct": f"{func_name}.{param_name}",
                        "type": param_type,
                        "context": "function_parameter",
                        "location": func.get("start_line", 0),
                    }
                )

        # Analyze function return type
        return_type = func.get("returns", "")
        if return_type:
            type_relationships.append(
                {
                    "construct": func_name,
                    "type": return_type,
                    "context": "function_return",
                    "location": func.get("start_line", 0),
                }
            )

    # Analyze class field types
    for cls in summary.get("classes", []):
        class_name = cls.get("name", "")
        fields = cls.get("fields", [])
        for field in fields:
            field_name = field.get("name", "")
            field_type = field.get("type", "")
            if field_name and field_type:
                type_relationships.append(
                    {
                        "construct": f"{class_name}.{field_name}",
                        "type": field_type,
                        "context": "class_field",
                        "location": cls.get("start_line", 0),
                    }
                )

    summary["type_relationships"] = type_relationships


def extract_access_relationships(summary: Dict[str, Any]) -> None:
    """Extract which functions access which attributes.

    This function analyzes:
    - Field access within methods
    - Property access
    - Variable access within functions
    """
    access_relationships = []

    # Analyze function bodies for field access
    for func in summary.get("functions", []):
        func_name = func.get("name", "")
        raw_code = func.get("raw", "")
        parent_class = func.get("parent_class", "")

        if raw_code and parent_class:
            # Look for field access patterns (self.field, this.field)

            field_patterns = [
                r"self\.(\w+)",  # Python
                r"this\.(\w+)",  # JavaScript/Java
                r"(\w+)\.(\w+)",  # General object.field
            ]

            for pattern in field_patterns:
                matches = re.findall(pattern, raw_code)
                for match in matches:
                    if isinstance(match, tuple):
                        obj_name, field_name = match
                    else:
                        field_name = match

                    access_relationships.append(
                        {
                            "function": func_name,
                            "attribute": field_name,
                            "context": "field_access",
                            "location": func.get("start_line", 0),
                        }
                    )

    # Analyze variable access within functions
    for func in summary.get("functions", []):
        func_name = func.get("name", "")
        variables = func.get("variables", [])

        for var in variables:
            var_name = var.get("name", "")
            if var_name:
                access_relationships.append(
                    {
                        "function": func_name,
                        "attribute": var_name,
                        "context": "variable_access",
                        "location": func.get("start_line", 0),
                    }
                )

    summary["access_relationships"] = access_relationships


def write_fields(
    g,
    constructs,
    file_uri,
    class_cache,
    prop_cache,
    uri_safe_string,
    class_uris,
    type_uris,
):
    # Handle both "fields" key (from Python AST) and "AttributeDeclaration" key (from tree-sitter)
    fields = constructs.get("fields", []) + constructs.get("AttributeDeclaration", [])
    for field in fields:
        field_id = field.get("name")
        if not field_id:
            continue
        field_uri = URIRef(f"{file_uri}/field/{uri_safe_string(field_id)}")
        g.add((field_uri, RDF.type, class_cache["AttributeDeclaration"]))
        g.add((field_uri, RDFS.label, Literal(field_id, datatype=XSD.string)))
        # Remove isElementOf (not in WDO)
        # g.add((field_uri, prop_cache.get("isElementOf", get_property_fallback("isElementOf")), file_uri))
        # Only add hasSimpleName for AttributeDeclaration (domain)
        g.add(
            (
                field_uri,
                prop_cache["hasSimpleName"],
                Literal(field_id, datatype=XSD.string),
            )
        )
        if "raw" in field and field["raw"]:
            g.add(
                (
                    field_uri,
                    prop_cache["hasSourceCodeSnippet"],
                    Literal(field["raw"], datatype=XSD.string),
                )
            )
        if "type" in field:
            field_type = field["type"].strip().lower()
            if field_type in type_uris:
                # Only add hasType if subject is CodeConstruct and object is TypeDeclaration
                g.add((field_uri, prop_cache["hasType"], type_uris[field_type]))
            else:
                logger.warning(
                    f"Field '{field_id}' has unknown type '{field_type}', skipping type triple."
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
        # Only add hasField if cls is ComplexType and field_uri is AttributeDeclaration
        for cls_name, cls_uri in class_uris.items():
            if _is_complex_type(cls_name):
                g.add((cls_uri, prop_cache["hasField"], field_uri))


def write_enums(g, constructs, file_uri, class_cache, prop_cache, uri_safe_string):
    """Write enum entities to the ontology."""
    enum_uris = {}
    for enum in (
        constructs.get("EnumDefinition", [])
        + constructs.get("EnumDeclaration", [])
        + constructs.get("enums", [])
    ):
        enum_id = enum.get("name")
        if not enum_id:
            logger.warning(f"Enum missing 'name', skipping hasSimpleName: {enum}")
            continue
        enum_uri = URIRef(f"{file_uri}/enum/{uri_safe_string(enum_id)}")
        enum_uris[enum_id] = enum_uri
        # Use fallback if EnumDefinition not in class_cache
        enum_class = class_cache.get(
            "EnumDefinition", class_cache.get("ClassDefinition", RDFS.seeAlso)
        )
        g.add((enum_uri, RDF.type, enum_class))
        g.add((enum_uri, prop_cache.get("isElementOf", RDFS.seeAlso), file_uri))
        g.add(
            (
                enum_uri,
                prop_cache["hasSimpleName"],
                Literal(enum_id, datatype=XSD.string),
            )
        )
        if "raw" in enum and enum["raw"]:
            g.add(
                (
                    enum_uri,
                    prop_cache.get("hasSourceCodeSnippet", RDFS.seeAlso),
                    Literal(enum["raw"], datatype=XSD.string),
                )
            )
        if "start_line" in enum:
            g.add(
                (
                    enum_uri,
                    prop_cache["startsAtLine"],
                    Literal(enum["start_line"], datatype=XSD.integer),
                )
            )
        if "end_line" in enum:
            g.add(
                (
                    enum_uri,
                    prop_cache["endsAtLine"],
                    Literal(enum["end_line"], datatype=XSD.integer),
                )
            )
        for dec in enum.get("decorators", []):
            g.add(
                (
                    enum_uri,
                    prop_cache.get("hasTextValue", RDFS.seeAlso),
                    Literal(dec, datatype=XSD.string),
                )
            )
    return enum_uris


def write_type_relationships(g, constructs, file_uri, prop_cache, uri_safe_string):
    """Write hasType relationships between code constructs and their types."""
    for rel in constructs.get("type_relationships", []):
        construct_name = rel.get("construct")
        type_name = rel.get("type")
        if construct_name and type_name:
            # Create URI for the construct
            construct_uri = URIRef(
                f"{file_uri}/construct/{uri_safe_string(construct_name)}"
            )

            # Add hasType relationship
            g.add(
                (
                    construct_uri,
                    prop_cache.get("hasType", RDFS.seeAlso),
                    Literal(type_name, datatype=XSD.string),
                )
            )


def process_file_for_ontology(
    *,
    ctx: OntologyContext,
    rec: dict[str, str],
    summary_data: dict[str, dict],
    global_type_uris: dict[str, str],
) -> None:
    """Process a single file's constructs and write entities and relationships to the ontology graph.

    Args:
        ctx: OntologyContext object containing graph, caches, and URI helpers.
        rec: File record with at least 'repository' and 'path' keys.
        summary_data: Mapping of file keys to construct summaries.
        global_type_uris: Mapping of global type names to their URIs.

    Returns:
        None. Writes entities and relationships to the ontology graph in ctx.
    """
    repo = rec["repository"]
    rel_path = rec["path"]
    file_enc = ctx.uri_safe_string(rel_path)
    repo_enc = ctx.uri_safe_string(repo)
    file_uri = ctx.INST[f"{repo_enc}/{file_enc}"]
    summary_key = f"{repo}/{rel_path}"
    constructs = summary_data.get(summary_key, {})
    ext = Path(rel_path).suffix.lower()
    language = language_mapping[ext] if ext in language_mapping else None
    all_entity_uris, interface_uris, module_uris = get_file_entity_uris(
        ctx, constructs, file_uri
    )
    func_uris = write_all_entities_for_file(
        ctx,
        constructs,
        file_uri,
        all_entity_uris,
        interface_uris,
        module_uris,
        global_type_uris,
        language,
    )
    write_all_relationships(
        ctx,
        constructs,
        file_uri,
        all_entity_uris,
        interface_uris,
        module_uris,
        func_uris,
        global_type_uris,
    )


def write_all_entities_for_file(
    ctx: OntologyContext,
    constructs,
    file_uri,
    all_entity_uris,
    interface_uris,
    module_uris,
    global_type_uris,
    language,
):
    func_uris = write_functions(
        ctx.g,
        constructs,
        file_uri,
        ctx.class_cache,
        ctx.prop_cache,
        ctx.uri_safe_string,
        all_entity_uris,
        global_type_uris,
        language,
    )
    write_parameters(
        ctx.g,
        constructs,
        file_uri,
        ctx.class_cache,
        ctx.prop_cache,
        ctx.uri_safe_string,
        func_uris,
        global_type_uris,
    )
    write_variables(
        ctx.g,
        constructs,
        file_uri,
        ctx.class_cache,
        ctx.prop_cache,
        ctx.uri_safe_string,
        func_uris,
        global_type_uris,
    )
    write_calls(
        ctx.g,
        constructs,
        file_uri,
        ctx.class_cache,
        ctx.prop_cache,
        ctx.uri_safe_string,
        func_uris,
        global_type_uris,
    )
    write_decorators(
        ctx.g,
        constructs,
        file_uri,
        ctx.class_cache,
        ctx.prop_cache,
        ctx.uri_safe_string,
    )
    write_types(
        ctx.g,
        constructs,
        file_uri,
        ctx.class_cache,
        ctx.prop_cache,
        ctx.uri_safe_string,
    )
    write_imports(
        ctx.g,
        constructs,
        file_uri,
        ctx.class_cache,
        ctx.prop_cache,
        ctx.uri_safe_string,
    )
    write_module_import_relationships(
        ctx.g, constructs, file_uri, ctx.prop_cache, ctx.uri_safe_string, module_uris
    )
    write_comments(
        ctx.g,
        constructs,
        file_uri,
        ctx.class_cache,
        ctx.prop_cache,
        ctx.uri_safe_string,
    )
    return func_uris


def write_all_relationships(
    ctx: OntologyContext,
    constructs,
    file_uri,
    all_entity_uris,
    interface_uris,
    module_uris,
    func_uris,
    global_type_uris,
):
    write_inheritance(ctx.g, constructs, all_entity_uris, ctx.prop_cache)
    write_implements_interface(
        ctx.g, constructs, all_entity_uris, interface_uris, ctx.prop_cache
    )
    write_fields(
        ctx.g,
        constructs,
        file_uri,
        ctx.class_cache,
        ctx.prop_cache,
        ctx.uri_safe_string,
        all_entity_uris,
        global_type_uris,
    )
    write_declaration_usage_relationships(
        ctx.g, constructs, file_uri, ctx.prop_cache, ctx.uri_safe_string
    )
    write_access_relationships(
        ctx.g, constructs, file_uri, ctx.prop_cache, ctx.uri_safe_string
    )
    write_type_relationships(
        ctx.g, constructs, file_uri, ctx.prop_cache, ctx.uri_safe_string
    )
    write_embedding_relationships(
        ctx.g, constructs, file_uri, ctx.prop_cache, ctx.uri_safe_string
    )
    write_manipulation_relationships(
        ctx.g, constructs, file_uri, ctx.prop_cache, ctx.uri_safe_string
    )
    write_styling_relationships(
        ctx.g, constructs, file_uri, ctx.prop_cache, ctx.uri_safe_string
    )
    write_testing_relationships(
        ctx.g, constructs, file_uri, ctx.prop_cache, ctx.uri_safe_string
    )
    write_repo_file_link(ctx.g, file_uri.split("/")[0], ctx.WDO, ctx.INST, file_uri)


def write_ontology(
    g,
    supported_files,
    summary_data,
    TTL_PATH,
    class_cache,
    prop_cache,
    INST,
    WDO,
    uri_safe_string,
):
    """Write ontology triples for all supported files. Rationale: Delegates per-file logic to a helper."""
    ctx = create_ontology_context(
        g=g,
        class_cache=class_cache,
        prop_cache=prop_cache,
        INST=INST,
        WDO=WDO,
        uri_safe_string=uri_safe_string,
        TTL_PATH=TTL_PATH,
    )
    global_type_uris = create_canonical_type_individuals(
        g, class_cache, prop_cache, uri_safe_string
    )
    for rec in supported_files:
        process_file_for_ontology(
            ctx=ctx,
            rec=rec,
            summary_data=summary_data,
            global_type_uris=global_type_uris,
        )


def extract_ast_entities_progress(
    supported_files, language_mapping, queries, summary_data, console
):
    with Progress(
        TextColumn("[bold blue]{task.description}"),
        BarColumn(),
        "[progress.percentage]{task.percentage:>3.0f}%",
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        extract_task = progress.add_task(
            "[blue]Extracting AST entities...", total=len(supported_files)
        )
        for rec in supported_files:
            repo = rec["repository"]
            rel_path = rec["path"]
            abs_path = rec["abs_path"]
            ext = rec["extension"]
            lang_name = language_mapping.get(ext)
            summary_key = f"{repo}/{rel_path}"
            summary_data[summary_key] = {"errors": []}
            if not lang_name:
                continue
            if lang_name == "python":
                code_bytes = read_code_bytes(abs_path)
                if code_bytes is None:
                    summary_data[summary_key].setdefault("errors", []).append(
                        f"Could not read file: {abs_path}"
                    )
                    continue
                try:
                    code_str = code_bytes.decode("utf-8", errors="ignore")
                    import ast

                    tree = ast.parse(code_str)
                    extract_python_entities(tree, summary_data[summary_key])
                except Exception as e:
                    summary_data[summary_key].setdefault("errors", []).append(str(e))
                    logger.warning(f"AST extraction failed for {abs_path}: {e}")
            elif lang_name in queries:
                code_bytes = read_code_bytes(abs_path)
                if code_bytes is None:
                    summary_data[summary_key].setdefault("errors", []).append(
                        f"Could not read file: {abs_path}"
                    )
                    continue
                try:
                    parser = get_parser(lang_name)
                    tree = parser.parse(code_bytes)
                    extract_tree_sitter_entities(
                        lang_name,
                        tree.root_node,
                        code_bytes,
                        queries,
                        summary_data[summary_key],
                    )
                except Exception as e:
                    summary_data[summary_key].setdefault("errors", []).append(str(e))
                    logger.warning(f"AST extraction failed for {abs_path}: {e}")
            progress.advance(extract_task)


def write_ontology_progress(
    ctx: OntologyContext, supported_files, summary_data, language_mapping
):
    with Progress(
        TextColumn("[bold blue]{task.description}"),
        BarColumn(),
        "[progress.percentage]{task.percentage:>3.0f}%",
        TimeElapsedColumn(),
        console=Console(),
    ) as progress:
        ttl_task = progress.add_task("[blue]Writing TTL...", total=len(supported_files))
        write_ontology(
            ctx.g,
            supported_files,
            summary_data,
            ctx.TTL_PATH,
            ctx.class_cache,
            ctx.prop_cache,
            ctx.INST,
            ctx.WDO,
            ctx.uri_safe_string,
        )
        for _ in supported_files:
            progress.advance(ttl_task)


def finalize_and_serialize_graph(ctx: OntologyContext):
    ctx.g.serialize(destination=str(ctx.TTL_PATH), format="turtle")


def log_startup():
    logger.info("Starting code extraction process...")


def extract_all_ast_entities(
    supported_files, language_mapping, queries, summary_data, console
):
    extract_ast_entities_progress(
        supported_files, language_mapping, queries, summary_data, console
    )


def write_and_serialize_ontology(ctx, supported_files, summary_data, language_mapping):
    logger.info(
        "AST extraction complete. Writing code structure entities to ontology..."
    )
    write_ontology_progress(ctx, supported_files, summary_data, language_mapping)
    finalize_and_serialize_graph(ctx)
    logger.info(
        f"Code extraction complete: {len(supported_files)} files processed and ontology updated"
    )


def print_completion_message(supported_files, TTL_PATH, console):
    console.print(
        f"[bold green]Code extraction complete:[/bold green] {len(supported_files)} files processed"
    )
    console.print(
        f"[bold green]Ontology updated and saved to:[/bold green] [cyan]{TTL_PATH}[/cyan]"
    )


def main() -> None:
    """Run the code extraction process. Rationale: Orchestrates high-level steps only."""
    console = Console()
    log_startup()
    supported_files, repo_dirs, INPUT_DIR, TTL_PATH = load_and_discover_files(
        language_mapping
    )
    if not supported_files:
        logger.info("No supported files found. Exiting code extraction.")
        return
    g, class_cache, prop_cache, ctx = initialize_context_and_graph(
        TTL_PATH, INST, WDO, uri_safe_string
    )
    summary_data: Dict[str, Dict[str, Any]] = {}
    extract_all_ast_entities(
        supported_files, language_mapping, queries, summary_data, console
    )
    write_and_serialize_ontology(ctx, supported_files, summary_data, language_mapping)
    print_completion_message(supported_files, TTL_PATH, console)


if __name__ == "__main__":
    main()
