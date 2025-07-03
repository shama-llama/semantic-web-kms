from rdflib import Graph


class GraphManager:
    def __init__(self, ontology):
        self.ontology = ontology
        self.graph = Graph()
        for prefix, ns in ontology.namespaces.items():
            self.graph.bind(prefix, ns)

    def add_triple(self, s, p, o):
        self.graph.add((s, p, o))

    def serialize(self, path, fmt='turtle'):
        self.graph.serialize(destination=path, format=fmt)

    def stats(self):
        return {
            'total_triples': len(self.graph),
            'subjects': len(set(self.graph.subjects())),
            'predicates': len(set(self.graph.predicates())),
            'objects': len(set(self.graph.objects())),
        }
