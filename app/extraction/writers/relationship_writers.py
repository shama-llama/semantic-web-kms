"""Writers for encoding code construct relationships as RDF triples in the ontology graph."""

from typing import Callable

from rdflib import Graph, Literal, URIRef
from rdflib.namespace import RDFS, XSD


def write_inheritance(g, constructs, class_uris, prop_cache):
    """
    Write inheritance relationships for all entity types, strictly enforcing WDO domain/range.

    Args:
        g: RDFLib Graph to add triples to.
        constructs: Dict of extracted code constructs.
        class_uris: Dict mapping class names to their URIs.
        prop_cache: Dict of ontology property URIs.
    Returns:
        None
    """
    for ext in constructs.get("extends", []):
        sub = ext.get("class")
        sup = ext.get("base")
        if sub and sup and sub in class_uris:
            if sup in class_uris:
                g.add((class_uris[sub], prop_cache["extendsType"], class_uris[sup]))
                g.add((class_uris[sup], prop_cache["isExtendedBy"], class_uris[sub]))
            else:
                parent_uri = URIRef(
                    f"http://semantic-web-kms.edu.et/wdo/external/{sup}"
                )
                g.add((class_uris[sub], prop_cache["extendsType"], parent_uri))


def write_implements_interface(g, constructs, class_uris, interface_uris, prop_cache):
    """
    Write implementsInterface relationships, strictly enforcing WDO domain/range.

    Args:
        g: RDFLib Graph to add triples to.
        constructs: Dict of extracted code constructs.
        class_uris: Dict mapping class names to their URIs.
        interface_uris: Dict mapping interface names to their URIs.
        prop_cache: Dict of ontology property URIs.
    Returns:
        None
    """
    for impl in constructs.get("implements", []):
        cls = impl.get("class")
        iface = impl.get("interface")
        if cls and iface and cls in class_uris and iface in interface_uris:
            g.add(
                (
                    class_uris[cls],
                    prop_cache["implementsInterface"],
                    interface_uris[iface],
                )
            )
            g.add(
                (interface_uris[iface], prop_cache["isImplementedBy"], class_uris[cls])
            )


def write_declaration_usage_relationships(
    g, constructs, file_uri, prop_cache, uri_safe_string
):
    """
    Write declaration-usage relationships between code constructs.

    Args:
        g: RDFLib Graph to add triples to.
        constructs: Dict of extracted code constructs.
        file_uri: URIRef for the file.
        prop_cache: Dict of ontology property URIs.
        uri_safe_string: Function to make URI-safe strings.
    Returns:
        None
    """
    for usage in constructs.get("declaration_usage", {}).get("variable_usages", []):
        declaration = usage.get("declaration")
        usage_name = usage.get("usage")
        if declaration and usage_name:
            decl_uri = URIRef(f"{file_uri}/var/{uri_safe_string(declaration)}")
            usage_uri = URIRef(f"{file_uri}/call/{uri_safe_string(usage_name)}")
            g.add(
                (
                    decl_uri,
                    prop_cache.get("isDeclarationUsedBy", RDFS.seeAlso),
                    usage_uri,
                )
            )
            g.add(
                (usage_uri, prop_cache.get("usesDeclaration", RDFS.seeAlso), decl_uri)
            )
    for usage in constructs.get("declaration_usage", {}).get("function_usages", []):
        usage_name = usage.get("usage")
        if usage_name:
            usage_uri = URIRef(f"{file_uri}/call/{uri_safe_string(usage_name)}")
            for func in constructs.get("functions", []) + constructs.get(
                "FunctionDefinition", []
            ):
                if func.get("name") == usage_name:
                    func_uri = URIRef(
                        f"{file_uri}/function/{uri_safe_string(usage_name)}"
                    )
                    g.add(
                        (
                            usage_uri,
                            prop_cache.get("callsFunction", RDFS.seeAlso),
                            func_uri,
                        )
                    )
                    g.add(
                        (
                            func_uri,
                            prop_cache.get("isCalledByFunctionAt", RDFS.seeAlso),
                            usage_uri,
                        )
                    )
                    break
    for usage in constructs.get("declaration_usage", {}).get("class_usages", []):
        usage_name = usage.get("usage")
        if usage_name:
            usage_uri = URIRef(f"{file_uri}/class/{uri_safe_string(usage_name)}")
            for cls in constructs.get("classes", []) + constructs.get(
                "ClassDefinition", []
            ):
                if cls.get("name") == usage_name:
                    cls_uri = URIRef(f"{file_uri}/class/{uri_safe_string(usage_name)}")
                    g.add(
                        (
                            usage_uri,
                            prop_cache.get("extendsType", RDFS.seeAlso),
                            cls_uri,
                        )
                    )
                    break
    for usage in constructs.get("declaration_usage", {}).get("import_usages", []):
        import_name = usage.get("import")
        if import_name:
            import_uri = URIRef(f"{file_uri}/import/{uri_safe_string(import_name)}")
            for imp in constructs.get("imports", []) + constructs.get(
                "ImportDeclaration", []
            ):
                if import_name in imp.get("raw", ""):
                    g.add(
                        (
                            import_uri,
                            prop_cache.get("imports", RDFS.seeAlso),
                            Literal(import_name, datatype=XSD.string),
                        )
                    )
                    break


