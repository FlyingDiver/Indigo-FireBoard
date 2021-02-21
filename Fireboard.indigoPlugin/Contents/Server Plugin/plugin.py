#! /usr/bin/env python
# -*- coding: utf-8 -*-
####################

import time
import requests
import logging
import json
from fireboard import FireBoard 

API_LOGIN = "https://fireboard.io/api/rest-auth/login/"
API_BASE  = "https://fireboard.io/api/v1/"

################################################################################
class Plugin(indigo.PluginBase):

    ########################################
    # Main Plugin methods
    ########################################
    def __init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs):
        indigo.PluginBase.__init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs)

        pfmt = logging.Formatter('%(asctime)s.%(msecs)03d\t[%(levelname)8s] %(name)20s.%(funcName)-25s%(msg)s', datefmt='%Y-%m-%d %H:%M:%S')
        self.plugin_file_handler.setFormatter(pfmt)

        try:
            self.logLevel = int(self.pluginPrefs[u"logLevel"])
        except:
            self.logLevel = logging.INFO
        self.indigo_log_handler.setLevel(self.logLevel)
    

    def startup(self):
        indigo.server.log(u"Starting FireBoard")

        self.fb_devices = {}     # Indigo device IDs, keyed by address (hardware_id)
        self.fb_channels = {}    # Indigo device IDs, keyed by uuid-channel string
        self.knownDevices = {}
        
        self.updateFrequency = float(self.pluginPrefs.get('updateFrequency', "1")) * 60.0
        self.logger.debug(u"updateFrequency = {}".format(self.updateFrequency))
        self.next_update = time.time()

        self.fb_account = FireBoard(username=self.pluginPrefs['FireBoardLogin'], password=self.pluginPrefs['FireBoardPassword'])
        for device in self.fb_account.get_devices():
            self.knownDevices[device['hardware_id']] = device
        self.logger.debug(u"knownDevices:\n{}".format(json.dumps(self.knownDevices, indent=4, separators=(',', ': '))))
            

    def shutdown(self):
        indigo.server.log(u"Shutting down FireBoard")


    def runConcurrentThread(self):

        try:
            while True:

                if time.time() > self.next_update:
