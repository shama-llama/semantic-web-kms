import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

import app.extraction.main_extractor as me


def test_pipeline_main_success(monkeypatch, tmp_path):
    # Create a minimal input directory with a dummy file
    repo_dir = tmp_path / "repo1"
    repo_dir.mkdir()
    (repo_dir / "file1.py").write_text("print('hello')\n")
    # Patch extractors to simulate success
    monkeypatch.setattr(me, "file_extractor", MagicMock())
    monkeypatch.setattr(me, "content_extractor", MagicMock())
    monkeypatch.setattr(me, "code_extractor", MagicMock())
    monkeypatch.setattr(me, "doc_extractor", MagicMock())
    monkeypatch.setattr(me, "git_extractor", MagicMock())
    monkeypatch.setattr(
        me, "run_extractor", lambda *a, **kw: me.ExtractionResult("X", True)
    )
    monkeypatch.setattr(me, "display_summary", lambda *a, **kw: None)
    with patch.object(sys, "exit") as mock_exit:
        me.main(str(tmp_path))
        mock_exit.assert_called_once_with(0)
