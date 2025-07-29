"""Defines the RdfSerializer class for serializing models to RDF using rdflib."""


import logging
from engine.extraction.models.code import CodeConstruct
from engine.extraction.models.core import Content, File, Repository
from engine.extraction.models.doc import CodeComment, Document, Heading
from engine.extraction.models.git import Commit
from engine.extraction.rdf.writers import (
    write_code_comment,
    write_commit,
    write_content,
    write_document,
    write_files,
    write_heading,
    write_organization,
    write_repository,
    write_code_construct,
)


class RdfSerializer:
    """
    Serializes model instances to RDF triples using rdflib.
    """

    def __init__(self, context):
        self.context = context
        self.logger = logging.getLogger("RdfSerializer")

    def serialize(self, model_instance):
        """
        Serializes the given model instance to RDF triples.
        Dispatches to the appropriate writer function based on model type.

        Args:
            model_instance: The model instance to serialize.
        """
        def _flatten_constructs(constructs: list[CodeConstruct]) -> list[CodeConstruct]:
            """Iteratively flatten all nested code constructs, avoiding cycles and duplicates."""
            flat_list = []
            seen = set()
            queue = list(constructs)
            while queue:
                construct = queue.pop(0)
                if id(construct) in seen:
                    continue
                seen.add(id(construct))
                flat_list.append(construct)
                for attr in dir(construct):
                    if attr.startswith('__'):
                        continue
                    value = getattr(construct, attr)
                    if isinstance(value, CodeConstruct):
                        queue.append(value)
                    elif isinstance(value, list):
                        for item in value:
                            if isinstance(item, CodeConstruct):
                                queue.append(item)
            return flat_list

        if isinstance(model_instance, list) and all(
            isinstance(m, CodeConstruct) for m in model_instance
        ):
            if not model_instance:
                return

            all_constructs = _flatten_constructs(model_instance)
            first = all_constructs[0]

            # Ensure necessary attributes are present
            if not all(hasattr(first, attr) for attr in ['file_path', 'organization_name', 'repository_name', 'relative_path']):
                self.logger.error(f"Skipping serialization for {getattr(first, 'file_path', 'unknown file')} due to missing metadata.")
                return
            
            assert first.file_path is not None
            assert first.organization_name is not None
            assert first.repository_name is not None
            assert first.relative_path is not None
            
            from pathlib import Path
            relative_path_obj = Path(first.relative_path)

            self.logger.debug(f"Serializing {len(all_constructs)} constructs for file: {first.file_path}")

            # --- Add hasCodePart/isCodePartOf relationships ---
            from rdflib import URIRef

            prop_cache = self.context.prop_cache
            if "hasCodePart" not in prop_cache or "isCodePartOf" not in prop_cache:
                self.logger.error("Ontology properties 'hasCodePart' or 'isCodePartOf' not found in cache.")
                return

            assert first.repository_name is not None
            assert first.relative_path is not None
            content_uri = self.context.content_registry.get_or_create_content_uri(
                first.repository_name, str(first.relative_path)
            )
            
            self.logger.debug(f"Linking constructs to content URI: {content_uri}")

            for c in all_constructs:
                try:
                    assert first.organization_name is not None
                    assert first.repository_name is not None
                    assert first.relative_path is not None
                    
                    from pathlib import Path
                    relative_path_obj = Path(first.relative_path)

                    # Write the code construct to RDF
                    write_code_construct(self.context.graph, c, self.context, content_uri)

                except Exception as e:
                    self.logger.error(f"Error generating or linking URI for construct {c}: {e}", exc_info=True)
        elif isinstance(model_instance, Commit):
            org_name = self.context.input_dir.name
            write_commit(self.context.graph, model_instance, self.context, org_name)
        elif isinstance(model_instance, File):
            write_files(self.context.graph, model_instance, self.context)
        elif isinstance(model_instance, Content):
            write_content(self.context.graph, model_instance, self.context)
        elif isinstance(model_instance, CodeComment):
            write_code_comment(self.context.graph, model_instance, self.context)
        elif isinstance(model_instance, Repository):
            org_name = self.context.input_dir.name
            write_repository(
                self.context.graph,
                org_name,
                model_instance.name,
                model_instance.remote_url,
            )
        elif isinstance(model_instance, Document):
            write_document(self.context.graph, model_instance, self.context)
        elif isinstance(model_instance, Heading):
            # Try to get org/repo/file context if available
            org_name = getattr(self.context, "input_dir", None)
            org_name = org_name.name if org_name else "unknown"
            repo_name = getattr(model_instance, "repository_name", "unknown")
            file_path = getattr(model_instance, "file_path", None)
            write_heading(
                self.context.graph, model_instance, org_name, repo_name, file_path
            )
        elif isinstance(model_instance, str) and model_instance == "organization":
            # Special case: serialize organization from context
            org_name = self.context.input_dir.name
            write_organization(self.context.graph, org_name)
