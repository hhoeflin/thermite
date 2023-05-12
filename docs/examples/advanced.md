# Transferring parameters between functions

Show a generic wrapper class, for using a function that works for
a single 'file' to adapt it to work on directories of files,
using automatically the information on options from the original file

!!! Example "Transferring paramters from one function to another"

    === "Help" 
        ```txt 
        --8<-- 'examples/adv/param_transfer_help.out'
        ```

    === "Output"
        ```txt 
        --8<-- 'examples/adv/param_transfer_output.out'
        ```
    
    === "Code" 
        ```python 
        --8<-- 'examples/adv/param_transfer.py'
        ```

# Using JSON configuration files

We can also use a YAML or JSON file to dynamically set the defaults 
of the CLI. This can be useful for complex data science projects in order 
not to have to hardcode defaults. 



!!! Example "Setting defaults using a config file"

    === "Help" 
        ```txt 
        --8<-- 'examples/adv/config_file_help.out'
        ```

    === "Config file"
        ```txt 
        --8<-- 'examples/adv/config_file.yml'
        ```

    === "Code" 
        ```python 
        --8<-- 'examples/adv/config_file.py'
        ```

While not available yet, in a very similar way plugins can be created that use 
environment variables this way as well.


