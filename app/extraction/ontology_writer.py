"""
Ontology triple-writing helpers for code entity extraction.
"""

from typing import Any, Callable, Dict

from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import RDF, RDFS, XSD


def write_fields(
    g,
    constructs,
    file_uri,
    class_cache,
    prop_cache,
    uri_safe_string,
    class_uris,
    type_uris,
):
    """
    Write field (attribute) entities to the ontology.
    """
    import logging

    logger = logging.getLogger("code_extractor")
    fields = constructs.get("fields", []) + constructs.get("AttributeDeclaration", [])
    for field in fields:
        field_id = field.get("name")
        if not field_id:
            continue
        field_uri = URIRef(f"{file_uri}/field/{uri_safe_string(field_id)}")
        g.add((field_uri, RDF.type, class_cache["AttributeDeclaration"]))
        g.add((field_uri, RDFS.label, Literal(field_id, datatype=XSD.string)))
        g.add(
            (
                field_uri,
                prop_cache["hasSimpleName"],
                Literal(field_id, datatype=XSD.string),
            )
        )
        if "raw" in field and field["raw"]:
            g.add(
                (
                    field_uri,
                    prop_cache["hasSourceCodeSnippet"],
                    Literal(field["raw"], datatype=XSD.string),
                )
            )
        if "type" in field:
            field_type = field["type"].strip().lower()
            if field_type in type_uris:
                g.add((field_uri, prop_cache["hasType"], type_uris[field_type]))
            else:
                logger.warning(
                    f"Field '{field_id}' has unknown type '{field_type}', skipping type triple."
                )
        if "start_line" in field:
            g.add(
                (
                    field_uri,
                    prop_cache["startsAtLine"],
                    Literal(field["start_line"], datatype=XSD.integer),
                )
            )
        if "end_line" in field:
            g.add(
                (
                    field_uri,
                    prop_cache["endsAtLine"],
                    Literal(field["end_line"], datatype=XSD.integer),
                )
            )
        for cls_name, cls_uri in class_uris.items():
            from .code_extractor import _is_complex_type

            if _is_complex_type(cls_name):
                g.add((cls_uri, prop_cache["hasField"], field_uri))


# ... (repeat for all other write_* functions, with concise docstrings) ...
