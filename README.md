# Copper Labs Cloud API

## Overview

Copper is a home energy management platform that performs realtime analysis of energy data by collecting it directly from gas, water and electric meters you likely already have installed. The system is unique in that it’s low cost, easy to self install, realtime and independent of utility database integration, Green Button or Smart Grid (AMI) deployments.

The Copper API is used by the Copper mobile application which handles meter on-boarding and display of user data and real-time alerts. Developers interested in developing alternative clients can do so with this public API.

### Support
For API support, please email info@copperlabs.com

## Authentication
* OAuth2 enables clients to obtain limited access to data without sharing passwords with third-party clients. Third-party clients can access data from a user's account by using the auth.copperlabs.com service. See [An Introduction to OAuth 2](https://www.digitalocean.com/community/tutorials/an-introduction-to-oauth-2) for more information.
* Insecure connections are rejected, https is required.
* Requests without a proper authentication token in the header are rejected.
* Access varies from real-time high-resolution meter data to anonymized trends across geographies - depending on utility, ownership, meter and permissions specific to the authentication.

## Throttling and caching
* Clients are rate-limited to a maximum of 100 requests per hour and 1000 requests per day.
* Responses may contain a Cache-Control header which instructs the client to cache a response. The client should expect data to be valid for anywhere from 1 minute to an entire year depending on the data requested.

## API Versioning
The first part of the URI path specifies the API version you wish to access in the format `v{version_number}`.

For example, version 2 of the API is accessible via:

```no-highlight
https://api.copperlabs.com/api/v2/
```

## HTTP requests
All API requests are made by sending a secure HTTPS request using one of the following methods, depending on the action being taken:

* `POST` Create a resource
* `PUT` Update a resource
* `GET` Get a resource or list of resources
* `DELETE` Delete a resource

For PUT and POST requests the body of your request may include a JSON payload, and the URI being requested may include a query string specifying additional filters or commands, all of which are outlined in the following sections.

## HTTP Response Codes
Each response will be returned with one of the following HTTP status codes:

* `200` `OK` The request was successful
* `400` `Bad request` There was a problem with the request (security, malformed, data validation, etc.)
* `401` `Unauthorized` The supplied API credentials are invalid
* `403` `Forbidden` The credentials provided do not have permission to access the requested resource
* `404` `Not found` An attempt was made to access a resource that does not exist in the API
* `405` `Method not allowed` The resource being accessed doesn't support the method specified (GET, POST, etc.).
* `429` `Too many requests` Client has sent too many requests in a given amount of time (rate limiting)
* `500` `Server error` An error on the server occurred

## Public API Endpoints
- **[Single premise for individual user](https://copperlabs.github.io/copper-types/app-docs.html)**
- **[Multiple premises for enterprise user](https://copperlabs.github.io/copper-types/partner-docs.html)**

## Example python command-line scripts
Pre-req: Install Python 3.9.

### (OPT) Create a python virtual environment and install requirements
```
./setup.sh
```

### Individual (single-account) access
This script will log in using your previously-registered email address (same as the mobile app installed on your phone), and provide a raw JSON dump of all premises and meter data attached to your account.

#### Execution:
```
# Display summary table of all meters for all homes on the account
python copper-client.py
```

### Enterprise (multi-account) access
This script will log in using a client ID and secret (provided out-of-band) and dump all meters for premises within the enterprise. This README captures the most common use-cases. Add '--help' to explore all available options for the script.

#### Premise Listing:
Download all premises created in the enterprise
```
python copper-enterprise-client.py --csv-output-file generated/premise_listing.csv premise
```

#### Bulk data download:
Bulk download of all connected meters with current reading
```
python copper-enterprise-client.py --csv-output-file generated/output.csv bulk
```
Include premise address:
```
python copper-enterprise-client.py --csv-output-file generated/output.csv bulk --detailed
```
Note that only meters heard 'recently' show up in the bulk output. Use the meter status command to fetch all meters, with last reading where appropriate
```
python copper-enterprise-client.py --csv-output-file generated/output.csv meter status --detailed
```

##### Note for interpreting CSV output files
Meter usage and baseline data returns a timeseries, by default on a bihour basis, in addition to summary stats for the meter. Each row in the CSV starts with one of four patterns:
- `usage_summary__` => will be the same for a set of unique meter usage_result__ rows
- `usage_result__` => will be unique for each meter row
- `baseline_summary__` => will be the same for a set of unique meter usage_result__ rows
- `baseline_result__` => will be unique for each meter row

#### Detailed historical meter usage download:
```
# Hourly download of all connected meters
# Start and end dates can span many days, one csv created per meter
python copper-enterprise-client.py --output-dir generated --csv-output-file meter_summary.csv meter usage '2020-12-22' '2021-01-12' --granularity hour
```
```
# Daily download of one connected meter:
# Note your OS might not allow creation of files with a ':' in the name, so replace ':' with '_' and manually enter the meter ID in the output filename.
python copper-enterprise-client.py --csv-output-file generated/meter_usage.${meter_id}.csv meter usage '2020-08-18' '2020-12-22' --meter-id ${meter_id} --granularity day
```
Or use the bash helper script (tested on macOS) to atomize high-granularity queries spanning a long timeframe due to API throttling:
```
# Minute download of all connected meters
# Start and end dates can span many days, one csv created per meter per day, organized into folders by day
./data_dump.sh ${name} ${start_date} ${finish_date} ${granularity}
ex:
./data_dump.sh foo 2020-10-01 2020-10-31 minute
```

##### Note for interpreting CSV output files
The CSV output file specific on the command-line contains summary information for premises, meters and sum usage between the start and end dates. Per-meter usage returns an hourly, interpolated timeseries and is written into a set of files; on per meter.

#### Grid readings download:
```
# Latest voltage and frequenct readings for all gateways
python copper-enterprise-client.py grid latest
```
```
# Historical voltage and frequenct readings for one gateway
# Note that output-dir is required due to the potential for a large number of files (one per gateway)
# Note the gateway-id parameter is optional to fetch readings for a single gateway instead of all gateways in the enterprise account.
python copper-enterprise-client.py --output-dir generated/xe_summit grid readings 2022-01-20 2022-01-21 --gateway-id 84cca8322ae4
```

#### Monthly report:
Download number of prems, meters and aggregate usage split out per meter type for a 1-month period.
```
python copper-enterprise-client.py report monthly 2021-09
```

#### Health report:
Download a 7-day history of all gateways and meter.
```
python copper-enterprise-client.py report health
```
Or use the bash helper script to bundle with a detailed premise listing into a zip archive.
```
./partner_report.sh ${handle}  # ${handle} is some string to name the report bundle
```
