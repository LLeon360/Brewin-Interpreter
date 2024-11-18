from intbase import InterpreterBase, ErrorType
from brewparse import parse_program
from element import Element

from typing import Optional, List, Dict, Any, Tuple

class Interpreter(InterpreterBase):
    """
    The main interpreter class that will run the AST
    
    Keeps track of the global scope
    
    Defines built-in functions
    """
    global_scope: 'Scope'
    
    # Add some types for operators
    ASSIGN_NODE = "="
    
    # Binary Int operations
    ADD_NODE = "+"
    SUB_NODE = "-"
    MULTIPLY_NODE = "*"
    DIVIDE_NODE = "/"
    
    # Binary Comparison operations
    EQUALS_NODE = "=="
    NOT_EQUALS_NODE = "!="
    GREATER_THAN_NODE = ">"
    LESS_THAN_NODE = "<"
    GREATER_THAN_EQ_NODE = ">="
    LESS_THAN_EQ_NODE = "<="
    
    # Binary Logical operations
    AND_NODE = "&&"
    OR_NODE = "||"    
    
    # add Binary operators for expressions
    BINARY_OP_NODES = [ADD_NODE, SUB_NODE, MULTIPLY_NODE, DIVIDE_NODE, EQUALS_NODE, NOT_EQUALS_NODE, GREATER_THAN_NODE, LESS_THAN_NODE, GREATER_THAN_EQ_NODE, LESS_THAN_EQ_NODE, AND_NODE, OR_NODE]
    
    # Unary operators
    UNARY_OP_NODES = [InterpreterBase.NEG_NODE, InterpreterBase.NOT_NODE]
    
    EXP_NODES = BINARY_OP_NODES + UNARY_OP_NODES + [InterpreterBase.FCALL_NODE, InterpreterBase.NEW_NODE, InterpreterBase.VAR_NODE]
    # side note: fcalls seem to be both expressions and statements, I believe the distinction is that the expressions (evaluate to / return) a value, this distinction isn't made on a syntax level, but on a semantic level
    
    # add value node types, int or string are valid elem_type
    VAL_NODES = [InterpreterBase.INT_NODE, InterpreterBase.STRING_NODE, InterpreterBase.BOOL_NODE, InterpreterBase.NIL_NODE]
    
    # add statement node types (variable definition, assignment, function call)
    STATEMENT_NODES = [InterpreterBase.VAR_DEF_NODE, ASSIGN_NODE, InterpreterBase.FCALL_NODE, InterpreterBase.IF_NODE, InterpreterBase.FOR_NODE]
    
    # nil 
    NIL = None
    
    # variable number of arguments
    VAR_ARGS = -1
    
    def __init__(self, console_output=True, inp=None, trace_output=False):
        super().__init__(console_output, inp) 
        
        self.global_scope = Scope(interpreter=self)
        self.trace_output = trace_output
        
        # SETUP BUILT-IN TYPES
        
        # map primitive types to Python types
        self.primitive_types: Dict[str, type] = {
            "int": int,
            "string": str,
            "bool": bool,
        }
        
        # map typing to Python types OR a dict of typings for fields
        self.defined_types: Dict[str, Any] = self.primitive_types.copy()
        
    def run(self, program: str):
        ast = parse_program(program)
        program_node = ast
        # root node should be program node
        assert(program_node.elem_type == InterpreterBase.PROGRAM_NODE)
        
        # add functions under program node to scope
        self.setup_global_scope(program_node.get("functions"), program_node.get("structs"))
        
        # check that main is defined
        if not self.global_scope.check_function("main", 0):
            super().error(ErrorType.NAME_ERROR, "No main() function was found")
            
        # call the main function
        self.global_scope.functions.functions[("main", 0)].execute(self.global_scope, [])
        
    def setup_global_scope(self, funcs: List[Element], structs_defs: List[Element]):
        """
        Add built-in functions, then user defined functions and structs to the global scope
        """
            
        for struct_def in structs_defs:
            assert(struct_def.elem_type == InterpreterBase.STRUCT_NODE)
            self.add_struct(struct_def)
        
        self.global_scope.functions.functions[("print", Interpreter.VAR_ARGS)] = PrintFunction(self)
        
        # the inputi funciton handles 0 or 1 arguments
        self.global_scope.functions.functions[("inputi", 0)] = InputIFunction(self)
        self.global_scope.functions.functions[("inputi", 1)] = InputIFunction(self)
        
        # the inputs funciton handles 0 or 1 arguments
        self.global_scope.functions.functions[("inputs", 0)] = InputSFunction(self)
        self.global_scope.functions.functions[("inputs", 1)] = InputSFunction(self)
        
        for func in funcs:
            assert(func.elem_type == InterpreterBase.FUNC_NODE)
            self.global_scope.add_function(func)
        
    
    # Apply coercian from given type to the type of the variable
    def coerce(self, var_type: str, value: Any):
        '''
        Attempt to coerce the value to the desire type if applicable
        
        Current supported coercions:
        Int to Bool: non-zero to True, zero to False
        
        var_type: str - the type to coerce to
        value: Any - the value to coerce
        '''
        
        py_type = type(value)
        if py_type in self.primitive_types.values():
            # int to bool
            if py_type == int and var_type == "bool":
                return (value != 0)
            
        return value
    
    def type_check(self, var_type: str, value: Any):
        '''
        Type check the value against the given type, doesn't actually return, asserts type check
        '''
        # sanity check, this type should be defined
        if var_type not in self.defined_types:
            self.error(ErrorType.TYPE_ERROR, f"Invalid type check attempted for undefined type {var_type}")
        
        # type check the value
        
        # for primitives, see if the value is of the correct type
        if var_type in self.primitive_types:
            if type(value) != self.primitive_types[var_type]:
                self.error(ErrorType.TYPE_ERROR, f"Invalid type, expected {var_type} but got {type(value)}")
        else:
            # allow Interpreter NIL or the value must have a matching structure to the struct type definition
            
            # if the value is NIL, it's fine
            if value == Interpreter.NIL:
                return
            # check that the value is a Struct and that it's type matches
            if not isinstance(value, Struct): # this shouldn't happen
                self.error(ErrorType.TYPE_ERROR, f"Invalid type, expected struct but got {type(value)}")
            if value.struct_type != var_type:
                self.error(ErrorType.TYPE_ERROR, f"Invalid type, expected struct {var_type} but got {value.struct_type}")
    
    def add_struct(self, struct_def_node: Element):
        '''
        Add a struct definition to the typings
        
        struct_def_node: Element - the struct node
        
        Forbid redifinition of structs
        Iterate through the fields and add them to the typings, check that each field is valid
        '''
        struct_name: str = struct_def_node.get("name")
        field_def_nodes: List[Element] = struct_def_node.get("fields")
        
        if struct_name in self.defined_types:
            self.error(ErrorType.TYPE_ERROR, f"Struct {struct_name} already defined")
        
        # map each field to a type
        struct_type: Dict[str, str] = {}
        self.defined_types[struct_name] = struct_type
        
        for field_def in field_def_nodes:
            field_name = field_def.get("name")
            field_type = field_def.get("var_type")
            
            # Check that the field type is valid
            if field_type not in self.defined_types:
                self.error(ErrorType.TYPE_ERROR, f"Invalid type {field_type} in field definition")
                
            struct_type[field_name] = field_type     
    
