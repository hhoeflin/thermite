# Adapting how *Lists* are handled

## Default

With lists we have a number of different ways on how to deal with them.

The basic version is that lists with options are used by
specifying the option multiple times. For this behaviour
nothing special needs to be done.

!!! Example "Basic version for options with List type"

    === "Help" 
        ```txt 
        --8<-- 'examples/lists/default_help.out'
        ```

    === "Output"
        ```txt 
        --8<-- 'examples/lists/default_output.out'
        ```
    
    === "Code" 
        ```python 
        --8<-- 'examples/lists/default.py'
        ```


## Passing multiple arguments for a single call to option

We can also set it up so that we can pass multiple values to the 
list for a single call to the option.


!!! Example "Single option with variable length arguments"


    === "Help" 
        ```txt 
        --8<-- 'examples/lists/var_length_list_opt_help.out'
        ```

    === "Output"
        ```txt 
        --8<-- 'examples/lists/var_length_list_opt_output.out'
        ```

    === "Code" 
        ```python 
        --8<-- 'examples/lists/var_length_list_opt.py'
        ```

## Multiple lists as arguments with no-op separator

in this library even multiple variable length arguments are possible,
we just have to seperate them with a no-op option. 

!!! example "multiple lists with variable arguments"

    === "help" 
        ```txt 
        --8<-- 'examples/lists/multiple_args_help.out'
        ```

    === "output"
        ```txt 
        --8<-- 'examples/lists/multiple_args_output.out'
        ```
    
    === "code" 
        ```python 
        --8<-- 'examples/lists/multiple_args.py'
        ```



## Setting an empty list (if it is not the default)

We can also set a trigger that sets a parameter to an empty list.

!!! example "Trigger for empty list"

    === "code" 
        ```python 
        --8<-- 'examples/lists/empty_list.py'
        ```

    === "help" 
        ```txt 
        --8<-- 'examples/lists/empty_list_help.out'
        ```

    === "output"
        ```txt 
        --8<-- 'examples/lists/empty_list_output.out'
        ```


Show lists with:

- an option to specify an empty list


