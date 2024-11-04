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
    
    # nil 
    NIL = None
    
    # variable number of arguments
    VAR_ARGS = -1
    
    def __init__(self, console_output=True, inp=None, trace_output=False):
        super().__init__(console_output, inp) 
        
        self.global_scope = Scope(interpreter=self)
        
    def run(self, program: str):
        ast = parse_program(program)
        program_node = ast
        # root node should be program node
        assert(program_node.elem_type == InterpreterBase.PROGRAM_NODE)
        
        # add functions under program node to scope
        self.setup_global_scope(program_node.get("functions"))
        
        # check that main is defined
        if not self.global_scope.check_function("main"):
            super().error(ErrorType.NAME_ERROR, "No main() function was found")
            
        # call the main function
        self.global_scope.functions["main"].execute(self.global_scope, [])
        
    def setup_global_scope(self, funcs: List[Element]):
        """
        Add built-in functions to the main scope
        """
        
        self.global_scope.functions[("print", Interpreter.VAR_ARGS)] = PrintFunction(self)
        
        # the inputi funciton handles 0 or 1 arguments
        self.global_scope.functions[("inputi", 0)] = InputFunction(self)
        self.global_scope.functions[("inputi", 1)] = InputFunction(self)
        
        for func in funcs:
            assert(func.elem_type == InterpreterBase.FUNC_NODE)
            self.global_scope.add_function(func)
    
class Variable():
    '''
    Represents a variable
    '''
    interpreter: Interpreter
    value: Any
    
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
    interpreter: Interpreter
    function_node: Element
    
    name: str
    args: List[Element] # list of argument nodes
    statements: List[Element] # list of statement nodes
    
    
    def __init__(self, interpreter: Interpreter, function_node: Element):
        self.interpreter = interpreter
        
        self.function_node = function_node
        
        # expect that Element is a function
        assert(function_node.elem_type == InterpreterBase.FUNC_NODE)
        
        self.name = function_node.get("name")
        self.args = function_node.get("args")
        self.statements = function_node.get("statements")
        
    def execute(self, calling_scope: Optional['Scope'], args: Optional[List[Any]]=None):
        fcall = FunctionCall(self.interpreter, self.name, self, args, calling_scope)
        fcall.run()

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
        
    def check_function(self, name, argc, recursive=False):
        if (name, argc) in self.functions:
            return True
        if (name, Interpreter.VAR_ARGS) in self.functions:
            return True
        if recursive and self.parent:
            return self.parent.check_function(name, argc, recursive)
    
    def get_function(self, name, argc=0):
        if (name, argc) in self.functions:
            return self.functions[(name, argc)]
        elif self.parent:
            return self.parent.get_function(name, argc)
        else:
            # search for a function with any number of arguments
            if (name, Interpreter.VAR_ARGS) in self.functions:
                return self.functions[(name, Interpreter.VAR_ARGS)]
            
            self.interpreter.error(ErrorType.NAME_ERROR, f"Function {name} with {argc} args has not been defined")
            
    def add_function(self, function, var_args=False):
        if var_args:
            self.functions[(function.name, Interpreter.VAR_ARGS)] = Function(self.interpreter, function)
        else:
            # functions are uniquely identified by name and number of arguments
            self.functions[(function.name, len(function.args))] = Function(self.interpreter, function)

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
        
    def declare_variable(self, name):
        # check if was already declared
        if self.check_variable(name, recursive=False):
            self.interpreter.error(ErrorType.NAME_ERROR, f"Variable {name} defined more than once")
        
        self.variables[name] = Variable(interpreter=self.interpreter)
        
    def assign_variable(self, name, value):
        if self.check_variable(name):
            self.variables[name].assign(value)
        elif self.parent:
            self.parent.assign_variable(name, value)
        else:
            self.interpreter.error(ErrorType.NAME_ERROR, f"Variable {name} has not been defined")
            
    def get_variable(self, name):
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

class Scope():
    '''
    Represents a scope of variables and functions
    '''
    interpreter: Interpreter
    variables: 'VariableScope'
    functions: 'FunctionScope'
    
    def __init__(self, interpreter: Interpreter, variables: Optional['VariableScope']=None, functions: Optional['FunctionScope']=None):
        self.interpreter = interpreter
        
        self.variables = variables or self.interpreter.global_scope.variables # If None provided, use global scope
        self.functions = functions or FunctionScope(interpreter=self.interpreter)
        
    def declare_variable(self, name):
        self.variables.declare_variable(name)
    
    def assign_variable(self, name, value):
        self.variables.assign_variable(name, value)
        
    def get_variable(self, name):
        self.variables.get_variable(name)
    
    def check_variable(self, name):
        return self.variables.check_variable(name)

    def check_function(self, name):
        return self.functions.check_function(name)
    
    def get_function(self, name, argc=0): # TODO reconsider default value for argc
        return self.functions.get_function(name, argc=argc)
    
    def assign_function(self, name, function):
        self.functions.functions[name] = function

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
        PrintFunctionCall(self.interpreter, self.name, self, args, calling_scope).run()
        
