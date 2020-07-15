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
from datetime import datetime, timedelta, date, time
from dateutil import parser, tz
import os
from pprint import pformat, pprint
import sys
from texttable import Texttable
from urllib import urlencode


TIME_FMT = "%Y-%m-%dT%H:%M:%SZ"


def __make_bulk_url(limit=1000):
    return '{url}/partner/{id}/bulk?limit={limit}'.format(
        url=CopperCloudClient.API_URL,
        id=os.environ['COPPER_ENTERPRISE_ID'],
        limit=limit)


def tick():
    print '.',
    sys.stdout.flush()


def __write_csvfile(output_file, rows):
    with open(output_file, 'wb') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerows(rows)


def __get_all_meters(cloud_client):
    headers = cloud_client.build_request_headers()
    meters = []
    more_meters = True
    next_url = __make_bulk_url()
    try:
        while(more_meters):
            resp = cloud_client.get_helper(next_url, headers)
            meters += resp['results']
            more_meters = (resp.get('next', None))
            if (more_meters):
                next_url = '{url}{uri}'.format(
                    url=CopperCloudClient.BASE_API_URL,
                    uri=resp['next'])
    except Exception as err:
        print('\nGET error:\n' + pformat(err))
    return meters


def __get_meter_usage(cloud_client, meter_id, start, end, granularity):
    headers = cloud_client.build_request_headers()
    url = '{url}/partner/{pid}/meter/{mid}/usage?{qstr}'.format(
        url=CopperCloudClient.API_URL,
        pid=os.environ['COPPER_ENTERPRISE_ID'],
        mid=meter_id,
        qstr=urlencode({
            'granularity': granularity,
            'start': start,
            'end': end,
            'include_start': False}))
    return cloud_client.get_helper(url, headers)


def get_bulk_data(cloud_client):
    title = 'Bulk meter download'
    if cloud_client.args.detailed:
        header = ['ID', 'Type', 'Address', 'City', 'Postal Code',
                  'Latest Timestamp',
                  'Latest Value']
    else:
        header = ['ID', 'Type', 'Latest Timestamp', 'Latest Value']
    headers = cloud_client.build_request_headers()
    meters = __get_all_meters(cloud_client)
    rows = []
    print('Building information for {num} meters on {now}...'.format(
        num=len(meters), now=datetime.now().strftime('%c')))
    for meter in meters:
        meter_value = format(meter['value'], '.3f')
        timestamp_utc = parser.parse(meter['timestamp'])
        if cloud_client.args.detailed:
            url = '{url}/partner/meter/{id}/location'.format(
                url=CopperCloudClient.API_URL, id=meter['meter_id'])
            try:
                tick()
                location = cloud_client.get_helper(url, headers)
                rows.append([
                    meter['meter_id'],
                    meter['meter_type'],
                    location['street_address'],
                    location['city_town'],
                    location['postal_code'].rjust(5, '0'),
                    timestamp_utc.astimezone(tz.tzlocal()),
                    meter_value
                ])
            except Exception as err:
                print('\nGET error:\n' + pformat(err))
            dtypes = ['t', 't', 't', 't', 't', 'a', 't']
        else:
            rows.append([
                meter['meter_id'],
                meter['meter_type'],
                timestamp_utc.astimezone(tz.tzlocal()),
                meter_value
            ])
            dtypes = ['t', 't', 'a', 't']
    return title, header, rows, dtypes


def get_meter_usage(cloud_client):
    start = parser.parse(cloud_client.args.start).strftime(TIME_FMT)
    end = parser.parse(cloud_client.args.end).strftime(TIME_FMT)
    title = 'Meter usage download {start} through {end}'.format(
        start=start,  end=end)
    header = ['ID', 'Type', 'Sum Usage']
    meters = __get_all_meters(cloud_client)
    rows = []
    for meter in meters:
        print('Collecting data for meter ' + meter['meter_id'])
        usage = __get_meter_usage(cloud_client, meter['meter_id'], start, end, cloud_client.args.granularity)
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


