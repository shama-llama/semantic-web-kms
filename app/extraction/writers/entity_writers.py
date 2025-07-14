"""Writers for encoding code construct entities as RDF triples in the ontology graph."""

from rdflib import Literal, URIRef
from rdflib.namespace import RDF, RDFS, XSD

from app.extraction.utils.code_analysis_utils import (
    calculate_cyclomatic_complexity,
    extract_access_modifier,
    extract_boolean_modifiers,
    generate_canonical_name,
)
from app.extraction.utils.string_utils import (
    calculate_line_count,
    calculate_token_count,
)


def write_classes(
    g, constructs, file_uri, class_cache, prop_cache, uri_safe_string, content_uri
):
    """
    Write class entities to the ontology, strictly enforcing WDO domain/range.

    Args:
        g: RDFLib Graph to add triples to.
        constructs: Dict of extracted code constructs.
        file_uri: URIRef for the file.
        class_cache: Dict of ontology class URIs.
        prop_cache: Dict of ontology property URIs.
        uri_safe_string: Function to make URI-safe strings.
        content_uri: URIRef for the content (e.g., a file or a class).
    Returns:
        Dict mapping class names to their URIs.
    """
    class_uris = {}
    class_methods = {}
    for cls in constructs.get("ClassDefinition", []) + constructs.get("classes", []):
        class_id = cls.get("name")
        if not class_id:
            continue
        class_uri = URIRef(f"{file_uri}/class/{uri_safe_string(class_id)}")
        class_uris[class_id] = class_uri
        _add_class_basic_triples(
            g, class_uri, class_id, class_cache, prop_cache, content_uri
        )
        # Add rdfs:label with prefix and truncation
        label = f"class: {_truncate_label(class_id)}"
        g.add((class_uri, RDFS.label, Literal(label, datatype=XSD.string)))
        _add_class_optional_properties(g, class_uri, cls, prop_cache)
        methods = _collect_class_methods(cls)
        if methods:
            class_methods[class_id] = methods
    _add_class_method_relationships(
        g, class_uris, class_methods, file_uri, prop_cache, uri_safe_string
    )
    return class_uris


def write_enums(
    g, constructs, file_uri, class_cache, prop_cache, uri_safe_string, content_uri
):
    """
    Write enum entities to the ontology.

    Args:
        g: RDFLib Graph to add triples to.
        constructs: Dict of extracted code constructs.
        file_uri: URIRef for the file.
        class_cache: Dict of ontology class URIs.
        prop_cache: Dict of ontology property URIs.
        uri_safe_string: Function to make URI-safe strings.
        content_uri: URIRef for the content (e.g., a file or a class).
    Returns:
        Dict mapping enum names to their URIs.
    """
    enum_uris = {}
    for enum in (
        constructs.get("EnumDefinition", [])
        + constructs.get("EnumDeclaration", [])
        + constructs.get("enums", [])
    ):
        enum_id = enum.get("name")
        if not enum_id:
            continue
        enum_uri = URIRef(f"{file_uri}/enum/{uri_safe_string(enum_id)}")
        enum_uris[enum_id] = enum_uri
        enum_class = class_cache.get(
            "EnumDefinition", class_cache.get("ClassDefinition", RDFS.seeAlso)
        )
        g.add((enum_uri, RDF.type, enum_class))
        g.add((enum_uri, prop_cache.get("isCodePartOf", RDFS.seeAlso), content_uri))
        label = f"enum: {_truncate_label(enum_id)}"
        g.add((enum_uri, RDFS.label, Literal(label, datatype=XSD.string)))
        g.add(
            (
                enum_uri,
                prop_cache["hasSimpleName"],
                Literal(enum_id, datatype=XSD.string),
            )
        )
        if "raw" in enum and enum["raw"]:
            g.add(
                (
                    enum_uri,
                    prop_cache.get("hasSourceCodeSnippet", RDFS.seeAlso),
                    Literal(enum["raw"], datatype=XSD.string),
                )
            )
        if "start_line" in enum:
            g.add(
                (
                    enum_uri,
                    prop_cache["startsAtLine"],
                    Literal(enum["start_line"], datatype=XSD.integer),
                )
            )
        if "end_line" in enum:
            g.add(
                (
                    enum_uri,
                    prop_cache["endsAtLine"],
                    Literal(enum["end_line"], datatype=XSD.integer),
                )
            )
        for dec in enum.get("decorators", []):
            g.add(
                (
                    enum_uri,
                    prop_cache.get("hasTextValue", RDFS.seeAlso),
                    Literal(dec, datatype=XSD.string),
                )
            )
    return enum_uris


