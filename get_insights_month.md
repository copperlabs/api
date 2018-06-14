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
twentyFourHourKwh | power readings resampled at 24 hour intervals
kwhRecorded | total energy used for the month (so far)
baselineKwhRecorded | monthly average of total energy used this month
twentyFourHourKwhBaseline | monthly average of power readings resampled at 24 hour intervals 

``` json
{
	"twentyFourHourKwh": [31, 5, 5, 15, 34, 18, 34, 12, 5, 5, 30, 23, 34, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null],
	"kwhRecorded": 251,
	"baselineKwhRecorded": 567.5,
	"twentyFourHourKwhBaseline": [5, 9.75, 22, 24.052799999999998, 31.697200000000002, 19.75, 19.75, 19.75, 5, 9.75, 22, 24.052799999999998, 31.697200000000002, 19.75, 19.75, 19.75, 5, 9.75, 22, 24.052799999999998, 31.697200000000002, 19.75, 19.75, 19.75, 5, 9.75, 22, 24.052799999999998, 31.697200000000002, 19.75]
}
```