def get_water_meter_reversals(cloud_client):
    midnight = datetime.combine(date.today(), time())
    start = (midnight - timedelta(days=30)).strftime(TIME_FMT)
    end = midnight.strftime(TIME_FMT)
    title = 'Suspect water meter reversals'
    header = ['Address', 'Indoor Usage', 'Outdoor Usage']
    headers = cloud_client.build_request_headers()
    meters = __get_all_meters(cloud_client)
    rows = []
    prems = {}
    num = cloud_client.args.check_limit if cloud_client.args.check_limit else len(meters)
    # Step 1: sort meters by prem
    print('Correlating water meters for each home...')
    for meter in meters:
        if not meter['meter_type'].startswith('water_'):
            continue
        if not num:
            break
        num -= 1
        tick()
        url = '{url}/partner/meter/{id}/location'.format(
            url=CopperCloudClient.API_URL, id=meter['meter_id'])
        location = cloud_client.get_helper(url, headers)
        if location['street_address'] not in prems.keys():
            prems[location['street_address']] = {}
        prems[location['street_address']][meter['meter_type']] = {
            'meter_id': meter['meter_id']
        }
    # Step 2: fetch meter usage and look for gross imbalance in usage
    print('Checking for potential water-meter reversals...')
    for (address, p) in prems.items():
        tick()
        indoor = {'sum_usage': None}
        outdoor = {'sum_usage': None}
        if 'water_indoor' in p.keys():
            indoor = __get_meter_usage(cloud_client, p['water_indoor']['meter_id'], start, end, 'day')
        if 'water_outdoor' in p.keys():
            outdoor = __get_meter_usage(cloud_client, p['water_outdoor']['meter_id'], start, end, 'day')
        add_the_row = False
        if not indoor['sum_usage'] or not outdoor['sum_usage']:
            # Flag missing data for further investigation
            add_the_row = True
        elif cloud_client.args.method == 'summer':
            # During summer: possible reversal if indoors dwarfs outdoor
            if indoor['sum_usage'] > 1000 and indoor['sum_usage'] > outdoor['sum_usage'] * 10:
                add_the_row = True
        elif outdoor['sum_usage'] > 1000:
            # During winter: possible reserval if outdoor has non-trivial usage
            add_the_row = True
        if add_the_row:
            rows.append([
                address,
                indoor['sum_usage'],
                outdoor['sum_usage']
            ])
    dtypes = ['a'] * len(header)
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
        '--query-limit', type=int, dest='query_limit', default=None,
        help='Limit API query (for debugging purposes).')

    subparser = parser.add_subparsers()

    parser_a = subparser.add_parser("bulk")
    parser_a.add_argument(
        '--detailed', dest='detailed', action='store_true', default=False,
        help='Enable detailed output')
    parser_a.set_defaults(func=get_bulk_data)

    parser_b = subparser.add_parser("meter")
    subparser_b = parser_b.add_subparsers()
    parser_c = subparser_b.add_parser("usage")
    parser_c.add_argument(
        '--granularity', dest='granularity', default='hour',
        help='Set query granularity for time-series data.')
    time_fmt = '%%Y-%%m-%%dT%%H:%%M:%%SZ'
    parser_c.add_argument(
        'start',
        help='Query start time, formatted as: ' + time_fmt)
    parser_c.add_argument(
        'end',
        help='Query end time, formatted as: ' + time_fmt)
    parser_c.set_defaults(func=get_meter_usage)
    parser_d = subparser_b.add_parser("check-for-water-reversals")
    parser_d.set_defaults(func=get_water_meter_reversals)
    parser_d.add_argument(
        '--check-limit', type=int, dest='check_limit', default=None,
        help='Limit number of homes to check (for debugging purposes).')
    parser_d.add_argument(
        '--method', dest='method', default='summer',
        help='Method for checking [summer, winter]')

    args = parser.parse_args()

    # Walk through user login (authorization, access_token grant, etc.)
    cloud_client = CopperCloudClient(args, __make_bulk_url(limit=1))

    # func = switcher.get(args.command, lambda: 'Invalid')
    title, header, rows, dtypes = args.func(cloud_client)

    table = Texttable(max_width=0)
    table.set_deco(Texttable.HEADER)
    table.set_cols_dtype(dtypes)
    row_align = ['l'] * len(header)
    row_align[-1] = 'r'
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
