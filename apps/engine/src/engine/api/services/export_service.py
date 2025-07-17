import pathlib
from flask import jsonify
from engine.api.db import db_connector
from engine.core.paths import PathManager


def export_data(export_format, app):
    """
    Export data from the triplestore in the requested format.
    Args:
        export_format (str): Export format (json, ttl, rdf, csv)
        app: Flask app instance (for config)
    Returns:
        tuple: (data, status_code, headers) or (jsonify, status_code)
    """
    if export_format not in ["json", "ttl", "rdf", "csv"]:
        return jsonify({"error": "Unsupported format"}), 400
    export_query = """
    CONSTRUCT { ?s ?p ?o }
    WHERE { ?s ?p ?o }
    """
    if export_format == "json":
        data = db_connector.execute_sparql_query(export_query)
        return jsonify(data), 200, {"Content-Type": "application/json"}
    elif export_format == "ttl":
        from rdflib import Graph
        g = Graph()
        ttl_path = PathManager.get_output_path("wdkb.ttl")
        if pathlib.Path(ttl_path).exists():
            g.parse(ttl_path, format="turtle")
            return g.serialize(format="turtle"), 200, {"Content-Type": "text/turtle"}
        else:
            return jsonify({"error": "No TTL file found"}), 404
    elif export_format == "rdf":
        from rdflib import Graph
        g = Graph()
        ttl_path = PathManager.get_output_path("wdkb.ttl")
        if pathlib.Path(ttl_path).exists():
            g.parse(ttl_path, format="turtle")
            return g.serialize(format="xml"), 200, {"Content-Type": "application/rdf+xml"}
        else:
            return jsonify({"error": "No TTL file found"}), 404
    elif export_format == "csv":
        csv_data = "Subject,Predicate,Object\n"
        triples_query = """
        SELECT ?s ?p ?o
        WHERE { ?s ?p ?o }
        LIMIT 1000
        """
        triples_data = db_connector.execute_sparql_query(triples_query)
        for binding in triples_data["results"]["bindings"]:
            s = binding["s"]["value"]
            p = binding["p"]["value"]
            o = binding["o"]["value"]
            csv_data += f'"{s}","{p}","{o}"\n'
        return csv_data, 200, {"Content-Type": "text/csv"} 