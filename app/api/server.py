"""Flask API server for Semantic Web KMS."""

import os
from typing import Any, Dict, List, cast

import requests
from flask import Flask, jsonify, request
from flask_caching import Cache
from flask_cors import CORS

# Configurations for AllegroGraph
AGRAPH_URL = os.environ.get("AGRAPH_SERVER_URL")
AGRAPH_REPO = os.environ.get("AGRAPH_REPO")
AGRAPH_USER = os.environ.get("AGRAPH_USERNAME")
AGRAPH_PASS = os.environ.get("AGRAPH_PASSWORD")

app = Flask(__name__)
CORS(app)

# Initialize Flask-Caching
cache = Cache(app, config={"CACHE_TYPE": "SimpleCache", "CACHE_DEFAULT_TIMEOUT": 300})

# Optimized dashboard stats queries
DASHBOARD_QUERIES = {
    "totalRepos": "SELECT (COUNT(DISTINCT ?repo) AS ?totalRepos) WHERE { ?repo a <http://semantic-web-kms.edu.et/wdo#Repository> . }",
    "totalFiles": "SELECT (COUNT(DISTINCT ?file) AS ?totalFiles) WHERE { ?repo a <http://semantic-web-kms.edu.et/wdo#Repository> . ?repo <http://www.w3.org/2000/01/rdf-schema#member> ?file . }",
    "totalEntities": """SELECT (COUNT(DISTINCT ?entity) AS ?totalEntities) WHERE {\n    ?entity a ?entityType .\n    FILTER(?entityType IN (\n        <http://semantic-web-kms.edu.et/wdo#SoftwareCode>,\n        <http://semantic-web-kms.edu.et/wdo#FunctionDefinition>,\n        <http://semantic-web-kms.edu.et/wdo#ClassDefinition>\n    ))\n}""",
    "totalRelationships": """SELECT (COUNT(*) AS ?totalRelationships) WHERE {\n    ?s ?relPred ?o .\n    FILTER(?relPred IN (\n        <http://semantic-web-kms.edu.et/wdo#invokes>,\n        <http://semantic-web-kms.edu.et/wdo#callsFunction>,\n        <http://semantic-web-kms.edu.et/wdo#extendsType>,\n        <http://semantic-web-kms.edu.et/wdo#implementsInterface>,\n        <http://semantic-web-kms.edu.et/wdo#declaresCode>,\n        <http://semantic-web-kms.edu.et/wdo#hasField>,\n        <http://semantic-web-kms.edu.et/wdo#hasMethod>,\n        <http://semantic-web-kms.edu.et/wdo#isRelatedTo>,\n        <http://semantic-web-kms.edu.et/wdo#usesFramework>,\n        <http://semantic-web-kms.edu.et/wdo#tests>,\n        <http://semantic-web-kms.edu.et/wdo#documentsEntity>,\n        <http://semantic-web-kms.edu.et/wdo#modifies>,\n        <http://semantic-web-kms.edu.et/wdo#imports>,\n        <http://semantic-web-kms.edu.et/wdo#isImportedBy>,\n        <http://semantic-web-kms.edu.et/wdo#conformsToGuideline>,\n        <http://semantic-web-kms.edu.et/wdo#copiesFrom>,\n        <http://semantic-web-kms.edu.et/wdo#embedsCode>,\n        <http://semantic-web-kms.edu.et/wdo#generates>,\n        <http://semantic-web-kms.edu.et/wdo#hasArgument>,\n        <http://semantic-web-kms.edu.et/wdo#hasResource>,\n        <http://semantic-web-kms.edu.et/wdo#isAbout>,\n        <http://semantic-web-kms.edu.et/wdo#isAboutCode>,\n        <http://semantic-web-kms.edu.et/wdo#isDependencyOf>,\n        <http://semantic-web-kms.edu.et/wdo#specifiesDependency>,\n        <http://semantic-web-kms.edu.et/wdo#styles>\n    ))\n}""",
}


def run_dashboard_sparql(query: str) -> Any:
    """
    Run a SPARQL query against the AllegroGraph endpoint and return the JSON result as a dictionary.

    Args:
        query (str): The SPARQL query string to execute.

    Returns:
        dict: The JSON-decoded response from the AllegroGraph endpoint.

    Raises:
        requests.HTTPError: If the HTTP request to the endpoint fails.
        Exception: For other unexpected errors during the request.

    Side Effects:
        Sends a POST request to the AllegroGraph server.
    """
    agraph_endpoint = (
        f"{AGRAPH_URL}/repositories/{AGRAPH_REPO}"  # AllegroGraph REST API endpoint
    )
    headers = {"Accept": "application/sparql-results+json"}
    auth = (AGRAPH_USER, AGRAPH_PASS) if AGRAPH_USER and AGRAPH_PASS else None
    resp = requests.post(
        agraph_endpoint,
        data={"query": query},
        headers=headers,
        auth=auth,
        timeout=30,  # 30 second timeout
    )
    resp.raise_for_status()
    return resp.json()


@app.route("/api/dashboard_stats", methods=["GET"])
@cache.cached()
def dashboard_stats() -> Any:
    """
    Return dashboard statistics by running predefined SPARQL queries and aggregating the results.

    Returns:
        flask.Response: A JSON response containing dashboard statistics as key-value pairs.

    Raises:
        Exception: If a SPARQL query fails, an exception may be raised by run_dashboard_sparql.

    Side Effects:
        Caches the response for improved performance.
    """
    results: Dict[str, int] = {}
    for key, query in DASHBOARD_QUERIES.items():
        data: Dict[str, Any] = run_dashboard_sparql(query)
        bindings: List[Dict[str, Any]] = cast(
            List[Dict[str, Any]], data["results"]["bindings"]
        )
        if bindings:
            first_binding: Dict[str, Any] = bindings[0]
            value_dict: Dict[str, Any] = next(iter(first_binding.values()))
            value: str = value_dict["value"]
            results[key] = int(value)
        else:
            results[key] = 0
    return jsonify(results)


@app.route("/api/sparql", methods=["POST"])
def sparql_query():
    """
    Handle a POST request to execute a SPARQL query and return the results as JSON.

    Returns:
        flask.Response: A JSON response containing the SPARQL query results or an error message.

    Raises:
        None. All exceptions are handled and returned as error responses.

    Request JSON:
        {
            "query": "SPARQL query string"
        }

    Response JSON:
        On success: SPARQL query results as JSON.
        On error: {"error": "error message"}
    """
    data = request.get_json()
    query = data.get("query")
    if not query:
        return jsonify({"error": "Missing query"}), 400
    agraph_endpoint = f"{AGRAPH_URL}/repositories/{AGRAPH_REPO}"
    headers = {"Accept": "application/sparql-results+json"}
    auth = (AGRAPH_USER, AGRAPH_PASS) if AGRAPH_USER and AGRAPH_PASS else None
    resp = requests.post(
        agraph_endpoint, data={"query": query}, headers=headers, auth=auth, timeout=30
    )
    if resp.status_code == 200:
        return jsonify(resp.json())
    else:
        return jsonify({"error": resp.text}), resp.status_code


if __name__ == "__main__":
    # Read host, port, and debug mode from environment variables, with sensible defaults
    host = os.environ.get("API_HOST", "127.0.0.1")
    port = int(os.environ.get("API_PORT", 5000))
    debug = os.environ.get("API_DEBUG", "true").lower() == "true"

    app.run(host=host, port=port, debug=debug)
