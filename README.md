# Run TLC in CMD

TLC's config files are not intuitive to write.
I write this tool to automatically generate TLC config files and batch check models.

## Dependencies

python3+, Java 8+

## How to run

```sh
python3 tlcwrapper.py config.ini
```

An example: [DieHard/run.sh](./examples/DieHard/run.sh)

## How to write config.ini

See [example.ini](./example.ini)

An example: [TPaxos/TPaxos-simulate.ini](./examples/TPaxos/TPaxos-simulate.ini)

## Misc

If you find bugs, welcome to submit issues and pull requests!