class Variable():
    '''
    Represents a variable
    '''
    interpreter: Interpreter
    value: Any
    
    def __init__(self, interpreter: Interpreter, var_type: str):
        self.interpreter = interpreter
        
        self.value = None

        if var_type not in self.interpreter.defined_types:
            self.interpreter.error(ErrorType.TYPE_ERROR, f"Invalid type {var_type} in variable definition")

        self.var_type: str = var_type
        
        self.assign_default()
                
    def assign(self, value: Any):
        # attempt coercion, will do nothing if not applicable
        value = self.interpreter.coerce(self.var_type, value)
        
        # perform appropriate type checking of the value
        self.interpreter.type_check(self.var_type, value)
        
        # Aside, need to convert NIL to Struct of NIL for future type checking
        if value == Interpreter.NIL:
            value = Struct(self.interpreter, self.var_type)
        
        self.value = value        
        
    def assign_default(self):
        if self.var_type in self.interpreter.primitive_types:
            self.value = self.interpreter.defined_types[self.var_type]()
        else:
            self.value = Struct(self.interpreter, self.var_type) # without specifiying new_struct, this will be NIL
   
class Function():
    '''
    Represents a function definition
    '''
    interpreter: Interpreter
    function_node: Element

    name: str
    args: List[Element] # list of argument nodes
    statements: List[Element] # list of statement nodes
    return_type: str
    
    def __init__(self, interpreter: Interpreter, function_node: Element):
        self.interpreter = interpreter
        
        self.function_node = function_node
        
        # expect that Element is a function
        assert(function_node.elem_type == InterpreterBase.FUNC_NODE)
        
        self.name = function_node.get("name")
        self.args = function_node.get("args")
        self.statements = function_node.get("statements")
        self.return_type = function_node.get("return_type")
        
        # ensure that return type exists or is void
        if self.return_type != "void" and self.return_type not in self.interpreter.defined_types:
            self.interpreter.error(ErrorType.TYPE_ERROR, f"Invalid type, return type {self.return_type} is not defined")
        
    def execute(self, calling_scope: Optional['Scope'], args: Optional[List[Any]]=None):
        # args are being passed by value here
        fcall = FunctionCall(self.interpreter, self.name, self, args, calling_scope)
        return fcall.run()