def write_interfaces(
    g, constructs, file_uri, class_cache, prop_cache, uri_safe_string, content_uri
):
    """
    Write interface entities to the ontology.

    Args:
        g: RDFLib Graph to add triples to.
        constructs: Dict of extracted code constructs.
        file_uri: URIRef for the file.
        class_cache: Dict of ontology class URIs.
        prop_cache: Dict of ontology property URIs.
        uri_safe_string: Function to make URI-safe strings.
        content_uri: URIRef for the content (e.g., a file or a class).
    Returns:
        Dict mapping interface names to their URIs.
    """
    interface_uris = {}
    for interface in constructs.get("InterfaceDefinition", []):
        interface_id = interface.get("name")
        if not interface_id:
            continue
        interface_uri = URIRef(f"{file_uri}/interface/{uri_safe_string(interface_id)}")
        interface_uris[interface_id] = interface_uri
        interface_class = class_cache.get(
            "InterfaceDefinition", class_cache.get("ClassDefinition", RDFS.seeAlso)
        )
        g.add((interface_uri, RDF.type, interface_class))
        g.add(
            (interface_uri, prop_cache.get("isCodePartOf", RDFS.seeAlso), content_uri)
        )
        label = f"interface: {_truncate_label(interface_id)}"
        g.add((interface_uri, RDFS.label, Literal(label, datatype=XSD.string)))
        g.add(
            (
                interface_uri,
                prop_cache["hasSimpleName"],
                Literal(interface_id, datatype=XSD.string),
            )
        )
        if "raw" in interface and interface["raw"]:
            g.add(
                (
                    interface_uri,
                    prop_cache.get("hasSourceCodeSnippet", RDFS.seeAlso),
                    Literal(interface["raw"], datatype=XSD.string),
                )
            )
        if "start_line" in interface:
            g.add(
                (
                    interface_uri,
                    prop_cache["startsAtLine"],
                    Literal(interface["start_line"], datatype=XSD.integer),
                )
            )
        if "end_line" in interface:
            g.add(
                (
                    interface_uri,
                    prop_cache["endsAtLine"],
                    Literal(interface["end_line"], datatype=XSD.integer),
                )
            )
        for dec in interface.get("decorators", []):
            g.add(
                (
                    interface_uri,
                    prop_cache.get("hasTextValue", RDFS.seeAlso),
                    Literal(dec, datatype=XSD.string),
                )
            )
    return interface_uris


def write_structs(
    g, constructs, file_uri, class_cache, prop_cache, uri_safe_string, content_uri
):
    """
    Write struct entities to the ontology.

    Args:
        g: RDFLib Graph to add triples to.
        constructs: Dict of extracted code constructs.
        file_uri: URIRef for the file.
        class_cache: Dict of ontology class URIs.
        prop_cache: Dict of ontology property URIs.
        uri_safe_string: Function to make URI-safe strings.
        content_uri: URIRef for the content (e.g., a file or a class).
    Returns:
        Dict mapping struct names to their URIs.
    """
    struct_uris = {}
    for struct in constructs.get("StructDefinition", []):
        struct_id = struct.get("name")
        if not struct_id:
            continue
        struct_uri = URIRef(f"{file_uri}/struct/{uri_safe_string(struct_id)}")
        struct_uris[struct_id] = struct_uri
        g.add(
            (
                struct_uri,
                RDF.type,
                class_cache.get("StructDefinition", class_cache["ClassDefinition"]),
            )
        )
        g.add((struct_uri, prop_cache.get("isCodePartOf", RDFS.seeAlso), content_uri))
        label = f"struct: {_truncate_label(struct_id)}"
        g.add((struct_uri, RDFS.label, Literal(label, datatype=XSD.string)))
        g.add(
            (
                struct_uri,
                prop_cache["hasSimpleName"],
                Literal(struct_id, datatype=XSD.string),
            )
        )
        if "raw" in struct and struct["raw"]:
            g.add(
                (
                    struct_uri,
                    prop_cache.get("hasSourceCodeSnippet", RDFS.seeAlso),
                    Literal(struct["raw"], datatype=XSD.string),
                )
            )
        if "start_line" in struct:
            g.add(
                (
                    struct_uri,
                    prop_cache["startsAtLine"],
                    Literal(struct["start_line"], datatype=XSD.integer),
                )
            )
        if "end_line" in struct:
            g.add(
                (
                    struct_uri,
                    prop_cache["endsAtLine"],
                    Literal(struct["end_line"], datatype=XSD.integer),
                )
            )
        for dec in struct.get("decorators", []):
            g.add(
                (
                    struct_uri,
                    prop_cache.get("hasTextValue", RDFS.seeAlso),
                    Literal(dec, datatype=XSD.string),
                )
            )
    return struct_uris


def write_traits(
    g, constructs, file_uri, class_cache, prop_cache, uri_safe_string, content_uri
):
    """
    Write trait entities to the ontology.

    Args:
        g: RDFLib Graph to add triples to.
        constructs: Dict of extracted code constructs.
        file_uri: URIRef for the file.
        class_cache: Dict of ontology class URIs.
        prop_cache: Dict of ontology property URIs.
        uri_safe_string: Function to make URI-safe strings.
        content_uri: URIRef for the content (e.g., a file or a class).
    Returns:
        Dict mapping trait names to their URIs.
    """
    trait_uris = {}
    for trait in constructs.get("TraitDefinition", []):
        trait_id = trait.get("name")
        if not trait_id:
            continue
        trait_uri = URIRef(f"{file_uri}/trait/{uri_safe_string(trait_id)}")
        trait_uris[trait_id] = trait_uri
        g.add(
            (
                trait_uri,
                RDF.type,
                class_cache.get(
                    "TraitDefinition",
                    class_cache.get(
                        "InterfaceDefinition", class_cache["ClassDefinition"]
                    ),
                ),
            )
        )
        g.add((trait_uri, prop_cache.get("isCodePartOf", RDFS.seeAlso), content_uri))
        label = f"trait: {_truncate_label(trait_id)}"
        g.add((trait_uri, RDFS.label, Literal(label, datatype=XSD.string)))
        g.add(
            (
                trait_uri,
                prop_cache["hasSimpleName"],
                Literal(trait_id, datatype=XSD.string),
            )
        )
        if "raw" in trait and trait["raw"]:
            g.add(
                (
                    trait_uri,
                    prop_cache.get("hasSourceCodeSnippet", RDFS.seeAlso),
                    Literal(trait["raw"], datatype=XSD.string),
                )
            )
        if "start_line" in trait:
            g.add(
                (
                    trait_uri,
                    prop_cache["startsAtLine"],
                    Literal(trait["start_line"], datatype=XSD.integer),
                )
            )
        if "end_line" in trait:
            g.add(
                (
                    trait_uri,
                    prop_cache["endsAtLine"],
                    Literal(trait["end_line"], datatype=XSD.integer),
                )
            )
        for dec in trait.get("decorators", []):
            g.add(
                (
                    trait_uri,
                    prop_cache.get("hasTextValue", RDFS.seeAlso),
                    Literal(dec, datatype=XSD.string),
                )
            )
    return trait_uris


