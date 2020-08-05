#! /usr/bin/env python
# -*- coding: utf-8 -*-
####################

import time
import requests
import logging
import json

kCurDevVersCount = 0       # current version of plugin devices

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

        self.needsUpdate = True
        self.device_info = {}

        self.fbDevices = {}
        self.fbChannels = {}
        self.triggers = { }
        self.knownDevices = {}
        
        self.statusFrequency = float(self.pluginPrefs.get('statusFrequency', "10")) * 60.0
        self.logger.debug(u"statusFrequency = {}".format(self.statusFrequency))
        self.next_status_check = time.time()

        if not self.fbLogin(username=self.pluginPrefs['FireBoardLogin'], password=self.pluginPrefs['FireBoardPassword']):
            indigo.server.error(u"FireBoard Login Failure")

    def shutdown(self):
        indigo.server.log(u"Shutting down FireBoard")


    def runConcurrentThread(self):

        try:
            while True:

                if self.needsUpdate or (time.time() > self.next_status_check):
                    self.getDevices()
                    self.next_status_check = time.time() + self.statusFrequency
                    self.needsUpdate = False

                self.sleep(1.0)

        except self.StopThread:
            pass

    def deviceStartComm(self, device):

        instanceVers = int(device.pluginProps.get('devVersCount', 0))
        if instanceVers >= kCurDevVersCount:
            self.logger.debug(u"{}: deviceStartComm: Device version is up to date ({})".format(device.name, instanceVers))
        elif instanceVers < kCurDevVersCount:
            newProps = device.pluginProps
            newProps["devVersCount"] = kCurDevVersCount
            device.replacePluginPropsOnServer(newProps)
            device.stateListOrDisplayStateIdChanged()
            self.logger.debug(u"{}: deviceStartComm: Updated to device version {}, props = {}".format(device.name, kCurDevVersCount, newProps))
        else:
            self.logger.error(u"{}: deviceStartComm: Unknown device version: {}".format(device.name, instanceVers))
        
        if device.deviceTypeId == 'fireboard':
            self.logger.debug(u"{}: deviceStartComm: Adding device ({}) to FireBoard list".format(device.name, device.id))
            assert device.address not in self.fbDevices
            self.fbDevices[device.address] = device.id
            self.logger.threaddebug(u"fbDevices = {}".format(self.fbDevices))
            self.needsUpdate = True
        elif device.deviceTypeId == 'fireboardChannel':
            self.logger.debug(u"{}: deviceStartComm: Adding device ({}) to Channel list".format(device.name, device.id))
            assert device.address not in self.fbChannels
            self.fbChannels[device.address] = device.id
            self.logger.threaddebug(u"fbChannels = {}".format(self.fbChannels))
            self.needsUpdate = True
            
        
    def deviceStopComm(self, device):

        if device.deviceTypeId == 'fireboard':
            self.logger.debug(u"{}: deviceStopComm: Removing device ({}) from FireBoard list".format(device.name, device.id))
            assert device.address in self.fbDevices
            del self.fbDevices[device.address]
        elif device.deviceTypeId == 'fireboardChannel':
            self.logger.debug(u"{}: deviceStopComm: Removing device ({}) from Channel list".format(device.name, device.id))
            assert device.address in self.fbChannels
            del self.fbChannels[device.address]


    ########################################
    # Event Methods
    ########################################

    def triggerStartProcessing(self, trigger):
        self.logger.debug(u"Adding Trigger {} ({}) - {}".format(trigger.name, trigger.id, trigger.pluginTypeId))
        assert trigger.id not in self.triggers
        self.triggers[trigger.id] = trigger

    def triggerStopProcessing(self, trigger):
        self.logger.debug(u"Removing Trigger {} ({})".format(trigger.name, trigger.id))
        assert trigger.id in self.triggers
        del self.triggers[trigger.id]

    def triggerCheck(self, device):
        for triggerId, trigger in sorted(self.triggers.iteritems()):
            self.logger.debug(u"Checking Trigger {} ({}), Type: {}".format(trigger.name, trigger.id, trigger.pluginTypeId))

