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
