#!/usr/bin/env python
import os, sys
import datetime
import logging
import time
import pprint
import signal

from watcher import Watcher
#from nibworker import NibWorker
from ec2worker import EC2Worker
from hostworker import HostWorker
from robot import Robot

CFGFILE = './ec2_vms.conf'

def initLog(fn, logger):
    #handler = logging.handler.RotatingFileHandler(fn, maxBytes=10*1024*1024, backupCount=5)
    logger.setLevel(logging.DEBUG)
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    formatter = logging.Formatter('[%(asctime)s - %(filename)s:%(lineno)s] - %(message)s')
    ch.setFormatter(formatter)
    logger.addHandler(ch)
    
    fh = logging.FileHandler('./logs/' + fn + '.log')
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(formatter)
    logger.addHandler(fh)
    return logger

def main():
    Watcher()
    rawlogger = logging.getLogger(__file__)
    logger = initLog(__file__, rawlogger)    
    
#    ec2worker = EC2Worker(conf=CFGFILE)
#    ec2worker.setLogger(logger)
#    ec2worker.connect_ec2()
#    vms, k = ec2worker.powerOnVMs()

    vms = ['ec2-107-23-11-238.compute-1.amazonaws.com']
    k = '/opt/ec2/opsvm/Ruibin-keypair.pem'
#    k = None 
    
    hostOps = {}
    for vm in vms:
        logger.debug("Prepare testing on %s", vm)
        hw = HostWorker(conf=CFGFILE, hostname=vm, rsakey=k)
        raw = logging.getLogger(vm)
        hlog = initLog(vm, raw)
        hw.setLogger(hlog)
        hostOps[vm] =  hw

    #logger.debug(pprint.pformat(hostOps))

    threads = []
    for vm, hw in hostOps.items():
        try:
            logger.debug("Launch testing on %s", vm)
            hwt = Robot(hw.superAction, vm) 
            hwt.daemon = True
            hwt.start()
            time.sleep(1)
        except Exception, e:
            logger.debug("Error: unable to start thread %s...", e)
        else:
            threads.append(hwt)

    for t in threads:
        t.join()

    #ec2worker.termAllVMs()
 
    return 0

if __name__ == '__main__':
    sys.exit(main());

