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
# Globals, prefs, presets
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
		self.alwaysUseVariables = pluginPrefs.get(u'alwaysUseVariables',False)
		
		# Error states
		self.pluginConfigErrorState = False # Whether or not plugin is in error state, due to faulty plugin config
		
		# Presets, not configurable
		self.notificationVarPrefix = u'_notification_'
		self.logDir = indigo.server.getInstallFolderPath() + u'/Logs/Notifications/'
		self.logFileSuffix = u' Notifications.txt'
		self.logFileDateFormat = u'%Y-%m-%d'
		
		# Device and variable lists
		self.personList = {}
		self.personPresentList = {}
		self.categoryList = {}
		#self.presenceVariableList = {}
		self.numPersonPresent = 0

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

		self.debugLog(u'Notification plugin started')

	########################################
	def shutdown(self):
		self.debugLog(u'Shutdown called')
		pass
		
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
	# Start and stop device communication, device updates
	########################################
	
	def deviceStartComm(self, dev):
		#self.debugLog(u'deviceStartComm called: %s' % (str(dev)))
		self.debugLog(u'deviceStartComm called, device %s' % (dev.name))
		
		if dev.deviceTypeId == u'notificationPerson':
			self.personUpdatePresence(dev)
		
			self.personList[dev.id] = 'active'
			
		if self.extDebug:
			self.debugLog(u'personList: %s' % (str(self.personList)))
			self.debugLog(u'personPresentList: %s' % (str(self.personPresentList)))
			self.debugLog(u'numPersonPresent: %i' % (self.numPersonPresent))
			self.debugLog(u'categoryList: %s' % (str(self.categoryList)))
			
	def deviceStopComm(self, dev):
		#if self.extDebug: self.debugLog(u'deviceStopComm called: %s' % (str(dev)))
		self.debugLog(u'deviceStopComm called, device %s' % (dev.name))
		
		if dev.deviceTypeId == u'notificationPerson':
			if dev.id in self.personList:
				del self.personList	[dev.id]
			if dev.id in self.personPresentList:
				del self.personPresentList[dev.id]
			self.numPersonPresent = len(self.personPresentList)
			
		
		if self.extDebug:
			self.debugLog(u'personList: %s' % (str(self.personList)))
			self.debugLog(u'personPresentList: %s' % (str(self.personPresentList)))
			self.debugLog(u'numPersonPresent: %i' % (self.numPersonPresent))
			self.debugLog(u'categoryList: %s' % (str(self.categoryList)))
		
	def deviceUpdated(self, origDev, newDev):
		if self.extDebug: self.debugLog(u'deviceUpdated called %s: \n\n\n***origDev:\n %s\n\n\n***newDev:\n %s' % (newDev.name, str(origDev), str(newDev)))
		else:
			self.debugLog(u'deviceUpdated called %s' % (newDev.name))
		
		if newDev.deviceTypeId == u'notificationPerson':
			if origDev.pluginProps[u'presenceVariable'] != newDev.pluginProps[u'presenceVariable']:
				self.personUpdatePresence(newDev)
				
		# CHECK if this is necessary, or should be handled by Indigo server somehow
		if origDev.enabled != newDev.enabled:
			if newDev.enabled:
				self.deviceStartComm(newDev)
			else:
				self.deviceStopComm(newDev)

	########################################
	# Change to device, perform necessary actions
	########################################
	
	# 	didDeviceCommPropertyChange(self, origDev, newDev):
	# 		if self.extDebug: self.debugLog(u'didDeviceCommPropertyChange called')
	# 		
	# 		# Check if it is necessary to restart device, return True if that's the case
	# 		
	# 		return False

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
		
		# Check if every notification is to be delivered, or by interval, and that interval is now exceeded
		send = False # whether or not to send notification
		
		if(len(catStates[u'lastNotificationTime']) > 0):
			if catProps[u'sendEvery'] == u'always':
				# Set to always send
				send = True
				self.debugLog(u'Notification category set to always send, will send now')
			else:
				# Notification category set to only send at given interval
				# Check when notification category was last sent/used
				self.debugLog(u'Notification category set to send every %s, need to check last sent time' % (catProps[u'sendEvery']))
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
					
				if strvartime.timeDiff(lastSent, 'now', 'seconds') >= intervalToSeconds[catProps[u'sendEvery']]:
					send = True
					self.debugLog(u'Notification category set to send every %s, Last notification sent %s. Will send notification now' % (catProps[u'sendEvery'], strvartime.prettyDate(lastSent)))
				else:
					self.debugLog(u'Notification category set to send every %s, Last notification sent %s. Will _not_ send notification now' % (catProps[u'sendEvery'], strvartime.prettyDate(lastSent)))
		else:
			self.debugLog(u'Notification category has never been sent before, will send now')
			send = True
			
		# Check on action level, that notification is to be sent (is not within specified interval frequency)
		variableNameStr = self.notificationVarPrefix + actionProps['identifier']
		if actionProps[u'sendEvery'] != u'always' and send: # a delivery frequency is set, need to check last time
			self.debugLog(u'Notification action set to send every %s, need to check last sent time' % (actionProps[u'sendEvery']))
			# Try to get value from variable
			try:
				notificationVar = indigo.variables[variableNameStr]
				if self.extDebug: self.debugLog(u'Notification variable value: %s' % (notificationVar.value))
				timeStr = notificationVar.value.rsplit(u'\t')[0]
				timeStamp = strvartime.strToTime(timeStr)
				if self.extDebug: self.debugLog(u'Notification action last sent: %s' % (timeStr))
				if strvartime.timeDiff(timeStamp, 'now', 'seconds') < intervalToSeconds[actionProps[u'sendEvery']]:
					# Interval/frequency has not been passed, will not send notification
					send = False
					self.debugLog(u'Notification action set to send every %s. Last notification sent %s. Will _not_ send notification now' % (actionProps[u'sendEvery'], strvartime.prettyDate(timeStamp)))
			except:
				if self.extDebug: self.debugLog(u'Could not get last sent time from variable, assume it hasn\'t been sent before and send notification')
		elif actionProps[u'sendEvery'] == u'always':
			self.debugLog(u'Notification action set to always send, no need to check time of last sent notification')
		else:
			self.debugLog(u'Determined by notification category last sent and set frequency that notification will not be sent, no need to check last sent time on action level')
		
		# Start sending notification
		growlsToSend = catProps[u'growlTypes'] # List given by notification category, will remove later based on presence
		emailsToSend = [] # Opposite logic, include later based on presence
		
		if send:
									
			#Make sure presence for persons is up to date
			self.debugLog(u'Notification category configured to use presence, updating presence status of persons')
			numPresent = self.personsUpdatePresence(True)
			self.debugLog(u'%i persons found to be present' % (numPresent))
			
			if numPresent == 0 and catProps[u'notifyPresent'] and not catProps[u'notifyAllIfNotPresent']:
				self.debugLog(u'Notify present only chosen, 0 persons will be notified as none are present')
			elif numPresent == 0 and catProps[u'notifyPresent'] and catProps[u'notifyAllIfNotPresent']:
				self.debugLog(u'Notify all if none are present chosen, none are present -> all will be notified')
			elif not catProps[u'notifyPresent']:
				self.debugLog(u'Notification based on presence disabled, all will be notified')
			elif catProps[u'notifyPresent']:
				self.debugLog(u'There are %i people present, those will be notified' % (numPresent))
		
			# Determine who to deliver to
			for person in catProps[u'deliverTo']:
				#if self.extDebug: self.debugLog(u'Person given by category: %s' % (str(person)))
				personDev = indigo.devices[int(person)]
				personProps = personDev.pluginProps
				personStates = personDev.states
				if personDev.enabled:
					if self.extDebug: self.debugLog(u'Person "%s" included by category, \nprops: %s\nstates: %s' % (personDev.name, str(personProps), str(personStates)))
					if (personStates[u'present'] and catProps[u'notifyPresent']) or (numPresent == 0 and catProps[u'notifyAllIfNotPresent']) or not catProps[u'notifyPresent']:
						# Include e-mail address
						self.debugLog(u'Person "%s" is to be notified, include e-mail "%s" in notification recipients' % (personDev.name, personProps[u'email']))
						if self.validateEmail(personProps[u'email']):
							emailsToSend.extend(personProps[u'email'])
						else:
							self.errorLog(u'Email address "%s" for person "%s" could not be validated' % (personProps[u'email'], personDev.name))
					else:
						self.debugLog(u'Person "%s" is not present, remove as notification recipient' % (personDev.name))
						# Exclude growl types for person
						for gt in personProps['growlTypes']:
							if gt in growlsToSend:
								growlsToSend.remove(gt)
								self.debugLog(u'Removed growl type %s from notifications, person "%s"' % (gt, personDev.name))
				else:
					self.debugLog(u'Person %s has been disabled, skipping notification' % (personDev.name))		
		
		# Update notification action variable if not sendEvery or if set in plugin config
		if actionProps[u'sendEvery'] != u'always' or self.alwaysUseVariables:
			variableNameStr = self.notificationVarPrefix + actionProps[u'identifier']
			self.debugLog(u'Setting to update variable "%s"' % (variableNameStr))
			# Check if variable exists
			if not variableNameStr in indigo.variables:
				# Variable does not exist, try to create it
				self.debugLog(u'Variable "%s" does not exist, creating it' % (variableNameStr))
				try:
					notificationVar = indigo.variable.create(variableNameStr, value=u'none', folder=self.varFolderId)
					self.debugLog(u'Created variable "%s" with id "%s"' % (variableNameStr, str(notificationVar.id)))
				except:
					self.errorLog(u'Could not create variable "%s" in folder "%s"' % (variableNameStr, self.varFolderName))
			else:
				# get variable
				try:
					notificationVar = indigo.variables[variableNameStr]
				except:
					self.errorLog(u'Could not get variable "%s"' % (variableNameStr))
			
			if self.extDebug: self.debugLog(u'notification log variable: %s' % (str(notificationVar)))
			# set variable value
			# Format: <Timestamp><tab><Notification text><tab><Notification category device id>
			# Indigo doesn't have a last changed attribute of the variable, so timestamp needs to be inserted
			try:
				self.debugLog(u'Setting value of variable "%s"' % (variableNameStr))
				varStr = strvartime.timeToStr() + u'\t' + actionProps[u'text'] + u'\t' + str(categoryDev.id)
				if self.extDebug: self.debugLog(u'varStr: %s' % (varStr))
				indigo.variable.updateValue(notificationVar, varStr)
				self.debugLog(u'Value of variable "%s" set to: %s' % (variableNameStr, varStr))
			except:
				self.errorLog(u'Could not update value of variable "%s"' % (variableNameStr))
				
		# Update device states			
		categoryDev.updateStateOnServer("lastNotificationTime", strvartime.timeToStr())
			
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
	# UI VALIDATION
	########################################	
				
	# Validate device configuration
	def validateDeviceConfigUi(self, valuesDict, typeId, devId):
		#  
		if self.extDebug: self.debugLog(u"validateDeviceConfigUi: typeId: %s  devId: %s valuesDict: %s" % (typeId, str(devId), str(valuesDict)))
		
		#FIX and clean this function
		
		dev = indigo.devices[devId]
		
