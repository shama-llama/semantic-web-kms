"""Classifier-based content extraction and modeling."""

import logging
from pathlib import Path

from engine.core.paths import get_content_types
from engine.extraction.context import ExtractionContext
from engine.extraction.models.core import Content
from engine.extraction.services.asset_metadata_service import AssetMetadataService
from engine.extraction.services.dependency_analysis_service import (
    DependencyAnalysisService,
)
from engine.extraction.services.framework_detection_service import (
    FrameworkDetectionService,
)
from engine.extraction.services.special_content_service import SpecialContentService
from engine.extraction.strategies.base import BaseExtractorStrategy
from engine.extraction.utils.classification_utils import (
    classify_file,
    load_classifiers_from_dict,
)
from engine.ontology.wdo import WDOOntology

logger = logging.getLogger("ContentStrategy")

CONTENT_CONFIG_PATH = "src/engine/config/content_types.json"


class ContentStrategy(BaseExtractorStrategy):
    """
    Extraction strategy for discovering and modeling InformationContentEntity content.
    Handles content-specific extraction and InformationContentEntity classification.
    """

    @property
    def name(self) -> str:
        return "Content Extractor"

    def extract(self, context: ExtractionContext, progress, task_id):
        """
        Processes files to extract InformationContentEntity content.
        Uses incremental serialization and batch processing to prevent memory buildup.

        Args:
            context (ExtractionContext): The shared pipeline context.
            progress: The rich progress bar instance.
            task_id: The ID of the task for this strategy.
        """
        # Get file metadata instead of full file objects
        file_metadata = getattr(context, "file_metadata", [])
        content_files = file_metadata

        progress.update(task_id, total=len(content_files))

        # Load classifiers and ontology
        content_types_data = get_content_types()
        classifiers, ignore_patterns = load_classifiers_from_dict(content_types_data)
        ontology = WDOOntology()

        # Initialize services for content analysis
        asset_service = AssetMetadataService()
        dependency_service = DependencyAnalysisService()
        framework_service = FrameworkDetectionService()
        special_content_service = SpecialContentService()

        # Process content files in batches
        batch_size = getattr(context, "batch_size", 500)

        def process_content_batch(batch_files, progress, task_id):
            """Process a batch of content files."""
            from engine.extraction.rdf.serializer import RdfSerializer

            serializer = RdfSerializer(context)

            for file_meta in batch_files:
                # Classify the file's content as InformationContentEntity
                class_name, class_uri, _ = classify_file(
                    Path(file_meta["path"]).name,
                    classifiers,
                    ignore_patterns,
                    ontology,
                    default_class="InformationContentEntity",
                )

                # Skip if no classification found
                if not class_name or not class_uri:
                    continue

                # Calculate relative path
                rel_path = self._calculate_relative_path(file_meta, context)
                if not rel_path:
                    continue

                # Extract content text for classes that need it
                content_text = None
                content_classes_with_text = {
                    "ConfigurationSetting",
                    "CommitMessage",
                    "Log",
                    "License",
                    "JSON",
                    "XML",
                    "YAML",
                    "DataFormat",
                    "Template",
                    "HTMLCode",
                    "CSSCode",
                    "BuildScript",
                    "DockerfileSpecification",
                    "JupyterNotebook",
                    "Notebook",
                    "DatabaseSchema",
                    "SQLCode",
                    "APIDocumentation",
                    "ArchitecturalDecisionRecord",
                    "BestPracticeGuideline",
                }
                if class_name in content_classes_with_text:
                    try:
                        file_path = Path(file_meta["path"])
                        # Use lazy loading if available, otherwise fallback to direct read
                        if hasattr(file_meta, "get_content"):
                            content_bytes = file_meta.get_content()
                        else:
                            with open(file_path, "rb") as f:
                                content_bytes = f.read()
                        content_text = content_bytes.decode("utf-8", errors="ignore")[
                            :1000
                        ]
                    except Exception:
                        content_text = None

                # Prepare additional content data
                programming_language = self._get_programming_language(class_name)
                line_count = self._get_line_count(
                    file_meta["path"], class_name, special_content_service
                )
                asset_metadata = self._get_asset_metadata(
                    file_meta["path"], class_name, asset_service
                )
                dependencies = self._get_dependencies(
                    file_meta["path"], class_name, dependency_service, context
                )
                frameworks = self._get_frameworks(
                    file_meta["path"], class_name, framework_service, context
                )
                special_content = self._get_special_content(
                    file_meta["path"], class_name, special_content_service
                )

                # Create and serialize Content model with all pre-calculated data
                content = Content(
                    path=Path(file_meta["path"]),
                    organization_name=file_meta["organization_name"],
                    repository_name=file_meta["repository_name"],
                    ontology_class=class_name,
                    class_uri=class_uri,
                    content=content_text,
                    relative_path=rel_path,
                    programming_language=programming_language,
                    line_count=line_count,
                    asset_metadata=asset_metadata,
                    dependencies=dependencies,
                    frameworks=frameworks,
                    special_content=special_content,
                )
                serializer.serialize(content)

        # Use batch processing from pipeline
        pipeline = getattr(context, "_pipeline", None)

        if pipeline and hasattr(pipeline, "process_batch"):
            pipeline.process_batch(
                content_files, process_content_batch, progress, task_id, "content files"
            )
        else:
            # Fallback to processing all files at once
            process_content_batch(content_files, progress, task_id)

    def _calculate_relative_path(self, file_meta, context):
        """Calculate relative path for content entity."""
        try:
            file_path = Path(file_meta["path"])
            # Try to find the matching file in context.files to get its relative_path
            for f in getattr(context, "files", []):
                if hasattr(f, "path") and f.path == file_path:
                    return f.relative_path

            # If not found, calculate from path structure
            path_parts = file_path.parts
            repo_name = file_meta["repository_name"]

            # Find the index of the repo name in the path
            try:
                repo_index = path_parts.index(repo_name)
                # Everything after the repo name is the relative path
                return Path(*path_parts[repo_index + 1 :])
            except ValueError:
                # Fallback: use the filename as relative path
                return Path(file_path.name)
        except Exception as e:
            logger.warning(
                f"Could not calculate relative path for {file_meta['path']}: {e}"
            )
            return None

    def _get_programming_language(self, class_name):
        """Get programming language for code files."""
        code_classes = {
            "JavaScriptCode": "javascript",
            "PHPCode": "php",
            "PythonCode": "python",
            "RubyCode": "ruby",
            "GraphQLCode": "graphql",
            "SQLCode": "sql",
            "CSharpCode": "csharp",
            "GoCode": "go",
            "JavaCode": "java",
            "RustCode": "rust",
            "TypeScriptCode": "typescript",
            "SoftwareCode": "software",
        }
        return code_classes.get(class_name)

    def _get_line_count(self, file_path, class_name, special_content_service):
        """Get line count for code files."""
        if class_name.endswith("Code") or class_name in [
            "SoftwareCode",
            "ProgrammingLanguageCode",
            "QueryLanguageCode",
            "WebPresentationCode",
        ]:
            try:
                return special_content_service.get_line_count(str(file_path))
            except Exception:
                return None
        return None

    def _get_asset_metadata(self, file_path, class_name, asset_service):
        """Get asset metadata for media files."""
        metadata = {}
        try:
            if class_name == "ImageDescription":
                metadata = asset_service.extract_image_metadata(file_path)
            elif class_name in [
                "VideoDescription",
                "AudioDescription",
                "FontDescription",
            ]:
                metadata = asset_service.extract_media_metadata(file_path, class_name)
        except Exception:
            pass
        return metadata

    def _get_dependencies(self, file_path, class_name, dependency_service, context):
        """Get dependencies for build files."""
        dependencies = []
        try:
            if class_name == "BuildScript":
                deps = dependency_service.extract_dependencies_from_build_file(
                    file_path, class_name
                )
                for dep in deps:
                    dep_uri = (
                        context.software_package_registry.get_or_create_package_uri(
                            dep["name"]
                        )
                    )
                    dependencies.append({
                        "name": dep["name"],
                        "version": dep.get("version"),
                        "uri": dep_uri,
                    })
        except Exception:
            pass
        return dependencies

    def _get_frameworks(self, file_path, class_name, framework_service, context):
        """Get frameworks for code files."""
        frameworks = []
        try:
            if class_name.endswith("Code") and class_name not in [
                "SoftwareCode",
                "ProgrammingLanguageCode",
                "QueryLanguageCode",
                "WebPresentationCode",
            ]:
                fw_list = framework_service.extract_frameworks_from_code_file(
                    file_path, class_name
                )
                for framework in fw_list:
                    framework_uri = (
                        context.framework_registry.get_or_create_framework_uri(
                            framework["name"]
                        )
                    )
                    frameworks.append({
                        "name": framework["name"],
                        "version": framework.get("version"),
                        "uri": framework_uri,
                    })
        except Exception:
            pass
        return frameworks

    def _get_special_content(self, file_path, class_name, special_content_service):
        """Get special content data."""
        special_content = []
        try:
            if class_name == "DockerfileSpecification":
                base_image = special_content_service.extract_dockerfile_base_image(
                    file_path
                )
                if base_image:
                    # Parse the Docker image name to extract just the meaningful part
                    clean_image_name = self._parse_docker_image_name(base_image)
                    special_content.append({
                        "type": "dockerfile_base_image",
                        "name": base_image,
                        "uri": f"container/{clean_image_name}",
                    })
            elif class_name == "License":
                license_id = special_content_service.extract_license_identifier(
                    file_path
                )
                if license_id:
                    special_content.append({
                        "type": "license_identifier",
                        "identifier": license_id,
                    })
        except Exception:
            pass
        return special_content

    def _parse_docker_image_name(self, image_name: str) -> str:
        """Parse Docker image name to extract meaningful identifier for URI."""
        import re

        cleaned = re.sub(r"--[a-zA-Z-]+(?:=[^\s]+)?", "", image_name)
        cleaned = cleaned.strip()

        if cleaned:
            parts = cleaned.split()
            if parts:
                image_name = parts[0]
        else:
            if "=" in image_name:
                image_name = image_name.split("=")[-1]
            else:
                parts = image_name.split()
                if parts:
                    image_name = parts[-1]

        clean_name = image_name.replace(":", "_").replace("/", "_").replace("=", "_")
        clean_name = clean_name.strip("_")

        return clean_name
