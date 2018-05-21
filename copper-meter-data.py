#!/usr/bin/python

#  copper-meter-data.py
#  Created by jeffm on 11/6/17.

import sys
import requests, json
import urllib

try:
    meterId = sys.argv[1]
    meterKey = sys.argv[2]
except:
    print "please use syntax", sys.argv[0], "meterId, meterKey"
    exit(1)

from datetime import datetime, timedelta
#server assumes UTC ISO 8601 time format
endDate = datetime.utcnow()
#adjust this if you want more or less data
startDate = endDate - timedelta(hours=24) 
print startDate, "to", endDate

url = 'https://api.copperlabs.com/api/v1/data'
headers = {'api-key': meterKey}
params = {'meterId': meterId,
          'startDate': str(startDate),
          'endDate': str(endDate),
        }

r = requests.get(url, headers=headers, params=params)
print(r.url)
if r.status_code != 200:
    print r
else:
    data = r.json()
    print 'units:', data['units']
    print 'data:'
    for e in data['data']:
        print e['time'], e['value']
