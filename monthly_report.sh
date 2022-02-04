#!/bin/bash
#
#  Copyright 2021-2022 Copper Labs, Inc.

# set -x

handle=$1
for_date=$2
reports_dir=generated/${handle}

ln -sf .envrc.${handle} .envrc

. venv/bin/activate
report=monthly_report.${handle}.${for_date}.csv
python copper-enterprise-client.py --output-dir ${reports_dir} --csv-output-file ${report} report monthly ${for_date}

echo "Done! Report is located at: ${reports_dir}/${report}"