class FunctionScope():
    '''
    Represents a scope for functions
    '''
    interpreter: 'Interpreter'
    functions: Dict[Tuple[str, int], Function]  # Functions are uniquely identified by name and number of arguments
    parent: Optional['FunctionScope']
    
    def __init__(self, interpreter: Interpreter, parent: Optional['FunctionScope']=None):
        self.interpreter = interpreter
        
        self.functions = {}
        
        self.parent = parent
        
    def check_function(self, name: str, argc: int, recursive=False):
        if (name, argc) in self.functions:
            return True
        if (name, Interpreter.VAR_ARGS) in self.functions:
            return True
        if recursive and self.parent:
            return self.parent.check_function(name, argc, recursive)
    
    def get_function(self, name: str, argc: int=0):
        if (name, argc) in self.functions:
            return self.functions[(name, argc)]
        elif self.parent:
            return self.parent.get_function(name, argc)
        else:
            # search for a function with any number of arguments
            if (name, Interpreter.VAR_ARGS) in self.functions:
                return self.functions[(name, Interpreter.VAR_ARGS)]
            
            self.interpreter.error(ErrorType.NAME_ERROR, f"Function {name} with {argc} args has not been defined")
            
    def add_function(self, function: Element, var_args=False):
        function_name = function.get("name")
        function_args = function.get("args")
        if var_args:
            self.functions[(function_name, Interpreter.VAR_ARGS)] = Function(self.interpreter, function)
        else:
            # functions are uniquely identified by name and number of arguments
            self.functions[(function_name, len(function_args))] = Function(self.interpreter, function)

class VariableScope():
    '''
    Represents a scope for variables
    '''
    interpreter: 'Interpreter'
    variables: Dict[str, Variable]
    parent: Optional['VariableScope']
    
    def __init__(self, interpreter: Interpreter, parent: Optional['VariableScope']=None):
        self.interpreter = interpreter
        
        self.variables = {}
        
        self.parent = parent
        
    def declare_variable(self, name: str, type: str):
        # check if was already declared in current scope, it's fine to shadow outer scopes
        if self.check_variable(name, recursive=False):
            self.interpreter.error(ErrorType.NAME_ERROR, f"Variable {name} defined more than once")
        
        self.variables[name] = Variable(interpreter=self.interpreter, var_type=type)
        
    def assign_variable(self, name, value):
        # handle struct.field... by splitting recursively
        if "." in name:
            parts = name.split(".")
            struct_name = parts[0]
            field_name = ".".join(parts[1:])
            struct = self.get_variable(struct_name)
            # NIL checks are done in the struct
            struct.assign_variable(field_name, value)
            return
        
        if self.check_variable(name):
            self.variables[name].assign(value)
        elif self.parent:
            self.parent.assign_variable(name, value)
        else:
            self.interpreter.error(ErrorType.NAME_ERROR, f"Variable {name} has not been defined")
            
    def get_variable(self, name):
        # handle struct.field... by splitting recursively
        if "." in name:
            parts = name.split(".")
            struct_name = parts[0]
            field_name = ".".join(parts[1:])
            struct = self.get_variable(struct_name)
            # NIL checks are done in the struct
            return struct.get_variable(field_name)
        
        if self.check_variable(name):
            return self.variables[name].value
        elif self.parent:
            return self.parent.get_variable(name)
        else:
            self.interpreter.error(ErrorType.NAME_ERROR, f"Variable {name} has not been defined",)
        
    def check_variable(self, name, recursive=False):
        if name in self.variables:
            return True
        if recursive and self.parent:
            return self.parent.check_variable(name, recursive)

