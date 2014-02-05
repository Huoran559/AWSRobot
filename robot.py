#!/usr/bin/env python

import threading 

class Robot(threading.Thread):
    
    def setLogger(self, logger):
        self.logger = logger

    def _log(self, msg, *args, **kwargs):
        if self.logger != None:
            self.logger.debug(msg, *args, **kwargs)


    def __init__(self, callback, obj):
        threading.Thread.__init__(self)
        self.callback = callback        
        self.objdata = obj

    def run(self):
        self.callback(self.objdata)
