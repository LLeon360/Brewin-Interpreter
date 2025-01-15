# Brewin Interpreter

This is an interpreter for the language Brewin made for the class CS 131 at UCLA in the Fall 2024 Quarter taught by Carey Nachenberg!

The parser and lexer are provided by the course organizers and can be found here [Brewin Interpreter Starter](https://github.com/UCLA-CS-131/fall-24-project-starter).

## Variations / Versions

The various specs are linked here:
- [v4](https://docs.google.com/document/d/1vUSQwrq8ePh-pmc2hia8GmapXXOSEEpu7xw2tgTbgII/edit?tab=t.0#heading=h.63zoibjlqvny)
- [v3](https://docs.google.com/document/d/1seLyYfAJs9xj_XgE8mB23KHuAGQOCnfYmRAwW4P8u1k/edit?tab=t.0#heading=h.3e9u78ortlte)
- [v2](https://docs.google.com/document/d/1M4e3mkNhUKC0d7dJZSetbR4M3ceq8y8BiGDJ4fMAK6I/edit?tab=t.0#heading=h.63zoibjlqvny)
- [v1](https://docs.google.com/document/d/1npomXM55cXg9Af7BUXEj3_bFpj1sy2Jty2Nwi6Kp64E/edit?tab=t.0#heading=h.63zoibjlqvny)

## TLDR:

Essentially,
**v1** supports basic code execution in the main function with dynamically typed variables and no conditionals. There are simple built-in functions like inputi for inputing numbers and printing as well as a few operators.

**v2** supports function definitions and control flow which includes if statements and for statements as well as returns. This brings about proper scoping within functions and code blocks as well as implementing requisite mechanisms for argument passing and managing scopes. 

**v3** is for Brewin++, a departure from the dynamically-typed versions that come previous as it enforces static typing of variables, arguments, and return types. Additionally, there are user-defined types in the form of structs which use pass-by-reference semantics. Additionally there are coercions for integers and booleans. There are void functions and seperately NIL values for structs and different handling for equality between structs of different types and NIL values. 

**v4** is for Brewin#, another spin-off of Brewin which supports need semantics and lazy evaluation as found in languages like Haskell. This means that expressions are not evaluated until they are necessarily used and then cached for further use. This requires mechanisms for snapshotting the environment and passing storing references to the cached versions of inner expressions in nested expressions. Another major feature is exception handling with the inclusion of try-catch handling of exceptions. Short-circuiting is also implemented to avoid unnecessary evaluations in AND and OR expressions.  

## Get Started

Each version of the interpreter can be found within the corresponding interpretervN.py file and can be run with the provided main function below it to execute a given Brewin program.

A provided autograder can be found [here](https://github.com/UCLA-CS-131/fall-24-autograder) which acts as a harness to execute a collection of tests for each version of the interpreter. The test cases can be viewed in plaintext alongside their intended outputs.

## Final Notes

Again, credits for the interpreter base and parser and lexer as well as the autograder goes to course organizers!
