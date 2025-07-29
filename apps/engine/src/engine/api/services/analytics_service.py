from engine.api.db import db_connector
from engine.api.utils.sparql_loader import load_query


def get_analytics():
    """
    Fetches analytics data for the dashboard, including codebase metrics and entity distribution.

    Returns:
        dict: Analytics data.
    """
    # Codebase metrics
    codebase_query = load_query("analytics/codebase_metrics.rq")
    codebase_result = db_connector.execute_sparql_query(codebase_query)
    codebase = {}
    if codebase_result and codebase_result["results"]["bindings"]:
        b = codebase_result["results"]["bindings"][0]
        codebase = {
            "totalRepositories": int(b.get("totalRepositories", {}).get("value", 0)),
            "totalFiles": int(b.get("totalFiles", {}).get("value", 0)),
            "sourceCodeFiles": int(b.get("sourceCodeFiles", {}).get("value", 0)),
            "documentationFiles": int(b.get("documentationFiles", {}).get("value", 0)),
            "assetFiles": int(b.get("assetFiles", {}).get("value", 0)),
        }
    # Entity distribution
    entity_query = load_query("analytics/entity_distribution.rq")
    entity_result = db_connector.execute_sparql_query(entity_query)
    entity = {}
    if entity_result and entity_result["results"]["bindings"]:
        b = entity_result["results"]["bindings"][0]
        entity = {
            "functions": int(b.get("functions", {}).get("value", 0)),
            "classes": int(b.get("classes", {}).get("value", 0)),
            "interfaces": int(b.get("interfaces", {}).get("value", 0)),
            "attributes": int(b.get("attributes", {}).get("value", 0)),
            "variables": int(b.get("variables", {}).get("value", 0)),
            "parameters": int(b.get("parameters", {}).get("value", 0)),
        }
    return {
        "codebaseMetrics": codebase,
        "entityDistribution": entity,
    }
