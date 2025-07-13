"""Module for generating class templates for semantic annotation."""

import json
import os
from collections import Counter
from typing import Any, Dict, List

from rdflib import RDF, Graph, URIRef

from app.annotation.utils import extract_class_name, get_gemini_template


def get_classes_and_properties(graph) -> dict:
    """Extract classes and their properties from an RDF graph.

    Args:
        graph: The RDF graph to extract from.

    Returns:
        Dictionary mapping class URIs to their property URIs.
    """
    class_to_properties: dict = {}
    for s, _, o in graph.triples((None, RDF.type, None)):
        class_uri = o
        if class_uri not in class_to_properties:
            class_to_properties[class_uri] = set()
        for p, _ in graph.predicate_objects(s):
            class_to_properties[class_uri].add(p)
    # Convert sets to sorted lists for consistency
    return {
        str(cls): sorted([str(p) for p in props])
        for cls, props in class_to_properties.items()
    }


def build_template_prompt(
    class_name, properties, include_statistics=False, properties_with_stats=None
):
    """Build a prompt for generating class templates.

    Args:
        class_name: The name of the class to generate a template for.
        properties: List of property URIs for the class.
        include_statistics: Whether to include statistical information in the prompt.
        properties_with_stats: List of property dictionaries with statistics.

    Returns:
        A formatted prompt string for template generation.
    """
    if include_statistics and properties_with_stats:
        # Use statistical prompt format
        def to_snake_case(uri):
            return uri.split("/")[-1].split("#")[-1].replace("-", "_")

        prop_lines = []
        for prop_info in properties_with_stats:
            prop_name = to_snake_case(prop_info["uri"])
            prop_lines.append(
                f"- `{prop_name}`: (Used in {prop_info['frequency']} of instances; cardinality: {prop_info['cardinality']})"
            )
        prop_str = "\n".join(prop_lines)

        prompt = f"""
You are a Semantic Architect and Knowledge Curator. Your task is to create a concise, specific, and informative description TEMPLATE for instances of a specific RDF class.

I will provide you with the class and its common properties (predicates), along with statistics about their frequency and cardinality. You must create a well-written, natural paragraph that explains what this entity is and its specific role in the codebase.

**CRITICAL INSTRUCTIONS:**
- The output MUST be a single JSON object.
- The JSON object must contain one key: "template".
- The value of "template" must be a string.
- Use curly braces `{{}}` to denote placeholders for property values (e.g., `{{label}}`).
- IMPORTANT: Use the exact property names I provide below (without the `wdo:` prefix).
- Write in natural, flowing language that reads like a proper description.
- Use the frequency and cardinality statistics to prioritize the most important properties.
- Create a narrative that explains what this entity is and what it does, incorporating the properties naturally.
- Make the description informative and engaging, as if explaining to someone what this entity represents.
- Structure the description to read naturally even if some placeholders are empty.
- Vary the sentence structure and use different ways to introduce and connect information.
- Use natural transitions and connectors to make the text flow smoothly.
- AVOID repetitive phrases like "fundamental component", "intrinsically linked", "plays a crucial role".
- Focus on the specific purpose and context of the entity within the codebase.
- Provide meaningful insights about the entity's role and relationships.
- **CRITICAL: NEVER include source code snippets in editorial notes. Focus on describing purpose, structure, and relationships instead.**

**Class:** `{extract_class_name(class_name)}`

**Common Properties & Statistics:**
{prop_str}

**Example template formats (vary the style and be specific):**
- "This {extract_class_name(class_name)} represents {{label}} and serves {{specific_purpose}}. It is part of {{isCodePartOf}} and contributes to {{specific_function}}."
- "A {extract_class_name(class_name)} instance identified as {{label}}, this entity {{specific_action}} and belongs to {{isCodePartOf}}. Its role within the system is to {{specific_role}}."
- "The {extract_class_name(class_name)} known as {{label}} {{specific_action}} within the codebase, being integrated into {{isCodePartOf}}. This component {{specific_benefit}}."

**Output JSON:**
"""
    else:
        # Use standard prompt format
        prop_lines = []
        for prop in properties:
            prop_lines.append(f"- `{prop}`: [description]")
        prop_str = "\n".join(prop_lines)
        prompt = f"""
You are a Semantic Architect and Knowledge Curator. Your purpose is to transmute raw semantic triples into definitive, encyclopedic summaries. The output must be so clear, well-structured, and informative that it serves as the canonical `dcterms:description` for an instance.

Your task is to create a single, generic, natural-language summary TEMPLATE for a given RDF class. This template, when populated, will produce a rich, cohesive, and human-readable paragraph.

---
### The Philosophy: Guiding Principles for a Definitive Description

1.  **Semantic Synthesis (Most Important):** Do not merely list properties. You must infer and state the *relationships between them*. The goal is narrative, not inventory.
    *   **Bad:** "Has author X. Has topic Y."
    *   **Good:** "Authored by X, this work explores the topic of Y."
    *   **Bad:** "Is a TestCode. Tests function Z."
    *   **Good:** "A suite of tests designed to validate the function Z."

2.  **Informational Hierarchy:** The summary must flow from most to least critical information.
    *   **Primary:** Start with what the thing *is* and what it *does* (its label, its purpose, its primary role).
    *   **Secondary:** Add important relational context (what it's part of, what it interacts with).
    *   **Tertiary:** Conclude with supplementary metadata (line counts, timestamps, identifiers) only if they add significant value.

3.  **Domain-Aware Terminology:** Use language that reflects the entity's domain.
    *   A `wdo:Dockerfile` is a "blueprint" or "specification for a container environment."
    *   A `wdo:Commit` represents a "snapshot of changes" or a "revision."
    *   A `wdo:Readme` is the "primary point of entry for understanding a project."

---
### The Mechanics: Technical Specification for a Flawless Template

1.  **JSON Output:** The output MUST be a single, valid JSON object containing one key: `"template"`.
2.  **Jinja2 Engine Syntax:** You MUST use Jinja2 syntax exclusively. The placeholder names will be provided in `snake_case`.
3.  **Handling Optional Data (`if` blocks):** To ensure grammatical integrity, every optional property MUST be wrapped in a conditional block. Punctuation and connecting words (e.g., "and", "located at", ",") MUST be *inside* the block.
4.  **Handling Lists of Data (`for` loops):** For properties that can have multiple values, you MUST use a Jinja2 `for` loop to render them as a natural language list.
    *   This correctly handles commas and avoids a trailing comma.

---
### The Gold-Standard Example: A Demonstration of Excellence

**Input Class:** `wdo_FunctionDefinition`
**Input Properties:**
- `rdfs_label` (string)
- `dcterms_description` (string)
- `wdo_isCodePartOf` (string)
- `wdo_hasProgrammingLanguage` (string)
- `wdo_tests` (list of strings)
- `wdo_hasCyclomaticComplexity` (integer)

**PERFECT Output JSON:**
```json
{{
  "template": "The function '{{{{ rdfs_label }}}}' is a discrete unit of code designed to {{{{ dcterms_description }}}}.{{% if wdo_isCodePartOf %}} As a component of the '{{{{ wdo_isCodePartOf }}}}' module{{% endif %}}{{% if wdo_hasProgrammingLanguage %}}, it is implemented in the {{{{ wdo_hasProgrammingLanguage }}}} language{{% endif %}}.{{% if wdo_tests %}} It is validated by a suite of tests, including {{% for test in wdo_tests %}}'{{{{ test }}}}'{{% if not loop.last %}}, {{% endif %}}{{% endfor %}}{{% endif %}}.{{% if wdo_hasCyclomaticComplexity %}} It has a calculated cyclomatic complexity of {{{{ wdo_hasCyclomaticComplexity }}}}, indicating its logical intricacy.{{% endif %}}"
}}
```

---
**Input Class:** `{class_name}`

**Input Properties:**
{prop_str}

**Output JSON:**
"""
    return prompt


