import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import pytest
import ast
from app.extraction import code_extractor
import types
from unittest import mock
import tempfile
import shutil
import io
from unittest.mock import patch, MagicMock
from rdflib import Graph, URIRef
import glob

def test_extract_python_entities_class_and_function():
    code = '''
class Foo:
    def bar(self, x):
        return x + 1

def baz(y):
    return y * 2
'''
    tree = ast.parse(code)
    summary = {}
    code_extractor.extract_python_entities(tree, summary)
    # Check class extraction
    assert any(cls["name"] == "Foo" for cls in summary.get("classes", []))
    # Check function extraction
    assert any(func["name"] == "baz" for func in summary.get("functions", []))
    # Check method extraction
    assert any(method["name"] == "bar" for method in summary.get("methods", []))

def test_extract_python_entities_imports():
    code = 'import os\nfrom sys import path\n'
    node = ast.parse(code)
    summary = {}
    code_extractor.extract_python_entities(node, summary)
    assert any('import' in i['raw'] for i in summary['imports'])

def test_extract_python_entities_imports_case():
    code = 'import os\nfrom sys import path\n'
    node = ast.parse(code)
    summary = {}
    code_extractor.extract_python_entities(node, summary)
    assert any('import' in i['raw'] for i in summary['imports'])

def test_extract_tree_sitter_entities_basic():
    # Mock tree-sitter language and query
    fake_node = types.SimpleNamespace(start_byte=0, end_byte=5, start_point=(0,0), end_point=(0,0))
    fake_query = mock.Mock()
    fake_query.captures.return_value = [(fake_node, 'class')]
    fake_language = mock.Mock()
    fake_language.query.return_value = fake_query
    with mock.patch('app.extraction.code_extractor.get_language', return_value=fake_language):
        summary = {}
        code_extractor.extract_tree_sitter_entities('python', mock.Mock(), b'class X:', {'python': {'test': ['query']}}, summary)
        assert 'classes' in summary and summary['classes'][0]['raw'] == 'class'

def test_extract_tree_sitter_language_not_found():
    with mock.patch('app.extraction.code_extractor.get_language', return_value=None):
        summary = {}
        code_extractor.extract_tree_sitter_entities('unknown', mock.Mock(), b'', {}, summary)
        assert summary == {}

def test_extract_tree_sitter_unknown_capture():
    fake_node = types.SimpleNamespace(start_byte=0, end_byte=5, start_point=(0,0), end_point=(0,0))
    fake_query = mock.Mock()
    fake_query.captures.return_value = [(fake_node, 'unknown_capture')]
    fake_language = mock.Mock()
    fake_language.query.return_value = fake_query
    with mock.patch('app.extraction.code_extractor.get_language', return_value=fake_language):
        summary = {}
        code_extractor.extract_tree_sitter_entities('python', mock.Mock(), b'class X:', {'python': {'test': ['query']}}, summary)
        assert summary == {}

def test_extract_tree_sitter_query_exception():
    fake_language = mock.Mock()
    fake_language.query.side_effect = Exception('fail')
    with mock.patch('app.extraction.code_extractor.get_language', return_value=fake_language):
        summary = {}
        code_extractor.extract_tree_sitter_entities('python', mock.Mock(), b'class X:', {'python': {'test': ['query']}}, summary)
        assert summary == {}

def test_extract_python_entities_annassign():
    code = 'x: int = 5'
    node = ast.parse(code)
    summary = {}
    code_extractor.extract_python_entities(node, summary)
    # Should not error, and variables/types should be present
    assert 'variables' in summary or 'fields' in summary

def test_extract_python_entities_assign():
    code = 'x = 42'
    node = ast.parse(code)
    summary = {}
    code_extractor.extract_python_entities(node, summary)
    assert 'variables' in summary

def test_extract_python_entities_call():
    code = 'def foo():\n    print("hi")\n    bar()'
    node = ast.parse(code)
    summary = {}
    code_extractor.extract_python_entities(node, summary)
    assert 'print' in summary.get('calls', []) and 'bar' in summary.get('calls', [])

def test_extract_python_entities_importfrom_none():
    node = ast.ImportFrom(module=None, names=[ast.alias(name='foo')], level=0)
    summary = {}
    code_extractor.extract_python_entities(node, summary)
    assert any('from .' in i['raw'] for i in summary['imports'])

def test_extract_python_entities_recurse():
    class Dummy(ast.AST):
        _fields = ('children',)
        def __init__(self):
            self.children = [ast.Pass()]
    node = Dummy()
    summary = {}
    code_extractor.extract_python_entities(node, summary)
    # Should not error, and summary should still be a dict
    assert isinstance(summary, dict)

# Helper to create a valid excluded directories file

def make_excluded_dirs_file():
    fd, path = tempfile.mkstemp()
    with open(path, 'w') as f:
        f.write('[]')
    return path

# --- UNIT TESTS FOR main() ---
def make_temp_repo_with_file(ext, content):
    temp_dir = tempfile.mkdtemp()
    repo_dir = os.path.join(temp_dir, "repo1")
    os.makedirs(repo_dir)
    file_path = os.path.join(repo_dir, f"file{ext}")
    with open(file_path, "w") as f:
        f.write(content)
    return temp_dir, repo_dir, file_path

