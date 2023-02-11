# Why another CLI generator?

There are already lots of CLI generators for python, many with lots of usage and great functionality. Just to name the most important are
- argparse
- click
- typer
- fire

So why another one? While argparse and click are both very feature rich, it is the functionality of fire and typer that are interesting,
with fire allowing to run pretty much any python object and typer making extensive use of type annotations. 

This project aims to take the best of fire and typer and create a package that lets you

- run any python function or class that has type annotations
- Use docstrings as the source of help
- not require changing the signature of existing functions to customize
- avoid a plethora of decorators on every function that is being used
- allow for grouped options in functions by using dataclasses as parameters

Overall it should make it easier to create CLIs, especially for complex cases with lots of options.

# What does a CLI look like in practice

## A single function

When a single function is passed, the parameters of that function are
made available to the tool using options. If the return parameter is None, the
run will end after executing the function. If the annotated return value is a 
class, the CLI will make the *instancemethods* and *classmethods* available
as subcommands.

## A class definition

When using a class definition, the __init__ function is taken as the starting
point with the classmethods and instancemethods of the return used as the 
subcommands.

## An instance of a class