class Struct():
    '''
    Represents the value of a struct
    '''
    Interpreter: Interpreter
    fields: Optional["VariableScope"] # may also be Interpreter.NIL
    struct_type: str
    
    def __init__(self, interpreter: "Interpreter", struct_type: str, new_struct=False):
        self.interpreter = interpreter
        
        self.struct_type = struct_type
        self.fields = Interpreter.NIL
        
        # if this is a new struct, create a new scope for the fields
        if new_struct:
            self.fields = VariableScope(interpreter=self.interpreter)
            
            # get the struct definition
            struct_def = self.interpreter.defined_types.get(struct_type, None)\
            
            # declare each field in the struct
            for field_name, field_type in struct_def.items():
                self.fields.declare_variable(field_name, field_type)
    
    def assign_variable(self, name, value):
        if self.fields:
            self.fields.assign_variable(name, value)
        else:
            self.interpreter.error(ErrorType.FAULT_ERROR, f"Invalid type, struct is NIL")
    
    def get_variable(self, name):
        if self.fields:
            return self.fields.get_variable(name)
        else:
            self.interpreter.error(ErrorType.FAULT_ERROR, f"Invalid type, struct is NIL")
    
class Scope():
    '''
    Represents a scope of variables and functions
    '''
    interpreter: Interpreter
    variables: 'VariableScope'
    functions: 'FunctionScope'
    
    def __init__(self, interpreter: Interpreter, variables: Optional['VariableScope']=None, functions: Optional['FunctionScope']=None):
        self.interpreter = interpreter
        
        self.variables = VariableScope(interpreter=self.interpreter, parent=variables)
        self.functions = FunctionScope(interpreter=self.interpreter, parent=functions)
        
    def declare_variable(self, name: str, type: str):
        self.variables.declare_variable(name, type)
    
    def assign_variable(self, name, value):
        self.variables.assign_variable(name, value)
        
    def get_variable(self, name):
        return self.variables.get_variable(name)
    
    def check_variable(self, name):
        return self.variables.check_variable(name)

    def check_function(self, name, argc):
        return self.functions.check_function(name, argc)
    
    def get_function(self, name, argc=0): # TODO reconsider default value for argc
        return self.functions.get_function(name, argc=argc)
    
    def add_function(self, function: Element):
        self.functions.add_function(function)

class PrintFunction(Function):
    '''
    Built-In Print Function
    Overwrites the execute so no need to implement this in the AST format
    '''       
    def __init__(self, interpreter: Interpreter):
        self.interpreter = interpreter
        
        self.function_node = None
        self.name = "print"
        self.statements = None
        self.args = [] # no named args
        self.return_type = "void"
    
    def execute(self, calling_scope: Optional[Scope], args: Optional[List[Element]]):
        PrintFunctionCall(self.interpreter, self.name, self, args, calling_scope).run()
        
class InputIFunction(Function):
    """
    Built in Input Function for Integers
    Overwrites the execute so no need to implement this in the AST format
    """
    interpreter: Interpreter
    def __init__(self, interpreter: Interpreter):
        self.interpreter = interpreter
        
        self.function_node = None
        self.name = "inputi"
        self.statements = None
        self.args = [] # no named args
        self.return_type = "int"
    
    def execute(self, calling_scope: Optional[Scope], args: Optional[List[Element]]):
        return InputIFunctionCall(self.interpreter, self.name, self, args, calling_scope).run()

class InputSFunction(Function):
    """
    Built in Input Function for Strings
    Overwrites the execute so no need to implement this in the AST format
    """
    interpreter: Interpreter
    def __init__(self, interpreter: Interpreter):
        self.interpreter = interpreter
        
        self.function_node = None
        self.name = "inputs"
        self.statements = None
        self.args = [] # no named args
        self.return_type = "string"
    
    def execute(self, calling_scope: Optional[Scope], args: Optional[List[Element]]):
        return InputSFunctionCall(self.interpreter, self.name, self, args, calling_scope).run()

