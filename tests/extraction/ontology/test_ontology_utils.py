import pytest
from rdflib import URIRef

from app.extraction.ontology import ontology_utils

# Test get_property_fallback and get_class_fallback


def test_get_property_fallback():
    uri = ontology_utils.get_property_fallback("hasTestProperty")
    assert isinstance(uri, URIRef)
    assert "hasTestProperty" in str(uri)


def test_get_class_fallback():
    uri = ontology_utils.get_class_fallback("TestClass")
    assert isinstance(uri, URIRef)
    assert "TestClass" in str(uri)


# Test _is_complex_type
@pytest.mark.parametrize(
    "class_name,expected",
    [
        ("ComplexType", True),
        ("ClassDefinition", True),
        ("EnumDefinition", True),
        ("InterfaceDefinition", True),
        ("StructDefinition", True),
        ("TraitDefinition", True),
        ("Other", False),
    ],
)
def test_is_complex_type(class_name, expected):
    assert ontology_utils._is_complex_type(class_name) == expected


# Test _is_code_construct
@pytest.mark.parametrize(
    "class_name,expected",
    [
        ("CodeConstruct", True),
        ("AttributeDeclaration", True),
        ("FunctionCallSite", True),
        ("FunctionDefinition", True),
        ("ImportDeclaration", True),
        ("Parameter", True),
        ("TypeDeclaration", True),
        ("VariableDeclaration", True),
        ("Other", False),
    ],
)
def test_is_code_construct(class_name, expected):
    assert ontology_utils._is_code_construct(class_name) == expected


# Test _is_type_declaration
@pytest.mark.parametrize(
    "class_name,expected",
    [
        ("TypeDeclaration", True),
        ("ComplexType", True),
        ("PrimitiveType", True),
        ("ClassDefinition", True),
        ("EnumDefinition", True),
        ("InterfaceDefinition", True),
        ("PackageDeclaration", True),
        ("StructDefinition", True),
        ("TraitDefinition", True),
        ("Other", False),
    ],
)
def test_is_type_declaration(class_name, expected):
    assert ontology_utils._is_type_declaration(class_name) == expected


# Test _is_attribute_declaration
@pytest.mark.parametrize(
    "class_name,expected",
    [
        ("AttributeDeclaration", True),
        ("Other", False),
    ],
)
def test_is_attribute_declaration(class_name, expected):
    assert ontology_utils._is_attribute_declaration(class_name) == expected
