from rdflib import Graph, URIRef, Namespace, RDF, RDFS, OWL
from typing import Optional, List, Set, Union, Dict
import os


class BaseOntology:
    def __init__(self, owl_path: Optional[str] = None):
        self.graph = Graph()
        self.ontology_uri: Optional[str] = None
        self.namespaces: Dict[str, Namespace] = {}
        if owl_path and os.path.exists(owl_path):
            self.graph.parse(owl_path)
            self._extract_namespaces()
            self.ontology_uri = self._get_ontology_uri()

    def _extract_namespaces(self) -> None:
        for prefix, ns in self.graph.namespaces():
            self.namespaces[prefix] = Namespace(ns)

    def _get_ontology_uri(self) -> Optional[str]:
        for s in self.graph.subjects(RDF.type, OWL.Ontology):
            return str(s)
        return None

    def get_namespace(self, name: str) -> Optional[Namespace]:
        return self.namespaces.get(name)

    def get_class_uri(self, class_name: str) -> Optional[URIRef]:
        for s in self.graph.subjects(RDF.type, OWL.Class):
            label = self.graph.value(s, RDFS.label)
            if label and str(label).lower() == class_name.lower():
                return URIRef(str(s))
            # fallback: match local part
            if str(s).split('#')[-1] == class_name or str(s).split('/')[-1] == class_name:
                return URIRef(str(s))
        return None

    def get_property_uri(self, prop_name: str) -> Optional[URIRef]:
        for s in self.graph.subjects(RDF.type, OWL.ObjectProperty):
            label = self.graph.value(s, RDFS.label)
            if label and str(label).lower() == prop_name.lower():
                return URIRef(str(s))
            if str(s).split('#')[-1] == prop_name or str(s).split('/')[-1] == prop_name:
                return URIRef(str(s))
        for s in self.graph.subjects(RDF.type, OWL.DatatypeProperty):
            label = self.graph.value(s, RDFS.label)
            if label and str(label).lower() == prop_name.lower():
                return URIRef(str(s))
            if str(s).split('#')[-1] == prop_name or str(s).split('/')[-1] == prop_name:
                return URIRef(str(s))
        return None

    def get_superclass_chain(self, class_uri: Union[str, URIRef]) -> List[str]:
        """Return the full superclass chain for a class URI, up to the root."""
        chain: List[str] = []
        current = URIRef(class_uri)
        visited: Set[URIRef] = set()
        while True:
            superclass = self.graph.value(current, RDFS.subClassOf)
            if superclass and superclass not in visited:
                chain.append(str(superclass))
                visited.add(URIRef(str(superclass)))
                current = URIRef(str(superclass))
            else:
                break
        return chain

    def get_all_classes(self) -> List[str]:
        return [str(s) for s in self.graph.subjects(RDF.type, OWL.Class)]

    def get_all_properties(self) -> List[str]:
        props: Set[str] = set()
        for s in self.graph.subjects(RDF.type, OWL.ObjectProperty):
            props.add(str(s))
        for s in self.graph.subjects(RDF.type, OWL.DatatypeProperty):
            props.add(str(s))
        return list(props)

    def get_subclasses(self, class_uri: Union[str, URIRef], direct_only: bool = False) -> List[str]:
        """Return all subclasses of a given class URI. If direct_only is False, returns recursively."""
        subclasses: Set[str] = set()
        to_visit: List[URIRef] = [URIRef(class_uri)]
        while to_visit:
            current = to_visit.pop()
            for s in self.graph.subjects(RDFS.subClassOf, current):
                if (s, RDF.type, OWL.Class) in self.graph:
                    subclasses.add(str(s))
                    if not direct_only:
                        to_visit.append(URIRef(str(s)))
        return list(subclasses)


# Central ontology registry
_ontology_registry: Dict[str, type] = {}


def register_ontology(name: str, ontology_cls: type) -> None:
    """Register an ontology class by name."""
    _ontology_registry[name] = ontology_cls
