#!/usr/bin/env python3

'''
Report pve-zsync jobs status to Zabbix.
'''

import json
import argparse
from datetime import datetime
from socket import getfqdn
from subprocess import call


class zsync:
    def __init__(self, statefile):
        self.statefile = statefile
        self.replnames = []
        self.replnames_json = []
        self.hostname = getfqdn()
        with open(self.statefile, "r") as config:
                try:
                    self.replicas = json.load(config)
                except ValueError as e:
                    print(e)
        for source, names in self.replicas.items():
            for name, config in names.items():
                repl = {}
                repl['{#REPLICA}'] = name
                self.replnames.append(name)
                self.replnames_json.append(repl)

    def discover(self):
        '''
        Make a zabbix-compatible json with pve-zsync jobs names
        '''
        print(json.dumps(
            {'data': self.replnames_json},
            indent=4,
            separators=(',', ':'))
            )

    def write_status(self):
        '''
        Write file with pve-zsync jobs stats
        '''
        with open('/tmp/zsync.status.dat', 'w') as statusfile:
            for source, replica in self.replicas.items():
                for replname, param in replica.items():
                    statusfile.write(
                     '{0} zsync.lsync[{1}] {2}\n'
                     .format(
                         self.hostname,
                         replname,
                         zsync.calculate_lag(param['lsync'])
                         )
                     )
                    statusfile.write(
                     '{0} zsync.state[{1}] {2}\n'
                     .format(
                         self.hostname,
                         replname,
                         param['state']
                         )
                     )

    def send(self):
        '''
        Send data to zabbix trapper
        '''
        with open("/tmp/zsync-zbx.log", 'a') as log:
            call([
                'zabbix_sender',
                '-c',
                '/etc/zabbix/zabbix_agentd.conf',
                '-i',
                '/tmp/zsync.status.dat'],
                stdout=log)
        print("1")

    def calculate_lag(lsync):
        '''
        Calculate time delta since last job run
        '''
        datefmt = "%Y-%m-%d_%H:%M:%S"
        if lsync == 0:
            return 0
        else:
            return (datetime.now() - datetime.strptime(lsync, datefmt)).seconds



parser = argparse.ArgumentParser()
parser.add_argument("--discover", action="store_true",
                    help="return a list of pve-zsync jobs "
                    "in zabbix discovery format")
parser.add_argument("--send", action="store_true",
                    help="send data via zabbix_sender to zabbix trapper")
args = parser.parse_args()

jobs = zsync(statefile = "sync_state")
if args.discover:
    jobs.discover()
elif args.send:
    jobs.write_status()
    jobs.send()
else:
    parser.print_help()