def test_main_no_supported_files(monkeypatch):
    temp_dir = tempfile.mkdtemp()
    excl_path = make_excluded_dirs_file()
    monkeypatch.setattr("app.extraction.code_extractor.get_input_path", lambda _: temp_dir)
    monkeypatch.setattr("app.extraction.code_extractor.language_mapping", {".py": "python"})
    monkeypatch.setattr("app.extraction.code_extractor.get_excluded_directories_path", lambda: excl_path)
    monkeypatch.setattr("app.extraction.code_extractor.get_ontology_cache", MagicMock())
    monkeypatch.setattr("app.extraction.code_extractor.get_code_extraction_properties", MagicMock(return_value=[]))
    monkeypatch.setattr("app.extraction.code_extractor.get_code_extraction_classes", MagicMock(return_value=[]))
    monkeypatch.setattr("app.extraction.code_extractor.get_output_path", lambda x: tempfile.mkstemp()[1])
    with patch("rich.console.Console.print"):
        code_extractor.main()
    shutil.rmtree(temp_dir)
    os.remove(excl_path)

def test_main_unreadable_file(monkeypatch):
    temp_dir, repo_dir, file_path = make_temp_repo_with_file(".py", "print('hi')")
    excl_path = make_excluded_dirs_file()
    monkeypatch.setattr("app.extraction.code_extractor.get_input_path", lambda _: temp_dir)
    monkeypatch.setattr("app.extraction.code_extractor.language_mapping", {".py": "python"})
    monkeypatch.setattr("app.extraction.code_extractor.get_excluded_directories_path", lambda: excl_path)
    monkeypatch.setattr("app.extraction.code_extractor.get_ontology_cache", MagicMock())
    monkeypatch.setattr("app.extraction.code_extractor.get_code_extraction_properties", MagicMock(return_value=[]))
    monkeypatch.setattr("app.extraction.code_extractor.get_code_extraction_classes", MagicMock(return_value=[]))
    monkeypatch.setattr("app.extraction.code_extractor.get_output_path", lambda x: tempfile.mkstemp()[1])
    with patch("rich.console.Console.print"):
        code_extractor.main()
    # Check that the output TTL file was not created
    assert not glob.glob(os.path.join(repo_dir, "*.ttl"))
    shutil.rmtree(temp_dir)
    os.remove(excl_path)

def test_code_extractor_ttl_creation(monkeypatch):
    import tempfile
    import os
    from unittest.mock import MagicMock, patch
    from rdflib import URIRef
    temp_dir = tempfile.mkdtemp()
    repo_dir = os.path.join(temp_dir, "repo1")
    os.makedirs(repo_dir)
    file_path = os.path.join(repo_dir, "file.py")
    with open(file_path, "w") as f:
        f.write("class A: pass\n")
    excl_path = os.path.join(temp_dir, "excluded.json")
    with open(excl_path, "w") as f:
        f.write("[]")
    ttl_path = os.path.join(temp_dir, "out.ttl")
    def get_output_path_patch(filename):
        if filename == "web_development_ontology.ttl":
            return ttl_path
        return os.path.join(temp_dir, filename)
    monkeypatch.setattr("app.extraction.code_extractor.get_input_path", lambda _: temp_dir)
    monkeypatch.setattr("app.extraction.code_extractor.language_mapping", {".py": "python"})
    monkeypatch.setattr("app.extraction.code_extractor.get_excluded_directories_path", lambda: excl_path)
    monkeypatch.setattr("app.extraction.code_extractor.get_code_extraction_properties", lambda: "mocked")
    monkeypatch.setattr("app.extraction.code_extractor.get_code_extraction_classes", lambda: "mocked")
    monkeypatch.setattr("app.extraction.code_extractor.get_output_path", get_output_path_patch)
    prop_keys = [
        "isElementOf", "hasSimpleName", "startsAtLine", "endsAtLine", "hasDecorator", "hasMethod",
        "hasFile", "hasTextValue", "hasType", "hasParameter", "declaresVariable", "invokes", "hasReturnType", "hasField", "extendsType"
    ]
    class_keys = [
        "ClassDefinition", "FunctionDefinition", "AttributeDeclaration", "Parameter", "VariableDeclaration", "Decorator", "Type", "ImportDeclaration", "FunctionCallSite"
    ]
    fake_prop_cache = {k: URIRef(f"http://example.org/{k}") for k in prop_keys}
    fake_class_cache = {k: URIRef(f"http://example.org/{k}") for k in class_keys}
    fake_cache = MagicMock()
    fake_cache.get_property_cache.return_value = fake_prop_cache
    fake_cache.get_class_cache.return_value = fake_class_cache
    monkeypatch.setattr("app.extraction.code_extractor.get_ontology_cache", lambda: fake_cache)
    with patch("rich.console.Console.print"):
        code_extractor.main()
    assert os.path.exists(ttl_path), f"TTL file was not created: {ttl_path}"
    # Clean up
    import shutil
    shutil.rmtree(temp_dir)