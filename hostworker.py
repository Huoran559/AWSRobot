#!/usr/bin/env python

import os, sys
import paramiko
import select
import socket
from utility import configSectionMap
import datetime
import time
import logging

class HostWorker:

    def setLogger(self, logger):
        self.logger = logger

    def enableSelfLogger(self):
        logger = logging.getLogger()
        logger.setLevel(logging.DEBUG)
        ch = logging.StreamHandler()
        ch.setLevel(logging.DEBUG)
        formatter = logging.Formatter('[%(asctime)s - %(filename)s:%(lineno)s] - %(message)s')
        ch.setFormatter(formatter)
        logger.addHandler(ch)
        
        fh = logging.FileHandler('./logs/' + self.hostname + '.log')
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(formatter)
        logger.addHandler(fh)
        self.logger = logger
        
    
    def _log(self, msg, *args, **kwargs):
        if self.logger != None:
            self.logger.debug(msg, *args, **kwargs)
    
    def __init__(self, conf, hostname, rsakey):
        self.hostname = hostname
        self.rsakey = rsakey
        excDict = configSectionMap(conf, 'VM')
        self.vmConf = excDict['VMConf'.lower()]
        self.loginName = excDict['LoginName'.lower()]
        self.passwd = excDict['Password'.lower()]
        self.rmtWorkDir = excDict['RemoteWorkDir'.lower()]
        self.rmtResultFile = excDict['ResultFile'.lower()]
        self.transportFile = excDict['LocalFile'.lower()].replace(' ', '').split(',')
        
        self.rmtLauncher = excDict['RemoteLaunch'.lower()]
        self.resultsDir = excDict['ResultsDir'.lower()]
        

    def _connect(self):
        self._log("Login %s with user %s and rsafile %s...", 
                        self.hostname, self.loginName, self.rsakey)
        
        self.client = paramiko.SSHClient()
        
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        iloop = 1
        while True:
            try:
                self._log("Trying connect %d times to %s...", iloop, self.hostname)
                if self.rsakey is not None:
                    self._log("connect with key %s...", self.rsakey)
                    self.client.connect(hostname=self.hostname, username=self.loginName,
                            key_filename=self.rsakey, timeout=300)
                else:
                    self._log("connect with user %s and password %s...", self.loginName, self.passwd)
                    self.client.connect(hostname=self.hostname, username=self.loginName,
                            password=self.passwd, timeout=300)
                
            except Exception, e:
                self._log("Failed ssh to %s, %s", self.hostname, e)
                iloop += 1
                time.sleep(10)
            else:
                self._log("Thanks GOD, connecting...")
                break;

        

    def superAction(self, args):
        self._connect()
        self.preAction()
        self.doAction()
        self.postAction()


    def preAction(self):

        bullets = []
        
        for f in self.transportFile:
            self._log(f)
            local_path = os.path.join(os.path.abspath('.'), f)
            fname = os.path.basename(local_path)
            remote_path = os.path.join(self.rmtWorkDir, fname) 
            bullets.append((local_path, remote_path))
        
        self._postFiles(bullets)

    def _postFiles(self, files):
        self._log("Transport necessary files to host %s...", self.hostname)

        sftp = self.client.open_sftp()
        for l, r in files:
            self._log("Copy file %s to remote %s", l, r)
            sftp.put(l, r)
        sftp.close()
        self._log("Transport completed...")

    def _getFiles(self, files):
        self._log("Collect necessary files from host %s...", self.hostname)
            
        sftp = self.client.open_sftp()
        for r, l in files:
            self._log("Get file %s from remote %s", l, r)
            sftp.get(r, l)
        sftp.close()
        self._log("Collect completed...")


    def _execLongOps(self, cmd):
        trans = self.client.get_transport()
        session = trans.open_session()
        session.exec_command(cmd)
        session.setblocking(0)
        while True:
            #self._log('session.recv_ready() = %s', str(session.recv_ready()))
            #self._log('session.exit_status_ready() = %s', str(session.exit_status_ready()))
            if session.recv_ready():
                data = session.recv(1024)
                self._log("%s", data)
                #print '{0}: {1}'.format(self.hostname, data)
#                pass

            if session.recv_stderr_ready():
                #self._log("Session error: %s", session.recv_stderr(1024))
                pass

            if session.exit_status_ready():
                break

            time.sleep(1)
        session.close()


    def doAction(self):
        rmtExecute = os.path.join(self.rmtWorkDir, self.rmtLauncher)
        self._log("Remote execute %s on %s...", rmtExecute, self.hostname)
        sin, sout, serr = self.client.exec_command('chmod +x ' + rmtExecute)
        self._log("Execute errput: %s", serr.readlines())

#        rmtExecute = """
#                sudo yum -y groupinstall 'Development Tools'
#                     """
        rmtExecute = rmtExecute + ' ' + self.rmtWorkDir
        self._execLongOps(rmtExecute)
        self._log("Remote calling done on %s...", self.hostname)


    def postAction(self):
        self._log("Collect all data from %s...", self.hostname)
        ts = datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")

        if not os.path.exists(self.resultsDir):
            os.makedirs(self.resultsDir, 0755)
        rest = self.hostname + '-' + ts + '.tar.gz'
        recvFiles = []
        rmt = self.rmtResultFile
        dst = self.resultsDir + '/' + rest
        recvFiles.append((rmt, dst))
         
        self._getFiles(recvFiles)
        self._log("Complete all test on %s...", self.hostname)
        
        self.client.close()



