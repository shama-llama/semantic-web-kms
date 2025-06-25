import os
import logging
from app.core.config import LOG_DIR
from app.core.paths import get_log_path
from rdflib import Literal, URIRef
from rdflib.namespace import RDFS

# Setup dedicated logger
os.makedirs(LOG_DIR, exist_ok=True)
log_path = get_log_path("doc_annotator.log")
logger = logging.getLogger("doc_annotator")
logger.setLevel(logging.INFO)
handler = logging.FileHandler(log_path, mode='w')
handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
if not logger.hasHandlers():
    logger.addHandler(handler)

class DocAnnotator:
    def __init__(self, ontology, graph_manager):
        self.ontology = ontology
        self.graph = graph_manager.graph
        self.generated_uris = set()

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

    def annotate(self, doc_data):
        logger.info(f"Annotating {len(doc_data)} documentation segments")
        type_map = {
            'heading1': self.ontology.get_class('Heading'),
            'heading2': self.ontology.get_class('Heading'),
            'heading3': self.ontology.get_class('Heading'),
            'code_block': self.ontology.get_class('CodeBlock'),
            'page': self.ontology.get_class('Page')
        }
        for doc_segment in doc_data:
            segment_uri = self._generate_uri(self.ontology.get_namespace("doc"), f"segment_{doc_segment['id']}", "doc")
            segment_type = doc_segment.get('segment_type', 'documentation')
            segment_class = type_map.get(segment_type, self.ontology.get_class('DocumentationSegment'))
            self.graph.add((segment_uri, self.ontology.get_class('DocumentationSegment'), segment_class))
            self.graph.add((segment_uri, RDFS.label, Literal(f"Documentation segment {doc_segment['id']}")))
            self.graph.add((segment_uri, self.ontology.get_property('hasContent'), Literal(doc_segment.get('content', ''))))
            if segment_type.startswith('heading'):
                level = int(segment_type[-1])
                self.graph.add((segment_uri, self.ontology.get_property('hasHeadingLevel'), Literal(level)))
            if doc_segment.get('page'):
                self.graph.add((segment_uri, self.ontology.get_property('onPage'), Literal(doc_segment['page'])))
            if doc_segment.get('file_id'):
                file_uri = self._generate_uri(self.ontology.get_namespace("file"), f"file_{doc_segment['file_id']}", "doc_file")
                self.graph.add((segment_uri, self.ontology.get_property('isElementOf'), file_uri))
            logger.debug(f"Annotated doc segment: {doc_segment['id']} ({segment_type})")
        logger.info("Documentation annotation complete.") 