def write_modules(
    g, constructs, file_uri, class_cache, prop_cache, uri_safe_string, content_uri
):
    """
    Write module entities to the ontology.

    Args:
        g: RDFLib Graph to add triples to.
        constructs: Dict of extracted code constructs.
        file_uri: URIRef for the file.
        class_cache: Dict of ontology class URIs.
        prop_cache: Dict of ontology property URIs.
        uri_safe_string: Function to make URI-safe strings.
        content_uri: URIRef for the content (e.g., a file or a class).
    Returns:
        Dict mapping module names to their URIs.
    """
    module_uris = {}
    for module in constructs.get("PackageDeclaration", []):
        module_id = module.get("name")
        if not module_id:
            continue
        module_uri = URIRef(f"{file_uri}/module/{uri_safe_string(module_id)}")
        module_uris[module_id] = module_uri
        g.add(
            (
                module_uri,
                RDF.type,
                class_cache.get("PackageDeclaration", RDFS.seeAlso),
            )
        )
        g.add((module_uri, prop_cache.get("isCodePartOf", RDFS.seeAlso), content_uri))
        label = f"module: {_truncate_label(module_id)}"
        g.add((module_uri, RDFS.label, Literal(label, datatype=XSD.string)))
        g.add(
            (
                module_uri,
                prop_cache["hasSimpleName"],
                Literal(module_id, datatype=XSD.string),
            )
        )
        if "raw" in module and module["raw"]:
            g.add(
                (
                    module_uri,
                    prop_cache.get("hasSourceCodeSnippet", RDFS.seeAlso),
                    Literal(module["raw"], datatype=XSD.string),
                )
            )
        if "start_line" in module:
            g.add(
                (
                    module_uri,
                    prop_cache["startsAtLine"],
                    Literal(module["start_line"], datatype=XSD.integer),
                )
            )
        if "end_line" in module:
            g.add(
                (
                    module_uri,
                    prop_cache["endsAtLine"],
                    Literal(module["end_line"], datatype=XSD.integer),
                )
            )
    return module_uris


def write_comments(
    g, constructs, file_uri, class_cache, prop_cache, uri_safe_string, content_uri
):
    """
    Write comment entities to the ontology, including rdfs:label in the format 'comment: <text>'.

    Args:
        g: RDFLib Graph to add triples to.
        constructs: Dict of extracted code constructs.
        file_uri: URIRef for the file.
        class_cache: Dict of ontology class URIs.
        prop_cache: Dict of ontology property URIs.
        uri_safe_string: Function to make URI-safe strings.
        content_uri: URIRef for the content (e.g., a file or a class).
    Returns:
        Dict mapping comment IDs to their URIs.
    """
    comment_uris: dict = {}
    for comment in constructs.get("CodeComment", []):
        comment_id = comment.get("raw") or comment.get("name") or str(len(comment_uris))
        comment_uri = URIRef(f"{file_uri}/comment/{uri_safe_string(str(comment_id))}")
        comment_uris[comment_id] = comment_uri
        comment_class = class_cache.get("CodeComment", RDFS.seeAlso)
        g.add((comment_uri, RDF.type, comment_class))
        g.add((comment_uri, prop_cache.get("isCodePartOf", RDFS.seeAlso), content_uri))
        # Add rdfs:label in the format 'comment: <text>' (truncated)
        comment_text = comment.get("raw") or comment.get("name") or str(comment_id)
        label = f"comment: {_truncate_label(comment_text)}"
        g.add((comment_uri, RDFS.label, Literal(label, datatype=XSD.string)))
        g.add(
            (
                comment_uri,
                prop_cache["hasTextValue"],
                Literal(str(comment_id), datatype=XSD.string),
            )
        )
        if "start_line" in comment:
            g.add(
                (
                    comment_uri,
                    prop_cache["startsAtLine"],
                    Literal(comment["start_line"], datatype=XSD.integer),
                )
            )
        if "end_line" in comment:
            g.add(
                (
                    comment_uri,
                    prop_cache["endsAtLine"],
                    Literal(comment["end_line"], datatype=XSD.integer),
                )
            )
    return comment_uris


