"""Shared utilities for annotation modules."""

import json
import logging
import re
from collections import Counter

import spacy
from jinja2 import Environment, select_autoescape
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from rdflib import RDF, Graph, URIRef
from rdflib.namespace import OWL, RDFS
from rich.console import Console
from rich.progress import BarColumn, Progress, TextColumn, TimeElapsedColumn

try:
    from google import genai
except ImportError:
    raise ImportError("google-genai is not installed.") from None

from engine.annotation import constants
from engine.annotation.constants import ANNOTATION_PROPERTIES
from engine.core.rate_limiter import get_gemini_limiter

logger = logging.getLogger("annotation_utils")


_SPACY_NLP = None


def get_spacy_nlp():
    """
    Get a cached spaCy NLP model for English.

    Returns:
        The spaCy language model.
    """
    global _SPACY_NLP
    if _SPACY_NLP is None:
        logger.info("Loading spaCy model 'en_core_web_sm'...")
        _SPACY_NLP = spacy.load("en_core_web_sm")
        logger.info("spaCy model loaded.")
    return _SPACY_NLP


def find_uri_by_label(graph: Graph, label: str) -> URIRef | None:
    """
    Find a URI in the graph by its rdfs:label (case-insensitive).

    Args:
        graph: The RDF graph to search in.
        label: The label to search for.

    Returns:
        The URI if found, None otherwise.
    """
    logger.debug(f"Searching for URI with label: {label}")
    for s, _p, o in graph.triples((None, RDFS.label, None)):
        if str(o).lower() == label.lower() and isinstance(s, URIRef):
            logger.debug(f"Found URI {s} for label '{label}'")
            return s
    logger.debug(f"No URI found for label '{label}'")
    return None


def build_label_to_uri_map(graph: Graph) -> dict[str, URIRef]:
    """
    Build a mapping from lowercase labels to URIs for all entities in the graph.

    Args:
        graph: The RDF graph.

    Returns:
        Dictionary mapping lowercase labels to URIs for fast lookups.
    """
    logger.info("Building label to URI lookup map...")
    label_map = {
        str(o).lower(): s
        for s, _p, o in graph.triples((None, RDFS.label, None))
        if isinstance(s, URIRef)
    }
    logger.info(f"Built label map with {len(label_map)} entries")
    return label_map


def _make_gemini_api_call(prompt: str, api_key: str, model: str) -> str:
    """
    Make an API call to Gemini for text generation.

    Args:
        prompt: The prompt to send to Gemini
        api_key: The Gemini API key
        model: The Gemini model to use

    Returns:
        The generated template string from the 'template' key in the JSON response.

    Raises:
        ImportError: If google-genai is not installed.
        ValueError: If no valid JSON object with a 'template' key is found.
    """
    logger.info(f"Sending prompt to Gemini model: {model}")
    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(model=model, contents=prompt)
    text = response.text or ""
    logger.debug(f"Raw response from Gemini: {text[:500]}...")

    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        logger.error("No JSON object found in Gemini response.")
        raise ValueError("No JSON object found in Gemini response.")

    try:
        json_data = json.loads(match.group(0))
        template = json_data["template"]
        logger.info("Successfully extracted template from Gemini response.")
        return str(template)
    except (json.JSONDecodeError, KeyError) as e:
        logger.error(f"Failed to parse JSON or find 'template' key: {e}")
        raise ValueError(
            f"Invalid JSON or missing 'template' key in response: {e}"
        ) from e


def get_gemini_template(prompt: str, api_key: str, model: str | None = None) -> str:
    """
    Get a Gemini template, using the centralized default model if none is specified.

    Args:
        prompt: The prompt to send to Gemini.
        api_key: The Gemini API key.
        model: The Gemini model to use. Defaults to the one in constants.py.

    Returns:
        The generated template string.
    """
    if model is None:
        model = constants.GEMINI_DEFAULT_MODEL

    rate_limiter = get_gemini_limiter()
    return str(
        rate_limiter.call_with_retry(_make_gemini_api_call, prompt, api_key, model)
    )


def extract_class_name(class_uri: str) -> str:
    """Extract the short class name from a full URI."""
    return class_uri.split("#")[-1]


def convert_property_to_snake_case(prop_uri: str) -> str:
    """Convert a property URI to a snake_case string."""
    return prop_uri.split("/")[-1].split("#")[-1].replace("-", "_")


def render_template_with_jinja2(template: str, properties: dict) -> str:
    """
    Render a template using Jinja2 with the provided properties.

    Args:
        template: A valid Jinja2 template string.
        properties: Dictionary of property values.

    Returns:
        The rendered string.
    """
    logger.debug(f"Rendering Jinja2 template with {len(properties)} properties.")
    try:
        env = Environment(autoescape=select_autoescape())
        jinja_template = env.from_string(template)
        return str(jinja_template.render(**properties))
    except Exception as e:
        logger.error(f"Failed to render Jinja2 template: {e}")
        return f"Error rendering template: {e}"


def get_label(graph: Graph, uri: URIRef) -> str:
    """Get a human-readable label for a URI from the graph."""
    label_obj = graph.value(subject=uri, predicate=RDFS.label, any=False)
    if label_obj:
        return str(label_obj).replace("_", " ").replace("-", " ").strip()

    # Fallback to parsing the URI
    return str(uri).split("/")[-1].split("#")[-1].replace("-", " ").replace("_", " ")


def is_instance(graph: Graph, entity: URIRef) -> bool:
    """
    Check if an entity is an instance (not a class or property).

    Args:
        graph: RDF graph to check in.
        entity: Entity to check.

    Returns:
        True if the entity is an instance, False otherwise.
    """
    if entity in ANNOTATION_PROPERTIES:
        return False

    for rdf_type in graph.objects(subject=entity, predicate=RDF.type):
        if rdf_type in (
            OWL.Class,
            RDFS.Class,
            RDF.Property,
            OWL.ObjectProperty,
            OWL.DatatypeProperty,
            OWL.AnnotationProperty,
        ):
            return False
    return True


def extract_keywords(text: str, top_n: int = 5) -> list[str]:
    """
    Extract top keywords from text using NLTK.

    Args:
        text: Input text.
        top_n: Number of keywords to return.

    Returns:
        List of keywords.
    """
    stopwords_set = set(stopwords.words("english"))
    words = [
        w.lower()
        for w in word_tokenize(text)
        if w.isalpha() and len(w) > 2 and w.lower() not in stopwords_set
    ]
    if not words:
        return []
    return [w for w, _ in Counter(words).most_common(top_n)]


def create_progress_bar():
    """Create a Rich progress bar with custom styling."""
    console = Console()
    bar_column = BarColumn(
        bar_width=30,
        style="blue",
        complete_style="bold blue",
        finished_style="bold green",
    )
    return Progress(
        TextColumn("[bold blue]{task.description:<40}", justify="left"),
        bar_column,
        "[progress.percentage]{task.percentage:>3.0f}%",
        TimeElapsedColumn(),
        console=console,
    )
