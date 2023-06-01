# Run TLC in CMD

This tool automatically generates TLC config files and can batch models.

Features:

- Support almost all options in TLA+ toolbox model checking panel
- Batch models
- Save batch result table
- Set an Init state from a trace file
- Script to read trace file to python object or dump json
- Make it easy to run distributed mode

## Dependencies

python3+, Java 11+

Optional modules:

```sh
pip3 install requests  # to download tla2tools.jar
pip3 install psutil    # for "memory ratio" option (see example.ini)
git submodule update --init --recursive  # for distributed mode
```

## How to run

### tlcwrapper.py

```txt
usage: tlcwrapper.py [-h] [-j CLASSPATH] [-g] [-r] [-s] [-d] [-c] [-m] [-n] [config.ini]

Run TLC in CMD

positional arguments:
  config.ini    Configuration file (if not presented, stdin is used)

options:
  -h, --help    show this help message and exit
  -j CLASSPATH  Java classpath to use
  -g            Generate TLC config files and print Java CMD strings
  -r            Run without processing TLC output
  -s            Do not save summary file
  -d            Download tla2tools.jar and CommunityModules-deps.jar and exit
  -c            Separate constants and model options into two files
  -m            Require community modules
  -n            Not to print debug messages
```

An example: [DieHard/run.sh](./examples/DieHard/run.sh)

New features:

- `-c` separates constants module and auto extends it in your spec,
  so that you can use the values of `set of model values` in your spec.
- distributed mode: easily run distributed mode with the [spssh](https://github.com/tangruize/spssh/) scripts.
  Just configure SSH no password login to worker nodes.

### trace_reader.py

```txt
usage: trace_reader.py [-h] [-o JSON_FILE] [-i INDENT] [-p HANDLER] [-a] trace_file

Read TLA traces into Python objects

positional arguments:
  trace_file    TLA trace file

options:
  -h, --help    show this help message and exit
  -o JSON_FILE  output to json file
  -i INDENT     json file indent
  -p HANDLER    python user_dict and list/kv handers
  -a            save action name in '_action' key if available
```

The trace file is the MC.out file or dumped by the `simulation dump traces` option.

New features:

- `-p` provides a python file with some handlers to replace data of the trace while converting.
- `-a` saves action name to `'_action'` key in JSON (requires latest TLC version)

Python `-p` handler example:

```py
# 'user_dict' replaces dict and list values (example: replace string 'None' to Python None obj)
user_dict = {'None': None}

# 'outside_kv_handler' replaces the outside dicts (i.e. keys are TLA+ variable names) keys and values
# 'inside_kv_handler' replaces the inside dicts/TLA+ records (nested in variables) keys and values
# Example: if key (TLA+ variable name) is "state", then return (k, v) without changing.
def outside_kv_handler(k, v):
    if k != "state":
        return k, v
    else:
        return k, "value is changed"

# 'list_handler' gets TLA+ set/sequence as list `l` with type annotation `k` (set/seq),
# and returns data after processing 
def list_handler(l, k):
    if k == "set":
        return l
    else:
        return [ "changed" ]
```

## How to write config.ini

See [example.ini](./example.ini)

An example: [TPaxos/TPaxos-simulate.ini](./examples/TPaxos/TPaxos-simulate.ini)

An example of replacing Init:
[DieHard/DieHard-simulate-replace-init.ini](./examples/DieHard/DieHard-simulate-replace-init.ini)

## Misc

If you find bugs, welcome to submit issues and pull requests!

If you can speak Chinese, this [video tutorial](https://www.bilibili.com/video/BV1B3411r71a) may help you get started.
