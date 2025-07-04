import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import pytest
from unittest.mock import patch
from app.api.server import app

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

@patch("app.api.server.run_dashboard_sparql")
def test_dashboard_stats_success(mock_sparql, client):
    mock_sparql.side_effect = lambda q: {"results": {"bindings": [{"val": {"value": "1"}}]}}
    # Patch the keys to match the code's expectations
    def fake_run(query):
        if "totalRepos" in query:
            return {"results": {"bindings": [{"totalRepos": {"value": "2"}}]}}
        if "totalFiles" in query:
            return {"results": {"bindings": [{"totalFiles": {"value": "10"}}]}}
        if "totalEntities" in query:
            return {"results": {"bindings": [{"totalEntities": {"value": "100"}}]}}
        if "totalRelationships" in query:
            return {"results": {"bindings": [{"totalRelationships": {"value": "200"}}]}}
        return {"results": {"bindings": []}}
    mock_sparql.side_effect = fake_run
    response = client.get("/api/dashboard_stats")
    assert response.status_code == 200
    data = response.get_json()
    assert data["totalRepos"] == 2
    assert data["totalFiles"] == 10
    assert data["totalEntities"] == 100
    assert data["totalRelationships"] == 200 