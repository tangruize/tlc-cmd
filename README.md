# TLC cmd tools

Welcome! Here you'll find scripts that automate TLC config file generation, batch model processing, simulation trace conversion to JSON, and Graphviz dot file conversion into traces.

Features:

- Comprehensive support for nearly all options in the TLA+ toolbox model checking panel
- Efficient batch processing of models
- Convenient saving of batch result tables
- Initialization of states from trace files
- Script for reading trace files into Python objects or JSON dumps
- Conversion of Graphviz dot state graph files into unique traces
- Seamless execution in distributed mode for easy scalability

## Dependencies

python3+, Java 11+

Optional modules:

```sh
pip3 install requests  # to download tla2tools.jar
pip3 install psutil    # for "memory ratio" option (see example.ini)
pip3 install networkx  # for conversion of Graphviz dot state graph file
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

### trace_reader.py

```txt
usage: trace_reader.py [-h] [-o JSON_FILE] [-i INDENT] [-p HANDLER] [-a] [-d] [-s] [-g] trace_file

Read TLA traces into Python objects

positional arguments:
  trace_file    TLA trace file

options:
  -h, --help    show this help message and exit
  -o JSON_FILE  output to json file
  -i INDENT     json file indent
  -p HANDLER    python user_dict and list/kv handers
  -a            save action name in '_action' key if available
  -d            make data structures hashable
  -s            sort dict by keys, true if -d is defined
  -g            get dot file graph
```

The trace file can be either the MC.out file or generated through the "simulation dump traces" option.

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

### trace_counter.py

```txt
usage: trace_counter.py [-h] [-p NPROC] [-n NTRACE] [-l LOGFILE] [-f HASHFILE] [-r] trace_dir

Simulation unique traces and distinct states counter

positional arguments:
  trace_dir    Trace dir

options:
  -h, --help   show this help message and exit
  -p NPROC     Number of processes
  -n NTRACE    Print progress every n traces
  -l LOGFILE   Log output to file
  -f HASHFILE  Hash file
  -r           Reduce only
```

### trace_generator.py

```txt
usage: trace_generator.py [-h] [-p NPROC] [-s SAVE_DIR] dot_file

Generate all simple paths of a dot file

positional arguments:
  dot_file     Dot file

options:
  -h, --help   show this help message and exit
  -p NPROC     Number of processes
  -s SAVE_DIR  Save all generated traces
```

## How to write config.ini

See [example.ini](./example.ini)

An example: [TPaxos/TPaxos-simulate.ini](./examples/TPaxos/TPaxos-simulate.ini)

An example of replacing Init:
[DieHard/DieHard-simulate-replace-init.ini](./examples/DieHard/DieHard-simulate-replace-init.ini)

## Misc

If you find bugs, welcome to submit issues and pull requests!

If you can speak Chinese, this [video tutorial](https://www.bilibili.com/video/BV1B3411r71a) may help you get started.
