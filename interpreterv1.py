from interpreterbase import InterpreterBase
from brewparse import parse_program, ErrorType, Element

from typing import Optional, List, Dict, Any

class Interpreter(InterpreterBase):
    """
    The main interpreter class that will run the AST
    
    Keeps track of the global scope
    
    Defines built-in functions
    """
    
    # Add some types for operators
    ASSIGN_NODE = "="
    ADD_NODE = "+"
    SUB_NODE = "-"
    
    # add Binary operators for expressions
    BINARY_OP_NODES = [ADD_NODE, SUB_NODE]
    
    # unary operators TODO
    # UNARY_OP_NODES = [InterpreterBase.NEG_NODE, InterpreterBase.NOT_NODE]
    
    EXP_NODES = BINARY_OP_NODES + [InterpreterBase.FCALL_NODE]
    # side note: fcalls seem to be both expressions and statements, I believe the distinction is that the expressions (evaluate to / return) a value, this distinction isn't made on a syntax level, but on a semantic level
    
    # add value node types, int or string are valid elem_type
    VAL_NODES = [InterpreterBase.INT_NODE, InterpreterBase.STRING_NODE]
    
    # add statement node types (variable definition, assignment, function call)
    STATEMENT_NODES = [InterpreterBase.VAR_DEF_NODE, ASSIGN_NODE, InterpreterBase.FCALL_NODE]
    
    def __init__(self, console_output=True, inp=None, trace_output=False):
        super().__init__(console_output, inp) 
        
        self.main_scope = Scope()
        
    def run(self, program: str):
        ast = parse_program(program)
        
    def setup_main_scope(self):
        """
        Add built-in functions to the main scope
        """
        self.main_scope.functions["print"] = PrintFunction()
        self.main_scope.functions["input"] = InputFunction(super().get_input)
        
        
class Scope():
    '''
    Represents a scope or namespace for a function call or block
    '''
    def __init__(self, interpreter: Interpreter, parent: Optional['Scope']=None):
        self.interpreter = interpreter
        
        self.variables: Dict[str, Variable] = {}
        self.functions: Dict[str, Function] = {}
        
        self.parent = parent
        
    def add_variable(self, name, value):
        self.variables[name] = Variable(value)
        
    def assign_variables(self, name, value):
        if self.check_variable(name):
            self.variables[name].assign(value)
        elif self.parent:
            self.parent.assign_variables(name, value)
        else:
            self.interpreter.raise_error(ErrorType.NAME_ERROR, f"Variable {name} not found")
            
    def get_variable(self, name):
        if self.check_variable(name):
            return self.variables[name].value
        elif self.parent:
            return self.parent.get_variable(name)
        else:
            self.interpreter.raise_error(ErrorType.NAME_ERROR, f"Variable {name} not found")
        
    def check_variable(self, name, recursive=False):
        if name in self.variables:
            return True
        if recursive and self.parent:
            return self.parent.check_variable(name, recursive)

class Variable():
    '''
    Represents a variable
    '''
    def __init__(self, interpreter: Interpreter, value: Any=None):
        self.interpreter = interpreter
        
        self.value: Any = value
        self.elem_type: type = type(value)
        
    def assign(self, value: Any):
        self.value: Any = value
        self.elem_type: type = type(value)
        
class Function():
    '''
    Represents a function definition
    '''
    def __init__(self, interpreter: Interpreter, function_node: Element):
        self.interpreter = interpreter
        
        self.function_node = function_node
        
        # expect that Element is a function
        assert(function_node.elem_type == InterpreterBase.FUNC_NODE)
        
        self.name = function_node.get("name")
        self.statements = function_node.get("statements")
        
    def execute(self, calling_scope: Optional[Scope], args: Optional[List[Any]]):
        fcall = FunctionCall(self.name, self, [], calling_scope)
        fcall.run()
        
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
    
    def execute(self, calling_scope: Optional[Scope], args: Optional[List[Element]]):
        values = []
        for arg in args:
            # if arg is a variable, get the value from the scope
            if arg.elem_type == InterpreterBase.VAR_NODE:
                values.append(calling_scope.get_variable(arg.get("name")))   
            # if arg is a value just put the literal into values
            elif arg.elem_type in Interpreter.VAL_NODES:
                # check if the elem_type belongs to the value types
                values.append(arg.get("value"))
            else:
                # raise error if the arg is not a variable or value
                self.__annotations__interpreter.raise_error(ErrorType.TYPE_ERROR, f"Invalid argument type {arg.elem_type}")
        super().output(values)
        
class InputFunction(Function):
    """
    Built in Input Function
    Overwrites the execute so no need to implement this in the AST format
    """
    def __init__(self, interpreter: Interpreter):
        self.Interpreter = interpreter
        
        self.function_node = None
        self.name = "inputi"
        self.statements = None
        
        self.get_input = interpreter.get_input
    
    def execute(self, calling_scope: Optional[Scope], args: Optional[List[Element]]):
        return self.get_input()
    
class FunctionCall():
    '''
    Represents the stack frame for a function call
    '''
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
        self.scope = Scope(calling_scope)
        
    def run(self):
        pass # TODO execute statements
    
    def evaluate_statement(self, statement: Element):
        # Check that statement is a valid statement
        assert(statement.elem_type in InterpreterBase.VALID_STATEMENTS)
        
    def evaluate_expression(self, expression: Element):
        # if this is a value node just return value
        if expression.elem_type in Interpreter.VAL_NODES:
            return expression.get("value")
        
        # if this is var node try to retrieve from scope
        if expression.elem_type == InterpreterBase.VAR_NODE:
            return self.scope.get_variable(expression.get("name"))
        
        # check that expression is a valid expression
        assert(expression.elem_type in InterpreterBase.VALID_EXPRESSIONS)
        
        # if expression is a binary node
        if expression.elem_type in Interpreter.BINARY_OP_NODES:
            return self.evaluate_binary_op(expression)
        elif expression.elem_type == InterpreterBase.FCALL_NODE:
            return self.evaluate_fcall(expression)
        
        raise Exception(f"Invalid expression {expression.elem_type}")
        
    def evaluate_binary_op(self, binary_op: Element):
        left = self.evaluate_expression(binary_op.get("op1"))
        right = self.evaluate_expression(binary_op.get("op2"))
        
        match (binary_op.elem_type):
            case InterpreterBase.ADD_NODE:
                # check that these are both ints
                if type(left) != int or type(right) != int:
                    self.interpreter.raise_error(ErrorType.TYPE_ERROR, f"Invalid types for addition {type(left)} and {type(right)}")                
                return self.evaluate_expression(left) + self.evaluate_expression(right)
            case InterpreterBase.SUB_NODE:
                # check that these are both ints
                if type(left) != int or type(right) != int:
                    self.interpreter.raise_error(ErrorType.TYPE_ERROR, f"Invalid types for subtraction {type(left)} and {type(right)}")    
                return self.evaluate_expression(left) - self.evaluate_expression(right)
            case _:
                # This should never happen, binary op is only called on operators belonging to BINARY_OP_NODES
                raise Exception(f"Invalid binary operator {binary_op.elem_type}")
        
        