class CodeBlock():
    '''
    Represents a block of code with its own variable scope
    
    Used for if and for statements
    
    Must propagate return statements to the outer fcall 
    '''
    interpreter: Interpreter
    fcall: 'FunctionCall'
    statements: List[Element]
    calling_scope: Scope
    def __init__(self, interpreter: Interpreter, fcall: 'FunctionCall', statements: List[Element], calling_scope: Scope):
        self.interpreter = interpreter
        
        self.fcall = fcall
        self.statements = statements
        self.calling_scope = calling_scope
        
        self.scope = Scope(interpreter=self.interpreter, variables=calling_scope.variables, functions=calling_scope.functions)

    def run(self):
        # execute list of statement nodes given
        for statement in self.statements:
            if statement.elem_type == InterpreterBase.RETURN_NODE:
                if statement.get("expression"):
                    # check if return type is void
                    if self.fcall.return_type == "void":
                        self.interpreter.error(ErrorType.TYPE_ERROR, f"Invalid return, expected void but got {self.fcall.return_type}")
                    
                    value_evaluted = self.evaluate_expression(statement.get("expression"))
                    
                    self.fcall.return_value.assign(value_evaluted)
                else:
                    self.fcall.return_value = Interpreter.NIL
                self.fcall.hit_return = True
                break
            else:
                self.evaluate_statement(statement)
                
            # if an inner function call hit a return statement, break out of the loop
            if self.fcall.hit_return:
                break
    
        return self.fcall.return_value
    
    def run_for(self, init_statement: Element, condition: Element, update_statement: Element):
        # execute the initialization statement
        self.evaluate_statement(init_statement)
        
        while self.evaluate_condition(condition):
            # each body of the loop needs it's own scope, so another CodeBlock
            loop_body = CodeBlock(self.interpreter, self.fcall, self.statements, self.scope)
            loop_body.run()
            
            if self.fcall.hit_return:
                return self.fcall.return_value
            
            # execute the update statement
            self.evaluate_statement(update_statement)        
        
    def evaluate_condition(self, condition: Element):
        value = self.evaluate_expression(condition)
        
        # attempt coercion to bool
        value = self.interpreter.coerce("bool", value)
        
        # type check as bool
        self.interpreter.type_check("bool", value)
        return value
    
    def evaluate_statement(self, statement: Element):
        # Check that statement is a valid statement
        assert(statement.elem_type in Interpreter.STATEMENT_NODES)
        
        match (statement.elem_type):
            case InterpreterBase.VAR_DEF_NODE:
                # add the variable to the scope
                self.scope.declare_variable(statement.get("name"), statement.get("var_type"))
            case Interpreter.ASSIGN_NODE:
                # assign the variable
                self.scope.assign_variable(statement.get("name"), self.evaluate_expression(statement.get("expression")))
            case InterpreterBase.FCALL_NODE:
                # evaluate the function call
                self.evaluate_fcall(statement)
            case InterpreterBase.IF_NODE:
                # evaluate the condition
                condition = self.evaluate_condition(statement.get("condition"))
                    
                # if the condition is true, execute the code block, if not execute the else block (if exists)
                if condition:
                    code_block = CodeBlock(self.interpreter, self.fcall, statement.get("statements"), self.scope)
                    code_block.run()
                elif statement.get("else_statements"):                    
                    code_block = CodeBlock(self.interpreter, self.fcall, statement.get("else_statements"), self.scope)
                    code_block.run()
            case InterpreterBase.FOR_NODE:
                init_statement = statement.get("init")
                condition = statement.get("condition")
                update_statement = statement.get("update")
                
                for_block = CodeBlock(self.interpreter, self.fcall, statement.get("statements"), self.scope)
                for_block.run_for(init_statement, condition, update_statement)
                
            case _:
                raise Exception(f"Invalid statement {statement.elem_type}")            
    
    def evaluate_fcall(self, fcall: Element):
        func_name = fcall.get("name")
        argc = len(fcall.get("args"))
        # get function from scope
        function = self.scope.get_function(func_name, argc)
        
        # evaluate all arguments into values
        arg_values = [self.evaluate_expression(arg) for arg in fcall.get("args")]
        
        # execute function
        return function.execute(self.scope, arg_values)
    
    def evaluate_expression(self, expression: Element):   
        match (expression.elem_type):
            # if this is a value node just return value
            case e_t if e_t in Interpreter.VAL_NODES:
                
                # if self.interpreter.trace_output:
                #     print(f"Value node: {expression.get('val')} of type {expression.elem_type}")
                    
                return expression.get("val")
            # if this is var node try to retrieve from scope
            case InterpreterBase.VAR_NODE:
                return self.scope.get_variable(expression.get("name"))
            case e_t if e_t in Interpreter.BINARY_OP_NODES:
                return self.evaluate_binary_op(expression)
            case e_t if e_t in Interpreter.UNARY_OP_NODES:
                return self.evaluate_unary_op(expression)
            case InterpreterBase.FCALL_NODE:                
                fname = expression.get("name")
                
                # check that the function does not return void
                if self.scope.get_function(fname, len(expression.get("args"))).return_type == "void":
                    self.interpreter.error(ErrorType.TYPE_ERROR, f"Invalid type, expected non-void return but got void")
                
                value = self.evaluate_fcall(expression)
                return value
            case InterpreterBase.NEW_NODE:
                struct_type = expression.get("struct_type")
                # check that the struct type is defined
                if struct_type not in self.interpreter.defined_types:
                    self.interpreter.error(ErrorType.TYPE_ERROR, f"Invalid type, attempted to new, struct {struct_type} is not defined")
                return Struct(self.interpreter, struct_type, new_struct=True)
            case _:
                raise Exception(f"Invalid expression {expression.elem_type}")
        
    def evaluate_binary_op(self, binary_op: Element):
        # strict evaluation, no short-circuiting, left and right are always evaluated
        left = self.evaluate_expression(binary_op.get("op1"))
        right = self.evaluate_expression(binary_op.get("op2"))
        
        match (binary_op.elem_type):
            # Integer operations
            case Interpreter.ADD_NODE:
                
                # if both are ints
                if type(left) == int and type(right) == int:
                    return left + right
                # if both are strings
                elif type(left) == str and type(right) == str:
                    return left + right
                
                # throw type error
                self.interpreter.error(ErrorType.TYPE_ERROR, f"Invalid type, expected int or string but got {type(left)} and {type(right)}")
                
            case Interpreter.SUB_NODE:
                # assert both ints
                self.interpreter.type_check("int", left)
                self.interpreter.type_check("int", right)
                
                return left - right
            case Interpreter.MULTIPLY_NODE:
                # assert both ints
                self.interpreter.type_check("int", left)
                self.interpreter.type_check("int", right)
                
                return left * right
            case Interpreter.DIVIDE_NODE:
                # assert both ints
                self.interpreter.type_check("int", left)
                self.interpreter.type_check("int", right)
                
                # Catch divide by zero
                if right == 0:
                    # Note, this isn't defined in the spec, so will throw as a type error, but TODO this doesn't fit exactly
                    self.interpreter.error(ErrorType.TYPE_ERROR, "Division by zero encountered: {left} / {right}")
                
                # DO INTEGER DIVISION
                return left // right
            
            # comparisons
            case Interpreter.EQUALS_NODE:
                # if one is bool attempt coercion of other to bool
                if type(left) == bool:
                    right = self.interpreter.coerce("bool", right)
                elif type(right) == bool:
                    left = self.interpreter.coerce("bool", left)
                
                # if either is a struct
                if type(left) == Struct or type(right) == Struct:
                    # allow comparison of any struct to a NIL
                    if (type(left) == Struct and right == Interpreter.NIL) or (type(right) == Struct and left == Interpreter.NIL):
                        if type(left) == Struct:
                            left = left.fields # will be NIL if NIL
                        if type(right) == Struct:
                            right = right.fields # will be NIL if NIL
                    
                    # otherwise both must be same struct type
                    elif left.struct_type != right.struct_type:
                        self.interpreter.error(ErrorType.TYPE_ERROR, f"Invalid type, tried to compare struct {left.struct_type} to struct {right.struct_type}")
                elif type(left) != type(right):
                    # for primitive types, they must be the same after coercion
                    self.interpreter.error(ErrorType.TYPE_ERROR, f"Invalid type, tried to compare {type(left)} to {type(right)}")

                return left == right
            
            case Interpreter.NOT_EQUALS_NODE:
                # if one is bool attempt coercion of other to bool
                if type(left) == bool:
                    right = self.interpreter.coerce("bool", right)
                elif type(right) == bool:
                    left = self.interpreter.coerce("bool", left)
                
                # if either is a struct
                if type(left) == Struct or type(right) == Struct:
                    # allow comparison of any struct to a NIL
                    if (type(left) == Struct and right == Interpreter.NIL) or (type(right) == Struct and left == Interpreter.NIL):
                        if type(left) == Struct:
                            left = left.fields # will be NIL if NIL
                        if type(right) == Struct:
                            right = right.fields # will be NIL if NIL
                    
                    # otherwise both must be same struct type
                    elif left.struct_type != right.struct_type:
                        self.interpreter.error(ErrorType.TYPE_ERROR, f"Invalid type, tried to compare struct {left.struct_type} to struct {right.struct_type}")
                elif type(left) != type(right):
                    # for primitive types, they must be the same after coercion
                    self.interpreter.error(ErrorType.TYPE_ERROR, f"Invalid type, tried to compare {type(left)} to {type(right)}")
                
                return left != right
            
            case Interpreter.GREATER_THAN_NODE:
                # assert both ints
                self.interpreter.type_check("int", left)
                self.interpreter.type_check("int", right)
                
                return left > right
            
            case Interpreter.LESS_THAN_NODE:
                # assert both ints
                self.interpreter.type_check("int", left)
                self.interpreter.type_check("int", right)
                
                return left < right
            
            case Interpreter.GREATER_THAN_EQ_NODE:
                # assert both ints
                self.interpreter.type_check("int", left)
                self.interpreter.type_check("int", right)
                
                return left >= right
            
            case Interpreter.LESS_THAN_EQ_NODE:
                # assert both ints
                self.interpreter.type_check("int", left)
                self.interpreter.type_check("int", right)
                
                return left <= right
            
            # logical operators
            case Interpreter.AND_NODE:
                # attempt coercion to bool
                left = self.interpreter.coerce("bool", left)
                right = self.interpreter.coerce("bool", right)
                
                # check if both are booleans
                self.interpreter.type_check("bool", left)
                self.interpreter.type_check("bool", right)
                
                return left and right
            
            case Interpreter.OR_NODE:
                # attempt coercion to bool
                left = self.interpreter.coerce("bool", left)
                right = self.interpreter.coerce("bool", right)
                
                # check if both are booleans
                self.interpreter.type_check("bool", left)
                self.interpreter.type_check("bool", right)
                
                return left or right
            
            case _:
                # This should never happen, binary op is only called on operators belonging to BINARY_OP_NODES
                raise Exception(f"Invalid binary operator {binary_op.elem_type}")
    
    def evaluate_unary_op(self, unary_op: Element):
        value = self.evaluate_expression(unary_op.get("op1"))
        match (unary_op.elem_type):
            case InterpreterBase.NEG_NODE:
                # check if is an int
                self.interpreter.type_check("int", value)
                return -value
            case InterpreterBase.NOT_NODE:
                # Barista appears to support coercion on not, although the spec is not clear about this
                # attempt coercion to bool
                value = self.interpreter.coerce("bool", value)
                # check if is a bool
                self.interpreter.type_check("bool", value)
                return not value
            case _:
                # This should never happen, unary op is only called on operators belonging to UNARY_OP_NODES
                raise Exception(f"Invalid unary operator {unary_op.elem_type}")
    
    # def assert_int(self, value: Any):
    #     if type(value) != int:
    #         self.interpreter.error(ErrorType.TYPE_ERROR, f"Invalid type, expected int but got {type(value)}")
    
    # def assert_bool(self, value: Any):
    #     if type(value) != bool:
    #         self.interpreter.error(ErrorType.TYPE_ERROR, f"Invalid type, expected bool but got {type(value)}")
    
    # def cast_value(self, value: Any, callable_type: type):
    #     try:
    #         value = callable_type(value)
    #         return value
    #     except:
    #         self.interpreter.error(ErrorType.TYPE_ERROR, f"Invalid type, expected {callable_type} but got {type(value)} of value {value}")

