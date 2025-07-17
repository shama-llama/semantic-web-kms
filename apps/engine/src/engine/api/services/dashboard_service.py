from engine.api.db import db_connector
from engine.api.utils.sparql_loader import load_query

def get_dashboard_statistics():
    """
    Fetches and computes all statistics for the dashboard.
    Returns:
        dict: Dashboard statistics (currently only totalRepos).
    """
    repo_count_query = load_query('dashboard/repositories_count.rq')
    result = db_connector.execute_sparql_query(repo_count_query)
    count = 0
    if result and result['results']['bindings']:
        count = int(result['results']['bindings'][0]['count']['value'])
    return {"totalRepos": count} 