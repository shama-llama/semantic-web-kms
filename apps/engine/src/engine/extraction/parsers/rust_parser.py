import tree_sitter_rust
from tree_sitter import Parser
from typing import List

from .base_parser import BaseCodeParser
from ..models.code import (
    CodeConstruct, ClassDefinition, FunctionDefinition, AttributeDeclaration,
    InterfaceDefinition, EnumDefinition, StructDefinition, Parameter, VariableDeclaration, FunctionCallSite, ImportDeclaration,
    PrimitiveType, ComplexType, Argument, TraitDefinition
)

class RustParser(BaseCodeParser):
    """
    Concrete parser for Rust source files. Inherits from BaseCodeParser and implements
    the required methods to provide the Rust tree-sitter language and parse Rust code.
    """
    def get_language(self):
        """
        Returns the tree-sitter language object for Rust.
        Returns:
            Language: The tree-sitter Rust language object.
        """
        from tree_sitter import Language
        return Language(tree_sitter_rust.language())

    def parse(self, file_content: str, file_path: str) -> List[CodeConstruct]:
        """
        Parses the given Rust file content and returns a list of CodeConstructs.
        Args:
            file_content (str): The content of the Rust file.
            file_path (str): The path to the Rust file.
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
            if node.type == 'use_declaration':
                import_model = ImportDeclaration(node, file_path)
                path_node = node.child_by_field_name('argument')
                if path_node:
                    import_model.hasCanonicalName = path_node.text.decode('utf8')
                all_constructs.append(import_model)
                return
            # Enum
            if node.type == 'enum_item':
                enum_model = EnumDefinition(node, file_path)
                name_node = node.child_by_field_name('name')
                if name_node:
                    enum_model.hasCanonicalName = name_node.text.decode('utf8')
                    name_registry[enum_model.hasCanonicalName] = enum_model
                all_constructs.append(enum_model)
                # Enum variants
                body_node = node.child_by_field_name('body')
                if body_node:
                    for variant in body_node.children:
                        if variant.type == 'enum_variant':
                            variant_name_node = variant.child_by_field_name('name')
                            if variant_name_node:
                                variant_model = CodeConstruct(variant, file_path)
                                variant_model.hasCanonicalName = variant_name_node.text.decode('utf8')
                                all_constructs.append(variant_model)
                for child in node.children:
                    traverse(child, parent_type_model=None, local_scope=local_scope)
                return
            # Struct
            if node.type == 'struct_item':
                struct_model = StructDefinition(node, file_path)
                name_node = node.child_by_field_name('name')
                if name_node:
                    struct_model.hasCanonicalName = name_node.text.decode('utf8')
                    name_registry[struct_model.hasCanonicalName] = struct_model
                all_constructs.append(struct_model)
                # Fields
                field_list = node.child_by_field_name('body')
                if field_list:
                    for field_decl in field_list.children:
                        if field_decl.type == 'struct_field':
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
                for child in node.children:
                    traverse(child, parent_type_model=struct_model, local_scope=local_scope)
                return
            # Trait
            if node.type == 'trait_item':
                trait_model = TraitDefinition(node, file_path)
                name_node = node.child_by_field_name('name')
                if name_node:
                    trait_model.hasCanonicalName = name_node.text.decode('utf8')
                    name_registry[trait_model.hasCanonicalName] = trait_model
                all_constructs.append(trait_model)
                # Trait methods
                body_node = node.child_by_field_name('body')
                if body_node:
                    for decl in body_node.children:
                        if decl.type == 'function_signature_item':
                            method_model = FunctionDefinition(decl, file_path)
                            name_node = decl.child_by_field_name('name')
                            if name_node:
                                method_model.hasCanonicalName = name_node.text.decode('utf8')
                            trait_model.add_method(method_model)
                            all_constructs.append(method_model)
                for child in node.children:
                    traverse(child, parent_type_model=trait_model, local_scope=local_scope)
                return
            # Impl block (methods for struct/trait)
            if node.type == 'impl_item':
                # Check if this is an impl for a trait for a type
                trait_node = node.child_by_field_name('trait')
                type_node = node.child_by_field_name('type')
                if trait_node and type_node:
                    trait_name = trait_node.text.decode('utf8')
                    type_name = type_node.text.decode('utf8')
                    if type_name in name_registry and trait_name in name_registry:
                        struct_model = name_registry[type_name]
                        trait_model = name_registry[trait_name]
                        if hasattr(struct_model, 'add_implements_interface'):
                            struct_model.add_implements_interface(trait_model)
                # Traverse impl body for methods
                for child in node.children:
                    traverse(child, parent_type_model=parent_type_model, local_scope=local_scope)
                return
            # Function
            if node.type == 'function_item':
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
                    for param in params_node.children:
                        if param.type == 'parameter':
                            param_model = Parameter(param, file_path)
                            name_node = param.child_by_field_name('pattern')
                            if name_node:
                                param_model.hasCanonicalName = name_node.text.decode('utf8')
                                func_scope[param_model.hasCanonicalName] = param_model
                            type_node = param.child_by_field_name('type')
                            if type_node:
                                param_model.hasType = type_node.text.decode('utf8')
                            all_constructs.append(param_model)
                            func_model.add_parameter(param_model)
                all_constructs.append(func_model)
                for child in node.children:
                    traverse(child, parent_type_model=func_model, local_scope=func_scope)
                return
            # Variable declaration
            if node.type == 'let_declaration':
                var_model = VariableDeclaration(node, file_path)
                name_node = node.child_by_field_name('pattern')
                if name_node:
                    var_model.hasCanonicalName = name_node.text.decode('utf8')
                    local_scope[var_model.hasCanonicalName] = var_model
                type_node = node.child_by_field_name('type')
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
