from Mooshimeter import *
import threading
import time

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
        # This block is filtering for UUID.  I know the UUID I want to connect to and will connect only to it.
        #if(m.sender == (0x9C,0xB4,0xA0,0x39,0xCD,0x20)):
        #if(m.sender == (0x9C,0xB4,0xA0,0x39,0xCD,0x20)):
        #if(m.sender == (0x6D,0x9D,0xA0,0x39,0xCD,0x20)):
        #if(m.sender == (0xA4,0xD3,0xCB,0x19,0x9E,0x68)):
        #if(m.sender == (0xCE,0xE6,0xCB,0x19,0x9E,0x68)):
        if(m.sender == (0x13,0x0F,0x8A,0xEA,0x4A,0x88)):
            main_meter = Mooshimeter(m)
            main_meter.connect()
            main_meter.loadTree()
    if main_meter == None:
        print "Didn't find our friend..."
        exit()
    # Wait for us to load the command tree
    while main_meter.tree.getNodeAtLongname('SAMPLING:TRIGGER')==None:
        BGWrapper.idle()
    # Unlock the meter by writing the correct CRC32 value
    # The CRC32 node's value is written when the tree is received
    main_meter.sendCommand('admin:crc32 '+str(main_meter.tree.getNodeAtLongname('admin:crc32').value))
    main_meter.sendCommand('sampling:rate 0')       # Rate 125Hz
    main_meter.sendCommand('sampling:depth 3')      # Depth 256
    main_meter.sendCommand('sampling:trigger 2')    # Trigger continuous
    main_meter.sendCommand('ch1:mapping 0')         # CH1 select current input
    main_meter.sendCommand('ch1:range_i 0')         # CH1 10A range
    main_meter.sendCommand('ch2:mapping 0')         # CH2 select voltage input
    main_meter.sendCommand('ch2:range_i 1')         # CH2 Voltage 600V range

    #main_meter.tree.getNodeAtLongname('')
    def printCH1Value(val):
        print "Received CH1: %f"%val
    def printCH2Value(val):
        print "Received CH2: %f"%val
    main_meter.attachCallback('ch1:value',printCH1Value)
    main_meter.attachCallback('ch2:value',printCH2Value)

    last_heartbeat_time = time.time()

    while True:
        # This call checks the serial port and processes new data
        BGWrapper.idle()
        if time.time()-last_heartbeat_time > 10:
            last_heartbeat_time = time.time()
            main_meter.sendCommand('pcb_version')
        if len(cmd_queue):
            cmd = cmd_queue.pop(0)
            # Carve out a special case for disconnect
            if cmd=='XXX':
                print "Disconnecting..."
                main_meter.disconnect()
            else:
                main_meter.sendCommand(cmd)