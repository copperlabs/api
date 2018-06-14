# Get Historical Data

    GET data
    
Returns all energy readings within a datetime range

## Parameters
  * meterId
  * startTime
  * endTime

## Example
### Request

    https://api.copperlabs.com/api/v1/data

### Response

Field | Description
--- | --- 
units | meter correction/scaling (e.g. for electic meters units=1.0 means values are kilowatt-hours while units=0.001 means watt-hours)
data | array of energy readings
time | ISO8601 UTC
value | energy reading

``` json
{
	"units": 1,
	"data": [{
		"time": "2018-06-13T01:18:20.966Z",
		"value": 6356
	}, ... {
		"time": "2018-06-14T00:41:01.268Z",
		"value": 6391
	}]
}
```