def write_access_relationships(g, constructs, file_uri, prop_cache, uri_safe_string):
    """
    Write access relationships between functions and attributes.

    Args:
        g: RDFLib Graph to add triples to.
        constructs: Dict of extracted code constructs.
        file_uri: URIRef for the file.
        prop_cache: Dict of ontology property URIs.
        uri_safe_string: Function to make URI-safe strings.
    Returns:
        None
    """
    for access in constructs.get("access_relationships", []):
        function_name = access.get("function")
        attribute_name = access.get("attribute")
        if function_name and attribute_name:
            func_uri = URIRef(f"{file_uri}/function/{uri_safe_string(function_name)}")
            attr_uri = URIRef(f"{file_uri}/attr/{uri_safe_string(attribute_name)}")
            g.add((func_uri, prop_cache.get("accesses", RDFS.seeAlso), attr_uri))
            g.add((attr_uri, prop_cache.get("isAccessedBy", RDFS.seeAlso), func_uri))


def write_type_relationships(g, constructs, file_uri, prop_cache, uri_safe_string):
    """
    Write hasType relationships between code constructs and their types.

    Args:
        g: RDFLib Graph to add triples to.
        constructs: Dict of extracted code constructs.
        file_uri: URIRef for the file.
        prop_cache: Dict of ontology property URIs.
        uri_safe_string: Function to make URI-safe strings.
    Returns:
        None
    """
    for rel in constructs.get("type_relationships", []):
        construct_name = rel.get("construct")
        type_name = rel.get("type")
        if construct_name and type_name:
            construct_uri = URIRef(
                f"{file_uri}/construct/{uri_safe_string(construct_name)}"
            )
            g.add(
                (
                    construct_uri,
                    prop_cache.get("hasType", RDFS.seeAlso),
                    Literal(type_name, datatype=XSD.string),
                )
            )


def write_embedding_relationships(g, constructs, file_uri, prop_cache, uri_safe_string):
    """
    Write embedsCode relationships between code constructs.

    Args:
        g: RDFLib Graph to add triples to.
        constructs: Dict of extracted code constructs.
        file_uri: URIRef for the file.
        prop_cache: Dict of ontology property URIs.
        uri_safe_string: Function to make URI-safe strings.
    Returns:
        None
    """
    for func in constructs.get("functions", []) + constructs.get(
        "FunctionDefinition", []
    ):
        func_name = func.get("name")
        calls = func.get("calls", [])
        if func_name and calls:
            func_uri = URIRef(f"{file_uri}/function/{uri_safe_string(func_name)}")
            for call in calls:
                call_name = call.get("name", "")
                if call_name:
                    call_uri = URIRef(f"{file_uri}/call/{uri_safe_string(call_name)}")
                    g.add(
                        (func_uri, prop_cache.get("embedsCode", RDFS.seeAlso), call_uri)
                    )
                    g.add(
                        (
                            call_uri,
                            prop_cache.get("isEmbeddedIn", RDFS.seeAlso),
                            func_uri,
                        )
                    )


def write_manipulation_relationships(
    g, constructs, file_uri, prop_cache, uri_safe_string
):
    """
    Write isManipulatedBy/manipulates relationships between code constructs.

    Args:
        g: RDFLib Graph to add triples to.
        constructs: Dict of extracted code constructs.
        file_uri: URIRef for the file.
        prop_cache: Dict of ontology property URIs.
        uri_safe_string: Function to make URI-safe strings.
    Returns:
        None
    """
    for var in constructs.get("variables", []) + constructs.get(
        "VariableDeclaration", []
    ):
        var_name = var.get("name")
        if var_name:
            var_uri = URIRef(f"{file_uri}/var/{uri_safe_string(var_name)}")
            for func in constructs.get("functions", []) + constructs.get(
                "FunctionDefinition", []
            ):
                func_name = func.get("name")
                raw_code = func.get("raw", "")
                if func_name and raw_code and var_name in raw_code:
                    func_uri = URIRef(
                        f"{file_uri}/function/{uri_safe_string(func_name)}"
                    )
                    g.add(
                        (func_uri, prop_cache.get("manipulates", RDFS.seeAlso), var_uri)
                    )
                    g.add(
                        (
                            var_uri,
                            prop_cache.get("isManipulatedBy", RDFS.seeAlso),
                            func_uri,
                        )
                    )


