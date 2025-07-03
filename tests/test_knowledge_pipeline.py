import sys
import types
import pytest
from unittest import mock

import app.knowledge_pipeline as kp


def test_run_cmd_success():
    with mock.patch('subprocess.run', return_value=types.SimpleNamespace(returncode=0)) as m:
        kp.run_cmd([sys.executable, '--version'], 'Test')
        m.assert_called_once()

def test_run_cmd_failure():
    with mock.patch('subprocess.run', return_value=types.SimpleNamespace(returncode=1)):
        with pytest.raises(SystemExit):
            kp.run_cmd([sys.executable, '--badflag'], 'TestFail')

def test_upload_ttl_to_allegrograph_success():
    mock_client = mock.MagicMock()
    mock_client.upload_ttl_file.return_value = True
    mock_ctx = mock.MagicMock()
    mock_ctx.__enter__.return_value = mock_client
    with mock.patch('app.knowledge_pipeline.AllegroGraphRESTClient', return_value=mock_ctx):
        kp.upload_ttl_to_allegrograph('fake.ttl')
        mock_client.upload_ttl_file.assert_called_once_with('fake.ttl')

def test_upload_ttl_to_allegrograph_failure():
    mock_client = mock.MagicMock()
    mock_client.upload_ttl_file.return_value = False
    mock_ctx = mock.MagicMock()
    mock_ctx.__enter__.return_value = mock_client
    with mock.patch('app.knowledge_pipeline.AllegroGraphRESTClient', return_value=mock_ctx):
        with pytest.raises(SystemExit):
            kp.upload_ttl_to_allegrograph('fake.ttl')

def test_main_success():
    with mock.patch('app.knowledge_pipeline.run_cmd') as m_run, \
         mock.patch('app.knowledge_pipeline.upload_ttl_to_allegrograph') as m_upload:
        kp.main()
        assert m_run.call_count == 2
        m_upload.assert_called_once()

def test_main_extraction_fail():
    with mock.patch('app.knowledge_pipeline.run_cmd', side_effect=[SystemExit(1)]):
        with pytest.raises(SystemExit):
            kp.main()

def test_main_annotation_fail():
    # Extraction succeeds, annotation fails
    with mock.patch('app.knowledge_pipeline.run_cmd', side_effect=[None, SystemExit(1)]):
        with pytest.raises(SystemExit):
            kp.main()

def test_main_upload_fail():
    with mock.patch('app.knowledge_pipeline.run_cmd'), \
         mock.patch('app.knowledge_pipeline.upload_ttl_to_allegrograph', side_effect=SystemExit(1)):
        with pytest.raises(SystemExit):
            kp.main() 