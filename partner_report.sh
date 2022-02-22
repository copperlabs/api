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
num_prems=`python copper-enterprise-client.py --csv-output-file ${prem_report} premise --with-users | grep 'Building information for' | awk '{print $4}'`
# BUG: repeat to make sure cloud has a fully-populated cache when fetching user emails
num_prems=`python copper-enterprise-client.py --csv-output-file ${prem_report} premise --with-users | grep 'Building information for' | awk '{print $4}'`

health_report=${reports_dir}/health_history.${handle}.${report_date}.csv
echo "Compiling health history for ${handle}"
python copper-enterprise-client.py --csv-output-file ${health_report} report health

echo "prems created:                         ${num_prems}"
echo "mobile users:                          `cat ${prem_report} | grep -c has_mobile_app`"
echo "total gateways:                        `cat ${health_report} | grep -c gateway`"
echo "active gateways:                       `cat ${health_report} | grep gateway | grep -c active`"
echo "disconnected gateways:                 `cat ${health_report} | grep gateway | grep -vc active`"
echo "total meters:                          `cat ${health_report} | grep -c meter`"
echo "connected meters:                      `cat ${health_report} | grep meter | grep -c ,connected`"
echo "degraded/disconnected meters:          `cat ${health_report} | grep meter | grep -vc ,connected`"
echo "total electric meters:                 `cat ${health_report} | grep -c ,power`"
echo "connected electric meters:             `cat ${health_report} | grep ,power | grep -c ,connected`"
echo "degraded/disconnected electric meters: `cat ${health_report} | grep ,power | grep -vc ,connected`"
echo "total gas meters:                      `cat ${health_report} | grep -c ,gas`"
echo "connected gas meters:                  `cat ${health_report} | grep ,gas | grep -c ,connected`"
echo "degraded/disconnected gas meters:      `cat ${health_report} | grep ,gas | grep -vc ,connected`"
echo "total water meters:                    `cat ${health_report} | grep -c ,water`"
echo "connected water meters:                `cat ${health_report} | grep ,water | grep -c ,connected`"
echo "degraded/disconnected water meters:    `cat ${health_report} | grep ,water | grep -vc ,connected`"

cd ${reports_dir}
report=${handle}.reports.${report_date}.zip
zip ${report} *.${handle}.${report_date}.csv
rm *.${handle}.*csv

echo "Done! Report is located at: ${reports_dir}/${report}"
