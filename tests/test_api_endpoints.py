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

@patch("app.api.server.requests.post")
def test_sparql_query_success(mock_post, client):
    mock_post.return_value.status_code = 200
    mock_post.return_value.json.return_value = {"results": {"bindings": [{"foo": {"value": "bar"}}]}}
    response = client.post("/api/sparql", json={"query": "SELECT * WHERE {?s ?p ?o}"})
    assert response.status_code == 200
    data = response.get_json()
    assert "results" in data
    assert data["results"]["bindings"][0]["foo"]["value"] == "bar"

@patch("app.api.server.run_dashboard_sparql")
def test_graph_search_success(mock_sparql, client):
    mock_sparql.return_value = {
        "results": {
            "bindings": [
                {
                    "entity": {"value": "http://example.org/e1"},
                    "type": {"value": "http://semantic-web-kms.edu.et/wdo#ClassDefinition"},
                    "label": {"value": "MyClass"},
                    "description": {"value": "A test class."},
                    "file": {"value": "file.py"}
                }
            ]
        }
    }
    response = client.get("/api/graph/search?q=MyClass")
    assert response.status_code == 200
    data = response.get_json()
    assert "results" in data
    assert data["results"][0]["label"] == "MyClass"
    assert data["results"][0]["type"] == "ClassDefinition"

@patch("app.api.server.run_dashboard_sparql")
def test_api_graph_success(mock_sparql, client):
    mock_sparql.return_value = {
        "results": {
            "bindings": [
                {
                    "entityA": {"value": "A1"},
                    "entityAType": {"value": "http://semantic-web-kms.edu.et/wdo#Class"},
                    "entityALabel": {"value": "ClassA"},
                    "entityB": {"value": "B1"},
                    "entityBType": {"value": "http://semantic-web-kms.edu.et/wdo#Class"},
                    "entityBLabel": {"value": "ClassB"},
                    "relPred": {"value": "http://semantic-web-kms.edu.et/wdo#callsFunction"}
                }
            ]
        }
    }
    response = client.get("/api/graph?repo=http://example.org/repo1")
    assert response.status_code == 200
    data = response.get_json()
    assert "nodes" in data
    assert "edges" in data
    assert data["nodes"][0]["label"] == "ClassA"
    assert data["edges"][0]["label"] == "callsFunction"

@patch("app.api.server.run_dashboard_sparql")
def test_recent_activity_success(mock_sparql, client):
    mock_sparql.return_value = {
        "results": {
            "bindings": [
                {
                    "message": {"value": "Initial commit"},
                    "hash": {"value": "abc123"},
                    "repo": {"value": "http://example.org/repo1"},
                    "timestamp": {"value": "1700000000"}
                }
            ]
        }
    }
    response = client.get("/api/recent_activity")
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)
    assert data[0]["title"].startswith("Initial commit")
    assert data[0]["desc"].startswith("repo1")

@patch("app.api.server.run_dashboard_sparql")
def test_analytics_file_distribution_success(mock_sparql, client):
    mock_sparql.return_value = {
        "results": {
            "bindings": [
                {"ext": {"value": ".py"}, "count": {"value": "5"}},
                {"ext": {"value": ".js"}, "count": {"value": "3"}}
            ]
        }
    }
    response = client.get("/api/analytics/file_distribution")
    assert response.status_code == 200
    data = response.get_json()
    assert any(d["label"] == "Python" and d["count"] == 5 for d in data)
    assert any(d["label"] == "JavaScript" and d["count"] == 3 for d in data)

@patch("app.api.server.run_dashboard_sparql")
def test_analytics_entity_types_success(mock_sparql, client):
    mock_sparql.return_value = {
        "results": {
            "bindings": [
                {"type": {"value": "http://semantic-web-kms.edu.et/wdo#ClassDefinition"}, "count": {"value": "7"}}
            ]
        }
    }
    response = client.get("/api/analytics/entity_types")
    assert response.status_code == 200
    data = response.get_json()
    assert any(d["label"] == "Class" and d["count"] == 7 for d in data)

