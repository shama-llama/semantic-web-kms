"""Semantic annotation utilities for knowledge graph entities and triples."""

import argparse
import logging
import os
from typing import Dict, List, Optional

import nltk  # If NLTK is not installed, install it via pip
from nltk.corpus import stopwords
from rdflib import Graph, URIRef
from rdflib.namespace import RDF, RDFS, SKOS
from rich.console import Console
from rich.panel import Panel

from app.annotation.data_processing import (
    get_all_instances,
    process_single_instance,
)
from app.annotation.generate_class_templates import (
    analyze_class_structure,
    build_template_prompt,
)
from app.annotation.similarity_calculator import enhanced_similarity_calculation
from app.annotation.utils import (
    build_label_to_uri_map,
    create_progress_bar,
    extract_class_name,
    get_gemini_template,
    get_spacy_nlp,
)
from app.core.namespaces import DCTERMS
from app.core.paths import get_log_path, get_output_path, set_input_dir

# Parse input-dir argument and set input dir before any other imports
parser = argparse.ArgumentParser(description="Run the semantic annotation pipeline.")
parser.add_argument(
    "--input-dir",
    type=str,
    default=None,
    help="Root directory to analyze (overrides default in config)",
)
args, unknown = parser.parse_known_args()
if args.input_dir:
    set_input_dir(args.input_dir)

# Setup logging to file only
log_path = get_log_path("annotation_extractor.log")
os.makedirs(os.path.dirname(log_path), exist_ok=True)
LOGFORMAT_FILE = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
logging.basicConfig(
    level=logging.INFO,
    format=LOGFORMAT_FILE,
    datefmt="[%Y-%m-%d %H:%M:%S]",
    handlers=[logging.FileHandler(log_path)],
)
logger = logging.getLogger("annotation_extractor")

TTL_PATH = get_output_path("wdkb.ttl")

# Ensure NLTK resources are downloaded
try:
    nltk.data.find("tokenizers/punkt")
except LookupError:
    nltk.download("punkt")
try:
    nltk.data.find("tokenizers/punkt_tab")
except LookupError:
    nltk.download("punkt_tab")
try:
    nltk.data.find("corpora/stopwords")
except LookupError:
    nltk.download("stopwords")


STOPWORDS = set(stopwords.words("english"))

ANNOTATION_PROPERTIES = {
    RDFS.label,
    RDFS.comment,
    DCTERMS.description,
    DCTERMS.type,
    RDFS.seeAlso,
}


def get_annotation_mode() -> str:
    """Get the current annotation mode based on API key availability."""
    return "AI-powered" if os.getenv("GEMINI_API_KEY") else "fallback"


def load_knowledge_graph() -> Graph:
    """
    Load and parse the knowledge graph from TTL file.

    Returns:
        Loaded RDF graph
    """
    with create_progress_bar() as progress:
        task = progress.add_task("Loading knowledge graph...", total=1)

        g = Graph()
        g.bind("dcterms", DCTERMS)
        g.bind("skos", SKOS)

        if os.path.exists(TTL_PATH):
            g.parse(TTL_PATH, format="turtle")
            logger.info(f"Loaded existing TTL graph from {TTL_PATH}")
            logger.info(f"Graph contains {len(g)} triples")
        else:
            logger.warning(
                f"TTL file not found at {TTL_PATH}, starting with empty graph."
            )

        progress.update(task, completed=1)
        return g


def perform_statistical_analysis(graph: Graph) -> Dict[str, List[Dict[str, str]]]:
    """
    Perform statistical analysis of class structure and properties.

    Args:
        graph: RDF graph to analyze

    Returns:
        Dictionary containing class analysis results
    """
    with create_progress_bar() as progress:
        task = progress.add_task("Analyzing ontology structure...", total=1)
        class_analysis = analyze_class_structure(graph)
        progress.update(task, completed=1)
        return class_analysis


def filter_wdo_classes(class_analysis: Dict[str, List[Dict[str, str]]]) -> List[tuple]:
    """
    Filter class analysis to only include WDO classes.

    Args:
        class_analysis: Dictionary containing class analysis results

    Returns:
        List of (class_name, properties_with_stats) tuples for WDO classes
    """
    wdo_classes = [
        (class_name, properties_with_stats)
        for class_name, properties_with_stats in class_analysis.items()
        if class_name.startswith("http://web-development-ontology.netlify.app/wdo#")
    ]

    logger.info(f"Found {len(wdo_classes)} WDO classes for annotation")
    return wdo_classes


