import os
import sys
import requests
import pytest
from typing import Dict, Any


sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../app'))

BASE_URL = os.environ.get("KMS_BASE_URL", "http://localhost:5000")
print(f"[DEBUG] BASE_URL used for tests: {BASE_URL}")

@pytest.fixture(scope="module")
def api_available():
    print(f"[DEBUG] Checking API availability at {BASE_URL}/api/dashboard_stats")
    try:
        response = requests.get(f"{BASE_URL}/api/dashboard_stats", timeout=5)
        print(f"[DEBUG] Response status code: {response.status_code}")
        print(f"[DEBUG] Response text: {response.text}")
        return response.status_code == 200
    except Exception as e:
        print(f"[DEBUG] Exception during API check: {e}")
        return False

def test_dashboard_stats(api_available):
    if not api_available:
        pytest.skip("API server not running")
    response = requests.get(f"{BASE_URL}/api/dashboard_stats")
    assert response.status_code == 200
    stats = response.json()
    assert "totalRepos" in stats
    assert "totalFiles" in stats
    assert "totalEntities" in stats
    assert "totalRelationships" in stats

def test_repository_list(api_available):
    if not api_available:
        pytest.skip("API server not running")
    query = """
    SELECT ?repository ?name WHERE {
      ?repository a <http://semantic-web-kms.edu.et/wdo#Repository> .
      OPTIONAL { ?repository <http://semantic-web-kms.edu.et/wdo#hasSimpleName> ?name }
    }
    LIMIT 5
    """
    response = requests.post(f"{BASE_URL}/api/sparql", json={"query": query})
    assert response.status_code == 200
    data = response.json()
    repos = data.get('results', {}).get('bindings', [])
    assert isinstance(repos, list)

def get_first_repo_uri():
    query = """
    SELECT ?repository WHERE {
      ?repository a <http://semantic-web-kms.edu.et/wdo#Repository> .
    }
    LIMIT 1
    """
    response = requests.post(f"{BASE_URL}/api/sparql", json={"query": query})
    if response.status_code == 200:
        data = response.json()
        repos = data.get('results', {}).get('bindings', [])
        if repos:
            return repos[0]['repository']['value']
    return None

def test_graph_analytics(api_available):
    if not api_available:
        pytest.skip("API server not running")
    repo_uri = get_first_repo_uri()
    if not repo_uri:
        pytest.skip("No repositories found for analytics testing")
    analytics_response = requests.get(f"{BASE_URL}/api/graph/analytics?repo={repo_uri}")
    assert analytics_response.status_code == 200
    analytics = analytics_response.json()
    assert "node_types" in analytics
    assert "relationship_types" in analytics
    assert "centrality" in analytics

def test_graph_data(api_available):
    if not api_available:
        pytest.skip("API server not running")
    repo_uri = get_first_repo_uri()
    if not repo_uri:
        pytest.skip("No repositories found for graph testing")
    graph_response = requests.get(f"{BASE_URL}/api/graph?repo={repo_uri}")
    assert graph_response.status_code == 200
    graph_data = graph_response.json()
    assert "nodes" in graph_data
    assert "edges" in graph_data

def test_entity_search(api_available):
    if not api_available:
        pytest.skip("API server not running")
    repo_uri = get_first_repo_uri()
    if not repo_uri:
        pytest.skip("No repositories found for search testing")
    search_response = requests.get(f"{BASE_URL}/api/graph/search?q=function&repo={repo_uri}")
    assert search_response.status_code == 200
    search_data = search_response.json()
    assert "results" in search_data
