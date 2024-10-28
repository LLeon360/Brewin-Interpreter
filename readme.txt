All Good!! :DDD


Notes (not bugs):

The interpreter is written modularly with future expansion in mind so there is a skeleton of support for features like scoping, other function defintions (besides main), argument passing, etc that aren't really tested.

The interpreter doesn't enforce a couple things for main because the spec states that these won't be tested:
- Checking for at least one statement in the body of main
- Checking that main has no parameters

This also isn't a bug but just an explanation of some exception raising in the interpreter:

There are situations in which the interpreter will raise Exceptions not through the `InterpreterBase` `error()` function because those Exceptions would not be semantic errors but more like sanity checks, ex. calling the evaluate_expression on an Element that does not fit into any possible expression category and thus falls through all pattern matching. This should never happen because evaluate_expression is only called when an expression should be there either syntactically (in which case the parser should catch it) or because the program already checked that it was an expression. 

Leon Liu
606226599