class FunctionCall():
    '''
    Represents the stack frame for a function call
    '''
    interpreter: Interpreter
    name: str
    args: Optional[List[Element]]
    function: Function
    calling_scope: Optional[Scope]
    scope: Scope
    hit_return: bool
    return_type: str
    return_value: Optional[Variable] # will be None for void functions, and initially
    
    def __init__(self, interpreter: Interpreter, name: str, function: Function, args: Optional[List[Element]], calling_scope: Optional[Scope]):
        '''
        interpreter: Interpreter - the interpreter object
        name: str - name of the function
        function: Element - the actual Function node to call
        args: Optional[List[Any]] - the arguments to pass to the function
        calling_scope: Optional[Scope] - the scope that called this function
        '''
        self.interpreter = interpreter
        
        self.name = name
        self.args = args        
        self.function = function
        self.calling_scope = calling_scope
        self.scope = Scope(interpreter=self.interpreter, variables=self.interpreter.global_scope, functions=calling_scope.functions) 

        # keep track of if a return statement was hit, especially in nested code blocks
        self.hit_return = False
        self.return_type = self.function.return_type
        
        # use this to track the return variable, use existing variable system to track the return value and type check
        self.return_value = None
        
        # add arguments to scope as variables, map each argument to the corresponding argument node's name
        # with variable arguments such as print, there will be no arg nodes, so it's still possible to access the arguments by index
        for arg_value, arg_node in zip(args, function.args):            
            arg_name = arg_node.get("name")
            arg_type = arg_node.get("var_type")
            self.scope.declare_variable(arg_name, arg_type)
            self.scope.assign_variable(arg_name, arg_value)
        
    def run(self):
        # set up return value if not void
        if self.return_type != "void":
            self.return_value = Variable(self.interpreter, self.return_type)
        
        # execute list of statement nodes in function node
        
        # create a CodeBlock for the main statement body
        code_block = CodeBlock(self.interpreter, self, self.function.statements, self.scope)
        code_block.run()
        
        # return no value for void functions
        if self.return_type == "void":
            return
        
        return self.return_value.value
        