def write_functions(
    g,
    constructs,
    file_uri,
    class_cache,
    prop_cache,
    uri_safe_string,
    class_uris,
    type_uris,
    content_uri,
    language=None,
):
    """
    Write function entities to the ontology, strictly enforcing WDO domain/range.

    Args:
        g: RDFLib Graph to add triples to.
        constructs: Dict of extracted code constructs.
        file_uri: URIRef for the file.
        class_cache: Dict of ontology class URIs.
        prop_cache: Dict of ontology property URIs.
        uri_safe_string: Function to make URI-safe strings.
        class_uris: Dict mapping class names to URIs.
        type_uris: Dict mapping type names to URIs.
        content_uri: URIRef for the content (e.g., a file or a class).
        language: Optional language string.
    Returns:
        Dict mapping function names to their URIs.
    """
    func_uris = {}
    for func in constructs.get("FunctionDefinition", []) + constructs.get(
        "functions", []
    ):
        func_id = func.get("name")
        if not func_id:
            continue
        func_uri = URIRef(f"{file_uri}/function/{uri_safe_string(func_id)}")
        func_uris[func_id] = func_uri
        _add_function_basic_triples(
            g, func_uri, func_id, class_cache, prop_cache, content_uri
        )
        # Add isCodePartOf relationship to content_uri
        g.add((func_uri, prop_cache.get("isCodePartOf", RDFS.seeAlso), content_uri))
        # Add rdfs:label with prefix and truncation
        label = f"func: {_truncate_label(func_id)}"
        g.add((func_uri, RDFS.label, Literal(label, datatype=XSD.string)))
        _add_function_optional_properties(g, func_uri, func, prop_cache)
        _add_function_return_type(g, func_uri, func, type_uris, prop_cache)
        _add_function_method_of(g, func_uri, func, class_uris, prop_cache)
        _add_function_language(g, func_uri, language, prop_cache)
    return func_uris


def write_parameters(
    g,
    constructs,
    file_uri,
    class_cache,
    prop_cache,
    uri_safe_string,
    func_uris,
    type_uris,
    content_uri,
):
    """
    Write parameter entities to the ontology, strictly enforcing WDO domain/range.

    Args:
        g: RDFLib Graph to add triples to.
        constructs: Dict of extracted code constructs.
        file_uri: URIRef for the file.
        class_cache: Dict of ontology class URIs.
        prop_cache: Dict of ontology property URIs.
        uri_safe_string: Function to make URI-safe strings.
        func_uris: Dict mapping function names to URIs.
        type_uris: Dict mapping type names to URIs.
        content_uri: URIRef for the content (e.g., a file or a class).
    Returns:
        None
    """
    for param in constructs.get("Parameter", []) + constructs.get("parameters", []):
        param_id = param.get("name")
        if not param_id:
            continue
        param_uri = URIRef(f"{file_uri}/param/{uri_safe_string(param_id)}")
        g.add((param_uri, RDF.type, class_cache["Parameter"]))
        g.add((param_uri, prop_cache.get("isCodePartOf", RDFS.seeAlso), content_uri))
        label = f"param: {_truncate_label(param_id)}"
        g.add((param_uri, RDFS.label, Literal(label, datatype=XSD.string)))
        g.add(
            (
                param_uri,
                prop_cache["hasSimpleName"],
                Literal(param_id, datatype=XSD.string),
            )
        )
        if "raw" in param and param["raw"]:
            g.add(
                (
                    param_uri,
                    prop_cache["hasSourceCodeSnippet"],
                    Literal(param["raw"], datatype=XSD.string),
                )
            )
        if "type" in param:
            param_type = param["type"].strip().lower()
            if param_type in type_uris:
                g.add((param_uri, prop_cache["hasType"], type_uris[param_type]))
        if "start_line" in param:
            g.add(
                (
                    param_uri,
                    prop_cache["startsAtLine"],
                    Literal(param["start_line"], datatype=XSD.integer),
                )
            )
        if "end_line" in param:
            g.add(
                (
                    param_uri,
                    prop_cache["endsAtLine"],
                    Literal(param["end_line"], datatype=XSD.integer),
                )
            )
        parent_func = param.get("parent_function")
        if parent_func and parent_func in func_uris:
            g.add((param_uri, prop_cache["isParameterOf"], func_uris[parent_func]))
            g.add((func_uris[parent_func], prop_cache["hasParameter"], param_uri))


def write_variables(
    g,
    constructs,
    file_uri,
    class_cache,
    prop_cache,
    uri_safe_string,
    func_uris,
    type_uris,
    content_uri,
):
    """
    Write variable entities to the ontology, strictly enforcing WDO domain/range.

    Args:
        g: RDFLib Graph to add triples to.
        constructs: Dict of extracted code constructs.
        file_uri: URIRef for the file.
        class_cache: Dict of ontology class URIs.
        prop_cache: Dict of ontology property URIs.
        uri_safe_string: Function to make URI-safe strings.
        func_uris: Dict mapping function names to URIs.
        type_uris: Dict mapping type names to URIs.
        content_uri: URIRef for the content (e.g., a file or a class).
    Returns:
        None
    """
    for var in constructs.get("VariableDeclaration", []) + constructs.get(
        "variables", []
    ):
        var_id = var.get("name")
        if not var_id:
            continue
        var_uri = URIRef(f"{file_uri}/var/{uri_safe_string(var_id)}")
        g.add((var_uri, RDF.type, class_cache["VariableDeclaration"]))
        g.add((var_uri, prop_cache.get("isCodePartOf", RDFS.seeAlso), content_uri))
        label = f"var: {_truncate_label(var_id)}"
        g.add((var_uri, RDFS.label, Literal(label, datatype=XSD.string)))
        g.add(
            (var_uri, prop_cache["hasSimpleName"], Literal(var_id, datatype=XSD.string))
        )
        if "raw" in var and var["raw"]:
            g.add(
                (
                    var_uri,
                    prop_cache["hasSourceCodeSnippet"],
                    Literal(var["raw"], datatype=XSD.string),
                )
            )
        if "type" in var:
            var_type = var["type"].strip().lower()
            if var_type in type_uris:
                g.add((var_uri, prop_cache["hasType"], type_uris[var_type]))
        if "start_line" in var:
            g.add(
                (
                    var_uri,
                    prop_cache["startsAtLine"],
                    Literal(var["start_line"], datatype=XSD.integer),
                )
            )
        if "end_line" in var:
            g.add(
                (
                    var_uri,
                    prop_cache["endsAtLine"],
                    Literal(var["end_line"], datatype=XSD.integer),
                )
            )


