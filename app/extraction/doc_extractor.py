import ast
import io
import json
import logging
import os
import re
import tokenize
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from markdown_it import MarkdownIt
from rdflib import Graph, Literal, URIRef
from rdflib.namespace import RDF, XSD
from rich.console import Console
from rich.progress import BarColumn, Progress, TextColumn, TimeElapsedColumn, SpinnerColumn

from app.core.ontology_cache import get_doc_extraction_properties, get_ontology_cache
from app.core.paths import (
    get_excluded_directories_path,
    get_input_path,
    get_log_path,
    get_output_path,
    get_web_dev_ontology_path,
    uri_safe_string,
)
from app.ontology.wdo import WDOOntology

# Setup logging to file only
log_path = get_log_path("doc_extractor.log")
os.makedirs(os.path.dirname(log_path), exist_ok=True)
LOGFORMAT_FILE = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
logging.basicConfig(
    level=logging.INFO,
    format=LOGFORMAT_FILE,
    datefmt="[%Y-%m-%d %H:%M:%S]",
    handlers=[logging.FileHandler(log_path)],
)
logger = logging.getLogger("doc_extractor")

# --- Ontology and File Paths ---
TTL_PATH = get_output_path("web_development_ontology.ttl")
INPUT_DIR = get_input_path("")

# --- Document file types and names ---
DOC_EXTS = {".md", ".markdown", ".rst", ".txt"}
DOC_NAMES = {
    "readme",
    "contributing",
    "changelog",
    "license",
    "adr",
    "guide",
    "tutorial",
    "user_guide",
    "best_practice",
    "api",
    "docs",
    "documentation",
}
# --- Code file extensions for comment extraction ---
CODE_EXTS = {
    ".py",
    ".js",
    ".ts",
    ".java",
    ".c",
    ".cpp",
    ".h",
    ".hpp",
    ".go",
    ".rb",
    ".php",
    ".cs",
}

# --- Markdown element to ontology class mapping (keys are markdown-it token types) ---
MD_TO_WDO = {
    "heading_open": "Heading",
    "paragraph_open": "Paragraph",
    "bullet_list_open": "List",
    "ordered_list_open": "List",
    "code_block": "CodeBlock",
    "fence": "CodeBlock",
    "blockquote_open": "Blockquote",
    "table_open": "Table",
    "section_open": "DocumentSection",
}


def get_doc_type(filename: str) -> str:
    """Identify documentation file type based on filename."""
    name = filename.lower()
    if "readme" in name:
        return "Readme"
    if "contributing" in name:
        return "ContributionGuide"
    if "changelog" in name:
        return "Changelog"
    if "adr" in name or "decision" in name:
        return "ArchitecturalDecisionRecord"
    if "guide" in name and "user" in name:
        return "UserGuide"
    if "guide" in name:
        return "Guide"
    if "tutorial" in name:
        return "Tutorial"
    if "best" in name and "practice" in name:
        return "BestPracticeGuideline"
    if "api" in name:
        return "APIDocumentation"
    if "license" in name:
        return "License"
    return "Documentation"


def extract_python_comments(code: str) -> List[Dict[str, Any]]:
    """Extract comments from Python code using tokenize and ast."""
    comments: List[Dict[str, Any]] = []
    # Extract # comments using tokenize
    try:
        tokens = tokenize.generate_tokens(io.StringIO(code).readline)
        for toknum, tokval, start, end, _ in tokens:
            if toknum == tokenize.COMMENT:
                comments.append(
                    {
                        "raw": tokval.lstrip("#").strip(),
                        "start_line": start[0],
                        "end_line": end[0],
                    }
                )
    except Exception:
        pass
    # Extract docstrings using ast
    try:
        tree = ast.parse(code)
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.ClassDef, ast.Module)):
                doc = ast.get_docstring(node)
                if doc:
                    comments.append(
                        {
                            "raw": doc.strip(),
                            "start_line": getattr(node, "lineno", 1),
                            "end_line": getattr(
                                node, "end_lineno", getattr(node, "lineno", 1)
                            ),
                        }
                    )
    except Exception:
        pass
    return comments


