"""Documentation and code extraction for semantic web KMS."""

import ast
import io
import json
import logging
import os
import re
import tokenize
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Tuple

from markdown_it import MarkdownIt
from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import RDF, RDFS, XSD
from rich.console import Console
from rich.progress import BarColumn, Progress, TextColumn, TimeElapsedColumn

from app.core.ontology_cache import get_doc_extraction_properties, get_ontology_cache
from app.core.paths import get_excluded_directories_path  # type: ignore
from app.core.paths import get_input_path  # type: ignore
from app.core.paths import get_log_path  # type: ignore
from app.core.paths import get_output_path  # type: ignore
from app.core.paths import get_web_dev_ontology_path  # type: ignore
from app.core.paths import uri_safe_string  # type: ignore
from app.extraction.file_utils import FileRecord
from app.ontology.wdo import WDOOntology


@dataclass
class DocExtractionContext:
    """Bundle state for extraction process; enables DRY and clarity."""

    ontology: Any
    ontology_cache: Any
    class_cache: Dict[str, Any]
    prop_cache: Dict[str, Any]
    excluded_dirs: set
    input_dir: str
    ttl_path: str
    log_path: str
    console: Optional[Console]

    def __str__(self) -> str:
        """User-friendly summary of context."""
        return f"DocExtractionContext(input_dir={self.input_dir}, ttl_path={self.ttl_path})"

    def __repr__(self) -> str:
        """Developer-friendly summary of context."""
        return (
            f"DocExtractionContext(ontology={self.ontology}, ontology_cache={self.ontology_cache}, "
            f"class_cache=..., prop_cache=..., excluded_dirs={self.excluded_dirs}, "
            f"input_dir={self.input_dir}, ttl_path={self.ttl_path}, log_path={self.log_path}, console={self.console})"
        )


@dataclass
class MarkdownElement:
    """Represents a parsed markdown element for triple generation."""

    type: str
    content: Optional[str] = None
    start_line: Optional[int] = None
    end_line: Optional[int] = None
    level: Optional[int] = None
    children: list = field(default_factory=list)
    token_index: Optional[int] = None
    tag: Optional[str] = None


# Setup logging to file only
log_path = get_log_path("doc_extractor.log")
os.makedirs(os.path.dirname(log_path), exist_ok=True)
LOGFORMAT_FILE = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
logger = logging.getLogger("doc_extractor")

# --- Ontology and File Paths ---
TTL_PATH = get_output_path("web_development_ontology.ttl")
INPUT_DIR = get_input_path("")

# --- Load documentation types and extensions from JSON files ---
CONTENT_TYPES_PATH = os.path.join(
    os.path.dirname(__file__), "../../model/content_types.json"
)
CARRIER_TYPES_PATH = os.path.join(
    os.path.dirname(__file__), "../../model/carrier_types.json"
)


