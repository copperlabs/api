# Copper Labs API

Copper provides real time energy data through a RESTful API.

# Authentication
* https is required. Insecure connections are rejected.
* Connections without an access key are rejected.

# Parameters
* All data is JSON
* All datetime fields are urlencoded ISO8601  

# Configuration
### Set the meter the gateway is tracking
```
curl -i -H "api-key:<KEY>" -X PUT "https://api.copperlabs.com/api/v1/gateway/<GATEWAY>" -d 'meterId=<METER>'
```

### Flush meter learning from a particular gateway
```
curl -i -H "api-key:<KEY>" -X POST "https://api.copperlabs.com/api/v1/gateway/flush/<GATEWAY>"
```

### Dump meter configuration
```
curl -i -H "api-key:<KEY>" -X GET https://api.copperlabs.com/api/v1/meter/<METER>?json=true
```

### Dump gateway configuration
```
curl -i -H "api-key:<KEY>" -X GET https://api.copperlabs.com/api/v1/gateway/<GATEWAY>?json=true
```

### Send push notification to applications associated with a particular meter
```
curl -i -H "api-key:<KEY>" -X POST "https://api.copperlabs.com/api/v1/push/<METER>" --data-urlencode message="42"
```

# Data

### Report the last few energy readings, current power (2nd energy derivative) and acceleration (3rd energy derivative)
```
curl -i -H "api-key:<KEY>" -X GET "https://api.copperlabs.com/api/v1/consumption/instant?meterId=<METER>"
```

### Report all energy readings within the startDate and endDate
```
curl -i -H "api-key:<KEY>" -X GET "https://api.copperlabs.com/api/v1/data?meterId=<METER>&startDate=<DATETIME>&endDate=<DATETIME>"
```

### Report all energy readings within the startDate and endDate (unabridged)
```
curl -i -H "api-key:<KEY>" -X GET "https://api.copperlabs.com/api/v1/consumption?meterId=<METER>&startDate=<DATETIME>&endDate=<DATETIME>"
```

### Report insights for day
```
curl -i -H "api-key:<KEY>" -X GET "https://api.copperlabs.com/api/v1/insights?meterId=<METER>&gatewayId=<GATEWAY>&date=<DATETIME>
```

### Report insights for month
```
curl -i -H "api-key:<KEY>" -X GET "https://api.copperlabs.com/api/v1/insights/monthly?meterId=<METER>&gatewayId=<GATEWAY>&date=<DATETIME>
```