#                indigo.trigger.execute(trigger) 


    ########################################
    # Menu Methods
    ########################################

    def menuDumpData(self):
        self.logger.info(u"menuDumpData Devices:\n{}".format(json.dumps(self.device_info, indent=4, separators=(',', ': '))))
        return True
        

    ########################################
    # ConfigUI methods
    ########################################

    def validatePrefsConfigUi(self, valuesDict):
        self.logger.debug(u"validatePrefsConfigUi called")
        errorDict = indigo.Dict()

        try:
            self.logLevel = int(valuesDict[u"logLevel"])
        except:
            self.logLevel = logging.INFO
        self.indigo_log_handler.setLevel(self.logLevel)
        self.logger.debug(u"logLevel = " + str(self.logLevel))

        if len(valuesDict['FireBoardLogin']) < 5:
            errorDict['FireBoardLogin'] = u"Enter your FireBoard login name (email address)"

        if len(valuesDict['FireBoardPassword']) < 1:
            errorDict['FireBoardPassword'] = u"Enter your FireBoard login password"

        statusFrequency = int(valuesDict['statusFrequency'])
        if (statusFrequency < 5) or (statusFrequency > (24 * 60)):
            errorDict['statusFrequency'] = u"Status frequency must be at least 5 min and no more than 24 hours"

        if len(errorDict) > 0:
            return (False, valuesDict, errorDict)

        if not self.fbLogin(username=valuesDict['FireBoardLogin'], password=valuesDict['FireBoardPassword']):
            errorDict['FireBoardLogin'] = u"Login to FireBoard server failed, check login, password"
            errorDict['FireBoardPassword'] = u"Login to FireBoard server failed, check login, password"
            return (False, valuesDict, errorDict)

        return (True, valuesDict)


    def closedPrefsConfigUi(self, valuesDict, userCancelled):
        if not userCancelled:
            try:
                self.logLevel = int(valuesDict[u"logLevel"])
            except:
                self.logLevel = logging.INFO
            self.indigo_log_handler.setLevel(self.logLevel)
            self.logger.debug(u"logLevel = " + str(self.logLevel))

            self.statusFrequency = float(self.pluginPrefs.get('statusFrequency', "10")) * 60.0
            self.logger.debug(u"statusFrequency = {}".format(self.statusFrequency))
            self.next_status_check = time.time() + self.statusFrequency

            self.getDevices()


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
    # DeviceFactory methods (specified in Devices.xml):
    ####################

    def getDeviceFactoryUiValues(self, devIdList):
        self.logger.debug(u"getDeviceFactoryUiValues: devIdList = {}".format(devIdList))
        valuesDict = indigo.Dict()
        errorMsgDict = indigo.Dict()
        return (valuesDict, errorMsgDict)

    def validateDeviceFactoryUi(self, valuesDict, devIdList):
        self.logger.debug(u"validateDeviceFactoryUi: valuesDict = {}, devIdList = {}".format(valuesDict, devIdList))
        errorsDict = indigo.Dict()
        return (True, valuesDict, errorsDict)

    def closedDeviceFactoryUi(self, valuesDict, userCancelled, devIdList):
        if userCancelled:
            self.logger.debug(u"closedDeviceFactoryUi: user cancelled")
            return

        self.logger.threaddebug(u"closedDeviceFactoryUi: valuesDict =\n{}\ndevIdList =\n{}".format(valuesDict, devIdList))
        
        # Create the controller device
        
        fbID = valuesDict['address']
        fbDevice = self.device_info[fbID]
        props = { "SupportsBatteryLevel": True,  "SupportsStatusRequest": True}
        newdev = indigo.device.create(indigo.kProtocol.Plugin, address=fbID, name=fbDevice['title'], props=props, deviceTypeId="fireboard")
        newdev.model = "FireBoard"
        newdev.subModel = fbDevice['model']
        newdev.replaceOnServer()
        
        # Now create the probe channels
        
        props = { "SupportsOnState": False, "SupportsSensorValue": True, "SupportsStatusRequest": False}

        for channel in fbDevice['channels']:
            newdev = indigo.device.create(indigo.kProtocol.Plugin, address=channel['id'], name=channel['channel_label'], props=props, deviceTypeId="fireboardChannel")
            newdev.model = "FireBoard"
            newdev.subModel = "Channel"
            newdev.replaceOnServer()
        
        return

    ########################################

    def fbLogin(self, username=None, password=None):

        if username == None or password == None:
            self.logger.debug(u"fbLogin failure, Username or Password not set")
            return False

        headers = {
                'Content-Type':     'application/json'
        }
        payload = {
                'username': username, 
                'password': password
        }

        try:
            response = requests.post(API_LOGIN, json=payload, headers=headers)
            self.logger.debug(u"fbLogin response = {}".format(response.text))
            
        except requests.exceptions.RequestException as err:
            self.logger.debug(u"fbLogin failure, request url: {}, RequestException: {}".format(url, err))
            self.loginKey = ""
            return False

        if (response.status_code != requests.codes.ok):
            self.logger.debug(u"fbLogin failure, status_code = {}".format(response.status_code))
            self.loginKey = ""
            return False        

        try:
            self.loginKey = response.json()['key']
        except:
            self.logger.debug(u"fbLogin failure, json decode failure")
            return False
        return True

    ########################################

    def getDevices(self):

        url = "{}/{}".format(API_BASE, 'devices.json')
        headers = {
                "Content-Type":     "application/json",
                'Authorization':    "Token " + self.loginKey
        }
        try:
            response = requests.get(url, headers=headers)
        except requests.exceptions.RequestException as err:
            self.logger.error(u"getDevices: RequestException: " + str(err))
            return False
        
        for fb in response.json():
            self.device_info[fb['hardware_id']] = fb
            
        self.logger.debug(u"getDevices: {} Devices".format(len(self.device_info)))
        self.logger.threaddebug(u"getDevices device_info = {}".format(self.device_info))

        for fbID, fbDevice in self.device_info.iteritems():

            fbName = fbDevice['title']
            self.logger.debug(u"getDevices: name = {}, hardware_id = {}".format(fbName, fbID))
            
            if not fbID in self.knownDevices:
                self.knownDevices[fbID] = fbName

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
                    self.logger.threaddebug(u"getDevices: channel = {}".format(channel))
                    channelID = str(channel['id'])
                    if channelID in self.fbChannels:
                        dev = indigo.devices[self.fbChannels[channelID]]
                        states_list = []
                        temp = channel.get('current_temp', None)
                        if not temp:
                            temp = 0.0
                        states_list.append({'key': 'sensorValue',   'value': temp, 'uiValue': "{:1}°".format(temp)})
                        states_list.append({'key': 'id',            'value': channel['id']})
                        states_list.append({'key': 'channel',       'value': channel['channel']})
                        states_list.append({'key': 'channel_label', 'value': channel['channel_label']})
                        states_list.append({'key': 'created',       'value': channel['created']})
                        states_list.append({'key': 'enabled',       'value': channel['enabled']})
                        dev.updateStatesOnServer(states_list)
                    
                    
                self.triggerCheck(dev)

    ########################################
