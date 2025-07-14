"""Shared utilities for annotation modules."""

import logging
from typing import Dict, List, Optional, Union

import spacy
from rdflib import RDF, Graph, URIRef
from rdflib.namespace import RDFS

from app.core.rate_limiter import get_gemini_limiter

logger = logging.getLogger("annotation_utils")


# Global spaCy NLP model for performance optimization
_SPACY_NLP = None


def get_spacy_nlp():
    """
    Get a cached spaCy NLP model for English.

    Returns:
        The spaCy language model.
    """
    global _SPACY_NLP
    if _SPACY_NLP is None:
        _SPACY_NLP = spacy.load("en_core_web_sm")
    return _SPACY_NLP


def find_uri_by_label(graph: Graph, label: str) -> Optional[URIRef]:
    """
    Find a URI in the label-to-URI map by label (case-insensitive).

    Args:
        label: The label to search for.

    Returns:
        The URI if found, None otherwise.
    """
    logger.debug(f"Searching for URI with label: {label}")
    for s, p, o in graph.triples((None, RDFS.label, None)):
        if str(o).lower() == label.lower() and isinstance(s, URIRef):
            logger.debug(f"Found URI {s} for label '{label}'")
            return s
    logger.debug(f"No URI found for label '{label}'")
    return None


def build_label_to_uri_map(graph: Graph) -> Dict[str, URIRef]:
    """
    Build a mapping from labels to URIs for all entities in the graph.

    Args:
        graph: The RDF graph.

    Returns:
        Dictionary mapping lowercase labels to URIs
    """
    logger.info("Building label to URI lookup map...")
    label_map = {
        str(o).lower(): s
        for s, p, o in graph.triples((None, RDFS.label, None))
        if isinstance(s, URIRef)
    }
    logger.info(f"Built label map with {len(label_map)} entries")
    return label_map


def find_uri_by_label_fast(
    label_map: Dict[str, URIRef], label: str
) -> Union[URIRef, None]:
    """
    Quickly find a URI by label using a pre-built map.

    Args:
        label_map: Pre-computed dictionary mapping lowercase labels to URIs
        label: Label to look up

    Returns:
        URIRef if found, None otherwise
    """
    return label_map.get(label.lower())


def _make_gemini_api_call(prompt: str, api_key: str, model: str) -> str:
    """
    Make an API call to Gemini for text generation.

    Args:
        prompt: The prompt to send to Gemini
        api_key: The Gemini API key
        model: The Gemini model to use

    Returns:
        The generated template string

    Raises:
        ImportError: If google-genai is not installed
        ValueError: If no JSON object is found in the response
    """
    try:
        from google import genai
    except ImportError:
        raise ImportError("google-genai is not installed.")

    logger.info(f"Sending prompt to Gemini model: {model}")
    logger.debug(f"Prompt length: {len(prompt)} characters")

    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(model=model, contents=prompt)

    import json
    import re

    text = response.text or ""

    logger.info(f"Received response from Gemini (length: {len(text)} characters)")
    logger.debug(f"Raw response: {text}")

    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            json_data = json.loads(match.group(0))
            template = json_data["template"]
            logger.info(
                f"Successfully extracted template (length: {len(template)} characters)"
            )
            logger.debug(f"Extracted template: {template}")
            return str(template)
        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Failed to parse JSON response: {e}")
            logger.debug(f"Matched text: {match.group(0)}")
            raise ValueError(f"Invalid JSON in Gemini response: {e}")
    else:
        logger.error("No JSON object found in Gemini response")
        logger.debug(f"Full response text: {text}")
        raise ValueError("No JSON object found in Gemini response.")


def get_gemini_template(
    prompt: str, api_key: str, model: str = "gemini-2.5-flash-lite-preview-06-17"
) -> str:
    """
    Get a Gemini template for a given class and properties.

    Args:
        prompt: The prompt to send to Gemini.
        api_key: The Gemini API key.
        model: The Gemini model to use.

    Returns:
        The generated template string.

    Raises:
        ImportError: If google-genai is not installed.
        ValueError: If no JSON object is found in the response.
    """
    # Get the rate limiter for Gemini API
    rate_limiter = get_gemini_limiter()

    # Use the rate limiter to make the API call with automatic retry logic
    return str(
        rate_limiter.call_with_retry(_make_gemini_api_call, prompt, api_key, model)
    )


def extract_class_name(class_uri: str) -> str:
    """
    Extract the class name from a URI or string.

    Args:
        class_uri: Full class URI

    Returns:
        Short class name
    """
    return class_uri.split("#")[-1]


def convert_property_to_snake_case(prop_uri: str) -> str:
    """
    Convert a property name to snake_case.

    Args:
        prop_uri: Property URI

    Returns:
        Snake_case property name
    """
    return prop_uri.split("/")[-1].split("#")[-1].replace("-", "_")


