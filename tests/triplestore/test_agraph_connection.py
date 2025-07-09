import os
import types
from unittest.mock import MagicMock, patch

import pytest

import app.triplestore.agraph_connection as ag_mod


class DummySession:
    def __init__(self):
        self.auth = None
        self.closed = False
        self.last_post = None
        self.last_get = None

    def post(self, url, data=None, headers=None, timeout=None):
        self.last_post = (url, data, headers, timeout)
        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        resp.status_code = 200
        return resp

    def get(self, url, timeout=None, verify=None):
        self.last_get = (url, timeout, verify)
        resp = MagicMock()
        resp.status_code = 200
        resp.text = "ok"
        return resp

    def close(self):
        self.closed = True


@patch.dict(
    os.environ,
    {
        "AGRAPH_CLOUD_URL": "http://repo",
        "AGRAPH_USERNAME": "user",
        "AGRAPH_PASSWORD": "pass",
    },
)
@patch("requests.Session", return_value=DummySession())
def test_init_and_context_management(mock_session):
    """Test AllegroGraphRESTClient initialization and context management."""
    client = ag_mod.AllegroGraphRESTClient()
    assert client.repo_url == "http://repo"
    assert client.username == "user"
    assert client.password == "pass"
    with client as c:
        assert c is client


@patch.dict(
    os.environ,
    {
        "AGRAPH_CLOUD_URL": "http://repo",
        "AGRAPH_USERNAME": "user",
        "AGRAPH_PASSWORD": "pass",
    },
)
@patch("requests.Session", return_value=DummySession())
def test_upload_ttl_file_success(mock_session, tmp_path):
    """Test upload_ttl_file returns True on success."""
    client = ag_mod.AllegroGraphRESTClient()
    file_path = tmp_path / "test.ttl"
    file_path.write_text("@prefix : <#> .")
    assert client.upload_ttl_file(str(file_path)) is True


@patch.dict(
    os.environ,
    {
        "AGRAPH_CLOUD_URL": "http://repo",
        "AGRAPH_USERNAME": "user",
        "AGRAPH_PASSWORD": "pass",
    },
)
@patch("requests.Session", return_value=DummySession())
def test_upload_ttl_file_file_not_found(mock_session):
    """Test upload_ttl_file returns False if file does not exist."""
    client = ag_mod.AllegroGraphRESTClient()
    assert client.upload_ttl_file("/nonexistent/file.ttl") is False


@patch.dict(
    os.environ,
    {
        "AGRAPH_CLOUD_URL": "http://repo",
        "AGRAPH_USERNAME": "user",
        "AGRAPH_PASSWORD": "pass",
    },
)
@patch("requests.Session", return_value=DummySession())
def test_upload_ttl_file_http_error(mock_session, tmp_path):
    """Test upload_ttl_file returns False on HTTP error."""
    client = ag_mod.AllegroGraphRESTClient()
    file_path = tmp_path / "test.ttl"
    file_path.write_text("@prefix : <#> .")

    # Patch session.post to raise HTTPError
    def bad_post(*a, **kw):
        resp = MagicMock()
        resp.raise_for_status.side_effect = ag_mod.requests.exceptions.HTTPError(
            response=resp
        )
        return resp

    client.session.post = bad_post
    assert client.upload_ttl_file(str(file_path)) is False


@patch.dict(
    os.environ,
    {
        "AGRAPH_CLOUD_URL": "http://repo",
        "AGRAPH_USERNAME": "user",
        "AGRAPH_PASSWORD": "pass",
    },
)
@patch("requests.Session", return_value=DummySession())
def test_test_connection_success(mock_session):
    """Test test_connection returns status code and text on success."""
    client = ag_mod.AllegroGraphRESTClient()
    code, text = client.test_connection()
    assert code == 200
    assert text == "ok"


@patch.dict(
    os.environ,
    {
        "AGRAPH_CLOUD_URL": "http://repo",
        "AGRAPH_USERNAME": "user",
        "AGRAPH_PASSWORD": "pass",
    },
)
@patch("requests.Session", return_value=DummySession())
def test_test_connection_failure(mock_session):
    """Test test_connection returns None and error string on failure."""
    client = ag_mod.AllegroGraphRESTClient()

    def bad_get(*a, **kw):
        raise Exception("fail")

    client.session.get = bad_get
    code, text = client.test_connection()
    assert code is None
    assert "fail" in text


@patch.dict(
    os.environ,
    {
        "AGRAPH_CLOUD_URL": "http://repo",
        "AGRAPH_USERNAME": "user",
        "AGRAPH_PASSWORD": "pass",
    },
)
def test_init_missing_env():
    """Test AllegroGraphRESTClient raises ValueError if env vars are missing."""
    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(ValueError):
            ag_mod.AllegroGraphRESTClient()
