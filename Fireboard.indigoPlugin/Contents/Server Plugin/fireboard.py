#! /usr/bin/env python
# -*- coding: utf-8 -*-
####################

import json
import logging
import requests

API_LOGIN = "https://fireboard.io/api/rest-auth/login/"
API_BASE  = "https://fireboard.io/api/v1/"
        
################################################################################

class FireBoard(object):

    def __init__(self, username=None, password=None):
        self.logger = logging.getLogger("Plugin.FireBoard")   
        self.auth_headers = None      
        
        self.logger.debug(u"FireBoard __init__ username = {}, password = {}".format(username, password))
        
        if username == None or password == None:
            self.logger.error(u"fbLogin failure, Username or Password not set")
            self.loginKey = None
            return None

        headers = { 'Content-Type': 'application/json' }
        payload = { 'username': username, 'password': password}
        try:
            response = requests.post(API_LOGIN, json=payload, headers=headers)            
        except requests.exceptions.RequestException as err:
            self.logger.error(u"fbLogin failure, request url: {}, RequestException: {}".format(url, err))
            return None

        if (response.status_code != requests.codes.ok):
            self.logger.error(u"fbLogin failure, status_code = {}".format(response.status_code))
            self.loginKey = None
            return None        

        try:
            auth_key = response.json()['key']
        except:
            self.logger.error(u"fbLogin failure, json decode failure")
            return None
        else:
            self.auth_headers = { "Content-Type": "application/json", 'Authorization': "Token " + auth_key }
                    

    ########################################
    # Commands to FireBoard cloud
    ########################################
    
    def get_devices(self):
        self.logger.debug(u"get_devices()")
            
        url = "{}/{}".format(API_BASE, 'devices.json')
        try:
            resp = requests.get(url, headers=self.auth_headers)
            resp.raise_for_status()
        except:
            raise
        self.logger.threaddebug(u"get_devices: {}".format(resp.json()))
        return resp.json()


    def get_device(self, device_id):
        self.logger.debug(u"get_device({})".format(device_id))
        
        url = "{}/{}".format(API_BASE, 'devices/{}.json'.format(device_id))
        try:
            resp = requests.get(url, headers=self.token_header)
            resp.raise_for_status()
        except:
            raise
        self.logger.threaddebug(u"get_device: {}".format(resp.json()))
        return resp.json()


    def get_device_temps(self, device_id):
        self.logger.debug(u"get_device_temps({})".format(device_id))
        
        url = "{}/{}".format(API_BASE, 'devices/{}/temps.json'.format(device_id))
        try:
            resp = requests.get(url, headers=self.token_header)
            resp.raise_for_status()
        except:
            raise
        self.logger.threaddebug(u"get_device_temps: {}".format(resp.json()))
        return resp.json()


    def get_device_drivelog(self, device_id):
        self.logger.debug(u"get_device_drivelog({})".format(device_id))
        
        url = "{}/{}".format(API_BASE, 'devices/{}/drivelog.json'.format(device_id))
        try:
            resp = requests.get(url, headers=self.token_header)
            resp.raise_for_status()
        except:
            raise
        self.logger.threaddebug(u"get_device_drivelog: {}".format(resp.json()))
        return resp.json()


    def get_sessions(self):
        self.logger.debug(u"get_sessions()")
            
        url = "{}/{}".format(API_BASE, 'sessions.json')
        try:
            resp = requests.get(url, headers=self.auth_headers)
            resp.raise_for_status()
        except:
            raise
        self.logger.threaddebug(u"get_sessions: {}".format(resp.json()))
        return resp.json()


    def get_session(self, session_id):
        self.logger.debug(u"get_session({})".format(session_id))
            
        url = "{}/{}".format(API_BASE, 'sessions/{}.json'.format(session_id))
        try:
            resp = requests.get(url, headers=self.auth_headers)
            resp.raise_for_status()
        except:
            raise
        self.logger.threaddebug(u"get_session: {}".format(resp.json()))
        return resp.json()


    def get_session_chart(self, session_id):
        self.logger.debug(u"get_session({})".format(session_id))
            
        url = "{}/{}".format(API_BASE, 'sessions/{}/chart.json'.format(session_id))
        try:
            resp = requests.get(url, headers=self.auth_headers)
            resp.raise_for_status()
        except:
            raise
        self.logger.threaddebug(u"get_session_chart: {}".format(resp.json()))
        return resp.json()


