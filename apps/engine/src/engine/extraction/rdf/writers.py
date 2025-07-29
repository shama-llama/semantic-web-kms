"""Defines writer functions for serializing models to RDF triples using rdflib."""

from pathlib import Path

from rdflib import Literal, URIRef
from rdflib.namespace import RDF, RDFS, XSD

from engine.core.namespaces import WDO
from engine.extraction.models.core import File
from engine.extraction.models.doc import CodeComment, Document, MarkdownElement
from engine.extraction.models.code import CodeConstruct


# --- DOCUMENT ---
def write_document(graph, doc: Document, context):
    """
    Serializes a Document model to RDF triples.
    """
    doc_name = Path(doc.path).name if doc.path else "unknown"
    doc_uri = WDO[f"document/{doc_name}"]
    graph.add((doc_uri, RDF.type, WDO.Documentation))
    graph.add((doc_uri, WDO.hasTitle, Literal(doc.title)))
    graph.add((doc_uri, WDO.hasContent, Literal(doc.content)))

    for element in doc.elements:
        _add_markdown_element_triples(element, graph, context, doc_uri, doc_name)


# --- MARKDOWN ELEMENT ---
def _add_markdown_element_triples(
    element: MarkdownElement, graph, context, parent_uri, file_name
):
    """
    Recursively adds triples for a markdown element.
    """
    elem_uri = WDO[f"element/{file_name}/{element.token_index}"]
    graph.add((elem_uri, RDF.type, WDO[element.type]))
    graph.add((parent_uri, WDO.hasDocumentComponent, elem_uri))
    graph.add((elem_uri, WDO.isDocumentComponentOf, parent_uri))

    if element.content:
        graph.add((elem_uri, WDO.hasTextValue, Literal(element.content)))
    if element.level:
        graph.add((elem_uri, WDO.hasHeadingLevel, Literal(element.level)))

    for child in element.children:
        _add_markdown_element_triples(child, graph, context, elem_uri, file_name)


# --- CODE COMMENT ---
def write_code_comment(graph, comment: CodeComment, context):
    """
    Serializes a CodeComment model to RDF triples.
    """
    file_uri = WDO[f"file/{Path(comment.file_path).name}"]
    comment_uri = WDO[f"comment/{Path(comment.file_path).name}/{comment.start_line}"]

    graph.add((comment_uri, RDF.type, WDO.CodeComment))
    graph.add((comment_uri, WDO.hasTextValue, Literal(comment.comment)))
    graph.add((comment_uri, WDO.hasStartLine, Literal(comment.start_line)))
    graph.add((comment_uri, WDO.hasEndLine, Literal(comment.end_line)))
    graph.add((comment_uri, WDO.isAboutCode, file_uri))
    graph.add((file_uri, WDO.hasCodeDocumentation, comment_uri))


# --- COMMIT ---
def write_commit(graph, commit, context, organization_name):
    """
    Serializes a Commit model to RDF triples and adds them to the graph.
    """
    repo_name = commit.repository_name
    commit_hash = commit.commit_hash
    commit_uri = WDO[f"commit/{repo_name}/{commit_hash}"]
    repo_uri = WDO[f"repo/{organization_name}/{repo_name}"]

    # Commit metadata
    graph.add((commit_uri, RDF.type, WDO.Commit))
    graph.add((commit_uri, WDO.hasCommitHash, Literal(commit_hash)))
    short_hash = commit_hash[:7]
    graph.add((commit_uri, RDFS.label, Literal(f"commit: {short_hash}")))
    graph.add((commit_uri, WDO.hasCommitDate, Literal(commit.committed_date)))
    graph.add((repo_uri, WDO.hasCommit, commit_uri))
    graph.add((commit_uri, WDO.isCommitIn, repo_uri))

    # Commit message
    cm_uri = WDO[f"msg/{organization_name}/{repo_name}/{commit_hash}"]
    write_commit_message(
        graph, commit_hash, organization_name, repo_name, commit.message
    )
    graph.add((commit_uri, WDO.hasCommitMessage, cm_uri))
    graph.add((cm_uri, WDO.isMessageOfCommit, commit_uri))

    # Contributor
    committer_uri = context.contributor_registry.get_or_create_contributor_uri(
        commit.committer_name, commit.committer_email
    )
    write_contributor(graph, commit.committer_name, context.contributor_registry)
    graph.add((commit_uri, WDO.committedBy, committer_uri))
    graph.add((committer_uri, WDO.committed, commit_uri))

    # Files changed
    for file_path in commit.files_changed:
        file_uri = WDO[f"file/{organization_name}/{repo_name}/{file_path.as_posix()}"]
        graph.add((commit_uri, WDO.modifies, file_uri))
        graph.add((file_uri, WDO.isModifiedBy, commit_uri))

    # Issues addressed
    for issue_ref in getattr(commit, "issue_references", []):
        issue_uri = WDO[f"issue/{organization_name}/{repo_name}/{issue_ref}"]
        graph.add((issue_uri, RDF.type, WDO.Issue))
        graph.add((issue_uri, WDO.hasIssueIdentifier, Literal(issue_ref)))
        graph.add((issue_uri, RDFS.label, Literal(f"issue: {repo_name}#{issue_ref}")))
        graph.add((commit_uri, WDO.addressesIssue, issue_uri))
        graph.add((issue_uri, WDO.isAddressedBy, commit_uri))


