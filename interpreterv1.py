from intbase import InterpreterBase, ErrorType
from brewparse import parse_program
from element import Element

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
        
        self.main_scope = Scope(interpreter=self)
        
    def run(self, program: str):
        ast = parse_program(program)
        program_node = ast
        # root node should be program node
        assert(program_node.elem_type == InterpreterBase.PROGRAM_NODE)
        
        # add functions under program node to scope
        self.setup_main_scope(program_node.get("functions"))
        
        # call the main function
        self.main_scope.functions["main"].execute(self.main_scope, [])
        
    def setup_main_scope(self, funcs: List[Element]):
        """
        Add built-in functions to the main scope
        """
        self.main_scope.functions["print"] = PrintFunction(self)
        self.main_scope.functions["input"] = InputFunction(self)
        
        for func in funcs:
            assert(func.elem_type == InterpreterBase.FUNC_NODE)
            self.main_scope.functions[func.get("name")] = Function(self, func)
        
class Scope():
    '''
    Represents a scope or namespace for a function call or block
    '''
    def __init__(self, interpreter: Interpreter, parent: Optional['Scope']=None):
        self.interpreter = interpreter
        if not isinstance(interpreter, Interpreter):
            raise Exception("Scope must be initialized with an Interpreter object")
        
        self.variables: Dict[str, Variable] = {}
        self.functions: Dict[str, Function] = {}
        
        self.parent = parent
        
    def add_variable(self, name):
        self.variables[name] = Variable(interpreter=self.interpreter)
        
    def assign_variables(self, name, value):
        if self.check_variable(name):
            self.variables[name].assign(value)
        elif self.parent:
            self.parent.assign_variables(name, value)
        else:
            self.interpreter.error(ErrorType.NAME_ERROR, f"Variable {name} not found")
            
    def get_variable(self, name):
        if self.check_variable(name):
            return self.variables[name].value
        elif self.parent:
            return self.parent.get_variable(name)
        else:
            self.interpreter.error(ErrorType.NAME_ERROR, f"Variable {name} not found")
        
    def check_variable(self, name, recursive=False):
        if name in self.variables:
            return True
        if recursive and self.parent:
            return self.parent.check_variable(name, recursive)
        
    def check_function(self, name, recursive=False):
        if name in self.functions:
            return True
        if recursive and self.parent:
            return self.parent.check_function(name, recursive)
    
    def get_function(self, name):
        if name in self.functions:
            return self.functions[name]
        elif self.parent:
            return self.parent.get_function(name)
        else:
            self.interpreter.error(ErrorType.NAME_ERROR, f"Function {name} not found")

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
        
    def execute(self, calling_scope: Optional[Scope], args: Optional[List[Any]]=None):
        fcall = FunctionCall(self.interpreter, self.name, self, args, calling_scope)
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
                values.append(arg.get("val"))
            else:
                # raise error if the arg is not a variable or value
                self.interpreter.error(ErrorType.TYPE_ERROR, f"Invalid argument type {arg.elem_type}")
        output_string = "".join([str(val) for val in values])
        self.interpreter.output(output_string)
        
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
        self.scope = Scope(interpreter=self.interpreter, parent=self.calling_scope)
        
    def run(self):
        # execute list of statement nodes in function node
        statements = self.function.function_node.get("statements")
        for statement in statements:
            self.evaluate_statement(statement)
    
    def evaluate_statement(self, statement: Element):
        # Check that statement is a valid statement
        assert(statement.elem_type in Interpreter.STATEMENT_NODES)
        
        match (statement.elem_type):
            case InterpreterBase.VAR_DEF_NODE:
                # add the variable to the scope
                self.scope.add_variable(statement.get("name"))
            case Interpreter.ASSIGN_NODE:
                # assign the variable
                self.scope.assign_variables(statement.get("name"), self.evaluate_expression(statement.get("expression")))
            case InterpreterBase.FCALL_NODE:
                # evaluate the function call
                self.evaluate_fcall(statement)
            case _:
                raise Exception(f"Invalid statement {statement.elem_type}")            
    
    def evaluate_fcall(self, fcall: Element):
        # get function from scope
        function = self.scope.get_function(fcall.get("name"))
        
        # execute function
        function.execute(self.scope, fcall.get("args"))
        
    
    def evaluate_expression(self, expression: Element):
        match (expression.elem_type):
            # if this is a value node just return value
            case e_t if e_t in Interpreter.VAL_NODES:
                return expression.get("val")
            # if this is var node try to retrieve from scope
            case InterpreterBase.VAR_NODE:
                return self.scope.get_variable(expression.get("name"))
            case e_t if e_t in Interpreter.BINARY_OP_NODES:
                return self.evaluate_binary_op(expression)
            case InterpreterBase.FCALL_NODE:
                return self.evaluate_fcall(expression)
            case _:
                raise Exception(f"Invalid expression {expression.elem_type}")
        
    def evaluate_binary_op(self, binary_op: Element):
        left = self.evaluate_expression(binary_op.get("op1"))
        right = self.evaluate_expression(binary_op.get("op2"))
        
        match (binary_op.elem_type):
            case Interpreter.ADD_NODE:
                # check that these are both ints
                if type(left) != int or type(right) != int:
                    self.interpreter.error(ErrorType.TYPE_ERROR, f"Invalid types for addition {type(left)} and {type(right)}")                
                return left + right
            case Interpreter.SUB_NODE:
                # check that these are both ints
                if type(left) != int or type(right) != int:
                    self.interpreter.error(ErrorType.TYPE_ERROR, f"Invalid types for subtraction {type(left)} and {type(right)}")    
                return left - right
            case _:
                # This should never happen, binary op is only called on operators belonging to BINARY_OP_NODES
                raise Exception(f"Invalid binary operator {binary_op.elem_type}")
        

# ===================================== MAIN Testing =====================================
def main():
    # all programs will be provided to your interpreter as a python string, 
    # just as shown here.
    program_source = """func main() {
        var x;
        x = 5 + 6;
        print("The sum is: ", x);
    }
    """
    
    # create an instance of your interpreter
    interpreter = Interpreter()
    
    # run the interpreter
    interpreter.run(program_source)
    
if __name__ == "__main__":
    main()