#                    self.getTemperatures()
                    self.next_update = time.time() + self.updateFrequency

                self.sleep(1.0)

        except self.StopThread:
            pass

    def deviceStartComm(self, device):
        
        if device.deviceTypeId == 'fireboardDevice':
            self.logger.debug(u"{}: deviceStartComm: Adding device ({}) to Device list".format(device.name, device.id))
            self.fb_devices[device.address] = device.id
            self.logger.threaddebug(u"fb_devices = {}".format(self.fb_devices))

            fbDevice = self.knownDevices[device.address]
            states_list = []
            states_list.append({'key': 'name',         'value': fbDevice['title']})
            states_list.append({'key': 'model',         'value': fbDevice['model']})
            states_list.append({'key': 'created',       'value': fbDevice['created']})
            states_list.append({'key': 'channel_count', 'value': fbDevice['channel_count']})
            states_list.append({'key': 'degreetype',    'value': fbDevice['degreetype']})
            states_list.append({'key': 'last_templog',  'value': fbDevice['last_templog']})
            states_list.append({'key': 'probe_config',  'value': fbDevice['probe_config']})
            states_list.append({'key': 'hardware_id',   'value': fbDevice['hardware_id']})
            states_list.append({'key': 'version',       'value': fbDevice['version']})
            states_list.append({'key': 'fbj_version',   'value': fbDevice['fbj_version']})
            states_list.append({'key': 'fbn_version',   'value': fbDevice['fbn_version']})
            states_list.append({'key': 'fbu_version',   'value': fbDevice['fbu_version']})                    
            device.updateStatesOnServer(states_list)
            
        
        elif device.deviceTypeId == 'fireboardChannel':
            self.logger.debug(u"{}: deviceStartComm: Adding device ({}) to Channel list".format(device.name, device.id))
            self.fb_channels[device.address] = device.id
            self.logger.threaddebug(u"fb_channels = {}".format(self.fb_channels))
            
            fbDevice = self.knownDevices[device.pluginProps['device']]
            for channel in fbDevice['channels']:
                self.logger.debug(u"getDevices: channel = {}".format(channel))
                states_list = []
                if channel.get('last_templog', None):
                    if channel['last_templog']['degreetype'] == 1:
                        scale = 'C'
                    elif  channel['last_templog'][u'degreetype'] == 2:
                        scale = 'F'
                    last_temp = channel['last_templog']['temp']
                    states_list.append({'key': 'sensorValue',   'value': last_temp, 'decimalPlaces': 1, 'uiValue': u'{:.1f} °{}'.format(last_temp, scale)})
                else:
                    states_list.append({'key': 'sensorValue',   'value': 0.0, 'decimalPlaces': 1, 'uiValue': u'0.0'})
                
                states_list.append({'key': 'id',            'value': channel['id']})
                states_list.append({'key': 'channel',       'value': channel['channel']})
                states_list.append({'key': 'channel_label', 'value': channel['channel_label']})
                states_list.append({'key': 'created',       'value': channel['created']})
                states_list.append({'key': 'enabled',       'value': channel['enabled']})
                device.updateStatesOnServer(states_list)

        
    def deviceStopComm(self, device):

        if device.deviceTypeId == 'fireboard':
            self.logger.debug(u"{}: deviceStopComm: Removing device ({}) from FireBoard list".format(device.name, device.id))
            del self.fb_devices[device.address]
        elif device.deviceTypeId == 'fireboardChannel':
            self.logger.debug(u"{}: deviceStopComm: Removing device ({}) from Channel list".format(device.name, device.id))
            del self.fb_channels[device.address]
            

    def getDeviceConfigUiValues(self, pluginProps, typeId, devId):
        self.logger.debug(u"getDeviceConfigUiValues, typeId = {}, devId = {}, pluginProps = {}".format(typeId, devId, pluginProps))
        valuesDict = pluginProps
        errorMsgDict = indigo.Dict()

        if not valuesDict.get('device', None) and len(self.knownDevices):
            valuesDict['device'] = self.knownDevices.keys()[0]
            self.logger.debug(u"getDeviceConfigUiValues, valuesDict = {}".format(valuesDict))
                        
        return (valuesDict, errorMsgDict)
             

    ########################################
    # Menu Methods
    ########################################

    def menuDumpData(self):
        self.logger.info(u"menuDumpData Devices:\n{}".format(json.dumps(self.device_info, indent=4, separators=(',', ': '))))
        return True
        
    def get_device_list(self, filter="", valuesDict=None, typeId="", targetId=0):
        self.logger.debug("get_device_list: typeId = {}, targetId = {}, filter = {}, valuesDict = {}".format(typeId, targetId, filter, valuesDict))
        retList = []
        for fb in self.knownDevices.values():
            retList.append((fb['hardware_id'], fb['title']))
        retList.sort(key=lambda tup: tup[1])
        return retList
    
    def get_channel_list(self, filter="", valuesDict=None, typeId="", targetId=0):
        self.logger.debug("get_channel_list: typeId = {}, targetId = {}, filter = {}, valuesDict = {}".format(typeId, targetId, filter, valuesDict))
        retList = []
        if not valuesDict.get('device', None):
            return retList
        fb = self.knownDevices[valuesDict['device']]
        for ch in fb['channels']:
            retList.append((ch['id'], ch['channel_label']))
        retList.sort(key=lambda tup: tup[1])
        return retList
    
    # doesn't do anything, just needed to force other menus to dynamically refresh
    def menuChanged(self, valuesDict = None, typeId = None, devId = None):
        self.logger.threaddebug("menuChanged: devId = {}, typeId = {}, valuesDict = {}".format(devId, typeId, valuesDict))
        return valuesDict


    def availableDeviceList(self, filter="", valuesDict=None, typeId="", targetId=0):

        in_use =[]
        for dev in indigo.devices.iter(filter="self.fireboard"):
            in_use.append(dev.address)

        retList =[]
        for FireBoardID, FireBoardName in self.knownDevices.iteritems():
            if FireBoardID not in in_use:
                retList.append((FireBoardID, FireBoardName))

        if targetId:
            try:
                dev = indigo.devices[targetId]
                retList.insert(0, (dev.pluginProps["address"], self.knownDevices[dev.pluginProps["address"]]))
            except:
                pass

        self.logger.debug(u"availableDeviceList: retList = {}".format(retList))
        return retList


    ########################################

    def getDeviceData(self):
    
        if not self.loginKey:
            return

        url = "{}/{}".format(API_BASE, 'devices.json')
        headers = { "Content-Type": "application/json", 'Authorization': "Token " + self.loginKey }
        try:
            response = requests.get(url, headers=headers)
        except requests.exceptions.RequestException as err:
            self.logger.error(u"getDevices: RequestException: " + str(err))
            return False
        
        # save the device data, converting from array of fireboard device dicts to a dict keyed on the fireboard hardware_id (Indigo address)
        for fb in response.json():
            self.device_info[fb['hardware_id']] = fb
        self.logger.debug(u"getDevices: {} Devices".format(len(self.device_info)))
        self.logger.threaddebug(u"getDevices device_info = {}".format(self.device_info))

        # Update the Indigo devices
        
        for fbID, fbDevice in self.device_info.iteritems():
            
            if not fbID in self.knownDevices:
                self.knownDevices[fbID] = fbDevice['title']

            if fbID in self.fbDevices:
                dev = indigo.devices[self.fbDevices[fbID]]
                self.logger.threaddebug(u'{}:\n{}'.format(dev.name, fbDevice))

                battery = fbDevice['last_battery_reading']
                if battery:
                    dev.updateStateOnServer('batteryLevel', battery, uiValue='{}%'.format(battery))

                states_list = []
                states_list.append({'key': 'uuid',          'value': fbDevice['uuid']})
                states_list.append({'key': 'title',         'value': fbDevice['title']})
                states_list.append({'key': 'model',         'value': fbDevice['model']})
                states_list.append({'key': 'created',       'value': fbDevice['created']})
                states_list.append({'key': 'channel_count', 'value': fbDevice['channel_count']})
                states_list.append({'key': 'degreetype',    'value': fbDevice['degreetype']})
                states_list.append({'key': 'last_templog',  'value': fbDevice['last_templog']})
                states_list.append({'key': 'probe_config',  'value': fbDevice['probe_config']})
                states_list.append({'key': 'id',            'value': fbDevice['id']})
                states_list.append({'key': 'hardware_id',   'value': fbDevice['hardware_id']})
                states_list.append({'key': 'version',       'value': fbDevice['version']})
                states_list.append({'key': 'fbj_version',   'value': fbDevice['fbj_version']})
                states_list.append({'key': 'fbn_version',   'value': fbDevice['fbn_version']})
                states_list.append({'key': 'fbu_version',   'value': fbDevice['fbu_version']})                    
                dev.updateStatesOnServer(states_list)
            
                for channel in fbDevice['channels']:
                    self.logger.debug(u"getDevices: channel = {}".format(channel))
                    key = "{}-{}".format(fbDevice['uuid'], channel['channel'])
                    if key in self.fbChannels:
                        dev = indigo.devices[self.fbChannels[key]]
                        states_list = []
                        if channel.get('last_templog', None):
                            if channel['last_templog']['degreetype'] == 1:
                                scale = 'C'
                            elif  channel['last_templog'][u'degreetype'] == 2:
                                scale = 'F'
                            last_temp = channel['last_templog']['temp']
                            states_list.append({'key': 'sensorValue',   'value': last_temp, 'decimalPlaces': 1, 'uiValue': u'{:.1f} °{}'.format(last_temp, scale)})
                        else:
                            states_list.append({'key': 'sensorValue',   'value': 0.0, 'decimalPlaces': 1, 'uiValue': u'0.0'})
                        
                        states_list.append({'key': 'id',            'value': channel['id']})
                        states_list.append({'key': 'channel',       'value': channel['channel']})
                        states_list.append({'key': 'channel_label', 'value': channel['channel_label']})
                        states_list.append({'key': 'created',       'value': channel['created']})
                        states_list.append({'key': 'enabled',       'value': channel['enabled']})
                        dev.updateStatesOnServer(states_list)


            battery = fbDevice['last_battery_reading']
            if battery:
                dev.updateStateOnServer('batteryLevel', battery, uiValue='{}%'.format(battery))



    ########################################

    def getTemperatures(self):

        if not self.loginKey:
            return

        for fbID in self.fbDevices:
        
            fbDevice = self.device_info[fbID]

            url = "{}/devices/{}/temps.json".format(API_BASE, fbDevice['uuid'])
            headers = { "Content-Type": "application/json", 'Authorization': "Token " + self.loginKey }
            try:
                response = requests.get(url, headers=headers)
            except requests.exceptions.RequestException as err:
                self.logger.error(u"getTemperatures: RequestException: " + str(err))
            else:
                self.logger.debug(u"getTemperatures for {}".format(fbDevice['uuid']))
                for probe in response.json():
                    self.logger.debug(u"getTemperatures: {}".format(probe))
                    key = "{}-{}".format(fbDevice['uuid'], probe['channel'])
                    device = indigo.devices[self.fbChannels[key]]
                    if probe[u'degreetype'] == 1:
                        scale = 'C'
                    elif  probe[u'degreetype'] == 2:
                        scale = 'F'
                    device.updateStateOnServer(key='sensorValue', value=probe[u'temp'], decimalPlaces=1, uiValue=u'{:.1f} °{}'.format(probe[u'temp'], scale))