def extract_code_comments(code: str, ext: str) -> List[Dict[str, Any]]:
    """Extract comments from code files using language-specific methods."""
    comments: List[Dict[str, Any]] = []
    if ext == ".py":
        return extract_python_comments(code)
    # Simple regex for //, /* */, and # comments
    # // and #
    for match in re.finditer(r"(?P<comment>//.*|#.*)", code):
        line = code[: match.start()].count("\n") + 1
        comments.append(
            {
                "raw": match.group().lstrip("/#").strip(),
                "start_line": line,
                "end_line": line,
            }
        )
    # /* ... */
    for match in re.finditer(r"/\*(.*?)\*/", code, re.DOTALL):
        start_line = code[: match.start()].count("\n") + 1
        end_line = code[: match.end()].count("\n") + 1
        comments.append(
            {
                "raw": match.group(1).strip(),
                "start_line": start_line,
                "end_line": end_line,
            }
        )
    return comments


def main() -> None:
    """Main function for documentation extraction."""
    console = Console()
    logger.info("Starting documentation extraction process...")

    # Load ontology and cache
    ontology = WDOOntology(get_web_dev_ontology_path())
    ontology_cache = get_ontology_cache()

    # Pre-fetch all needed classes/properties
    class_cache = {
        k: ontology.get_class(k)
        for k in set(MD_TO_WDO.values()) | {"DocumentationFile", "CodeComment"}
    }
    prop_cache = ontology_cache.get_property_cache(get_doc_extraction_properties())

    # Scan for documentation and code files
    excluded_dirs_path = get_excluded_directories_path()
    with open(excluded_dirs_path, "r") as f:
        excluded_dirs = set(json.load(f))

    repo_dirs = [
        d
        for d in os.listdir(INPUT_DIR)
        if os.path.isdir(os.path.join(INPUT_DIR, d)) and d not in excluded_dirs
    ]

    doc_files: List[Dict[str, Any]] = []
    code_files: List[Dict[str, Any]] = []
    file_id = 1

    for repo in repo_dirs:
        repo_path = os.path.join(INPUT_DIR, repo)
        for dirpath, dirnames, filenames in os.walk(repo_path):
            # Exclude directories in-place at every level
            dirnames[:] = [d for d in dirnames if d not in excluded_dirs]
            for fname in filenames:
                abs_path = os.path.join(dirpath, fname)
                rel_path = os.path.relpath(abs_path, repo_path)
                ext = Path(fname).suffix.lower()
                name_lower = fname.lower()

                # Check if it's a documentation file
                is_doc = ext in DOC_EXTS or any(
                    doc_name in name_lower for doc_name in DOC_NAMES
                )
                # Check if it's a code file
                is_code = ext in CODE_EXTS

                if is_doc:
                    doc_files.append(
                        {
                            "id": file_id,
                            "repository": repo,
                            "path": rel_path,
                            "filename": fname,
                            "extension": ext,
                            "abs_path": abs_path,
                        }
                    )
                    file_id += 1
                elif is_code:
                    code_files.append(
                        {
                            "id": file_id,
                            "repository": repo,
                            "path": rel_path,
                            "filename": fname,
                            "extension": ext,
                            "abs_path": abs_path,
                        }
                    )
                    file_id += 1

    logger.info(
        f"Found {len(doc_files)} documentation files and {len(code_files)} code files in {len(repo_dirs)} repositories"
    )

    g = Graph()
    if os.path.exists(TTL_PATH):
        g.parse(TTL_PATH, format="turtle")

    with Progress(
        TextColumn("[bold blue]{task.description}"),
        BarColumn(),
        "[progress.percentage]{task.percentage:>3.0f}%",
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        extract_task = progress.add_task(
            "[blue]Extracting documentation...", total=len(doc_files) + len(code_files)
        )
        # --- Documentation files ---
        for rec in doc_files:
            repo = rec["repository"]
            rel_path = rec["path"]
            abs_path = rec["abs_path"]
            fname = rec["filename"]
            ext = rec["extension"]
            file_enc = uri_safe_string(rel_path)
            repo_enc = uri_safe_string(repo)
            file_uri = URIRef(
                f"http://semantic-web-kms.edu.et/wdo/instances/{repo_enc}/{file_enc}"
            )
            doc_type = get_doc_type(fname)
            # File individual
            g.add((file_uri, RDF.type, class_cache["DocumentationFile"]))
            g.add(
                (
                    file_uri,
                    prop_cache["hasRelativePath"],
                    Literal(rel_path, datatype=XSD.string),
                )
            )
            g.add(
                (
                    file_uri,
                    prop_cache["hasExtension"],
                    Literal(ext, datatype=XSD.string),
                )
            )
            g.add(
                (
                    file_uri,
                    prop_cache["hasSimpleName"],
                    Literal(fname, datatype=XSD.string),
                )
            )
            # Content entity
            doc_uri = URIRef(
                f"http://semantic-web-kms.edu.et/wdo/instances/{repo_enc}/{file_enc}_content"
            )
            g.add((doc_uri, RDF.type, ontology.get_class(doc_type)))
            g.add((file_uri, prop_cache["bearerOfInformation"], doc_uri))
            g.add((doc_uri, prop_cache["informationBorneBy"], file_uri))
            g.add(
                (
                    doc_uri,
                    prop_cache["hasSimpleName"],
                    Literal(fname, datatype=XSD.string),
                )
            )
            # Parse Markdown
            try:
                with open(abs_path, "r", encoding="utf-8", errors="ignore") as f:
                    text = f.read()
                md = MarkdownIt()
                tokens = md.parse(text)
                parent_stack: List[Tuple[URIRef, Optional[str]]] = [
                    (doc_uri, None)
                ]  # (parent_uri, section_level)
                line_map: Dict[int, Tuple[Optional[int], Optional[int]]] = (
                    {}
                )  # token index -> (start_line, end_line)
                for i, token in enumerate(tokens):
                    # Try to get line numbers if available
                    start_line = getattr(token, "map", [None, None])[0]
                    end_line = getattr(token, "map", [None, None])[1]
                    line_map[i] = (start_line, end_line)
                    if token.type in MD_TO_WDO:
                        elem_class = class_cache[MD_TO_WDO[token.type]]
                        elem_id = f"{file_enc}_{token.type}_{i}"
                        elem_uri = URIRef(
                            f"http://semantic-web-kms.edu.et/wdo/instances/{elem_id}"
                        )
                        g.add((elem_uri, RDF.type, elem_class))
                        g.add((elem_uri, prop_cache["isElementOf"], file_uri))
                        if start_line is not None:
                            g.add(
                                (
                                    elem_uri,
                                    prop_cache["startsAtLine"],
                                    Literal(start_line + 1, datatype=XSD.integer),
                                )
                            )
                        if end_line is not None:
                            g.add(
                                (
                                    elem_uri,
                                    prop_cache["endsAtLine"],
                                    Literal(end_line, datatype=XSD.integer),
                                )
                            )
                        # Add text value for paragraphs, headings, code blocks, etc.
                        if token.type in {
                            "paragraph_open",
                            "heading_open",
                            "code_block",
                            "fence",
                            "blockquote_open",
                        }:
                            # Find the next inline or text token for content
                            content = ""
                            for j in range(i + 1, len(tokens)):
                                if tokens[j].type in {
                                    "inline",
                                    "text",
                                    "code_block",
                                    "fence",
                                }:
                                    content = tokens[j].content.strip()
                                    break
                            if content:
                                g.add(
                                    (
                                        elem_uri,
                                        prop_cache["hasTextValue"],
                                        Literal(content, datatype=XSD.string),
                                    )
                                )
                        # Nesting: link to parent
                        parent_uri, parent_level = parent_stack[-1]
                        g.add(
                            (parent_uri, prop_cache["hasDocumentComponent"], elem_uri)
                        )
                        # If this is a section/heading, push to stack
                        if token.type in {"section_open", "heading_open"}:
                            parent_stack.append(
                                (elem_uri, token.tag if hasattr(token, "tag") else None)
                            )
                        # If this is a section/heading close, pop from stack
                        if (
                            token.type in {"section_close", "heading_close"}
                            and len(parent_stack) > 1
                        ):
                            parent_stack.pop()
                # Add full text as hasContent
                g.add(
                    (
                        doc_uri,
                        prop_cache["hasContent"],
                        Literal(text, datatype=XSD.string),
                    )
                )
            except Exception as e:
                logger.warning(f"Failed to parse {abs_path}: {e}")
            progress.advance(extract_task)
        # --- Code files: extract code comments ---
        for rec in code_files:
            repo = rec["repository"]
            rel_path = rec["path"]
            abs_path = rec["abs_path"]
            fname = rec["filename"]
            ext = rec["extension"]
            file_enc = uri_safe_string(rel_path)
            repo_enc = uri_safe_string(repo)
            file_uri = URIRef(
                f"http://semantic-web-kms.edu.et/wdo/instances/{repo_enc}/{file_enc}"
            )
            # File individual (if not already present)
            g.add(
                (
                    file_uri,
                    prop_cache["hasRelativePath"],
                    Literal(rel_path, datatype=XSD.string),
                )
            )
            g.add(
                (
                    file_uri,
                    prop_cache["hasExtension"],
                    Literal(ext, datatype=XSD.string),
                )
            )
            g.add(
                (
                    file_uri,
                    prop_cache["hasSimpleName"],
                    Literal(fname, datatype=XSD.string),
                )
            )
            try:
                with open(abs_path, "r", encoding="utf-8", errors="ignore") as f:
                    code = f.read()
                comments = extract_code_comments(code, ext)
                for idx, comment in enumerate(comments):
                    comment_id = f"{file_enc}_codecomment_{idx}"
                    comment_uri = URIRef(
                        f"http://semantic-web-kms.edu.et/wdo/instances/{comment_id}"
                    )
                    g.add((comment_uri, RDF.type, class_cache["CodeComment"]))
                    g.add((comment_uri, prop_cache["isElementOf"], file_uri))
                    g.add(
                        (
                            comment_uri,
                            prop_cache["hasTextValue"],
                            Literal(comment["raw"], datatype=XSD.string),
                        )
                    )
                    g.add(
                        (
                            comment_uri,
                            prop_cache["startsAtLine"],
                            Literal(comment["start_line"], datatype=XSD.integer),
                        )
                    )
                    g.add(
                        (
                            comment_uri,
                            prop_cache["endsAtLine"],
                            Literal(comment["end_line"], datatype=XSD.integer),
                        )
                    )
            except Exception as e:
                logger.warning(f"Failed to process {abs_path}: {e}")
            progress.advance(extract_task)

        # TTL writing progress bar
        ttl_task = progress.add_task("[blue]Writing TTL...", total=1)
        g.serialize(destination=TTL_PATH, format="turtle")
        progress.advance(ttl_task)

    logger.info(
        f"Documentation extraction complete: {len(doc_files)} doc files, {len(code_files)} code files processed"
    )
    console.print(
        f"[bold green]Documentation extraction complete:[/bold green] {len(doc_files)} doc files, {len(code_files)} code files processed"
    )
    console.print(
        f"[bold green]Ontology updated and saved to:[/bold green] [cyan]{TTL_PATH}[/cyan]"
    )


if __name__ == "__main__":
    main()
