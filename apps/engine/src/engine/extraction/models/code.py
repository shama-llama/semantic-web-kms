"""
This file defines the standardized output format for all code parsers.
Every parser, regardless of the language it handles, must produce instances of these classes.
"""

from __future__ import annotations
from typing import List, Optional

# ============================================================================== 
# BASE CLASSES
# ==============================================================================

class CodeConstruct:
    """Represents a syntactically atomic unit of a programming language. This is an abstract class."""

    def __init__(self, node, file_path: str):
        # --- Internal ---
        self.node = node
        self.file_path = file_path
        self.organization_name: Optional[str] = None
        self.repository_name: Optional[str] = None
        self.relative_path: Optional[str] = None
        
        # --- Data Properties ---
        self.hasStartLine: int = node.start_point[0] + 1
        self.hasEndLine: int = node.end_point[0] + 1
        self.hasSourceCodeSnippet: str = node.text.decode('utf8', errors='ignore')
        self.hasCanonicalName: Optional[str] = None
        self.hasLineCount: int = self.hasEndLine - self.hasStartLine + 1
        
        # --- Object Properties (Relationships) ---
        self.isDeclaredBy: Optional[CodeConstruct] = None
        self.usesDeclaration: List[CodeConstruct] = []
        self.isDeclarationUsedBy: List[CodeConstruct] = []

    def set_declared_by(self, container: CodeConstruct):
        """Sets the container that declares this construct (isDeclaredBy)."""
        if not isinstance(container, CodeConstruct):
            raise TypeError("Container must be a CodeConstruct.")
        self.isDeclaredBy = container

    def add_uses_declaration(self, declaration: CodeConstruct):
        """Links this construct to a declaration it uses (usesDeclaration)."""
        if not isinstance(declaration, CodeConstruct):
            raise TypeError("Declaration must be a CodeConstruct.")
        if declaration not in self.usesDeclaration:
            self.usesDeclaration.append(declaration)
        # Also set the inverse relationship
        if self not in declaration.isDeclarationUsedBy:
            declaration.isDeclarationUsedBy.append(self)

class TypeDeclaration(CodeConstruct):
    """Represents the specification of a data type in a programming language. This is an abstract class."""
    
    def __init__(self, node, file_path: str):
        super().__init__(node, file_path)
        # --- Object Properties (Relationships) ---
        self.isTypeOf: List[CodeConstruct] = []
        self.isReturnTypeOf: List[FunctionDefinition] = []

class PrimitiveType(TypeDeclaration):
    """Represents a basic data type provided by a programming language (e.g., integer, boolean)."""
    
    def __init__(self, node, file_path: str):
        super().__init__(node, file_path)
        self.hasCanonicalName = self.hasSourceCodeSnippet

class ComplexType(TypeDeclaration):
    """Represents a composite data type, such as a class, interface, or enumeration. This is an abstract class."""
    
    def __init__(self, node, file_path: str):
        super().__init__(node, file_path)
        # --- Object Properties (Relationships) ---
        self.extendsType: List[ComplexType] = []
        self.isExtendedBy: List[ComplexType] = []
        self.hasField: List[AttributeDeclaration] = []
        self.hasMethod: List[FunctionDefinition] = []

    def add_extends_type(self, super_type: ComplexType):
        """Sets the super type this type extends (extendsType)."""
        if not isinstance(super_type, ComplexType):
            raise TypeError("Super type must be a ComplexType.")
        if super_type not in self.extendsType:
            self.extendsType.append(super_type)
        if self not in super_type.isExtendedBy:
            super_type.isExtendedBy.append(self)
    
    def add_field(self, field: AttributeDeclaration):
        """Adds a field to this type (hasField)."""
        if not isinstance(field, AttributeDeclaration):
            raise TypeError("Field must be an AttributeDeclaration.")
        if field not in self.hasField:
            self.hasField.append(field)
        # Set the inverse relationship
        field.isFieldOf = self

    def add_method(self, method: FunctionDefinition):
        """Adds a method to this type (hasMethod)."""
        if not isinstance(method, FunctionDefinition):
            raise TypeError("Method must be a FunctionDefinition.")
        if method not in self.hasMethod:
            self.hasMethod.append(method)
        # Set the inverse relationship
        method.isMethodOf = self

# ============================================================================== 
# CONCRETE TYPE DEFINITIONS
# ==============================================================================

class ClassDefinition(ComplexType):
    """The specification of a class, defining a template for objects."""
    
    def __init__(self, node, file_path: str):
        super().__init__(node, file_path)
        # --- Data Properties ---
        self.isFinal: bool = False
        
        # --- Object Properties (Relationships) ---
        self.implementsInterface: List[ComplexType] = []

    def add_implements_interface(self, interface: ComplexType):
        """Links this class to an interface it implements (implementsInterface)."""
        if not isinstance(interface, (InterfaceDefinition, TraitDefinition)):
            raise TypeError("Implemented type must be an InterfaceDefinition or TraitDefinition.")
        if interface not in self.implementsInterface:
            self.implementsInterface.append(interface)
        # Set the inverse relationship
        if not hasattr(interface, 'isImplementedBy'):
            interface.isImplementedBy = []
        if self not in interface.isImplementedBy:
            interface.isImplementedBy.append(self)

