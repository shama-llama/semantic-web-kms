"""Module for postprocessing and enriching semantic annotations."""

import logging
from typing import Dict, List, Optional, Tuple

import numpy as np
import textstat
from nltk.sentiment import SentimentIntensityAnalyzer
from nltk.tokenize import sent_tokenize, word_tokenize
from rdflib import RDF, Graph, URIRef
from rdflib.term import Node

from app.annotation.utils import extract_keywords, find_uri_by_label, get_spacy_nlp

# Global sentiment analyzer for performance optimization
_SIA = None


def get_sentiment_analyzer():
    """Get NLTK sentiment analyzer, loading it only once for performance."""
    global _SIA
    if _SIA is None:
        _SIA = SentimentIntensityAnalyzer()
    return _SIA


logger = logging.getLogger("annotation_postprocessing")


def enrich_description_with_links(
    graph: Graph,
    description: str,
    label_map: Optional[Dict[str, URIRef]] = None,
    nlp=None,
    base_url: str = "https://your-kg.org/entity/",
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

    # Use pre-loaded spaCy model or load if needed
    if nlp is None:
        nlp = get_spacy_nlp()

    # Process text with spaCy
    doc = nlp(description)

    if not doc.ents:
        return description

    logger.info(f"Found {len(doc.ents)} named entities in description")
    logger.debug(f"Named entities: {[ent.text for ent in doc.ents]}")

    enriched = description
    offset = 0
    links_added = 0

    for ent in doc.ents:
        logger.debug(f"Processing entity: {ent.text}")

        # Use fast lookup if label_map is provided, otherwise fall back to slow search
        if label_map is not None:
            uri = label_map.get(ent.text.lower())
            lookup_method = "fast lookup"
        else:
            uri = find_uri_by_label(graph, ent.text)
            lookup_method = "graph search"

        if uri:
            uri_str = str(uri)
            href = f"{base_url}{uri_str.split('#')[-1]}"
            start = enriched.find(ent.text, offset)
            if start != -1:
                end = start + len(ent.text)
                enriched = (
                    enriched[:start]
                    + f"<a href='{href}'>{ent.text}</a>"
                    + enriched[end:]
                )
                offset = end + len(href) + 15
                links_added += 1
                logger.debug(
                    f"Added link for '{ent.text}' -> {href} (using {lookup_method})"
                )
            else:
                logger.debug(
                    f"Could not find '{ent.text}' in enriched text for linking"
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
        text: The text to check.

    Returns:
        True if the description is grammatical, False otherwise.
    """
    logger.debug(
        f"Checking grammaticality of description (length: {len(description)} characters)"
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
        text: The text to score.

    Returns:
        The Flesch reading ease score.
    """
    logger.debug(
        f"Calculating readability score for description (length: {len(description)} characters)"
    )

    score = getattr(textstat, "flesch_reading_ease", lambda x: 50.0)(description)

    logger.debug(f"Readability score: {score:.2f}")

    # Log readability interpretation
    if score >= 90:
        level = "Very Easy"
    elif score >= 80:
        level = "Easy"
    elif score >= 70:
        level = "Fairly Easy"
    elif score >= 60:
        level = "Standard"
    elif score >= 50:
        level = "Fairly Difficult"
    elif score >= 30:
        level = "Difficult"
    else:
        level = "Very Difficult"

    logger.info(f"Readability: {score:.2f} ({level})")
    return score


def get_sentiment(description: str) -> Dict[str, float]:
    """
    Analyze the sentiment of a text and return a sentiment score.

    Args:
        text: The text to analyze.

    Returns:
        Dictionary containing sentiment scores (negative, neutral, positive, compound).
    """
    logger.debug(
        f"Analyzing sentiment of description (length: {len(description)} characters)"
    )

    sia = get_sentiment_analyzer()
    sentiment_scores: Dict[str, float] = sia.polarity_scores(description)

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


def enrich_and_validate_summary(
    graph: Graph,
    instance_uri: Node,
    summary: str,
    label_map: Optional[Dict[str, URIRef]] = None,
) -> Tuple[str, Dict]:
    """
    Enrich and validate a summary for an instance.

    Args:
        graph: The RDF graph containing the instance.
        instance_uri: The URI of the instance.
        summary: The original summary text.
        label_map: Optional pre-computed label to URI mapping.

    Returns:
        Tuple of (enriched_summary, metrics).
    """
    logger.info(f"Starting enrichment and validation for instance {instance_uri}")
    logger.info(f"Original summary length: {len(summary)} characters")
    logger.debug(f"Original summary: {summary}")

    # Step 1: Enrich with entity links
    enriched_summary = enrich_description_with_links(graph, summary, label_map)

    # Step 2: Calculate quality metrics
    grammatical = check_grammaticality(enriched_summary)
    readability = get_readability_score(enriched_summary)
    sentiment = get_sentiment(enriched_summary)

    metrics = {
        "grammatical": grammatical,
        "readability": readability,
        "sentiment": sentiment,
        "original_length": len(summary),
        "enriched_length": len(enriched_summary),
        "links_added": (
            len(enriched_summary) - len(summary)
            if len(enriched_summary) > len(summary)
            else 0
        ),
    }

    logger.info(f"Enrichment and validation complete for instance {instance_uri}")
    logger.info(
        f"Quality metrics: grammatical={grammatical}, readability={readability:.2f}, sentiment_compound={sentiment['compound']:.3f}"
    )
    logger.debug(f"Final enriched summary: {enriched_summary}")

    return enriched_summary, metrics


def extract_relationship_context(
    graph: Graph, entity: URIRef, label_lookup: Dict
) -> List[str]:
    """
    Extract and phrase relationships for an entity in natural language.

    Args:
        graph: RDF graph.
        entity: The instance URI.
        label_lookup: Precomputed {URI: label} dict for fast lookup.

    Returns:
        List of natural language relationship descriptions.
    """
    from app.annotation.semantic_annotator import ANNOTATION_PROPERTIES

    rels: List[str] = []
    for _, p, o in graph.triples((entity, None, None)):
        if p in ANNOTATION_PROPERTIES or p == RDF.type:
            continue
        # Only consider object properties to other instances
        if isinstance(o, URIRef) and o in label_lookup:
            pred_label = label_lookup.get(p, str(p).split("/")[-1])
            obj_label = label_lookup.get(o, str(o).split("/")[-1])
            # Phrase the relationship in context
            rels.append(f"This instance {pred_label.replace('_', ' ')} {obj_label}.")
    return rels


def summarize_code_snippet(snippet: str, rel_context: List[str]) -> str:
    """
    Generate a detailed, natural language summary of the code snippet, enriched with relationship context.

    Args:
        snippet: Code or text snippet.
        rel_context: List of relationship context sentences.

    Returns:
        Enriched summary string.
    """
    if not snippet.strip():
        base = "No code or content available."
    else:
        # Prefer docstring or comment as base
        lines = snippet.strip().splitlines()
        docstring = ""
        for line in lines:
            if line.strip().startswith('"""') or line.strip().startswith("'''"):
                docstring = line.strip().strip("\"'")
                break
            if line.strip().startswith("#"):
                docstring = line.strip().lstrip("#").strip()
                break
        if docstring:
            base = docstring
        else:
            # Use spaCy and NLTK to extract informative sentences
            text = " ".join(lines[:15])
            doc = get_spacy_nlp()(text)
            sents = [sent.text for sent in doc.sents]
            if not sents:
                sents = sent_tokenize(text)
            # Score sentences by keyword overlap
            keywords = extract_keywords(text, top_n=7)
            sent_scores = []
            for sent in sents:
                sent_words = set(word_tokenize(sent.lower()))
                score = sum(1 for k in keywords if k in sent_words)
                sent_scores.append(score)
            if sent_scores:
                idx = int(np.argmax(sent_scores))
                base = sents[idx]
            else:
                base = lines[0][:120] + ("..." if len(lines[0]) > 120 else "")
    # Add relationship context
    rel_part = " " + " ".join(rel_context or [])
    # Compose a 2-3 sentence summary
    summary = base
    if rel_part.strip():
        summary += rel_part
    # Optionally, add more context if available
    return summary.strip()
