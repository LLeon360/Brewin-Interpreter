from intbase import InterpreterBase, ErrorType
from brewparse import parse_program
from element import Element

from typing import Optional, List, Dict, Any, Tuple

import copy

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
    
    EXP_NODES = BINARY_OP_NODES + [InterpreterBase.FCALL_NODE]
    # side note: fcalls seem to be both expressions and statements, I believe the distinction is that the expressions (evaluate to / return) a value, this distinction isn't made on a syntax level, but on a semantic level
    
    # add value node types, int or string are valid elem_type
    VAL_NODES = [InterpreterBase.INT_NODE, InterpreterBase.STRING_NODE, InterpreterBase.BOOL_NODE, InterpreterBase.NIL_NODE]
    
    # add statement node types (variable definition, assignment, function call)
    STATEMENT_NODES = [InterpreterBase.VAR_DEF_NODE, ASSIGN_NODE, InterpreterBase.FCALL_NODE, InterpreterBase.IF_NODE, InterpreterBase.FOR_NODE, InterpreterBase.RETURN_NODE]
    
    # nil 
    NIL = None
    
    # variable number of arguments
    VAR_ARGS = -1
    
    global_interpreter: Optional['Interpreter'] = None
    
    def __init__(self, console_output=True, inp=None, trace_output=False):
        super().__init__(console_output, inp) 
        Interpreter.global_interpreter = self
        
        self.global_scope = Scope()
        self.trace_output = trace_output
        
    def run(self, program: str):
        ast = parse_program(program)
        program_node = ast
        # root node should be program node
        assert(program_node.elem_type == InterpreterBase.PROGRAM_NODE)
        
        # add functions under program node to scope
        self.setup_global_scope(program_node.get("functions"))
        
        # check that main is defined
        if not self.global_scope.check_function("main", 0):
            super().error(ErrorType.NAME_ERROR, "No main() function was found")
            
        # call the main function
        self.global_scope.functions.functions[("main", 0)].execute(self.global_scope, [])
        
    def setup_global_scope(self, funcs: List[Element]):
        """
        Add built-in functions to the main scope
        """
        
        self.global_scope.functions.functions[("print", Interpreter.VAR_ARGS)] = PrintFunction()
        
        # the inputi funciton handles 0 or 1 arguments
        self.global_scope.functions.functions[("inputi", 0)] = InputIFunction()
        self.global_scope.functions.functions[("inputi", 1)] = InputIFunction()
        
        # the inputs funciton handles 0 or 1 arguments
        self.global_scope.functions.functions[("inputs", 0)] = InputSFunction()
        self.global_scope.functions.functions[("inputs", 1)] = InputSFunction()
        
        for func in funcs:
            assert(func.elem_type == InterpreterBase.FUNC_NODE)
            self.global_scope.add_function(func)
    
class Variable():
    '''
    Represents a variable
    '''
    value: Any
    
    def __init__(self, value: Any=None):
        # TODO Remove
        
        self.value: Any = value
        self.elem_type: type = type(value)
        
    def assign(self, value: Any):
        self.value: Any = value
        self.elem_type: type = type(value)

class LazyExpression():
    '''
    Represents an expression that is lazily evaluated
    It stores a snapshot of the current state of the current scope and the expression to evaluate.
    
    Note: since this stores a copy of the variables, any if the expression somehow should modifies variables in the broader scope this wouldn't work, but since there aren't object references/structs or pointers to anything outside of the scope in v4, all of the changes are local to the scope 
    '''
    
    def __init__(self, scope: 'Scope', expression: Element):      
        # TODO Remove 
        # snapshot of the current scope's variables so that modifications to the original scope do not affect the lazy expression
        variable_snapshot = copy.deepcopy(scope.variables)
        self.scope = Scope(variables=variable_snapshot, functions=scope.functions)
        self.expression = expression
        
        
    def evaluate(self):
        # create a CodeBlock for the expression
        code_block = CodeBlock(None, None, self.scope)
        return code_block.evaluate_expression(self.expression)
    
