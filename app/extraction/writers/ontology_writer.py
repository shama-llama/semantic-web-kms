"""Writers for encoding code construct entities and relationships as RDF triples in the ontology graph."""

import logging
from pathlib import Path

from rdflib import Literal, URIRef
from rdflib.namespace import RDF, RDFS, XSD

from app.extraction.ontology.ontology_context import (
    OntologyContext,
    create_ontology_context,
    get_file_entity_uris,
)
from app.extraction.ontology.ontology_utils import _is_complex_type
from app.extraction.writers.entity_writers import (
    create_canonical_type_individuals,
    write_calls,
    write_comments,
    write_decorators,
    write_functions,
    write_imports,
    write_parameters,
    write_repo_file_link,
    write_types,
    write_variables,
)
from app.extraction.writers.relationship_writers import (
    write_access_relationships,
    write_declaration_usage_relationships,
    write_embedding_relationships,
    write_implements_interface,
    write_inheritance,
    write_manipulation_relationships,
    write_module_import_relationships,
    write_styling_relationships,
    write_testing_relationships,
    write_type_relationships,
)


def process_file_for_ontology(
    *,
    ctx: OntologyContext,
    rec: dict[str, str],
    summary_data: dict[str, dict],
    global_type_uris: dict[str, str],
    language_mapping: dict[str, str],
) -> None:
    """
    Process a single file's constructs and write entities and relationships to the ontology graph.

    Args:
        ctx: OntologyContext object containing graph, caches, and URI helpers.
        rec: File record with at least 'repository' and 'path' keys.
        summary_data: Mapping of file keys to construct summaries.
        global_type_uris: Mapping of global type names to their URIs.
        language_mapping: Mapping of file extensions to language names.
    Returns:
        None. Writes entities and relationships to the ontology graph in ctx.
    """
    repo = rec["repository"]
    rel_path = rec["path"]
    file_enc = ctx.uri_safe_string(rel_path)
    repo_enc = ctx.uri_safe_string(repo)
    file_uri = ctx.INST[f"{repo_enc}/{file_enc}"]
    summary_key = f"{repo}/{rel_path}"
    constructs = summary_data.get(summary_key, {})
    ext = Path(rel_path).suffix.lower()
    language = language_mapping[ext] if ext in language_mapping else None
    all_entity_uris, interface_uris, module_uris = get_file_entity_uris(
        ctx, constructs, file_uri
    )
    func_uris = write_all_entities_for_file(
        ctx,
        constructs,
        file_uri,
        all_entity_uris,
        interface_uris,
        module_uris,
        global_type_uris,
        language,
    )
    write_all_relationships(
        ctx,
        constructs,
        file_uri,
        all_entity_uris,
        interface_uris,
        module_uris,
        func_uris,
        global_type_uris,
    )


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

    Args:
        g: RDFLib Graph to add triples to.
        constructs: Dict of extracted code constructs.
        file_uri: URIRef for the file.
        class_cache: Dict of ontology class URIs.
        prop_cache: Dict of ontology property URIs.
        uri_safe_string: Function to make URI-safe strings.
        class_uris: Dict mapping class names to their URIs.
        type_uris: Dict mapping type names to their URIs.
    Returns:
        None
    """
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
            if _is_complex_type(cls_name):
                g.add((cls_uri, prop_cache["hasField"], field_uri))


def write_all_entities_for_file(
    ctx: OntologyContext,
    constructs,
    file_uri,
    all_entity_uris,
    interface_uris,
    module_uris,
    global_type_uris,
    language,
):
    """
    Write all entity types for a single file.

    Args:
        ctx: OntologyContext object.
        constructs: Dict of extracted code constructs.
        file_uri: URIRef for the file.
        all_entity_uris: Dict of all entity URIs for the file.
        interface_uris: Dict of interface URIs for the file.
        module_uris: Dict of module URIs for the file.
        global_type_uris: Dict mapping type names to URIs.
        language: Programming language string.
    Returns:
        Dict mapping function names to their URIs.
    """
    func_uris = write_functions(
        ctx.g,
        constructs,
        file_uri,
        ctx.class_cache,
        ctx.prop_cache,
        ctx.uri_safe_string,
        all_entity_uris,
        global_type_uris,
        language,
    )
    write_parameters(
        ctx.g,
        constructs,
        file_uri,
        ctx.class_cache,
        ctx.prop_cache,
        ctx.uri_safe_string,
        func_uris,
        global_type_uris,
    )
    write_variables(
        ctx.g,
        constructs,
        file_uri,
        ctx.class_cache,
        ctx.prop_cache,
        ctx.uri_safe_string,
        func_uris,
        global_type_uris,
    )
    write_calls(
        ctx.g,
        constructs,
        file_uri,
        ctx.class_cache,
        ctx.prop_cache,
        ctx.uri_safe_string,
        func_uris,
        global_type_uris,
    )
    write_decorators(
        ctx.g,
        constructs,
        file_uri,
        ctx.class_cache,
        ctx.prop_cache,
        ctx.uri_safe_string,
    )
    write_types(
        ctx.g,
        constructs,
        file_uri,
        ctx.class_cache,
        ctx.prop_cache,
        ctx.uri_safe_string,
    )
    write_imports(
        ctx.g,
        constructs,
        file_uri,
        ctx.class_cache,
        ctx.prop_cache,
        ctx.uri_safe_string,
    )
    write_module_import_relationships(
        ctx.g, constructs, file_uri, ctx.prop_cache, ctx.uri_safe_string, module_uris
    )
    write_comments(
        ctx.g,
        constructs,
        file_uri,
        ctx.class_cache,
        ctx.prop_cache,
        ctx.uri_safe_string,
    )
    return func_uris


def write_all_relationships(
    ctx: OntologyContext,
    constructs,
    file_uri,
    all_entity_uris,
    interface_uris,
    module_uris,
    func_uris,
    global_type_uris,
):
    """
    Write all relationship types for a single file.

    Args:
        ctx: OntologyContext object.
        constructs: Dict of extracted code constructs.
        file_uri: URIRef for the file.
        all_entity_uris: Dict of all entity URIs for the file.
        interface_uris: Dict of interface URIs for the file.
        module_uris: Dict of module URIs for the file.
        func_uris: Dict mapping function names to their URIs.
        global_type_uris: Dict mapping type names to URIs.
    Returns:
        None
    """
    write_inheritance(ctx.g, constructs, all_entity_uris, ctx.prop_cache)
    write_implements_interface(
        ctx.g, constructs, all_entity_uris, interface_uris, ctx.prop_cache
    )
    write_fields(
        ctx.g,
        constructs,
        file_uri,
        ctx.class_cache,
        ctx.prop_cache,
        ctx.uri_safe_string,
        all_entity_uris,
        global_type_uris,
    )
    write_declaration_usage_relationships(
        ctx.g, constructs, file_uri, ctx.prop_cache, ctx.uri_safe_string
    )
    write_access_relationships(
        ctx.g, constructs, file_uri, ctx.prop_cache, ctx.uri_safe_string
    )
    write_type_relationships(
        ctx.g, constructs, file_uri, ctx.prop_cache, ctx.uri_safe_string
    )
    write_embedding_relationships(
        ctx.g, constructs, file_uri, ctx.prop_cache, ctx.uri_safe_string
    )
    write_manipulation_relationships(
        ctx.g, constructs, file_uri, ctx.prop_cache, ctx.uri_safe_string
    )
    write_styling_relationships(
        ctx.g, constructs, file_uri, ctx.prop_cache, ctx.uri_safe_string
    )
    write_testing_relationships(
        ctx.g, constructs, file_uri, ctx.prop_cache, ctx.uri_safe_string
    )
    write_repo_file_link(ctx.g, file_uri.split("/")[0], ctx.WDO, ctx.INST, file_uri)


def write_ontology(
    g,
    supported_files,
    summary_data,
    TTL_PATH,
    class_cache,
    prop_cache,
    INST,
    WDO,
    uri_safe_string,
    language_mapping,
):
    """
    Write ontology triples for all supported files.

    Args:
        g: RDFLib Graph to add triples to.
        supported_files: List of file records.
        summary_data: Dict mapping file keys to construct summaries.
        TTL_PATH: Path to the TTL output file.
        class_cache: Dict of ontology class URIs.
        prop_cache: Dict of ontology property URIs.
        INST: Instance namespace.
        WDO: WDO namespace.
        uri_safe_string: Function to make URI-safe strings.
        language_mapping: Dict mapping file extensions to language names.
    Returns:
        None
    """
    ctx = create_ontology_context(
        g=g,
        class_cache=class_cache,
        prop_cache=prop_cache,
        INST=INST,
        WDO=WDO,
        uri_safe_string=uri_safe_string,
        TTL_PATH=TTL_PATH,
    )
    global_type_uris = create_canonical_type_individuals(
        g, class_cache, prop_cache, uri_safe_string
    )
    for rec in supported_files:
        process_file_for_ontology(
            ctx=ctx,
            rec=rec,
            summary_data=summary_data,
            global_type_uris=global_type_uris,
            language_mapping=language_mapping,
        )


def finalize_and_serialize_graph(ctx: OntologyContext):
    """
    Serialize the ontology graph to TTL format.

    Args:
        ctx: OntologyContext object containing the graph and TTL path.
    Returns:
        None
    """
    ctx.g.serialize(destination=str(ctx.TTL_PATH), format="turtle")
