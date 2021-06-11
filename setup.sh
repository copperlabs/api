#!/bin/bash
#
#  Copyright 2021 Copper Labs, Inc.

# set -x

mkdir -p ./venv
virtualenv -p `which python3` ./venv
. venv/bin/activate
pip install -r requirements.txt
