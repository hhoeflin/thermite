### Callbacks at the CLI level 

Callbacks at the CLI level are used to customize behavior based on user
input that is not directly related to the object for which the CLI is being created.
Typical use cases for this are:

- Showing the help for the current command
- Customizing default values based on JSON or YAML input files
- Creating shell-completion
- A 'no-op' callback, that does nothing but is useful to work as an input 
  delimiter for variable lengh options or arguments

In fact, all of these provided in this library (including the help itself) is
written only using public interfaces. So if you don't like the look of the current
help - you can just write your own :).

These callbacks can be specified to either work for the top-level command and
all subcommands or only for the top-level command. Using the event-system above
it is of course also possible to specify callbacks that only work for specific 
subcommands.

