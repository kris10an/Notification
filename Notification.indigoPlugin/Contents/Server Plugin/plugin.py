#! /usr/bin/env python
# -*- coding: utf-8 -*-
####################
# Copyright (c) 2016, krishj. All rights reserved.
# http://www.indigodomo.com

import indigo

import os
import sys
import time
import operator
from datetime import datetime
import strvartime
import csv

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
	
logFileHeadings = [
	u'Date',
	u'Time',
	u'Identifier',
	u'Notification',
	u'Log type',
	u'Title',
	u'Is error',
	u'Category',
	u'Persons',
	u'Number present',
	u'E-mail recipients',
	u'Growl types',
	u'Growl priority',
	u'Growl sticky',
	u'Variables' ]


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
		self.logFileDateFormat = pluginPrefs.get(u'logFileFormat','%Y-%m')
		
		# Error states
		self.pluginConfigErrorState = False # Whether or not plugin is in error state, due to faulty plugin config
		
		# Presets, not configurable
		self.notificationVarPrefix = u'_notification_'
		self.logDir = indigo.server.getInstallFolderPath() + u'/Logs/Notifications test/'
		self.logFileSuffix = u' Notifications.csv'
		#self.logFileDateFormat = u'%Y-%m-%d'
		
		# Device and variable lists
		self.personList = {} #dev.id : string
		self.personPresentList = {} # dev.id : string
		self.categoryList = {} # dev.id : string
		self.presenceVariableList = {} #var.id : dev.id
		self.numPersonPresent = 0
		
		# Threads
		self.threads = []

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
				
		# Check if log file dir exists
		if self.pluginLog:
			if not self.checkAndCreateLogFile():
				self.errorLog(u'Could not verify or create plugin log folder')
			else:
				self.debugLog(u'Verified plugin log folder and file. Log file: %s' % (self.logFile))
		else:
			self.debugLog(u'Plugin log disabled')
				
		self.debugLog(u'Subscribing to variable changes')
		indigo.variables.subscribeToChanges()

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
	# DEVICES Start and stop device communication, device updates
	########################################
	
	def deviceStartComm(self, dev):
		#self.debugLog(u'deviceStartComm called: %s' % (str(dev)))
		self.debugLog(u'deviceStartComm called, device %s' % (dev.name))
		
		if dev.deviceTypeId == u'notificationPerson':
			self.personUpdatePresence(dev)
			self.personList[dev.id] = 'active'		
		elif dev.deviceTypeId == u'notificationCategory':
			self.categoryList[dev.id] = 'active'	
			
		if self.extDebug:
			self.debugLog(u'personList: %s' % (str(self.personList)))
			self.debugLog(u'personPresentList: %s' % (str(self.personPresentList)))
			self.debugLog(u'numPersonPresent: %i' % (self.numPersonPresent))
			self.debugLog(u'categoryList: %s' % (str(self.categoryList)))
			self.debugLog(u'presenceVariableList: %s' % (str(self.presenceVariableList)))
			
	def deviceStopComm(self, dev):
		#if self.extDebug: self.debugLog(u'deviceStopComm called: %s' % (str(dev)))
		self.debugLog(u'deviceStopComm called, device %s' % (dev.name))
		
		if dev.deviceTypeId == u'notificationPerson':
			if dev.id in self.personList:
				del self.personList	[dev.id]
			if dev.id in self.personPresentList:
				del self.personPresentList[dev.id]
			self.numPersonPresent = len(self.personPresentList)
			self.debugLog(u'deviceStopComm update numPersonPresent: %i' % (self.numPersonPresent))
		elif dev.deviceTypeId == u'notificationCategory':
			if dev.id in self.categoryList:
				del self.categoryList[dev.id]
			
		
		if self.extDebug:
			self.debugLog(u'personList: %s' % (str(self.personList)))
			self.debugLog(u'personPresentList: %s' % (str(self.personPresentList)))
			self.debugLog(u'numPersonPresent: %i' % (self.numPersonPresent))
			self.debugLog(u'categoryList: %s' % (str(self.categoryList)))
		
	def deviceUpdated(self, origDev, newDev):
		# call the base's implementation first just to make sure all the right things happen elsewhere
		# FIX / CHECK should this be done or not?
		indigo.PluginBase.deviceUpdated(self, origDev, newDev)
		#if self.extDebug: self.debugLog(u'deviceUpdated called %s: \n\n\n***origDev:\n %s\n\n\n***newDev:\n %s' % (newDev.name, str(origDev), str(newDev)))
		#else:
		self.debugLog(u'deviceUpdated called %s' % (newDev.name))
		
		if origDev.deviceTypeId != newDev.deviceTypeId:
			self.debugLog(u'Device type changed, restarting device %s' % (newDev.name))
			# FIX still some error being thrown when changing device type
			self.deviceStopComm(newDev)
			if newDev.enabled:
				self.deviceStartComm(newDev)
			return
		
		if newDev.deviceTypeId == u'notificationPerson':
			if origDev.pluginProps[u'presenceVariable'] != newDev.pluginProps[u'presenceVariable']:
				self.personUpdatePresence(newDev)
			# FIX need to do something else?
		elif newDev.deviceTypeId == u'notificationCategory':
			# FIX need to do something else?
			pass
				
		# CHECK if this is necessary, or should be handled by Indigo server somehow
		if origDev.enabled != newDev.enabled:
			if newDev.enabled:
				self.deviceStartComm(newDev)
			else:
				self.deviceStopComm(newDev)

	########################################
	# Change to device, perform necessary actions
	########################################
	
	# FIX should this be implemented or not?@+
	# 	didDeviceCommPropertyChange(self, origDev, newDev):
	# 		if self.extDebug: self.debugLog(u'didDeviceCommPropertyChange called')
	# 		
	# 		# Check if it is necessary to restart device, return True if that's the case
	# 		
	# 		return False
	
	########################################
	# VARIABLES
	########################################
	
	def variableUpdated(self, origVar, newVar):
		
		if origVar.id in self.presenceVariableList:
			# call the base's implementation first just to make sure all the right things happen elsewhere
			# do it within if to save resources (??)
			indigo.PluginBase.variableUpdated(self, origVar, newVar)
			self.debugLog(u'variableUpdated called, %s' % (origVar.name))
			try:
				if self.presenceVariableList[origVar.id] in self.personList:
					dev = indigo.devices[self.presenceVariableList[origVar.id]]
					self.personUpdatePresence(dev)
					self.debugLog(u'variableUpdated called updatePersonPresence for "%s"' % (dev.name))
			except:
				self.errorLog(u'Could not find device to update presence for, variable "%s"' % (origVar.name))

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
		if ((not categoryDev.id in self.categoryList) or (not categoryDev.enabled)):
			self.errorLog(u'Notification category device "%s" invalid or disabled, skipping notification.\nNotification text: %s' % (categoryDev.name, action.text))
			return
			
		actionProps = action.props
		catProps = categoryDev.pluginProps
		catStates = categoryDev.states
		if self.extDebug: self.debugLog(u'Notification category "%s" plugin props: %s' % (categoryDev.name, str(catProps)))
		if self.extDebug: self.debugLog(u'Notification category "%s" states: %s' % (categoryDev.name, str(catStates)))
		
		# Check if every notification is to be delivered, or by interval, and that interval is now exceeded
		send = False # whether or not to send notification
		sent = False # whether or not notification has actually been sent
		sentOrLog = False # whether or not notification has actually been sent, or logged, or spoken etc.
		
		# Find the time to use for the notification
		notificationTime = datetime.now()
		
		# Set to default values if not specified
		if not u'sendEvery' in actionProps:
			actionProps[u'sendEvery'] = u'always'
		if not u'additionalRecipients' in actionProps:
			actionProps[u'additionalRecipients'] = u''
		if not u'title' in actionProps:
			actionProps[u'title'] = u''
		if not u'speak' in actionProps:
			actionProps[u'speak'] = u'default'
		if not u'logAsError' in actionProps:
			actionProps[u'logAsError'] = u'default'
		if not u'logType' in actionProps:
			actionProps[u'logType'] = catProps[u'logType']
		
		"""# Check first if at least one method for sending is selected, and not only logs
		if len(catProps[u'presentDeliveryMethod']) > 0 or len(catProps[u'nonPresentDeliveryMethod']) > 0:
			sendSelected = True
			self.debugLog(u'At least one method for sending out notification selected (excluding logs)')
			if self.extDebug:
				self.debugLog(u'presentDeliveryMethod:\n%s' % str(catProps[u'presentDeliveryMethod']))
				self.debugLog(u'nonPresentDeliveryMethod:\n%s' % str(catProps[u'nonPresentDeliveryMethod']))
		else: 
			sendSelected = False
			self.debugLog(u'No methods for sending out notification selected (excluding logs), will not send out notification')
		
		if sendSelected:"""
		
		# Check on category level whether to send, based on last notification time
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
				
				if strvartime.timeDiff(lastSent, notificationTime, 'seconds') >= intervalToSeconds[catProps[u'sendEvery']]:
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
				if strvartime.timeDiff(timeStamp, notificationTime, 'seconds') < intervalToSeconds[actionProps[u'sendEvery']]:
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
		notifyVars = []
		personNameArray = []
		variableNameArray = []
		personDevArray = []
		if self.extDebug: self.debugLog(u'growlsToSend:\n%s' % str(growlsToSend))
	
		if send:
								
			#Make sure presence for persons is up to date
			#self.debugLog(u'Notification category configured to use presence, updating presence status of persons')
			#numPresent = self.personsUpdatePresence(True)
			#self.debugLog(u'%i persons found to be present' % (numPresent))
			numPresent = self.numPersonPresent
			self.debugLog(u'%i persons indicated as present' % (numPresent))
			
			# Check if 'all' is selected as recipient
			if u'all' in catProps[u'deliverTo']:
				self.debugLog(u'All persons selected for delivery')
				personsList = self.personList
			else:
				personsList = catProps[u'deliverTo']
				
			if self.extDebug: self.debugLog(u'personsList: %s' % str(personsList))
			
			# Determine who to send out notifications to
			for personId in personsList:
				
				try:
					personDev = indigo.devices[int(personId)]
					personNameArray.append(personDev.name)
				except:
					self.errorLog(u'Could not get person device "%i", delivery of notification could not be retrieved.\nNotification text:%s' % (int(personId), actionProps[u'text']))
					continue
					
				personDevArray.append(personDev)
				
				# if option for "all if none present" is selected, handle all as present
				if catProps[u'notifyAllIfNonePresent'] and numPresent == 0:
					present = True
					self.debugLog(u'None are present but options for notifying all is selected, all will be notified')
				elif not catProps[u'notifyAllIfNonePresent'] and  numPresent == 0:
					present = personDev.states[u'present']
					self.debugLog(u'None are present and options for notifying all is not selected, none will be notified')
				else:
					present = personDev.states[u'present']
				
				# Remove growl/push notification from growl list, opposite logic from email
				if (not u'growl' in catProps[u'presentDeliveryMethod'] and not u'growl' in catProps[u'nonPresentDeliveryMethod']) or ((u'growl' in catProps[u'presentDeliveryMethod'] and not present) and (not u'growl' in catProps[u'nonPresentDeliveryMethod'])) or ((u'growl' in catProps[u'nonPresentDeliveryMethod']) and (not u'growl' in catProps[u'presentDeliveryMethod']) and present):
					# Logic:
						# If no growl delivery is selected
						# OR
						# Delivery to present persons is selected, but person is NOT present AND delivery to non-present persons is NOT selected
						# OR 
						# Delivery to non-present persons is selected AND Delivery to present persons is NOT selected AND person is present
					for growlType in personDev.pluginProps[u'growlTypes']:
						# if growl type is listed in category settings, send
						if growlType in growlsToSend:
							self.debugLog(u'Removing growl notification type "%s" for "%s", person is present: %r' % (growlType, personDev.name, present))
							growlsToSend.remove(growlType)
				elif self.extDebug: self.debugLog(u'Growl logic not triggered for person "%s"' % (personDev.name))
							
				# Add e-mail
				if (present and u'email' in catProps[u'presentDeliveryMethod']) or (not present and u'email' in catProps[u'nonPresentDeliveryMethod']):
					if len(personDev.pluginProps[u'email']) > 0:
						if self.validateEmail(personDev.pluginProps[u'email']):
							emailsToSend.append(personDev.pluginProps[u'email'])
							self.debugLog(u'Adding "%s" to e-mail recipients, e-mail address: %s' % (personDev.name, personDev.pluginProps[u'email']))	
						else:
							self.errorLog(u'Invalid e-mail address specified for "%s": %s' % (personDev.name, personDev.pluginProps[u'email']))
					else:
						self.debugLog(u'No e-mail address specified for "%s"' % (personDev.name))
				elif self.extDebug: self.debugLog(u'Email logic not triggered for person "%s"' % (personDev.name))
					
				# Add variable
				if (present and u'variable' in catProps[u'presentDeliveryMethod']) or (not present and u'variable' in catProps[u'nonPresentDeliveryMethod']):
					if len(personDev.pluginProps[u'logVariable']) > 0:
						try:
							notifyVar = indigo.variables[int(personDev.pluginProps[u'logVariable'])]
							self.debugLog(u'Adding variable notification for "%s", variable: %s' % (personDev.name, notifyVar.name))
							notifyVars.append(notifyVar.id)
							variableNameArray.append(notifyVar.name)
						except:
							self.errorLog(u'Could not get notification variable specified for "%s": %s' % (personDev.name, personDev.pluginProps[u'logVariable']))
					else:
						self.debugLog(u'No variable for notification specified for "%s"' % (personDev.name))
				elif self.extDebug: self.debugLog(u'Variable logic not triggered for person "%s"' % (personDev.name))
						
			if self.extDebug:
				self.debugLog(u'growlsToSend:\n%s' % str(growlsToSend))
				self.debugLog(u'emailsToSend:\n%s' % str(emailsToSend))
				self.debugLog(u'notifyVars:\n%s' % str(notifyVars))
				
			# Determine additional recipient given by category
			self.debugLog(u'Determine additional recipient given by notification category, regardless of presence etc.')
			if len(catProps[u'alwaysDeliverTo']) > 0:
				rcptArray = catProps[u'alwaysDeliverTo'].replace(u'\n',u'').split(u',')
				if self.extDebug: self.debugLog(u'rcptArray: %s' % (str(rcptArray)))
				for rcpt in rcptArray:
					rcpt = rcpt.split(u':')
					if rcpt[0].strip() == u'email':
						if self.validateEmail(rcpt[1].strip()):
							emailsToSend.append(rcpt[1].strip())
						else:
							self.errorLog(u'Invalid e-mail given as additional e-mail recipient for notification category "%s": "%s"' % (categoryDev.name, rcpt[1]))
					else:
						self.errorLog(u'Invalid delivery method "%s" spefified for additional receipients for notification category "%s". Valid options are: email' % (rcpt[0], categoryDev.name))
					
			# Determine additional recipient given by category
			self.debugLog(u'Determine additional recipient given by notification action, regardless of presence etc.')
			if len(actionProps[u'additionalRecipients']) > 0:
				rcptArray = actionProps[u'additionalRecipients'].replace(u'\n',u'').split(u',')
				if self.extDebug: self.debugLog(u'rcptArray: %s' % (str(rcptArray)))
				for rcpt in rcptArray:
					rcpt = rcpt.split(u':')
					if rcpt[0].strip() == u'email':
						if self.validateEmail(rcpt[1].strip()):
							emailsToSend.append(rcpt[1].strip())
						else:
							self.errorLog(u'Invalid e-mail given as additional e-mail recipient for notification action: "%s"' % (rcpt[1]))
					else:
						self.errorLog(u'Invalid delivery method "%s" spefified for additional receipients for notification action. Valid options are: email' % (rcpt[0]))
		
			# Find log type, title etc.
			if len(actionProps[u'logType']) > 0:
				logType = actionProps[u'logType']
			else:
				logType = catProps[u'logType']
			if len(actionProps[u'title']) > 0:
				title = actionProps[u'title']
				emailSubject = title
			else:
				title = logType
				emailSubject = 'Indigo ' + title
			identifier = actionProps[u'identifier']
			notificationText = self.substitute(actionProps[u'text'])
			emailBody = notificationText + '\n\nIdentifier: ' + identifier + '\nCategory: ' + categoryDev.name + '\nLog type: ' + logType
		
		
			# Start sending notifications
			# GROWL
			if len(growlsToSend) > 0:
				# remove possible duplicates
				growlsToSend = set(growlsToSend)
				if self.extDebug: self.debugLog(u'Starting sending growl notifications, growlsToSend: %s' % str(growlsToSend))
				growlPlugin = indigo.server.getPlugin("com.perceptiveautomation.indigoplugin.growl")		
				if growlPlugin.isEnabled():		
					for growlType in growlsToSend:
						self.debugLog(u'Growl notification type "%s" with title "%s" being sent' % (growlType,title))
						try:
							growlPlugin.executeAction("notify", props={'type':growlType, 'title':title, 'descString':notificationText, 'priority':catProps[u'growlPriority'], 'sticky':catProps[u'growlSticky']})
							sent = True
						except:
							self.errorLog(u'Could not send growl notification "%s" with title "%s"' % (growlType,title))
				else:
					self.errorLog(u'Growl Plugin is disabled, growl notifications could not be sent!\nNotification category: %s\nNotification text: %s' % (categoryDev.name, notificationText))
		
			# EMAIL
			if len(emailsToSend) > 0:
				# remove possible duplicates
				emailsToSend = set(emailsToSend)
				if self.extDebug: self.debugLog(u'Starting sending e-mail notifications, emailsToSend: %s' % str(emailsToSend))
				for rcpt in emailsToSend:
					self.debugLog(u'E-mail notification to %s with subject "%s" being sent' % (rcpt, emailSubject))
					indigo.server.sendEmailTo(rcpt, subject=emailSubject, body=emailBody)
					sent = True
				
			# VARIABLE
			if len(notifyVars) > 0:
				# remove possible duplicates
				notifyVars = set(notifyVars)
				if self.extDebug: self.debugLog(u'Starting writing variable notifications, notifyVars: %s' % str(notifyVars))
				for nVarId in notifyVars:
					try:
						nVar = indigo.variables[nVarId]
					except:
						self.errorLog(u'Could not get notification variable with id %i' % (nVarId))
					else:
						self.debugLog(u'Notification being written to variable %s' % (nVar.name))
						# First, set variable to nothing, make it possible to trigger off variable changes even if same notification
						# is sent two times in a row
						indigo.variable.updateValue(nVar,'')
						indigo.variable.updateValue(nVar,notificationText)
						sent = True

		# LOG AND SPEECH
		# Perform regardless of presence settings etc.
		sentOrLog = sent # start with initial value of sent variable
		
		# Check speech settings
		speech = False
		# Check if action has override settings
		if actionProps[u'speak'] == u'default':
			if self.extDebug: self.debugLog(u'Notification action set to use speech setting of category, checking category setting')
			# Check category settings
			if (u'speak' in catProps[u'nonPersonalDeliveryMethod']):
				if self.extDebug: self.debugLog(u'Speech selected in notification category')
				if catProps[u'speak'] == u'always':
					if self.extDebug: self.debugLog(u'Notification category set to always speak, speak enabled')
					speech = True
				elif catProps[u'speak'] == u'ifPresent':
					if numPresent > 0:
						if self.extDebug: self.debugLog(u'Notification category set to speak if someone present, %i persons present, speech enabled' % (numPresent))
						speech = True
					elif numPresent == 0:
						self.debugLog(u'Notification category set to speak if someone present, but no-one present, speech disabled')
						speech = False
					else:
						self.errorLog(u'Unexpected result when determining whether to speak notification category "%s" based on presence, speech enabled' % (categoryDev.name))
						speech = True
				else:
						self.errorLog(u'Unexpected setting for speech in notification category "%s", speech enabled' % (categoryDev.name))
						speech = True
			else:
				if self.extDebug: self.debugLog(u'Speech NOT selected in notification category, disabling speech')
				speech = False
		elif actionProps[u'speak'] == u'always':
			if self.extDebug: self.debugLog(u'Notification action set to always speak, overriding category setting')
			speech = True
		elif actionProps[u'speak'] == u'ifPresent':
			if numPresent > 0:
				if self.extDebug: self.debugLog(u'Notification action set to override category setting and speak if someone present -> enabling speech')
				speech = True
			else:
				self.debugLog(u'Notification action set to override category setting and speak if someone present -> disabling speech')
				speech = False
		elif actionProps[u'speak'] == u'never':
			self.debugLog(u'Notification action set to override category setting and never speak -> speech disabled')
			speech = False
		else:
			self.errorLog(u'Unexpected setting for speech in notification action, notification category "%s", speech enabled' % (categoryDev.name))
			speech = True
			
		# Perform speech
		if speech:
			self.debugLog(u'Speaking notification and waiting until finished')
			#thread.start_new_thread( speakNotification, (notificationText, catProps[u'beforeSpeakActionGroup'], catProps[u'afterSpeakActionGroup'] ) )
			#speakThread = speakNotificationThread(notificationText, catProps[u'beforeSpeakActionGroup'], catProps[u'afterSpeakActionGroup'] )
			#speakThread.start()
			#self.threads.append(speakThread)
			#speakThread.join()
			#if self.extDebug: self.debugLog(u'Thread for speech notification started')
			if len(catProps[u'beforeSpeakActionGroup']) > 0:
				try:
					indigo.actionGroup.execute(int(catProps[u'beforeSpeakActionGroup']))
				except:
					self.errorLog(u'Could not execute action group specified before speech')
			try:
				indigo.server.speak(notification, waitUntilDone=True)
			except:
				self.errorLog(u'Could not speak notification')
			if len(catProps[u'afterSpeakActionGroup']) > 0:
				try:
					indigo.actionGroup.execute(int(catProps[u'afterSpeakActionGroup']))
				except:
					self.errorLog(u'Could not execute action group specified after speech')
			sentOrLog = True
		
		# Indigo log and notification plugin log
		writeLog = False
		
		'''
		DISABLED, too complex user interface for this logic..
		# Check if action has override settings
		if actionProps[u'log'] == u'default':
			if self.extDebug: self.debugLog(u'Notification action set to use log setting of category, checking category setting')
			# Check category settings
			if (u'log' in catProps[u'nonPersonalDeliveryMethod'] or (u'notificationLog' in catProps[u'nonPersonalDeliveryMethod'] and self.pluginLog)):
				if self.extDebug: self.debugLog(u'Indigo log and/or Notification plugin log selected in notification category')
				if catProps[u'log'] == u'always':
					if self.extDebug: self.debugLog(u'Notification category set to always log, log enabled')
					writeLog = True
				elif catProps[u'log'] == u'ifPresent':
					if numPresent > 0:
						if self.extDebug: self.debugLog(u'Notification category set to log if someone present, %i persons present, log enabled' % (numPresent))
						writeLog = True
					elif numPresent == 0 and catProps[u'notifyAllIfNonePresent']:
						if self.extDebug: self.debugLog(u'Notification category set to log if someone present, no-one is present, but notify all if none present selected -> log enabled' % (numPresent))
						writeLog = True
					elif numPresent == 0:
						self.debugLog(u'Notification category set to log if someone present, but no-one present, log entry disabled')
						writeLog = False
					else:
						self.errorLog(u'Unexpected result when determining whether to log notification category "%s" based on presence, log entry enabled' % (categoryDev.name))
						writeLog = True
				else:
						self.errorLog(u'Unexpected setting for log in notification category "%s", log entry enabled' % (categoryDev.name))
						writeLog = True
			else:
				if self.extDebug: self.debugLog(u'Indigo log and/or Notification plugin log NOT selected in notification category (or plugin preferences), disabling log')
				writeLog = False
		elif actionProps[u'log'] == u'always':
			if self.extDebug: self.debugLog(u'Notification action set to always log, overriding category setting')
			writeLog = True
		elif actionProps[u'log'] == u'ifPresent':
			if numPresent > 0 or (numPresent == 0 and catProps[u'notifyAllIfNonePresent']):
				if self.extDebug: self.debugLog(u'Notification action set to override category setting and log if someone present -> enabling log entry')
				writeLog = True
			else:
				self.debugLog(u'Notification action set to override category setting and log if someone present -> disabling log entry')
				writeLog = False
		elif actionProps[u'log'] == u'never':
			self.debugLog(u'Notification action set to override category setting and never log -> log entry disabled')
			writeLog = False
		else:
			self.errorLog(u'Unexpected setting for log in notification action, notification category "%s", log entry enabled' % (categoryDev.name))
			writeLog = True'''
		
		# Check category settings
		if (u'log' in catProps[u'nonPersonalDeliveryMethod'] or (u'notificationLog' in catProps[u'nonPersonalDeliveryMethod'] and self.pluginLog)):
			if self.extDebug: self.debugLog(u'Indigo log and/or Notification plugin log selected in notification category')
			if catProps[u'log'] == u'always':
				if self.extDebug: self.debugLog(u'Notification category set to always log, log enabled')
				writeLog = True
			elif catProps[u'log'] == u'ifPresent':
				if numPresent > 0:
					if self.extDebug: self.debugLog(u'Notification category set to log if someone present, %i persons present, log enabled' % (numPresent))
					writeLog = True
				elif numPresent == 0 and catProps[u'notifyAllIfNonePresent']:
					if self.extDebug: self.debugLog(u'Notification category set to log if someone present, no-one is present, but notify all if none present selected -> log enabled' % (numPresent))
					writeLog = True
				elif numPresent == 0:
					self.debugLog(u'Notification category set to log if someone present, but no-one present, log entry disabled')
					writeLog = False
				else:
					self.errorLog(u'Unexpected result when determining whether to log notification category "%s" based on presence, log entry enabled' % (categoryDev.name))
					writeLog = True
			else:
					self.errorLog(u'Unexpected setting for log in notification category "%s", log entry enabled' % (categoryDev.name))
					writeLog = True
		else:
			if self.extDebug: self.debugLog(u'Indigo log and/or Notification plugin log NOT selected in notification category (or plugin preferences), disabling log')
			writeLog = False		
		
		# Start writing log entries
		if writeLog:
			# Check log As Error
			logAsError = False
			if actionProps[u'logAsError'] == u'default':
				# Use category setting
				logAsError = bool(catProps[u'logAsError'])
				if self.extDebug: self.debugLog(u'Notifcation action set to use log-as-error setting of category, log as error: %r' % (logAsError))
			elif actionProps[u'logAsError'] == u'true':
				logAsError = True
				if self.extDebug: self.debugLog(u'Notifcation action set to always log as error, enabling log as error')
			elif actionProps[u'logAsError'] == u'false':
				logAsError = False
				if self.extDebug: self.debugLog(u'Notifcation action set to not log as error, disabling log as error')
			else:
				self.errorLog(u'Unexpected setting of log as error, enabling log as error to be user')
				logAsError = True
		
			# Write Indigo log entry
			if u'log' in catProps[u'nonPersonalDeliveryMethod']:
				if len(actionProps[u'identifier']) > 0:
					logEntryStr = notificationText + u' (Identifier: ' + actionProps[u'identifier'] + u')'
				else:
					logEntryStr = notificationText
				self.debugLog(u'Making indigo log entry')
				indigo.server.log(notificationText, isError=logAsError, type=logType)
				sentOrLog = True
			
			# Write notification plugin log entry
			if u'notificationLog' in catProps[u'nonPersonalDeliveryMethod'] and self.pluginLog:
				self.debugLog(u'Making plugin log entry, file %s' % (self.logFile))

				logFileEntry = {
					u'Date'					: notificationTime.strftime('%Y-%m-%d'),
					u'Time'					: notificationTime.strftime('%H:%M:%S'),
					u'Identifier'			: identifier,
					u'Notification'			: notificationText,
					u'Log type'				: logType,
					u'Title'				: title,
					u'Is error'				: str(logAsError),
					u'Category'				: categoryDev.name,
					u'Persons'				: u', '.join(personNameArray),
					u'Number present'		: str(numPresent),
					u'E-mail recipients'	: u', '.join(emailsToSend),
					u'Growl types'			: u', '.join(growlsToSend),
					u'Growl priority'		: str(catProps[u'growlPriority']),
					u'Growl sticky'			: str(catProps[u'growlSticky']),
					u'Variables' 			: u', '.join(variableNameArray) }
					
				if self.extDebug: self.debugLog(u'Information for plugin log entry: %s' % (str(logFileEntry)))
				
				result = self.writeLogFile(logFileEntry)
				sentOrLog = True
				
				if result:
					self.debugLog(u'Plugin log entry made to %s' % (self.logFile))
			elif not self.pluginLog:
				self.debugLog(u'Notification plugin log has been disabled in plugin preferences')
			elif not u'notificationLog' in catProps[u'nonPersonalDeliveryMethod']:
				self.debugLog(u'Notification plugin log not selected in notification category, skipping')
			else:
				self.errorLog(u'Unexpected result when checking settings for notification plugin log, please check settings')
				
		else:
			self.debugLog(u'Making log entries for notification disabled, skipping both indigo and notification plugin log')
			
			# Check if 
		
		# Update notification action variable if not sendEvery or if set in plugin config
		# For now, variable and device states is updated if send=True, not if sent=True
		# Believe this is most correct, as log etc. might be written even if no persons are directly notified
		# 14.03: Changed to sentOrLog variable
		if (sentOrLog and actionProps[u'sendEvery'] != u'always') or self.alwaysUseVariables:
			variableNameStr = self.notificationVarPrefix + actionProps[u'identifier']
			if self.extDebug: self.debugLog(u'Setting to update variable "%s"' % (variableNameStr))
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
				if self.extDebug: self.debugLog(u'Setting value of variable "%s"' % (variableNameStr))
				varStr = strvartime.timeToStr() + u'\t' + actionProps[u'text'] + u'\t' + str(categoryDev.id)
				if self.extDebug: self.debugLog(u'varStr: %s' % (varStr))
				indigo.variable.updateValue(notificationVar, varStr)
				self.debugLog(u'Value of variable "%s" set to: %s' % (variableNameStr, varStr))
			except:
				self.errorLog(u'Could not update value of variable "%s"' % (variableNameStr))
				
		# Update device states	
		if sentOrLog:
			for personDev in personDevArray:
				# FIX is there a way to update all states simultaneously? Tried below, but does not work
				self.debugLog(u'Updating device states for "%s"' % (personDev.name))
				'''personDev.states[u'lastNotificationTime'] = strvartime.timeToStr(notificationTime)
				personDev.states[u'lastNotificationTime.ui'] = strvartime.timeToStr(notificationTime, format='short')
				personDev.states[u'lastNotificationIdentifier'] = identifier
				personDev.states[u'lastNotificationText'] = notificationText
				personDev.states[u'lastNotificationCategory'] = categoryDev.name
				personDev.replaceOnServer()
				personDev.stateListOrDisplayStateIdChanged()'''
				personDev.updateStateOnServer(u'lastNotificationTime', strvartime.timeToStr(notificationTime), uiValue=strvartime.timeToStr(notificationTime, format='short'))
				personDev.updateStateOnServer(u'lastNotificationIdentifier', identifier)
				personDev.updateStateOnServer(u'lastNotificationText', notificationText)
				personDev.updateStateOnServer(u'lastNotificationCategory', categoryDev.name)
				personDev.stateListOrDisplayStateIdChanged()
				
			self.debugLog(u'Update notification category device states')
			categoryDev.updateStateOnServer(u'lastNotificationTime', strvartime.timeToStr(notificationTime), uiValue=strvartime.timeToStr(notificationTime, format='short'))
			categoryDev.updateStateOnServer(u'lastNotificationIdentifier', identifier)
			categoryDev.updateStateOnServer(u'lastNotificationText', notificationText)
			categoryDev.updateStateOnServer(u'lastLogType', logType)
			categoryDev.updateStateOnServer(u'lastNotifiedPersons', u', '.join(personNameArray))
			categoryDev.stateListOrDisplayStateIdChanged()
			
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
		
		
	# def getDeviceConfigUiValues():
	# possible to get values of device config UI?	
		
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
		self.logFileDateFormat = self.pluginPrefs.get(u'logFileFormat','%Y-%m')
		
		# DO VALIDATION
		self.pluginConfigErrorState = False
		

	########################################
	# CALLBACK METHODS
	########################################
	
	# Devices.XML notificationPerson
	def clearSelectionPresenceVariable(self, valuesDict, typeId, devId):
		valuesDict[u'presenceVariable'] = ''
		return valuesDict
	def clearSelectionLogVariable(self, valuesDict, typeId, devId):
		valuesDict[u'logVariable'] = ''
		return valuesDict
	
	# Devices.XML notificationCategory
	def clearSelectionCategoryActionGroups(self, valuesDict, typeId, devId):
		valuesDict[u'beforeSpeakActionGroup'] = ''
		valuesDict[u'afterSpeakActionGroup'] = ''
		return valuesDict
		
	# List generators, definitions:
	
	def nonPersonalDeliveryMethodsList(self, filter="", valuesDict=None, typeId="", targetId=0):
		self.debugLog(u'nonPersonalDeliveryMethodsList called')
		myArray = [
			(u"log",u"Indigo Log"),
			(u"notificationLog",u"Notification plugin log"),
			(u"speak",u"Speak")]
		return myArray
		
	def personalDeliveryMethodsList(self, filter="", valuesDict=None, typeId="", targetId=0):
		self.debugLog(u'personalDeliveryMethodsList called')
		myArray = [
			(u"email",u"E-mail"),
			(u"growl",u"Push (Growl)"),
			(u"variable","Write to variable")]
		return myArray
		
	def personDeviceListIncludingAll(self, filter="", valuesDict=None, typeId="", targetId=0):
		self.debugLog(u'personDeviceListIncludingAll called')
		# return list of person devices to Device Config, including option for all
		devArray = []
		for dev in indigo.devices.iter(pluginId + u'.notificationPerson'):
			# (could use self.personList, but want to include disabled devices in dialog
			devArray.append ( (dev.id,dev.name) )
		sortedDevArray = sorted ( devArray, key = operator.itemgetter(1))
		sortedDevArray.insert (0, (u"all",u"All persons"))
		if self.extDebug: self.debugLog(u'sortedDevArray:\n%s' % str(sortedDevArray))
		return sortedDevArray


	'''	########################################
	# SEND NOTIFICATION FUNCTIONS
	###################
	
		
	def notifySendGrowl():
		pass
		
	def notifySendEmail():
		pass
		
	def notifyToVariable():
		pass	'''

		
	########################################
	# OTHER FUNCTIONS
	###################
	
	
	# Validate e-mail addres:
	def validateEmail(self, emailStr):
		# FIX something here
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
				self.presenceVariableList[presenceVar.id] = dev.id
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
		
		# refresh Indigo, not sure if this is necessary?
		dev.stateListOrDisplayStateIdChanged()
		
	def checkAndCreateLogDir(self, dirname):
		# credit http://stackoverflow.com/questions/12517451/python-automatically-creating-directories-with-file-output
		if not os.path.exists(dirname):
			try:
				os.makedirs(dirname)
				return True
			except OSError as exc: # Guard against race condition
				if exc.errno != errno.EEXIST:
					raise	
				return False
		else:
			return True
		
	def checkAndCreateLogFile(self):
	
		self.logFile = self.getLogFileName()
		if self.extDebug: self.debugLog(u'checkAndCreateLogFile, self.logFile: %s' % (self.logFile))
		dirResult = self.checkAndCreateLogDir(self.logDir)
		if self.extDebug: self.debugLog(u'checkAndCreateLogFile, dirResult: %r' % (dirResult))
		if dirResult:
			if os.path.isfile(self.logFile):
				if self.extDebug: self.debugLog(u'checkAndCreateLogFile, log file already exists')
				return True
			else:
				#try:
				fp = open(self.logFile, 'wb')
				#fp.write(u'\ufeff'.encode('utf8')) # BOM (optional...Excel needs it to open UTF-8 file properly)
				writer = DictWriterEx(fp, logFileHeadings, dialect='excel', delimiter=';')
				writer.writeheader()
				fp.close()
				self.debugLog(u'checkAndCreateLogFile, headers written to log file')
				return True
				#except:
				#	self.errorLog(u'Could not create or write to plugin log file %s' % (self.logFile))
				#	return False
		else:
			return False
			
	def getLogFileName(self):
	
		try:
			logFileDatePart = datetime.strftime(datetime.now(), self.logFileDateFormat)
		except:
			self.errorLog(u'Could not get date part of notification plugin log file, check settings')
			return False
		else:
			logFileStr = self.logDir + logFileDatePart + self.logFileSuffix
			return logFileStr
			
	def writeLogFile(self, wDict):
	
		if self.checkAndCreateLogFile():
			if self.extDebug: self.debugLog(u'Checked log file OK')
			#try:
			if self.extDebug: self.debugLog(u'Writing to plugin log file: %s' % (str(wDict)))
			fp = open(self.logFile, 'ab')
			writer = DictWriterEx(fp, logFileHeadings, dialect='excel', delimiter=';')
			writer.writerow(dict((k, v.encode('utf-8')) for k, v in wDict.iteritems()))
			fp.close()
			return True
			#xcept:
			#	self.errorLog(u'Could not write notification to plugin log file %s' % (self.logFile))
			#	return False
		else:
			self.errorLog(u'Could not get or create plugin log file %s' % (self.logFile))
			return False
		
# from http://stackoverflow.com/questions/5838605/python-dictwriter-writing-utf-8-encoded-csv-files
class DictWriterEx(csv.DictWriter):
    def writeheader(self):
        header = dict(zip(self.fieldnames, self.fieldnames))
        self.writerow(header)
