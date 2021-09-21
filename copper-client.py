#  Copyright 2018-2019 Copper Labs, Inc.
#
#  copper-client.py
#
# prerequisites:
#    pip install -r requirements.txt

import argparse
from base64 import urlsafe_b64encode
import copy
import csv
from datetime import datetime, timedelta
from dateutil import parser, tz
from hashlib import sha256
import json
import os
from pprint import pformat
import requests
from requests_toolbelt.utils import dump
from texttable import Texttable
try:
    from urllib.parse import urlencode #python 3
except Exception:
    from urllib import urlencode #python 2
import webbrowser
if hasattr(__builtins__, 'raw_input'):
    input = raw_input


class UnauthorizedError(Exception):
    def __init__(self, error):
        Exception.__init__(self, 'error = {error}'.format(
            error=pformat(error)))
        self.error = error


class CopperClient():
    CACHEFILE = '.cache'
    CLIENT_ID = 'RvXeGVUtzcz9iWnP4QJFwnVwCHVUoMIA'
    BASE_AUTH_URL = 'https://auth.copperlabs.com'
    BASE_API_URL = 'https://api.copperlabs.com'
    AUDIENCE_URL = 'https://api.copperlabs.com'
    API_URL = '{url}/api/v2/app'.format(url=BASE_API_URL)

    def __init__(self, args):
        self.app = {}
        self.args = args
        self.code_verifier = urlsafe_b64encode(os.urandom(32)).rstrip(b'=')
        m = sha256()
        m.update(self.code_verifier)
        self.code_challenge = urlsafe_b64encode(m.digest()).rstrip(b'=')
        self.token_data = {}
        # use cache if it exists
        if os.path.isfile(CopperClient.CACHEFILE):
            if self.args.debug:
                print('Using cached token data')
            with open(CopperClient.CACHEFILE, 'r') as file:
                self.token_data = json.load(file)
        else:
            if self.args.debug:
                print('Generating new token data')
            auth_code = self.__authorize()
            self.__get_token_data_from_auth_code(auth_code)
        # attempt to fetch app state, use this to test access_token and
        # refresh if possible
        try:
            self.__get_app_state()
        except Exception:
            # assume the access_token expired, automatically refresh
            self.__get_token_data_from_refresh_token()
            self.__get_app_state()
        self.__update_cache()

    def __authorize(self):
        # obtain an authorization code
        url = '{url}/authorize'.format(url=CopperClient.BASE_AUTH_URL)
        params = {'response_type': 'code',
                  'code_challenge': self.code_challenge,
                  'code_challenge_method': 'S256',
                  'client_id': CopperClient.CLIENT_ID,
                  'scope': 'app offline_access',
                  'audience': CopperClient.AUDIENCE_URL,
                  'redirect_uri': CopperClient.API_URL}
        qstr = urlencode(params)
        webbrowser.open_new_tab('{url}/?{qstr}'.format(url=url, qstr=qstr))

        print ('')
        print ('Opening a web brower to complete passwordless login with Copper Labs...')
        print ('')
        print ('Upon successful login, the URL in your browser will contain a code.')
        print ('Example, {url}?code=bk1AEJKK0NUYh-XI'.format(
            url=CopperClient.API_URL))
        print ('')
        print ('Copy the text following "code=" and enter it here:')
        auth_code = str(input())
        return auth_code

    def __get_token_data_from_auth_code(self, auth_code):
        if self.args.debug:
            print('trade the auth code for an auth token')
        url = '{url}/oauth/token'.format(url=CopperClient.BASE_AUTH_URL)
        headers = {'content-type': 'application/json'}
        data = {'grant_type': 'authorization_code',
                'code_verifier': self.code_verifier.decode(),
                'client_id': CopperClient.CLIENT_ID,
                'code': auth_code,
                'redirect_uri': CopperClient.API_URL}
        self.token_data = self.post_helper(url, headers, data)

    def __get_token_data_from_refresh_token(self):
        if self.args.debug:
            print('trade the refresh token for an auth token')
        url = '{url}/oauth/token'.format(url=CopperClient.BASE_AUTH_URL)
        headers = {'content-type': 'application/json'}
        data = {'grant_type': 'refresh_token',
                'client_id': CopperClient.CLIENT_ID,
                'refresh_token': self.token_data['refresh_token']}
        # response will not contain a new refresh_token, so only update
        # the access_token
        token_data = self.post_helper(url, headers, data)
        self.token_data['access_token'] = token_data['access_token']

    def __update_cache(self):
        # cache token data for future use
        with open(CopperClient.CACHEFILE, 'w') as file:
            json.dump(self.token_data, file)

    def __get_app_state(self):
        # ask for app data
        url = '{url}/state'.format(url=CopperClient.API_URL)
        headers = {'content-type': 'application/json',
                   'Authorization': '{token_type} {access_token}'.format(
                       token_type=self.token_data['token_type'],
                       access_token=self.token_data['access_token'])}
        self.app = self.get_helper(url, headers)

    def get_helper(self, url, headers):
        r = requests.get(url, headers=headers)
        if self.args.debug:
            print(dump.dump_all(r).decode('utf-8') + '\n\n')
        if r.status_code != 200:
            if r.status_code == 401 or r.status_code == 403:
                raise UnauthorizedError(r)
            else:
                raise Exception(r)
        return r.json()

    def post_helper(self, url, headers, data):
        r = requests.post(url, headers=headers, json=data)
        if self.args.debug:
            print(dump.dump_all(r).decode('utf-8') + '\n\n')
        if r.status_code != 200:
            raise Exception(r)
        return r.json()

    def print_usage_data(self):
        today = datetime.now(tz.tzlocal()).replace(
            hour=0, minute=0, second=0, microsecond=0)
        start = (today - timedelta(1)).astimezone(tz.tzutc()).strftime(
            "%Y-%m-%dT%H:%M:%SZ")
        end = (today - timedelta(0)).astimezone(tz.tzutc()).strftime(
            "%Y-%m-%dT%H:%M:%SZ")
        headers = {'content-type': 'application/json',
                   'Authorization': '{token_type} {access_token}'.format(
                       token_type=self.token_data['token_type'],
                       access_token=self.token_data['access_token'])}

        table = Texttable(max_width=0)
        print('Summary Table as of {time}:'.format(time=datetime.now()))
        table.header([
            'Premise Name', 'Meter ID', 'Meter Type', 'Current Value',
            'Time Received'])

        for premise in self.app['premise_list']:
            # ask for premise data
            url = '{url}/instant/{id}'.format(
                url=CopperClient.API_URL, id=premise['id'])
            p = self.get_helper(url, headers)
            for meter in p['results']:
                table.add_row([
                    premise['name'],
                    meter['id'],
                    meter['type'],
                    meter['instant_power'],
                    meter['updated_at']])

        print(table.draw() + '\n')


def main():
    parser = argparse.ArgumentParser(
        description='Raw data download from Copper Labs.')
    parser.add_argument('--debug', dest='debug', action='store_true',
                        default=False, help='Enable debug output')
    args = parser.parse_args()

    # Walk through user login (authorization, access_token grant, etc.)
    c = CopperClient(args)

    c.print_usage_data()

    print('complete!')


if __name__ == "__main__":
    main()
