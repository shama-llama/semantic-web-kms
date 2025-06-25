from rdflib import Namespace
from .base import BaseOntology, register_ontology

class WDOOntology(BaseOntology):
    def __init__(self):
        super().__init__()
        self.namespaces = {
            "wdo": Namespace("http://semantic-web.edu.et/wdo#"),
            "project": Namespace("http://semantic-web.edu.et/project/"),
            "asset": Namespace("http://semantic-web.edu.et/asset/"),
            "file": Namespace("http://semantic-web.edu.et/file/"),
            "code": Namespace("http://semantic-web.edu.et/code/"),
            "doc": Namespace("http://semantic-web.edu.et/doc/")
        }
        self.class_map = {
            'Project': self.namespaces["wdo"].Project,
            'File': self.namespaces["wdo"].File,
            'CodeFile': self.namespaces["wdo"].CodeFile,
            'MarkupFile': self.namespaces["wdo"].MarkupFile,
            'StyleFile': self.namespaces["wdo"].StyleFile,
            'ConfigurationFile': self.namespaces["wdo"].ConfigurationFile,
            'AssetFile': self.namespaces["wdo"].AssetFile,
            'DocumentationFile': self.namespaces["wdo"].DocumentationFile,
            'DataFile': self.namespaces["wdo"].DataFile,
            'TemplateFile': self.namespaces["wdo"].TemplateFile,
            'TestFile': self.namespaces["wdo"].TestFile,
            'DockerRelatedFile': self.namespaces["wdo"].DockerRelatedFile,
            'BuildFile': self.namespaces["wdo"].BuildFile,
            'ArchiveFile': self.namespaces["wdo"].ArchiveFile,
            'DatabaseFile': self.namespaces["wdo"].DatabaseFile,
            'NotebookFile': self.namespaces["wdo"].NotebookFile,
            'MiscellaneousFile': self.namespaces["wdo"].MiscellaneousFile,
            'Function': self.namespaces["wdo"].Function,
            'Class': self.namespaces["wdo"].Class,
            'Interface': self.namespaces["wdo"].Interface,
            'Struct': self.namespaces["wdo"].Struct,
            'Trait': self.namespaces["wdo"].Trait,
            'Variable': self.namespaces["wdo"].Variable,
            'Import': self.namespaces["wdo"].Import,
            'Comment': self.namespaces["wdo"].Comment,
            'CodeConstruct': self.namespaces["wdo"].CodeConstruct,
            'Heading': self.namespaces["wdo"].Heading,
            'CodeBlock': self.namespaces["wdo"].CodeBlock,
            'Page': self.namespaces["wdo"].Page,
            'DocumentationSegment': self.namespaces["wdo"].DocumentationSegment
        }
        self.property_map = {
            'hasPath': self.namespaces["wdo"].hasPath,
            'hasExtension': self.namespaces["wdo"].hasExtension,
            'hasCategory': self.namespaces["wdo"].hasCategory,
            'hasLanguage': self.namespaces["wdo"].hasLanguage,
            'hasName': self.namespaces["wdo"].hasName,
            'hasContent': self.namespaces["wdo"].hasContent,
            'atLine': self.namespaces["wdo"].atLine,
            'isElementOf': self.namespaces["wdo"].isElementOf,
            'containsElement': self.namespaces["wdo"].containsElement,
            'imports': self.namespaces["wdo"].imports,
            'hasHeadingLevel': self.namespaces["wdo"].hasHeadingLevel,
            'onPage': self.namespaces["wdo"].onPage,
            'belongsToClass': self.namespaces["wdo"].belongsToClass,
            'hasResource': self.namespaces["wdo"].hasResource
        }
    def get_namespace(self, name: str) -> Namespace:
        return self.namespaces[name]
    def get_class(self, class_name: str):
        return self.class_map[class_name]
    def get_property(self, prop_name: str):
        return self.property_map[prop_name]

register_ontology('wdo', WDOOntology) 