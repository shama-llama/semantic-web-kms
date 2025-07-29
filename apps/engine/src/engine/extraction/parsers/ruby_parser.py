import tree_sitter_ruby
from tree_sitter import Parser
from typing import List

from .base_parser import BaseCodeParser
from ..models.code import (
    CodeConstruct, ClassDefinition, FunctionDefinition, AttributeDeclaration,
    InterfaceDefinition, EnumDefinition, StructDefinition, Parameter, VariableDeclaration, FunctionCallSite, ImportDeclaration,
    PrimitiveType, ComplexType, Argument, TraitDefinition
)

class RubyParser(BaseCodeParser):
    """
    Concrete parser for Ruby source files. Inherits from BaseCodeParser and implements
    the required methods to provide the Ruby tree-sitter language and parse Ruby code.
    """
    def get_language(self):
        """
        Returns the tree-sitter language object for Ruby.
        Returns:
            Language: The tree-sitter Ruby language object.
        """
        from tree_sitter import Language
        return Language(tree_sitter_ruby.language())

    def parse(self, file_content: str, file_path: str) -> List[CodeConstruct]:
        """
        Parses the given Ruby file content and returns a list of CodeConstructs.
        Args:
            file_content (str): The content of the Ruby file.
            file_path (str): The path to the Ruby file.
        Returns:
            List[CodeConstruct]: List of parsed code constructs.
        """
        tree = self.parser.parse(bytes(file_content, "utf8"))
        all_constructs: List[CodeConstruct] = []
        name_registry = {}

        def traverse(node, parent_type_model=None, local_scope=None):
            if local_scope is None:
                local_scope = {}
            # Module (Trait)
            if node.type == 'module':
                trait_model = TraitDefinition(node, file_path)
                name_node = node.child_by_field_name('name')
                if name_node:
                    trait_model.hasCanonicalName = name_node.text.decode('utf8')
                    name_registry[trait_model.hasCanonicalName] = trait_model
                all_constructs.append(trait_model)
                body_node = node.child_by_field_name('body')
                if body_node:
                    for child in body_node.children:
                        traverse(child, parent_type_model=trait_model, local_scope=local_scope)
                return
            # Require/import
            if node.type in {'require', 'require_relative'}:
                import_model = ImportDeclaration(node, file_path)
                arg_node = node.child_by_field_name('argument')
                if arg_node:
                    import_model.hasCanonicalName = arg_node.text.decode('utf8')
                all_constructs.append(import_model)
                return
            # Class
            if node.type == 'class':
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
                    for child in body_node.children:
                        traverse(child, parent_type_model=class_model, local_scope=local_scope)
                return
            # attr_accessor (Field) and include (implements)
            if node.type == 'call' and parent_type_model:
                method_name_node = node.child_by_field_name('method')
                if method_name_node:
                    method_name = method_name_node.text.decode('utf8')
                    # attr_accessor :name -> AttributeDeclaration
                    if method_name == 'attr_accessor':
                        args_node = node.child_by_field_name('arguments')
                        if args_node and args_node.children:
                            # Assuming the first argument is the symbol for the attribute name
                            attr_symbol_node = args_node.children[0]
                            if attr_symbol_node.type == 'simple_symbol':
                                attr_model = AttributeDeclaration(attr_symbol_node, file_path)
                                attr_model.hasCanonicalName = attr_symbol_node.text.decode('utf8').lstrip(':')
                                all_constructs.append(attr_model)
                                parent_type_model.add_field(attr_model)
                        return
                    # include Drawable -> implementsInterface
                    if method_name == 'include':
                        args_node = node.child_by_field_name('arguments')
                        if args_node and args_node.children:
                            # Assuming the first argument is the constant for the module name
                            module_name_node = args_node.children[0]
                            if module_name_node.type == 'constant':
                                module_name = module_name_node.text.decode('utf8')
                                if module_name in name_registry and isinstance(name_registry[module_name], TraitDefinition):
                                    parent_type_model.add_implements_interface(name_registry[module_name])
                        return
            # Method
            if node.type == 'method':
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
                    for param in params_node.children:
                        if param.type == 'identifier':
                            param_model = Parameter(param, file_path)
                            param_model.hasCanonicalName = param.text.decode('utf8')
                            method_scope[param_model.hasCanonicalName] = param_model
                            all_constructs.append(param_model)
                            method_model.add_parameter(param_model)
                all_constructs.append(method_model)
                if parent_type_model is not None and hasattr(parent_type_model, 'add_method'):
                    parent_type_model.add_method(method_model)
                for child in node.children:
                    traverse(child, parent_type_model=method_model, local_scope=method_scope)
                return
            # Variable assignment
            if node.type == 'assignment':
                var_model = VariableDeclaration(node, file_path)
                left_node = node.child_by_field_name('left')
                if left_node:
                    var_model.hasCanonicalName = left_node.text.decode('utf8')
                    local_scope[var_model.hasCanonicalName] = var_model
                all_constructs.append(var_model)
                return
            # Function call
            if node.type == 'call':
                # First, handle specific call types like attr_accessor and include inside a class/module
                if parent_type_model:
                    method_name_node = node.child_by_field_name('method')
                    if method_name_node:
                        method_name = method_name_node.text.decode('utf8')
                        if method_name == 'attr_accessor':
                            args_node = node.child_by_field_name('arguments')
                            if args_node and args_node.children and args_node.children[0].type == 'simple_symbol':
                                attr_model = AttributeDeclaration(args_node.children[0], file_path)
                                attr_model.hasCanonicalName = args_node.children[0].text.decode('utf8').lstrip(':')
                                all_constructs.append(attr_model)
                                if hasattr(parent_type_model, 'add_field'):
                                    parent_type_model.add_field(attr_model)
                            return
                        if method_name == 'include':
                            args_node = node.child_by_field_name('arguments')
                            if args_node and args_node.children and args_node.children[0].type == 'constant':
                                module_name = args_node.children[0].text.decode('utf8')
                                if module_name in name_registry and isinstance(name_registry.get(module_name), TraitDefinition):
                                    if hasattr(parent_type_model, 'add_implements_interface'):
                                        parent_type_model.add_implements_interface(name_registry[module_name])
                            return

                # Generic function call
                callsite_model = FunctionCallSite(node, file_path)
                function_node = node.child_by_field_name('method')
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
