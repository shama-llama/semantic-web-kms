import json
import re
import tempfile

from app.extraction.utils import classification_utils


class DummyOntology:
    def get_class(self, class_name):
        return f"http://example.org/{class_name}"


def test_is_ignored():
    pats = [re.compile(r".*\.py$"), re.compile(r"ignore_me")]
    assert classification_utils.is_ignored("foo.py", pats)
    assert classification_utils.is_ignored("ignore_me.txt", pats)
    assert not classification_utils.is_ignored("bar.txt", pats)


def test_load_classifiers_from_json():
    data = {
        "classifiers": [
            {"class": "Code", "regex": r".*\.py$"},
            {"class": "Text", "regex": r".*\.txt$"},
        ],
        "ignore_patterns": [r"ignore_me"],
    }
    with tempfile.NamedTemporaryFile(mode="w+", delete=False) as tmp:
        json.dump(data, tmp)
        tmp_path = tmp.name
    try:
        classifiers, ignore_patterns = classification_utils.load_classifiers_from_json(
            tmp_path
        )
        assert len(classifiers) == 2
        assert classifiers[0][0] == "Code"
        assert classifiers[1][0] == "Text"
        assert any(pat.search("ignore_me.txt") for pat in ignore_patterns)
    finally:
        import os

        os.remove(tmp_path)


def test_classify_file():
    classifiers = [
        ("Code", re.compile(r".*\.py$")),
        ("Text", re.compile(r".*\.txt$")),
    ]
    ignore_patterns = [re.compile(r"ignore_me")]
    ontology = DummyOntology()
    # Ignored file
    result = classification_utils.classify_file(
        "ignore_me.txt", classifiers, ignore_patterns, ontology
    )
    assert result == (None, None, "ignored")
    # Code file (no ignore_patterns for .py)
    result = classification_utils.classify_file("foo.py", classifiers, [], ontology)
    assert result == ("Code", "http://example.org/Code", "high")
    # Text file with ontology_class_cache
    result = classification_utils.classify_file(
        "bar.txt", classifiers, [], ontology, ontology_class_cache={"Text"}
    )
    assert result == ("Text", "http://example.org/Text", "high")
    # No match, use default_class
    result = classification_utils.classify_file(
        "unknown.xyz", classifiers, [], ontology, default_class="Text"
    )
    assert result == ("Text", "http://example.org/Text", "low")
    # No match, no default
    result = classification_utils.classify_file(
        "unknown.xyz", classifiers, [], ontology
    )
    assert result == (None, None, "unknown")
