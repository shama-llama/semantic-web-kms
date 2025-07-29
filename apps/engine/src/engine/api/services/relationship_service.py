from engine.api.db import db_connector
from engine.api.utils.sparql_loader import load_query


def get_relationships():
    """
    Get relationships for the knowledge graph.

    Returns:
        dict: Relationship types and counts.
    """
    query = load_query("relationships/relationship_types.rq")
    result = db_connector.execute_sparql_query(query)
    bindings = result.get("results", {}).get("bindings", [])
    relationships = []
    for binding in bindings:
        rel_type = binding["relationshipType"]["value"]
        count = int(binding["count"]["value"])
        rel_name = (
            rel_type.split("#")[-1] if "#" in rel_type else rel_type.split("/")[-1]
        )
        relationships.append({"type": rel_type, "name": rel_name, "count": count})
    return {
        "relationships": relationships,
        "totalRelationships": sum(r["count"] for r in relationships),
    }