def analyze_class_structure(graph) -> Dict[str, List[Dict[str, str]]]:
    """
    Analyze the graph to find classes and computes statistics about their properties.

    Args:
        graph: An RDFLib Graph containing the ontology data.

    Returns:
        Dict mapping each class URI to a list of property statistics, where each property
        statistic is a dict with keys: 'uri', 'frequency', and 'cardinality'.
    """
    import logging

    logger = logging.getLogger("annotation_generate_templates")

    logger.info("Starting class structure analysis...")
    class_instances: Dict = {}
    # First, gather all instances for each class
    for s, _, o in graph.triples((None, RDF.type, None)):
        if o not in class_instances:
            class_instances[o] = []
        class_instances[o].append(s)

    logger.info(f"Found {len(class_instances)} classes with instances")

    class_analysis: Dict[str, List[Dict[str, str]]] = {}
    for class_uri, instances in class_instances.items():
        num_instances = len(instances)
        if num_instances == 0:
            continue

        logger.info(f"Analyzing class {class_uri} with {num_instances} instances")

        prop_counter: Counter = Counter()
        prop_cardinality = {}  # Track occurrences per instance

        for instance_uri in instances:
            # Get unique properties for this instance to count frequency correctly
            instance_props = {p for p, _ in graph.predicate_objects(instance_uri)}
            prop_counter.update(instance_props)

            # Check for multi-valued properties
            instance_prop_counts = Counter(
                p for p, _ in graph.predicate_objects(instance_uri)
            )
            for prop, count in instance_prop_counts.items():
                if prop not in prop_cardinality:
                    prop_cardinality[prop] = "single"
                if count > 1:
                    prop_cardinality[prop] = (
                        "multiple"  # If it's ever multi, treat as multi
                    )

        # Format the final analysis for the prompt
        properties_with_stats: List[Dict[str, str]] = []
        for prop, count in prop_counter.most_common():
            frequency = (count / num_instances) * 100
            cardinality = prop_cardinality.get(prop, "single")
            properties_with_stats.append(
                {
                    "uri": str(prop),
                    "frequency": f"{frequency:.0f}%",
                    "cardinality": cardinality,
                }
            )

        class_analysis[str(class_uri)] = properties_with_stats
        logger.info(
            f"Class {class_uri}: {len(properties_with_stats)} properties analyzed"
        )

    logger.info(
        f"Class structure analysis complete. Analyzed {len(class_analysis)} classes"
    )
    return class_analysis


