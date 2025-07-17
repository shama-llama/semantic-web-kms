import sys
from unittest.mock import MagicMock, patch

import pytest

import app.extraction.main_extractor as me


def test_extraction_result_repr_and_str():
    result_success = me.ExtractionResult("TestExtractor", True)
    result_fail = me.ExtractionResult("TestExtractor", False, "Some error")
    assert "PASSED" in str(result_success)
    assert "FAILED" in str(result_fail)
    assert "ExtractionResult" in repr(result_success)
    assert "ExtractionResult" in repr(result_fail)


def test_run_extractor_success():
    mock_module = MagicMock()
    mock_module.main = MagicMock()
    mock_console = MagicMock()
    result = me.run_extractor(
        "MockExtractor", mock_module, mock_console, input_dir="/tmp"
    )
    assert result.success is True
    mock_module.main.assert_called()
    mock_console.print.assert_any_call(
        "[bold blue]Running MockExtractor...[/bold blue]"
    )


def test_run_extractor_no_main():
    mock_module = MagicMock()
    del mock_module.main
    mock_console = MagicMock()
    result = me.run_extractor("NoMainExtractor", mock_module, mock_console)
    assert result.success is False
    assert result.error is not None and "does not have a main() method" in result.error


def test_run_extractor_exception():
    mock_module = MagicMock()
    mock_module.main.side_effect = Exception("Boom!")
    mock_console = MagicMock()
    result = me.run_extractor("FailExtractor", mock_module, mock_console)
    assert result.success is False
    assert result.error is not None and "Boom!" in result.error


def test_display_summary_all_passes():
    mock_console = MagicMock()
    results = [me.ExtractionResult("A", True), me.ExtractionResult("B", True)]
    me.display_summary(results, mock_console)
    # Should print a green panel for success
    assert mock_console.print.call_count > 0


def test_display_summary_some_fail():
    mock_console = MagicMock()
    results = [me.ExtractionResult("A", True), me.ExtractionResult("B", False, "fail")]
    me.display_summary(results, mock_console)
    # Should print a red panel for failure
    assert mock_console.print.call_count > 0


def test_main_all_success(monkeypatch):
    # Patch run_extractor to always succeed
    monkeypatch.setattr(
        me, "run_extractor", lambda *a, **kw: me.ExtractionResult("X", True)
    )
    monkeypatch.setattr(me, "display_summary", lambda *a, **kw: None)
    monkeypatch.setattr(me, "file_extractor", MagicMock())
    monkeypatch.setattr(me, "content_extractor", MagicMock())
    monkeypatch.setattr(me, "code_extractor", MagicMock())
    monkeypatch.setattr(me, "doc_extractor", MagicMock())
    monkeypatch.setattr(me, "git_extractor", MagicMock())
    with patch.object(sys, "exit") as mock_exit:
        me.main("/tmp")
        mock_exit.assert_called_once_with(0)


def test_main_some_fail(monkeypatch):
    # Patch run_extractor to fail for one extractor
    calls = [
        me.ExtractionResult("X", True),
        me.ExtractionResult("Y", False, "fail"),
        me.ExtractionResult("Z", True),
        me.ExtractionResult("W", True),
        me.ExtractionResult("V", True),
    ]

    def fake_run_extractor(*a, **kw):
        return calls.pop(0)

    monkeypatch.setattr(me, "run_extractor", fake_run_extractor)
    monkeypatch.setattr(me, "display_summary", lambda *a, **kw: None)
    monkeypatch.setattr(me, "file_extractor", MagicMock())
    monkeypatch.setattr(me, "content_extractor", MagicMock())
    monkeypatch.setattr(me, "code_extractor", MagicMock())
    monkeypatch.setattr(me, "doc_extractor", MagicMock())
    monkeypatch.setattr(me, "git_extractor", MagicMock())
    with patch.object(sys, "exit") as mock_exit:
        me.main("/tmp")
        mock_exit.assert_called_once_with(1)
