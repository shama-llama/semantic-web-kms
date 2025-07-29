import tree_sitter_c_sharp
from tree_sitter import Parser
from typing import List

from .base_parser import BaseCodeParser
from ..models.code import (
    CodeConstruct, ClassDefinition, FunctionDefinition, AttributeDeclaration,
    InterfaceDefinition, EnumDefinition, StructDefinition, Parameter, VariableDeclaration, FunctionCallSite, ImportDeclaration,
    PrimitiveType, ComplexType, Argument
)

class CSharpParser(BaseCodeParser):
    """
    Concrete parser for C# source files. Inherits from BaseCodeParser and implements
    the required methods to provide the C# tree-sitter language and parse C# code.
    """
    def get_language(self):
        """
        Returns the tree-sitter language object for C#.
        Returns:
            Language: The tree-sitter C# language object.
        """
        from tree_sitter import Language
        return Language(tree_sitter_c_sharp.language())

    def parse(self, file_content: str, file_path: str) -> List[CodeConstruct]:
        """
        Parses the given C# file content and returns a list of CodeConstructs.
        Args:
            file_content (str): The content of the C# file.
            file_path (str): The path to the C# file.
        Returns:
            List[CodeConstruct]: List of parsed code constructs.
        """
        tree = self.parser.parse(bytes(file_content, "utf8"))
        all_constructs: List[CodeConstruct] = []
        name_registry = {}

        def traverse(node, parent_class_model=None, local_scope=None):
            if local_scope is None:
                local_scope = {}
            # Enum
            if node.type == 'enum_declaration':
                enum_model = EnumDefinition(node, file_path)
                name_node = node.child_by_field_name('name')
                if name_node:
                    enum_model.hasCanonicalName = name_node.text.decode('utf8')
                    name_registry[enum_model.hasCanonicalName] = enum_model
                all_constructs.append(enum_model)
                # Enum members
                body_node = node.child_by_field_name('body')
                if body_node:
                    for child in body_node.children:
                        if child.type == 'enum_member_declaration':
                            member_name_node = child.child_by_field_name('name')
                            if member_name_node:
                                member_model = AttributeDeclaration(child, file_path)
                                member_model.hasCanonicalName = member_name_node.text.decode('utf8')
                                all_constructs.append(member_model)
                                enum_model.add_field(member_model)
                for child in node.children:
                    traverse(child, parent_class_model=None, local_scope=local_scope)
                return
            # Struct
            if node.type == 'struct_declaration':
                struct_model = StructDefinition(node, file_path)
                name_node = node.child_by_field_name('name')
                if name_node:
                    struct_model.hasCanonicalName = name_node.text.decode('utf8')
                    name_registry[struct_model.hasCanonicalName] = struct_model
                all_constructs.append(struct_model)
                for child in node.children:
                    traverse(child, parent_class_model=struct_model, local_scope=local_scope)
                return
            # Class
            if node.type == 'class_declaration':
                class_model = ClassDefinition(node, file_path)
                name_node = node.child_by_field_name('name')
                if name_node:
                    class_model.hasCanonicalName = name_node.text.decode('utf8')
                    name_registry[class_model.hasCanonicalName] = class_model
                # Base types (extends/implements)
                base_list = node.child_by_field_name('base')
                if base_list:
                    for base in base_list.children:
                        if base.type == 'identifier':
                            base_name = base.text.decode('utf8')
                            if base_name in name_registry:
                                # If the base is an interface, add as implementsInterface
                                if isinstance(name_registry[base_name], InterfaceDefinition):
                                    class_model.add_implements_interface(name_registry[base_name])
                                else:
                                    class_model.add_extends_type(name_registry[base_name])
                all_constructs.append(class_model)
                for child in node.children:
                    traverse(child, parent_class_model=class_model, local_scope=local_scope)
                return
            # Interface
            if node.type == 'interface_declaration':
                interface_model = InterfaceDefinition(node, file_path)
                name_node = node.child_by_field_name('name')
                if name_node:
                    interface_model.hasCanonicalName = name_node.text.decode('utf8')
                    name_registry[interface_model.hasCanonicalName] = interface_model
                # Extends (superinterfaces)
                base_list = node.child_by_field_name('base_list')
                if base_list:
                    for base in base_list.children:
                        if base.type == 'identifier':
                            base_name = base.text.decode('utf8')
                            if base_name in name_registry:
                                interface_model.add_extends_type(name_registry[base_name])
                all_constructs.append(interface_model)
                for child in node.children:
                    traverse(child, parent_class_model=interface_model, local_scope=local_scope)
                return
            # Method/Constructor
            if node.type in {'method_declaration', 'constructor_declaration'}:
                method_model = FunctionDefinition(node, file_path)
                name_node = node.child_by_field_name('name')
                if name_node:
                    method_model.hasCanonicalName = name_node.text.decode('utf8')
                modifiers_node = None
                for child in node.children:
                    if child.type == 'modifier':
                        modifiers_node = child
                        break
                if modifiers_node:
                    mod_text = modifiers_node.text.decode('utf8')
                    if mod_text in {'public', 'private', 'protected', 'internal'}:
                        method_model.hasAccessModifier = mod_text
                    if 'static' in mod_text:
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
                if parent_class_model and hasattr(parent_class_model, 'add_method'):
                    parent_class_model.add_method(method_model)
                # Parameters
                parameters_node = node.child_by_field_name('parameters')
                method_scope = dict(local_scope)
                if parameters_node:
                    method_model.hasParameter.clear()
                    for param in parameters_node.children:
                        if param.type == 'parameter':
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
            # Field/Property
            if node.type in {'field_declaration', 'property_declaration'}:
                attr_model = AttributeDeclaration(node, file_path)
                modifiers_node = None
                for child in node.children:
                    if child.type == 'modifier':
                        modifiers_node = child
                        break
                if modifiers_node:
                    mod_text = modifiers_node.text.decode('utf8')
                    if mod_text in {'public', 'private', 'protected', 'internal'}:
                        attr_model.hasAccessModifier = mod_text
                    if 'static' in mod_text:
                        attr_model.isStatic = True
                    if 'final' in mod_text or 'readonly' in mod_text:
                        attr_model.isFinal = True
                declarator = None
                for child in node.children:
                    if child.type == 'variable_declaration':
                        declarator = child
                        break
                if declarator:
                    name_node = None
                    for child in declarator.children:
                        if child.type == 'variable_declarator':
                            name_node = child.child_by_field_name('name')
                            break
                    if name_node:
                        attr_model.hasCanonicalName = name_node.text.decode('utf8')
                        local_scope[attr_model.hasCanonicalName] = attr_model
                type_node = node.child_by_field_name('type')
                if type_node:
                    attr_model.hasType = type_node.text.decode('utf8')
                all_constructs.append(attr_model)
                if parent_class_model and hasattr(parent_class_model, 'add_field'):
                    parent_class_model.add_field(attr_model)
                return
            # Local variable
            if node.type == 'local_declaration_statement':
                var_model = VariableDeclaration(node, file_path)
                declarator = None
                for child in node.children:
                    if child.type == 'variable_declaration':
                        declarator = child
                        break
                if declarator:
                    name_node = None
                    for child in declarator.children:
                        if child.type == 'variable_declarator':
                            name_node = child.child_by_field_name('name')
                            break
                    if name_node:
                        var_model.hasCanonicalName = name_node.text.decode('utf8')
                        local_scope[var_model.hasCanonicalName] = var_model
                    type_node = declarator.child_by_field_name('type')
                    if type_node:
                        var_model.hasType = type_node.text.decode('utf8')
                all_constructs.append(var_model)
                if parent_class_model and hasattr(parent_class_model, 'add_local_variable'):
                    parent_class_model.add_local_variable(var_model)
                return
            # Global variable (no parent_class_model)
            if node.type == 'local_declaration_statement' and parent_class_model is None:
                var_model = VariableDeclaration(node, file_path)
                declarator = None
                for child in node.children:
                    if child.type == 'variable_declaration':
                        declarator = child
                        break
                if declarator:
                    name_node = None
                    for child in declarator.children:
                        if child.type == 'variable_declarator':
                            name_node = child.child_by_field_name('name')
                            break
                    if name_node:
                        var_model.hasCanonicalName = name_node.text.decode('utf8')
                        local_scope[var_model.hasCanonicalName] = var_model
                    type_node = declarator.child_by_field_name('type')
                    if type_node:
                        var_model.hasType = type_node.text.decode('utf8')
                all_constructs.append(var_model)
                return
            # Global function (no parent_class_model)
            if node.type == 'local_function_statement' and parent_class_model is None:
                func_model = FunctionDefinition(node, file_path)
                name_node = node.child_by_field_name('name')
                if name_node:
                    func_model.hasCanonicalName = name_node.text.decode('utf8')
                modifiers_node = None
                for child in node.children:
                    if child.type == 'modifier':
                        modifiers_node = child
                        break
                if modifiers_node:
                    mod_text = modifiers_node.text.decode('utf8')
                    if mod_text in {'public', 'private', 'protected', 'internal'}:
                        func_model.hasAccessModifier = mod_text
                    if 'static' in mod_text:
                        func_model.isStatic = True
                func_model.hasCyclomaticComplexity = 1
                func_model.isAsynchronous = False
                return_type_node = node.child_by_field_name('type')
                if return_type_node:
                    type_name = return_type_node.text.decode('utf8')
                    if type_name and type_name[0].islower():
                        return_type_model = PrimitiveType(return_type_node, file_path)
                    else:
                        return_type_model = ComplexType(return_type_node, file_path)
                    return_type_model.hasCanonicalName = type_name
                    func_model.hasReturnType = return_type_model
                    all_constructs.append(return_type_model)
                all_constructs.append(func_model)
                # Parameters
                parameters_node = node.child_by_field_name('parameters')
                func_scope = dict(local_scope)
                if parameters_node:
                    func_model.hasParameter.clear()
                    for param in parameters_node.children:
                        if param.type == 'parameter':
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
                for child in node.children:
                    traverse(child, parent_class_model=func_model, local_scope=func_scope)
                return
            # Global function call (no parent_class_model)
            if node.type == 'expression_statement' and parent_class_model is None:
                # Check if this is a function call
                for child in node.children:
                    if child.type == 'invocation_expression':
                        callsite_model = FunctionCallSite(child, file_path)
                        function_node = child.child_by_field_name('function')
                        if function_node:
                            callsite_model.hasCanonicalName = function_node.text.decode('utf8')
                        all_constructs.append(callsite_model)
                        arguments_node = child.child_by_field_name('arguments')
                        if arguments_node:
                            for arg in arguments_node.children:
                                if arg.type == 'argument':
                                    arg_model = Argument(arg, file_path)
                                    if hasattr(arg_model, 'hasCanonicalName') and hasattr(arg, 'text'):
                                        arg_model.hasCanonicalName = arg.text.decode('utf8')
                                    arg_model.isArgumentIn = callsite_model
                                    callsite_model.hasArgument.append(arg_model)
                                    all_constructs.append(arg_model)
                return
            # Identifier usage
            if node.type == 'identifier' and parent_class_model:
                ident_name = node.text.decode('utf8')
                if isinstance(parent_class_model, FunctionDefinition) and ident_name in local_scope:
                    parent_class_model.add_access(local_scope[ident_name])
                return
            # Function/method call
            if node.type == 'invocation_expression' and parent_class_model:
                callsite_model = FunctionCallSite(node, file_path)
                # Function name
                function_node = node.child_by_field_name('function')
                if function_node:
                    callsite_model.hasCanonicalName = function_node.text.decode('utf8')
                all_constructs.append(callsite_model)
                # Arguments
                arguments_node = node.child_by_field_name('arguments')
                if arguments_node:
                    for arg in arguments_node.children:
                        if arg.type == 'argument':
                            arg_model = Argument(arg, file_path)
                            if hasattr(arg_model, 'hasCanonicalName') and hasattr(arg, 'text'):
                                arg_model.hasCanonicalName = arg.text.decode('utf8')
                            arg_model.isArgumentIn = callsite_model
                            callsite_model.hasArgument.append(arg_model)
                            all_constructs.append(arg_model)
                if hasattr(parent_class_model, 'callsFunction'):
                    parent_class_model.callsFunction.append(callsite_model)
                return
            # Import
            if node.type == 'using_directive':
                import_model = ImportDeclaration(node, file_path)
                name_node = node.child_by_field_name('name')
                if name_node:
                    import_model.hasCanonicalName = name_node.text.decode('utf8')
                else:
                    import_model.hasCanonicalName = import_model.hasSourceCodeSnippet
                all_constructs.append(import_model)
                return
            # Recurse
            for child in node.children:
                traverse(child, parent_class_model=parent_class_model, local_scope=local_scope)

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
