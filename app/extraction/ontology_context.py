from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict

from rdflib import Graph, Namespace

from app.core.ontology_cache import (
    get_code_extraction_classes,
    get_code_extraction_properties,
    get_ontology_cache,
)
from app.core.paths import get_log_path


@dataclass
class OntologyContext:
    g: Graph
    class_cache: dict
    prop_cache: dict
    INST: Namespace
    WDO: Namespace
    uri_safe_string: Callable[[str], str]
    TTL_PATH: Path


def create_ontology_context(
    *,
    g: Graph,
    class_cache: dict,
    prop_cache: dict,
    INST: Namespace,
    WDO: Namespace,
    uri_safe_string: Callable[[str], str],
    TTL_PATH: Path,
) -> OntologyContext:
    """Create and return an OntologyContext object. Rationale: Centralizes context creation."""
    return OntologyContext(
        g=g,
        class_cache=class_cache,
        prop_cache=prop_cache,
        INST=INST,
        WDO=WDO,
        uri_safe_string=uri_safe_string,
        TTL_PATH=TTL_PATH,
    )


def initialize_graph_and_cache(TTL_PATH: Path):
    """Initialize the RDF graph and ontology caches, loading from TTL_PATH if it exists."""
    ontology_cache = get_ontology_cache()
    prop_cache = ontology_cache.get_property_cache(get_code_extraction_properties())
    class_cache = ontology_cache.get_class_cache(get_code_extraction_classes())
    g = Graph()
    if TTL_PATH.exists():
        g.parse(str(TTL_PATH), format="turtle")
    return g, class_cache, prop_cache


def initialize_context_and_graph(
    TTL_PATH: Path,
    INST: Namespace,
    WDO: Namespace,
    uri_safe_string: Callable[[str], str],
):
    """Initialize the graph, caches, and OntologyContext."""
    g, class_cache, prop_cache = initialize_graph_and_cache(TTL_PATH)
    ctx = create_ontology_context(
        g=g,
        class_cache=class_cache,
        prop_cache=prop_cache,
        INST=INST,
        WDO=WDO,
        uri_safe_string=uri_safe_string,
        TTL_PATH=TTL_PATH,
    )
    return g, class_cache, prop_cache, ctx


def get_file_entity_uris(ctx: OntologyContext, constructs, file_uri):
    """Return all entity URIs for a file, including classes, enums, interfaces, structs, traits, modules, and schemas."""
    from app.extraction.entity_writers import (
        write_classes,
        write_database_schemas,
        write_enums,
        write_interfaces,
        write_modules,
        write_structs,
        write_traits,
    )

    class_uris = write_classes(
        ctx.g,
        constructs,
        file_uri,
        ctx.class_cache,
        ctx.prop_cache,
        ctx.uri_safe_string,
    )
    enum_uris = write_enums(
        ctx.g,
        constructs,
        file_uri,
        ctx.class_cache,
        ctx.prop_cache,
        ctx.uri_safe_string,
    )
    interface_uris = write_interfaces(
        ctx.g,
        constructs,
        file_uri,
        ctx.class_cache,
        ctx.prop_cache,
        ctx.uri_safe_string,
    )
    struct_uris = write_structs(
        ctx.g,
        constructs,
        file_uri,
        ctx.class_cache,
        ctx.prop_cache,
        ctx.uri_safe_string,
    )
    trait_uris = write_traits(
        ctx.g,
        constructs,
        file_uri,
        ctx.class_cache,
        ctx.prop_cache,
        ctx.uri_safe_string,
    )
    module_uris = write_modules(
        ctx.g,
        constructs,
        file_uri,
        ctx.class_cache,
        ctx.prop_cache,
        ctx.uri_safe_string,
    )
    schema_uris = write_database_schemas(
        ctx.g,
        constructs,
        file_uri,
        ctx.class_cache,
        ctx.prop_cache,
        ctx.uri_safe_string,
    )
    return (
        {
            **class_uris,
            **enum_uris,
            **interface_uris,
            **struct_uris,
            **trait_uris,
            **module_uris,
            **schema_uris,
        },
        interface_uris,
        module_uris,
    )