class Function():
    '''
    Represents a function definition
    '''
    function_node: Element
    
    name: str
    args: List[Element] # list of argument nodes
    statements: List[Element] # list of statement nodes
    
    
    def __init__(self, function_node: Element):
        
        self.function_node = function_node
        
        # expect that Element is a function
        assert(function_node.elem_type == InterpreterBase.FUNC_NODE)
        
        self.name = function_node.get("name")
        self.args = function_node.get("args")
        self.statements = function_node.get("statements")
        
    def execute(self, calling_scope: Optional['Scope'], args: Optional[List[Any]]=None):
        # args are being passed by value here
        fcall = FunctionCall(self.name, self, args, calling_scope)
        return fcall.run()

class FunctionScope():
    '''
    Represents a scope for functions
    '''
    interpreter: 'Interpreter'
    functions: Dict[Tuple[str, int], Function]  # Functions are uniquely identified by name and number of arguments
    parent: Optional['FunctionScope']
    
    def __init__(self, parent: Optional['FunctionScope']=None):
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
            
            Interpreter.global_interpreter.error(ErrorType.NAME_ERROR, f"Function {name} with {argc} args has not been defined")
            
    def add_function(self, function: Element, var_args=False):
        function_name = function.get("name")
        function_args = function.get("args")
        if var_args:
            self.functions[(function_name, Interpreter.VAR_ARGS)] = Function(function)
        else:
            # functions are uniquely identified by name and number of arguments
            self.functions[(function_name, len(function_args))] = Function(function)

class VariableScope():
    '''
    Represents a scope for variables
    '''
    interpreter: 'Interpreter'
    variables: Dict[str, Variable]
    parent: Optional['VariableScope']
    
    def __init__(self, parent: Optional['VariableScope']=None):
        
        self.variables = {}
        
        self.parent = parent
        
    def declare_variable(self, name):
        # check if was already declared in current scope, it's fine to shadow outer scopes
        if self.check_variable(name, recursive=False):
            Interpreter.global_interpreter.error(ErrorType.NAME_ERROR, f"Variable {name} defined more than once")
        
        self.variables[name] = Variable()
        
    def assign_variable(self, name, value):
        if self.check_variable(name):
            self.variables[name].assign(value)
        elif self.parent:
            self.parent.assign_variable(name, value)
        else:
            Interpreter.global_interpreter.error(ErrorType.NAME_ERROR, f"Variable {name} has not been defined")
            
    def get_variable(self, name):
        if self.check_variable(name):
            return self.variables[name].value
        elif self.parent:
            return self.parent.get_variable(name)
        else:
            Interpreter.global_interpreter.error(ErrorType.NAME_ERROR, f"Variable {name} has not been defined",)
        
    def check_variable(self, name, recursive=False):
        if name in self.variables:
            return True
        if recursive and self.parent:
            return self.parent.check_variable(name, recursive)

class Scope():
    '''
    Represents a scope of variables and functions
    '''
    variables: 'VariableScope'
    functions: 'FunctionScope'
    
    def __init__(self, variables: Optional['VariableScope']=None, functions: Optional['FunctionScope']=None):
        self.variables = VariableScope(parent=variables)
        self.functions = FunctionScope(parent=functions)
        
    def declare_variable(self, name):
        self.variables.declare_variable(name)
    
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
    def __init__(self):
        
        self.function_node = None
        self.name = "print"
        self.statements = None
        self.args = [] # no named args
    
    def execute(self, calling_scope: Optional[Scope], args: Optional[List[Element]]):
        PrintFunctionCall(self.name, self, args, calling_scope).run()
        
class InputIFunction(Function):
    """
    Built in Input Function for Integers
    Overwrites the execute so no need to implement this in the AST format
    """
    def __init__(self):
    
        self.function_node = None
        self.name = "inputi"
        self.statements = None
        self.args = [] # no named args
    
    def execute(self, calling_scope: Optional[Scope], args: Optional[List[Element]]):
        return InputIFunctionCall(self.name, self, args, calling_scope).run()

