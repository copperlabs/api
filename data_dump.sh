#!/bin/bash

set -x

enterprise_name=$1
start_date=$2   # Provide in format: YYYY-MM-DD, ex: 2020-09-25
days=$3
granularity=$4

output_base_dir="generated/${enterprise_name}"
report_date=`date "+%Y%m%d"`

for i in $(eval echo "{0..$days}")
do
    bucket=`date -j -v +${i}d -f "%Y-%m-%d" "${start_date}" "+%Y-%m-%d"`
    sdate="${bucket}T06:00:00Z"
    fdate=`date -j -v +$((i+1))d -f "%Y-%m-%d" "${start_date}" "+%Y-%m-%dT06:00:00Z"`
    echo $bucket
    output_dir="${output_base_dir}/${bucket}"
    mkdir -p ${output_dir}
    python copper-enterprise-client.py \
      --output-dir ${output_dir} \
      --csv-output-file meter_summary.csv \
      meter usage \
        --granularity ${granularity} ${sdate} ${fdate}
done

cd generated
zip -r ${enterprise_name}.${report_date}.zip ${enterprise_name}