class InterfaceDefinition(ComplexType):
    """The specification of an abstract type used to define a contract of methods."""

    def __init__(self, node, file_path: str):
        super().__init__(node, file_path)
        # --- Object Properties (Relationships) ---
        self.isImplementedBy: List[ComplexType] = []

class EnumDefinition(ComplexType):
    """Defines an enumeration, a special data type consisting of a set of named constants."""
    pass # No special properties defined in the ontology

class StructDefinition(ComplexType):
    """Defines a struct, a composite data type that groups variables under a single name."""
    def __init__(self, node, file_path: str):
        super().__init__(node, file_path)
        # --- Object Properties (Relationships) ---
        self.implementsInterface: List[InterfaceDefinition] = []

    def add_implements_interface(self, interface: InterfaceDefinition):
        """Links this struct to an interface it implements (implementsInterface)."""
        if not isinstance(interface, InterfaceDefinition):
            raise TypeError("Implemented type must be an InterfaceDefinition.")
        if interface not in self.implementsInterface:
            self.implementsInterface.append(interface)
        # Set the inverse relationship
        if not hasattr(interface, 'isImplementedBy'):
            interface.isImplementedBy = []
        if self not in interface.isImplementedBy:
            interface.isImplementedBy.append(self)

class TraitDefinition(ComplexType):
    """Defines a collection of methods that can be implemented by other types for sharing functionality."""
    def __init__(self, node, file_path: str):
        super().__init__(node, file_path)
        # --- Object Properties (Relationships) ---
        self.isImplementedBy: List[ComplexType] = []

# NOTE: StructDefinition and TraitDefinition can be added here following the same pattern if needed.

# ============================================================================== 
# OTHER CODE CONSTRUCTS
# ==============================================================================

class FunctionDefinition(CodeConstruct):
    """The specification of a function, method, or constructor, including its signature and body."""
    
    def __init__(self, node, file_path: str):
        super().__init__(node, file_path)
        # --- Data Properties ---
        self.hasAccessModifier: Optional[str] = None # e.g., "public", "private"
        self.hasCyclomaticComplexity: int = 1 # Start at 1 for a single path
        self.isAsynchronous: bool = False
        self.isStatic: bool = False
        
        # --- Object Properties (Relationships) ---
        self.hasParameter: List[Parameter] = []
        self.hasReturnType: Optional[TypeDeclaration] = None
        self.isMethodOf: Optional[ComplexType] = None
        self.accesses: List[CodeConstruct] = [] # Attr or Var declarations
        self.invokes: List[FunctionDefinition] = []
        self.isInvokedBy: List[FunctionDefinition] = []
        self.callsFunction: List[FunctionCallSite] = [] # Inverse of isCalledByFunctionAt
        self.hasLocalVariable: List[VariableDeclaration] = []

    def add_parameter(self, parameter: Parameter):
        """Adds a parameter to this function's signature (hasParameter)."""
        if not isinstance(parameter, Parameter):
            raise TypeError("Parameter must be a Parameter.")
        if parameter not in self.hasParameter:
            self.hasParameter.append(parameter)
        # Set the inverse relationship
        parameter.isParameterOf = self

    def set_return_type(self, return_type: TypeDeclaration):
        """Sets the return type of this function (hasReturnType)."""
        if not isinstance(return_type, TypeDeclaration):
            raise TypeError("Return type must be a TypeDeclaration.")
        self.hasReturnType = return_type
        # Set the inverse relationship
        if self not in return_type.isReturnTypeOf:
            return_type.isReturnTypeOf.append(self)

    def add_access(self, var_or_attr: CodeConstruct):
        """Notes that this function accesses a variable, parameter, or attribute (accesses)."""
        if not isinstance(var_or_attr, (AttributeDeclaration, VariableDeclaration, Parameter)):
            raise TypeError("Accessed construct must be an Attribute, Variable, or Parameter Declaration.")
        if var_or_attr not in self.accesses:
            self.accesses.append(var_or_attr)
        # Set the inverse relationship
        if hasattr(var_or_attr, 'isAccessedBy') and self not in var_or_attr.isAccessedBy:
            var_or_attr.isAccessedBy.append(self)
            
    def add_invokes(self, other_function: FunctionDefinition):
        """Notes that this function invokes another function (invokes)."""
        if not isinstance(other_function, FunctionDefinition):
            raise TypeError("Invoked construct must be a FunctionDefinition.")
        if other_function not in self.invokes:
            self.invokes.append(other_function)
        # Set the inverse relationship
        if self not in other_function.isInvokedBy:
            other_function.isInvokedBy.append(self)

    def add_local_variable(self, var: VariableDeclaration):
        """Adds a local variable to this function (hasLocalVariable)."""
        if not isinstance(var, VariableDeclaration):
            raise TypeError("Local variable must be a VariableDeclaration.")
        if var not in self.hasLocalVariable:
            self.hasLocalVariable.append(var)
        # Set the inverse relationship if needed
        var.isLocalVariableOf = self

