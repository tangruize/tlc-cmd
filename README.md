# Run TLC in CMD

This tool automatically generates TLC config files and can batch models.

Features:

- Support almost all options in TLA+ toolbox model checking panel
- Batch models
- Save batch result table
- Set an Init state from a trace file
- Script to read trace file to python object or dump json

## Dependencies

python3+, Java 8+

Optional modules:

```sh
pip3 install requests  # to download tla2tools.jar
pip3 install psutil    # for "memory ratio" option (see example.ini)
```

## How to run

### tlcwrapper.py

```txt
usage: tlcwrapper.py [-h] [-j CLASSPATH] [-g] [-r] [-s] [-d] [-c] [-m] [-n] [config.ini]

Run TLC in CMD

positional arguments:
  config.ini    Configuration file (if not presented, stdin is used)

optional arguments:
  -h, --help    show this help message and exit
  -j CLASSPATH  Java classpath to use
  -g            Generate TLC config files and print Java CMD strings
  -r            Run without processing TLC output
  -s            Do not save summary file
  -d            Download tla2tools.jar and CommunityModules-deps.jar and exit
  -c            separate constants and model options into two files
  -m            Require community modules
  -n            Not to print debug messages
```

An example: [DieHard/run.sh](./examples/DieHard/run.sh)

A new feature: "-c" separates constants module and auto extends it in your spec,
so that you can use the values of `set of model values` in your spec.

### trace_reader.py

```txt
usage: trace_reader.py [-h] [-o JSON_FILE] [-i INDENT] trace_file

Read TLA traces into Python objects

positional arguments:
  trace_file    TLA trace file

optional arguments:
  -h, --help    show this help message and exit
  -o JSON_FILE  output to json file
  -i INDENT     json file indent
```

The trace file is the MC.out file or dumped by the `simulation dump traces` option.

## How to write config.ini

See [example.ini](./example.ini)

An example: [TPaxos/TPaxos-simulate.ini](./examples/TPaxos/TPaxos-simulate.ini)

An example of replacing Init:
[DieHard/DieHard-simulate-replace-init.ini](./examples/DieHard/DieHard-simulate-replace-init.ini)

## Misc

If you find bugs, welcome to submit issues and pull requests!

If you can speak Chinese, this [video tutorial](https://www.bilibili.com/video/BV1B3411r71a) may help you get started.
