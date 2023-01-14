#! /usr/bin/env python
# -*- coding: utf-8 -*-
####################

import json
import logging
import requests

API_LOGIN = "https://fireboard.io/api/rest-auth/login/"
API_BASE = "https://fireboard.io/api/v1/"


################################################################################
class FireBoard(object):

    def __init__(self, username=None, password=None):
        self.logger = logging.getLogger("Plugin.FireBoard")
        self.auth_headers = None

        if username is None or password is None:
            self.logger.error("fbLogin failure, Username or Password not set")
            self.loginKey = None
            return

        headers = {'Content-Type': 'application/json'}
        payload = {'username': username, 'password': password}
        try:
            response = requests.post(API_LOGIN, json=payload, headers=headers)
        except requests.exceptions.RequestException as err:
            self.logger.error(f"fbLogin failure, request url: {url}, RequestException: {err}")
            return

        if response.status_code != requests.codes.ok:
            self.logger.error(f"fbLogin failure, status_code = {response.status_code}")
            self.loginKey = None
            return

        try:
            auth_key = response.json()['key']
        except (Exception,):
            self.logger.error("fbLogin failure, json decode failure")
            return
        else:
            self.auth_headers = {"Content-Type": "application/json", 'Authorization': "Token " + auth_key}

    ########################################
    # Commands to FireBoard cloud
    ########################################

    def get_devices(self):
        url = f"{API_BASE}/{'devices.json'}"
        try:
            resp = requests.get(url, headers=self.auth_headers)
            resp.raise_for_status()
        except TimeoutError as err:
            self.logger.warning(f"fbGetDevices timeout error, request url: {url}, Error: {err}")
            return None
        except (Exception,):
            raise
        return resp.json()

    def get_device(self, device_id):
        url = f"{API_BASE}/devices/{device_id}.json"
        try:
            resp = requests.get(url, headers=self.token_header)
            resp.raise_for_status()
        except TimeoutError as err:
            self.logger.warning(f"fbGetDevices timeout error, request url: {url}, Error: {err}")
            return None
        except (Exception,):
            raise
        return resp.json()

    def get_device_temps(self, device_id):
        url = f"{API_BASE}/devices/{device_id}/temps.json"
        try:
            resp = requests.get(url, headers=self.token_header)
            resp.raise_for_status()
        except TimeoutError as err:
            self.logger.warning(f"fbGetDevices timeout error, request url: {url}, Error: {err}")
            return None
        except (Exception,):
            raise
        return resp.json()

    def get_device_drivelog(self, device_id):
        url = f"{API_BASE}/devices/{device_id}/drivelog.json"
        try:
            resp = requests.get(url, headers=self.token_header)
            resp.raise_for_status()
        except TimeoutError as err:
            self.logger.warning(f"fbGetDevices timeout error, request url: {url}, Error: {err}")
            return None
        except (Exception,):
            raise
        return resp.json()

    def get_sessions(self):
        url = f"{API_BASE}/sessions.json"
        try:
            resp = requests.get(url, headers=self.auth_headers)
            resp.raise_for_status()
        except TimeoutError as err:
            self.logger.warning(f"fbGetDevices timeout error, request url: {url}, Error: {err}")
            return None
        except (Exception,):
            raise
        return resp.json()

    def get_session(self, session_id):
        url = f"{API_BASE}/sessions/{session_id}.json"
        try:
            resp = requests.get(url, headers=self.auth_headers)
            resp.raise_for_status()
        except TimeoutError as err:
            self.logger.warning(f"fbGetDevices timeout error, request url: {url}, Error: {err}")
            return None
        except (Exception,):
            raise
        return resp.json()

    def get_session_chart(self, session_id):
        url = f"{API_BASE}/sessions/{session_id}/chart.json"
        try:
            resp = requests.get(url, headers=self.auth_headers)
            resp.raise_for_status()
        except TimeoutError as err:
            self.logger.warning(f"fbGetDevices timeout error, request url: {url}, Error: {err}")
            return None
        except (Exception,):
            raise
        return resp.json()
