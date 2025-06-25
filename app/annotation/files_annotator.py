import os
import logging
from app.core.config import LOG_DIR
from app.core.paths import get_log_path
from rdflib import Literal, URIRef
from rdflib.namespace import RDFS

# Setup dedicated logger
os.makedirs(LOG_DIR, exist_ok=True)
log_path = get_log_path("file_annotator.log")
logger = logging.getLogger("file_annotator")
logger.setLevel(logging.INFO)
handler = logging.FileHandler(log_path, mode='w')
handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
if not logger.hasHandlers():
    logger.addHandler(handler)

class FileAnnotator:
    def __init__(self, ontology, graph_manager):
        self.ontology = ontology
        self.graph = graph_manager.graph
        self.generated_uris = set()
        self.project_ref = None

    def _generate_uri(self, namespace, identifier, prefix=""):
        safe_id = identifier.replace(" ", "_").replace("/", "_").replace("\\", "_")
        safe_id = "".join(c for c in safe_id if c.isalnum() or c in "_-." )
        uri_str = f"{namespace}{prefix}_{safe_id}" if prefix else f"{namespace}{safe_id}"
        counter = 1
        original_uri = uri_str
        while uri_str in self.generated_uris:
            uri_str = f"{original_uri}_{counter}"
            counter += 1
        self.generated_uris.add(uri_str)
        return URIRef(uri_str)

    def annotate(self, file_records, project_name, project_uri=None):
        logger.info(f"Annotating {len(file_records)} files for project '{project_name}'")
        # Set up project entity
        project_ns = self.ontology.get_namespace("project")
        wdo = self.ontology.get_namespace("wdo")
        self.project_ref = URIRef(project_uri or f"{project_ns}{project_name.lower().replace(' ', '_')}")
        self.graph.add((self.project_ref, self.ontology.get_class('Project'), wdo.Project))
        self.graph.add((self.project_ref, RDFS.label, Literal(project_name)))
        # File type mapping
        file_type_map = {
            'code': self.ontology.get_class('CodeFile'),
            'markup': self.ontology.get_class('MarkupFile'),
            'style': self.ontology.get_class('StyleFile'),
            'config': self.ontology.get_class('ConfigurationFile'),
            'assets': self.ontology.get_class('AssetFile'),
            'docs': self.ontology.get_class('DocumentationFile'),
            'data': self.ontology.get_class('DataFile'),
            'templates': self.ontology.get_class('TemplateFile'),
            'test': self.ontology.get_class('TestFile'),
            'docker': self.ontology.get_class('DockerRelatedFile'),
            'build_project': self.ontology.get_class('BuildFile'),
            'archives_compression': self.ontology.get_class('ArchiveFile'),
            'database': self.ontology.get_class('DatabaseFile'),
            'jupyter_notebooks': self.ontology.get_class('NotebookFile'),
            'misc': self.ontology.get_class('MiscellaneousFile')
        }
        for file_record in file_records:
            file_uri = self._generate_uri(self.ontology.get_namespace("file"), file_record['path'], "file")
            file_type = file_type_map.get(file_record['type'], self.ontology.get_class('File'))
            self.graph.add((file_uri, self.ontology.get_class('File'), file_type))
            self.graph.add((file_uri, RDFS.label, Literal(file_record['path'])))
            self.graph.add((file_uri, self.ontology.get_property('hasPath'), Literal(file_record['path'])))
            self.graph.add((file_uri, self.ontology.get_property('hasExtension'), Literal(file_record['extension'])))
            self.graph.add((file_uri, self.ontology.get_property('hasCategory'), Literal(file_record['type'])))
            self.graph.add((self.project_ref, self.ontology.get_property('hasResource'), file_uri))
            logger.debug(f"Annotated file: {file_record['path']} as {file_record['type']} ({file_record['extension']})")
        logger.info(f"File annotation complete for project '{project_name}'") 