def generate_templates(wdo_classes: List[tuple]) -> Dict[str, str]:
    """
    Generate templates using AI only - no fallbacks.

    Args:
        wdo_classes: List of WDO classes to generate templates for

    Returns:
        Dictionary mapping class URIs to templates
    """
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

    if not GEMINI_API_KEY:
        logger.error(
            "GEMINI_API_KEY not set. Cannot generate templates without AI. Exiting."
        )
        raise ValueError(
            "GEMINI_API_KEY not set. Cannot generate templates without AI."
        )
    else:
        return generate_ai_templates(wdo_classes, GEMINI_API_KEY)


def generate_ai_templates(wdo_classes: List[tuple], api_key: str) -> Dict[str, str]:
    """
    Generate AI templates using Gemini API - no fallbacks.

    Args:
        wdo_classes: List of WDO classes to generate templates for
        api_key: Gemini API key

    Returns:
        Dictionary mapping class URIs to templates
    """
    templates = {}
    logger.info("Generating AI templates using Gemini API")

    with create_progress_bar() as progress:
        task = progress.add_task("Generating AI templates...", total=len(wdo_classes))

        for class_name, properties_with_stats in wdo_classes:
            progress.update(
                task,
                description=f"Generating template for {extract_class_name(class_name)}...",
            )

            try:
                # Try AI generation
                prompt = build_template_prompt(
                    class_name,
                    [],
                    include_statistics=True,
                    properties_with_stats=properties_with_stats,
                )
                template = get_gemini_template(prompt, api_key)
                templates[class_name] = template
                logger.info(
                    f"Generated AI template for class: {extract_class_name(class_name)}"
                )
            except Exception as e:
                logger.error(
                    f"AI template generation failed for {extract_class_name(class_name)}: {e}"
                )
                # Don't use fallbacks - fail gracefully
                raise ValueError(
                    f"Failed to generate template for {extract_class_name(class_name)}: {e}"
                )

            progress.advance(task)

    return templates


def prepare_label_lookup(graph: Graph) -> Dict[str, URIRef]:
    """
    Prepare label lookup map for performance optimization.

    Args:
        graph: RDF graph to process

    Returns:
        Dictionary mapping lowercase labels to URIs
    """
    with create_progress_bar() as progress:
        task = progress.add_task("Building label lookup map...", total=1)
        label_to_uri_map = build_label_to_uri_map(graph)
        progress.update(task, completed=1)
        return label_to_uri_map


def annotate_instances(
    graph: Graph, templates: Dict, label_to_uri_map: Dict[str, URIRef]
) -> int:
    """
    Annotate instances with summaries using templates with optimized batch processing.

    Args:
        graph: RDF graph to annotate
        templates: Dictionary mapping class URIs to templates
        label_to_uri_map: Pre-computed label lookup map

    Returns:
        Number of instances annotated
    """
    # Get all instances that need annotation
    all_instances = get_all_instances(graph, templates)
    total_instances = len(all_instances)

    annotation_mode = get_annotation_mode()
    logger.info(
        f"Starting {annotation_mode} annotation of {total_instances} instances across {len(templates)} classes with optimized processing"
    )

    # Pre-load spaCy model once for batch processing
    nlp = get_spacy_nlp()
    logger.info("Pre-loaded spaCy model for batch processing")

    # Get progress tracker for frontend reporting
    from app.core.progress_tracker import get_current_tracker

    tracker = get_current_tracker()

    with create_progress_bar() as progress:
        task = progress.add_task(
            "Annotating instances with summaries...", total=total_instances
        )

        successful_annotations = 0
        batch_size = 100  # Increased batch size for better performance

        for batch_start in range(0, total_instances, batch_size):
            batch_end = min(batch_start + batch_size, total_instances)
            batch_instances = all_instances[batch_start:batch_end]

            logger.info(
                f"Processing batch {batch_start//batch_size + 1}: instances {batch_start+1}-{batch_end}"
            )

            # Process batch with optimized operations
            for idx, (instance, template, class_name) in enumerate(
                batch_instances, batch_start + 1
            ):
                progress.update(
                    task,
                    description=f"Annotating {class_name} instance {idx}...",
                )

                if process_single_instance(
                    graph,
                    instance,
                    template,
                    label_to_uri_map,
                    class_name,
                    nlp,
                    optimized=True,
                ):
                    successful_annotations += 1

                progress.advance(task)

                # Update frontend progress tracker every 50 instances or at completion
                if tracker and (idx % 50 == 0 or idx == total_instances):
                    progress_percentage = 50 + int(
                        (idx / total_instances) * 40
                    )  # 50-90% range for annotation
                    tracker.update_stage(
                        "semanticAnnotation",
                        "processing",
                        progress_percentage,
                        f"Annotating instances: {idx}/{total_instances} ({successful_annotations} successful)",
                    )

        return successful_annotations


def save_results(graph: Graph) -> None:
    """
    Save the enriched knowledge graph to file.

    Args:
        graph: RDF graph to save
    """
    with create_progress_bar() as progress:
        task = progress.add_task("Saving enriched knowledge graph...", total=1)
        graph.serialize(destination=TTL_PATH, format="turtle")
        progress.update(task, completed=1)


