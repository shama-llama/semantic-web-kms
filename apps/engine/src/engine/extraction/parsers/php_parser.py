import tree_sitter_php
from tree_sitter import Parser
from typing import List

from .base_parser import BaseCodeParser
from ..models.code import (
    CodeConstruct, ClassDefinition, FunctionDefinition, AttributeDeclaration,
    InterfaceDefinition, EnumDefinition, StructDefinition, Parameter, VariableDeclaration, FunctionCallSite, ImportDeclaration,
    PrimitiveType, ComplexType, Argument, TraitDefinition
)

class PHPParser(BaseCodeParser):
    """
    Concrete parser for PHP source files. Inherits from BaseCodeParser and implements
    the required methods to provide the PHP tree-sitter language and parse PHP code.
    """
    def get_language(self):
        """
        Returns the tree-sitter language object for PHP.
        Returns:
            Language: The tree-sitter PHP language object.
        """
        from tree_sitter import Language
        return Language(tree_sitter_php.language_php())

    def parse(self, file_content: str, file_path: str) -> List[CodeConstruct]:
        """
        Parses the given PHP file content and returns a list of CodeConstructs.
        Args:
            file_content (str): The content of the PHP file.
            file_path (str): The path to the PHP file.
        Returns:
            List[CodeConstruct]: List of parsed code constructs.
        """
        tree = self.parser.parse(bytes(file_content, "utf8"))
        all_constructs: List[CodeConstruct] = []
        name_registry = {}

        def traverse(node, parent_type_model=None, local_scope=None):
            if local_scope is None:
                local_scope = {}
            
            # Namespace
            if node.type == 'namespace_definition':
                name_node = node.child_by_field_name('name')
                if name_node:
                    # This could be a top-level construct if needed, for now just printing
                    print(f"Namespace: {name_node.text.decode('utf8')}")

            # Import (use statement)
            if node.type == 'namespace_use_declaration':
                import_model = ImportDeclaration(node, file_path)
                name_node = node.child_by_field_name('name')
                if name_node:
                    import_model.hasCanonicalName = name_node.text.decode('utf8')
                all_constructs.append(import_model)
                return
            # Enum
            if node.type == 'enum_declaration':
                enum_model = EnumDefinition(node, file_path)
                name_node = node.child_by_field_name('name')
                if name_node:
                    enum_model.hasCanonicalName = name_node.text.decode('utf8')
                    name_registry[enum_model.hasCanonicalName] = enum_model
                
                body_node = node.child_by_field_name('body')
                if body_node:
                    for case_node in body_node.children:
                        if case_node.type == 'enum_case':
                            case_model = AttributeDeclaration(case_node, file_path)
                            case_name_node = case_node.child_by_field_name('name')
                            if case_name_node:
                                case_model.hasCanonicalName = case_name_node.text.decode('utf8')
                            all_constructs.append(case_model)
                            enum_model.add_field(case_model)

                all_constructs.append(enum_model)
                for child in node.children:
                    traverse(child, parent_type_model=None, local_scope=local_scope)
                return
            # Interface
            if node.type == 'interface_declaration':
                interface_model = InterfaceDefinition(node, file_path)
                name_node = node.child_by_field_name('name')
                if name_node:
                    interface_model.hasCanonicalName = name_node.text.decode('utf8')
                    name_registry[interface_model.hasCanonicalName] = interface_model
                all_constructs.append(interface_model)
                for child in node.children:
                    traverse(child, parent_type_model=interface_model, local_scope=local_scope)
                return
            
            # Trait
            if node.type == 'trait_declaration':
                trait_model = TraitDefinition(node, file_path)
                name_node = node.child_by_field_name('name')
                if name_node:
                    trait_model.hasCanonicalName = name_node.text.decode('utf8')
                    name_registry[trait_model.hasCanonicalName] = trait_model
                all_constructs.append(trait_model)
                for child in node.children:
                    traverse(child, parent_type_model=trait_model, local_scope=local_scope)
                return

            # Class
            if node.type == 'class_declaration':
                class_model = ClassDefinition(node, file_path)
                name_node = node.child_by_field_name('name')
                if name_node:
                    class_model.hasCanonicalName = name_node.text.decode('utf8')
                    name_registry[class_model.hasCanonicalName] = class_model
                
                # Implements
                implements_node = node.child_by_field_name('interfaces')
                if implements_node:
                    for interface_node in implements_node.children:
                        if interface_node.type == 'name':
                            interface_name = interface_node.text.decode('utf8')
                            if interface_name in name_registry:
                                class_model.add_implements_interface(name_registry[interface_name])

                # Trait usage
                body_node = node.child_by_field_name('body')
                if body_node:
                    for use_node in body_node.children:
                        if use_node.type == 'use_declaration':
                            for trait_name_node in use_node.children:
                                if trait_name_node.type == 'name':
                                    trait_name = trait_name_node.text.decode('utf8')
                                    if trait_name in name_registry:
                                        # In our model, using a trait is like implementing an interface
                                        class_model.add_implements_interface(name_registry[trait_name])
                        # Properties
                        if use_node.type == 'property_declaration':
                            prop_model = AttributeDeclaration(use_node, file_path)
                            # In PHP, property name is inside a property_element node
                            for prop_element in use_node.children:
                                if prop_element.type == 'property_element':
                                    prop_name_node = prop_element.child_by_field_name('name')
                                    if prop_name_node:
                                        prop_model.hasCanonicalName = prop_name_node.text.decode('utf8').lstrip('$')
                            
                            prop_type_node = use_node.child_by_field_name('type')
                            if prop_type_node:
                                type_model = PrimitiveType(prop_type_node, file_path)
                                type_model.hasCanonicalName = prop_type_node.text.decode('utf8')
                                prop_model.set_type(type_model)
                            all_constructs.append(prop_model)
                            class_model.add_field(prop_model)

                # Superclass
                super_node = node.child_by_field_name('base_clause')
                if super_node:
                    for base in super_node.children:
                        if base.type == 'qualified_name':
                            base_name = base.text.decode('utf8')
                            if base_name in name_registry:
                                class_model.add_extends_type(name_registry[base_name])
                all_constructs.append(class_model)
                for child in node.children:
                    traverse(child, parent_type_model=class_model, local_scope=local_scope)
                return

            # Function (top-level)
            if node.type == 'function_definition':
                func_model = FunctionDefinition(node, file_path)
                name_node = node.child_by_field_name('name')
                if name_node:
                    func_model.hasCanonicalName = name_node.text.decode('utf8')
                
                # Parameters
                params_node = node.child_by_field_name('parameters')
                func_scope = dict(local_scope)
                if params_node:
                    func_model.hasParameter.clear()
                    for param in params_node.children:
                        if param.type == 'simple_parameter':
                            param_model = Parameter(param, file_path)
                            name_node = param.child_by_field_name('name')
                            if name_node:
                                param_model.hasCanonicalName = name_node.text.decode('utf8').lstrip('$')
                                if param_model.hasCanonicalName in func_scope:
                                    continue
                                func_scope[param_model.hasCanonicalName] = param_model
                            all_constructs.append(param_model)
                            func_model.add_parameter(param_model)

                all_constructs.append(func_model)
                name_registry[func_model.hasCanonicalName] = func_model
                
                for child in node.children:
                    if child.type != 'formal_parameters':
                        traverse(child, parent_type_model=func_model, local_scope=func_scope)
                return

            # Method
            if node.type == 'method_declaration' and parent_type_model:
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
                        if param.type == 'simple_parameter':
                            param_model = Parameter(param, file_path)
                            name_node = param.child_by_field_name('name')
                            if name_node:
                                param_model.hasCanonicalName = name_node.text.decode('utf8').lstrip('$')
                                if param_model.hasCanonicalName in method_scope:
                                    continue
                                method_scope[param_model.hasCanonicalName] = param_model
                            type_node = param.child_by_field_name('type')
                            if type_node:
                                type_model = PrimitiveType(type_node, file_path)
                                type_model.hasCanonicalName = type_node.text.decode('utf8')
                                param_model.set_type(type_model)
                            all_constructs.append(param_model)
                            method_model.add_parameter(param_model)
                
                # Return type
                return_type_node = node.child_by_field_name('return_type')
                if return_type_node:
                    type_model = PrimitiveType(return_type_node, file_path)
                    type_model.hasCanonicalName = return_type_node.text.decode('utf8')
                    method_model.set_return_type(type_model)
                
                all_constructs.append(method_model)
                if parent_type_model is not None and hasattr(parent_type_model, 'add_method'):
                    parent_type_model.add_method(method_model)
                for child in node.children:
                    if child.type != 'formal_parameters':
                        traverse(child, parent_type_model=method_model, local_scope=method_scope)
                return
            # Variable declaration
            if node.type == 'expression_statement' and node.children and node.children[0].type == 'assignment_expression':
                assignment_node = node.children[0]
                var_model = VariableDeclaration(assignment_node, file_path)
                left_node = assignment_node.child_by_field_name('left')
                if left_node and left_node.type == 'variable_name':
                    var_model.hasCanonicalName = left_node.text.decode('utf8').lstrip('$')
                    local_scope[var_model.hasCanonicalName] = var_model
                    all_constructs.append(var_model)
                return
            
            # Expression Statement containing a call
            if node.type == 'expression_statement' and node.children and node.children[0].type in ['function_call_expression', 'member_call_expression']:
                # The actual call expression is the child, so we traverse down to it
                # and let the dedicated handlers for those types take over.
                # This avoids double-counting.
                traverse(node.children[0], parent_type_model=parent_type_model, local_scope=local_scope)
                return

            # Function call
            if node.type == 'function_call_expression':
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
                
                if parent_type_model and hasattr(parent_type_model, 'callsFunction'):
                    parent_type_model.callsFunction.append(callsite_model)
                elif not parent_type_model:
                     all_constructs.append(callsite_model) # Top-level call

                return
            
            # Member call (e.g., $this->log())
            if node.type == 'member_call_expression':
                callsite_model = FunctionCallSite(node, file_path)
                name_node = node.child_by_field_name('name')
                if name_node:
                    callsite_model.hasCanonicalName = name_node.text.decode('utf8')
                all_constructs.append(callsite_model)
                if parent_type_model and hasattr(parent_type_model, 'callsFunction'):
                    parent_type_model.callsFunction.append(callsite_model)
                return

            # Identifier usage
            if node.type == 'name' and parent_type_model:
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
                    
                    caller_func = None
                    current_node = c.node
                    while current_node:
                        if current_node.type in ['method_declaration', 'function_definition']:
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
