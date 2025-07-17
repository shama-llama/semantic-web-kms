"""Module for generating class templates for semantic annotation."""

import logging
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from engine.annotation.utils import (
    convert_property_to_snake_case,
    extract_class_name,
    get_gemini_template,
)

logger = logging.getLogger(__name__)

PROMPT_DIR = Path(__file__).parent / "prompts"
jinja_env = Environment(loader=FileSystemLoader(PROMPT_DIR), autoescape=False)


def build_template_prompt(class_name: str, properties_with_stats: list[dict]) -> str:
    """
    Builds a prompt for generating a class description template by rendering an external Jinja2 file.

    Args:
        class_name: The name of the class.
        properties_with_stats: List of property dictionaries with statistics.

    Returns:
        A formatted prompt string for the AI model.
    """
    try:
        template = jinja_env.get_template("class_description_template.j2")
        prompt_context = {
            "class_name": extract_class_name(class_name),
            "properties": [
                {
                    "name": convert_property_to_snake_case(p["uri"]),
                    "frequency": p["frequency"],
                    "cardinality": p["cardinality"],
                }
                for p in properties_with_stats
            ],
        }
        return template.render(prompt_context)
    except Exception as e:
        logger.error(f"Failed to build prompt from template file: {e}")
        raise


def generate_templates_from_class_stats(wdo_classes: list, api_key: str) -> dict:
    """
    Generates AI templates using Gemini based on class statistics.
    This is the single, focused function for this module.
    """
    templates = {}
    logger.info(f"Generating AI templates for {len(wdo_classes)} classes...")
    for i, (class_name, properties_with_stats) in enumerate(wdo_classes, 1):
        logger.info(
            f"Generating template {i}/{len(wdo_classes)} for {extract_class_name(class_name)}..."
        )
        try:
            prompt = build_template_prompt(class_name, properties_with_stats)
            template = get_gemini_template(prompt, api_key)
            templates[class_name] = template
        except Exception as e:
            logger.error(
                f"AI template generation failed for {extract_class_name(class_name)}: {e}"
            )
            raise ValueError(
                f"Failed to generate template for {extract_class_name(class_name)}: {e}"
            ) from e
    logger.info(f"Successfully generated {len(templates)} templates.")
    return templates
