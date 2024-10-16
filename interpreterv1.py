from interpreterbase import InterpreterBase
from brewparse import parse_program, ErrorType, Element

from typing import Optional, List, Dict, Any



class Interpreter(InterpreterBase):
    def __init__(self):
        super().__init__()
        self.scope = Scope()
        
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
    def __init__(self, value:Any=None):
        self.value: Any = value
        self.elem_type: type = type(value)
        
    def assign(self, value:Any):
        self.value: Any = value
        self.elem_type: type = type(value)
        
class Function():
    '''
    Represents a function definition
    '''
    def __init__(self, functionNode: Element):
        self.functionNode = functionNode
        self.name = functionNode.get("name")
        self.statements = functionNode.get("statements")
        
        
class FunctionCall():
    '''
    Represents the stack frame for a function call
    '''
    def __init__(self, name: str, function: Function, args: List[Any], callingScope: Optional[Scope]):
        '''
        name: str - name of the function
        function: Element - the actual Function node to call
        args: List[Any] - the arguments to pass to the function
        callingScope: Optional[Scope] - the scope that called this function
        '''
        self.name = name
        self.args = args
        self.function = function
        self.callingScope = callingScope