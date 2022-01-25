# The `init` command

```shell
➜ pybm init -h               
usage: pybm init [<options>]

    Initialize pybm in a git repository by adding a configuration file
    and an environment list into a directory.
    

optional arguments:
  -h, --help            Show this message and exit.
  -v                    Enable verbose mode. Makes pybm log information that might be useful for debugging.
  --rm                  Overwrite existing configuration.
  -o OVERRIDES, --override OVERRIDES
                        Override a specific configuration setting with a custom value for the new pybm configuration file. Supplied arguments need to have the form 'key=value'. For a comprehensive list of
                        configuration options, run `pybm config list`.
  --skip-global         Skip applying system-wide defaults set in the global config file to the newly created pybm configuration.
```

The `pybm init` command creates a configuration file and a state file that tracks the currently available benchmark
environments. It is normally the first command you run in your `pybm` benchmarking workflow.

By passing the `--rm` option, you can reset an already existing configuration file to a default state.

The `-o/--override` switch can be used to override default values. If you are not satisfied with the default options, or
need to tweak a specific setting to suit your needs, supply your value of choice with the `key=value` syntax:

```shell
# this sets runner and builder to custom classes
pybm init -o runner.name=MyRunner -o builder.name=MyPythonBuilder
```

(If you are wondering about the default values or the names of certain config options, run the
command `pybm config list`.)

The `-o` switch can be used multiple times to set multiple different values at the same time. If you have a lot of
default values that you want to set, and do not want to type out long commands each time, consider writing a global pybm
config - this feature will be added in an upcoming release.

By default, if a global config file is present, global values are used as defaults when running `pybm init`. If you 
want to avoid adopting global settings locally, you can supply the `--skip-global` switch to `pybm init`.