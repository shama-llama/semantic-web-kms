from rdflib import Namespace

class BaseOntology:
    def __init__(self):
        self.namespaces = {}
    def get_namespace(self, name: str) -> Namespace:
        return self.namespaces[name]
    def get_class(self, class_name: str):
        raise NotImplementedError
    def get_property(self, prop_name: str):
        raise NotImplementedError

# Central ontology registry
_ontology_registry = {}

def register_ontology(name, ontology_cls):
    """Register an ontology class by name."""
    _ontology_registry[name] = ontology_cls

def get_ontology(name):
    """Retrieve a registered ontology class by name."""
    return _ontology_registry.get(name) 