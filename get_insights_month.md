# Get Month Insights

    GET insights/monthly
    
Returns insights for a particular month

## Parameters
  * meterId
  * gatewayId
  * date

## Example
### Request

    https://api.copperlabs.com/api/v1/insights/monthly?meterId=<METER>&gatewayId=<GATEWAY>&date=<DATETIME>

### Response

Field | Description
--- | --- 
twoHourKwh | power readings resampled at two hour intervals 
kwhRecorded | total energy used for the day
baselineKwhRecorded | weekly average of total energy used each day
twoHourKwhBaseline | weekly average of power readings resampled at two hour intervals 
highestTwoHourInterval | maxium power reading for the day
weather | weather information for the day

``` json
{
	"twoHourKwh": [0, 1, 0, 0.5312907431552958, 1.985716059565675, 5.164137265075624, 7.124123290543139, 9.365048943363036, 7.829683698297231, 1, null, null],
	"kwhRecorded": 34,
	"baselineKwhRecorded": 18.1429,
	"twoHourKwhBaseline": [0.428571, 0.26372600000000007, 0.6179829999999998, 0.2611500000000002, 0.6828299999999998, 4.8276699999999995, 4.75137, 3.100200000000001, 1.7958999999999978, 0.6992000000000012, 0.28570000000000206, 0.4285999999999994],
	"highestTwoHourInterval": 5,
	"weather": {
		"icon": "partly-cloudy-day",
		"precip": "rain",
		"temperature": 89.78
	}
}
```