def write_calls(
    g,
    constructs,
    file_uri,
    class_cache,
    prop_cache,
    uri_safe_string,
    func_uris,
    type_uris,
    content_uri,
):
    """
    Write function call entities to the ontology, strictly enforcing WDO domain/range.

    Args:
        g: RDFLib Graph to add triples to.
        constructs: Dict of extracted code constructs.
        file_uri: URIRef for the file.
        class_cache: Dict of ontology class URIs.
        prop_cache: Dict of ontology property URIs.
        uri_safe_string: Function to make URI-safe strings.
        func_uris: Dict mapping function names to URIs.
        type_uris: Dict mapping type names to URIs.
        content_uri: URIRef for the content (e.g., a file or a class).
    Returns:
        None
    """
    for call in constructs.get("calls", []):
        call_id = call.get("name")
        if not call_id:
            continue
        call_uri = URIRef(f"{file_uri}/call/{uri_safe_string(call_id)}")
        g.add((call_uri, RDF.type, class_cache["FunctionCallSite"]))
        g.add((call_uri, prop_cache.get("isCodePartOf", RDFS.seeAlso), content_uri))
        # Always set rdfs:label with 'callsite: ' prefix
        label = (
            f"callsite: {call_id}" if not call_id.startswith("callsite: ") else call_id
        )
        g.add((call_uri, RDFS.label, Literal(label, datatype=XSD.string)))
        g.add(
            (
                call_uri,
                prop_cache["hasSimpleName"],
                Literal(call_id, datatype=XSD.string),
            )
        )
        if call.get("raw"):
            g.add(
                (
                    call_uri,
                    prop_cache["hasSourceCodeSnippet"],
                    Literal(call["raw"], datatype=XSD.string),
                )
            )
        if call.get("start_line") is not None:
            g.add(
                (
                    call_uri,
                    prop_cache["startsAtLine"],
                    Literal(call["start_line"], datatype=XSD.integer),
                )
            )
        if call.get("end_line") is not None:
            g.add(
                (
                    call_uri,
                    prop_cache["endsAtLine"],
                    Literal(call["end_line"], datatype=XSD.integer),
                )
            )
        for arg in call.get("arguments", []):
            arg_id = arg.get("name") if isinstance(arg, dict) else arg
            if not arg_id:
                continue
            arg_uri = URIRef(f"{call_uri}/arg/{uri_safe_string(arg_id)}")
            g.add((call_uri, prop_cache["hasArgument"], arg_uri))
            g.add((arg_uri, prop_cache["isArgumentIn"], call_uri))
            # Type the argument node as Argument
            g.add((arg_uri, RDF.type, class_cache["Argument"]))
            # Add rdfs:label with prefix for argument
            g.add((arg_uri, RDFS.label, Literal(f"arg: {arg_id}", datatype=XSD.string)))
            # If the argument is a variable and a VariableDeclaration exists, link them
            var_uri = URIRef(f"{file_uri}/var/{uri_safe_string(arg_id)}")
            if any(
                v.get("name") == arg_id
                for v in constructs.get("VariableDeclaration", [])
                + constructs.get("variables", [])
            ):
                g.add((arg_uri, prop_cache["refersToVariable"], var_uri))
                g.add((var_uri, prop_cache["isReferredToByArgument"], arg_uri))
        if "calls" in call:
            for callee in call["calls"]:
                if callee in func_uris:
                    g.add((call_uri, prop_cache["callsFunction"], func_uris[callee]))
                    g.add(
                        (
                            func_uris[callee],
                            prop_cache["isCalledByFunctionAt"],
                            call_uri,
                        )
                    )


def write_decorators(
    g, constructs, file_uri, class_cache, prop_cache, uri_safe_string, content_uri
):
    """
    Write decorator entities to the ontology.

    Args:
        g: RDFLib Graph to add triples to.
        constructs: Dict of extracted code constructs.
        file_uri: URIRef for the file.
        class_cache: Dict of ontology class URIs.
        prop_cache: Dict of ontology property URIs.
        uri_safe_string: Function to make URI-safe strings.
        content_uri: URIRef for the content (e.g., a file or a class).
    Returns:
        None
    """
    for dec in constructs.get("decorators", []):
        if isinstance(dec, dict):
            dec_id = dec.get("raw") or dec.get("name")
        else:
            dec_id = dec
        if not dec_id:
            continue
        dec_uri = URIRef(f"{file_uri}/decorator/{uri_safe_string(str(dec_id))}")
        decorator_class = class_cache.get("Decorator", RDFS.seeAlso)
        g.add((dec_uri, RDF.type, decorator_class))
        g.add((dec_uri, prop_cache.get("isCodePartOf", RDFS.seeAlso), content_uri))
        g.add(
            (
                dec_uri,
                prop_cache["hasSimpleName"],
                Literal(str(dec_id), datatype=XSD.string),
            )
        )
        if isinstance(dec, dict) and "raw" in dec and dec["raw"]:
            g.add(
                (
                    dec_uri,
                    prop_cache.get("hasSourceCodeSnippet", RDFS.seeAlso),
                    Literal(dec["raw"], datatype=XSD.string),
                )
            )


