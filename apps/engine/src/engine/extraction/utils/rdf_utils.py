"""RDF and graph utility functions for extraction and serialization."""

import os
from typing import Any, Set

from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import RDF, RDFS, XSD

from app.core.namespaces import INST, WDO
from app.core.paths import uri_safe_file_path, uri_safe_string


def add_repository_metadata(
    g: Graph,
    repo_enc: str,
    repo_name: str,
    input_dir: str,
    processed_repos: Set[str],
) -> None:
    """
    Add repository and organization metadata triples to the RDF graph.

    Args:
        g (Graph): The RDF graph to which triples will be added.
        repo_enc (str): URI-safe encoded repository name.
        repo_name (str): Original repository name.
        input_dir (str): Path to the input directory (used to infer organization).
        processed_repos (Set[str]): Set of already processed repository encodings.

    Returns:
        None

    Side Effects:
        Modifies the RDF graph in-place and updates processed_repos.
    """
    repo_uri = INST[repo_enc]
    g.add((repo_uri, RDF.type, WDO.Repository))
    # Use only the clean repository name as rdfs:label
    g.add((repo_uri, RDFS.label, Literal(repo_name, datatype=XSD.string)))
    repo_metadata_uri = INST[f"{repo_enc}_metadata"]
    g.add((repo_metadata_uri, RDF.type, WDO.InformationContentEntity))
    g.add(
        (repo_metadata_uri, WDO.hasSimpleName, Literal(repo_name, datatype=XSD.string))
    )
    g.add(
        (
            repo_metadata_uri,
            RDFS.label,
            Literal(f"metadata: {repo_name}", datatype=XSD.string),
        )
    )
    org_name = os.path.basename(os.path.abspath(input_dir))
    org_uri = INST[uri_safe_string(org_name)]
    g.add((org_uri, RDFS.member, repo_uri))
    g.add((org_uri, RDF.type, WDO.Organization))
    g.add(
        (
            org_uri,
            Namespace("http://www.w3.org/2004/02/skos/core#").prefLabel,
            Literal(org_name, datatype=XSD.string),
        )
    )
    g.add((org_uri, RDFS.label, Literal(org_name, datatype=XSD.string)))
    g.add((org_uri, WDO.hasRepository, repo_uri))
    g.add((repo_uri, WDO.isRepositoryOf, org_uri))
    processed_repos.add(repo_enc)


def add_superclass_triples(
    g: Graph, file_uri: URIRef, wdo_class_uri: str, extractor: Any
) -> None:
    """
    Add RDF triples for the full superclass chain of a file's ontology class.

    Args:
        g (Graph): The RDF graph to which triples will be added.
        file_uri (URIRef): The URI of the file entity.
        wdo_class_uri (str): The URI of the file's ontology class.
        extractor (Any): Extractor object with an ontology supporting get_superclass_chain.

    Returns:
        None

    Side Effects:
        Modifies the RDF graph in-place.
    """
    superclass_chain = [
        str(s) for s in extractor.ontology.get_superclass_chain(wdo_class_uri)
    ]
    for superclass_uri in superclass_chain:
        g.add((file_uri, RDF.type, URIRef(superclass_uri)))


def add_file_metadata_triples(g: Graph, file_uri: URIRef, record: Any) -> None:
    """
    Add metadata triples for a file to the RDF graph.

    Args:
        g (Graph): The RDF graph to which triples will be added.
        file_uri (URIRef): The URI of the file entity.
        record (Any): An object with file metadata attributes (path, size_bytes, etc.).

    Returns:
        None

    Side Effects:
        Modifies the RDF graph in-place.
    """
    g.add((file_uri, WDO.hasRelativePath, Literal(record.path, datatype=XSD.string)))
    g.add(
        (file_uri, WDO.hasSizeInBytes, Literal(record.size_bytes, datatype=XSD.integer))
    )
    g.add((file_uri, WDO.hasExtension, Literal(record.extension, datatype=XSD.string)))
    g.add((file_uri, RDFS.label, Literal(record.filename, datatype=XSD.string)))
    repo_clean = record.repository.replace(" ", "_")
    repo_enc = uri_safe_string(repo_clean)
    repo_url = f"https://github.com/gothinkster/{record.repository}"
    g.add(
        (
            INST[repo_enc],
            WDO.hasSourceRepositoryURL,
            Literal(repo_url, datatype=XSD.anyURI),
        )
    )
    if record.creation_timestamp:
        g.add(
            (
                file_uri,
                WDO.hasCreationTimestamp,
                Literal(record.creation_timestamp, datatype=XSD.dateTime),
            )
        )
    if record.modification_timestamp:
        g.add(
            (
                file_uri,
                WDO.hasModificationTimestamp,
                Literal(record.modification_timestamp, datatype=XSD.dateTime),
            )
        )


def add_file_triples(
    g: Graph,
    record: Any,
    extractor: Any,
    input_dir: str,
    processed_repos: Set[str],
) -> tuple:
    """
    Add RDF triples for a file and its repository relationship.

    Args:
        g (Graph): The RDF graph to which triples will be added.
        record (Any): An object with file metadata and ontology class URI.
        extractor (Any): Extractor object (used for superclass chain, if enabled).
        input_dir (str): Path to the input directory (used to infer organization).
        processed_repos (Set[str]): Set of already processed repository encodings.

    Returns:
        tuple: (file_uri (URIRef), repo_enc (str), path_enc (str))
            file_uri: The URI of the file entity.
            repo_enc: The URI-safe encoded repository name.
            path_enc: The URI-safe encoded file path.

    Side Effects:
        Modifies the RDF graph in-place and updates processed_repos.
    """
    repo_name = record.repository
    repo_clean = repo_name.replace(" ", "_")
    path_clean = record.path.replace(" ", "_")
    repo_enc = uri_safe_string(repo_clean)
    path_enc = uri_safe_file_path(path_clean)
    file_uri = INST[f"{repo_enc}/{path_enc}"]
    wdo_class_uri = record.class_uri
    if repo_enc not in processed_repos:
        add_repository_metadata(g, repo_enc, repo_name, input_dir, processed_repos)
    g.add((file_uri, RDF.type, URIRef(wdo_class_uri)))
    # add_superclass_triples(g, file_uri, wdo_class_uri, extractor)
    add_file_metadata_triples(g, file_uri, record)
    g.add((INST[repo_enc], WDO.hasFile, file_uri))
    g.add((file_uri, WDO.isFileOf, INST[repo_enc]))
    return file_uri, repo_enc, path_enc


def write_ttl_with_progress(
    records: list,
    add_triples_fn,
    graph: Graph,
    ttl_path: str,
    progress,
    ttl_task,
    *args,
    **kwargs,
) -> None:
    """
    Write records to a Turtle file with progress tracking, using a callback to add triples.

    Args:
        records (list): List of record objects to serialize.
        add_triples_fn (Callable): Function to add triples for each record.
        graph (Graph): The RDF graph to which triples will be added.
        ttl_path (str): Path to the output Turtle (.ttl) file.
        progress: Progress bar object supporting advance() and update().
        ttl_task: Task identifier for the progress bar.
        *args: Additional positional arguments for add_triples_fn.
        **kwargs: Additional keyword arguments for add_triples_fn.

    Returns:
        None

    Side Effects:
        Modifies the RDF graph in-place and writes to the output file.
    """
    for record in records:
        add_triples_fn(graph, record, *args, **kwargs)
        progress.advance(ttl_task)
    progress.update(ttl_task, completed=progress.tasks[ttl_task].total)
    graph.serialize(destination=ttl_path, format="turtle")
