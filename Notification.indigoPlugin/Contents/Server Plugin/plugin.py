#! /usr/bin/env python
# -*- coding: utf-8 -*-
####################
# Copyright (c) 2016, krishj. All rights reserved.
# http://www.indigodomo.com

import indigo

import os
import sys
import time
from datetime import datetime
import strvartime

# Note the "indigo" module is automatically imported and made available inside
# our global name space by the host process.

################################################################################
class Plugin(indigo.PluginBase):
	########################################
	def __init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs):
		indigo.PluginBase.__init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs)
		self.debug = pluginPrefs.get(u'debugLog', False)
		self.extDebug = pluginPrefs.get(u'extensiveDebug', False)
		self.pluginLog = pluginPrefs.get(u'pluginLog', True)
		self.notifyVarPrefix = u'notification'
		self.notifyVarFolder = u'Notification log'
		self.logDir = indigo.server.getInstallFolderPath() + u'/Logs/Notifications/'
		self.logFileSuffix = u' Notifications.txt'
		self.logFileDateFormat = u'%Y-%m-%d'

	########################################
	def __del__(self):
		indigo.PluginBase.__del__(self)

	########################################
	def startup(self):
		self.debugLog(u'Startup called')
		self.debugLog(u'Log folder: %s' % self.logDir)

	########################################
	def shutdown(self):
		self.debugLog(u'Shutdown called')
		pass
		
	def closedPrefsConfigUi(self, valuesDict, userCancelled):
		self.debug = self.pluginPrefs.get("debugLog", False)
		self.extDebug = self.pluginPrefs.get(u'extensiveDebug', False)
		self.pluginLog = self.pluginPrefs.get("pluginLog", True)

	########################################
	# If runConcurrentThread() is defined, then a new thread is automatically created
	# and runConcurrentThread() is called in that thread after startup() has been called.
	#
	# runConcurrentThread() should loop forever and only return after self.stopThread
	# becomes True. If this function returns prematurely then the plugin host process
	# will log an error and attempt to call runConcurrentThread() again after several seconds.
	def runConcurrentThread(self):
		try:
			while True:
				self.sleep(600)
		except self.StopThread:
			pass
			
	#def getDeviceDisplayStateId(self, dev):
	

	########################################
	# Actions defined in MenuItems.xml:
	####################

	########################################
	# Methods defined for notificationPerson

	########################################
	# ACTIONS
	########################################
	
	########################################
	# sendNotification
	########################################
	
	def sendNotification(self, action):
		if self.extDebug: self.debugLog(u"sendNotification action called: props: %s" % (str(action)))
		else: self.debugLog(u'sendNotification action called')

		# Check if category device is valid		
		try:
			categoryDev = indigo.devices[action.deviceId]
		except:
			self.errorLog(u"Invalid notification category device specified in send notification action")
			return
		
		# Check if category device is enabled
		if not categoryDev.enabled:
			indigo.server.log(u'Notification category device "%s" has been disabled, skipping notification' % (categoryDev.name))
			return
			
		catProps = categoryDev.pluginProps
		catStates = categoryDev.states
		if self.extDebug: self.debugLog(u'Notification category "%s" plugin props: %s' % (categoryDev.name, str(catProps)))
		if self.extDebug: self.debugLog(u'Notification category "%s" states: %s' % (categoryDev.name, str(catStates)))
		
		# Check if every notification is to be delivered, or by interval
		send = False
		timeNow = datetime.now()
		if(len(catStates[u'lastNotificationTime']) > 0):
			try:
				lastSent = strvartime.strToTime(catStates[u'lastNotificationTime'])
				self.debugLog(u'Notification category last sent: %s' % (catStates[u'lastNotificationTime']))
			except:
				lastSent = strvartime.strToTime(u'2000-01-01 00:00:00')	
				self.debugLog(u'Last notification time of category could not be obtatined, set to year 2000')		
					
			if catProps[u'sendEvery'] == u'always':
				send = True
				self.debugLog(u'Notification category set to always send, will send now')
			else:
				#Determine if enough time has passed to send it again
			
				if catProps[u'sendEvery'] == u'1hour':
					if strvartime.timeDiff(lastSent, timeNow, 'seconds') >= 60*60: send = True
				elif catProps[u'sendEvery'] == u'12hours':
					if strvartime.timeDiff(lastSent, timeNow, 'seconds') >= 60*60*12: send = True
				elif catProps[u'sendEvery'] == u'1day':
					if strvartime.timeDiff(lastSent, timeNow, 'seconds') >= 60*60*24: send = True
				elif catProps[u'sendEvery'] == u'1week':
					if strvartime.timeDiff(lastSent, timeNow, 'seconds') >= 60*60*24*7: send = True
				elif catProps[u'sendEvery'] == u'1month':
					if strvartime.timeDiff(lastSent, timeNow, 'seconds') >= 60*60*24*30: send = True
				
				self.debugLog(u'Notification category set to send every %s. Send now: %s' % (catProps[u'sendEvery'], str(send)))
	
		else:
			self.debugLog(u'Notification category has never been sent before, will send now')
			send = True
			
		
		#Make sure presence for persons is up to date
		self.personsUpdatePresence()
		
		
		
		# Determine who to deliver to
		
			
		#categoryDev.updateStateOnServer("lastNotificationTime", strvartime.timeToStr())
			
		#self.debugLog(u"%s" % str(categoryDev))

	########################################
	# update last notification time manually, mainly for testing
	########################################
		
	def updateLastNotificationTimeManually ( self, valuesDict, typeId ):
	
		#CLEAN UP function if used for other things
		
		if self.extDebug: self.debugLog(u"updateLastNotificationTimeManually action called: props: %s" % (str(valuesDict)))
		
		try:
			dev = indigo.devices[int(valuesDict[u'targetDevice'])]
			dev.updateStateOnServer('lastNotificationTime',valuesDict[u'newValue'])
		
			errorsDict = indigo.Dict()
			return (True, valuesDict, errorsDict)
		except:
			self.ErrorLog(u'Could not update last notification time manually')
			return (False, valuesDict, errorsDict)
	
		
	########################################
	# Update presence state of persons
	########################################	
	
	def personsUpdatePresence( self ):
	
		self.debugLog(u'Update presence for "person" devices')
		# iterate through "person" devices"
		for dev in indigo.devices.iter('com.perceptiveautomation.indigoplugin.notification.notificationPerson'):
			devProps = dev.pluginProps
			if self.extDebug: self.debugLog(u'"%s" plugin properties: %s' % (dev.name, str(devProps)))
			try:
				# Set state of presence based on variable given in device config UI
				presenceVar = indigo.variables[int(devProps['presenceVariable'])]
				dev.updateStateOnServer('present',str(presenceVar.getValue(bool, default=True)))
				self.debugLog(u'"%s" person device presence set to: %s' % (dev.name, str(presenceVar.getValue(bool, default=True))))
			except:
				# Most likely no variable for presence is given, set to being present
				dev.updateStateOnServer('present',str(presenceVar.getValue(bool, default=True)))
				self.debugLog(u'"%s" person device presence set to true as no real presence could be obtained from variable' % (dev.name))
				
	########################################
	# Validate device configuration
	########################################
	def validateDeviceConfigUi(self, valuesDict, typeId, devId):
		#  
		if self.extDebug: self.debugLog(u"validateDeviceConfigUi: typeId: %s  devId: %s" % (typeId, str(devId)))
		
		dev = indigo.devices[devId]
		
# 		if valuesDict['enabled']:
# 			dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOn)
# 		else:
# 			dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOff)
			
		return (True, valuesDict)
		
	########################################
	# Validate action configuration
	########################################
	def validateActionConfigUi(self, valuesDict, typeId, devId):
		# 
		if self.extDebug: self.debugLog(u"validateActionConfigUi: typeId: %s  devId: %s  valuesDict: %s" % (typeId, str(devId), str(valuesDict)))
		return (True, valuesDict)
		
	########################################
	# Validate plugin prefs changes:
	####################
	def validatePrefsConfigUi(self, valuesDict):
		if self.extDebug: self.debugLog("validatePrefsConfigUI valuesDict: %s" % str(valuesDict))
		return (True, valuesDict)
