import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import pytest
from app.extraction import doc_extractor

def test_get_doc_type():
    assert doc_extractor.get_doc_type("README.md") == "Readme"
    assert doc_extractor.get_doc_type("contributing.txt") == "ContributionGuide"
    assert doc_extractor.get_doc_type("changelog.rst") == "Changelog"
    assert doc_extractor.get_doc_type("adr.md") == "ArchitecturalDecisionRecord"
    assert doc_extractor.get_doc_type("user_guide.md") == "UserGuide"
    assert doc_extractor.get_doc_type("guide.md") == "Guide"
    assert doc_extractor.get_doc_type("tutorial.md") == "Tutorial"
    assert doc_extractor.get_doc_type("best_practice.md") == "BestPracticeGuideline"
    assert doc_extractor.get_doc_type("api.md") == "APIDocumentation"
    assert doc_extractor.get_doc_type("license.txt") == "License"
    assert doc_extractor.get_doc_type("random.txt") == "Documentation"

def test_extract_python_comments():
    code = '''
# This is a comment
def foo():
    """Docstring for foo"""
    pass
'''
    comments = doc_extractor.extract_python_comments(code)
    raw_comments = [c["raw"] for c in comments]
    assert "This is a comment" in raw_comments
    assert "Docstring for foo" in raw_comments

def test_extract_code_comments_python():
    code = '''
# Top comment
def bar():
    """Bar docstring"""
    pass
'''
    comments = doc_extractor.extract_code_comments(code, ".py")
    raw_comments = [c["raw"] for c in comments]
    assert "Top comment" in raw_comments
    assert "Bar docstring" in raw_comments

def test_extract_code_comments_js():
    code = '''
// JS single line comment
/* Multi-line\ncomment */
function baz() {}
'''
    comments = doc_extractor.extract_code_comments(code, ".js")
    raw_comments = [c["raw"] for c in comments]
    assert "JS single line comment" in raw_comments
    assert "Multi-line\ncomment" in raw_comments

def test_get_doc_type_variants():
    assert doc_extractor.get_doc_type('README.md') == 'Readme'
    assert doc_extractor.get_doc_type('CONTRIBUTING.txt') == 'ContributionGuide'
    assert doc_extractor.get_doc_type('CHANGELOG.md') == 'Changelog'
    assert doc_extractor.get_doc_type('ADR.md') == 'ArchitecturalDecisionRecord'
    assert doc_extractor.get_doc_type('user_guide.md') == 'UserGuide'
    assert doc_extractor.get_doc_type('guide.md') == 'Guide'
    assert doc_extractor.get_doc_type('tutorial.md') == 'Tutorial'
    assert doc_extractor.get_doc_type('best_practice.md') == 'BestPracticeGuideline'
    assert doc_extractor.get_doc_type('api.md') == 'APIDocumentation'
    assert doc_extractor.get_doc_type('LICENSE') == 'License'
    assert doc_extractor.get_doc_type('other.md') == 'Documentation'

def test_extract_python_comments_and_docstrings():
    code = '# comment\n"""docstring"""\ndef foo():\n    """func doc"""\n    pass\n'
    comments = doc_extractor.extract_python_comments(code)
    assert any('docstring' in c['raw'] for c in comments)
    assert any('func doc' in c['raw'] for c in comments)
    assert any('comment' in c['raw'] for c in comments)

def test_extract_code_comments_various():
    py_code = '# pycomment\n'
    js_code = '// jscomment\n/* block comment */'
    comments_py = doc_extractor.extract_code_comments(py_code, '.py')
    comments_js = doc_extractor.extract_code_comments(js_code, '.js')
    assert any('pycomment' in c['raw'] for c in comments_py)
    assert any('jscomment' in c['raw'] for c in comments_js)
    assert any('block comment' in c['raw'] for c in comments_js) 