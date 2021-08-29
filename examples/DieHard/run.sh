#!/bin/bash

python3 ../../tlcwrapper.py DieHard.ini
MODEL_DIR=$(ls -dt model_* | head -1)
python3 ../../trace_reader.py ${MODEL_DIR}/MC.out -o ${MODEL_DIR}/MC.json -i 2
cat ${MODEL_DIR}/MC.json
