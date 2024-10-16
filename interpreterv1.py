from interpreterbase import InterpreterBase
from brewparse import parse_program, ErrorType, Element

from typing import Optional, List, Dict, Any



class Interpreter(InterpreterBase):
    
    # add value node types, int or string are valid elem_type
    INT_NODE = "int"
    STRING_NODE = "string"
    VAL_NODES = [INT_NODE, STRING_NODE]
    
    def __init__(self):
        super().__init__()
        self.main_scope = Scope()
        
        # add built-in functions to the main_scope
        self.main_scope.functions["print"] = PrintFunction()
        self.main_scope.functions["input"] = InputFunction()
        
    def run(self, program: str):
        ast = parse_program(program)
        
        
class Scope():
    '''
    Represents a scope or namespace for a function call or block
    '''
    def __init__(self, parent: Optional['Scope']=None):
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
            # create new variable in scope
            self.variables[name] = Variable(value)
            
    def get_variable(self, name):
        if self.check_variable(name):
            return self.variables[name].value
        elif self.parent:
            return self.parent.get_variable(name)
        else:
            super().raise_error(ErrorType.NAME_ERROR, f"Variable {name} not found")
        
    def check_variable(self, name, recursive=False):
        if name in self.variables:
            return True
        if recursive and self.parent:
            return self.parent.check_variable(name, recursive)

class Variable():
    '''
    Represents a variable
    '''
    def __init__(self, value: Any=None):
        self.value: Any = value
        self.elem_type: type = type(value)
        
    def assign(self, value: Any):
        self.value: Any = value
        self.elem_type: type = type(value)
        
class Function():
    '''
    Represents a function definition
    '''
    def __init__(self, function_node: Element):
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
    def __init__(self):
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
                super().raise_error(ErrorType.TYPE_ERROR, f"Invalid argument type {arg.elem_type}")
        super().output(values)
        
class InputFunction(Function):
    def __init__(self):
        self.function_node = None
        self.name = "input"
        self.statements = None
    
    def execute(self, calling_scope: Optional[Scope], args: Optional[List[Element]]):
        pass #TODO, make use of the intbase input

class FunctionCall():
    '''
    Represents the stack frame for a function call
    '''
    def __init__(self, name: str, function: Function, args: Optional[List[Element]], calling_scope: Optional[Scope]):
        '''
        name: str - name of the function
        function: Element - the actual Function node to call
        args: Optional[List[Any]] - the arguments to pass to the function
        calling_scope: Optional[Scope] - the scope that called this function
        '''
        self.name = name
        self.args = args
        self.function = function
        self.calling_scope = calling_scope
        self.scope = Scope(calling_scope)
        
    def run(self):
        pass # TODO execute statements