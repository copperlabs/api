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
from dateutil.relativedelta import relativedelta
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
    DATETIME_FMT = "%Y-%m-%dT%H:%M:%SZ"
    DATE_FMT = "%Y-%m-%d"
    HELP_DATE_FMT = "%%Y-%%m-%%d"
    METER_TYPE_UOM = {
        "power":         "kwh",
        "power_net":     "kwh",
        "power_gen":     "kwh",
        "power_sub":     "kwh",
        "gas":           "ccf",
        "water":         "gal",
        "water_indoor":  "gal",
        "water_outdoor": "gal",
    }

    def __init__(self):
        self.parse_args()
        # Walk through user login (authorization, access_token grant, etc.)
        self.cloud_client = CopperCloudClient(self.args, self._make_next_url("bulk", limit=1))

    def create_and_print_table(self, title, header, rows, dtypes):
        table = Texttable(max_width=0)
        table.set_deco(Texttable.HEADER)
        table.set_cols_dtype(dtypes)
        row_align = ["l"] * len(header)
        row_align[-1] = "r"
        table.set_header_align(row_align)
        table.set_cols_align(row_align)
        table.add_rows(rows)
        print("\n{title} (rows={num}):".format(title=title, num=len(rows) - 1))
        print (table.draw() + "\n")

    def run(self):
        if self.args.output_dir and not os.path.exists(self.args.output_dir):
            os.makedirs(self.args.output_dir) 
        output_file = None
        if self.args.csv_output_file:
            output_file = self.args.csv_output_file
            if self.args.output_dir:
                output_file = os.path.join(self.args.output_dir, output_file)
            dirname = os.path.dirname(output_file)
            if dirname and not os.path.exists(dirname):
                os.makedirs(dirname) 

        title, header, rows, dtypes = self.args.func(self)
        rows.insert(0, header)

        if not self.args.quiet:
            self.create_and_print_table(title, header, rows, dtypes)

        if output_file:
            self.write_csvfile(output_file, rows, mode="w")

    def _make_next_url(self, endpoint, limit=1000):
        return "{url}/partner/{id}/{endpoint}?limit={limit}".format(
            url=CopperCloudClient.API_URL,
            id=self.args.enterprise_id,
            endpoint=endpoint,
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

    def _get_all_elements_next(self, endpoint):
        headers = self.cloud_client.build_request_headers()
        elements = []
        more_elements = True
        next_url = self._make_next_url(endpoint)
        try:
            while more_elements:
                resp = self.cloud_client.get_helper(next_url, headers)
                elements += resp["results"]
                more_elements = resp.get("next", None)
                if more_elements:
                    next_url = "{url}{uri}".format(
                        url=CopperCloudClient.BASE_API_URL, uri=resp["next"]
                    )
        except Exception as err:
            print ("\nGET error:\n" + pformat(err))
        return elements

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

    def _get_meter_usage(self, meter_id, start, end, granularity, meter_created_at=None, step=1, timezone=None):
        headers = self.cloud_client.build_request_headers()
        timezone = getattr(self.args, "timezone", timezone)
        if timezone:
            location = {"timezone": timezone}
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
        utc_start = datetime.combine(start, time()) - timedelta(hours=offset)
        utc_end = datetime.combine(end, time()) - timedelta(hours=offset)
        usage = None
        meter_created = parser.parse(meter_created_at).astimezone(tz).replace(tzinfo=None) if meter_created_at else None
        if meter_created and utc_start < meter_created:
            start = meter_created
        for d in self._daterange(start, end, step):
            self.tick()
            istart = datetime.combine(d, time()) - timedelta(hours=offset)
            iend = istart + timedelta(days=step)
            if iend > utc_end:
                iend = utc_end
            if meter_created and iend < meter_created:
                if self.args.debug:
                    print("skipping meter {} which does not exist on {}".format(meter_id, d))
                continue
            url = "{url}/partner/{eid}/meter/{mid}/usage?{qstr}".format(
                url=CopperCloudClient.API_URL,
                eid=self.args.enterprise_id,
                mid=meter_id,
                qstr=urlencode(
                    {
                        "granularity": granularity,
                        "start": istart.strftime(CopperEnterpriseClient.DATETIME_FMT),
                        "end": iend.strftime(CopperEnterpriseClient.DATETIME_FMT),
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
                    if (len(data["results"]) and
                        d != end and
                        usage["results"][-1]["time"] == data["results"][0]["time"]):
                        del usage["results"][-1]
                    usage["results"] += data["results"]

            except Exception as err:
                print("GET ERROR: {}".format(pformat(err)))
        return usage

    def _get_meter_readings(self, meter_id, start, end, granularity, meter_created_at=None):
        headers = self.cloud_client.build_request_headers()
        if getattr(self.args, "timezone", None):
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
                    print("skipping meter {} which does not exist on {}".format(meter_id, d))
                continue
            url = "{url}/partner/{eid}/meter/{mid}/readings?{qstr}".format(
                url=CopperCloudClient.API_URL,
                eid=self.args.enterprise_id,
                mid=meter_id,
                qstr=urlencode({
                    "start": istart.strftime(CopperEnterpriseClient.DATETIME_FMT),
                    "end": iend.strftime(CopperEnterpriseClient.DATETIME_FMT),
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
                print("GET ERROR: {}".format(pformat(err)))
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
        bulk_meters = self._get_all_elements_next("bulk")
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
        query_params = {}
        if self.args.with_users:
            query_params["with_users"] = True
        url =  "{url}/partner/{id}/premise{qstr}".format(
            url=CopperCloudClient.API_URL,
            id=self.args.enterprise_id,
            qstr="?{}".format(urlencode(query_params)) if len(list(query_params)) else ""
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
            emails = ";".join([u["email"] for u in p.get("user_list", [])]) 
            rows.append([
                p["id"],
                p["created_at"],
                p["street_address"].encode("utf8").decode("ascii"),
                p["suite_apartment_unit"],
                p["city_town"],
                p["postal_code"],
                p["county_district"],
                p["state_region"],
                list(set(p["tags"])),
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
        if not self.args.output_dir:
            print("Must add the top-level --output-dir option when running this command")
            exit(1)
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
                    print("nothing to save for meter {}".format(meter["id"]))
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
        if not self.args.output_dir:
            print("Must add the top-level --output-dir option when running this command")
            exit(1)
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
                    print("nothing to save for meter {}".format(meter["id"]))
                continue
            results = [["ID", "Type", "Timestamp", "Actual ({})".format(meter["uom"]), "Normalized (kwh)"]]
            for result in readings["results"]:
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
        title = "Grid latest download"
        header = ["Premise ID", "Address", "City", "Postal Code", "Gateway ID", "Timestamp", "Voltage", "Frequency"]
        premises = {premise["id"]: premise for premise in self._get_all_elements("premise")}
        results = self._get_all_elements_next("grid/latest")
        rows = []

        for result in results:
            rx_utc = parser.parse(result["hw_timestamp"])
            rx_local = rx_utc.astimezone(pytz.timezone(premises[result["premise_id"]]["timezone"])).replace(tzinfo=None)
            self.tick()
            rows.append([
                premises[result["premise_id"]]["id"],
                premises[result["premise_id"]]["street_address"],
                premises[result["premise_id"]]["city_town"],
                premises[result["premise_id"]]["postal_code"].rjust(5, "0"),
                result["gateway_id"],
                rx_local,
                result["voltage"],
                result["frequency"],
            ])
        dtypes = ["t", "t", "t", "t", "t", "t", "a", "a"]
        return title, header, rows, dtypes

    def _get_grid_readings(self, start, end, timezone, premise_id=None, gateway_id=None):
        headers = self.cloud_client.build_request_headers()
        tz = pytz.timezone(timezone)
        start = parser.parse(start)
        end = parser.parse(end)
        offset = int(tz.localize(start).strftime("%z")[:-2])
        readings = []
        for d in self._daterange(start, end):
            self.tick()
            istart = datetime.combine(d, time()) - timedelta(hours=offset)
            iend = istart + timedelta(days=1)
            query_params = {
                "start": istart.strftime(CopperEnterpriseClient.DATETIME_FMT),
                "end": iend.strftime(CopperEnterpriseClient.DATETIME_FMT),
            }
            if premise_id != None:
                query_params["premise_id"] = premise_id
            if gateway_id != None:
                query_params["gateway_id"] = gateway_id
            url = "{url}/partner/{eid}/grid/readings?{qstr}".format(
                url=CopperCloudClient.API_URL,
                eid=self.args.enterprise_id,
                qstr=urlencode(query_params)
            )
            try:
                data = self.cloud_client.get_helper(url, headers)
                data = sorted(data, key=lambda x:x["hw_timestamp"])
                readings += data

            except Exception as err:
                print("GET ERROR: {}".format(pformat(err)))
                break
        return readings

    def get_grid_readings(self):
        if not self.args.output_dir:
            print("Must add the top-level --output-dir option when running this command")
            exit(1)
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
        gateway_readings = {}
        # This could be a huge amoun of data. Sort through it once at the cost of memory.
        for reading in all_gateway_readings:
            if reading["gateway_id"] not in gateway_readings.keys():
                gateway_readings[reading["gateway_id"]] = []
            gateway_readings[reading["gateway_id"]].append(reading)
            
        for gateway in gateways:
            self.tick("g")
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
            readings = gateway_readings.get(gateway["id"], [])
            if len(readings) == 0:
                if self.args.debug:
                    print("nothing to save for gateway {}".format(gateway["id"]))
                continue
            data = [["Gateway ID", "Timestamp", "Voltage", "Frequency"]]
            for reading in readings:
                rx_utc = parser.parse(reading["hw_timestamp"])
                rx_local = rx_utc.astimezone(pytz.timezone(self.args.timezone)).replace(tzinfo=None)
                data.append([
                    reading["gateway_id"],
                    rx_local,
                    reading["voltage"],
                    reading["frequency"],
                ])
            self.write_csvfile(destpath, data)
        dtypes = ["t", "t", "t", "t", "t"]
        return title, header, rows, dtypes

    def get_water_meter_reversals(self):
        midnight = datetime.combine(date.today(), time())
        start = (midnight - timedelta(days=30)).strftime(CopperEnterpriseClient.DATE_FMT)
        end = midnight.strftime(CopperEnterpriseClient.DATE_FMT)
        title = "Suspect water meter reversals"
        header = ["Address", "Indoor Usage", "Outdoor Usage"]
        headers = self.cloud_client.build_request_headers()
        meters = self._get_all_elements_next("bulk")
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
                    p["water_indoor"]["meter_id"], start, end, "day", step=30
                )
            if "water_outdoor" in p.keys():
                outdoor = self._get_meter_usage(
                    p["water_outdoor"]["meter_id"], start, end, "day", step=30
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
        return text.encode("ascii", "ignore") if text else ""

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
                    down = ["down", "disconnected"]
                    up = ["active", "connected"]
                    if not ((state in down and next_state in down) or (state in up and next_state in up)):
                        # filter out equivalent states from the end-user perspective
                        state = "change"
            row += self._state_to_symbol(state)
            state = next_state
        return row

    def get_health_data(self):
        days_history = 7
        title = "Premise Health"
        header = [
            "Premise ID",
            "Address",
            "Type",
            "ID",
            "State",
        ]
        self.tick("\\")
        premises = sorted(self._get_all_elements("premise"), key=lambda x : x["created_at"])
        self.tick("_")
        gateways = self._get_all_elements("gateway")
        self.tick("/")
        meters = self._get_all_elements("meter")

        rows = []
        for p in premises:
            self.tick("p")
            #  Build meter status for this prem
            for m in meters:
                if m["premise_id"] != p["id"]: continue
                self.tick("m")
                row = [
                    p["id"],
                    p["street_address"],
                    "{type} meter".format(type=m["type"]),
                    m["id"],
                    m["state"],
                ]
                rows.append(row + self._fill_element_states(p["created_at"], p["timezone"], days_history, m["state"], m["seven_day_history"]))

            # Build gateway status for this prem
            for g in gateways:
                if g["premise_id"] != p["id"]: continue
                self.tick("g")
                row = [
                    p["id"],
                    p["street_address"],
                    "gateway",
                    g["id"],
                    g["state"],
                ]
                rows.append(row + self._fill_element_states(p["created_at"], p["timezone"], days_history, g["state"], g["seven_day_history"]))

        for i in range(days_history):
            header.append((date.today() - timedelta(days=i)).strftime("%m/%d"))
        dtypes = ["t"] * len(header)
        return title, header, rows, dtypes

    def get_monthly_report(self):
        headers = self.cloud_client.build_request_headers()
        title = "Monthly report for {}".format(self.args.date)
        header = ["Statistic", "Value", "Units", "Note"]
        self.tick("\\")
        premises = {premise["id"]: premise for premise in sorted(self._get_all_elements("premise"), key=lambda x : x["created_at"])}
        self.tick("_")
        all_meters = self._get_all_elements("meter")
        self.tick("/")
        meter_types = list(set([meter["type"] for meter in all_meters])) if len(all_meters) else list(CopperEnterpriseClient.METER_TYPE_UOM)
        meter_types.sort()
        rows = []
        meters_by_type = {type: [] for type in meter_types}

        # Grab the monthly usage calculated in arrears for the first day of month after the desired month
        start = parser.parse(self.args.date).replace(day=1)
        end = start + relativedelta(months=1) + timedelta(days=1)

        for premise in premises.values():
            premise["meters"] = []

        # Split meters out by type for faster processing below, and drop meters that did not exist prior to the start date
        meters = []
        for meter in all_meters:
            #if meter["state"] != "connected":
            #    print("skipping disonnected meter {}".format(meter["id"]))
            #    continue
            premise = premises[meter["premise_id"]]
            tz = pytz.timezone(premise["timezone"])
            meter_created = parser.parse(meter["created_at"]).astimezone(tz).replace(tzinfo=None)
            premise_created = parser.parse(meter["premise_created_at"]).astimezone(tz).replace(tzinfo=None)
            if end < meter_created or end < premise_created:
                if self.args.debug:
                    print("skipping meter {} which did not exist prior to {}".format(meter["id"], end))
                continue
            meters.append(meter)
            meters_by_type[meter["type"]].append(meter)
            premise["meters"].append(meter)

        # Drop premises that did not exist prior to the start date. Can't combine with previous step
        # since there may be multiple meters for the same prem needing to look up timezone
        timezone = None
        istart = None
        iend = None
        for pid in list(premises):
            premise = premises[pid]
            tz = pytz.timezone(premise["timezone"])
            if not timezone:
                timezone = premise["timezone"]
                offset = int(tz.localize(start).strftime("%z")[:-2])
                istart = datetime.combine(start, time()) - timedelta(hours=offset)
                iend = (istart + relativedelta(months=1) + timedelta(days=1)).strftime(CopperEnterpriseClient.DATETIME_FMT)
                istart = istart.strftime(CopperEnterpriseClient.DATETIME_FMT)
            tz = pytz.timezone(premise["timezone"])
            premise_created = parser.parse(premise["created_at"]).astimezone(tz).replace(tzinfo=None)
            if end < premise_created:
                if self.args.debug:
                    print("dropping premise {} which did not exist prior to {}".format(premise["id"], end))
                if len(premise["meters"]):
                    raise Exception("ERROR: premise {} still contains meters {}".format(premise["id"], pformat(premise["meters"])))
                del premises[pid]

        rows.append(["total homes", len(premises), "", "1"])
        rows.append(["total meters", len(meters), "", "1"])

        reporting_meters = 0
        for meter_type in meter_types:
            rows.append(["{} meters".format(meter_type), len([meter for meter in meters if meter["type"] == meter_type]), "", "1"])
            if self.args.include_sum:
                print("\n{}".format(meter_type))
                sum_usage = 0
                for meter in meters_by_type[meter_type]:
                    usage = self._get_meter_usage(
                        meter["id"],
                        start.strftime(CopperEnterpriseClient.DATE_FMT),
                        end.strftime(CopperEnterpriseClient.DATE_FMT),
                        "month",
                        step=45,
                        timezone=premises[meter["premise_id"]]["timezone"]
                    )
                    sum_usage += usage.get("sum_usage", 0) if usage else 0
                rows.append(["{} cumulative per-meter usage".format(meter_type), round(sum_usage, 2), CopperEnterpriseClient.METER_TYPE_UOM[meter_type], "2"])
            url = "{url}/partner/{eid}/aggregate/usage?{qstr}".format(
                url=CopperCloudClient.API_URL,
                eid=self.args.enterprise_id,
                qstr=urlencode(
                    {
                        "granularity": "month",
                        "start": istart,
                        "end": iend,
                        "meter_type": meter_type,
                    }
                ),
            )
            try:
                self.tick()
                response = self.cloud_client.get_helper(url, headers)
            except Exception as err:
                # assume there were no meters found for this type
                response = {"meter_count": 0, "sum_energy": 0}
            sum_usage = response["sum_energy"] if response["sum_energy"] else 0
            reporting_meters += response["meter_count"] if response["meter_count"] else 0
            if response["meter_count"]:
                #rows.append(["{} meters reporting".format(meter_type), response["meter_count"], "", "3"])
                rows.append(["{} aggregate usage".format(meter_type), round(sum_usage, 2), CopperEnterpriseClient.METER_TYPE_UOM[meter_type], "4"])

        #rows.append(["total reporting meters", reporting_meters, "", "3"])

        legend_header = ["Note", "Description"]
        legend_rows = [
            legend_header,
            ["1", "Number of elements in existence during the report window"],
            ["2", "Sum of individual meter usages during the report window"],
            ["3", "Number of currently-connected meters contributing to the aggregate usage"],
            ["4", "Aggregate usage of currently-connected meters during the report window"],
        ]
        if not self.args.quiet:
            self.create_and_print_table("\nLegend", legend_header, legend_rows, ["t"] * len(legend_header))
        if self.args.csv_output_file:
            output_file = os.path.join(self.args.output_dir, "readme.txt")
            self.write_csvfile(output_file, legend_rows, mode="w")

        dtypes = ["t"] * len(header)
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
            dest="enterprise_id",
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
        parser_c.add_argument("start", help="Query start date, formatted as: " + CopperEnterpriseClient.HELP_DATE_FMT)
        parser_c.add_argument("end", help="Query end date, formatted as: " + CopperEnterpriseClient.HELP_DATE_FMT)
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
        parser_meter_readings.add_argument("start", help="Query start date, formatted as: " + CopperEnterpriseClient.HELP_DATE_FMT)
        parser_meter_readings.add_argument("end", help="Query end date, formatted as: " + CopperEnterpriseClient.HELP_DATE_FMT)
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
        parser_prem .add_argument(
            "--with-users",
            dest="with_users",
            action="store_true",
            default=False,
            help="Include user emails in report",
        )
        parser_prem.set_defaults(func=CopperEnterpriseClient.get_prem_data)

        parser_gateway = subparser.add_parser("gateway")
        parser_gateway.set_defaults(func=CopperEnterpriseClient.get_gateway_data)

        parser_grid = subparser.add_parser("grid")
        subparser_grid = parser_grid.add_subparsers()
        parser_grid_latest = subparser_grid.add_parser("latest")
        parser_grid_latest.set_defaults(func=CopperEnterpriseClient.get_grid_latest)
        parser_grid_readings = subparser_grid.add_parser("readings")
        parser_grid_readings.add_argument("start", help="Query start date, formatted as: " + CopperEnterpriseClient.HELP_DATE_FMT)
        parser_grid_readings.add_argument("end", help="Query end date, formatted as: " + CopperEnterpriseClient.HELP_DATE_FMT)
        parser_grid_readings.add_argument("timezone", help="Timezone (ex: 'America/Denver') for all meters to minimize hits on Copper Cloud.")
        parser_grid_readings.set_defaults(func=CopperEnterpriseClient.get_grid_readings)

        parser_report = subparser.add_parser("report")
        subparser_report = parser_report.add_subparsers()

        parser_health = subparser_report.add_parser("health")
        parser_health.set_defaults(func=CopperEnterpriseClient.get_health_data)

        parser_monthly = subparser_report.add_parser("monthly")
        parser_monthly.add_argument("date", help="Query date, formatted as: " + CopperEnterpriseClient.HELP_DATE_FMT)
        parser_monthly.add_argument(
            "--include-per-meter-sum",
            dest="include_sum",
            action="store_true",
            default=False,
            help="Include cumulative per-meter usage query in addition to the aggregate query. Warning, this may take a LONG time and exhaust the API rate limit",
        )
        parser_monthly.set_defaults(func=CopperEnterpriseClient.get_monthly_report)

        self.args = parser.parse_args()


def main():
    client = CopperEnterpriseClient()
    client.run()
    print ("complete!")


if __name__ == "__main__":
    main()