class InputIFunctionCall(FunctionCall):
    '''
    Represents a function call to the built-in input function
    '''
    def __init__(self, interpreter: Interpreter, name: str, function: Function, args: Optional[List[Element]], calling_scope: Optional[Scope]):
        super().__init__(interpreter, name, function, args, calling_scope)
        
    def run(self):
        # accept up to one argument
        if len(self.args) > 1:
            self.interpreter.error(ErrorType.NAME_ERROR, f"No inputi() function found that takes > 1 parameter")
        
        # if there is an argument, print it
        if self.args:
            prompt = self.args[0]
            self.interpreter.output(prompt)
        
        input_value = self.interpreter.get_input()
        # try to cast to int
        try:
            input_value = int(input_value)
        except:
            self.interpreter.error(ErrorType.TYPE_ERROR, f"Invalid type, expected int but got {type(input_value)} of value {input_value} in inputi")
        return input_value   

class InputSFunctionCall(FunctionCall):
    '''
    Represents a function call to the built-in input function
    '''
    def __init__(self, interpreter: Interpreter, name: str, function: Function, args: Optional[List[Element]], calling_scope: Optional[Scope]):
        super().__init__(interpreter, name, function, args, calling_scope)
        
    def run(self):
        # accept up to one argument
        if len(self.args) > 1:
            self.interpreter.error(ErrorType.NAME_ERROR, f"No inputs() function found that takes > 1 parameter")
        
        # if there is an argument, print it
        if self.args:
            prompt = self.args[0]
            self.interpreter.output(prompt)
        
        input_value = self.interpreter.get_input()
        
        # Check that it's a string
        self.interpreter.type_check("string", input_value)
        
        return input_value 
    
class PrintFunctionCall(FunctionCall):
    '''
    Represents a function call to the built-in print function
    '''
    def __init__(self, interpreter: Interpreter, name: str, function: Function, args: Optional[List[Element]], calling_scope: Optional[Scope]):
        super().__init__(interpreter, name, function, args, calling_scope)
        
    def run(self):
        values = self.args
        
        for i, val in enumerate(values):
            # replace bools with strings
            if type(val) == bool:
                values[i] = "true" if val else "false"
            # replace NIL with "nil"
            if val == Interpreter.NIL:
                values[i] = "nil"
            if type(val) == Struct:
                # handle the Struct wrapping NIL case
                if val.fields == Interpreter.NIL:
                    values[i] = "nil"
                else:
                    values[i] = val.fields
                        
        # print the values
        output_string = "".join([str(val) for val in values])
        self.interpreter.output(output_string)
        
        return 
        

# ===================================== MAIN Testing =====================================
def main():
    program_source = """
func main() : void {
  var b: bool;
  b = foo() == nil;
}

func foo() : void {
  var a: int;
}


    """
    
    interpreter = Interpreter()
    
    interpreter.run(program_source)
    
if __name__ == "__main__":
    main()