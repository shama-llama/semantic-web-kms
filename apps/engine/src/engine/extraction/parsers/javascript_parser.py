import tree_sitter_javascript
from tree_sitter import Parser
from typing import List

from .base_parser import BaseCodeParser
from ..models.code import (
    CodeConstruct, ClassDefinition, FunctionDefinition, AttributeDeclaration,
    InterfaceDefinition, EnumDefinition, StructDefinition, Parameter, VariableDeclaration, FunctionCallSite, ImportDeclaration,
    PrimitiveType, ComplexType, Argument
)

class JavaScriptParser(BaseCodeParser):
    """
    Concrete parser for JavaScript source files. Inherits from BaseCodeParser and implements
    the required methods to provide the JavaScript tree-sitter language and parse JavaScript code.
    """
    def get_language(self):
        """
        Returns the tree-sitter language object for JavaScript.
        Returns:
            Language: The tree-sitter JavaScript language object.
        """
        from tree_sitter import Language
        return Language(tree_sitter_javascript.language())

    def parse(self, file_content: str, file_path: str) -> List[CodeConstruct]:
        """
        Parses the given JavaScript file content and returns a list of CodeConstructs.
        Args:
            file_content (str): The content of the JavaScript file.
            file_path (str): The path to the JavaScript file.
        Returns:
            List[CodeConstruct]: List of parsed code constructs.
        """
        tree = self.parser.parse(bytes(file_content, "utf8"))
        all_constructs: List[CodeConstruct] = []
        name_registry = {}

        def traverse(node, parent_type_model=None, local_scope=None):
            if local_scope is None:
                local_scope = {}
            # Import (import_declaration, require, etc.)
            if node.type == 'import_statement':
                import_model = ImportDeclaration(node, file_path)
                source_node = node.child_by_field_name('source')
                if source_node:
                    import_model.hasCanonicalName = source_node.text.decode('utf8')
                all_constructs.append(import_model)
                return
            # JSDoc Interface
            if node.type == 'function_declaration':
                comment_node = node.prev_sibling
                if comment_node and comment_node.type == 'comment' and '@interface' in comment_node.text.decode('utf8'):
                    interface_model = InterfaceDefinition(node, file_path)
                    name_node = node.child_by_field_name('name')
                    if name_node:
                        interface_model.hasCanonicalName = name_node.text.decode('utf8')
                        name_registry[interface_model.hasCanonicalName] = interface_model
                    all_constructs.append(interface_model)
                    return
            # Class
            if node.type == 'class_declaration':
                class_model = ClassDefinition(node, file_path)
                name_node = node.child_by_field_name('name')
                if name_node:
                    class_model.hasCanonicalName = name_node.text.decode('utf8')
                    name_registry[class_model.hasCanonicalName] = class_model
                # Superclass
                super_node = node.child_by_field_name('superclass')
                if super_node:
                    super_name = super_node.text.decode('utf8')
                    if super_name in name_registry:
                        class_model.add_extends_type(name_registry[super_name])
                all_constructs.append(class_model)
                
                body_node = node.child_by_field_name('body')
                if body_node:
                    for member in body_node.children:
                        if member.type == 'field_definition':
                            attr_model = AttributeDeclaration(member, file_path)
                            name_node = member.child_by_field_name('property')
                            if name_node:
                                attr_model.hasCanonicalName = name_node.text.decode('utf8')
                            all_constructs.append(attr_model)
                            class_model.add_field(attr_model)
                        else:
                            traverse(member, parent_type_model=class_model, local_scope=local_scope)
                return
            # Method
            if node.type == 'method_definition' and parent_type_model:
                method_model = FunctionDefinition(node, file_path)
                name_node = node.child_by_field_name('name')
                if name_node:
                    method_model.hasCanonicalName = name_node.text.decode('utf8')
                method_model.isStatic = False
                method_model.hasCyclomaticComplexity = 1
                method_model.isAsynchronous = False
                # Parameters
                params_node = node.child_by_field_name('parameters')
                method_scope = dict(local_scope)
                if params_node:
                    method_model.hasParameter.clear()
                    for param in params_node.children:
                        if param.type == 'identifier':
                            param_model = Parameter(param, file_path)
                            param_model.hasCanonicalName = param.text.decode('utf8')
                            if param_model.hasCanonicalName in method_scope:
                                continue
                            method_scope[param_model.hasCanonicalName] = param_model
                            all_constructs.append(param_model)
                            method_model.add_parameter(param_model)
                all_constructs.append(method_model)
                if hasattr(parent_type_model, 'add_method'):
                    parent_type_model.add_method(method_model)
                for child in node.children:
                    traverse(child, parent_type_model=method_model, local_scope=method_scope)
                return
            # Function (function_declaration, function_expression, arrow_function)
            if node.type in {'function_declaration', 'function_expression', 'arrow_function'}:
                func_model = FunctionDefinition(node, file_path)
                name_node = node.child_by_field_name('name')
                if name_node:
                    func_model.hasCanonicalName = name_node.text.decode('utf8')
                func_model.isStatic = True
                func_model.hasCyclomaticComplexity = 1
                func_model.isAsynchronous = False
                # Parameters
                params_node = node.child_by_field_name('parameters')
                func_scope = dict(local_scope)
                if params_node:
                    func_model.hasParameter.clear()
                    for param in params_node.children:
                        if param.type == 'identifier':
                            param_model = Parameter(param, file_path)
                            param_model.hasCanonicalName = param.text.decode('utf8')
                            if param_model.hasCanonicalName in func_scope:
                                continue
                            func_scope[param_model.hasCanonicalName] = param_model
                            all_constructs.append(param_model)
                            func_model.add_parameter(param_model)
                all_constructs.append(func_model)
                for child in node.children:
                    traverse(child, parent_type_model=func_model, local_scope=func_scope)
                return
            # Variable and Lexical Declarations (var, let, const)
            if node.type in {'variable_declaration', 'lexical_declaration'}:
                for child in node.children:
                    if child.type == 'variable_declarator':
                        # Check if the value is an object, which we'll treat as an enum
                        value_node = child.child_by_field_name('value')
                        if value_node and value_node.type == 'object':
                            enum_model = EnumDefinition(child, file_path)
                            name_node = child.child_by_field_name('name')
                            if name_node:
                                enum_model.hasCanonicalName = name_node.text.decode('utf8')
                                name_registry[enum_model.hasCanonicalName] = enum_model
                            all_constructs.append(enum_model)
                            # Parse enum members
                            for pair in value_node.children:
                                if pair.type == 'pair':
                                    member_name_node = pair.child_by_field_name('key')
                                    if member_name_node:
                                        member_model = AttributeDeclaration(pair, file_path)
                                        member_model.hasCanonicalName = member_name_node.text.decode('utf8')
                                        all_constructs.append(member_model)
                                        enum_model.add_field(member_model)
                        else:
                            var_model = VariableDeclaration(child, file_path)
                            name_node = child.child_by_field_name('name')
                            if name_node:
                                var_model.hasCanonicalName = name_node.text.decode('utf8')
                                local_scope[var_model.hasCanonicalName] = var_model
                            all_constructs.append(var_model)
                return
            # Export statement
            if node.type == 'export_statement':
                export_model = CodeConstruct(node, file_path)
                export_model.hasCanonicalName = "export" # Or parse specifiers
                all_constructs.append(export_model)
                return
            # Top-level function call
            if node.type == 'expression_statement' and parent_type_model is None:
                for child in node.children:
                    if child.type == 'call_expression':
                        callsite_model = FunctionCallSite(child, file_path)
                        function_node = child.child_by_field_name('function')
                        if function_node:
                            callsite_model.hasCanonicalName = function_node.text.decode('utf8')
                        all_constructs.append(callsite_model)
                        # Arguments
                        arguments_node = child.child_by_field_name('arguments')
                        if arguments_node:
                            for arg in arguments_node.children:
                                if arg.type not in {',', '(', ')'}:
                                    arg_model = Argument(arg, file_path)
                                    if hasattr(arg_model, 'hasCanonicalName') and hasattr(arg, 'text'):
                                        arg_model.hasCanonicalName = arg.text.decode('utf8')
                                    arg_model.isArgumentIn = callsite_model
                                    callsite_model.hasArgument.append(arg_model)
                                    all_constructs.append(arg_model)
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

        # Post-processing: resolve callsFunction for each FunctionCallSite
        function_registry = {}
        for c in all_constructs:
            if isinstance(c, FunctionDefinition) and c.hasCanonicalName:
                function_registry[c.hasCanonicalName] = c
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
