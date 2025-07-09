import importlib.util
import json
import os
import sys
from unittest.mock import patch

import pytest
from flask import Flask

# Dynamically import the app from app/api/server.py
spec = importlib.util.spec_from_file_location(
    "server", os.path.join(os.path.dirname(__file__), "../../app/api/server.py")
)
if spec is None or spec.loader is None:
    raise ImportError("Could not load app/api/server.py for testing.")
server = importlib.util.module_from_spec(spec)
sys.modules["server"] = server
spec.loader.exec_module(server)
app = server.app


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def test_dashboard_stats_success(client):
    mock_response = {
        "results": {
            "bindings": [
                {"totalRepos": {"value": "5"}},
                {"totalFiles": {"value": "10"}},
                {"totalEntities": {"value": "20"}},
                {"totalRelationships": {"value": "30"}},
            ]
        }
    }
    with patch("server.run_dashboard_sparql", return_value=mock_response):
        response = client.get("/api/dashboard_stats")
        assert response.status_code == 200
        data = response.get_json()
        assert isinstance(data, dict)


def test_sparql_query_success(client):
    mock_sparql_result = {"results": {"bindings": [{"foo": {"value": "bar"}}]}}
    with patch("requests.post") as mock_post:
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = mock_sparql_result
        response = client.post(
            "/api/sparql", json={"query": "SELECT * WHERE {?s ?p ?o}"}
        )
        assert response.status_code == 200
        assert response.get_json() == mock_sparql_result


def test_sparql_query_missing_query(client):
    response = client.post("/api/sparql", json={})
    assert response.status_code == 400
    data = response.get_json()
    assert "error" in data


def test_sparql_query_error_response(client):
    with patch("requests.post") as mock_post:
        mock_post.return_value.status_code = 500
        mock_post.return_value.text = "SPARQL error"
        response = client.post(
            "/api/sparql", json={"query": "SELECT * WHERE {?s ?p ?o}"}
        )
        assert response.status_code == 500
        data = response.get_json()
        assert "error" in data
