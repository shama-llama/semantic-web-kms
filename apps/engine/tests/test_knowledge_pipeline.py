import sys
from unittest.mock import MagicMock, patch

import pytest

import app.knowledge_pipeline as kp


def test_run_cmd_success():
    """Test run_cmd completes successfully when subprocess returns 0."""
    with patch("subprocess.run", return_value=MagicMock(returncode=0)) as mock_run:
        kp.run_cmd(["echo", "hi"], "Echo Test")
        mock_run.assert_called_once()


def test_run_cmd_failure():
    """Test run_cmd exits if subprocess returns non-zero."""
    with patch("subprocess.run", return_value=MagicMock(returncode=1)):
        with patch("sys.exit") as mock_exit:
            kp.run_cmd(["fail"], "Fail Test")
            mock_exit.assert_called_once_with(1)


def test_upload_ttl_to_allegrograph_success():
    """Test upload_ttl_to_allegrograph succeeds when upload returns True."""
    mock_client = MagicMock()
    mock_client.upload_ttl_file.return_value = True
    mock_client.__enter__.return_value = mock_client
    with patch(
        "app.knowledge_pipeline.AllegroGraphRESTClient", return_value=mock_client
    ):
        kp.upload_ttl_to_allegrograph("fake.ttl")
        mock_client.upload_ttl_file.assert_called_once_with("fake.ttl")


def test_upload_ttl_to_allegrograph_failure():
    """Test upload_ttl_to_allegrograph exits if upload fails."""
    mock_client = MagicMock()
    mock_client.upload_ttl_file.return_value = False
    mock_client.__enter__.return_value = mock_client
    with patch(
        "app.knowledge_pipeline.AllegroGraphRESTClient", return_value=mock_client
    ):
        with patch("sys.exit") as mock_exit:
            kp.upload_ttl_to_allegrograph("fail.ttl")
            mock_exit.assert_called_once_with(1)


def test_main_success():
    """Test main runs all steps successfully."""
    with patch(
        "app.knowledge_pipeline.run_extraction_with_progress"
    ) as mock_extraction, patch(
        "app.knowledge_pipeline.run_annotation_with_progress"
    ) as mock_annotation, patch(
        "app.knowledge_pipeline.upload_ttl_to_allegrograph"
    ) as mock_upload, patch(
        "app.knowledge_pipeline.print_pipeline_summary"
    ) as mock_summary:
        kp.main()
        mock_extraction.assert_called_once()
        mock_annotation.assert_called_once()
        mock_upload.assert_called_once_with(kp.TTL_PATH)
        mock_summary.assert_called_once()


def test_main_failure_exits():
    """Test main exits if a step fails."""
    with patch(
        "app.knowledge_pipeline.run_extraction_with_progress",
        side_effect=Exception("Test error"),
    ), patch("app.knowledge_pipeline.upload_ttl_to_allegrograph") as mock_upload:
        with pytest.raises(SystemExit):
            kp.main()
        # Should not call upload if extraction step fails
        mock_upload.assert_not_called()