# 		if valuesDict['enabled']:
# 			dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOn)
# 		else:
# 			dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOff)
			
		return (True, valuesDict)
		
	# Validate action configuration
	def validateActionConfigUi(self, valuesDict, typeId, devId):
		# 
		if self.extDebug: self.debugLog(u"validateActionConfigUi: typeId: %s  devId: %s  valuesDict: %s" % (typeId, str(devId), str(valuesDict)))
		return (True, valuesDict)
		
	# Validate plugin prefs changes:
	def validatePrefsConfigUi(self, valuesDict):
		if self.extDebug: self.debugLog("validatePrefsConfigUI valuesDict: %s" % str(valuesDict))
		return (True, valuesDict)
		
		
	# Catch changes to config prefs
	
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
		self.alwaysUseVariables = self.pluginPrefs.get(u'alwaysUseVariables',False)
		
		# DO VALIDATION
		self.pluginConfigErrorState = False
		

	########################################
	# CALLBACK METHODS
	########################################
	
	# Devices.XML notificationPerson
	def clearSelectionPresenceVariable(self, valuesDict, typeId, devId):
		valuesDict['presenceVariable'] = ''
		return valuesDict
	def clearSelectionLogVariable(self, valuesDict, typeId, devId):
		valuesDict['logVariable'] = ''
		return valuesDict
		
		
	########################################
	# OTHER FUNCTIONS
	###################
	
	
	# Validate e-mail addres:
	def validateEmail(self, emailStr):
		# FIX
		return True
		
	
	# Update presence state of persons
	
	# errorIfNotSuccessful :	Sometimes may be useful not to throw errors if presence variable is not set/in use
	