# --- FILE ENTITY ---
def write_files(graph, file_model: File, context):
    file_uri = WDO[
        f"file/{file_model.organization_name}/{file_model.repository_name}/{file_model.relative_path.as_posix()}"
    ]
    # Add the specific subclass type if available, otherwise add DigitalInformationCarrier
    if file_model.class_uri:
        graph.add((file_uri, RDF.type, file_model.class_uri))
    else:
        graph.add((file_uri, RDF.type, WDO.DigitalInformationCarrier))
    graph.add((file_uri, WDO.hasRelativePath, Literal(str(file_model.relative_path))))
    # Add rdfs:label as "file: [file name]"
    graph.add((file_uri, RDFS.label, Literal(f"file: {file_model.path.name}")))
    # Link file to its repository using the correct ontology property
    repository_uri = WDO[
        f"repo/{file_model.organization_name}/{file_model.repository_name}"
    ]
    graph.add((file_uri, WDO.isFileOf, repository_uri))
    graph.add((repository_uri, WDO.hasFile, file_uri))
    graph.add((file_uri, WDO.hasExtension, Literal(file_model.extension)))
    graph.add((file_uri, WDO.hasSizeInBytes, Literal(file_model.size_bytes)))
    graph.add((
        file_uri,
        WDO.hasCreationTimestamp,
        Literal(file_model.creation_timestamp),
    ))
    graph.add((
        file_uri,
        WDO.hasModificationTimestamp,
        Literal(file_model.modification_timestamp),
    ))
    # Explicitly mark as not removed
    graph.add((file_uri, WDO.isRemoved, Literal(False, datatype=XSD.boolean)))
    # Link file to its content entities (if any)
    for content in getattr(context, "contents", []):
        if hasattr(content, "path") and content.path == file_model.path:
            content_uri = WDO[
                f"content/{content.organization_name}/{content.repository_name}/{content.path.relative_to(file_model.path.parents[1]).as_posix()}"
            ]
            graph.add((file_uri, WDO.bearerOfInformation, content_uri))


# --- CONTENT ENTITY ---
def write_content(graph, content_model, context):
    """
    Write RDF triples for InformationContentEntity content.

    File metadata (size, path, timestamps) is handled by write_file_to_graph for DigitalInformationCarrier.
    """
    if not hasattr(content_model, "relative_path") or not content_model.relative_path:
        return

    rel_path_str = content_model.relative_path.as_posix()
    # Use the content registry from context to manage content URIs
    content_uri = context.content_registry.get_or_create_content_uri(
        content_model.repository_name, rel_path_str
    )

    # Add basic content triples
    write_basic_content_triples(graph, content_uri, content_model)

    # Add content-specific properties
    write_content_properties(graph, content_uri, content_model)

    # Add programming language
    write_programming_language(graph, content_uri, content_model)

    # Add line count
    write_line_count(graph, content_uri, content_model)

    # Add asset metadata
    write_asset_metadata(graph, content_uri, content_model)

    # Add dependencies
    write_dependencies(graph, content_uri, content_model)

    # Add frameworks
    write_frameworks(graph, content_uri, content_model)

    # Add special content triples
    write_special_content(graph, content_uri, content_model)

    # Link to file entity (DigitalInformationCarrier)
    write_content_file_link(graph, content_uri, content_model, rel_path_str)


def write_basic_content_triples(graph, content_uri, content_model):
    """Add basic RDF type triples for content entity."""
    if content_model.class_uri:
        graph.add((content_uri, RDF.type, URIRef(content_model.class_uri)))


