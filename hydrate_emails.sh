#!/bin/bash

# set -x

more="1"

source .envrc
. ./venv/bin/activate

while [ "$more" -ne "0" ]
do
  more=`python copper-enterprise-client.py premise --with-users | grep -c missing`
  more=$((more))
  if [ "$more" -eq "0" ]; then
    exit
  fi
  echo "still hydrating... $more"
  sleep 2
done