def render_template_with_jinja2(template: str, properties: Dict) -> str:
    """
    Render a template using Jinja2 with the provided context.

    Args:
        template: Jinja2 template string
        properties: Dictionary of property values (should be in snake_case)

    Returns:
        Rendered template string
    """
    logger.info(f"Rendering template with {len(properties)} properties")
    logger.debug(f"Template: {template}")
    logger.debug(f"Properties: {properties}")

    try:
        # Convert simple {} placeholders to Jinja2 {{}} syntax if needed
        import re

        if "{{" not in template and "}}" not in template:
            # Convert simple {} placeholders to Jinja2 {{}} syntax
            template = re.sub(r"\{([^}]+)\}", r"{{\1}}", template)
            logger.debug(f"Converted template to Jinja2 syntax: {template}")

        from jinja2 import Environment, select_autoescape

        env = Environment(autoescape=select_autoescape())
        jinja_template = env.from_string(template)
        result = jinja_template.render(**properties)
        logger.info(
            f"Template rendered successfully (length: {len(result)} characters)"
        )
        logger.debug(f"Rendered result: {result}")
        return str(result)
    except Exception as e:
        logger.error(f"Failed to render Jinja2 template: {e}")
        logger.debug(f"Template that failed: {template}")
        logger.debug(f"Properties that failed: {properties}")
        # Fallback to simple string replacement for basic templates
        return str(template)


def clean_label(label: str) -> str:
    """
    Clean up a label for display.

    Args:
        label: The label string to clean.

    Returns:
        Cleaned label string with underscores/hyphens replaced by spaces, stripped, and title-cased.
    """
    label = label.replace("_", " ").replace("-", " ").strip()
    if not label:
        return ""
    # If label is all uppercase or all lowercase, use title case
    if label.isupper() or label.islower():
        label = label.title()
    else:
        # Otherwise, just capitalize first letter
        label = label[0].upper() + label[1:]
    return label


def get_label(graph: Graph, uri) -> str:
    """
    Get a human-readable label for a URI from the graph.

    Args:
        graph: RDF graph to search in.
        uri: URI to get label for.

    Returns:
        Cleaned label string.
    """
    label = None
    for _, _, o in graph.triples((uri, RDFS.label, None)):
        label = str(o)
        break
    if label:
        return clean_label(label)
    if isinstance(uri, URIRef):
        raw = str(uri).split("/")[-1].split("#")[-1]
        return clean_label(raw)
    return clean_label(str(uri))


def is_instance(graph: Graph, entity) -> bool:
    """
    Check if an entity is an instance (not a class or property).

    Args:
        graph: RDF graph to check in.
        entity: Entity to check.

    Returns:
        True if entity is an instance, False otherwise.
    """
    from rdflib.namespace import OWL

    from app.annotation.semantic_annotator import ANNOTATION_PROPERTIES

    # Exclude annotation properties and ontology classes/properties
    for _, _, o in graph.triples((entity, RDF.type, None)):
        if o in (
            OWL.Class,
            OWL.ObjectProperty,
            OWL.DatatypeProperty,
            RDFS.Class,
            RDF.Property,
            OWL.AnnotationProperty,
        ):
            return False
    if entity in ANNOTATION_PROPERTIES:
        return False
    return True


def get_code_snippet(graph: Graph, entity) -> str:
    """
    Return the code snippet (hasSourceCodeSnippet) for the given entity URI, or empty string.

    Args:
        graph: RDF graph to search in.
        entity: Entity URI to get the code snippet for.

    Returns:
        The code snippet as a string if found, otherwise an empty string.
    """
    for _, p, o in graph.triples((entity, None, None)):
        if "hasSourceCodeSnippet" in str(p):
            return str(o)
    return ""


def extract_keywords(text: str, top_n: int = 5) -> List[str]:
    """
    Extract top keywords from text using NLTK and NumPy.

    Args:
        text: Input text.
        top_n: Number of keywords to return.

    Returns:
        List of keywords.
    """
    from collections import Counter

    from nltk.corpus import stopwords
    from nltk.tokenize import word_tokenize

    STOPWORDS = set(stopwords.words("english"))

    words = [
        w.lower()
        for w in word_tokenize(text)
        if w.isalpha() and w.lower() not in STOPWORDS
    ]
    if not words:
        return []
    counts = Counter(words)
    most_common = counts.most_common(top_n)
    return [w for w, _ in most_common]


def create_progress_bar():
    """
    Create a Rich progress bar with custom styling to match the extraction pipeline.

    Returns:
        Progress object
    """
    from rich.console import Console
    from rich.progress import BarColumn, Progress, TextColumn, TimeElapsedColumn

    console = Console()

    # Define custom progress bar with green completion styling (matching extraction)
    bar_column = BarColumn(
        bar_width=30,  # Thinner bar width
        style="blue",  # Style for the incomplete part of the bar
        complete_style="bold blue",  # Style for the completed part
        finished_style="bold green",  # Style when task is 100% complete
    )

    return Progress(
        TextColumn(
            "[bold blue]{task.description:<40}", justify="left"
        ),  # Fixed width for alignment
        bar_column,  # Use custom bar column
        "[progress.percentage]{task.percentage:>3.0f}%",
        TimeElapsedColumn(),
        console=console,
    )
