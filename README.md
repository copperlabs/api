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
- **https://api.copperlabs.com/api/v2/**

## Example python command-line scripts

### Pre-requisites:
- pip install -r requirements.txt

### Individual (single-account) access
This script will log in using your previously-registered email address (same as the mobile app installed on your phone), and provide a raw JSON dump of all premises and meter data attached to your account.

#### Execution:
```
# Display summary table of connected meters with current reading
python copper-client.py --summary

# Dump instant, current day and baseline usage per meter for all premises to CSV file(s)
python copper-client.py  --save-to-csv
```

### Enterprise (multi-account) access
This script will log in using a client ID and secret (provided out-of-band) and dump all meters for premises within the enterprise.

#### Execution:
```
# Bulk download of all connected meters with current reading
python copper-enterprise-client.py --csv-output-file generated/output.csv bulk
```

#### Note for interpreting CSV output files
Meter usage and baseline data returns a timeseries, by default on a bihour basis, in addition to summary stats for the meter. Each row in the CSV starts with one of four patterns:
- `usage_summary__` => will be the same for a set of unique meter usage_result__ rows
- `usage_result__` => will be unique for each meter row
- `baseline_summary__` => will be the same for a set of unique meter usage_result__ rows
- `baseline_result__` => will be unique for each meter row
