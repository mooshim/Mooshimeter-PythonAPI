from Mooshimeter import *
import threading

class InputThread(threading.Thread):
    def __init__(self):
        super(InputThread, self).__init__()
        self.cb=None
    def run(self):
        while True:
            s = raw_input()
            if self.cb != None:
                self.cb(s)

"""
Example.py
This script is meant to demonstrate use of the Mooshimeter and BGWrapper classes.
The script does the following:
- Scan for BLE devices
- Filter for Mooshimeters
- Connect to the Mooshimeter with strongest signal
- Configure the meter to read Voltage in 60V range and Current in 10A range
- Begin streaming data and printing the results to the console
"""

if __name__=="__main__":
    # Set up the lower level to talk to a BLED112 in port COM4
    # REPLACE THIS WITH THE BLED112 PORT ON YOUR SYSTEM
    BGWrapper.initialize("COM4")
    inputthread = InputThread()
    inputthread.start()
    cmd_queue = []
    def addToQueue(s):
        cmd_queue.append(s)
    inputthread.cb = addToQueue
    # Scan for 3 seconds
    scan_results = BGWrapper.scan(3)
    # Filter for devices advertising the Mooshimeter service
    meters = filter(lambda(p):Mooshimeter.mUUID.METER_SERVICE in p.ad_services, scan_results)
    if len(meters) == 0:
        print "No Mooshimeters found"
        exit(0)
    # Display detected meters
    for m in meters:
        print m
    main_meter = None
    for m in meters:
        if(m.sender == (0x9C,0xB4,0xA0,0x39,0xCD,0x20)):
            main_meter = Mooshimeter(m)
            main_meter.connect()
            main_meter.loadTree()
    if main_meter == None:
        print "Didn't find our friend..."
        exit()
    # Wait for us to load the command tree
    while main_meter.tree.getNodeAtLongname('SAMPLING:TRIGGER')==None:
        BGWrapper.idle()
    #main_meter.sendCommand('sampling:depth 3')
    #main_meter.sendCommand('sampling:trigger 2')
    #main_meter.sendCommand('ch2:mapping:voltage:range 1')
    main_meter.sendCommand('ch2:m 3')
    main_meter.sendCommand('sh 1')
    main_meter.sendCommand('sh:r:r 4')
    #main_meter.sendCommand('ch1:m:c:a 0')
    #main_meter.sendCommand('ch2:m:v:a 0')
    main_meter.sendCommand('s:d 0')
    main_meter.sendCommand('s:t 2')
    main_meter.sendCommand('l:i 6')
    main_meter.sendCommand('l:o 1')
    while True:
        # This call checks the serial port and processes new data
        BGWrapper.idle()
        if len(cmd_queue):
            cmd = cmd_queue.pop(0)
            # Carve out a special case for disconnect
            if cmd=='XXX':
                main_meter.disconnect()
            else:
                main_meter.sendCommand(cmd)