def write_content_properties(graph, content_uri, content_model):
    """Add basic content properties like name, label, and content text."""
    # Add content-specific properties
    graph.add((
        content_uri,
        WDO.hasSimpleName,
        Literal(content_model.path.name, datatype=XSD.string),
    ))
    graph.add((
        content_uri,
        RDFS.label,
        Literal(f"content: {content_model.path.name}", datatype=XSD.string),
    ))

    # Add content text for specific classes (pre-determined in strategy)
    if content_model.content:
        graph.add((
            content_uri,
            WDO.hasContent,
            Literal(content_model.content, datatype=XSD.string),
        ))


def write_programming_language(graph, content_uri, content_model):
    """Add programming language property if available."""
    if (
        hasattr(content_model, "programming_language")
        and content_model.programming_language
    ):
        graph.add((
            content_uri,
            WDO.hasProgrammingLanguage,
            Literal(content_model.programming_language, datatype=XSD.string),
        ))


def write_line_count(graph, content_uri, content_model):
    """Add line count property if available."""
    if hasattr(content_model, "line_count") and content_model.line_count:
        graph.add((
            content_uri,
            WDO.hasLineCount,
            Literal(content_model.line_count, datatype=XSD.integer),
        ))


def write_asset_metadata(graph, content_uri, content_model):
    """Add asset metadata properties like image dimensions and format."""
    if hasattr(content_model, "asset_metadata") and content_model.asset_metadata:
        for key, value in content_model.asset_metadata.items():
            if key == "width" and value:
                graph.add((
                    content_uri,
                    WDO.hasImageWidth,
                    Literal(value, datatype=XSD.nonNegativeInteger),
                ))
            elif key == "height" and value:
                graph.add((
                    content_uri,
                    WDO.hasImageHeight,
                    Literal(value, datatype=XSD.nonNegativeInteger),
                ))
            elif key == "format" and value:
                graph.add((
                    content_uri,
                    WDO.hasImageFormatName,
                    Literal(value, datatype=XSD.string),
                ))


def write_dependencies(graph, content_uri, content_model):
    """Add dependency relationships and create dependency entities."""
    if hasattr(content_model, "dependencies") and content_model.dependencies:
        for dep in content_model.dependencies:
            dep_uri = URIRef(dep["uri"])
            # Add the dependency entity to the graph if not already present
            if (dep_uri, RDF.type, WDO.SoftwarePackage) not in graph:
                graph.add((dep_uri, RDF.type, WDO.SoftwarePackage))
                graph.add((
                    dep_uri,
                    WDO.hasSimpleName,
                    Literal(dep["name"], datatype=XSD.string),
                ))
                graph.add((
                    dep_uri,
                    RDFS.label,
                    Literal(f"pkg: {dep['name']}", datatype=XSD.string),
                ))
                if dep.get("version"):
                    graph.add((
                        dep_uri,
                        WDO.hasVersion,
                        Literal(dep["version"], datatype=XSD.string),
                    ))
            graph.add((content_uri, WDO.specifiesDependency, dep_uri))
            graph.add((dep_uri, WDO.isDependencyOf, content_uri))


def write_frameworks(graph, content_uri, content_model):
    """Add framework relationships and create framework entities."""
    if hasattr(content_model, "frameworks") and content_model.frameworks:
        for framework in content_model.frameworks:
            framework_uri = URIRef(framework["uri"])
            # Add the framework entity to the graph if not already present
            if (framework_uri, RDF.type, WDO.SoftwareFramework) not in graph:
                graph.add((framework_uri, RDF.type, WDO.SoftwareFramework))
                graph.add((
                    framework_uri,
                    WDO.hasSimpleName,
                    Literal(framework["name"], datatype=XSD.string),
                ))
                graph.add((
                    framework_uri,
                    RDFS.label,
                    Literal(framework["name"], datatype=XSD.string),
                ))
                if framework.get("version"):
                    graph.add((
                        framework_uri,
                        WDO.hasVersion,
                        Literal(framework["version"], datatype=XSD.string),
                    ))
            graph.add((content_uri, WDO.usesFramework, framework_uri))
            graph.add((framework_uri, WDO.isFrameworkFor, content_uri))


def write_special_content(graph, content_uri, content_model):
    """Add special content relationships like base images and licenses."""
    if hasattr(content_model, "special_content") and content_model.special_content:
        for special in content_model.special_content:
            if special["type"] == "dockerfile_base_image":
                image_uri = WDO[special["uri"]]
                # Write the container image entity with proper classification
                write_container_image(graph, image_uri, special["name"])
                # Add the relationship triples
                graph.add((content_uri, WDO.isBasedOn, image_uri))
                graph.add((image_uri, WDO.isBaseFor, content_uri))
            elif special["type"] == "license_identifier":
                graph.add((
                    content_uri,
                    WDO.hasLicenseIdentifier,
                    Literal(special["identifier"], datatype=XSD.string),
                ))


