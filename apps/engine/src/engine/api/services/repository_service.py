from engine.api.db import db_connector
from engine.api.utils.sparql_loader import load_query


def list_repositories():
    """
    Fetches all repositories with their name and last updated timestamp.

    Returns:
        list[dict]: List of repositories.
    """
    query = load_query("repositories/list_repositories.rq")
    result = db_connector.execute_sparql_query(query)
    bindings = result.get("results", {}).get("bindings", [])
    repos = []
    for b in bindings:
        repo_id = b["repo"]["value"]
        name = b.get("name", {}).get("value", "")
        last_updated = b.get("lastUpdated", {}).get("value", "")
        repos.append({
            "id": repo_id,
            "name": name,
            "lastUpdated": last_updated,
        })
    return repos
