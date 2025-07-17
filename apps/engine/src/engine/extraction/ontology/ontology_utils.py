"""Ontology utility functions for fallback URIs and type checks."""

from rdflib import URIRef

from app.core.namespaces import WDO


def get_property_fallback(prop_name: str) -> URIRef:
    """
    Return a fallback WDO property URI for a missing property name.

    Args:
        prop_name: Name of the property.
    Returns:
        URIRef for the fallback property.
    """
    return WDO[prop_name]


def get_class_fallback(class_name: str) -> URIRef:
    """
    Return a fallback WDO class URI for a missing class name.

    Args:
        class_name: Name of the class.
    Returns:
        URIRef for the fallback class.
    """
    return WDO[class_name]


def _is_complex_type(class_name: str) -> bool:
    """
    Return True if class_name is a complex type in the ontology.

    Args:
        class_name: Name of the class.
    Returns:
        True if complex type, else False.
    """
    return class_name in {
        "ComplexType",
        "ClassDefinition",
        "EnumDefinition",
        "InterfaceDefinition",
        "StructDefinition",
        "TraitDefinition",
    }


def _is_code_construct(class_name: str) -> bool:
    """
    Return True if class_name is a code construct in the ontology.

    Args:
        class_name: Name of the class.
    Returns:
        True if code construct, else False.
    """
    return class_name in {
        "CodeConstruct",
        "AttributeDeclaration",
        "FunctionCallSite",
        "FunctionDefinition",
        "ImportDeclaration",
        "Parameter",
        "TypeDeclaration",
        "VariableDeclaration",
    }


def _is_type_declaration(class_name: str) -> bool:
    """
    Return True if class_name is a type declaration in the ontology.

    Args:
        class_name: Name of the class.
    Returns:
        True if type declaration, else False.
    """
    return class_name in {
        "TypeDeclaration",
        "ComplexType",
        "PrimitiveType",
        "ClassDefinition",
        "EnumDefinition",
        "InterfaceDefinition",
        "PackageDeclaration",
        "StructDefinition",
        "TraitDefinition",
    }


def _is_attribute_declaration(class_name: str) -> bool:
    """
    Return True if class_name is an attribute declaration in the ontology.

    Args:
        class_name: Name of the class.
    Returns:
        True if attribute declaration, else False.
    """
    return class_name == "AttributeDeclaration"