def write_styling_relationships(g, constructs, file_uri, prop_cache, uri_safe_string):
    """
    Write isStyledBy/styles relationships between code constructs.

    Args:
        g: RDFLib Graph to add triples to.
        constructs: Dict of extracted code constructs.
        file_uri: URIRef for the file.
        prop_cache: Dict of ontology property URIs.
        uri_safe_string: Function to make URI-safe strings.
    Returns:
        None
    """
    for func in constructs.get("functions", []) + constructs.get(
        "FunctionDefinition", []
    ):
        func_name = func.get("name")
        raw_code = func.get("raw", "")
        if func_name and raw_code:
            styling_keywords = ["style", "css", "class", "className", "id"]
            if any(keyword in raw_code.lower() for keyword in styling_keywords):
                func_uri = URIRef(f"{file_uri}/function/{uri_safe_string(func_name)}")
                for var in constructs.get("variables", []) + constructs.get(
                    "VariableDeclaration", []
                ):
                    var_name = var.get("name")
                    if var_name and "element" in var_name.lower():
                        var_uri = URIRef(f"{file_uri}/var/{uri_safe_string(var_name)}")
                        g.add(
                            (func_uri, prop_cache.get("styles", RDFS.seeAlso), var_uri)
                        )
                        g.add(
                            (
                                var_uri,
                                prop_cache.get("isStyledBy", RDFS.seeAlso),
                                func_uri,
                            )
                        )


def extract_test_relationships(
    constructs: dict,
    file_uri: str,
    prop_cache: dict,
    uri_safe_string: Callable[[str], str],
    g: "Graph",
) -> None:
    """
    Extract and add test relationships between functions in the ontology graph.

    Args:
        constructs: Parsed code constructs.
        file_uri: URI of the file being processed.
        prop_cache: Property cache for RDF predicates.
        uri_safe_string: Function to make strings URI-safe.
        g: RDFLib Graph to which relationships are added.
    Returns:
        None
    """
    test_keywords = ["test", "spec", "assert", "expect", "describe", "it"]
    for func in constructs.get("functions", []) + constructs.get(
        "FunctionDefinition", []
    ):
        func_name = func.get("name")
        raw_code = func.get("raw", "")
        if func_name and raw_code:
            if any(
                keyword in func_name.lower() or keyword in raw_code.lower()
                for keyword in test_keywords
            ):
                test_uri = URIRef(f"{file_uri}/function/{uri_safe_string(func_name)}")
                for target_func in constructs.get("functions", []) + constructs.get(
                    "FunctionDefinition", []
                ):
                    target_name = target_func.get("name")
                    if target_name and target_name in raw_code:
                        target_uri = URIRef(
                            f"{file_uri}/function/{uri_safe_string(target_name)}"
                        )
                        g.add(
                            (
                                test_uri,
                                prop_cache.get("tests", RDFS.seeAlso),
                                target_uri,
                            )
                        )
                        g.add(
                            (
                                target_uri,
                                prop_cache.get("isTestedBy", RDFS.seeAlso),
                                test_uri,
                            )
                        )


def write_testing_relationships(g, constructs, file_uri, prop_cache, uri_safe_string):
    """
    Write isTestedBy/tests relationships between code constructs.

    Args:
        g: RDFLib Graph to add triples to.
        constructs: Dict of extracted code constructs.
        file_uri: URIRef for the file.
        prop_cache: Dict of ontology property URIs.
        uri_safe_string: Function to make URI-safe strings.
    Returns:
        None
    """
    extract_test_relationships(constructs, file_uri, prop_cache, uri_safe_string, g)


def write_module_import_relationships(
    g, constructs, file_uri, prop_cache, uri_safe_string, module_uris
):
    """
    Write imports/isImportedBy relationships between modules (PackageDeclaration), strictly enforcing WDO domain/range.

    Args:
        g: RDFLib Graph to add triples to.
        constructs: Dict of extracted code constructs.
        file_uri: URIRef for the file.
        prop_cache: Dict of ontology property URIs.
        uri_safe_string: Function to make URI-safe strings.
        module_uris: Dict mapping module names to their URIs.
    Returns:
        None
    """
    imports = constructs.get("ImportDeclaration", []) + constructs.get("imports", [])
    for imp in imports:
        imported_name = imp.get("name") or imp.get("raw") or None
        if not imported_name:
            continue
        for mod_name, mod_uri in module_uris.items():
            if imported_name == mod_name:
                g.add((mod_uri, prop_cache["imports"], module_uris[imported_name]))
                g.add((module_uris[imported_name], prop_cache["isImportedBy"], mod_uri))
