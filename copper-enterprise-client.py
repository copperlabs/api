#  Copyright 2019 Copper Labs, Inc.
#
#  copper-enterprise-client.py
#
# prerequisites:
#    pip install -r requirements.txt
#    export COPPER_CLIENT_ID, COPPER_CLIENT_SECRET, COPPER_ENTERPRISE_ID

import argparse
import csv
from copper_cloud import CopperCloudClient
from dateutil import parser, tz
import os
from pprint import pformat
from texttable import Texttable
from urllib import urlencode


BULK_URL = '{url}/partner/{id}/bulk'.format(
    url=CopperCloudClient.API_URL,
    id=os.environ['COPPER_ENTERPRISE_ID'])
TIME_FMT = "%Y-%m-%dT%H:%M:%SZ"


def __write_csvfile(output_file, rows):
    with open(output_file, 'wb') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerows(rows)


def get_bulk_data(cloud_client):
    title = 'Bulk meter download'
    header = ['ID', 'Type', 'Address', 'City', 'Postal Code',
              'Latest Timestamp',
              'Latest Value']
    headers = cloud_client.build_request_headers()
    try:
        meters = cloud_client.get_helper(BULK_URL, headers)
    except Exception as err:
        print('\nGET error:\n' + pformat(err))
    rows = []
    for meter in meters['results']:
        url = '{url}/partner/meter/{id}/location'.format(
            url=CopperCloudClient.API_URL, id=meter['meter_id'])
        try:
            location = cloud_client.get_helper(url, headers)
        except Exception as err:
            print('\nGET error:\n' + pformat(err))
        timestamp_utc = parser.parse(meter['timestamp'])
        rows.append([
            meter['meter_id'],
            meter['meter_type'],
            location['street_address'],
            location['city_town'],
            location['postal_code'].rjust(5, '0'),
            timestamp_utc.astimezone(tz.tzlocal()),
            meter['value']
        ])
    dtypes = ['t', 't', 't', 't', 't', 'a', 'a']
    return title, header, rows, dtypes


def get_meter_usage(cloud_client):
    start = parser.parse(cloud_client.args.start).strftime(TIME_FMT)
    end = parser.parse(cloud_client.args.end).strftime(TIME_FMT)
    title = 'Meter usage download {start} through {end}'.format(
        start=start,  end=end)
    header = ['ID', 'Type', 'Sum Usage']
    headers = cloud_client.build_request_headers()
    try:
        meters = cloud_client.get_helper(BULK_URL, headers)
    except Exception as err:
        print('\nGET error:\n' + pformat(err))
    rows = []
    for meter in meters['results']:
        print('Collecting data for meter ' + meter['meter_id'])
        url = '{url}/partner/{pid}/meter/{mid}/usage?{qstr}'.format(
            url=CopperCloudClient.API_URL,
            pid=os.environ['COPPER_ENTERPRISE_ID'],
            mid=meter['meter_id'],
            qstr=urlencode({
                'granularity': 'hour',
                'start': start,
                'end': end,
                'include_start': False}))
        try:
            usage = cloud_client.get_helper(url, headers)
        except Exception as err:
            print('\nGET error:\n' + pformat(err))
        rows.append([
            usage['meter_id'],
            usage['meter_type'],
            usage['sum_usage'],
        ])
        results = []
        results.append(['timestamp', 'energy', 'power'])
        for result in usage['results']:
            rx_utc = parser.parse(result['time'])
            rx_local = rx_utc.astimezone(tz.tzlocal()).replace(tzinfo=None)
            results.append([
                rx_local,
                result['value'],
                result['power'],
                ])
        __write_csvfile('generated/{mid}.csv'.format(
            mid=usage['meter_id'].replace(':', '_')),
            results)
    dtypes = ['t', 't', 'a']
    return title, header, rows, dtypes


def main():
    parser = argparse.ArgumentParser(
        add_help=True,
        description='Command-line utilities to interact with Copper Cloud.')
    parser.add_argument(
        '--csv-output-file', dest='csv_output_file', default=None,
        help='Write output to CSV file.')
    parser.add_argument(
        '--quiet', dest='quiet', action='store_true', default=False,
        help='Suppress printing results to the console.')
    parser.add_argument(
        '--debug', dest='debug', action='store_true', default=False,
        help='Enable debug output')
    parser.add_argument(
        '--query-limit', dest='query_limit', default=None,
        help='Limit API query (for debugging purposes).')

    subparser = parser.add_subparsers()

    parser_a = subparser.add_parser("bulk")
    parser_a.set_defaults(func=get_bulk_data)

    parser_b = subparser.add_parser("meter")
    subparser_b = parser_b.add_subparsers()
    parser_c = subparser_b.add_parser("usage")
    time_fmt = '%%Y-%%m-%%dT%%H:%%M:%%SZ'
    parser_c.add_argument(
        'start',
        help='Query start time, formatted as: ' + time_fmt)
    parser_c.add_argument(
        'end',
        help='Query end time, formatted as: ' + time_fmt)
    parser_c.set_defaults(func=get_meter_usage)

    args = parser.parse_args()

    # Walk through user login (authorization, access_token grant, etc.)
    cloud_client = CopperCloudClient(args, BULK_URL)

    # func = switcher.get(args.command, lambda: 'Invalid')
    title, header, rows, dtypes = args.func(cloud_client)

    table = Texttable(max_width=0)
    table.set_deco(Texttable.HEADER)
    table.set_cols_dtype(dtypes)
    row_align = ['l'] * len(header)
    table.set_header_align(row_align)
    table.set_cols_align(row_align)
    rows.insert(0, header)
    table.add_rows(rows)

    if not args.quiet:
        print('\n\n{title}:\n'.format(title=title))
        print(table.draw() + '\n')

    if args.csv_output_file:
        __write_csvfile(args.csv_output_file, rows)

    print('complete!')


if (__name__ == "__main__"):
    main()