@patch("app.api.server.run_dashboard_sparql")
def test_analytics_repo_activity_success(mock_sparql, client):
    mock_sparql.return_value = {
        "results": {
            "bindings": [
                {"repo": {"value": "http://example.org/repo1"}, "count": {"value": "5"}}
            ]
        }
    }
    response = client.get("/api/analytics/repo_activity")
    assert response.status_code == 200
    data = response.get_json()
    assert any(d["repo"] == "repo1" and d["activity"] == 5 for d in data)

@patch("app.api.server.run_dashboard_sparql")
def test_graph_analytics_success(mock_sparql, client):
    mock_sparql.side_effect = [
        {"results": {"bindings": [{"type": {"value": "http://semantic-web-kms.edu.et/wdo#Class"}, "count": {"value": "2"}}]}},
        {"results": {"bindings": [{"relType": {"value": "http://semantic-web-kms.edu.et/wdo#callsFunction"}, "count": {"value": "3"}}]}},
        {"results": {"bindings": [{"entity": {"value": "http://example.org/e1"}, "label": {"value": "E1"}, "degree": {"value": "4"}}]}}
    ]
    response = client.get("/api/graph/analytics?repo=http://example.org/repo1")
    assert response.status_code == 200
    data = response.get_json()
    assert "node_types" in data
    assert "relationship_types" in data
    assert "centrality" in data
    assert data["node_types"][0]["type"] == "Class"
    assert data["relationship_types"][0]["type"] == "callsFunction"
    assert data["centrality"][0]["label"] == "E1"

@patch("app.api.server.run_dashboard_sparql")
def test_entity_details_success(mock_sparql, client):
    # details, incoming, outgoing
    mock_sparql.side_effect = [
        {"results": {"bindings": [{"type": {"value": "http://semantic-web-kms.edu.et/wdo#Class"}, "label": {"value": "E1"}, "description": {"value": "desc"}, "file": {"value": "f.py"}, "startLine": {"value": "1"}, "endLine": {"value": "2"}}]}},
        {"results": {"bindings": [{"source": {"value": "src"}, "sourceType": {"value": "http://semantic-web-kms.edu.et/wdo#Class"}, "sourceLabel": {"value": "SRC"}, "relType": {"value": "http://semantic-web-kms.edu.et/wdo#callsFunction"}}]}},
        {"results": {"bindings": [{"target": {"value": "tgt"}, "targetType": {"value": "http://semantic-web-kms.edu.et/wdo#Class"}, "targetLabel": {"value": "TGT"}, "relType": {"value": "http://semantic-web-kms.edu.et/wdo#callsFunction"}}]}}
    ]
    response = client.get("/api/graph/entity/http://example.org/e1")
    assert response.status_code == 200
    data = response.get_json()
    assert "details" in data
    assert "incoming" in data
    assert "outgoing" in data
    assert data["details"]["label"] == "E1"
    assert data["incoming"][0]["sourceLabel"] == "SRC"
    assert data["outgoing"][0]["targetLabel"] == "TGT"

@patch("app.api.server.run_dashboard_sparql")
def test_entity_neighborhood_success(mock_sparql, client):
    # neighborhood, then rels
    mock_sparql.side_effect = [
        {"results": {"bindings": [
            {"entity": {"value": "e1"}, "type": {"value": "http://semantic-web-kms.edu.et/wdo#Class"}, "label": {"value": "E1"}, "distance": {"value": "0"}},
            {"entity": {"value": "e2"}, "type": {"value": "http://semantic-web-kms.edu.et/wdo#Class"}, "label": {"value": "E2"}, "distance": {"value": "1"}}
        ]}},
        {"results": {"bindings": [
            {"from": {"value": "e1"}, "to": {"value": "e2"}, "relType": {"value": "http://semantic-web-kms.edu.et/wdo#callsFunction"}}
        ]}}
    ]
    response = client.get("/api/graph/neighborhood/e1?depth=1")
    assert response.status_code == 200
    data = response.get_json()
    assert "nodes" in data
    assert "edges" in data
    assert data["nodes"][0]["label"] == "E1"
    assert data["edges"][0]["label"] == "callsFunction"

# Error cases

def test_api_graph_missing_param(client):
    response = client.get("/api/graph")
    assert response.status_code == 400
    data = response.get_json()
    assert "error" in data

def test_graph_analytics_missing_param(client):
    response = client.get("/api/graph/analytics")
    assert response.status_code == 400
    data = response.get_json()
    assert "error" in data 