"""Code construct extraction module for Semantic Web KMS."""

import ast
import json
import logging
import re
import warnings
from pathlib import Path
from typing import Any, Callable, Dict, Optional

from rich.console import Console
from rich.progress import BarColumn, Progress, TextColumn, TimeElapsedColumn
from tree_sitter_languages import get_parser

from app.core.namespaces import INST, WDO
from app.core.paths import (
    get_code_queries_path,
    get_language_mapping_path,
    uri_safe_string,
)
from app.extraction.ontology.ontology_context import initialize_context_and_graph
from app.extraction.utils.ast_extraction import (
    extract_python_entities,
    extract_tree_sitter_entities,
)
from app.extraction.utils.file_discovery import load_and_discover_files
from app.extraction.utils.file_utils import read_code_bytes
from app.extraction.writers.ontology_writer import (
    finalize_and_serialize_graph,
    write_ontology,
)

warnings.filterwarnings("ignore", category=FutureWarning, module="tree_sitter")

logger = logging.getLogger("code_extractor")

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


def process_file_with_ast(
    abs_path: str,
    summary: Dict[str, Any],
    parse_func: Optional[Callable[[Any], Any]],
    extract_func: Callable[..., None],
    *extract_args,
    **extract_kwargs,
) -> None:
    """
    Parse a file and extract entities, updating the summary dict.

    Args:
        abs_path: Absolute file path.
        summary: Dict to update with results/errors.
        parse_func: Function to parse code (e.g., ast.parse), or None.
        extract_func: Function to extract entities from the parsed tree.
        *extract_args: Positional args for extract_func.
        **extract_kwargs: Keyword args for extract_func.
    """
    code_bytes = read_code_bytes(abs_path)
    if code_bytes is None:
        summary.setdefault("errors", []).append(f"Could not read file: {abs_path}")
        return
    try:
        if parse_func is not None and getattr(parse_func, "__name__", "") == "parse":
            tree = parse_func(code_bytes)
        elif parse_func is not None:
            code_str = code_bytes.decode("utf-8", errors="ignore")
            tree = parse_func(code_str)
        else:
            tree = None
        extract_func(tree, summary, *extract_args, **extract_kwargs)
    except (SyntaxError, UnicodeDecodeError) as e:
        summary.setdefault("errors", []).append(str(e))
        logger.warning(f"AST extraction failed for {abs_path}: {e}")


def extract_python_file(abs_path: str, summary: Dict[str, Any]) -> None:
    """
    Extract Python entities from a file using AST.

    Args:
        abs_path: Absolute file path.
        summary: Dict to update with results/errors.
    """
    process_file_with_ast(abs_path, summary, ast.parse, extract_python_entities)


def extract_tree_sitter_file(
    abs_path: str, lang_name: str, queries: Dict[str, Any], summary: Dict[str, Any]
) -> None:
    """
    Extract entities from a file using tree-sitter for the given language.

    Args:
        abs_path: Absolute file path.
        lang_name: Language name for tree-sitter.
        queries: Query dict for tree-sitter.
        summary: Dict to update with results/errors.
    """
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
    except (Exception, UnicodeDecodeError) as e:
        summary.setdefault("errors", []).append(str(e))
        logger.warning(f"AST extraction failed for {abs_path}: {e}")


def extract_type_relationships(summary: Dict[str, Any]) -> None:
    """
    Extract hasType relationships between code constructs and their types.

    Args:
        summary: Dict to update with type relationships.
    """
    type_relationships = []
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
    """
    Extract which functions access which attributes.

    Args:
        summary: Dict to update with access relationships.
    """
    access_relationships = []
    for func in summary.get("functions", []):
        func_name = func.get("name", "")
        raw_code = func.get("raw", "")
        parent_class = func.get("parent_class", "")
        if raw_code and parent_class:
            field_patterns = [
                r"self\.(\w+)",
                r"this\.(\w+)",
                r"(\w+)\.(\w+)",
            ]
            for pattern in field_patterns:
                matches = re.findall(pattern, raw_code)
                for match in matches:
                    if isinstance(match, tuple):
                        _, field_name = match if len(match) == 2 else (None, match[0])
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


