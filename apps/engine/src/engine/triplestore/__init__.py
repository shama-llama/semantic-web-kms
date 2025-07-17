"""Triplestore package for Semantic Web KMS."""

# Centralized user-facing messages and error strings for triplestore operations
MESSAGES = {
    "connection_failed": "Failed to connect to triplestore at {endpoint}.",
    "query_error": "Error executing SPARQL query: {error}",
    "update_success": "Triplestore updated successfully.",
    "graph_not_found": "Graph not found: {graph_uri}",
    "invalid_credentials": "Invalid credentials for triplestore access.",
}