# 	def personsUpdatePresence( self, errorIfNotSuccessful = True ):
# 	
# 		self.debugLog(u'Update presence for "person" devices')
# 		i = 0 # Number of persons present
# 		# iterate through "person" devices"
# 		for dev in indigo.devices.iter(pluginId + u'.notificationPerson'):
# 			devProps = dev.pluginProps
# 			if self.extDebug: self.debugLog(u'"%s" person notification device pluginProps: %s' % (dev.name, str(devProps)))
# 			try:
# 				# Set state of presence based on variable given in device config UI
# 				presenceVar = indigo.variables[int(devProps['presenceVariable'])]
# 				dev.updateStateOnServer('present',presenceVar.getValue(bool, default=True))
# 				if presenceVar.getValue(bool, default=True): i = i + 1 # person is present
# 				self.debugLog(u'"%s" person device presence set to: %s' % (dev.name, str(presenceVar.getValue(bool, default=True))))
# 			except:
# 				if errorIfNotSuccessful: self.errorLog(u'Could not get presence of person "%s", please check settings. Presence set to true as default' % dev.name)
# 				# Most likely no variable for presence is given, set to being present as it's "safer" to receive notification than not
# 				dev.updateStateOnServer('present',True)
# 				i = i + 1
# 				self.debugLog(u'"%s" person device presence set to true as no real presence could be obtained from variable' % (dev.name))
# 		return i

	def personUpdatePresence( self, dev, errorIfNotSuccessful = True ):
		if self.extDebug: self.debugLog(u'personUpdatePresence called')
	
		devProps = dev.pluginProps
		if self.extDebug: self.debugLog(u'"%s" person notification device pluginProps: %s' % (dev.name, str(devProps)))

		# Check if presence variable is set
		if len(devProps[u'presenceVariable']) > 0:
			try:
				# Get value of indigo variable
				presenceVar = indigo.variables[int(devProps[u'presenceVariable'])]
				dev.updateStateOnServer(u'present', presenceVar.getValue(bool, default=True))
				self.debugLog(u'"%s" person device presence set to: %s' % (dev.name, str(presenceVar.getValue(bool, default=True))))
			except:
				if errorIfNotSuccessful: self.errorLog(u'Could not get presence of person "%s", please check settings. Presence set to true as default' % dev.name)
				# set presence to true, safest choice
				dev.updateStateOnServer(u'present',True)
				self.debugLog(u'"%s" person device presence set to true as no real presence could be obtained from variable' % (dev.name))
			dev.updateStateOnServer(u'usePresence', True)
		else:
			# Presence variable not set
			self.debugLog(u'"%s" person device presence has no presence variable specified, setting presence to unknown' % (dev.name))
			dev.updateStateOnServer(u'usePresence', False)
			dev.updateStateOnServer(u'present',None)
			
		if dev.states[u'present']:
			self.personPresentList[dev.id] = u'present'
		elif dev.id in self.personPresentList:
			del self.personPresentList[dev.id]
		self.numPersonPresent = len(self.personPresentList)
		