class InputSFunction(Function):
    """
    Built in Input Function for Strings
    Overwrites the execute so no need to implement this in the AST format
    """
    def __init__(self):
        
        self.function_node = None
        self.name = "inputs"
        self.statements = None
        self.args = [] # no named args
    
    def execute(self, calling_scope: Optional[Scope], args: Optional[List[Element]]):
        return InputSFunctionCall(self.name, self, args, calling_scope).run()

class CodeBlock():
    '''
    Represents a block of code with its own variable scope
    
    Used for if and for statements
    
    Must propagate return statements to the outer fcall 
    '''
    fcall: 'FunctionCall'
    statements: List[Element]
    calling_scope: Scope
    def __init__(self, fcall: Optional['FunctionCall'], statements: Optional[List[Element]], calling_scope: Scope):
        
        self.fcall = fcall
        self.statements = statements
        self.calling_scope = calling_scope
        
        self.scope = Scope(variables=calling_scope.variables, functions=calling_scope.functions)

    def run(self):
        # execute list of statement nodes given
        for statement in self.statements:
            if statement.elem_type == InterpreterBase.RETURN_NODE:
                if statement.get("expression"):
                    self.fcall.return_value = self.evaluate_expression(statement.get("expression"))
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
            loop_body = CodeBlock(self.fcall, self.statements, self.scope)
            loop_body.run()
            
            if self.fcall.hit_return:
                return self.fcall.return_value
            
            # execute the update statement
            self.evaluate_statement(update_statement)        
        
    def evaluate_condition(self, condition: Element):
        value = self.evaluate_expression(condition)
        self.assert_bool(value)
        return value
    
    def evaluate_statement(self, statement: Element):
        # Check that statement is a valid statement
        assert(statement.elem_type in Interpreter.STATEMENT_NODES)
        
        match (statement.elem_type):
            case InterpreterBase.VAR_DEF_NODE:
                # add the variable to the scope
                self.scope.declare_variable(statement.get("name"))
            case Interpreter.ASSIGN_NODE:
                # lazy evaluation, store the current scope and the expression to evaluate in a lazy expression object
                lazy_expression = LazyExpression(self.scope, statement.get("expression"))
                # assign the variable
                self.scope.assign_variable(statement.get("name"), lazy_expression)
            case InterpreterBase.FCALL_NODE:
                # evaluate the function call
                self.evaluate_fcall(statement)
            case InterpreterBase.IF_NODE:
                # evaluate the condition
                condition = self.evaluate_condition(statement.get("condition"))
                    
                # if the condition is true, execute the code block, if not execute the else block (if exists)
                if condition:
                    code_block = CodeBlock(self.fcall, statement.get("statements"), self.scope)
                    code_block.run()
                elif statement.get("else_statements"):                    
                    code_block = CodeBlock(self.fcall, statement.get("else_statements"), self.scope)
                    code_block.run()
            case InterpreterBase.FOR_NODE:
                init_statement = statement.get("init")
                condition = statement.get("condition")
                update_statement = statement.get("update")
                
                for_block = CodeBlock(self.fcall, statement.get("statements"), self.scope)
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
                
                # if Interpreter.global_interpreter.trace_output:
                #     print(f"Value node: {expression.get('val')} of type {expression.elem_type}")
                    
                return expression.get("val")
            # if this is var node try to retrieve from scope
            case InterpreterBase.VAR_NODE:
                var_val = self.scope.get_variable(expression.get("name"))
                
                # If the variable is a lazy expression, evaluate it now, and cache the actual value 
                if isinstance(var_val, LazyExpression):
                    # var_val = self.evaluate_expression(var_val.expression)
                    var_val = var_val.evaluate()
                    self.scope.assign_variable(expression.get("name"), var_val)
                
                return var_val
                
            case e_t if e_t in Interpreter.BINARY_OP_NODES:
                return self.evaluate_binary_op(expression)
            case e_t if e_t in Interpreter.UNARY_OP_NODES:
                return self.evaluate_unary_op(expression)
            case InterpreterBase.FCALL_NODE:
                fname = expression.get("name")
                value = self.evaluate_fcall(expression)
                return value
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
                Interpreter.global_interpreter.error(ErrorType.TYPE_ERROR, f"Invalid type, expected int or string but got {type(left)} and {type(right)}")
                
            case Interpreter.SUB_NODE:
                # check that both are ints
                self.assert_int(left)
                self.assert_int(right)
                
                return left - right
            case Interpreter.MULTIPLY_NODE:
                # check that both are ints
                self.assert_int(left)
                self.assert_int(right)
                
                return left * right
            case Interpreter.DIVIDE_NODE:
                # check that both are ints
                self.assert_int(left)
                self.assert_int(right)
                
                # Catch divide by zero
                if right == 0:
                    # Note, this isn't defined in the spec, so will throw as a type error, but TODO this doesn't fit exactly
                    Interpreter.global_interpreter.error(ErrorType.TYPE_ERROR, "Division by zero encountered: {left} / {right}")
                
                # DO INTEGER DIVISION
                return left // right
            
            # comparisons
            case Interpreter.EQUALS_NODE:
                # allows different types
                if type(left) != type(right):
                    return False
                
                return left == right
            case Interpreter.NOT_EQUALS_NODE:
                # allows different types
                if type(left) != type(right):
                    return True
                
                return left != right
            
            case Interpreter.GREATER_THAN_NODE:
                # assert both ints
                self.assert_int(left)
                self.assert_int(right)
                
                return left > right
            
            case Interpreter.LESS_THAN_NODE:
                # assert both ints
                self.assert_int(left)
                self.assert_int(right)
                
                return left < right
            
            case Interpreter.GREATER_THAN_EQ_NODE:
                # assert both ints
                self.assert_int(left)
                self.assert_int(right)
                
                return left >= right
            
            case Interpreter.LESS_THAN_EQ_NODE:
                # assert both ints
                self.assert_int(left)
                self.assert_int(right)
                
                return left <= right
            
            # logical operators
            case Interpreter.AND_NODE:
                # check if both are booleans
                self.assert_bool(left)
                self.assert_bool(right)
                
                return left and right
            
            case Interpreter.OR_NODE:
                # check if both are booleans
                self.assert_bool(left)
                self.assert_bool(right)
                
                return left or right
            
            case _:
                # This should never happen, binary op is only called on operators belonging to BINARY_OP_NODES
                raise Exception(f"Invalid binary operator {binary_op.elem_type}")
    
    def evaluate_unary_op(self, unary_op: Element):
        value = self.evaluate_expression(unary_op.get("op1"))
        match (unary_op.elem_type):
            case InterpreterBase.NEG_NODE:
                # check if is an int
                self.assert_int(value)
                return -value
            case InterpreterBase.NOT_NODE:
                # check if is a bool
                self.assert_bool(value)
                return not value
            case _:
                # This should never happen, unary op is only called on operators belonging to UNARY_OP_NODES
                raise Exception(f"Invalid unary operator {unary_op.elem_type}")
    
    def assert_int(self, value: Any):
        if type(value) != int:
            Interpreter.global_interpreter.error(ErrorType.TYPE_ERROR, f"Invalid type, expected int but got {type(value)}")
    
    def assert_bool(self, value: Any):
        if type(value) != bool:
            Interpreter.global_interpreter.error(ErrorType.TYPE_ERROR, f"Invalid type, expected bool but got {type(value)}")
    
    # def cast_value(self, value: Any, callable_type: type):
    #     try:
    #         value = callable_type(value)
    #         return value
    #     except:
    #         Interpreter.global_interpreter.error(ErrorType.TYPE_ERROR, f"Invalid type, expected {callable_type} but got {type(value)} of value {value}")

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
        # TODO Remove
        
        self.name = name
        self.args = args        
        self.function = function
        self.calling_scope = calling_scope
        self.scope = Scope(variables=Interpreter.global_interpreter.global_scope, functions=calling_scope.functions) 

        # keep track of if a return statement was hit, especially in nested code blocks
        self.hit_return = False
        # track return value, default to NIL
        self.return_value = Interpreter.NIL
        
        # add arguments to scope as variables, map each argument to the corresponding argument node's name
        # with variable arguments such as print, there will be no arg nodes, so it's still possible to access the arguments by index
        for arg_value, arg_node in zip(args, function.args):
            arg_name = arg_node.get("name")
            self.scope.declare_variable(arg_name)
            self.scope.assign_variable(arg_name, arg_value)
        
    def run(self):
        # execute list of statement nodes in function node
        
        # create a CodeBlock for the main statement body
        code_block = CodeBlock(self, self.function.statements, self.scope)
        code_block.run()
        
        return self.return_value
        
