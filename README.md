# Copper Labs Cloud API

## Overview

Copper is a home energy management platform that performs realtime analysis of energy data by collecting it directly from gas, water and electric meters you likely already have installed. The system is unique in that it’s low cost, easy to self install, realtime and independent of utility database integration, Green Button or Smart Grid (AMI) deployments. 

The Copper API is used by the Copper mobile application which handles meter on-boarding and display of user data and real-time alerts. Developers interested in developing alternative clients can do so with this public API.

### Support
For API support, please email info@copperlabs.com

## Authentication
* Insecure connections are rejected, https is required. 
* Requests without an 'api-key' header are rejected.
* Access varies from real-time high-resolution meter data to anonymized trends across geographies - depending on utility, ownership, meter and key.

## Throttling and caching
* Clients are rate-limited to a maximum of 1 request per minute and 1000 requests per day.
* Responses may contain a Cache-Control header which instructs the client to cache a response. The client should expect data to be valid for anywhere from 1 minute to an entire year depending on the data requested.

## API Versioning
The first part of the URI path specifies the API version you wish to access in the format `v{version_number}`. 

For example, version 1 of the API (most current) is accessible via:

```no-highlight
https://api.copperlabs.com/api/v1/
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
* `400` `Bad Request` There was a problem with the request (security, malformed, data validation, etc.)
* `401` `Unauthorized` The supplied API credentials are invalid
* `403` `Forbidden` The credentials provided do not have permission to access the requested resource
* `404` `Not found` An attempt was made to access a resource that does not exist in the API
* `405` `Method not allowed` The resource being accessed doesn't support the method specified (GET, POST, etc.).
* `500` `Server Error` An error on the server occurred

## Request Modifiers and Record Filtering
Request modifiers may be included in the request URI query string. The following modifiers are available throughout the API.  Other resource-specific modifiers are covered under the specific resource documentation sections.
* `startDate` ISO8601 date-time UTC.  
* `endDate` ISO8601 date-time UTC.  
* `date` ISO8601 date-time UTC.  
* `gatewayId` The gateway ID for the request.
* `meterId` The meter ID for the request.
* `appId` The client ID for the request.

Some values, such as dates, support range selection by using 'startDate' and 'endDate'.  i.e. all data available from January 1, 2018 at 8:00AM to February 1, 2018 at 8:00AM could be retrieved with the following query:

```no-highlight
https://api.copperlabs.com/xxxx/startDate=2018-01-01+00%3A00%3A00.000000&endDate=2018-02-01+00%3A00%3A00.000000
```

#### Note that all dates are in the url-encoded ISO8601 and returned in UTC - you will have to account for time zone adjustment depending on your client's location.

## Resources

### Configuration and General
- **[<code>GET</code> Get Meter](/get_nda.md)**
- **[<code>POST</code> Set Meter](/get_nda.md)**
- **[<code>GET</code> Get Gateway](/get_nda.md)**
- **[<code>PUT</code> Set_Gateway](/get_nda.md)**
- **[<code>GET</code> Get Client](/get_nda.md)**
- **[<code>POST</code> Set Client](/get_nda.md)**
- **[<code>POST</code> Send Alert to Client](/get_nda.md)**

### Data and Insights
- **[<code>GET</code> Get Instant](/get_instant.md)**
- **[<code>GET</code> Get Historical](/get_data.md)**
- **[<code>GET</code> Get Historical Unabridged](/get_consumption.md)**
- **[<code>GET</code> Get Insights for Day](/get_insights_day.md)**
- **[<code>GET</code> Get Insights for Month](/get_insights_month.md)**
- **[<code>GET</code> Get Energy Archetype](/get_archetype.md)**


