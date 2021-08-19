# Run TLC in CMD

TLC's config files are not intuitive to write.
This tool automatically generates TLC config files and can batch models.

## Dependencies

python3+, Java 8+

Optional modules:

```sh
pip3 install requests  # download tla2tools.jar
pip3 install psutil    # for "memory ratio" option (see example.ini)
```

## How to run

```txt
usage: tlcwrapper.py [-h] [-g] [-r] [-s] [-d] [-c] [config.ini]

Run TLC in CMD

positional arguments:
  config.ini  Configuration file (if not presented, stdin is used)

optional arguments:
  -h, --help  show this help message and exit
  -g          Generate TLC config files and print Java CMD strings
  -r          Run without processing TLC output
  -s          Do not save summary file
  -d          Download tla2tools.jar and exit
  -c          separate constants and model options into two files
```

An example: [DieHard/run.sh](./examples/DieHard/run.sh)

A new feature: "-c" separates constants module and auto extends it in your spec,
so that you can use the values of `set of model values` in your spec.

## How to write config.ini

See [example.ini](./example.ini)

An example: [TPaxos/TPaxos-simulate.ini](./examples/TPaxos/TPaxos-simulate.ini)

## Misc

If you find bugs, welcome to submit issues and pull requests!
