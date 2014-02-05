#!/usr/bin/env python
import os, sys

import time
import boto
from boto.exception import EC2ResponseError
from utility import configSectionMap
import pprint
import datetime
import threading
from robot import Robot

class EC2Worker:
    # Launch shell after instance boot up 
    USER_DEFINE_SCRIPTS = """ 
                            #!/bin/bash
                            echo 'I am coming' > /tmp/dummy.txt
                          """

    def setLogger(self, logger):
        self.logger = logger
        
    
    def _log(self, msg, *args, **kwargs):
        if self.logger != None:
            self.logger.debug(msg, *args, **kwargs)


    def __init__(self, conf):
        secDict = configSectionMap(conf, 'SecurityKey')
        self.access_key = secDict['AWSAccessKeyId'.lower()]
        self.secret_key = secDict['AWSSecretKey'.lower()]
        
        instDict = configSectionMap(conf, 'Instances')
        self.image_id = instDict['ImageID'.lower()]
        self.min_count = instDict['MinCount'.lower()]
        self.max_count = instDict['MaxCount'.lower()]
        self.keypair= instDict['KeyPair'.lower()]
        self.instance_type = instDict['InstanceType'.lower()]

        self.vmHostNames = []
        self._lock = threading.Lock()

    def _find_placements(self, instance_type):
        zones = []
        past_time = datetime.datetime.now() - datetime.timedelta(hours=24)
        default_zone = "us-east-1a"
        for zone in self.ec2Obj.get_all_zones():
            self._log("Query Zone %s state %s", zone, zone.state)
            if zone.state in ["available"]:
                spotList = self.ec2Obj.get_spot_price_history(instance_type=instance_type,
                                                    end_time=past_time.isoformat(),
                                                    availability_zone=zone.name) 
                #self._log(pprint.pformat(spotList))
                if len(spotList) > 0:
                    zones.append(zone.name)
        if len(zones) == 0:
            zones.append(default_zone)
        
        self._log(pprint.pformat(zones))
    
        #zones.sort(reverse=True)
        return zones[0]

    def connect_ec2(self):
        self.ec2Obj = boto.connect_ec2(self.access_key, self.secret_key) 
        self._log(pprint.pformat(self.ec2Obj))
        self.key_file = os.path.join(os.path.abspath('.'), self.keypair) + '.pem'
        if not os.path.isfile(self.key_file):
            self._log("Create key pair %s...", self.key_file)
            key_pair = self.ec2Obj.create_key_pair(self.keypair)
            key_pair.save('./')


    def _close_ec2(self):
        self._log("Close ec2 connection")
        self.ec2Obj.close()


    def _pingVM(self, vmInstance):
        status = vmInstance.update()
        while status != 'running' and status != 'terminated':
            self._log("Instance %s status %s...", vmInstance.id, status)
            time.sleep(10)
            status = vmInstance.update()
        self._log("New instance %s has been running...", vmInstance.public_dns_name)
        self._lock.acquire()
        self.vmHostNames.append(vmInstance.public_dns_name)
        self._lock.release()

    def powerOnVMs(self):
        self._log("Get an available placement...")
        placement = self._find_placements(self.instance_type)

        self._log("AMI id %s, Launch all instances on %s...", self.image_id, placement)
        resObj = self.ec2Obj.run_instances(image_id = self.image_id,
                                    min_count = self.min_count,
                                    max_count = self.max_count,
                                    key_name = self.keypair,
                                    instance_type = self.instance_type,
                                    placement = placement,
                                    user_data = self.USER_DEFINE_SCRIPTS)

        vmInsts = resObj.instances
        #self._log(pprint.pformat(vmInsts))
        threads = []
        for inst in vmInsts:
            try:
                t = Robot(self._pingVM, inst)
                t.start()
                time.sleep(1)
            except Exception, e:
                self._log("Error: unable to start thread %s...", e)
            else:
                threads.append(t)

        for t in threads:
            t.join()

        return self.vmHostNames, self.key_file
        
    def termAllVMs(self):
        res = self.ec2Obj.get_all_instances()
        if not res:
            self._log("Terminate all instances %d", len(insts)) 
            ids = []
            for i in res.instances:
                ids.append(i)
            self.ec2Obj.terminate_instances(instance_ids=ids)
        self._close_ec2()


