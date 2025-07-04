import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import pytest
from app.extraction import main_extractor
from rich.console import Console

class DummyExtractor:
    def __init__(self, should_fail=False):
        self.should_fail = should_fail
        self.called = False
    def main(self):
        self.called = True
        if self.should_fail:
            raise Exception("Dummy failure")

def test_extraction_result():
    result = main_extractor.ExtractionResult("Test", True)
    assert result.name == "Test"
    assert result.success is True
    assert result.error is None
    result2 = main_extractor.ExtractionResult("Test2", False, "error")
    assert result2.success is False
    assert result2.error == "error"

def test_run_extractor_success():
    dummy = DummyExtractor()
    console = Console(file=open(os.devnull, 'w'))
    result = main_extractor.run_extractor("Dummy", dummy, console)
    assert result.success is True
    assert dummy.called is True

def test_run_extractor_failure():
    dummy = DummyExtractor(should_fail=True)
    console = Console(file=open(os.devnull, 'w'))
    result = main_extractor.run_extractor("DummyFail", dummy, console)
    assert result.success is False
    assert dummy.called is True
    assert "Dummy failure" in (result.error or "") 