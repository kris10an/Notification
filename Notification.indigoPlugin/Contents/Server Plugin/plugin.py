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

############################
# Globals
############################

pluginId = u'com.kris10an.indigoplugin.notification'

intervalToSeconds = {
	u'1 hour'	:	60*60,
	u'12 hours'	:	60*60*12,
	u'1 day'		:	60*60*24,
	u'1 week'	:	60*60*24*7,
	u'1 month'	:	60*60*24*30 }


################################################################################
class Plugin(indigo.PluginBase):
	########################################
	def __init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs):
		indigo.PluginBase.__init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs)
		
		# Plugin prefs
		self.debug = pluginPrefs.get(u'debugLog', False)
		self.extDebug = pluginPrefs.get(u'extensiveDebug', False)
		self.pluginLog = pluginPrefs.get(u'pluginLog', True)
		self.varFolderName = pluginPrefs.get(u'varFolderName','Notification plugin log')
		
		# Error states
		self.pluginConfigErrorState = False # Whether or not plugin is in error state, due to faulty plugin config
		
		# Presets, not configurable
		self.notifyVarPrefix = u'notification'
		self.logDir = indigo.server.getInstallFolderPath() + u'/Logs/Notifications/'
		self.logFileSuffix = u' Notifications.txt'
		self.logFileDateFormat = u'%Y-%m-%d'

	########################################
	def __del__(self):
		indigo.PluginBase.__del__(self)

	########################################
	def startup(self):
		self.debugLog(u'Startup called')
		self.debugLog(u'Log folder: %s' % (self.logDir))
		self.debugLog(u'Variable folder name: %s' % (self.varFolderName))
		
		# Check if our variable folder exists
		if len(self.varFolderName) == 0:
			# No folder name specified, quit plugin
			self.pluginConfigErrorState = True
			self.pluginConfigErrorMsg = u'No variable folder name specified in plugin config, please fix'
			return
		else:
			if not self.varFolderName in indigo.variables.folders:
				# Variable folder does not exist, create
				self.debugLog(u'Variable folder "%s" not found, creating folder' % (self.varFolderName))
				try:
					newFolder = indigo.variables.folder.create(self.varFolderName)
					indigo.variables.folder.displayInRemoteUI(newFolder, value=False)
					self.varFolderId = newFolder.id
					indigo.server.log(u'Variable folder "%s" did not exist, folder was created' % (self.varFolderName))
				except:
					self.errorLog(u'Could not create variable folder "%s" for some reason' % (self.varFolderName))
			else:
				# Find ID of existing folder
				self.varFolderId = indigo.variables.folders[self.varFolderName]

		indigo.server.log(u'Notification plugin started')

	########################################
	def shutdown(self):
		self.debugLog(u'Shutdown called')
		pass
		
	def closedPrefsConfigUi(self, valuesDict, userCancelled):
		# Plugin prefs
		self.debug = self.pluginPrefs.get("debugLog", False)
		self.extDebug = self.pluginPrefs.get(u'extensiveDebug', False)
		self.pluginLog = self.pluginPrefs.get("pluginLog", True)
		if self.pluginPrefs.get(u'varFolderName','Notification plugin log') != self.varFolderName:
			#Variable folder name has changed, restart plugin
			indigo.server.log(u'Variable folder name has changed, plugin will restart')
			plugin = indigo.server.getPlugin(pluginId)
			if plugin.isEnabled():
   				plugin.restart(waitUntilDone=False)
		self.varFolderName = self.pluginPrefs.get(u'varFolderName','Notification plugin log')
		
		# DO VALIDATION
		self.pluginConfigErrorState = False
		

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
				# Check for errors
				if self.pluginConfigErrorState:
					self.errorLog(self.pluginConfigErrorMsg)
					
				self.sleep(5)
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
			self.errorLog(u'Invalid or unspecified notification category device specified in send notification action, dropping notification.\nNotification text: %s' % action.text)
			return
		
		# Check if category device is enabled
		if not categoryDev.enabled:
			indigo.server.log(u'Notification category device "%s" has been disabled, skipping notification.\nNotification text: %s' % (categoryDev.name, action.text))
			return
			
		actionProps = action.props
		catProps = categoryDev.pluginProps
		catStates = categoryDev.states
		if self.extDebug: self.debugLog(u'Notification category "%s" plugin props: %s' % (categoryDev.name, str(catProps)))
		if self.extDebug: self.debugLog(u'Notification category "%s" states: %s' % (categoryDev.name, str(catStates)))
		
		# Check if every notification is to be delivered, or by interval
		send = False
		timeNow = datetime.now()
		
		if(len(catStates[u'lastNotificationTime']) > 0):
			if catProps[u'sendEvery'] == u'always':
				# Set to always send
				send = True
				self.debugLog(u'Notification category set to always send, will send now')
			else:
				# Notification category set to only send at given interval
				# Check when notification category was last sent/used
				try:
					lastSent = strvartime.strToTime(catStates[u'lastNotificationTime'])
					self.debugLog(u'Notification category last sent: %s' % (catStates[u'lastNotificationTime']))
				except:
					lastSent = strvartime.strToTime(u'2000-01-01 00:00:00')	
				self.debugLog(u'Last notification time of category could not be obtatined, set to year 2000')
				
				#Determine if enough time has passed to send it again
				if not catProps[u'sendEvery'] in intervalToSeconds:
					self.errorLog(u'Invalid setting for delivery interval for category "%s". Check settings. Notification skipped.\nNotification text: %s' % (categoryDev.name, actionProps[u'text']))
					return
					
				if strvartime.timeDiff(lastSent, timeNow, 'seconds') >= intervalToSeconds[catProps[u'sendEvery']]:
					send = True
					self.debugLog(u'Notification category set to send every %s, Last notification sent %s. Will send notification now' % (catProps[u'sendEvery'], strvartime.prettyDate(lastSent)))
				else:
					self.debugLog(u'Notification category set to send every %s, Last notification sent %s. Will _not_ send notification now' % (catProps[u'sendEvery'], strvartime.prettyDate(lastSent)))
		else:
			self.debugLog(u'Notification category has never been sent before, will send now')
			send = True
			
		#Make sure presence for persons is up to date
		if catProps[u'notifyPresent']:
			numPresent = self.personsUpdatePresence(True)
		
		
		
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
			dev.updateStateOnServer(u'lastNotificationTime',valuesDict[u'newValue'])
			indigo.server.log(u'Last notification time for device "%s" set to %s' % (dev.name, valuesDict[u'newValue']))
			return True
		except:
			self.errorLog(u'Could not update last notification time manually')
			return
	
		
	########################################
	# Update presence state of persons
	########################################	
	
	# errorIfNotSuccessful :	Sometimes may be useful not to throw errors if presence variable is not set/in use
	
	def personsUpdatePresence( self, errorIfNotSuccessful = True ):
	
		self.debugLog(u'Update presence for "person" devices')
		i = 0 # Number of persons present
		# iterate through "person" devices"
		for dev in indigo.devices.iter(pluginId + u'.notificationPerson'):
			devProps = dev.pluginProps
			if self.extDebug: self.debugLog(u'"%s" plugin properties: %s' % (dev.name, str(devProps)))
			try:
				# Set state of presence based on variable given in device config UI
				presenceVar = indigo.variables[int(devProps['presenceVariable'])]
				dev.updateStateOnServer('present',presenceVar.getValue(bool, default=True))
				if presenceVar.getValue(bool, default=True): i = i + 1 # person is present
				self.debugLog(u'"%s" person device presence set to: %s' % (dev.name, str(presenceVar.getValue(bool, default=True))))
			except:
				if errorIfNotSuccessful: self.errorLog(u'Could not get presence of person "%s", please check settings. Presence set to true as default' % dev.name)
				# Most likely no variable for presence is given, set to being present as it's "safer" to receive notification than not
				dev.updateStateOnServer('present',True)
				i = i + 1
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
