# Welcome to Thermite, a CLI generator

What are the main things that this package provides.

- run any python function or class that has type annotations
- Use docstrings as the source of help
- not require changing the signature of existing functions to customize
- allow for classes as parameter annotations in functions that will be translated
  into grouped options
- Allow for custom classes to be used as type annotations.
- provides the possibility to change the defaults in the CLI by using 
  YAML or JSON definitions (an easy way to use configuration files with CLIs)
- provides a plugin-interface to extend functionality (e.g. the help itself
  is just a plugin)


## Installation

The package is available on pip, so can be installed with 

```bash
pip install thermite
```

## Getting started


For any function, class or instance, just use 

```python
from thermite import run

if __name__ == "__main__":
    run(obj)
```
and the package does the rest.

## Motivating example

As a motivating example I wanted to use a typical piece of code as you find it often 
in machine learning today. This repo of the [SimCLR](https://github.com/sthalles/SimCLR)
and specifically the implementation of the CLI in 
[run.py](https://github.com/sthalles/SimCLR/blob/master/run.py).
It is a well written repo and like many others of its type, provides a
command line interface using argparse. This is very normal and it works well,
but comes with certain drawbacks:

- The variables are inside a namespace, without typing. In general it is somewhat
  opaque where the variables are being used.
- The documentation of the variables in the argparse definition, not in docstrings. 
  So to maintain proper documentation, would need to write it twice.
- They are all ungrouped in one big list, which may be hard to distinguish what 
  is intended for what part of the algorithm.

With thermite, it is easy to arrange this differently.


## Customization options

The package allows plenty of different customization options, enabled 
through the plugin system. More information is available on other pages of
this documentation.


## Examples of common customizations

For various examples on how to customize the CLI, please see the Table of Contents
on the side.



## Bash completion

Not yet implemented. Plan is to have a JSON specification of the core
of the commands. This will then be run by bash using only minimal dependencies
so that loading the completion is fast, even if the CLI underneath can be slow
due to heavy dependencies (e.g. pytorch).

# Other CLI generators

There are already lots of CLI generators for python, many with lots of 
usage and great functionality that have inspired this package. Check them out.

- argparse
- click
- typer
- fire
- docopt
