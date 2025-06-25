import os
import logging
from app.core.config import LOG_DIR
from app.core.paths import get_log_path
from rdflib import Literal, URIRef
from rdflib.namespace import RDFS
import uuid

# Setup dedicated logger
os.makedirs(LOG_DIR, exist_ok=True)
log_path = get_log_path("code_annotator.log")
logger = logging.getLogger("code_annotator")
logger.setLevel(logging.INFO)
handler = logging.FileHandler(log_path, mode='w')
handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
if not logger.hasHandlers():
    logger.addHandler(handler)

class CodeAnnotator:
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

    def annotate(self, code_data):
        logger.info(f"Annotating code entities from {len(code_data)} files")
        type_map = {
            'Functions': self.ontology.get_class('Function'),
            'Classes': self.ontology.get_class('Class'),
            'Interfaces': self.ontology.get_class('Interface'),
            'Structs': self.ontology.get_class('Struct'),
            'Traits': self.ontology.get_class('Trait'),
            'Variables': self.ontology.get_class('Variable'),
            'Imports': self.ontology.get_class('Import'),
            'Comments': self.ontology.get_class('Comment'),
            'Methods': self.ontology.get_class('Function'),
            'Requires': self.ontology.get_class('Import'),
            'Includes': self.ontology.get_class('Import'),
            'Using': self.ontology.get_class('Import'),
            'Components': self.ontology.get_class('Class'),
            'Types': self.ontology.get_class('Class'),
            'Objects': self.ontology.get_class('Class'),
            'Modules': self.ontology.get_class('Class'),
            'Selectors': self.ontology.get_class('Variable'),
            'Tags': self.ontology.get_class('Class'),
            'Mixins': self.ontology.get_class('Function')
        }
        for file_path, file_data in code_data.items():
            file_uri = self._generate_uri(self.ontology.get_namespace("file"), file_path, "file")
            language = file_data.get('language', 'unknown')
            self.graph.add((file_uri, self.ontology.get_property('hasLanguage'), Literal(language)))
            constructs = file_data.get('constructs', {})
            for construct_type, construct_list in constructs.items():
                for construct in construct_list:
                    construct_class = type_map.get(construct_type, self.ontology.get_class('CodeConstruct'))
                    construct_name = construct.get('text', str(uuid.uuid4()))
                    construct_uri = self._generate_uri(self.ontology.get_namespace("code"), construct_name, construct_type.lower())
                    self.graph.add((construct_uri, self.ontology.get_class('CodeConstruct'), construct_class))
                    self.graph.add((construct_uri, RDFS.label, Literal(construct_name)))
                    self.graph.add((construct_uri, self.ontology.get_property('hasName'), Literal(construct_name)))
                    self.graph.add((construct_uri, self.ontology.get_property('hasContent'), Literal(construct.get('text', ''))))
                    self.graph.add((construct_uri, self.ontology.get_property('atLine'), Literal(construct.get('line', 0))))
                    self.graph.add((construct_uri, self.ontology.get_property('isElementOf'), file_uri))
                    self.graph.add((file_uri, self.ontology.get_property('containsElement'), construct_uri))
                    if construct_type in ['Imports', 'Requires', 'Includes', 'Using']:
                        import_text = construct.get('text', '')
                        if import_text:
                            imported_uri = self._generate_uri(self.ontology.get_namespace("file"), import_text, "import")
                            self.graph.add((construct_uri, self.ontology.get_property('imports'), imported_uri))
                    logger.debug(f"Annotated code construct: {construct_name} in {file_path}")
        logger.info("Code annotation complete.") 