def analyze_property_context(
    graph: Graph, instance: URIRef, properties: Dict[str, Any]
) -> Dict[str, str]:
    """
    Analyze properties to provide context-aware information for template generation.

    Args:
        graph: RDF graph containing the instance
        instance: Instance URI to analyze
        properties: Dictionary of instance properties

    Returns:
        Dictionary with contextual information for template generation
    """
    context = {}

    # Analyze code snippets for specific patterns
    if "hasSourceCodeSnippet" in properties:
        code_snippet = properties["hasSourceCodeSnippet"]
        if code_snippet.startswith("import ") or code_snippet.startswith("from "):
            context["specific_purpose"] = (
                "enable access to external libraries and modules"
            )
            context["specific_function"] = "imports external dependencies"
            context["specific_action"] = "imports external functionality"
            context["specific_benefit"] = "provides access to additional capabilities"
        elif code_snippet.startswith("def ") or code_snippet.startswith("function "):
            context["specific_purpose"] = "encapsulate reusable logic and operations"
            context["specific_function"] = "implements a specific operation"
            context["specific_action"] = "performs computational tasks"
            context["specific_benefit"] = "enables code reuse and modularity"
        elif code_snippet.startswith("class ") or "class" in code_snippet:
            context["specific_purpose"] = "define object blueprints and data structures"
            context["specific_function"] = "defines a class structure"
            context["specific_action"] = "organizes related data and methods"
            context["specific_benefit"] = "provides object-oriented structure"
        elif code_snippet.startswith("//") or code_snippet.startswith("#"):
            context["specific_purpose"] = "document code behavior and purpose"
            context["specific_function"] = "provides code documentation"
            context["specific_action"] = "explains implementation details"
            context["specific_benefit"] = "improves code readability and maintenance"
        else:
            context["specific_purpose"] = "contribute to system functionality"
            context["specific_function"] = "serves a specific role"
            context["specific_action"] = "performs its designated function"
            context["specific_benefit"] = "supports overall system operation"

    # Analyze relationships for context
    if "isCodePartOf" in properties:
        parent_context = properties["isCodePartOf"]
        if "function" in str(parent_context):
            context["specific_role"] = "function implementation"
        elif "class" in str(parent_context):
            context["specific_role"] = "class definition"
        elif "file" in str(parent_context):
            context["specific_role"] = "file organization"
        else:
            context["specific_role"] = "system component"

    # Analyze labels for specific context
    if "label" in properties:
        label = properties["label"]
        if "import" in label.lower():
            context["specific_purpose"] = (
                "enable access to external libraries and modules"
            )
        elif "var" in label.lower() or "variable" in label.lower():
            context["specific_purpose"] = "store and manage data values"
        elif "func" in label.lower() or "function" in label.lower():
            context["specific_purpose"] = "encapsulate reusable logic and operations"
        elif "class" in label.lower():
            context["specific_purpose"] = "define object blueprints and data structures"
        elif "comment" in label.lower():
            context["specific_purpose"] = "document code behavior and purpose"

    return context


