# Get Instant

    GET consumption/instant
    
Returns the last few energy readings, current power (2nd energy derivative) and acceleration (3rd energy derivative)

## Parameters
  * meterId

## Example
### Request

    https://api.copperlabs.com/api/v1/consumption/instant?meterId=<METER>

### Response

Field | Description
--- | --- 
kw | most recent power (2nd energy derivative) values
acc | usage acceleration (3rd energy derivative) value
age | age in hours for the last three energy readings
ts | ISO8601 timestamps UTC for the last three energy readings

``` json
{
	"kw": ["1.315", "4.295"],
	"acc": "-2.042",
	"age": ["0.821", "1.581", "2.280"],
	"ts": ["2018-06-14T00:41:01.268Z", "2018-06-13T23:55:24.457Z", "2018-06-13T23:13:29.650Z"]
}
```