class InputIFunctionCall(FunctionCall):
    '''
    Represents a function call to the built-in input function
    '''
    def __init__(self, name: str, function: Function, args: Optional[List[Element]], calling_scope: Optional[Scope]):
        super().__init__(name, function, args, calling_scope)
        
    def run(self):
        # accept up to one argument
        if len(self.args) > 1:
            Interpreter.global_interpreter.error(ErrorType.NAME_ERROR, f"No inputi() function found that takes > 1 parameter")
        
        # if there is an argument, print it
        if self.args:
            prompt = self.args[0]
            Interpreter.global_interpreter.output(prompt)
        
        input_value = Interpreter.global_interpreter.get_input()
        # try to cast to int
        try:
            input_value = int(input_value)
        except:
            Interpreter.global_interpreter.error(ErrorType.TYPE_ERROR, f"Invalid type, expected int but got {type(input_value)} of value {input_value}")
        return input_value   

class InputSFunctionCall(FunctionCall):
    '''
    Represents a function call to the built-in input function
    '''
    def __init__(self, name: str, function: Function, args: Optional[List[Element]], calling_scope: Optional[Scope]):
        super().__init__(name, function, args, calling_scope)
        
    def run(self):
        # accept up to one argument
        if len(self.args) > 1:
            Interpreter.global_interpreter.error(ErrorType.NAME_ERROR, f"No inputs() function found that takes > 1 parameter")
        
        # if there is an argument, print it
        if self.args:
            prompt = self.args[0]
            Interpreter.global_interpreter.output(prompt)
        
        input_value = Interpreter.global_interpreter.get_input()
        return input_value 
    
class PrintFunctionCall(FunctionCall):
    '''
    Represents a function call to the built-in print function
    '''
    def __init__(self, name: str, function: Function, args: Optional[List[Element]], calling_scope: Optional[Scope]):
        super().__init__(name, function, args, calling_scope)
        
    def run(self):        
        values = self.args
        
        for i, val in enumerate(values):
            # replace bools with strings
            if type(val) == bool:
                values[i] = "true" if val else "false"
            # replace NIL with "nil"
            if val == Interpreter.NIL:
                values[i] = "nil"
                        
        # print the values
        output_string = "".join([str(val) for val in values])
        Interpreter.global_interpreter.output(output_string)
        
        return Interpreter.NIL
        

# ===================================== MAIN Testing =====================================
def main():
    program_source = """
func bar(x) {
 print("bar: ", x);
 return x;
}

func main() {
 var a;
 a = bar(0);
 a = a + bar(1);
 a = a + bar(2);
 a = a + bar(3);
 print("---");
 print(a);
 print("---");
 print(a);
}
    """
    
    interpreter = Interpreter()
    
    interpreter.run(program_source)
    
if __name__ == "__main__":
    main()