def generate_ai_templates(wdo_classes: list, api_key: str) -> dict:
    """
    Generate AI templates using Gemini API with parallelization.

    Args:
        wdo_classes: List of (class_name, properties_with_stats) tuples
        api_key: Gemini API key

    Returns:
        Dictionary mapping class URIs to templates
    """
    import logging

    logger = logging.getLogger("annotation_generate_templates")
    templates = {}

    logger.info("Generating AI templates using Gemini API")
    logger.info(f"Processing {len(wdo_classes)} classes...")

    for i, (class_name, properties_with_stats) in enumerate(wdo_classes, 1):
        logger.info(
            f"Generating template {i}/{len(wdo_classes)} for {extract_class_name(class_name)}..."
        )

        try:
            # Try AI generation - get_gemini_template already handles rate limiting
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

    logger.info(f"Successfully generated {len(templates)} templates")
    return templates


if __name__ == "__main__":
    g = Graph()
    g.parse("output/wdkb.ttl", format="turtle")
    class_props = get_classes_and_properties(g)
    with open("output/class_properties.json", "w", encoding="utf-8") as f:
        json.dump(class_props, f, indent=2, ensure_ascii=False)
    print(
        f"Extracted {len(class_props)} classes and their properties. Saved to output/class_properties.json."
    )
    # After saving class_properties.json, generate templates
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    if not GEMINI_API_KEY:
        print("GEMINI_API_KEY not set. Skipping template generation.")
        exit(0)
    with open("output/class_properties.json", encoding="utf-8") as f:
        class_props = json.load(f)
    templates = {}
    for class_name, properties in class_props.items():
        # Only process WDO namespace classes
        if not class_name.startswith(
            "http://www.semanticweb.org/ontologies/2024/1/wdo#"
        ):
            print(f"Skipping non-WDO class: {class_name}")
            continue
        print(f"Generating template for {class_name}...")
        prompt = build_template_prompt(class_name, properties)
        try:
            template = get_gemini_template(prompt, GEMINI_API_KEY)
            templates[class_name] = template
        except Exception as e:
            print(f"Failed to generate template for {class_name}: {e}")
    with open("output/class_templates.json", "w", encoding="utf-8") as f:
        json.dump(templates, f, indent=2, ensure_ascii=False)
    print(f"Saved {len(templates)} templates to output/class_templates.json.")
