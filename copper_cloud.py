#  Copyright 2019-2021 Copper Labs, Inc.
#
#  copper_cloud.py
#
# prerequisites:
#    pip install -r requirements.txt

import json
import os
from pprint import pformat
import requests
from requests_toolbelt.utils import dump
try:
    from urllib import urlencode
except ImportError:
    from urllib.parse import urlencode


class UnauthorizedError(Exception):
    def __init__(self, error):
        Exception.__init__(self, 'error = {error}'.format(
            error=pformat(error)))
        self.error = error


class ClientError(Exception):
    def __init__(self, error):
        Exception.__init__(self, 'error = {error}'.format(
            error=pformat(error)))
        self.error = error


class CopperCloudClient():
    CACHEFILE = '.copper_cloud_cache'
    CLIENT_ID = os.environ['COPPER_CLIENT_ID']
    CLIENT_SECRET = os.environ['COPPER_CLIENT_SECRET']
    BASE_AUTH_URL = 'https://auth.copperlabs.com'
    BASE_API_URL = 'https://api.copperlabs.com'
    API_URL = '{api_host}/api/v2'.format(api_host=BASE_API_URL)

    def __init__(self, args, test_url):
        self.args = args
        self.token_data = {}
        # use cache if it exists
        if os.path.isfile(CopperCloudClient.CACHEFILE):
            if self.args.debug:
                print('Using cached token data')
            with open(CopperCloudClient.CACHEFILE, 'r') as file:
                self.token_data = json.load(file)
        else:
            if self.args.debug:
                print('Generating new token data')
            self.__get_token_data()

        # hit API endpoint, in part to make sure the access_token is valid
        try:
            self.get_helper(test_url, self.build_request_headers())
        except UnauthorizedError:
            # assume the access_token expired, automatically refresh
            self.__get_token_data()
            self.get_helper(test_url, self.build_request_headers())

    def __get_token_data(self):
        if self.args.debug:
            print('get an auth token')
        url = '{url}/oauth/token'.format(url=CopperCloudClient.BASE_AUTH_URL)
        headers = {'content-type': 'application/json'}
        data = {'grant_type': 'client_credentials',
                'client_id': CopperCloudClient.CLIENT_ID,
                'client_secret': CopperCloudClient.CLIENT_SECRET,
                'audience': CopperCloudClient.BASE_API_URL}
        self.token_data = self.post_helper(url, headers, data)
        self.__update_cache()

    def __update_cache(self):
        # cache token data for future use
        with open(CopperCloudClient.CACHEFILE, 'w') as file:
            json.dump(self.token_data, file)

    def __build_query_params(self):
        params = {}
        query_limit = getattr(self.args, 'query_limt', None)
        if query_limit:
            params['limit'] = query_limit
        postal_code = getattr(self.args, 'postal_code', None)
        if postal_code:
            params['postal_code'] = postal_code
        qstr = '?{qstr}'.format(
            qstr=urlencode(params)) if len(params.keys()) else ''
        return qstr

    def build_request_headers(self):
        return {'content-type': 'application/json',
                'Authorization': '{token_type} {access_token}'.format(
                    token_type=self.token_data['token_type'],
                    access_token=self.token_data['access_token'])}

    def get_helper(self, url, headers):
        try:
            r = requests.get(url, headers=headers)
            self.__handle_response(r)
        except ClientError as err:
            raise err
        except Exception as err:
            if err == UnauthorizedError:
                self.__get_token_data()
            r = requests.get(url, headers=headers)
            self.__handle_response(r)
        return r.json()
    
    def __handle_response(self, r):
        if self.args.debug:
            print(dump.dump_all(r).decode('utf-8') + '\n\n')
        if r.status_code != 200:
            if r.status_code == 401 or r.status_code == 403:
                raise UnauthorizedError(r)
            elif r.status_code == 400:
                raise ClientError(r)
            else:
                raise Exception(r)

    def post_helper(self, url, headers, data):
        try:
            r = requests.post(url, headers=headers, json=data)
            self.__handle_response(r)
        except Exception as err:
            if err == UnauthorizedError:
                self.__get_token_data()
            else:
                print(err)
            r = requests.post(url, headers=headers, json=data)
            self.__handle_response(r)
        return r.json()
