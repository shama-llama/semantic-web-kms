import tree_sitter_java
from tree_sitter import Parser
from typing import List

from .base_parser import BaseCodeParser
from ..models.code import (
    CodeConstruct, ClassDefinition, FunctionDefinition, AttributeDeclaration,
    InterfaceDefinition, EnumDefinition, Parameter, VariableDeclaration, FunctionCallSite, ImportDeclaration,
    PrimitiveType, ComplexType, Argument
)

class JavaParser(BaseCodeParser):
    """
    Concrete parser for Java source files. Inherits from BaseCodeParser and implements
    the required methods to provide the Java tree-sitter language and parse Java code.
    """
    def get_language(self):
        """
        Returns the tree-sitter language object for Java.
        Returns:
            Language: The tree-sitter Java language object.
        """
        from tree_sitter import Language
        return Language(tree_sitter_java.language())

    def parse(self, file_content: str, file_path: str) -> List[CodeConstruct]:
        """
        Parses the given Java file content and returns a list of CodeConstructs.
        Args:
            file_content (str): The content of the Java file.
            file_path (str): The path to the Java file.
        Returns:
            List[CodeConstruct]: List of parsed code constructs.
        """
        tree = self.parser.parse(bytes(file_content, "utf8"))
        all_constructs: List[CodeConstruct] = []
        # Registry for name lookup (for extends/implements)
        name_registry = {}

        # --- AST Traversal and Model Instantiation ---
        def traverse(node, parent_class_model=None, local_scope=None):
            if local_scope is None:
                local_scope = {}
            # Example: Handle enum declarations
            if node.type == 'enum_declaration':
                enum_model = EnumDefinition(node, file_path)
                name_node = node.child_by_field_name('name')
                if name_node:
                    enum_model.hasCanonicalName = name_node.text.decode('utf8')
                    name_registry[enum_model.hasCanonicalName] = enum_model
                # Enum constants as AttributeDeclaration
                body_node = node.child_by_field_name('body')
                if body_node:
                    for child in body_node.children:
                        if child.type == 'enum_constant':
                            const_name_node = child.child_by_field_name('name')
                            if const_name_node:
                                const_model = AttributeDeclaration(child, file_path)
                                const_model.hasCanonicalName = const_name_node.text.decode('utf8')
                                all_constructs.append(const_model)
                                enum_model.add_field(const_model)
                all_constructs.append(enum_model)
                for child in node.children:
                    traverse(child, parent_class_model=None, local_scope=local_scope)
                return
            # Example: Handle class declarations
            if node.type == 'class_declaration':
                class_model = ClassDefinition(node, file_path)
                name_node = node.child_by_field_name('name')
                if name_node:
                    class_model.hasCanonicalName = name_node.text.decode('utf8')
                    name_registry[class_model.hasCanonicalName] = class_model
                superclass_node = node.child_by_field_name('superclass')
                if superclass_node:
                    super_name_node = superclass_node.child_by_field_name('name')
                    if super_name_node:
                        super_name = super_name_node.text.decode('utf8')
                        if super_name in name_registry:
                            class_model.add_extends_type(name_registry[super_name])
                interfaces_node = node.child_by_field_name('interfaces')
                if interfaces_node:
                    for iface in interfaces_node.children:
                        if iface.type == 'type_list':
                            for type_id in iface.children:
                                if type_id.type == 'type_identifier':
                                    iface_name = type_id.text.decode('utf8')
                                    if iface_name in name_registry:
                                        class_model.add_implements_interface(name_registry[iface_name])
                all_constructs.append(class_model)
                for child in node.children:
                    traverse(child, parent_class_model=class_model, local_scope=local_scope)
                return
            # Example: Handle method declarations
            if node.type == 'method_declaration' and parent_class_model:
                method_model = FunctionDefinition(node, file_path)
                name_node = node.child_by_field_name('name')
                if name_node:
                    method_model.hasCanonicalName = name_node.text.decode('utf8')
                modifiers_node = node.child_by_field_name('modifiers')
                if modifiers_node:
                    for mod in modifiers_node.children:
                        if mod.type == 'public' or mod.type == 'private' or mod.type == 'protected':
                            method_model.hasAccessModifier = mod.type
                        if mod.type == 'static':
                            method_model.isStatic = True
                method_model.hasCyclomaticComplexity = 1
                method_model.isAsynchronous = False
                return_type_node = node.child_by_field_name('type')
                if return_type_node:
                    type_name = return_type_node.text.decode('utf8')
                    if type_name and type_name[0].islower():
                        return_type_model = PrimitiveType(return_type_node, file_path)
                    else:
                        return_type_model = ComplexType(return_type_node, file_path)
                    return_type_model.hasCanonicalName = type_name
                    method_model.hasReturnType = return_type_model
                    all_constructs.append(return_type_model)
                all_constructs.append(method_model)
                parent_class_model.add_method(method_model)
                # Extract parameters
                parameters_node = node.child_by_field_name('parameters')
                method_scope = dict(local_scope)  # new scope for method
                if parameters_node:
                    method_model.hasParameter.clear()
                    for param in parameters_node.children:
                        if param.type == 'formal_parameter':
                            param_model = Parameter(param, file_path)
                            name_node = param.child_by_field_name('name')
                            if name_node:
                                param_model.hasCanonicalName = name_node.text.decode('utf8')
                                if param_model.hasCanonicalName in method_scope:
                                    continue
                                method_scope[param_model.hasCanonicalName] = param_model
                            type_node = param.child_by_field_name('type')
                            if type_node:
                                param_model.hasType = type_node.text.decode('utf8')
                            all_constructs.append(param_model)
                            method_model.add_parameter(param_model)
                for child in node.children:
                    traverse(child, parent_class_model=method_model, local_scope=method_scope)
                return
            # Handle attribute (field) declarations inside classes
            if node.type == 'field_declaration' and parent_class_model:
                attr_model = AttributeDeclaration(node, file_path)
                modifiers_node = node.child_by_field_name('modifiers')
                if modifiers_node:
                    for mod in modifiers_node.children:
                        if mod.type == 'public' or mod.type == 'private' or mod.type == 'protected':
                            attr_model.hasAccessModifier = mod.type
                        if mod.type == 'static':
                            attr_model.isStatic = True
                        if mod.type == 'final':
                            attr_model.isFinal = True
                declarator = None
                for child in node.children:
                    if child.type == 'variable_declarator':
                        declarator = child
                        break
                if declarator:
                    name_node = declarator.child_by_field_name('name')
                    if name_node:
                        attr_model.hasCanonicalName = name_node.text.decode('utf8')
                        local_scope[attr_model.hasCanonicalName] = attr_model
                type_node = node.child_by_field_name('type')
                if type_node:
                    attr_model.hasType = type_node.text.decode('utf8')
                all_constructs.append(attr_model)
                if hasattr(parent_class_model, 'add_field'):
                    parent_class_model.add_field(attr_model)
                return
            # Handle local variable declarations inside methods
            if node.type == 'local_variable_declaration' and parent_class_model:
                var_model = VariableDeclaration(node, file_path)
                declarator = None
                for child in node.children:
                    if child.type == 'variable_declarator':
                        declarator = child
                        break
                if declarator:
                    name_node = declarator.child_by_field_name('name')
                    if name_node:
                        var_model.hasCanonicalName = name_node.text.decode('utf8')
                        local_scope[var_model.hasCanonicalName] = var_model
                    type_node = declarator.child_by_field_name('type')
                    if type_node:
                        var_model.hasType = type_node.text.decode('utf8')
                all_constructs.append(var_model)
                if hasattr(parent_class_model, 'add_local_variable'):
                    parent_class_model.add_local_variable(var_model)
                return
            # Handle identifier usage (accesses)
            if node.type == 'identifier' and parent_class_model:
                ident_name = node.text.decode('utf8')
                if isinstance(parent_class_model, FunctionDefinition) and ident_name in local_scope:
                    parent_class_model.add_access(local_scope[ident_name])
                return
            # Handle function/method call sites inside methods
            if node.type == 'method_invocation' and parent_class_model:
                callsite_model = FunctionCallSite(node, file_path)
                name_node = node.child_by_field_name('name')
                if name_node:
                    callsite_model.hasCanonicalName = name_node.text.decode('utf8')
                all_constructs.append(callsite_model)
                # Extract arguments
                arguments_node = node.child_by_field_name('arguments')
                if arguments_node:
                    for arg in arguments_node.children:
                        # Only process non-punctuation nodes
                        if arg.type not in {',', '(', ')'}:
                            arg_model = Argument(arg, file_path)
                            # Try to set canonical name
                            if hasattr(arg_model, 'hasCanonicalName') and hasattr(arg, 'text'):
                                arg_model.hasCanonicalName = arg.text.decode('utf8')
                            arg_model.isArgumentIn = callsite_model
                            callsite_model.hasArgument.append(arg_model)
                            all_constructs.append(arg_model)
                # Relate to parent method (FunctionDefinition) via callsFunction
                if hasattr(parent_class_model, 'callsFunction'):
                    parent_class_model.callsFunction.append(callsite_model)
                return
            # Handle interface declarations
            if node.type == 'interface_declaration':
                interface_model = InterfaceDefinition(node, file_path)
                name_node = node.child_by_field_name('name')
                if name_node:
                    interface_model.hasCanonicalName = name_node.text.decode('utf8')
                    name_registry[interface_model.hasCanonicalName] = interface_model
                # Parse extends (superinterfaces)
                superinterfaces_node = node.child_by_field_name('superinterfaces')
                if superinterfaces_node:
                    for iface in superinterfaces_node.children:
                        if iface.type == 'type_list':
                            for type_id in iface.children:
                                if type_id.type == 'type_identifier':
                                    iface_name = type_id.text.decode('utf8')
                                    if iface_name in name_registry:
                                        interface_model.add_extends_type(name_registry[iface_name])
                all_constructs.append(interface_model)
                # Traverse children with this interface as parent
                for child in node.children:
                    traverse(child, parent_class_model=interface_model)
                return
            # Handle import declarations
            if node.type == 'import_declaration':
                import_model = ImportDeclaration(node, file_path)
                # Try to extract the import path as canonical name
                name_node = node.child_by_field_name('name')
                if name_node:
                    import_model.hasCanonicalName = name_node.text.decode('utf8')
                else:
                    # Fallback: use the source code snippet
                    import_model.hasCanonicalName = import_model.hasSourceCodeSnippet
                all_constructs.append(import_model)
                return
            # Recurse for all children
            for child in node.children:
                traverse(child, parent_class_model=parent_class_model, local_scope=local_scope)

        traverse(tree.root_node)

        # Post-processing: resolve callsFunction for each FunctionCallSite
        # Build a registry of all FunctionDefinition objects by canonical name
        function_registry = {}
        for c in all_constructs:
            if isinstance(c, FunctionDefinition) and c.hasCanonicalName:
                function_registry[c.hasCanonicalName] = c
        for c in all_constructs:
            if isinstance(c, FunctionCallSite) and c.hasCanonicalName:
                target_func = function_registry.get(c.hasCanonicalName)
                if target_func:
                    c.callsFunction = target_func
                    # Set the inverse relationship if not already present
                    if hasattr(target_func, 'isCalledByFunctionAt'):
                        if c not in target_func.isCalledByFunctionAt:
                            target_func.isCalledByFunctionAt.append(c)
                    else:
                        target_func.isCalledByFunctionAt = [c]
                    # Set invokes/isInvokedBy relationships
                    # Find the caller FunctionDefinition (the parent method)
                    caller_func = None
                    for possible_parent in all_constructs:
                        if isinstance(possible_parent, FunctionDefinition):
                            # Check if this callsite is in the callsFunction list of the parent
                            if hasattr(possible_parent, 'callsFunction') and c in possible_parent.callsFunction:
                                caller_func = possible_parent
                                break
                    if caller_func:
                        if hasattr(caller_func, 'invokes'):
                            if target_func not in caller_func.invokes:
                                caller_func.invokes.append(target_func)
                        else:
                            caller_func.invokes = [target_func]
                        if hasattr(target_func, 'isInvokedBy'):
                            if caller_func not in target_func.isInvokedBy:
                                target_func.isInvokedBy.append(caller_func)
                        else:
                            target_func.isInvokedBy = [caller_func]

        return all_constructs
