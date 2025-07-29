import re

from engine.api.db import db_connector
from engine.api.tasks.analysis import run_organization_analysis
from engine.api.utils.sparql_loader import load_query


def is_valid_uri(uri: str) -> bool:
    """Validate that the input string is a well-formed HTTP(S) URI for SPARQL queries."""
    if any(c in uri for c in (">", '"', "'", "{", "}", ";")):
        return False
    return bool(re.match(r"^https?://[^\s]+$", uri))


def list_organizations():
    """
    Fetches all organizations and their repositories from the triplestore.

    Returns:
        list[dict]: List of organizations, each with id, name, and repositories.
    """
    query = load_query("organizations/list_organizations.rq")
    result = db_connector.execute_sparql_query(query)
    bindings = result.get("results", {}).get("bindings", [])
    orgs = {}
    for b in bindings:
        org_id = b["org"]["value"]
        org_name = b.get("name", {}).get("value", org_id.split("/")[-1])
        repo_id = b["repo"]["value"]
        repo_name = b.get("repoName", {}).get("value", repo_id.split("/")[-1])
        if org_id not in orgs:
            orgs[org_id] = {"id": org_id, "name": org_name, "repositories": []}
        orgs[org_id]["repositories"].append({"id": repo_id, "name": repo_name})
    return list(orgs.values())


def get_organization_details(org_id: str):
    """
    Fetches details for a specific organization, including repositories, file count, and relationship count.

    Args:
        org_id (str): The organization URI.

    Returns:
        dict: Organization details, or None if not found/invalid.
    """
    if not is_valid_uri(org_id):
        return None
    # 1. Get org and repo details
    details_query = load_query("organizations/get_organization_details.rq").format(
        org_id=org_id
    )
    details_result = db_connector.execute_sparql_query(details_query)
    bindings = details_result.get("results", {}).get("bindings", [])
    if not bindings:
        return None
    org_name = bindings[0].get("name", {}).get("value", org_id.split("/")[-1])
    repositories = []
    for b in bindings:
        repo_id = b["repo"]["value"]
        repo_name = b.get("repoName", {}).get("value", repo_id.split("/")[-1])
        repositories.append({"id": repo_id, "name": repo_name})
    # 2. File count
    file_count_query = load_query(
        "organizations/get_organization_file_count.rq"
    ).format(org_id=org_id)
    file_count_result = db_connector.execute_sparql_query(file_count_query)
    file_count = 0
    file_bindings = file_count_result.get("results", {}).get("bindings", [])
    if file_bindings:
        file_count = int(file_bindings[0]["totalFiles"]["value"])
    # 3. Relationship count
    rel_count_query = load_query(
        "organizations/get_organization_relationship_count.rq"
    ).format(org_id=org_id)
    rel_count_result = db_connector.execute_sparql_query(rel_count_query)
    rel_count = 0
    rel_bindings = rel_count_result.get("results", {}).get("bindings", [])
    if rel_bindings:
        rel_count = int(rel_bindings[0]["totalRelationships"]["value"])
    return {
        "id": org_id,
        "name": org_name,
        "totalFiles": file_count,
        "totalRelations": rel_count,
        "repositories": repositories,
    }


def start_organization_analysis(organization_name):
    """
    Start the organization analysis as a background Celery task.

    Args:
        organization_name (str): Name of the organization.

    Returns:
        dict: Job id and status.
    """
    task = run_organization_analysis.delay(organization_name)
    return {"job_id": task.id, "status": "submitted"}
