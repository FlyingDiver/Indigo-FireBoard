#! /usr/bin/env python
# -*- coding: utf-8 -*-
####################

import time
import requests
import logging
import json
from fireboard import FireBoard

API_LOGIN = "https://fireboard.io/api/rest-auth/login/"
API_BASE = "https://fireboard.io/api/v1/"


################################################################################
class Plugin(indigo.PluginBase):

    ########################################
    # Main Plugin methods
    ########################################
    def __init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs):
        indigo.PluginBase.__init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs)

        pfmt = logging.Formatter('%(asctime)s.%(msecs)03d\t[%(levelname)8s] %(name)20s.%(funcName)-25s%(msg)s', datefmt='%Y-%m-%d %H:%M:%S')
        self.plugin_file_handler.setFormatter(pfmt)
        self.logLevel = int(self.pluginPrefs.get("logLevel", logging.INFO))
        self.indigo_log_handler.setLevel(self.logLevel)
        self.logger.debug(f"logLevel = {self.logLevel}")

        self.fb_devices = {}  # Indigo device IDs, keyed by address (hardware_id)
        self.fb_channels = {}  # Indigo device IDs, keyed by uuid-channel string
        self.knownDevices = {}

        self.fb_account = FireBoard(username=pluginPrefs['FireBoardLogin'], password=pluginPrefs['FireBoardPassword'])
        for device in self.fb_account.get_devices():
            self.knownDevices[device['hardware_id']] = device
        self.logger.threaddebug(f"knownDevices = {self.knownDevices}")

        self.updateFrequency = float(self.pluginPrefs.get('updateFrequency', "1")) * 60.0
        self.logger.debug(f"updateFrequency = {self.updateFrequency}")
        self.next_update = time.time()

    def startup(self):
        self.logger.info("Starting FireBoard")

    def shutdown(self):
        self.logger.info("Shutting down FireBoard")

    def closedPrefsConfigUi(self, valuesDict, userCancelled):
        if not userCancelled:
            self.logLevel = int(valuesDict.get("logLevel", logging.INFO))
            self.indigo_log_handler.setLevel(self.logLevel)
            self.logger.debug(f"logLevel = {self.logLevel}")

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
            self.logger.debug(f"{device.name}: deviceStartComm: Adding device ({device.id}) to Device list")
            self.fb_devices[device.address] = device.id
            self.logger.debug(f"deviceStartComm, self.fb_devices = {self.fb_devices}")
            self.logger.debug(f"deviceStartComm, self.knownDevices = {self.knownDevices}")

            fbDevice = self.knownDevices[device.address]
            self.logger.debug(f"deviceStartComm, fbDevice = {fbDevice}")

            battery = fbDevice.get("last_battery_reading", None)
            if battery:
                battery = int(battery * 100)
                device.updateStateOnServer('batteryLevel', battery, uiValue='{}%'.format(battery))

            states_list = [{'key': 'name', 'value': fbDevice['title']},
                           {'key': 'model', 'value': fbDevice['model']},
                           {'key': 'created', 'value': fbDevice['created']},
                           {'key': 'channel_count', 'value': fbDevice['channel_count']},
                           {'key': 'degreetype', 'value': fbDevice['degreetype']},
                           {'key': 'last_templog', 'value': fbDevice['last_templog']},
                           {'key': 'probe_config', 'value': fbDevice['probe_config']},
                           {'key': 'hardware_id', 'value': fbDevice['hardware_id']},
                           {'key': 'version', 'value': fbDevice['version']},
                           {'key': 'fbj_version', 'value': fbDevice['fbj_version']},
                           {'key': 'fbn_version', 'value': fbDevice['fbn_version']},
                           {'key': 'fbu_version', 'value': fbDevice['fbu_version']}]

            if fbDevice.get('last_drivelog', None):
                states_list.append({'key': 'drive_type', 'value': fbDevice['last_drivelog']['drivetype']})
                states_list.append({'key': 'drive_set', 'value': fbDevice['last_drivelog']['setpoint']})
                states_list.append({'key': 'drive_per', 'value': fbDevice['last_drivelog']['driveper']})
                states_list.append({'key': 'drive_mode', 'value': fbDevice['last_drivelog']['modetype']})

            device.updateStatesOnServer(states_list)

        elif device.deviceTypeId == 'fireboardChannel':
            self.logger.debug(f"{device.name}: deviceStartComm: Adding device ({device.id}) to Channel list")
            self.fb_channels[device.address] = device.id
            self.logger.debug(f"deviceStartComm, self.fb_channels = {self.fb_channels}")

            for channel in self.knownDevices[device.pluginProps['device']]['channels']:
                chanNumber = int(device.address.split('-')[1])
                if channel['channel'] != chanNumber:
                    continue

                self.logger.debug(u"getDevices: channel = {}".format(channel))
                states_list = [{'key': 'id', 'value': channel['id']},
                               {'key': 'channel', 'value': channel['channel']},
                               {'key': 'channel_label', 'value': channel['channel_label']},
                               {'key': 'created', 'value': channel['created']},
                               {'key': 'enabled', 'value': channel['enabled']},
                               {'key': 'sensorValue', 'value': 0, 'uiValue': u'0'}]
                device.updateStatesOnServer(states_list)

    def deviceStopComm(self, device):

        if device.deviceTypeId == 'fireboard':
            self.logger.debug(f"{device.name}: deviceStopComm: Removing device ({device.id}) from FireBoard list")
            del self.fb_devices[device.address]
        elif device.deviceTypeId == 'fireboardChannel':
            self.logger.debug(f"{device.name}: deviceStopComm: Removing device ({device.id}) from Channel list")
            del self.fb_channels[device.address]

    def getDeviceConfigUiValues(self, pluginProps, typeId, devId):
        self.logger.debug(f"getDeviceConfigUiValues, typeId = {typeId}, devId = {devId}, pluginProps = {pluginProps}")
        valuesDict = pluginProps
        errorMsgDict = indigo.Dict()

        if not valuesDict.get('device', None) and len(self.knownDevices):
            valuesDict['device'] = self.knownDevices.keys()[0]
            self.logger.debug(u"getDeviceConfigUiValues, valuesDict = {}".format(valuesDict))

        return valuesDict, errorMsgDict

    ########################################
    # Menu Methods
    ########################################

    def menuDumpData(self):
        self.logger.info(f"menuDumpData Devices:\n{json.dumps(self.device_info, indent=4, separators=(',', ': '))}")
        return True

    def get_device_list(self, filter="", valuesDict=None, typeId="", targetId=0):
        self.logger.debug(f"get_device_list: typeId = {typeId}, targetId = {targetId}, filter = {filter}, valuesDict = {valuesDict}")
        retList = []
        for fb in self.knownDevices.values():
            retList.append((fb['hardware_id'], fb['title']))
        retList.sort(key=lambda tup: tup[1])
        return retList

    def get_channel_list(self, filter="", valuesDict=None, typeId="", targetId=0):
        self.logger.debug(f"get_channel_list: typeId = {typeId}, targetId = {targetId}, filter = {filter}, valuesDict = {valuesDict}")
        retList = []
        if not valuesDict.get('device', None):
            return retList
        fb = self.knownDevices[valuesDict['device']]
        for ch in fb['channels']:
            addr = f"{valuesDict['device']}-{ch['channel']}"
            retList.append((addr, ch['channel_label']))
        retList.sort(key=lambda tup: tup[1])
        return retList

    # doesn't do anything, just needed to force other menus to dynamically refresh
    @staticmethod
    def menuChanged(valuesDict=None, typeId=None, devId=None):
        return valuesDict

    ########################################

    def getUpdate(self):

        for fb_device in self.fb_account.get_devices():
            self.knownDevices[fb_device['hardware_id']] = fb_device
        self.logger.threaddebug(f"knownDevices:\n{json.dumps(self.knownDevices, indent=4, separators=(',', ': '))}")

        for fb_address, devID in self.fb_devices.items():
            fb_device = indigo.devices[int(devID)]
            fb_info = self.knownDevices[fb_address]
            if fb_info.get('last_drivelog', None):
                states_list = [{'key': 'drive_type', 'value': fb_info['last_drivelog']['drivetype']},
                               {'key': 'drive_set', 'value': fb_info['last_drivelog']['setpoint']},
                               {'key': 'drive_per', 'value': fb_info['last_drivelog']['driveper']},
                               {'key': 'drive_mode', 'value': fb_info['last_drivelog']['modetype']}]
            else:
                states_list = []

            battery = fb_info.get("last_battery_reading", None)
            if battery:
                battery = int(battery * 100)
                states_list.append({'key': 'batteryLevel', 'value': battery, 'uiValue': f'{battery}%'})

            fb_device.updateStatesOnServer(states_list)

        for ch_address, devID in self.fb_channels.items():
            ch_device = indigo.devices[int(devID)]
            fb_device = ch_address.split('-')[0]
            chanNumber = int(ch_address.split('-')[1])

            fb_info = self.knownDevices[fb_device]

            # find the sensor in the list of temp reports.  Not present means it's not reporting, so no update.
            for sensor in fb_info['latest_temps']:
                if sensor['channel'] != chanNumber:
                    continue

                if sensor['degreetype'] == 1:
                    scale = 'C'
                else:
                    scale = 'F'

                ch_device.updateStateOnServer(key='sensorValue', value=sensor['temp'], decimalPlaces=1,
                                              uiValue=u'{:.1f} °{}'.format(sensor['temp'], scale))
                ch_device.updateStateOnServer(key='created', value=sensor['created'])