class AttributeDeclaration(CodeConstruct):
    """The declaration of a field, attribute, or property within a class."""
    
    def __init__(self, node, file_path: str):
        super().__init__(node, file_path)
        # --- Data Properties ---
        self.hasAccessModifier: Optional[str] = None
        self.isFinal: bool = False
        self.isStatic: bool = False
        
        # --- Object Properties (Relationships) ---
        self.hasType: Optional[TypeDeclaration] = None
        self.isFieldOf: Optional[ComplexType] = None
        self.isAccessedBy: List[FunctionDefinition] = []

    def set_type(self, type_decl: TypeDeclaration):
        """Sets the type of this attribute (hasType)."""
        if not isinstance(type_decl, TypeDeclaration):
            raise TypeError("Type must be a TypeDeclaration.")
        self.hasType = type_decl
        # Set the inverse relationship
        if self not in type_decl.isTypeOf:
            type_decl.isTypeOf.append(self)

class Parameter(CodeConstruct):
    """The specification of a variable bound within the scope of a function or method signature."""
    
    def __init__(self, node, file_path: str):
        super().__init__(node, file_path)
        # --- Object Properties (Relationships) ---
        self.hasType: Optional[TypeDeclaration] = None
        self.isParameterOf: Optional[FunctionDefinition] = None
        self.isAccessedBy: List[FunctionDefinition] = []
        
    def set_type(self, type_decl: TypeDeclaration):
        """Sets the type of this parameter (hasType)."""
        if not isinstance(type_decl, TypeDeclaration):
            raise TypeError("Type must be a TypeDeclaration.")
        self.hasType = type_decl
        # Set the inverse relationship
        if self not in type_decl.isTypeOf:
            type_decl.isTypeOf.append(self)

class VariableDeclaration(CodeConstruct):
    """The declaration of a variable within a local scope, such as a function body."""
    
    def __init__(self, node, file_path: str):
        super().__init__(node, file_path)
        # --- Object Properties (Relationships) ---
        self.hasType: Optional[TypeDeclaration] = None
        self.isAccessedBy: List[FunctionDefinition] = []
        self.isLocalVariableOf: Optional[FunctionDefinition] = None

    def set_type(self, type_decl: TypeDeclaration):
        """Sets the type of this variable (hasType)."""
        if not isinstance(type_decl, TypeDeclaration):
            raise TypeError("Type must be a TypeDeclaration.")
        self.hasType = type_decl
        # Set the inverse relationship
        if self not in type_decl.isTypeOf:
            type_decl.isTypeOf.append(self)

class FunctionCallSite(CodeConstruct):
    """Represents a single, specific invocation of a function or method."""
    
    def __init__(self, node, file_path: str):
        super().__init__(node, file_path)
        # --- Object Properties (Relationships) ---
        self.callsFunction: Optional[FunctionDefinition] = None
        self.hasArgument: List[CodeConstruct] = [] # Arguments are just other constructs

    def set_calls_function(self, function_def: FunctionDefinition):
        """Links this call site to the function it calls (callsFunction)."""
        if not isinstance(function_def, FunctionDefinition):
            raise TypeError("Called function must be a FunctionDefinition.")
        self.callsFunction = function_def
        # Set the inverse relationship
        if self not in function_def.callsFunction:
            function_def.callsFunction.append(self)
    
    def add_argument(self, argument: CodeConstruct):
        """Adds an argument to this call site (hasArgument)."""
        if not isinstance(argument, CodeConstruct):
            raise TypeError("Argument must be a CodeConstruct.")
        if argument not in self.hasArgument:
            self.hasArgument.append(argument)
        # The ontology defines isArgumentIn from CodeConstruct -> FunctionCallSite,
        # but a specific 'Argument' class is not defined, so we won't set an inverse
        # unless an 'Argument' class is added. This is a reasonable simplification.

class Argument(CodeConstruct):
    """Represents the use of a value as an argument at a specific function callsite."""
    def __init__(self, node, file_path: str):
        super().__init__(node, file_path)
        from typing import Optional
        self.isArgumentIn: Optional[FunctionCallSite] = None

class ImportDeclaration(CodeConstruct):
    """A statement making entities from another module or package available for use."""
    pass # No special properties defined in the ontology