def load_json(path: str) -> Any:
    """Load and parse JSON file for configuration or mapping."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


content_types = load_json(CONTENT_TYPES_PATH)
carrier_types = load_json(CARRIER_TYPES_PATH)


# Build a set of all documentation-related types and their children
doc_type_keys = [
    "APIDocumentation",
    "ArchitecturalDecisionRecord",
    "BestPracticeGuideline",
    "Changelog",
    "CodeComment",
    "ContributionGuide",
    "Tutorial",
    "UserGuide",
    "Readme",
    "Guide",
]
# Add 'Documentation' as a fallback
all_doc_types = set(doc_type_keys + ["Documentation"])

# Build regex patterns from content_types.json
doc_type_patterns = []
for classifier in content_types.get("classifiers", []):
    doc_type = classifier.get("class")
    regex_pattern = classifier.get("regex")
    if doc_type and regex_pattern:
        doc_type_patterns.append((re.compile(regex_pattern), doc_type))

# Also include extensions from carrier_types.json for DocumentationFile
for ext in carrier_types.get("DocumentationFile", []):
    if ext.startswith("."):
        doc_type_patterns.append((re.compile(f"^{re.escape(ext)}$"), "Documentation"))
    else:
        doc_type_patterns.append((re.compile(f"^{re.escape(ext)}$"), "Documentation"))


def get_doc_type_from_json(filename: str) -> str:
    """Identify documentation file type using regex patterns from content_types.json only."""
    for pattern, doc_type in doc_type_patterns:
        if pattern.match(filename):
            return str(doc_type)
    return "Documentation"


# Dynamically build code extensions from carrier_types.json
CODE_EXTS = set(carrier_types.get("SourceCodeFile", []))
CODE_EXTS.update(carrier_types.get("ScriptFile", []))

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

WDO = Namespace("http://semantic-web-kms.edu.et/wdo#")


def get_doc_type(filename: str) -> str:
    """Identify documentation file type based on filename using JSON mappings."""
    return get_doc_type_from_json(filename)


def extract_python_comments(code: str) -> List[Dict[str, Any]]:
    """Extract comments from Python code using tokenize and ast."""
    comments: List[Dict[str, Any]] = []
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
    except tokenize.TokenError:
        # TokenError can occur for incomplete code; skip such cases
        pass
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
    except (SyntaxError, ValueError):
        # Ignore files that can't be parsed as Python
        pass
    return comments


def extract_heading_level(token) -> Optional[int]:
    """Extract heading level from markdown token."""
    if token.type == "heading_open":
        # Extract level from tag (h1, h2, etc.)
        tag = getattr(token, "tag", "")
        if tag.startswith("h"):
            try:
                level = int(tag[1:])
                return level
            except ValueError:
                pass
        else:
            pass
    return None


def parse_api_documentation(
    text: str, doc_uri: URIRef, g: Graph, prop_cache: Dict[str, Any]
) -> None:
    """Parse API documentation for endpoints and HTTP methods."""
    # Why: Extract API endpoints and HTTP methods for semantic linking of documentation to API structure.
    import re

    # Extract endpoints (e.g., /api/users, /api/posts/{id})
    endpoint_pattern = r'["\'](/api/[^"\']+)["\']'
    for match in re.finditer(endpoint_pattern, text):
        endpoint = match.group(1)
        g.add(
            (
                doc_uri,
                prop_cache["hasEndpointPath"],
                Literal(endpoint, datatype=XSD.string),
            )
        )

    # Extract HTTP methods (GET, POST, PUT, DELETE, etc.)
    http_methods = ["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"]
    for method in http_methods:
        if method.lower() in text.lower():
            g.add(
                (
                    doc_uri,
                    prop_cache["hasHttpMethod"],
                    Literal(method, datatype=XSD.string),
                )
            )


def parse_adr_documentation(
    text: str,
    doc_uri: URIRef,
    g: Graph,
    prop_cache: Dict[str, Any],
    class_cache: Dict[str, Any],
) -> None:
    """Parse Architectural Decision Record for decision context."""
    # Why: Extract ADR context for traceability and architectural reasoning.
    import re

    # Extract decision context (often in sections like "Context", "Decision", "Consequences")
    context_patterns = [
        r"##\s*Context[:\s]*(.*?)(?=##|\Z)",
        r"##\s*Decision[:\s]*(.*?)(?=##|\Z)",
        r"##\s*Consequences[:\s]*(.*?)(?=##|\Z)",
    ]

    for pattern in context_patterns:
        for match in re.finditer(pattern, text, re.DOTALL | re.IGNORECASE):
            context = match.group(1).strip()
            if context:
                # Create a context element
                context_uri = URIRef(f"{doc_uri}_context_{hash(context) % 10000}")
                g.add((context_uri, RDF.type, class_cache["TextualElement"]))
                g.add(
                    (
                        context_uri,
                        prop_cache["hasTextValue"],
                        Literal(context, datatype=XSD.string),
                    )
                )
                # Add rdfs:label for context element
                g.add(
                    (
                        context_uri,
                        RDFS.label,
                        Literal(f"context: {context[:50]}...", datatype=XSD.string),
                    )
                )
                g.add((doc_uri, prop_cache["hasDocumentComponent"], context_uri))


def parse_guideline_documentation(
    text: str,
    doc_uri: URIRef,
    g: Graph,
    prop_cache: Dict[str, Any],
    class_cache: Dict[str, Any],
) -> None:
    """Parse Best Practice Guideline for guideline rules."""
    # Why: Extract guideline rules for best practice documentation and knowledge graph enrichment.
    import re

    # Extract guideline rules (often in numbered lists or bullet points)
    rule_patterns = [
        r"^\d+\.\s*(.+)$",  # Numbered lists
        r"^[-*]\s*(.+)$",  # Bullet points
        r"##\s*Guidelines?[:\s]*(.*?)(?=##|\Z)",
    ]

    for pattern in rule_patterns:
        for match in re.finditer(pattern, text, re.MULTILINE | re.IGNORECASE):
            rule = match.group(1).strip()
            if rule:
                # Create a rule element
                rule_uri = URIRef(f"{doc_uri}_rule_{hash(rule) % 10000}")
                g.add((rule_uri, RDF.type, class_cache["TextualElement"]))
                g.add(
                    (
                        rule_uri,
                        prop_cache["hasTextValue"],
                        Literal(rule, datatype=XSD.string),
                    )
                )
                # Add rdfs:label for rule element
                g.add(
                    (
                        rule_uri,
                        RDFS.label,
                        Literal(f"rule: {rule[:50]}...", datatype=XSD.string),
                    )
                )
                g.add((doc_uri, prop_cache["hasDocumentComponent"], rule_uri))


def extract_code_comments(code: str, ext: str) -> List[Dict[str, Any]]:
    """Extract comments from code files using language-specific methods."""
    comments: List[Dict[str, Any]] = []
    # Only extract comments for known code file types
    if ext == ".py":
        return extract_python_comments(code)
    # C/C++/Java/JavaScript/TypeScript style
    if ext in {
        ".js",
        ".mjs",
        ".jsx",
        ".ts",
        ".tsx",
        ".java",
        ".c",
        ".cpp",
        ".cs",
        ".go",
        ".rs",
    }:
        # // and /* ... */
        for match in re.finditer(r"//.*", code):
            line = code[: match.start()].count("\n") + 1
            comments.append(
                {
                    "raw": match.group().lstrip("//").strip(),
                    "start_line": line,
                    "end_line": line,
                }
            )
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
    # Shell and scripting languages
    if ext in {".sh", ".bash", ".zsh", ".ps1", ".rb", ".pl", ".lua", ".r"}:
        for match in re.finditer(r"#.*", code):
            line = code[: match.start()].count("\n") + 1
            comments.append(
                {
                    "raw": match.group().lstrip("#").strip(),
                    "start_line": line,
                    "end_line": line,
                }
            )
        return comments
    # Otherwise, do not extract comments
    return comments


# Helper: Check if a class is a subclass of another (by name)
def _is_textual_element(class_name: str) -> bool:
    return class_name in {
        "TextualElement",
        "Blockquote",
        "CodeBlock",
        "DocumentSection",
        "Heading",
        "List",
        "Paragraph",
        "Table",
    }


def _is_heading(class_name: str) -> bool:
    return class_name == "Heading"


def _is_software_code(class_name: str) -> bool:
    return class_name in {
        "SoftwareCode",
        "ProgrammingLanguageCode",
        "QueryLanguageCode",
        "WebPresentationCode",
        "JavaScriptCode",
        "PythonCode",
        "TypeScriptCode",
        "PHPCode",
        "RubyCode",
        "GoCode",
        "JavaCode",
        "RustCode",
        "CSharpCode",
        "SQLCode",
        "GraphQLCode",
        "CSSCode",
        "HTMLCode",
        "TestCode",
    }


def _is_documentation(class_name: str) -> bool:
    return class_name in {
        "Documentation",
        "APIDocumentation",
        "ArchitecturalDecisionRecord",
        "BestPracticeGuideline",
        "Changelog",
        "CodeComment",
        "ContributionGuide",
        "Guide",
        "Readme",
        "UserGuide",
    }


def add_doc_file_triples(
    file_rec: FileRecord,
    g: Graph,
    context: DocExtractionContext,
    file_uri: URIRef,
    doc_uri: URIRef,
    doc_type_class: Any,
    repo_uri: URIRef,
) -> None:
    """Add base triples for a documentation file and its content."""
    # Why: Add semantic triples for documentation file structure and relationships.
    g.add((file_uri, RDF.type, context.class_cache["DocumentationFile"]))
    g.add((file_uri, RDFS.label, Literal(file_rec.filename, datatype=XSD.string)))
    g.add(
        (
            file_uri,
            context.prop_cache["hasRelativePath"],
            Literal(file_rec.path, datatype=XSD.string),
        )
    )
    g.add(
        (
            file_uri,
            context.prop_cache["hasExtension"],
            Literal(file_rec.extension, datatype=XSD.string),
        )
    )
    g.add((doc_uri, RDF.type, doc_type_class))
    g.add(
        (
            doc_uri,
            RDFS.label,
            Literal(f"content: {file_rec.filename}", datatype=XSD.string),
        )
    )
    g.add((file_uri, context.prop_cache["bearerOfInformation"], doc_uri))
    g.add((doc_uri, context.prop_cache["informationBorneBy"], file_uri))
    g.add(
        (
            doc_uri,
            context.prop_cache["hasSimpleName"],
            Literal(file_rec.filename, datatype=XSD.string),
        )
    )
    g.add((repo_uri, WDO.hasFile, file_uri))


def parse_markdown(text: str) -> MarkdownElement:
    """Parse markdown text into a tree of MarkdownElement objects."""
    md = MarkdownIt()
    tokens = md.parse(text)
    root = MarkdownElement(type="document", children=[])
    parent_stack = [root]
    for i, token in enumerate(tokens):
        elem = None
        if token.nesting == 1:  # Opening token
            elem = MarkdownElement(
                type=token.type,
                content=None,
                start_line=token.map[0] + 1 if token.map else None,
                end_line=None,
                level=(
                    int(token.tag[1:])
                    if token.type == "heading_open"
                    and hasattr(token, "tag")
                    and token.tag.startswith("h")
                    and token.tag[1:].isdigit()
                    else None
                ),
                children=[],
                token_index=i,
                tag=getattr(token, "tag", None),
            )
            parent_stack[-1].children.append(elem)
            parent_stack.append(elem)
        elif token.nesting == -1:
            if len(parent_stack) > 1:
                parent_stack[-1].end_line = token.map[1] if token.map else None
                parent_stack.pop()
        elif token.nesting == 0:
            content = (
                token.content.strip()
                if hasattr(token, "content") and token.content
                else None
            )
            elem = MarkdownElement(
                type=token.type,
                content=content,
                start_line=token.map[0] + 1 if token.map else None,
                end_line=token.map[1] if token.map else None,
                children=[],
                token_index=i,
                tag=getattr(token, "tag", None),
            )
            parent_stack[-1].children.append(elem)
    return root


def add_triples_from_markdown(
    element: MarkdownElement,
    g: Graph,
    context: DocExtractionContext,
    parent_uri: URIRef,
    file_enc: str,
    parent_stack: Optional[list] = None,
):
    """Recursively add triples for markdown elements to the graph."""
    if parent_stack is None:
        parent_stack = [parent_uri]
    elem_uri = None
    if element.type in MD_TO_WDO:
        elem_class = context.class_cache[MD_TO_WDO[element.type]]
        elem_id = (
            f"{file_enc}_{element.type.replace('_open', '')}_{element.token_index}"
        )
        elem_uri = URIRef(f"http://semantic-web-kms.edu.et/wdo/instances/{elem_id}")
        label_prefix = MD_TO_WDO[element.type]
        label_content = element.content[:50] if element.content else None
        label = f"{label_prefix}: {label_content}" if label_content else label_prefix
        g.add((elem_uri, RDF.type, elem_class))
        g.add((elem_uri, RDFS.label, Literal(label, datatype=XSD.string)))
        g.add((parent_stack[-1], context.prop_cache["hasDocumentComponent"], elem_uri))
        if "isDocumentComponentOf" in context.prop_cache:
            g.add(
                (
                    elem_uri,
                    context.prop_cache["isDocumentComponentOf"],
                    parent_stack[-1],
                )
            )
        if element.start_line is not None:
            g.add(
                (
                    elem_uri,
                    context.prop_cache["startsAtLine"],
                    Literal(element.start_line, datatype=XSD.integer),
                )
            )
        if element.type == "heading_open" and element.level is not None:
            g.add(
                (
                    elem_uri,
                    context.prop_cache["hasHeadingLevel"],
                    Literal(element.level, datatype=XSD.positiveInteger),
                )
            )
        parent_stack.append(elem_uri)
    elif element.type in {"fence", "code_block"}:
        elem_class = context.class_cache["CodeBlock"]
        elem_id = f"{file_enc}_codeblock_{element.token_index}"
        elem_uri = URIRef(f"http://semantic-web-kms.edu.et/wdo/instances/{elem_id}")
        code_label = (
            f"CodeBlock: {element.content[:50]}" if element.content else "CodeBlock"
        )
        g.add((elem_uri, RDF.type, elem_class))
        g.add((elem_uri, RDFS.label, Literal(code_label, datatype=XSD.string)))
        g.add((parent_stack[-1], context.prop_cache["hasDocumentComponent"], elem_uri))
        if "isDocumentComponentOf" in context.prop_cache:
            g.add(
                (
                    elem_uri,
                    context.prop_cache["isDocumentComponentOf"],
                    parent_stack[-1],
                )
            )
        if element.content:
            g.add(
                (
                    elem_uri,
                    context.prop_cache["hasTextValue"],
                    Literal(element.content, datatype=XSD.string),
                )
            )
    elif element.type == "inline" and element.content:
        g.add(
            (
                parent_stack[-1],
                context.prop_cache["hasTextValue"],
                Literal(element.content, datatype=XSD.string),
            )
        )
    # Recurse for children
    for child in element.children:
        add_triples_from_markdown(
            child, g, context, elem_uri or parent_stack[-1], file_enc, parent_stack[:]
        )
    if elem_uri and elem_uri in parent_stack:
        parent_stack.pop()


def handle_special_doc_types(doc_type_class, text: str, doc_uri, g, context):
    """Handle special parsing for API, ADR, and Guideline documentation types."""
    if doc_type_class == context.class_cache["APIDocumentation"]:
        parse_api_documentation(text, doc_uri, g, context.prop_cache)
    elif doc_type_class == context.class_cache["ArchitecturalDecisionRecord"]:
        parse_adr_documentation(
            text, doc_uri, g, context.prop_cache, context.class_cache
        )
    elif doc_type_class == context.class_cache["BestPracticeGuideline"]:
        parse_guideline_documentation(
            text, doc_uri, g, context.prop_cache, context.class_cache
        )


def process_doc_files_with_context(
    doc_files: List[Dict[str, Any]], g: Graph, context: DocExtractionContext
) -> Iterator[int]:
    """Process documentation files and add triples to graph."""
    for rec in doc_files:
        repo = rec["repository"]
        rel_path = rec["path"]
        abs_path = rec["abs_path"]
        fname = rec["filename"]
        ext = rec["extension"]
        file_enc = uri_safe_string(rel_path)
        repo_enc = uri_enc = uri_safe_string(repo)
        file_uri = URIRef(
            f"http://semantic-web-kms.edu.et/wdo/instances/{repo_enc}/{file_enc}"
        )
        doc_uri = URIRef(
            f"http://semantic-web-kms.edu.et/wdo/instances/{repo_enc}/{file_enc}_content"
        )
        doc_type_class_name = get_doc_type(fname)
        doc_type_class = context.class_cache.get(
            doc_type_class_name, context.class_cache["Documentation"]
        )
        repo_uri = URIRef(f"http://semantic-web-kms.edu.et/wdo/instances/{repo_enc}")
        file_rec = FileRecord(
            id=rec["id"],
            repository=repo,
            path=rel_path,
            filename=fname,
            extension=ext,
            size_bytes=os.path.getsize(abs_path),
            abs_path=abs_path,
            class_uri=rec.get("class_uri") or "",
        )
        add_doc_file_triples(
            file_rec, g, context, file_uri, doc_uri, doc_type_class, repo_uri
        )
        try:
            with open(abs_path, "r", encoding="utf-8", errors="ignore") as f:
                text = f.read()
            root_elem = parse_markdown(text)
            add_triples_from_markdown(root_elem, g, context, doc_uri, file_enc)
            handle_special_doc_types(doc_type_class, text, doc_uri, g, context)
        except FileNotFoundError:
            # Why: File was deleted or moved during processing
            logger.error(f"File not found: {abs_path}", exc_info=True)
        except UnicodeDecodeError:
            # Why: File encoding is not supported or file is binary
            logger.error(f"Unicode decode error for file: {abs_path}", exc_info=True)
        except Exception as e:
            # Why: Catch-all for unexpected errors; log type for debugging
            logger.error(
                f"Unexpected error processing {abs_path} ({type(e).__name__}): {e}",
                exc_info=True,
            )
        yield 1


def add_code_file_triples(
    file_rec: FileRecord, g: Graph, context: DocExtractionContext, file_uri: URIRef
) -> None:
    """Add triples for code file structure and relationships."""
    # Why: Add semantic triples for code file structure and relationships.
    g.add(
        (
            file_uri,
            context.prop_cache["hasRelativePath"],
            Literal(file_rec.path, datatype=XSD.string),
        )
    )
    g.add(
        (
            file_uri,
            context.prop_cache["hasExtension"],
            Literal(file_rec.extension, datatype=XSD.string),
        )
    )


def add_code_comment_triples(
    comments: List[Dict[str, Any]],
    g: Graph,
    context: DocExtractionContext,
    file_uri: URIRef,
    file_enc: str,
    file_rec: FileRecord,
) -> None:
    """Add triples for code comments and their relationships to code files."""
    # Why: Add semantic triples for code comments and their relationships to code files.
    for idx, comment in enumerate(comments):
        comment_id = f"{file_enc}_codecomment_{idx}"
        comment_uri = URIRef(
            f"http://semantic-web-kms.edu.et/wdo/instances/{comment_id}"
        )
        g.add((comment_uri, RDF.type, context.class_cache["CodeComment"]))
        comment_label = (
            f"CodeComment: {comment['raw'][:50]}"
            if comment.get("raw")
            else "CodeComment"
        )
        g.add((comment_uri, RDFS.label, Literal(comment_label, datatype=XSD.string)))
        if "isElementOf" in context.prop_cache:
            g.add((comment_uri, context.prop_cache["isElementOf"], file_uri))
        g.add(
            (
                comment_uri,
                context.prop_cache["hasTextValue"],
                Literal(comment["raw"], datatype=XSD.string),
            )
        )
        g.add(
            (
                comment_uri,
                context.prop_cache["startsAtLine"],
                Literal(comment["start_line"], datatype=XSD.integer),
            )
        )
        g.add(
            (
                comment_uri,
                context.prop_cache["endsAtLine"],
                Literal(comment["end_line"], datatype=XSD.integer),
            )
        )
        comment_class_name = None
        for k, v in context.class_cache.items():
            if v == context.class_cache["CodeComment"]:
                comment_class_name = k
                break
        file_class_name = None
        for k, v in context.class_cache.items():
            if v == file_rec.class_uri:
                file_class_name = k
                break
        if file_class_name is not None and _is_software_code(file_class_name):
            g.add((comment_uri, context.prop_cache["isAboutCode"], file_uri))
        if (
            file_class_name is not None
            and comment_class_name is not None
            and _is_software_code(file_class_name)
            and _is_documentation(comment_class_name)
        ):
            g.add((file_uri, context.prop_cache["hasCodeDocumentation"], comment_uri))


def process_code_files_with_context(
    code_files: List[Dict[str, Any]], g: Graph, context: DocExtractionContext
) -> Iterator[int]:
    """Process code files and add code comment triples to graph."""
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
        file_rec = FileRecord(
            id=rec["id"],
            repository=repo,
            path=rel_path,
            filename=fname,
            extension=ext,
            size_bytes=os.path.getsize(abs_path),
            abs_path=abs_path,
            class_uri=rec.get("class_uri") or "",
        )
        add_code_file_triples(file_rec, g, context, file_uri)
        try:
            with open(abs_path, "r", encoding="utf-8", errors="ignore") as f:
                code = f.read()
            comments = extract_code_comments(code, ext)
            add_code_comment_triples(comments, g, context, file_uri, file_enc, file_rec)
        except FileNotFoundError:
            # Why: File was deleted or moved during processing
            logger.warning(f"File not found: {abs_path}")
        except UnicodeDecodeError:
            # Why: File encoding is not supported or file is binary
            logger.warning(f"Unicode decode error for file: {abs_path}")
        except Exception as e:
            # Why: Catch-all for unexpected errors; log type for debugging
            logger.warning(
                f"Unexpected error processing {abs_path} ({type(e).__name__}): {e}"
            )
        yield 1


def process_doc_files(doc_files, g, class_cache, prop_cache, ontology, console):
    """Create context and process documentation files."""
    context = DocExtractionContext(
        ontology=ontology,
        ontology_cache=None,
        class_cache=class_cache,
        prop_cache=prop_cache,
        excluded_dirs=set(),
        input_dir="",
        ttl_path="",
        log_path="",
        console=console,
    )
    yield from process_doc_files_with_context(doc_files, g, context)


def process_code_files(code_files, g, class_cache, prop_cache):
    """Create context and process code files."""
    context = DocExtractionContext(
        ontology=None,
        ontology_cache=None,
        class_cache=class_cache,
        prop_cache=prop_cache,
        excluded_dirs=set(),
        input_dir="",
        ttl_path="",
        log_path="",
        console=None,
    )
    yield from process_code_files_with_context(code_files, g, context)


def run_extraction(context: DocExtractionContext, doc_files, code_files, g):
    """Run extraction and write TTL with progress bar."""
    with Progress(
        TextColumn("[bold blue]{task.description}"),
        BarColumn(),
        "[progress.percentage]{task.percentage:>3.0f}%",
        TimeElapsedColumn(),
        console=context.console,
    ) as progress:
        extract_task = progress.add_task(
            "[blue]Extracting documentation...", total=len(doc_files) + len(code_files)
        )
        for _ in process_doc_files_with_context(doc_files, g, context):
            progress.advance(extract_task)
        for _ in process_code_files(
            code_files, g, context.class_cache, context.prop_cache
        ):
            progress.advance(extract_task)
        # Use the new write_ttl_with_progress signature from rdf_utils
        from app.extraction.rdf_utils import write_ttl_with_progress

        all_records = doc_files + code_files

        def add_triples_fn(graph, record, *args, **kwargs):
            # This is a placeholder; actual triple addition logic should be implemented as needed
            pass

        ttl_task = progress.add_task("[blue]Writing TTL...", total=len(all_records))
        write_ttl_with_progress(
            all_records,
            add_triples_fn,
            g,
            context.ttl_path,
            progress,
            ttl_task,
        )


def report_progress(context: DocExtractionContext, doc_files, repo_dirs):
    """Log and print extraction completion summary."""
    logger.info(f"Documentation extraction complete: {len(doc_files)} doc files")
    if context.console is not None:
        context.console.print(
            f"[bold green]Documentation extraction complete:[/bold green] {len(doc_files)} doc files"
        )
        context.console.print(
            f"[bold green]Ontology updated and saved to:[/bold green] [cyan]{context.ttl_path}[/cyan]"
        )


def _setup_ontology_and_cache():
    ontology = WDOOntology(get_web_dev_ontology_path())
    ontology_cache = get_ontology_cache()
    class_cache = {
        k: ontology.get_class(k)
        for k in set(MD_TO_WDO.values())
        | {
            "DocumentationFile",
            "Documentation",
            "CodeComment",
            "APIDocumentation",
            "ArchitecturalDecisionRecord",
            "BestPracticeGuideline",
            "TextualElement",
            "Heading",
            "Paragraph",
            "List",
            "CodeBlock",
            "Blockquote",
            "Table",
            "DocumentSection",
        }
    }
    prop_cache = ontology_cache.get_property_cache(get_doc_extraction_properties())
    return ontology, ontology_cache, class_cache, prop_cache


def _create_context(console, ontology, ontology_cache, class_cache, prop_cache):
    excluded_dirs_path = get_excluded_directories_path()
    with open(excluded_dirs_path, "r") as f:
        excluded_dirs = set(json.load(f))
    return DocExtractionContext(
        ontology=ontology,
        ontology_cache=ontology_cache,
        class_cache=class_cache,
        prop_cache=prop_cache,
        excluded_dirs=excluded_dirs,
        input_dir=INPUT_DIR,
        ttl_path=TTL_PATH,
        log_path=log_path,
        console=console,
    )


def discover_files(
    context: DocExtractionContext,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[str]]:
    """Discover documentation and code files in input repositories."""
    doc_files: List[Dict[str, Any]] = []
    code_files: List[Dict[str, Any]] = []
    file_id = 1
    repo_dirs = [
        d
        for d in os.listdir(context.input_dir)
        if os.path.isdir(os.path.join(context.input_dir, d))
        and d not in context.excluded_dirs
    ]
    for repo in repo_dirs:
        repo_path = os.path.join(context.input_dir, repo)
        for dirpath, dirnames, filenames in os.walk(repo_path):
            dirnames[:] = [d for d in dirnames if d not in context.excluded_dirs]
            for fname in filenames:
                abs_path = os.path.join(dirpath, fname)
                rel_path = os.path.relpath(abs_path, repo_path)
                ext = Path(fname).suffix.lower()
                is_doc = get_doc_type(fname) != "Documentation"
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
    return doc_files, code_files, repo_dirs


def setup_graph(context: DocExtractionContext) -> Graph:
    """Load or create RDF graph for triples."""
    g = Graph()
    if os.path.exists(context.ttl_path):
        g.parse(context.ttl_path, format="turtle")
    return g


def main() -> None:
    """Run the documentation extraction process."""
    console = Console()
    logger.info("Starting documentation extraction process...")
    ontology, ontology_cache, class_cache, prop_cache = _setup_ontology_and_cache()
    context = _create_context(
        console, ontology, ontology_cache, class_cache, prop_cache
    )
    doc_files, code_files, repo_dirs = discover_files(context)
    g = setup_graph(context)
    logger.info(
        f"Found {len(doc_files)} documentation files and {len(code_files)} code files in {len(repo_dirs)} repositories"
    )
    run_extraction(context, doc_files, code_files, g)
    report_progress(context, doc_files, repo_dirs)


if __name__ == "__main__":
    main()
