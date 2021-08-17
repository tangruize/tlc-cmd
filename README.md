# Run TLC in CMD

TLC's config files are not intuitive to write.
I write this tool to automatically generate TLC config files and batch check models.

## Dependencies

python3+, Java 8+

Optional modules:

```sh
pip3 install requests  # download tla2tools.jar
pip3 install psutil    # for "memory ratio" option (see example.ini)
```

## How to run

```txt
usage: tlcwrapper.py [-h] [-g] [-r] [-s] [-d] [config.ini]

Run TLC in CMD

positional arguments:
  config.ini  Configuration file (if not presented, stdin is used)

optional arguments:
  -h, --help  show this help message and exit
  -g          Generate TLC config files and print Java CMD strings
  -r          Run without processing TLC output
  -s          Do not save summary file
  -d          Download tla2tools.jar and exit
```

An example: [DieHard/run.sh](./examples/DieHard/run.sh)

## How to write config.ini

See [example.ini](./example.ini)

An example: [TPaxos/TPaxos-simulate.ini](./examples/TPaxos/TPaxos-simulate.ini)

## Misc

If you find bugs, welcome to submit issues and pull requests!