def write_container_image(graph, image_uri, image_name):
    """Write RDF triples for a ContainerImage entity."""
    # Classify the image as a ContainerImage
    graph.add((image_uri, RDF.type, WDO.ContainerImage))
    graph.add((
        image_uri,
        WDO.hasSimpleName,
        Literal(image_name, datatype=XSD.string),
    ))
    graph.add((
        image_uri,
        RDFS.label,
        Literal(f"img: {image_name}", datatype=XSD.string),
    ))


def write_content_file_link(graph, content_uri, content_model, rel_path_str):
    """Link content entity to its file entity (DigitalInformationCarrier)."""
    file_uri = WDO[
        f"file/{content_model.organization_name}/{content_model.repository_name}/{rel_path_str}"
    ]
    graph.add((file_uri, WDO.bearerOfInformation, content_uri))
    graph.add((content_uri, WDO.informationBorneBy, file_uri))


# --- CODE CONSTRUCT ---
def write_code_construct(graph, construct: CodeConstruct, context, content_uri):
    """
    Serializes a CodeConstruct (or subclass) to RDF triples.
    """
    from rdflib import URIRef, Literal
    from rdflib.namespace import RDF, RDFS, XSD
    from engine.core.namespaces import WDO

    # Build a URI for the construct
    # Use file, start/end line, and canonical name if available
    file_part = (
        f"{construct.organization_name}/{construct.repository_name}/{construct.relative_path}"
    )
    name_part = (
        f"{construct.hasCanonicalName or 'construct'}_L{construct.hasStartLine}-{construct.hasEndLine}"
    )
    construct_uri = WDO[f"code/{file_part}/{name_part}"]

    # Type: Use class name as RDF type (can be mapped to ontology if needed)
    graph.add((construct_uri, RDF.type, WDO.CodeConstruct))
    graph.add((construct_uri, RDFS.label, Literal(f"code: {construct.hasCanonicalName or name_part}")))
    graph.add((construct_uri, WDO.hasStartLine, Literal(construct.hasStartLine, datatype=XSD.integer)))
    graph.add((construct_uri, WDO.hasEndLine, Literal(construct.hasEndLine, datatype=XSD.integer)))
    graph.add((construct_uri, WDO.hasSourceCodeSnippet, Literal(construct.hasSourceCodeSnippet, datatype=XSD.string)))
    if construct.hasCanonicalName:
        graph.add((construct_uri, WDO.hasCanonicalName, Literal(construct.hasCanonicalName, datatype=XSD.string)))
    graph.add((construct_uri, WDO.hasLineCount, Literal(construct.hasLineCount, datatype=XSD.integer)))

    # Link to content entity
    graph.add((content_uri, WDO.hasCodePart, construct_uri))
    graph.add((construct_uri, WDO.isCodePartOf, content_uri))

    # Relationships
    if construct.isDeclaredBy:
        declared_by_uri = WDO[f"code/{file_part}/{construct.isDeclaredBy.hasCanonicalName or 'container'}_L{construct.isDeclaredBy.hasStartLine}-{construct.isDeclaredBy.hasEndLine}"]
        graph.add((construct_uri, WDO.isDeclaredBy, declared_by_uri))
        graph.add((declared_by_uri, WDO.declares, construct_uri))
    for used in getattr(construct, "usesDeclaration", []):
        used_uri = WDO[f"code/{file_part}/{used.hasCanonicalName or 'used'}_L{used.hasStartLine}-{used.hasEndLine}"]
        graph.add((construct_uri, WDO.usesDeclaration, used_uri))
        graph.add((used_uri, WDO.isDeclarationUsedBy, construct_uri))
    for user in getattr(construct, "isDeclarationUsedBy", []):
        user_uri = WDO[f"code/{file_part}/{user.hasCanonicalName or 'user'}_L{user.hasStartLine}-{user.hasEndLine}"]
        graph.add((construct_uri, WDO.isDeclarationUsedBy, user_uri))
        graph.add((user_uri, WDO.usesDeclaration, construct_uri))

    # TODO: Add more relationships for subclasses (fields, methods, parameters, etc.) if needed


