"""Module for postprocessing and enriching semantic annotations."""

import logging
from dataclasses import dataclass

import numpy as np
import textstat
from nltk.sentiment import SentimentIntensityAnalyzer
from nltk.tokenize import sent_tokenize, word_tokenize
from rdflib import RDF, Graph, URIRef
from rdflib.term import Node

from engine.annotation.constants import ANNOTATION_PROPERTIES, ENTITY_BASE_URL
from engine.annotation.utils import extract_keywords, find_uri_by_label, get_spacy_nlp

_SIA = None


def get_sentiment_analyzer():
    """
    Get NLTK sentiment analyzer, loading it only once for performance.

    Returns:
        SentimentIntensityAnalyzer instance.
    """
    global _SIA
    if _SIA is None:
        _SIA = SentimentIntensityAnalyzer()
    return _SIA


logger = logging.getLogger("annotation_postprocessing")


def enrich_description_with_links(
    graph: Graph,
    description: str,
    label_map: dict[str, URIRef] | None = None,
    nlp=None,
    base_url: str = ENTITY_BASE_URL,
) -> str:
    """
    Enrich a description with entity links using the RDF graph.

    Args:
        graph: The RDF graph.
        description: The description text to enrich.
        label_map: Optional pre-computed label to URI mapping.
        nlp: Pre-loaded spaCy model for performance.
        base_url: Base URL for entity links.

    Returns:
        The enriched description with HTML links.
    """
    if not description.strip():
        return description

    if nlp is None:
        nlp = get_spacy_nlp()

    doc = nlp(description)
    if not doc.ents:
        return description

    logger.info(f"Found {len(doc.ents)} named entities in description")
    logger.debug(f"Named entities: {[ent.text for ent in doc.ents]}")

    enriched = description
    offset = 0
    links_added = 0

    def _get_uri(ent_text: str) -> tuple[URIRef | None, str]:
        if label_map is not None:
            return label_map.get(ent_text.lower()), "fast lookup"
        return find_uri_by_label(graph, ent_text), "graph search"

    def _add_link(
        enriched: str, ent_text: str, href: str, offset: int
    ) -> tuple[str, int]:
        start = enriched.find(ent_text, offset)
        if start == -1:
            logger.debug(f"Could not find '{ent_text}' in enriched text for linking")
            return enriched, offset
        end = start + len(ent_text)
        linked = enriched[:start] + f"<a href='{href}'>{ent_text}</a>" + enriched[end:]
        new_offset = end + len(href) + 15
        return linked, new_offset

    for ent in doc.ents:
        logger.debug(f"Processing entity: {ent.text}")
        uri, lookup_method = _get_uri(ent.text)
        if uri:
            uri_str = str(uri)
            href = f"{base_url}{uri_str.split('#')[-1]}"
            enriched, offset = _add_link(enriched, ent.text, href, offset)
            links_added += 1
            logger.debug(
                f"Added link for '{ent.text}' -> {href} (using {lookup_method})"
            )
        else:
            logger.debug(
                f"No URI found for entity '{ent.text}' (using {lookup_method})"
            )

    logger.info(f"Enrichment complete: added {links_added} links to description")
    logger.debug(f"Enriched description length: {len(enriched)} characters")
    return enriched


def check_grammaticality(description: str) -> bool:
    """
    Check the grammaticality of a text using language tools.

    Args:
        description: The text to check.

    Returns:
        True if the description is grammatical, False otherwise.
    """
    logger.debug(
        f"Checking grammaticality of description (length: {len(description)} "
        "characters)"
    )

    nlp = get_spacy_nlp()
    doc = nlp(description)

    has_root_verb = any(token.dep_ == "ROOT" and token.pos_ == "VERB" for token in doc)

    if has_root_verb:
        logger.debug("Description is grammatical (has root verb)")
    else:
        logger.debug("Description is not grammatical (no root verb)")

    return has_root_verb


def get_readability_score(description: str) -> float:
    """
    Compute the readability score for a given text.

    Args:
        description: The text to score.

    Returns:
        The Flesch reading ease score.
    """
    logger.debug(
        f"Calculating readability score for description (length: {len(description)} characters)"
    )
    score = getattr(textstat, "flesch_reading_ease", lambda _: 50.0)(description)
    logger.debug(f"Readability score: {score:.2f}")
    logger.info(f"Readability: {score:.2f} ({_interpret_readability(score)})")
    return score


def _interpret_readability(score: float) -> str:
    """Return a human-readable interpretation of the Flesch reading ease score."""
    if score >= 90:
        return "Very Easy"
    if score >= 80:
        return "Easy"
    if score >= 70:
        return "Fairly Easy"
    if score >= 60:
        return "Standard"
    if score >= 50:
        return "Fairly Difficult"
    if score >= 30:
        return "Difficult"
    return "Very Difficult"


def get_sentiment(description: str) -> dict[str, float]:
    """
    Analyze the sentiment of a text and return a sentiment score.

    Args:
        description: The text to analyze.

    Returns:
        Dictionary containing sentiment scores (negative, neutral, positive, compound).
    """
    logger.debug(
        f"Analyzing sentiment of description (length: {len(description)} characters)"
    )

    sia = get_sentiment_analyzer()
    sentiment_scores: dict[str, float] = sia.polarity_scores(description)

    logger.debug(f"Sentiment scores: {sentiment_scores}")

    # Determine primary sentiment
    compound = sentiment_scores["compound"]
    if compound >= 0.05:
        sentiment = "Positive"
    elif compound <= -0.05:
        sentiment = "Negative"
    else:
        sentiment = "Neutral"

    logger.info(f"Sentiment: {sentiment} (compound: {compound:.3f})")
    return sentiment_scores


