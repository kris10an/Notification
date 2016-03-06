#! /usr/bin/env python
# -*- coding: utf-8 -*-
####################
# Copyright (c) 2016, krishj. All rights reserved.
# http://www.indigodomo.com

import indigo

import os
import sys
import time

# Note the "indigo" module is automatically imported and made available inside
# our global name space by the host process.

################################################################################
class Plugin(indigo.PluginBase):
	########################################
	def __init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs):
		indigo.PluginBase.__init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs)
		self.debug = pluginPrefs.get("debugLog", False)
		self.pluginLog = pluginPrefs.get("pluginLog", True)

	########################################
	def __del__(self):
		indigo.PluginBase.__del__(self)

	########################################
	def startup(self):
		self.debugLog(u"Startup called")

	########################################
	def shutdown(self):
		self.debugLog(u"shutdown called")
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
				self.sleep(120)
		except self.StopThread:
			pass

	########################################
	# Actions defined in MenuItems.xml:
	####################

	########################################
	# Methods defined for notificationPerson


	########################################
	# Validate device configuration
	########################################
	def validateDeviceConfigUi(self, valuesDict, typeId, devId):
		#  
		self.debugLog(u"validateDeviceConfigUi: typeId: %s  devId: %s" % (typeId, str(devId)))
		if typeId == "scene":
			if "memberDeviceList" in valuesDict:
				valuesDict["memberDeviceList"] = ""
			if "sourceDeviceMenu" in valuesDict:
				valuesDict["sourceDeviceMenu"] = ""
		return (True, valuesDict)
		
	########################################
	# Validate action configuration
	########################################
	def validateActionConfigUi(self, valuesDict, typeId, devId):
		# 
		self.debugLog(u"validateActionConfigUi: typeId: %s  devId: %s  valuesDict: %s" % (typeId, str(devId), str(valuesDict)))
		return (True, valuesDict)
		
	########################################
	# Validate plugin prefs changes:
	####################
	def validatePrefsConfigUi(self, valuesDict):
		self.debugLog("valuesDict: %s" % str(valuesDict))
		errorsDict = indigo.Dict()
		if len(errorsDict) > 0:
			return (False, valuesDict, errorsDict)
		return (True, valuesDict)
