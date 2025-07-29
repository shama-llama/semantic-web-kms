"""Defines the SpecializedDocParser class for parsing specialized documentation."""

import re
from typing import Any

from rdflib import Graph, Literal, URIRef
from rdflib.namespace import RDF, RDFS, XSD


class SpecializedDocParser:
    """
    Parses specialized documentation formats like API docs, ADRs, and guidelines.
    """

    def parse_api_documentation(
        self, text: str, doc_uri: URIRef, g: Graph, prop_cache: dict[str, Any]
    ):
        """
        Parses API documentation for endpoints and HTTP methods.
        """
        endpoint_pattern = r'["\'](/api/[^"\']+)["\']'
        for match in re.finditer(endpoint_pattern, text):
            endpoint = match.group(1)
            g.add((
                doc_uri,
                prop_cache["hasEndpointPath"],
                Literal(endpoint, datatype=XSD.string),
            ))

        http_methods = ["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"]
        for method in http_methods:
            if method.lower() in text.lower():
                g.add((
                    doc_uri,
                    prop_cache["hasHttpMethod"],
                    Literal(method, datatype=XSD.string),
                ))

    def parse_adr_documentation(
        self,
        text: str,
        doc_uri: URIRef,
        g: Graph,
        prop_cache: dict[str, Any],
        class_cache: dict[str, Any],
    ):
        """
        Parses Architectural Decision Record (ADR) documentation.
        """
        context_patterns = [
            r"##\s*Context[:\s]*(.*?)(?=##|\Z)",
            r"##\s*Decision[:\s]*(.*?)(?=##|\Z)",
            r"##\s*Consequences[:\s]*(.*?)(?=##|\Z)",
        ]

        for pattern in context_patterns:
            for match in re.finditer(pattern, text, re.DOTALL | re.IGNORECASE):
                context = match.group(1).strip()
                if context:
                    context_uri = URIRef(f"{doc_uri}_context_{hash(context) % 10000}")
                    g.add((context_uri, RDF.type, class_cache["TextualElement"]))
                    g.add((
                        context_uri,
                        prop_cache["hasTextValue"],
                        Literal(context, datatype=XSD.string),
                    ))
                    g.add((
                        context_uri,
                        RDFS.label,
                        Literal(f"context: {context[:50]}...", datatype=XSD.string),
                    ))
                    g.add((doc_uri, prop_cache["hasDocumentComponent"], context_uri))

    def parse_guideline_documentation(
        self,
        text: str,
        doc_uri: URIRef,
        g: Graph,
        prop_cache: dict[str, Any],
        class_cache: dict[str, Any],
    ):
        """
        Parses best practice guideline documentation.
        """
        rule_patterns = [
            r"^\d+\.\s*(.+)$",
            r"^[-*]\s*(.+)$",
            r"##\s*Guidelines?[:\s]*(.*?)(?=##|\Z)",
        ]

        for pattern in rule_patterns:
            for match in re.finditer(pattern, text, re.MULTILINE | re.IGNORECASE):
                rule = match.group(1).strip()
                if rule:
                    rule_uri = URIRef(f"{doc_uri}_rule_{hash(rule) % 10000}")
                    g.add((rule_uri, RDF.type, class_cache["TextualElement"]))
                    g.add((
                        rule_uri,
                        prop_cache["hasTextValue"],
                        Literal(rule, datatype=XSD.string),
                    ))
                    g.add((
                        rule_uri,
                        RDFS.label,
                        Literal(f"rule: {rule[:50]}...", datatype=XSD.string),
                    ))
                    g.add((doc_uri, prop_cache["hasDocumentComponent"], rule_uri))