# --- ORGANIZATION ---
def write_organization(graph, organization_name):
    org_uri = WDO[f"org/{organization_name}"]
    graph.add((org_uri, RDF.type, WDO.Organization))
    graph.add((org_uri, RDFS.label, Literal(f"org: {organization_name}")))


# --- REPOSITORY ---
def write_repository(graph, organization_name, repository_name, remote_url=None):
    repo_uri = WDO[f"repo/{organization_name}/{repository_name}"]
    graph.add((repo_uri, RDF.type, WDO.Repository))
    graph.add((repo_uri, RDFS.label, Literal(f"repo: {repository_name}")))
    org_uri = WDO[f"org/{organization_name}"]
    graph.add((repo_uri, WDO.isRepositoryOf, org_uri))
    graph.add((org_uri, WDO.hasRepository, repo_uri))
    if remote_url:
        graph.add((repo_uri, WDO.hasSourceRepositoryURL, Literal(remote_url)))


# --- HEADING ---
def write_heading(graph, heading, organization_name, repository_name, file_path):
    rel_path = Path(file_path).relative_to(Path(file_path).parents[1])
    heading_uri = WDO[
        f"heading/{organization_name}/{repository_name}/{rel_path.as_posix()}#L{heading.start_line}-{heading.end_line}"
    ]
    graph.add((heading_uri, RDF.type, WDO.Heading))
    graph.add((heading_uri, WDO.hasTextValue, Literal(heading.text)))
    graph.add((heading_uri, WDO.hasHeadingLevel, Literal(heading.level)))
    graph.add((heading_uri, WDO.hasStartLine, Literal(heading.start_line)))
    graph.add((heading_uri, WDO.hasEndLine, Literal(heading.end_line)))


# --- PARAGRAPH ---
def write_paragraph(graph, paragraph, organization_name, repository_name, file_path):
    rel_path = Path(file_path).relative_to(Path(file_path).parents[1])
    para_uri = WDO[
        f"paragraph/{organization_name}/{repository_name}/{rel_path.as_posix()}#L{paragraph.start_line}-{paragraph.end_line}"
    ]
    graph.add((para_uri, RDF.type, WDO.Paragraph))
    graph.add((para_uri, WDO.hasTextValue, Literal(paragraph.text)))
    graph.add((para_uri, WDO.hasStartLine, Literal(paragraph.start_line)))
    graph.add((para_uri, WDO.hasEndLine, Literal(paragraph.end_line)))


# --- ISSUE ---
def write_issue(
    graph, issue_id, organization_name, repository_name, title=None, status=None
):
    issue_uri = WDO[f"issue/{organization_name}/{repository_name}/{issue_id}"]
    graph.add((issue_uri, RDF.type, WDO.Issue))
    graph.add((
        issue_uri,
        RDFS.label,
        Literal(f"issue: {repository_name}#{issue_id}"),
    ))
    if status:
        graph.add((issue_uri, WDO.hasStatus, Literal(status)))


# --- COMMIT MESSAGE ---
def write_commit_message(
    graph, commit_hash, organization_name, repository_name, message
):
    cm_uri = WDO[f"msg/{organization_name}/{repository_name}/{commit_hash}"]
    graph.add((cm_uri, RDF.type, WDO.CommitMessage))
    graph.add((cm_uri, WDO.hasContent, Literal(message)))
    short_msg = message[:30] + ("..." if len(message) > 30 else "")
    graph.add((cm_uri, RDFS.label, Literal(f"msg: {short_msg}")))


# --- CONTRIBUTOR ---
def write_contributor(graph, contributor_name, contributor_registry):
    """Write a contributor to the graph."""
    import re
    import unicodedata

    from engine.core.namespaces import FOAF, WDO

    # Use the same normalization as the registry
    def normalize_contributor_name(name: str) -> str:
        name = unicodedata.normalize("NFKD", name)
        name = "".join([c for c in name if not unicodedata.combining(c)])
        name = name.lower().strip()
        name = re.sub(r"\s+", " ", name)
        return name

    norm_name = normalize_contributor_name(contributor_name)
    contributor_uri = WDO[f"person/{norm_name.replace(' ', '_')}"]
    graph.add((contributor_uri, RDF.type, WDO.Contributor))
    graph.add((contributor_uri, FOAF.name, Literal(contributor_name)))
    graph.add((contributor_uri, RDFS.label, Literal(f"contrib: {contributor_name}")))
    for email in contributor_registry.get_emails_for_contributor(contributor_name):
        if email:
            graph.add((contributor_uri, FOAF.mbox, Literal(email)))