class InputFunction(Function):
    """
    Built in Input Function
    Overwrites the execute so no need to implement this in the AST format
    """
    def __init__(self, interpreter: Interpreter):
        self.interpreter = interpreter
        
        self.function_node = None
        self.name = "inputi"
        self.statements = None
    
    def execute(self, calling_scope: Optional[Scope], args: Optional[List[Element]]):
        return InputFunctionCall(self.interpreter, self.name, self, args, calling_scope).run()

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
        self.scope = Scope(interpreter=self.interpreter, variables=None, functions=calling_scope.functions) 
        
        # add arguments to scope as variables, map each argument to the corresponding argument node's name
        # with variable arguments such as print, there will be no arg nodes, so it's still possible to access the arguments by index
        for arg, arg_node in zip(args, function.args):
            self.scope.declare_variable(arg_node.get("name"))
            self.scope.assign_variable(arg_node.get("name"), arg)
        
    def run(self):
        # execute list of statement nodes in function node
        statements = self.function.function_node.get("statements")
        
        return_value = Interpreter.NIL
        
        for statement in statements:
            if statement.elem_type == InterpreterBase.RETURN_NODE:
                return_value = self.evaluate_expression(statement.get("expression"))
                break
            else:
                self.evaluate_statement(statement)
    
        return return_value
    
    def evaluate_statement(self, statement: Element):
        # Check that statement is a valid statement
        assert(statement.elem_type in Interpreter.STATEMENT_NODES)
        
        match (statement.elem_type):
            case InterpreterBase.VAR_DEF_NODE:
                # add the variable to the scope
                self.scope.declare_variable(statement.get("name"))
            case Interpreter.ASSIGN_NODE:
                # assign the variable
                self.scope.assign_variable(statement.get("name"), self.evaluate_expression(statement.get("expression")))
            case InterpreterBase.FCALL_NODE:
                # evaluate the function call
                self.evaluate_fcall(statement)
            case _:
                raise Exception(f"Invalid statement {statement.elem_type}")            
    
    def evaluate_fcall(self, fcall: Element):
        func_name = fcall.get("name")
        argc = len(fcall.get("args"))
        # get function from scope
        function = self.scope.get_function(func_name, argc)
        
        # execute function
        return function.execute(self.scope, fcall.get("args"))
    
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
                fname = expression.get("name")
                
                value = self.evaluate_fcall(expression)
                
                return value
            case _:
                raise Exception(f"Invalid expression {expression.elem_type}")
        
    def evaluate_binary_op(self, binary_op: Element):
        left = self.evaluate_expression(binary_op.get("op1"))
        right = self.evaluate_expression(binary_op.get("op2"))
        
        match (binary_op.elem_type):
            case Interpreter.ADD_NODE:
                # try casting both to ints
                left = self.cast_value(left, int)
                right = self.cast_value(right, int)
                
                return left + right
            case Interpreter.SUB_NODE:
                # try casting both to ints
                left = self.cast_value(left, int)
                right = self.cast_value(right, int)
                
                return left - right
            case _:
                # This should never happen, binary op is only called on operators belonging to BINARY_OP_NODES
                raise Exception(f"Invalid binary operator {binary_op.elem_type}")
    
    def cast_value(self, value: Any, callable_type: type):
        try:
            value = callable_type(value)
            return value
        except:
            self.interpreter.error(ErrorType.TYPE_ERROR, f"Invalid type, expected {callable_type} but got {type(value)} of value {value}")

class InputFunctionCall(FunctionCall):
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
            prompt = self.evaluate_expression(self.args[0])
            self.interpreter.output(prompt)
        
        input_value = self.interpreter.get_input()
        # try to cast to int
        try:
            input_value = int(input_value)
        except:
            self.interpreter.error(ErrorType.TYPE_ERROR, f"Invalid type, expected int but got {type(input_value)} of value {input_value}")
        return input_value    
    
class PrintFunctionCall(FunctionCall):
    '''
    Represents a function call to the built-in print function
    '''
    def __init__(self, interpreter: Interpreter, name: str, function: Function, args: Optional[List[Element]], calling_scope: Optional[Scope]):
        super().__init__(interpreter, name, function, args, calling_scope)
        
    def run(self):
        # evaluate the arguments
        values = [self.evaluate_expression(arg) for arg in self.args]
        
        for i, val in enumerate(values):
            # replace bools with strings
            if type(val) == bool:
                values[i] = "true" if val else "false"
            # replace NIL with "nil"
            if val == Interpreter.NIL:
                values[i] = "nil"
                        
        # print the values
        output_string = "".join([str(val) for val in values])
        self.interpreter.output(output_string)
        
        return Interpreter.NIL
        

# ===================================== MAIN Testing =====================================
# def main():
#     program_source = """func main() {
#         var bar;
#         bar = 5;
#         print("The answer is: ", (10 + bar) - 6, "!");
#     }
#     """
    
#     interpreter = Interpreter()
    
#     interpreter.run(program_source)
    
# if __name__ == "__main__":
#     main()