import os
import tempfile
import json
import pytest
from app.extraction.file_extractor import OntologyDrivenExtractor
from app.core.paths import get_web_dev_ontology_path

def extractor():
    ontology_path = get_web_dev_ontology_path()
    return OntologyDrivenExtractor(ontology_path)

def test_categorize_python_file():
    result = extractor().categorize_file('/tmp/fake.py', 'fake.py')
    assert result["ontology_class"] == "ScriptFile"
    assert result["confidence"] == "high"
    assert "ScriptFile" in result["description"]

def test_categorize_javascript_file():
    result = extractor().categorize_file('/tmp/fake.js', 'fake.js')
    assert result["ontology_class"] in ("ScriptFile", "JavaScriptCode", "SourceCodeFile")
    assert result["confidence"] == "high"

def test_categorize_html_file():
    result = extractor().categorize_file('/tmp/fake.html', 'fake.html')
    assert result["ontology_class"] in ("MarkupFile", "HTMLCode")
    assert result["confidence"] == "high"

def test_categorize_css_file():
    result = extractor().categorize_file('/tmp/fake.css', 'fake.css')
    assert result["ontology_class"] in ("StylesheetFile", "CSSCode")
    assert result["confidence"] == "high"

def test_categorize_json_file():
    result = extractor().categorize_file('/tmp/fake.json', 'fake.json')
    assert result["ontology_class"] in ("ConfigurationFile", "JSON")
    assert result["confidence"] == "high"

def test_categorize_markdown_file():
    result = extractor().categorize_file('/tmp/fake.md', 'fake.md')
    assert result["ontology_class"] in ("DocumentationFile", "MarkupFile")
    assert result["confidence"] == "high"

def test_categorize_test_file():
    result = extractor().categorize_file('/tmp/test_example.test.py', 'test_example.test.py')
    assert result["ontology_class"] == "TestFile"
    assert result["confidence"] == "high"

def test_categorize_dockerfile():
    result = extractor().categorize_file('/tmp/Dockerfile', 'Dockerfile')
    assert result["ontology_class"] == "Dockerfile"
    assert result["confidence"] == "high"

def test_categorize_build_file():
    result = extractor().categorize_file('/tmp/Makefile', 'Makefile')
    assert result["ontology_class"] == "BuildFile"
    assert result["confidence"] == "high"

def test_categorize_sqlite_file():
    result = extractor().categorize_file('/tmp/fake.sqlite', 'fake.sqlite')
    assert result["ontology_class"] == "DatabaseSchemaFile"
    assert result["confidence"] == "high"

def test_categorize_image_file():
    result = extractor().categorize_file('/tmp/fake.png', 'fake.png')
    assert result["ontology_class"] == "ImageFile"
    assert result["confidence"] == "high"

def test_categorize_license_file():
    result = extractor().categorize_file('/tmp/LICENSE', 'LICENSE')
    assert result["ontology_class"] == "LicenseFile"
    assert result["confidence"] == "high"
    assert "LicenseFile" in result["description"]

def test_categorize_unknown_file():
    result = extractor().categorize_file('/tmp/fake.unknown', 'fake.unknown')
    assert result["ontology_class"] == "DigitalInformationCarrier"
    assert result["confidence"] == "low" 