def display_completion_summary(
    class_analysis: Dict, templates: Dict, num_annotated: int
) -> None:
    """
    Display completion summary and statistics.

    Args:
        class_analysis: Dictionary containing class analysis results
        templates: Dictionary mapping class URIs to templates
        num_annotated: Number of instances annotated
    """
    from rich.rule import Rule
    from rich.table import Table

    annotation_mode = get_annotation_mode()
    template_type = "AI templates" if os.getenv("GEMINI_API_KEY") else "no templates"

    logger.info("=" * 80)
    logger.info("ANNOTATION PROCESS COMPLETE")
    logger.info(f"Mode: {annotation_mode}")
    logger.info(f"Analyzed {len(class_analysis)} classes")
    logger.info(f"Generated {len(templates)} {template_type}")
    logger.info(f"Successfully annotated {num_annotated} instances")
    logger.info(f"Saved to: {TTL_PATH}")
    logger.info("=" * 80)

    console = Console()

    # Load the knowledge graph ONCE for summary counting

    g = load_knowledge_graph()

    # Build a table of classes and number of instances annotated
    table = Table(title="Annotation Pipeline Summary")
    table.add_column("Class", style="cyan", no_wrap=True)
    table.add_column("Instances Annotated", style="bold")

    for class_uri, properties in class_analysis.items():
        class_name = extract_class_name(class_uri)
        count = len(list(g.triples((None, RDF.type, URIRef(class_uri)))))
        table.add_row(class_name, str(count))

    console.print()
    console.print(Rule(style="dim"))
    console.print(table)
    console.print(
        f"\n[bold green]Successfully annotated {num_annotated} instances[/bold green]"
    )


# --- Main annotation logic using statistical templates ---
def main(input_dir: Optional[str] = None) -> None:
    """Run the semantic annotation process."""
    console = Console()
    console.print(
        Panel(
            "[bold blue]Semantic Web Knowledge Management System[/bold blue]\n"
            "Semantic Annotation Pipeline Orchestrator",
            title="🚀 Starting Annotation Pipeline",
            border_style="blue",
        )
    )
    logger.info("Starting annotation pipeline orchestration")
    logger.info("=" * 80)
    logger.info("STARTING STATISTICAL ANNOTATION/ENRICHMENT PROCESS")
    logger.info("=" * 80)

    # Get progress tracker for frontend reporting
    from app.core.progress_tracker import get_current_tracker

    tracker = get_current_tracker()

    # Step 1: Load and parse graph
    if tracker:
        tracker.update_stage(
            "semanticAnnotation", "processing", 10, "Loading knowledge graph..."
        )
    graph = load_knowledge_graph()

    # Step 2: Statistical analysis
    if tracker:
        tracker.update_stage(
            "semanticAnnotation", "processing", 20, "Performing statistical analysis..."
        )
    class_analysis = perform_statistical_analysis(graph)

    # Step 3: Template generation
    if tracker:
        tracker.update_stage(
            "semanticAnnotation", "processing", 30, "Generating annotation templates..."
        )
    wdo_classes = filter_wdo_classes(class_analysis)
    templates = generate_templates(wdo_classes)

    # Step 4: Pre-compute label lookup for performance
    if tracker:
        tracker.update_stage(
            "semanticAnnotation", "processing", 40, "Preparing label lookup map..."
        )
    label_to_uri_map = prepare_label_lookup(graph)

    # Step 5: Instance annotation
    if tracker:
        tracker.update_stage(
            "semanticAnnotation", "processing", 50, "Starting instance annotation..."
        )
    num_annotated = annotate_instances(graph, templates, label_to_uri_map)

    # Step 6: Add similarity relationships
    if tracker:
        tracker.update_stage(
            "semanticAnnotation",
            "processing",
            80,
            "Calculating instance similarities...",
        )
    logger.info("Adding similarity relationships between instances")
    try:
        relationships_added = enhanced_similarity_calculation(
            graph, use_centrality=True, max_instances=1000
        )
        logger.info(
            f"Successfully added {relationships_added} similarity relationships"
        )
    except Exception as e:
        logger.error(f"Failed to add similarity relationships: {e}")
        relationships_added = 0

    # Step 7: Save results
    if tracker:
        tracker.update_stage(
            "semanticAnnotation", "processing", 90, "Saving enriched knowledge graph..."
        )
    save_results(graph)

    # Step 7: Display completion summary
    if tracker:
        tracker.update_stage(
            "semanticAnnotation",
            "completed",
            100,
            "Semantic annotation completed successfully",
        )
    display_completion_summary(class_analysis, templates, num_annotated)


if __name__ == "__main__":
    # Use the already parsed args from the top of the file
    main(args.input_dir)