def write_types(
    g, constructs, file_uri, class_cache, prop_cache, uri_safe_string, content_uri
):
    """
    Write type entities to the ontology.

    Args:
        g: RDFLib Graph to add triples to.
        constructs: Dict of extracted code constructs.
        file_uri: URIRef for the file.
        class_cache: Dict of ontology class URIs.
        prop_cache: Dict of ontology property URIs.
        uri_safe_string: Function to make URI-safe strings.
        content_uri: URIRef for the content (e.g., a file or a class).
    Returns:
        None
    """
    for typ in constructs.get("types", []):
        typ_id = typ.get("raw") or typ.get("name") or typ
        if not typ_id:
            continue
        primitive_types = [
            "int",
            "float",
            "str",
            "bool",
            "char",
            "double",
            "long",
            "short",
            "byte",
            "void",
            "null",
            "undefined",
            "number",
            "string",
            "boolean",
        ]
        is_primitive = any(primitive in typ_id.lower() for primitive in primitive_types)
        if is_primitive:
            typ_uri = URIRef(f"{file_uri}/types/{uri_safe_string(typ_id.lower())}")
            if not (typ_uri, RDF.type, None) in g:
                type_class = class_cache.get(
                    "PrimitiveType", class_cache.get("Type", RDFS.seeAlso)
                )
                g.add((typ_uri, RDF.type, type_class))
                g.add(
                    (
                        typ_uri,
                        prop_cache.get("hasSimpleName", RDFS.seeAlso),
                        Literal(typ_id.lower(), datatype=XSD.string),
                    )
                )
        else:
            typ_uri = URIRef(f"{file_uri}/type/{uri_safe_string(str(typ_id))}")
            type_class = class_cache.get("Type", RDFS.seeAlso)
            g.add((typ_uri, RDF.type, type_class))
            g.add(
                (
                    typ_uri,
                    prop_cache.get("isCodePartOf", RDFS.seeAlso),
                    content_uri,
                )
            )
            g.add(
                (
                    typ_uri,
                    prop_cache.get("hasSimpleName", RDFS.seeAlso),
                    Literal(str(typ_id), datatype=XSD.string),
                )
            )
            if "raw" in typ and typ["raw"]:
                g.add(
                    (
                        typ_uri,
                        prop_cache.get("hasSourceCodeSnippet", RDFS.seeAlso),
                        Literal(typ["raw"], datatype=XSD.string),
                    )
                )


def write_imports(
    g, constructs, file_uri, class_cache, prop_cache, uri_safe_string, content_uri
):
    """
    Write import entities to the ontology.

    Args:
        g: RDFLib Graph to add triples to.
        constructs: Dict of extracted code constructs.
        file_uri: URIRef for the file.
        class_cache: Dict of ontology class URIs.
        prop_cache: Dict of ontology property URIs.
        uri_safe_string: Function to make URI-safe strings.
        content_uri: URIRef for the content (e.g., a file or a class).
    Returns:
        None
    """
    imports = constructs.get("ImportDeclaration", []) + constructs.get("imports", [])
    for imp in imports:
        imp_id = imp.get("raw") or imp.get("name") or imp
        if not imp_id:
            continue
        imp_uri = URIRef(f"{file_uri}/import/{uri_safe_string(imp_id)}")
        import_class = class_cache.get("ImportDeclaration", RDFS.seeAlso)
        g.add((imp_uri, RDF.type, import_class))
        g.add((imp_uri, prop_cache.get("isCodePartOf", RDFS.seeAlso), content_uri))
        label = f"import: {_truncate_label(str(imp_id))}"
        g.add((imp_uri, RDFS.label, Literal(label, datatype=XSD.string)))
        g.add(
            (
                imp_uri,
                prop_cache["hasSourceCodeSnippet"],
                Literal(imp_id, datatype=XSD.string),
            )
        )


def write_repo_file_link(g, repo_enc, WDO, INST, file_uri):
    """
    Add a triple linking a repository to a file in the ontology.

    Args:
        g: RDFLib Graph to add triples to.
        repo_enc: Encoded repository name.
        WDO: WDO namespace.
        INST: Instance namespace.
        file_uri: URIRef for the file.
    Returns:
        None
    """
    g.add((INST[repo_enc], WDO.hasFile, file_uri))


def write_database_schemas(
    g, constructs, file_uri, class_cache, prop_cache, uri_safe_string
):
    """
    Stub: No-op for database schema extraction. Returns empty dict.

    Args:
        g: RDFLib Graph to add triples to.
        constructs: Dict of extracted code constructs.
        file_uri: URIRef for the file.
        class_cache: Dict of ontology class URIs.
        prop_cache: Dict of ontology property URIs.
        uri_safe_string: Function to make URI-safe strings.
    Returns:
        Empty dict.
    """
    return {}


