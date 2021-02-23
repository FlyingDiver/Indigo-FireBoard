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

    def shutdown(self):
        indigo.server.log(u"Shutting down FireBoard")

    def validatePrefsConfigUi(self, valuesDict):
        errorDict = indigo.Dict()

        if len(errorDict) > 0:
            return (False, valuesDict, errorDict)

        return True
        
    def closedPrefsConfigUi(self, valuesDict, userCancelled):
        if not userCancelled:
            try:
                self.logLevel = int(valuesDict[u"logLevel"])
            except:
                self.logLevel = logging.INFO
            self.indigo_log_handler.setLevel(self.logLevel)
            self.logger.debug(u"closedPrefsConfigUi, logLevel = {}".format(self.logLevel))        



    def runConcurrentThread(self):

        try:
            while True:

                if time.time() > self.next_update:
                    self.next_update = time.time() + self.updateFrequency
                    self.getUpdate()

                self.sleep(1.0)

        except self.StopThread:
            pass

    def deviceStartComm(self, device):
        
        if device.deviceTypeId == 'fireboardDevice':
            self.logger.debug(u"{}: deviceStartComm: Adding device ({}) to Device list".format(device.name, device.id))
            self.fb_devices[device.address] = device.id
            self.logger.threaddebug(u"fb_devices = {}".format(self.fb_devices))
            self.logger.debug(u"deviceStartComm, self.fb_devices = {}".format(self.fb_devices))

            fbDevice = self.knownDevices[device.address]

            battery = fbDevice.get("last_battery_reading", None)
            if battery:
                battery = int(battery * 100)
                device.updateStateOnServer('batteryLevel', battery, uiValue='{}%'.format(battery))

            states_list = []
            states_list.append({'key': 'name',          'value': fbDevice['title']})
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
            states_list.append({'key': 'drive_type',    'value': fbDevice['last_drivelog']['drivetype']})                    
            states_list.append({'key': 'drive_set',     'value': fbDevice['last_drivelog']['setpoint']})                    
            states_list.append({'key': 'drive_per',     'value': fbDevice['last_drivelog']['driveper']})                    
            states_list.append({'key': 'drive_mode',    'value': fbDevice['last_drivelog']['modetype']})                    
            device.updateStatesOnServer(states_list)
            
        
        elif device.deviceTypeId == 'fireboardChannel':
            self.logger.debug(u"{}: deviceStartComm: Adding device ({}) to Channel list".format(device.name, device.id))
            self.fb_channels[device.address] = device.id
            self.logger.debug(u"deviceStartComm, self.fb_channels = {}".format(self.fb_channels))
            
            for channel in self.knownDevices[device.pluginProps['device']]['channels']:
                chanNumber = int(device.address.split('-')[1])
                if channel['channel'] != chanNumber:
                    continue
                    
                self.logger.debug(u"getDevices: channel = {}".format(channel))
                states_list = []
                states_list.append({'key': 'id',            'value': channel['id']})
                states_list.append({'key': 'channel',       'value': channel['channel']})
                states_list.append({'key': 'channel_label', 'value': channel['channel_label']})
                states_list.append({'key': 'created',       'value': channel['created']})
                states_list.append({'key': 'enabled',       'value': channel['enabled']})
                states_list.append({'key': 'sensorValue',   'value': 0, 'uiValue': u'0'})
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
            addr = "{}-{}".format(valuesDict['device'], ch['channel'])
            retList.append((addr, ch['channel_label']))
        retList.sort(key=lambda tup: tup[1])
        return retList
    
    # doesn't do anything, just needed to force other menus to dynamically refresh
    def menuChanged(self, valuesDict = None, typeId = None, devId = None):
        self.logger.threaddebug("menuChanged: devId = {}, typeId = {}, valuesDict = {}".format(devId, typeId, valuesDict))
        return valuesDict


    ########################################

    def getUpdate(self):

        for fb_device in self.fb_account.get_devices():       
            self.knownDevices[fb_device['hardware_id']] = fb_device
        self.logger.threaddebug(u"knownDevices:\n{}".format(json.dumps(self.knownDevices, indent=4, separators=(',', ': '))))
            
        for fb_address, devID in self.fb_devices.iteritems():
            fb_device = indigo.devices[int(devID)]
            fb_info = self.knownDevices[fb_address]
            states_list = []
                        
            battery = fb_info.get("last_battery_reading", None)
            if battery:
                battery = int(battery * 100)
                states_list.append({'key': 'batteryLevel', 'value': battery, 'uiValue': '{}%'.format(battery)})                    

            states_list.append({'key': 'drive_type',    'value': fb_info['last_drivelog']['drivetype']})                    
            states_list.append({'key': 'drive_set',     'value': fb_info['last_drivelog']['setpoint']})                    
            states_list.append({'key': 'drive_per',     'value': fb_info['last_drivelog']['driveper']})                    
            states_list.append({'key': 'drive_mode',    'value': fb_info['last_drivelog']['modetype']})                    
            fb_device.updateStatesOnServer(states_list)

        for ch_address, devID in self.fb_channels.iteritems():
            ch_device = indigo.devices[int(devID)]
            fb_device  = ch_address.split('-')[0]
            chanNumber = int(ch_address.split('-')[1])
        
            fb_info = self.knownDevices[fb_device]
                
            # find the sensor in the list of temp reports.  Not present means it's not reporting, so no update.
            for sensor in fb_info['latest_temps']:
                if sensor['channel'] != chanNumber:
                    continue
            
                if sensor['degreetype'] == 1:
                    scale = 'C'
                elif sensor['degreetype'] == 2:
                    scale = 'F'

                ch_device.updateStateOnServer(key='sensorValue', value=sensor['temp'], decimalPlaces=1, uiValue=u'{:.1f} °{}'.format(sensor['temp'], scale))
                ch_device.updateStateOnServer(key='created', value=sensor['created'])

