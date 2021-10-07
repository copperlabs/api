#  Copyright 2019-2021 Copper Labs, Inc.
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
import pytz
import sys
from texttable import Texttable
try:
    from urllib import urlencode
except ImportError:
    from urllib.parse import urlencode


class CopperEnterpriseClient():

    def __init__(self):
        self.time_fmt = "%Y-%m-%dT%H:%M:%SZ"
        self.parse_args()
        # Walk through user login (authorization, access_token grant, etc.)
        self.cloud_client = CopperCloudClient(self.args, self._make_bulk_url(limit=1))

    def run(self):
        title, header, rows, dtypes = self.args.func(self)

        table = Texttable(max_width=0)
        table.set_deco(Texttable.HEADER)
        table.set_cols_dtype(dtypes)
        row_align = ["l"] * len(header)
        table.set_header_align(row_align)
        table.set_cols_align(row_align)
        rows.insert(0, header)
        table.add_rows(rows)

        if not self.args.quiet:
            print("\n{title} (rows={num}):".format(title=title, num=len(rows) - 1))
            print (table.draw() + "\n")

        if self.args.output_dir and not os.path.exists(self.args.output_dir):
            os.makedirs(self.args.output_dir) 

        if self.args.csv_output_file:
            output_file = self.args.csv_output_file
            if self.args.output_dir:
                output_file = os.path.join(self.args.output_dir, output_file)
            dirname = os.path.dirname(output_file)
            if dirname and not os.path.exists(dirname):
                os.makedirs(dirname) 
            self.write_csvfile(output_file, rows, mode="w")

    def _make_bulk_url(self, limit=1000):
        return "{url}/partner/{id}/bulk?limit={limit}".format(
            url=CopperCloudClient.API_URL,
            id=self.args.enterprise_id,
            limit=limit,
        )

    def _make_element_url(self, endpoint, limit=1000, offset=0):
        return "{url}/partner/{id}/{endpoint}?limit={limit}&offset={offset}".format(
            url=CopperCloudClient.API_URL,
            id=self.args.enterprise_id,
            limit=limit,
            offset=offset,
            endpoint=endpoint
        )

    def tick(self, char="."):
        sys.stdout.write(char)
        sys.stdout.flush()

    def write_csvfile(self, output_file, rows, mode="w"):
        with open(output_file, mode) as csvfile:
            writer = csv.writer(csvfile)
            writer.writerows(rows)

    def _get_all_meters_bulk(self):
        headers = self.cloud_client.build_request_headers()
        meters = []
        more_meters = True
        next_url = self._make_bulk_url()
        try:
            while more_meters:
                resp = self.cloud_client.get_helper(next_url, headers)
                meters += resp["results"]
                more_meters = resp.get("next", None)
                if more_meters:
                    next_url = "{url}{uri}".format(
                        url=CopperCloudClient.BASE_API_URL, uri=resp["next"]
                    )
        except Exception as err:
            print ("\nGET error:\n" + pformat(err))
        return meters

    def _get_all_elements(self, endpoint):
        headers = self.cloud_client.build_request_headers()
        elements = []
        more_elements = True
        limit=1000
        offset=0
        next_url = self._make_element_url(endpoint, limit=limit, offset=offset)
        try:
            while more_elements:
                resp = self.cloud_client.get_helper(next_url, headers)
                elements += resp
                more_elements = (len(resp) == limit)
                if more_elements:
                    offset += limit
                    next_url = self._make_element_url(endpoint, limit=limit, offset=offset)
        except Exception as err:
            raise Exception("\nGET error:\n" + pformat(err))
        return elements

    def _daterange(self, start, end, step=1):
        return (start + timedelta(days=i) for i in range(0, (end - start).days + 1, step))

    def _get_meter_usage(self, meter_id, start, end, granularity, meter_created_at=None, step=1):
        headers = self.cloud_client.build_request_headers()
        if getattr(self.args, 'timezone', None):
            location = {"timezone": self.args.timezone}
        else:
            url = "{url}/partner/{eid}/meter/{mid}/location".format(
                url=CopperCloudClient.API_URL,
                mid=meter_id,
                eid=self.args.enterprise_id,
            )
            location = self.cloud_client.get_helper(url, headers)
        tz = pytz.timezone(location["timezone"])
        start = parser.parse(start)
        end = parser.parse(end)
        offset = int(tz.localize(start).strftime("%z")[:-2])
        usage = None
        meter_created = parser.parse(meter_created_at).astimezone(tz).replace(tzinfo=None) if meter_created_at else None
        if start < meter_created:
            start = meter_created
        for d in self._daterange(start, end, step):
            self.tick()
            istart = datetime.combine(d, time()) - timedelta(hours=offset)
            iend = istart + timedelta(days=step)
            if iend > end:
                iend = end
            if meter_created and iend < meter_created:
                if self.args.debug:
                    print('skipping meter {} which does not exist on {}'.format(meter_id, d))
                continue
            url = "{url}/partner/{eid}/meter/{mid}/usage?{qstr}".format(
                url=CopperCloudClient.API_URL,
                eid=self.args.enterprise_id,
                mid=meter_id,
                qstr=urlencode(
                    {
                        "granularity": granularity,
                        "start": istart.strftime(self.time_fmt),
                        "end": iend.strftime(self.time_fmt),
                        "include_start": False,
                    }
                ),
            )
            try:
                data = self.cloud_client.get_helper(url, headers)
                if not usage:
                    usage = {
                        "meter_id": data["meter_id"],
                        "meter_type": data["meter_type"],
                        "sum_usage": data["sum_usage"],
                        "results": data["results"],
                        "tz_offset": offset,
                        "tz": location["timezone"]
                    }
                else:
                    usage["sum_usage"] += data["sum_usage"]
                    if len (usage["results"]):
                        del usage["results"][-1]
                    usage["results"] += data["results"]

            except Exception as err:
                print('GET ERROR: {}'.format(pformat(err)))
        return usage

    def _get_meter_readings(self, meter_id, start, end, granularity, meter_created_at=None):
        headers = self.cloud_client.build_request_headers()
        if getattr(self.args, 'timezone', None):
            location = {"timezone": self.args.timezone}
        else:
            url = "{url}/partner/{eid}/meter/{mid}/location".format(
                url=CopperCloudClient.API_URL,
                mid=meter_id,
                eid=self.args.enterprise_id,
            )
            location = self.cloud_client.get_helper(url, headers)
        tz = pytz.timezone(location["timezone"])
        start = parser.parse(start)
        end = parser.parse(end)
        offset = int(tz.localize(start).strftime("%z")[:-2])
        readings = None
        meter_created = parser.parse(meter_created_at).astimezone(tz).replace(tzinfo=None) if meter_created_at else None
        for d in self._daterange(start, end):
            self.tick()
            istart = datetime.combine(d, time()) - timedelta(hours=offset)
            iend = istart + timedelta(days=1)
            if meter_created and istart < meter_created:
                if self.args.debug:
                    print('skipping meter {} which does not exist on {}'.format(meter_id, d))
                continue
            url = "{url}/partner/{eid}/meter/{mid}/readings?{qstr}".format(
                url=CopperCloudClient.API_URL,
                eid=self.args.enterprise_id,
                mid=meter_id,
                qstr=urlencode({
                    "start": istart.strftime(self.time_fmt),
                    "end": iend.strftime(self.time_fmt),
                }),
            )
            try:
                data = self.cloud_client.get_helper(url, headers)
                data["results"] = sorted(data["results"], key=lambda x:x["time"])
                if not readings:
                    readings = data
                else:
                    readings["results"] += data["results"]

            except Exception as err:
                print('GET ERROR: {}'.format(pformat(err)))
                break
        return readings

    def get_bulk_data(self):
        title = "Bulk meter download"
        if self.args.detailed:
            header = [
                "ID",
                "Type",
                "Address",
                "City",
                "Postal Code",
                "Latest Timestamp",
                "Latest Value",
            ]
        else:
            header = ["ID", "Type", "Latest Timestamp", "Latest Value"]
        bulk_meters = self._get_all_meters_bulk()
        meters = {meter["id"]: meter for meter in self._get_all_elements("meter")}
        premises = {}
        if self.args.detailed:
            premises = {premise["id"]: premise for premise in self._get_all_elements("premise")}
        rows = []
        print (
            "Building information for {num} meters on {now}...".format(
                num=len(bulk_meters), now=datetime.now().strftime("%c")
            )
        )
        for meter in bulk_meters:
            self.tick()
            meter_value = format(meter["value"], ".3f")
            timestamp_utc = parser.parse(meter["timestamp"])
            if self.args.detailed:
                rows.append(
                    [
                        meter["meter_id"],
                        meter["meter_type"],
                        premises[meters[meter["meter_id"]]["premise_id"]]["street_address"],
                        premises[meters[meter["meter_id"]]["premise_id"]]["city_town"],
                        premises[meters[meter["meter_id"]]["premise_id"]]["postal_code"].rjust(5, "0"),
                        timestamp_utc.astimezone(tz.tzlocal()),
                        meter_value,
                    ]
                )
                dtypes = ["t", "t", "t", "t", "t", "a", "t"]
            else:
                rows.append(
                    [
                        meter["meter_id"],
                        meter["meter_type"],
                        timestamp_utc.astimezone(tz.tzlocal()),
                        meter_value,
                    ]
                )
                dtypes = ["t", "t", "a", "t"]
        return title, header, rows, dtypes

    def get_prem_data(self):
        title = "Premise download"
        header = [
            "ID",
            "Created",
            "Address",
            "Suite/Apt",
            "City",
            "Postal Code",
            "County",
            "State",
            "Tags",
            "Email",
        ]
        headers = self.cloud_client.build_request_headers()
        url =  "{url}/partner/{id}/premise".format(
            url=CopperCloudClient.API_URL,
            id=self.args.enterprise_id,
        )
        prems = self.cloud_client.get_helper(url, headers)
        prems = sorted(prems, key=lambda x:x["created_at"])
        rows = []
        print (
            "Building information for {num} premises on {now}...".format(
                num=len(prems), now=datetime.now().strftime("%c")
            )
        )
        for p in prems:
            emails = ';'.join([u['email'] for u in p.get('user_list', [])]) 
            rows.append([
                p["id"],
                p["created_at"],
                p["street_address"].encode("utf8").decode('ascii'),
                p["suite_apartment_unit"],
                p["city_town"],
                p["postal_code"],
                p["county_district"],
                p["state_region"],
                p["tags"],
                emails,
            ])
        dtypes = ["a"] * len(header)
        return title, header, rows, dtypes

    def get_gateway_data(self):
        title = "Gateway download"
        header = [
            "ID",
            "Premise ID",
            "State",
            "Model",
            "Last Heard",
            "Firmware Version",
        ]
        headers = self.cloud_client.build_request_headers()
        url =  "{url}/partner/{id}/gateway".format(
            url=CopperCloudClient.API_URL,
            id=self.args.enterprise_id,
        )
        gateways = self.cloud_client.get_helper(url, headers)
        rows = []
        print (
            "Building information for {num} gateways on {now}...".format(
                num=len(gateways), now=datetime.now().strftime("%c")
            )
        )
        for g in gateways:
            rows.append([
                g["id"],
                g["premise_id"],
                g["state"],
                g["model"],
                g["last_heard"],
                g["firmware_version"],

            ])
        dtypes = ["a"] * len(header)
        return title, header, rows, dtypes

    def get_meter_usage(self):
        title = "Meter usage download {} through {}".format(self.args.start, self.args.end)
        header = ["ID", "Type", "Sum Usage"]
        meters = self._get_all_elements("meter")
        rows = []
        for meter in meters:
            if self.args.meter_id and meter["id"] != self.args.meter_id:
                continue
            destpath = "{output_dir}/{mid}.csv".format(output_dir=self.args.output_dir, mid=meter["id"].replace(":", "_"))
            if os.path.isfile(destpath):
                if self.args.debug:
                    print ("\nSkipping collection for meter " + meter["id"])
                continue
            print ("\nCollecting data for meter " + meter["id"])
            usage = self._get_meter_usage(
                meter["id"],
                self.args.start,
                self.args.end,
                self.args.granularity,
                meter["created_at"],
                self.args.step
            )
            if not usage or not usage["sum_usage"]:
                if self.args.debug:
                    print('nothing to save for meter {}'.format(meter["id"]))
                continue
            rows.append(
                [usage["meter_id"], usage["meter_type"], usage["sum_usage"],]
            )
            results = []
            results.append(["timestamp", "energy", "power"])
            for result in usage["results"]:
                rx_utc = parser.parse(result["time"])
                rx_local = rx_utc.astimezone(pytz.timezone(usage["tz"])).replace(tzinfo=None)
                results.append(
                    [rx_local, result["value"], result["power"],]
                )
            self.write_csvfile(destpath, results)
        dtypes = ["t", "t", "a"]
        return title, header, rows, dtypes

    def get_meter_readings(self):
        title = "Meter readings download {} through {}".format(self.args.start, self.args.end)
        header = ["ID", "Type", "Created"]
        meters = self._get_all_elements("meter")
        rows = []
        for meter in meters:
            if self.args.meter_id and meter["id"] != self.args.meter_id:
                continue
            created_utc = parser.parse(meter["created_at"])
            created_local = created_utc.astimezone(pytz.timezone(self.args.timezone)).replace(tzinfo=None)
            rows.append([
                meter["id"],
                meter["type"],
                created_local,
            ])
            destpath = "{output_dir}/{mid}.csv".format(output_dir=self.args.output_dir, mid=meter["id"].replace(":", "_"))
            if os.path.isfile(destpath):
                if self.args.debug:
                    print ("\nSkipping collection for meter " + meter["id"])
                continue
            print ("\nCollecting data for meter " + meter["id"])
            readings = self._get_meter_readings(
                meter["id"],
                self.args.start,
                self.args.end,
                meter["created_at"]
            )
            if not readings or not readings["results"]:
                if self.args.debug:
                    print('nothing to save for meter {}'.format(meter["id"]))
                continue
            results = [["ID", "Type", "Timestamp", "Actual ({})".format(meter["uom"]), "Normalized (kwh)"]]
            for result in readings['results']:
                rx_utc = parser.parse(result["time"])
                rx_local = rx_utc.astimezone(pytz.timezone(self.args.timezone)).replace(tzinfo=None)
                results.append([
                    readings["meter_id"],
                    readings["meter_type"],
                    rx_local,
                    result["actual"],
                    result["value"],
                ])
            self.write_csvfile(destpath, results)
        dtypes = ["t", "t", "a"]
        return title, header, rows, dtypes

    def get_grid_latest(self):
        raise Exception('not implemented')

    def _get_grid_readings(self, start, end, timezone, premise_id=None, gateway_id=None):
        headers = self.cloud_client.build_request_headers()
        tz = pytz.timezone(timezone)
        start = parser.parse(start)
        end = parser.parse(end)
        offset = int(tz.localize(start).strftime("%z")[:-2])
        readings = None
        for d in self._daterange(start, end):
            self.tick()
            istart = datetime.combine(d, time()) - timedelta(hours=offset)
            iend = istart + timedelta(days=1)
            query_params = {
                "start": istart.strftime(self.time_fmt),
                "end": iend.strftime(self.time_fmt),
            }
            if premise_id != None:
                query_params['premise_id'] = premise_id
            if gateway_id != None:
                query_params['gateway_id'] = gateway_id
            url = "{url}/partner/{eid}/grid/readings?{qstr}".format(
                url=CopperCloudClient.API_URL,
                eid=self.args.enterprise_id,
                qstr=urlencode(query_params)
            )
            try:
                data = self.cloud_client.get_helper(url, headers)
                data = sorted(data, key=lambda x:x["hw_timestamp"])
                if not readings:
                    readings = data
                else:
                    readings += data

            except Exception as err:
                print('GET ERROR: {}'.format(pformat(err)))
                break
        return readings

    def get_grid_readings(self):
        title = "Grid readings download {} through {}".format(self.args.start, self.args.end)
        header = ["Premise ID", "Address", "City", "Postal Code", "Gateway ID"]
        premises = {premise["id"]: premise for premise in self._get_all_elements("premise")}
        gateways = self._get_all_elements("gateway")
        all_gateway_readings = self._get_grid_readings(
            self.args.start,
            self.args.end,
            self.args.timezone,
        )
        rows = []
        for gateway in gateways:
            self.tick('g')
            rows.append([
                premises[gateway["premise_id"]]["id"],
                premises[gateway["premise_id"]]["street_address"],
                premises[gateway["premise_id"]]["city_town"],
                premises[gateway["premise_id"]]["postal_code"].rjust(5, "0"),
                gateway["id"]
            ])
            destpath = "{output_dir}/{gid}.csv".format(
                output_dir=self.args.output_dir,
                gid=gateway["id"]
            )
            if os.path.isfile(destpath):
                if self.args.debug:
                    a = 0
                print("\nSkipping collection for gateway {}".format(gateway["id"]))
                continue
            gateway_readings = [reading for reading in all_gateway_readings if reading["gateway_id"] == gateway["id"]]
            if not gateway_readings or len(gateway_readings) == 0:
                if self.args.debug:
                    a = 0
                print('nothing to save for gateway {}'.format(gateway["id"]))
                continue
            readings = [["Gateway ID", "Timestamp", "Voltage", "Frequency"]]
            for reading in gateway_readings:
                rx_utc = parser.parse(reading["hw_timestamp"])
                rx_local = rx_utc.astimezone(pytz.timezone(self.args.timezone)).replace(tzinfo=None)
                readings.append([
                    reading["gateway_id"],
                    rx_local,
                    reading["voltage"],
                    reading["frequency"],
                ])
            self.write_csvfile(destpath, readings)
        dtypes = ["t", "t", "t", "t", "t"]
        return title, header, rows, dtypes

    def get_water_meter_reversals(self):
        midnight = datetime.combine(date.today(), time())
        start = (midnight - timedelta(days=30)).strftime(self.time_fmt)
        end = midnight.strftime(self.time_fmt)
        title = "Suspect water meter reversals"
        header = ["Address", "Indoor Usage", "Outdoor Usage"]
        headers = self.cloud_client.build_request_headers()
        meters = self._get_all_meters_bulk()
        rows = []
        prems = {}
        num = (
            self.args.check_limit if self.args.check_limit else len(meters)
        )
        # Step 1: sort meters by prem
        print ("Correlating water meters for each home...")
        for meter in meters:
            if not meter["meter_type"].startswith("water_"):
                continue
            if not num:
                break
            num -= 1
            self.tick()
            url = "{url}/partner/{eid}/meter/{mid}/location".format(
                url=CopperCloudClient.API_URL, mid=meter["meter_id"],
                eid=self.args.enterprise_id,
            )
            location = self.cloud_client.get_helper(url, headers)
            if location["street_address"] not in prems.keys():
                prems[location["street_address"]] = {}
            prems[location["street_address"]][meter["meter_type"]] = {
                "meter_id": meter["meter_id"]
            }
        # Step 2: fetch meter usage and look for gross imbalance in usage
        print ("Checking for potential water-meter reversals...")
        for (address, p) in prems.items():
            self.tick()
            indoor = {"sum_usage": None}
            outdoor = {"sum_usage": None}
            if "water_indoor" in p.keys():
                indoor = self._get_meter_usage(
                    p["water_indoor"]["meter_id"], start, end, "day"
                )
            if "water_outdoor" in p.keys():
                outdoor = self._get_meter_usage(
                    p["water_outdoor"]["meter_id"], start, end, "day"
                )
            add_the_row = False
            if not indoor["sum_usage"] or not outdoor["sum_usage"]:
                # Flag missing data for further investigation
                add_the_row = True
            elif self.args.method == "summer":
                # During summer: possible reversal if indoors dwarfs outdoor
                if (
                    indoor["sum_usage"] > 1000
                    and indoor["sum_usage"] > outdoor["sum_usage"] * 10
                ):
                    add_the_row = True
            elif outdoor["sum_usage"] > 1000:
                # During winter: possible reserval if outdoor has non-trivial usage
                add_the_row = True
            if add_the_row:
                rows.append([address, indoor["sum_usage"], outdoor["sum_usage"]])
        dtypes = ["a"] * len(header)
        return title, header, rows, dtypes

    def strip_unicode_chars(self, text):
        return text.encode('ascii', 'ignore') if text else ''

    def _state_to_symbol(self, state):
        switcher = {
            "active": ".",
            "connected": ".",
            "degraded": "/",
            "disconnected": "X",
            "down": "X",
            # don't care
            "skip": " ",
        }
        return switcher.get(state, "?")

    def _fill_element_states(self, starting_date, timezone, days_history, state, state_changes):
        state_changes = state_changes if state_changes != None else []
        tz = pytz.timezone(timezone)
        starting_date = parser.parse(starting_date).astimezone(tz).replace(tzinfo=None)
        row = []
        for change in state_changes:
            change["timestamp"] = parser.parse(change["timestamp"]).astimezone(tz).replace(tzinfo=None)
        for i in range(days_history):
            day = date.today() - timedelta(days=i)
            if starting_date.date() > day:
                row += self._state_to_symbol("skip")
                continue
            next_state = state
            last_change = first_change = None
            for change in state_changes:
                change_day = change["timestamp"].date()
                if change_day == day:
                    if not last_change:
                        last_change = change
                    if not first_change:
                        first_change = change
                    if last_change and change["timestamp"] > last_change["timestamp"]:
                        last_change = change
                    if first_change and change["timestamp"] < first_change["timestamp"]:
                        first_change = change
                    next_state = first_change["from"]
                    down = ['down', 'disconnected']
                    up = ['active', 'connected']
                    if not ((state in down and next_state in down) or (state in up and next_state in up)):
                        # filter out equivalent states from the end-user perspective
                        state = "change"
            row += self._state_to_symbol(state)
            state = next_state
        return row

    def get_health_data(self):
        days_history = 7
        title = 'Premise Health'
        header = [
            'Premise ID',
            'Address',
            'Type',
            'ID',
            'State',
        ]
        self.tick('\\')
        premises = sorted(self._get_all_elements("premise"), key=lambda x : x["created_at"])
        self.tick('_')
        gateways = self._get_all_elements("gateway")
        self.tick('/')
        meters = self._get_all_elements("meter")

        rows = []
        for p in premises:
            self.tick('p')
            #  Build meter status for this prem
            for m in meters:
                if m['premise_id'] != p['id']: continue
                self.tick('m')
                row = [
                    p['id'],
                    p['street_address'],
                    "{type} meter".format(type=m["type"]),
                    m['id'],
                    m['state'],
                ]
                rows.append(row + self._fill_element_states(p["created_at"], p['timezone'], days_history, m["state"], m['seven_day_history']))

            # Build gateway status for this prem
            for g in gateways:
                if g['premise_id'] != p['id']: continue
                self.tick('g')
                row = [
                    p['id'],
                    p['street_address'],
                    "gateway",
                    g['id'],
                    g['state'],
                ]
                rows.append(row + self._fill_element_states(p["created_at"], p['timezone'], days_history, g["state"], g['seven_day_history']))

        for i in range(days_history):
            header.append((date.today() - timedelta(days=i)).strftime("%m/%d"))
        dtypes = ['t'] * len(header)
        return title, header, rows, dtypes

    def parse_args(self):
        parser = argparse.ArgumentParser(
            add_help=True,
            description="Command-line utilities to interact with Copper Cloud.",
        )
        parser.add_argument(
            "--csv-output-file",
            dest="csv_output_file",
            default=None,
            help="Write output to CSV file.",
        )
        parser.add_argument(
            "--output-dir",
            dest="output_dir",
            default=None,
            help="Write output to specified directory.",
        )
        parser.add_argument(
            "--quiet",
            dest="quiet",
            action="store_true",
            default=False,
            help="Suppress printing results to the console.",
        )
        parser.add_argument(
            "--debug",
            dest="debug",
            action="store_true",
            default=False,
            help="Enable debug output",
        )
        parser.add_argument(
            "--query-limit",
            type=int,
            dest="query_limit",
            default=None,
            help="Limit API query (for debugging purposes).",
        )
        parser.add_argument(
            "--enterprise_id",
            dest='enterprise_id',
            default=os.environ["COPPER_ENTERPRISE_ID"],
            help="Enterprise ID (filter premises belonging to enterprise)"
        )

        subparser = parser.add_subparsers()

        parser_a = subparser.add_parser("bulk")
        parser_a.add_argument(
            "--detailed",
            dest="detailed",
            action="store_true",
            default=False,
            help="Enable detailed output",
        )
        parser_a.set_defaults(func=CopperEnterpriseClient.get_bulk_data)

        parser_b = subparser.add_parser("meter")
        subparser_b = parser_b.add_subparsers()
        parser_c = subparser_b.add_parser("usage")
        parser_c.add_argument(
            "--meter-id",
            dest="meter_id",
            default=None,
            help="Select a single meter to query.",
        )
        parser_c.add_argument(
            "--granularity",
            dest="granularity",
            default="hour",
            help="Set query granularity for time-series data.",
        )
        parser_c.add_argument(
            "--timezone",
            dest="timezone",
            default=None,
            help="Force same timezone (ex: 'America/New_York') for all meters to minimize hits on Copper Cloud.",
        )
        parser_c.add_argument(
            "--step",
            type=int,
            dest="step",
            default=1,
            help="Set number of days (end - start) to request per API call.",
        )
        time_fmt = "%%Y-%%m-%%d"
        parser_c.add_argument("start", help="Query start date, formatted as: " + time_fmt)
        parser_c.add_argument("end", help="Query end date, formatted as: " + time_fmt)
        parser_c.set_defaults(func=CopperEnterpriseClient.get_meter_usage)
        parser_meter_readings = subparser_b.add_parser("readings")
        parser_meter_readings.add_argument(
            "--meter-id",
            dest="meter_id",
            default=None,
            help="Select a single meter to query.",
        )
        parser_meter_readings.add_argument(
            "--timezone",
            dest="timezone",
            default="America/Denver",
            help="Force same timezone (ex: 'America/New_York') for all meters to minimize hits on Copper Cloud.",
        )
        time_fmt = "%%Y-%%m-%%d"
        parser_meter_readings.add_argument("start", help="Query start date, formatted as: " + time_fmt)
        parser_meter_readings.add_argument("end", help="Query end date, formatted as: " + time_fmt)
        parser_meter_readings.set_defaults(func=CopperEnterpriseClient.get_meter_readings)
        parser_d = subparser_b.add_parser("check-for-water-reversals")
        parser_d.set_defaults(func=CopperEnterpriseClient.get_water_meter_reversals)
        parser_d.add_argument(
            "--check-limit",
            type=int,
            dest="check_limit",
            default=None,
            help="Limit number of homes to check (for debugging purposes).",
        )
        parser_d.add_argument(
            "--method",
            dest="method",
            default="summer",
            help="Method for checking [summer, winter]",
        )

        parser_prem = subparser.add_parser("premise")
        parser_prem.set_defaults(func=CopperEnterpriseClient.get_prem_data)

        parser_gateway = subparser.add_parser("gateway")
        parser_gateway.set_defaults(func=CopperEnterpriseClient.get_gateway_data)

        parser_grid = subparser.add_parser("grid")
        subparser_grid = parser_grid.add_subparsers()
        parser_grid_latest = subparser_grid.add_parser("latest")
        parser_grid_latest.set_defaults(func=CopperEnterpriseClient.get_grid_readings)
        parser_grid_readings = subparser_grid.add_parser("readings")
        time_fmt = "%%Y-%%m-%%d"
        parser_grid_readings.add_argument("start", help="Query start date, formatted as: " + time_fmt)
        parser_grid_readings.add_argument("end", help="Query end date, formatted as: " + time_fmt)
        parser_grid_readings.add_argument("timezone", help="Timezone (ex: 'America/Denver') for all meters to minimize hits on Copper Cloud.")
        parser_grid_readings.set_defaults(func=CopperEnterpriseClient.get_grid_readings)

        parser_health = subparser.add_parser("health")
        parser_health.set_defaults(func=CopperEnterpriseClient.get_health_data)

        self.args = parser.parse_args()


def main():
    client = CopperEnterpriseClient()
    client.run()
    print ("complete!")


if __name__ == "__main__":
    main()
