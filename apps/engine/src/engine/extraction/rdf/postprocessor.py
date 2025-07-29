"""Graph-level post-processing utilities for RDF extraction pipeline."""

from rdflib import RDF, RDFS, Literal
from rdflib.namespace import XSD

from engine.core.namespaces import WDO


class Postprocessor:
    """
    Performs post-processing on the RDF graph after extraction, such as adding minimal entities for deleted files.

    Args:
        context: The ExtractionContext containing the RDF graph and related state.
    """

    def __init__(self, context):
        self.context = context

    def add_deleted_files(self):
        """
        Add minimal entities for files that are referenced (e.g., by commits) but not defined as DigitalInformationCarrier.
        This ensures deleted/removed files are represented in the output RDF graph.
        """
        g = self.context.graph
        referenced_files = set(g.objects(None, WDO.modifies))
        referenced_files.update(g.subjects(WDO.isModifiedBy, None))
        defined_files = set(g.subjects(RDF.type, WDO.DigitalInformationCarrier))
        missing_files = referenced_files - defined_files
        if not missing_files:
            return
        for file_uri in missing_files:
            # Skip if isRemoved is already set to False (i.e., present file)
            if (file_uri, WDO.isRemoved, Literal(False, datatype=XSD.boolean)) in g:
                continue
            filename = str(file_uri).split("/")[-1]
            g.add((file_uri, RDF.type, WDO.DigitalInformationCarrier))
            g.add((file_uri, RDFS.label, Literal(f"file: {filename}")))
            g.add((file_uri, WDO.isRemoved, Literal(True, datatype=XSD.boolean)))