# Helper functions for entity writing (add as needed)
def _add_class_basic_triples(
    g, class_uri, class_id, class_cache, prop_cache, content_uri
):
    """
    Add basic RDF triples for a class entity.

    Args:
        g: RDFLib Graph to add triples to.
        class_uri: URIRef for the class.
        class_id: Class name.
        class_cache: Dict of ontology class URIs.
        prop_cache: Dict of ontology property URIs.
        content_uri: URIRef for the content (e.g., a file or a class).
    Returns:
        None
    """
    g.add((class_uri, RDF.type, class_cache["ClassDefinition"]))
    g.add(
        (class_uri, prop_cache["hasSimpleName"], Literal(class_id, datatype=XSD.string))
    )
    g.add((class_uri, prop_cache.get("isCodePartOf", RDFS.seeAlso), content_uri))


def _add_class_optional_properties(g, class_uri, cls, prop_cache):
    """
    Add optional RDF triples for a class entity (canonical name, code, etc).

    Args:
        g: RDFLib Graph to add triples to.
        class_uri: URIRef for the class.
        cls: Dict with class details.
        prop_cache: Dict of ontology property URIs.
    Returns:
        None
    """
    canonical_name = generate_canonical_name(cls)
    if canonical_name:
        g.add(
            (
                class_uri,
                prop_cache["hasCanonicalName"],
                Literal(canonical_name, datatype=XSD.string),
            )
        )
    if "raw" in cls and cls["raw"]:
        g.add(
            (
                class_uri,
                prop_cache["hasSourceCodeSnippet"],
                Literal(cls["raw"], datatype=XSD.string),
            )
        )
        access_modifier = extract_access_modifier(cls, cls["raw"])
        if access_modifier:
            g.add(
                (
                    class_uri,
                    prop_cache["hasAccessModifier"],
                    Literal(access_modifier, datatype=XSD.string),
                )
            )
        token_count = calculate_token_count(cls["raw"])
        g.add(
            (
                class_uri,
                prop_cache["hasTokenCount"],
                Literal(token_count, datatype=XSD.nonNegativeInteger),
            )
        )
        line_count = calculate_line_count(cls["raw"])
        g.add(
            (
                class_uri,
                prop_cache["hasLineCount"],
                Literal(line_count, datatype=XSD.nonNegativeInteger),
            )
        )
        boolean_modifiers = extract_boolean_modifiers(cls, cls["raw"])
        for modifier_name, modifier_value in boolean_modifiers.items():
            if modifier_value and modifier_name in prop_cache:
                g.add(
                    (
                        class_uri,
                        prop_cache[modifier_name],
                        Literal(modifier_value, datatype=XSD.boolean),
                    )
                )
    if "start_line" in cls:
        g.add(
            (
                class_uri,
                prop_cache["startsAtLine"],
                Literal(cls["start_line"], datatype=XSD.integer),
            )
        )
    if "end_line" in cls:
        g.add(
            (
                class_uri,
                prop_cache["endsAtLine"],
                Literal(cls["end_line"], datatype=XSD.integer),
            )
        )
    for dec in cls.get("decorators", []):
        g.add(
            (class_uri, prop_cache["hasTextValue"], Literal(dec, datatype=XSD.string))
        )


def _add_class_method_relationships(
    g, class_uris, class_methods, file_uri, prop_cache, uri_safe_string
):
    """
    Add method relationships between classes and their methods.

    Args:
        g: RDFLib Graph to add triples to.
        class_uris: Dict mapping class names to URIs.
        class_methods: Dict mapping class names to method names.
        file_uri: URIRef for the file.
        prop_cache: Dict of ontology property URIs.
        uri_safe_string: Function to make URI-safe strings.
    Returns:
        None
    """
    for class_id, method_names in class_methods.items():
        class_uri = class_uris[class_id]
        for method_name in method_names:
            method_uri = URIRef(f"{file_uri}/function/{uri_safe_string(method_name)}")
            g.add((class_uri, prop_cache["hasMethod"], method_uri))
            g.add((method_uri, prop_cache["isMethodOf"], class_uri))


def _add_function_basic_triples(
    g, func_uri, func_id, class_cache, prop_cache, content_uri
):
    """
    Add basic RDF triples for a function entity.

    Args:
        g: RDFLib Graph to add triples to.
        func_uri: URIRef for the function.
        func_id: Function name.
        class_cache: Dict of ontology class URIs.
        prop_cache: Dict of ontology property URIs.
        content_uri: URIRef for the content (e.g., a file or a class).
    Returns:
        None
    """
    g.add((func_uri, RDF.type, class_cache["FunctionDefinition"]))
    g.add(
        (func_uri, prop_cache["hasSimpleName"], Literal(func_id, datatype=XSD.string))
    )
    g.add((func_uri, prop_cache.get("isCodePartOf", RDFS.seeAlso), content_uri))