@dataclass(frozen=True)
class QualityMetrics:
    """A structured container for text quality metrics."""

    is_grammatical: bool
    readability_score: float
    sentiment_scores: dict[str, float]
    original_length: int
    enriched_length: int


def enrich_and_validate_summary(
    graph: Graph,
    instance_uri: Node,
    summary: str,
    label_map: dict[str, URIRef] | None = None,
) -> tuple[str, QualityMetrics]:
    """
    Enrich and validate a summary for an instance.

    Args:
        graph: The RDF graph containing the instance.
        instance_uri: The URI of the instance.
        summary: The original summary text.
        label_map: Optional pre-computed label to URI mapping.

    Returns:
        Tuple of (enriched_summary, QualityMetrics).
    """
    logger.info(f"Starting enrichment and validation for instance {instance_uri}")
    logger.info(f"Original summary length: {len(summary)} characters")
    logger.debug(f"Original summary: {summary}")

    enriched_summary = enrich_description_with_links(graph, summary, label_map)

    grammatical = check_grammaticality(enriched_summary)
    readability = get_readability_score(enriched_summary)
    sentiment = get_sentiment(enriched_summary)

    metrics = QualityMetrics(
        is_grammatical=grammatical,
        readability_score=readability,
        sentiment_scores=sentiment,
        original_length=len(summary),
        enriched_length=len(enriched_summary),
    )

    logger.info(f"Enrichment and validation complete for instance {instance_uri}")
    logger.info(
        f"Quality metrics: grammatical={metrics.is_grammatical}, "
        f"readability={metrics.readability_score:.2f}, "
        f"sentiment_compound={metrics.sentiment_scores['compound']:.3f}"
    )
    logger.debug(f"Final enriched summary: {enriched_summary}")

    return enriched_summary, metrics


def extract_relationship_context(
    graph: Graph, entity: URIRef, label_lookup: dict
) -> list[str]:
    """
    Extract and phrase relationships for an entity in natural language.

    Args:
        graph: RDF graph.
        entity: The instance URI.
        label_lookup: Precomputed {URI: label} dict for fast lookup.

    Returns:
        List of natural language relationship descriptions.
    """

    def _should_skip_property(p):
        return p in ANNOTATION_PROPERTIES or p == RDF.type

    def _get_label(uri):
        return label_lookup.get(uri, str(uri).split("/")[-1])

    rels: list[str] = []
    for _, p, o in graph.triples((entity, None, None)):
        if _should_skip_property(p):
            continue
        if isinstance(o, URIRef) and o in label_lookup:
            pred_label = _get_label(p)
            obj_label = _get_label(o)
            rels.append(f"This instance {pred_label.replace('_', ' ')} {obj_label}.")
    return rels


def _extract_docstring_or_comment(lines: list[str]) -> str:
    """Extract the first docstring or comment from the code snippet lines."""
    for line in lines:
        stripped = line.strip()
        if stripped.startswith('"""') or stripped.startswith("'''"):
            return stripped.strip("\"'")
        if stripped.startswith("#"):
            return stripped.lstrip("#").strip()
    return ""


def _select_informative_sentence(lines: list[str]) -> str:
    """Select the most informative sentence from the code snippet using NLP and keyword overlap."""
    text = " ".join(lines[:15])
    doc = get_spacy_nlp()(text)
    sents = [sent.text for sent in doc.sents]
    if not sents:
        sents = sent_tokenize(text)
    keywords = extract_keywords(text, top_n=7)
    sent_scores = _score_sentences_by_keywords(sents, keywords)
    if sent_scores:
        idx = int(np.argmax(sent_scores))
        return sents[idx]
    if lines:
        return lines[0][:120] + ("..." if len(lines[0]) > 120 else "")
    return ""


def _score_sentences_by_keywords(sents: list[str], keywords: list[str]) -> list[int]:
    """Score each sentence by the number of keyword overlaps."""
    scores = []
    for sent in sents:
        sent_words = set(word_tokenize(sent.lower()))
        score = sum(1 for k in keywords if k in sent_words)
        scores.append(score)
    return scores


def _compose_summary(base: str, rel_context: list[str]) -> str:
    """Compose the final summary with relationship context."""
    rel_part = " " + " ".join(rel_context or [])
    summary = base
    if rel_part.strip():
        summary += rel_part
    return summary.strip()


def summarize_code_snippet(snippet: str, rel_context: list[str]) -> str:
    """
    Generate a detailed, natural language summary of the code snippet.

    Args:
        snippet: Code or text snippet.
        rel_context: List of relationship context sentences.

    Returns:
        Enriched summary string.
    """
    if not snippet.strip():
        base = "No code or content available."
    else:
        lines = snippet.strip().splitlines()
        docstring = _extract_docstring_or_comment(lines)
        if docstring:
            base = docstring
        else:
            base = _select_informative_sentence(lines)
    return _compose_summary(base, rel_context)
