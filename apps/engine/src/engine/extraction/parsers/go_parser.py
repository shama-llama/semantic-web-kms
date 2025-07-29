import tree_sitter_go
from tree_sitter import Parser
from typing import List

from .base_parser import BaseCodeParser
from ..models.code import (
    CodeConstruct, ClassDefinition, FunctionDefinition, AttributeDeclaration,
    InterfaceDefinition, EnumDefinition, StructDefinition, Parameter, VariableDeclaration, FunctionCallSite, ImportDeclaration,
    PrimitiveType, ComplexType, Argument
)

class GoParser(BaseCodeParser):
    """
    Concrete parser for Go source files. Inherits from BaseCodeParser and implements
    the required methods to provide the Go tree-sitter language and parse Go code.
    """
    def get_language(self):
        """
        Returns the tree-sitter language object for Go.
        Returns:
            Language: The tree-sitter Go language object.
        """
        from tree_sitter import Language
        return Language(tree_sitter_go.language())

    def parse(self, file_content: str, file_path: str) -> List[CodeConstruct]:
        """
        Parses the given Go file content and returns a list of CodeConstructs.
        Args:
            file_content (str): The content of the Go file.
            file_path (str): The path to the Go file.
        Returns:
            List[CodeConstruct]: List of parsed code constructs.
        """
        tree = self.parser.parse(bytes(file_content, "utf8"))
        all_constructs: List[CodeConstruct] = []
        name_registry = {}

        def traverse(node, parent_type_model=None, local_scope=None):
            if local_scope is None:
                local_scope = {}
            
            # Package
            if node.type == 'package_clause':
                name_node = node.child_by_field_name('name')
                if name_node:
                    # This could be a top-level construct if needed, for now just printing
                    print(f"Package: {name_node.text.decode('utf8')}")

            # Import
            if node.type == 'import_declaration':
                import_model = ImportDeclaration(node, file_path)
                # Try to extract the import path as canonical name
                import_spec = None
                for child in node.children:
                    if child.type == 'import_spec':
                        import_spec = child
                        break
                if import_spec:
                    path_node = import_spec.child_by_field_name('path')
                    if path_node:
                        import_model.hasCanonicalName = path_node.text.decode('utf8')
                all_constructs.append(import_model)
                return
            # Interface
            if node.type == 'type_declaration':
                for child in node.children:
                    if child.type == 'type_spec':
                        type_name_node = child.child_by_field_name('name')
                        type_type_node = child.child_by_field_name('type')
                        if type_type_node and type_type_node.type == 'interface_type':
                            interface_model = InterfaceDefinition(child, file_path)
                            if type_name_node:
                                interface_model.hasCanonicalName = type_name_node.text.decode('utf8')
                                name_registry[interface_model.hasCanonicalName] = interface_model
                            all_constructs.append(interface_model)
                            # Methods
                            for iface_child in type_type_node.children:
                                if iface_child.type == 'method_elem':
                                    method_name_node = iface_child.child_by_field_name('name')
                                    method_model = FunctionDefinition(iface_child, file_path)
                                    if method_name_node:
                                        method_model.hasCanonicalName = method_name_node.text.decode('utf8')
                                    method_model.isStatic = False
                                    method_model.hasCyclomaticComplexity = 1
                                    method_model.isAsynchronous = False
                                    # Parameters
                                    params_node = iface_child.child_by_field_name('parameters')
                                    method_scope = dict(local_scope)
                                    if params_node:
                                        for param in params_node.children:
                                            if param.type == 'parameter_declaration':
                                                param_model = Parameter(param, file_path)
                                                name_node = param.child_by_field_name('name')
                                                if name_node:
                                                    param_model.hasCanonicalName = name_node.text.decode('utf8')
                                                    method_scope[param_model.hasCanonicalName] = param_model
                                                type_node = param.child_by_field_name('type')
                                                if type_node:
                                                    param_model.hasType = type_node.text.decode('utf8')
                                                all_constructs.append(param_model)
                                                method_model.add_parameter(param_model)
                                    all_constructs.append(method_model)
                                    interface_model.add_method(method_model)
                            return
                        # Struct
                        if type_type_node and type_type_node.type == 'struct_type':
                            struct_model = StructDefinition(child, file_path)
                            if type_name_node:
                                struct_model.hasCanonicalName = type_name_node.text.decode('utf8')
                                name_registry[struct_model.hasCanonicalName] = struct_model
                            all_constructs.append(struct_model)
                            # Fields
                            field_list = None
                            for st_child in type_type_node.children:
                                if st_child.type == 'field_declaration_list':
                                    field_list = st_child
                                    break
                            if field_list:
                                for field_decl in field_list.children:
                                    if field_decl.type == 'field_declaration':
                                        attr_model = AttributeDeclaration(field_decl, file_path)
                                        name_node = field_decl.child_by_field_name('name')
                                        if name_node:
                                            attr_model.hasCanonicalName = name_node.text.decode('utf8')
                                            local_scope[attr_model.hasCanonicalName] = attr_model
                                        type_node = field_decl.child_by_field_name('type')
                                        if type_node:
                                            attr_model.hasType = type_node.text.decode('utf8')
                                        all_constructs.append(attr_model)
                                        struct_model.add_field(attr_model)
                            return
            # Method (with receiver)
            if node.type == 'method_declaration':
                method_model = FunctionDefinition(node, file_path)
                name_node = node.child_by_field_name('name')
                if name_node:
                    method_model.hasCanonicalName = name_node.text.decode('utf8')
                
                # Receiver
                receiver_node = node.child_by_field_name('receiver')
                if receiver_node:
                    for param_decl in receiver_node.children:
                        if param_decl.type == 'parameter_declaration':
                            type_node = param_decl.child_by_field_name('type')
                            if type_node:
                                receiver_type_name = type_node.text.decode('utf8')
                                if receiver_type_name in name_registry:
                                    receiver_model = name_registry[receiver_type_name]
                                    if isinstance(receiver_model, StructDefinition):
                                        receiver_model.add_method(method_model)

                method_model.isStatic = False
                method_model.hasCyclomaticComplexity = 1
                method_model.isAsynchronous = False
                # Parameters
                params_node = node.child_by_field_name('parameters')
                method_scope = dict(local_scope)
                if params_node:
                    for param in params_node.children:
                        if param.type == 'parameter_declaration':
                            param_model = Parameter(param, file_path)
                            name_node = param.child_by_field_name('name')
                            if name_node:
                                param_model.hasCanonicalName = name_node.text.decode('utf8')
                                method_scope[param_model.hasCanonicalName] = param_model
                            type_node = param.child_by_field_name('type')
                            if type_node:
                                param_model.hasType = type_node.text.decode('utf8')
                            all_constructs.append(param_model)
                            method_model.add_parameter(param_model)
                all_constructs.append(method_model)
                # Traverse body for calls, accesses, etc.
                for child in node.children:
                    traverse(child, parent_type_model=method_model, local_scope=method_scope)
                return
            # Function
            if node.type == 'function_declaration':
                func_model = FunctionDefinition(node, file_path)
                name_node = node.child_by_field_name('name')
                if name_node:
                    func_model.hasCanonicalName = name_node.text.decode('utf8')
                func_model.isStatic = True
                func_model.hasCyclomaticComplexity = 1
                func_model.isAsynchronous = False

                # Return type
                result_node = node.child_by_field_name('result')
                if result_node:
                    type_model = PrimitiveType(result_node, file_path)
                    type_model.hasCanonicalName = result_node.text.decode('utf8')
                    func_model.set_return_type(type_model)

                # Parameters
                params_node = node.child_by_field_name('parameters')
                func_scope = dict(local_scope)
                if params_node:
                    func_model.hasParameter.clear()
                    for param in params_node.children:
                        if param.type == 'parameter_declaration':
                            param_model = Parameter(param, file_path)
                            name_node = param.child_by_field_name('name')
                            if name_node:
                                param_model.hasCanonicalName = name_node.text.decode('utf8')
                                if param_model.hasCanonicalName in func_scope:
                                    continue
                                func_scope[param_model.hasCanonicalName] = param_model
                            type_node = param.child_by_field_name('type')
                            if type_node:
                                param_model.hasType = type_node.text.decode('utf8')
                            all_constructs.append(param_model)
                            func_model.add_parameter(param_model)
                all_constructs.append(func_model)
                # Traverse body for calls, accesses, etc.
                for child in node.children:
                    if child.type != 'parameter_list':
                        traverse(child, parent_type_model=func_model, local_scope=func_scope)
                return
            # Variable declaration
            if node.type == 'var_declaration':
                for child in node.children:
                    if child.type == 'var_spec':
                        var_model = VariableDeclaration(child, file_path)
                        name_node = child.child_by_field_name('name')
                        if name_node:
                            var_model.hasCanonicalName = name_node.text.decode('utf8')
                            local_scope[var_model.hasCanonicalName] = var_model
                        type_node = child.child_by_field_name('type')
                        if type_node:
                            var_model.hasType = type_node.text.decode('utf8')
                        all_constructs.append(var_model)
                return
            # Function call
            if node.type == 'call_expression' and parent_type_model:
                callsite_model = FunctionCallSite(node, file_path)
                function_node = node.child_by_field_name('function')
                if function_node:
                    callsite_model.hasCanonicalName = function_node.text.decode('utf8')
                all_constructs.append(callsite_model)
                # Arguments
                arguments_node = node.child_by_field_name('arguments')
                if arguments_node:
                    for arg in arguments_node.children:
                        if arg.type not in {',', '(', ')'}:
                            arg_model = Argument(arg, file_path)
                            if hasattr(arg_model, 'hasCanonicalName') and hasattr(arg, 'text'):
                                arg_model.hasCanonicalName = arg.text.decode('utf8')
                            arg_model.isArgumentIn = callsite_model
                            callsite_model.hasArgument.append(arg_model)
                            all_constructs.append(arg_model)
                if hasattr(parent_type_model, 'callsFunction'):
                    parent_type_model.callsFunction.append(callsite_model)
                return
            # Identifier usage
            if node.type == 'identifier' and parent_type_model:
                ident_name = node.text.decode('utf8')
                if isinstance(parent_type_model, FunctionDefinition) and ident_name in local_scope:
                    parent_type_model.add_access(local_scope[ident_name])
                return
            # Recurse
            for child in node.children:
                traverse(child, parent_type_model=parent_type_model, local_scope=local_scope)

        traverse(tree.root_node)

        # Post-processing: resolve callsFunction and check for interface implementation
        function_registry = {}
        for c in all_constructs:
            if isinstance(c, FunctionDefinition) and c.hasCanonicalName:
                function_registry[c.hasCanonicalName] = c

        # Check for interface implementations
        for c in all_constructs:
            if isinstance(c, StructDefinition):
                struct_methods = {m.hasCanonicalName for m in c.hasMethod}
                for i in all_constructs:
                    if isinstance(i, InterfaceDefinition):
                        interface_methods = {m.hasCanonicalName for m in i.hasMethod}
                        if interface_methods.issubset(struct_methods):
                            c.add_implements_interface(i)

        for c in all_constructs:
            if isinstance(c, FunctionCallSite) and c.hasCanonicalName:
                target_func = function_registry.get(c.hasCanonicalName)
                if target_func:
                    c.callsFunction = target_func
                    if hasattr(target_func, 'isCalledByFunctionAt'):
                        if c not in target_func.isCalledByFunctionAt:
                            target_func.isCalledByFunctionAt.append(c)
                    else:
                        target_func.isCalledByFunctionAt = [c]
                    caller_func = None
                    for possible_parent in all_constructs:
                        if isinstance(possible_parent, FunctionDefinition):
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
