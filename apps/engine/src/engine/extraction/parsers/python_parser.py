import tree_sitter_python
from tree_sitter import Parser
from typing import List

from .base_parser import BaseCodeParser
from ..models.code import (
    CodeConstruct, ClassDefinition, FunctionDefinition, AttributeDeclaration,
    InterfaceDefinition, EnumDefinition, StructDefinition, Parameter, VariableDeclaration, FunctionCallSite, ImportDeclaration,
    PrimitiveType, ComplexType, Argument
)

class PythonParser(BaseCodeParser):
    """
    Concrete parser for Python source files. Inherits from BaseCodeParser and implements
    the required methods to provide the Python tree-sitter language and parse Python code.
    """
    def get_language(self):
        """
        Returns the tree-sitter language object for Python.
        Returns:
            Language: The tree-sitter Python language object.
        """
        from tree_sitter import Language
        return Language(tree_sitter_python.language())

    def parse(self, file_content: str, file_path: str) -> List[CodeConstruct]:
        """
        Parses the given Python file content and returns a list of CodeConstructs.
        Args:
            file_content (str): The content of the Python file.
            file_path (str): The path to the Python file.
        Returns:
            List[CodeConstruct]: List of parsed code constructs.
        """
        tree = self.parser.parse(bytes(file_content, "utf8"))
        all_constructs: List[CodeConstruct] = []
        name_registry = {}

        def traverse(node, parent_type_model=None, local_scope=None):
            if local_scope is None:
                local_scope = {}
            # Import
            if node.type == 'import_statement':
                import_model = ImportDeclaration(node, file_path)
                # Try to extract the import path as canonical name
                name_node = node.child_by_field_name('name')
                if name_node:
                    import_model.hasCanonicalName = name_node.text.decode('utf8')
                all_constructs.append(import_model)
                return

            if node.type == 'import_from_statement':
                import_model = ImportDeclaration(node, file_path)
                module_name_node = node.child_by_field_name('module_name')
                module_name = module_name_node.text.decode('utf8') if module_name_node else ''
                
                names_node = node.child_by_field_name('name')
                if names_node:
                    # from module import a, b, c
                    imported_names = [child.text.decode('utf8') for child in names_node.children if child.type == 'identifier']
                    import_model.hasCanonicalName = f"from {module_name} import {', '.join(imported_names)}"
                else:
                    # from module import *
                    import_model.hasCanonicalName = f"from {module_name} import *"

                all_constructs.append(import_model)
                return

            # Class
            if node.type == 'class_definition':
                class_model = ClassDefinition(node, file_path)
                name_node = node.child_by_field_name('name')
                if name_node:
                    class_model.hasCanonicalName = name_node.text.decode('utf8')
                    name_registry[class_model.hasCanonicalName] = class_model
                # Superclass
                super_node = node.child_by_field_name('superclasses')
                if super_node:
                    for base in super_node.children:
                        if base.type == 'identifier':
                            base_name = base.text.decode('utf8')
                            # Create a placeholder ComplexType if not in registry
                            base_class_model = name_registry.get(base_name)
                            if not base_class_model:
                                base_class_model = ComplexType(base, file_path)
                                base_class_model.hasCanonicalName = base_name
                            class_model.add_extends_type(base_class_model)
                all_constructs.append(class_model)
                class_scope = {}
                for child in node.children:
                    if child.type == 'block':
                        for statement in child.children:
                             # Look for attribute declarations: name: str
                            if statement.type == 'expression_statement':
                                assignment_node = statement.children[0]
                                if assignment_node.type == 'assignment' and assignment_node.child_by_field_name('type'):
                                    attr_model = AttributeDeclaration(assignment_node, file_path)
                                    name_node = assignment_node.child_by_field_name('left')
                                    type_node = assignment_node.child_by_field_name('type')
                                    if name_node:
                                        attr_model.hasCanonicalName = name_node.text.decode('utf8')
                                    if type_node:
                                        type_model = PrimitiveType(type_node, file_path)
                                        type_model.hasCanonicalName = type_node.text.decode('utf8')
                                        attr_model.set_type(type_model)
                                    all_constructs.append(attr_model)
                                    class_model.add_field(attr_model)
                                    class_scope[attr_model.hasCanonicalName] = attr_model
                    traverse(child, parent_type_model=class_model, local_scope={**local_scope, **class_scope})
                return
            # Function/method
            if node.type == 'function_definition':
                func_model = FunctionDefinition(node, file_path)
                name_node = node.child_by_field_name('name')
                if name_node:
                    func_model.hasCanonicalName = name_node.text.decode('utf8')
                func_model.isStatic = False
                func_model.hasCyclomaticComplexity = 1
                func_model.isAsynchronous = False
                # Parameters
                params_node = node.child_by_field_name('parameters')
                func_scope = dict(local_scope)
                if params_node:
                    # Clear existing parameters to avoid duplicates from different scopes
                    func_model.hasParameter.clear()
                    for param in params_node.children:
                        param_model = None
                        if param.type == 'identifier':
                            param_model = Parameter(param, file_path)
                            param_model.hasCanonicalName = param.text.decode('utf8')
                        elif param.type == 'typed_parameter':
                            param_model = Parameter(param, file_path)
                            name_node = param.children[0]
                            type_node = param.children[2] if len(param.children) > 2 else None
                            if name_node:
                                param_model.hasCanonicalName = name_node.text.decode('utf8')
                            if type_node:
                                type_model = PrimitiveType(type_node, file_path)
                                type_model.hasCanonicalName = type_node.text.decode('utf8')
                                param_model.set_type(type_model)
                        
                        if param_model:
                            if param_model.hasCanonicalName in func_scope:
                                continue
                            func_scope[param_model.hasCanonicalName] = param_model
                            all_constructs.append(param_model)
                            func_model.add_parameter(param_model)

                all_constructs.append(func_model)
                if parent_type_model and isinstance(parent_type_model, ComplexType):
                     parent_type_model.add_method(func_model)

                for child in node.children:
                    traverse(child, parent_type_model=func_model, local_scope=func_scope)
                return
            # Variable assignment
            if node.type == 'assignment':
                var_model = VariableDeclaration(node, file_path)
                target_node = node.child_by_field_name('left')
                if target_node:
                    var_model.hasCanonicalName = target_node.text.decode('utf8')
                    local_scope[var_model.hasCanonicalName] = var_model
                all_constructs.append(var_model)
                return
            # Function call
            if node.type == 'call' and parent_type_model:
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
                    # Avoid re-adding parameters as accesses
                    if not any(p.hasCanonicalName == ident_name for p in parent_type_model.hasParameter):
                        parent_type_model.add_access(local_scope[ident_name])
                return
            # Top-level function call
            if node.type == 'call' and not parent_type_model:
                callsite_model = FunctionCallSite(node, file_path)
                function_node = node.child_by_field_name('function')
                if function_node:
                    callsite_model.hasCanonicalName = function_node.text.decode('utf8')
                
                arguments_node = node.child_by_field_name('arguments')
                if arguments_node:
                    for arg in arguments_node.children:
                        if arg.type not in {',', '(', ')'}:
                            arg_model = Argument(arg, file_path)
                            arg_model.hasCanonicalName = arg.text.decode('utf8')
                            arg_model.isArgumentIn = callsite_model
                            callsite_model.hasArgument.append(arg_model)
                            all_constructs.append(arg_model)

                all_constructs.append(callsite_model)
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
                    if not hasattr(target_func, 'isCalledByFunctionAt'):
                        target_func.isCalledByFunctionAt = []
                    if c not in target_func.isCalledByFunctionAt:
                        target_func.isCalledByFunctionAt.append(c)
                    
                    caller_func = None
                    # Walk up the parent chain to find the containing function
                    current_node = c.node
                    while current_node:
                        if current_node.type == 'function_definition':
                            func_name_node = current_node.child_by_field_name('name')
                            if func_name_node:
                                caller_name = func_name_node.text.decode('utf8')
                                caller_func = function_registry.get(caller_name)
                            break
                        current_node = current_node.parent

                    if caller_func:
                        if not hasattr(caller_func, 'invokes'):
                            caller_func.invokes = []
                        if target_func not in caller_func.invokes:
                            caller_func.invokes.append(target_func)
                        
                        if not hasattr(target_func, 'isInvokedBy'):
                            target_func.isInvokedBy = []
                        if caller_func not in target_func.isInvokedBy:
                            target_func.isInvokedBy.append(caller_func)

        return all_constructs
