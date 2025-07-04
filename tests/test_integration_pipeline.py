import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import pytest
from unittest.mock import patch, MagicMock
from app.extraction import main_extractor

@patch("app.extraction.file_extractor.main", return_value=None)
@patch("app.extraction.code_extractor.main", return_value=None)
@patch("app.extraction.doc_extractor.main", return_value=None)
@patch("app.extraction.git_extractor.main", return_value=None)
@patch("sys.exit")
def test_extraction_pipeline(mock_exit, mock_git, mock_doc, mock_code, mock_file):
    # Patch Console.print to suppress output
    with patch("rich.console.Console.print", return_value=None):
        # Run the pipeline
        main_extractor.main()
        # Check that each extractor's main was called
        assert mock_file.called
        assert mock_code.called
        assert mock_doc.called
        assert mock_git.called
        # Check that sys.exit was called (pipeline completes)
        assert mock_exit.called 