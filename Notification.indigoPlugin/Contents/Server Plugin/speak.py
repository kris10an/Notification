#! /usr/bin/env python
# -*- coding: utf-8 -*-
####################
# Copyright (c) 2016, krishj. All rights reserved.
# http://www.indigodomo.com

import threading
#import sys
#import indigo


# http://www.tutorialspoint.com/python/python_multithreading.htm			
class speakNotificationThread (threading.Thread):
    def __init__(self, notification, beforeAG, afterAG):
        threading.Thread.__init__(self)
        self.notification = notification
        self.beforeAG = beforeAG
        self.afterAG = afterAG
        #self.nplugin = nplugin
    def run(self):
        indigo.server.log( "Starting speak thread--")
        speakNotification(self.notification, self.beforeAG, self.afterAG)
        #Plugin.speakNotification(self.notification, self.beforeAG, self.afterAG)
        indigo.server.log( "Exiting speak thread--")
        
def speakNotification(notification, beforeAG, afterAG):
	#self.debugLog(u'speakNotification called')
	if len(beforeAG) > 0:
		#ag1 = indigo.actionGroups[int(beforeAG)]
		indigo.actionGroup.execute(int(beforeAG))
	indigo.server.speak(notification, waitUntilDone=True)
	if len(afterAG) > 0:
		indigo.actionGroup.execute(int(afterAG))
		
speakNotification("Heisann dette er en test","","")