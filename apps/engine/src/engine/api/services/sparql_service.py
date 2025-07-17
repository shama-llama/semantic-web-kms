from engine.api.db import db_connector

def execute_sparql(query: str):
    """
    Execute a SPARQL query against the triplestore.
    Args:
        query (str): The SPARQL query string.
    Returns:
        dict: SPARQL query results as JSON.
    """
    return db_connector.execute_sparql_query(query) 