def _add_function_optional_properties(g, func_uri, func, prop_cache):
    """
    Add optional RDF triples for a function entity (canonical name, code, etc).

    Args:
        g: RDFLib Graph to add triples to.
        func_uri: URIRef for the function.
        func: Dict with function details.
        prop_cache: Dict of ontology property URIs.
    Returns:
        None
    """
    parent_class = func.get("parent_class")
    canonical_name = generate_canonical_name(func, parent_context=parent_class)
    if canonical_name:
        g.add(
            (
                func_uri,
                prop_cache["hasCanonicalName"],
                Literal(canonical_name, datatype=XSD.string),
            )
        )
    if "raw" in func and func["raw"]:
        g.add(
            (
                func_uri,
                prop_cache["hasSourceCodeSnippet"],
                Literal(func["raw"], datatype=XSD.string),
            )
        )
        access_modifier = extract_access_modifier(func, func["raw"])
        if access_modifier:
            g.add(
                (
                    func_uri,
                    prop_cache["hasAccessModifier"],
                    Literal(access_modifier, datatype=XSD.string),
                )
            )
        token_count = calculate_token_count(func["raw"])
        g.add(
            (
                func_uri,
                prop_cache["hasTokenCount"],
                Literal(token_count, datatype=XSD.nonNegativeInteger),
            )
        )
        line_count = calculate_line_count(func["raw"])
        g.add(
            (
                func_uri,
                prop_cache["hasLineCount"],
                Literal(line_count, datatype=XSD.nonNegativeInteger),
            )
        )
        boolean_modifiers = extract_boolean_modifiers(func, func["raw"])
        for modifier_name, modifier_value in boolean_modifiers.items():
            if modifier_value and modifier_name in prop_cache:
                g.add(
                    (
                        func_uri,
                        prop_cache[modifier_name],
                        Literal(modifier_value, datatype=XSD.boolean),
                    )
                )
        if "hasCyclomaticComplexity" in prop_cache:
            complexity = calculate_cyclomatic_complexity(func["raw"])
            g.add(
                (
                    func_uri,
                    prop_cache["hasCyclomaticComplexity"],
                    Literal(complexity, datatype=XSD.integer),
                )
            )
    if "start_line" in func:
        g.add(
            (
                func_uri,
                prop_cache["startsAtLine"],
                Literal(func["start_line"], datatype=XSD.integer),
            )
        )
    if "end_line" in func:
        g.add(
            (
                func_uri,
                prop_cache["endsAtLine"],
                Literal(func["end_line"], datatype=XSD.integer),
            )
        )


def _add_function_return_type(g, func_uri, func, type_uris, prop_cache):
    """
    Add RDF triples for a function's return type.

    Args:
        g: RDFLib Graph to add triples to.
        func_uri: URIRef for the function.
        func: Dict with function details.
        type_uris: Dict mapping type names to URIs.
        prop_cache: Dict of ontology property URIs.
    Returns:
        None
    """
    return_type = func.get("returns", "")
    if return_type:
        type_uri = type_uris.get(return_type.strip().lower())
        if type_uri:
            g.add((func_uri, prop_cache["hasReturnType"], type_uri))
            g.add((type_uri, prop_cache["isReturnTypeOf"], func_uri))


def _add_function_method_of(g, func_uri, func, class_uris, prop_cache):
    """
    Add RDF triples linking a function to its parent class as a method.

    Args:
        g: RDFLib Graph to add triples to.
        func_uri: URIRef for the function.
        func: Dict with function details.
        class_uris: Dict mapping class names to URIs.
        prop_cache: Dict of ontology property URIs.
    Returns:
        None
    """
    parent_class = func.get("parent_class")
    if parent_class and parent_class in class_uris:
        class_uri = class_uris[parent_class]
        g.add((func_uri, prop_cache["isMethodOf"], class_uri))
        g.add((class_uri, prop_cache["hasMethod"], func_uri))


def _add_function_language(g, func_uri, language, prop_cache):
    """
    Add RDF triple for a function's programming language. Language name is normalized to lowercase.

    Args:
        g: RDFLib Graph to add triples to.
        func_uri: URIRef for the function.
        language: Programming language as a string.
        prop_cache: Dict of ontology property URIs.
    Returns:
        None
    """
    if language and "hasProgrammingLanguage" in prop_cache:
        normalized_language = language.lower()
        g.add(
            (
                func_uri,
                prop_cache["hasProgrammingLanguage"],
                Literal(normalized_language, datatype=XSD.string),
            )
        )


def _collect_class_methods(cls):
    """
    Collect method names from a class dictionary.

    Args:
        cls: Dict with class details (should have 'methods' key).
    Returns:
        List of method names (strings).
    """
    if "methods" in cls and isinstance(cls["methods"], list):
        return [m.get("name") for m in cls["methods"] if m.get("name")]
    return []


def create_canonical_type_individuals(g, class_cache, prop_cache, uri_safe_string):
    """
    Stub: No-op for canonical type individuals. Returns empty dict.

    Args:
        g: RDFLib Graph to add triples to.
        class_cache: Dict of ontology class URIs.
        prop_cache: Dict of ontology property URIs.
        uri_safe_string: Function to make URI-safe strings.
    Returns:
        Empty dict.
    """
    return {}


def _truncate_label(text: str, max_length: int = 60) -> str:
    """
    Truncate a label to a maximum length for display or storage.

    Args:
        text: The string to truncate.
        max_length: The maximum allowed length.

    Returns:
        Truncated string, not cutting words in half.
    """
    if len(text) <= max_length:
        return text
    cutoff = text.rfind(" ", 0, max_length)
    if cutoff == -1:
        return text[:max_length].rstrip() + "..."
    return text[:cutoff].rstrip() + "..."