def extract_ast_entities_progress(
    supported_files, language_mapping, queries, summary_data, progress, extract_task
):
    """
    Extract AST/code entities from supported files, updating progress.

    Args:
        supported_files: List of file records.
        language_mapping: Dict mapping file extensions to languages.
        queries: Dict of tree-sitter queries.
        summary_data: Dict to update with extraction results.
        progress: Progress bar object.
        extract_task: Progress task ID.
    """
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
            process_file_with_ast(
                abs_path, summary_data[summary_key], ast.parse, extract_python_entities
            )
        elif lang_name in queries:
            extract_tree_sitter_file(
                abs_path, lang_name, queries, summary_data[summary_key]
            )
        progress.advance(extract_task)


def write_ontology_progress(
    ctx, supported_files, summary_data, language_mapping, progress, ttl_task
):
    """
    Write ontology triples for extracted entities, updating progress.

    Args:
        ctx: Ontology context.
        supported_files: List of file records.
        summary_data: Extraction results.
        language_mapping: Dict mapping file extensions to languages.
        progress: Progress bar object.
        ttl_task: Progress task ID.
    """
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
        language_mapping,
    )
    for _ in supported_files:
        progress.advance(ttl_task)


def log_startup() -> None:
    """Log the start of the code extraction process."""
    logger.info("Starting code extraction process...")


def extract_all_ast_entities(
    supported_files, language_mapping, queries, summary_data, console
):
    """
    Extract AST/code entities from all supported files with progress bar.

    Args:
        supported_files: List of file records.
        language_mapping: Dict mapping file extensions to languages.
        queries: Dict of tree-sitter queries.
        summary_data: Dict to update with extraction results.
        console: Rich console for progress display.
    """
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
        extract_ast_entities_progress(
            supported_files,
            language_mapping,
            queries,
            summary_data,
            progress,
            extract_task,
        )


def write_and_serialize_ontology(ctx, supported_files, summary_data, language_mapping):
    """
    Write ontology triples and serialize the graph to disk.

    Args:
        ctx: Ontology context.
        supported_files: List of file records.
        summary_data: Extraction results.
        language_mapping: Dict mapping file extensions to languages.
    """
    logger.info(
        "AST extraction complete. Writing code structure entities to ontology..."
    )
    with Progress(
        TextColumn("[bold blue]{task.description}"),
        BarColumn(),
        "[progress.percentage]{task.percentage:>3.0f}%",
        TimeElapsedColumn(),
        console=None,  # No console for this internal task
    ) as progress:
        ttl_task = progress.add_task("[blue]Writing TTL...", total=len(supported_files))
        write_ontology_progress(
            ctx, supported_files, summary_data, language_mapping, progress, ttl_task
        )
    finalize_and_serialize_graph(ctx)
    logger.info(
        f"Code extraction complete: {len(supported_files)} files processed and ontology updated"
    )


def print_completion_message(supported_files, TTL_PATH, console) -> None:
    """
    Print completion message to the console.

    Args:
        supported_files: List of file records.
        TTL_PATH: Path to the TTL output file.
        console: Rich console for output.
    """
    console.print(
        f"[bold green]Code extraction complete:[/bold green] {len(supported_files)} files processed"
    )
    console.print(
        f"[bold green]Ontology updated and saved to:[/bold green] [cyan]{TTL_PATH}[/cyan]"
    )


def main() -> None:
    """
    Run the code extraction process for the Semantic Web KMS.

    The input directory is determined by the centralized configuration (set via set_input_dir in the pipeline, or falls back to the default). This function does not accept or parse an input directory argument.

    Returns:
        None. Writes output to file and logs progress.

    Raises:
        Exceptions may propagate if configuration files are missing or unreadable.
    """
    console = Console()
    log_startup()
    supported_files, repo_dirs, input_dir, ttl_path = load_and_discover_files(
        language_mapping
    )
    if not supported_files:
        logger.info("No supported files found. Exiting code extraction.")
        return
    g, class_cache, prop_cache, ctx = initialize_context_and_graph(
        ttl_path, INST, WDO, uri_safe_string
    )
    summary_data: Dict[str, Dict[str, Any]] = {}
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
        extract_ast_entities_progress(
            supported_files,
            language_mapping,
            queries,
            summary_data,
            progress,
            extract_task,
        )
        ttl_task = progress.add_task("[blue]Writing TTL...", total=len(supported_files))
        write_ontology_progress(
            ctx, supported_files, summary_data, language_mapping, progress, ttl_task
        )
    finalize_and_serialize_graph(ctx)
    console.print(
        f"[bold green]Code extraction complete:[/bold green] {len(supported_files)} files processed"
    )
    console.print(
        f"[bold green]Ontology updated and saved to:[/bold green] [cyan]{ttl_path}[/cyan]"
    )


if __name__ == "__main__":
    main()
