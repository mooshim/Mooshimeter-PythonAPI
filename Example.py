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
    scan_results = BGWrapper.scan(5)
    # Filter for devices advertising the Mooshimeter service
    results_wrapped = filter(lambda(p):Mooshimeter.mUUID.METER_SERVICE in p.ad_services, scan_results)
    if len(results_wrapped) == 0:
        print "No Mooshimeters found"
        exit(0)
    meters = []
    for r in results_wrapped:
        # Use a statement like the below to filter for UUID
        #if(r.sender == (0x9C,0xB4,0xA0,0x39,0xCD,0x20)):
        m = Mooshimeter(r)
        m.connect()
        m.loadTree()
        # Wait for us to load the command tree
        while m.tree.getNodeAtLongname('SAMPLING:TRIGGER')==None:
            BGWrapper.idle()
        # Unlock the meter by writing the correct CRC32 value
        # The CRC32 node's value is written when the tree is received
        m.sendCommand('admin:crc32 '+str(m.tree.getNodeAtLongname('admin:crc32').value))
        meters.append(m)

    # All the meters are unlocked.  Prepare the logfile.
    logfile = file('log.txt', 'w+')
    logfile.write("Log started at: %f\n"%(time.time()))

    for m in meters:
        m.sendCommand('sampling:rate 0')       # Rate 125Hz
        m.sendCommand('sampling:depth 3')      # Depth 256
        m.sendCommand('ch1:mapping 0')         # CH1 select current input
        m.sendCommand('ch1:range_i 0')         # CH1 10A range
        m.sendCommand('ch2:mapping 0')         # CH2 select voltage input
        m.sendCommand('ch2:range_i 1')         # CH2 Voltage 600V range
        m.sendCommand('sampling:trigger 2')    # Trigger continuous
        def printCH1Value(meter,val):
            s = meter.p.getUUIDString()
            logfile.write("%s 1: %f\n"%(s,val))
            print "%s CH1: %f"%(s,val)
        def printCH2Value(meter,val):
            s = meter.p.getUUIDString()
            logfile.write("%s 2: %f\n"%(s,val))
            print "%s CH2: %f"%(s,val)
        m.attachCallback('ch1:value',printCH1Value)
        m.attachCallback('ch2:value',printCH2Value)

    last_heartbeat_time = time.time()

    while True:
        # This call checks the serial port and processes new data
        BGWrapper.idle()
        if time.time()-last_heartbeat_time > 10:
            last_heartbeat_time = time.time()
            for m in meters:
                m.sendCommand('pcb_version')
            logfile.flush()
        if len(cmd_queue):
            cmd = cmd_queue.pop(0)
            # Carve out a special case for disconnect
            if cmd=='XXX':
                print "Disconnecting..."
                for m in meters:
                    m.disconnect()
            else:
                for m in meters:
                    m.sendCommand(cmd)