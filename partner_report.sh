#!/bin/bash
#
#  Copyright 2021 Copper Labs, Inc.

# set -x

reports_dir=generated
report_date=`date "+%Y%m%d"`
handle=$1

. venv/bin/activate
prem_report=${reports_dir}/premises.${handle}.${report_date}.csv
echo "Compiling prem list for ${handle}"
num_prems=`python copper-enterprise-client.py --csv-output-file ${prem_report} premise | grep 'Building information for' | awk '{print $4}'`

health_report=${reports_dir}/health_history.${handle}.${report_date}.csv
echo "Compiling health history for ${handle}"
python copper-enterprise-client.py --csv-output-file ${health_report} report health

echo "prems created:                ${num_prems}"
echo "total gateways:               `cat ${health_report} | grep -c gateway`"
echo "active gateways:              `cat ${health_report} | grep gateway | grep -c active`"
echo "disconnected gateways:        `cat ${health_report} | grep gateway | grep -vc active`"
echo "total meters:                 `cat ${health_report} | grep -c meter`"
echo "connected meters:             `cat ${health_report} | grep meter | grep -c ,connected`"
echo "degraded/disconnected meters: `cat ${health_report} | grep meter | grep -vc ,connected`"

cd ${reports_dir}
report=${handle}.reports.${report_date}.zip
zip ${report} *.${handle}.${report_date}.csv
rm *.${handle}.*csv

echo "Done! Report is located at: ${reports_dir}/${report}"
