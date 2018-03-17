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

class LogWriter(object):
    def __init__(self,logfile):
        self.logfile = logfile
        self.val_dict = {}
    def __addReadingForMeter(self,meter,val,channel):
        uuid = meter.getUUIDString()
        val_pair = self.val_dict.get(uuid,None)
        if val_pair is None:
            val_pair = [None,None]
        val_pair[channel] = val
        if not (None in val_pair):
            t = time.time()
            logstr = "%d %.3f %f %f\n"%(meter.p.conn_handle, t,val_pair[0],val_pair[1])
            print logstr
            logfile.write(logstr)
            logfile.flush()
            #reset
            del self.val_dict[uuid]
        else:
            self.val_dict[uuid] = val_pair
    def writeCh1(self, meter, val):
        self.__addReadingForMeter(meter,val,0)
    def writeCh2(self, meter, val):
        self.__addReadingForMeter(meter,val,1)

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

    settings_file = file('settings.txt','r')
    settings = [line.strip() for line in settings_file.readlines()]
    # Filter out comments and empties
    settings = [line for line in settings if (line!='' and line[0] != '#')]
    settings_file.close()

    for m in meters:
        for line in settings:
            m.sendCommand(line)
        m.sendCommand('sampling:trigger 2')    # Trigger continuous
        writer = LogWriter(logfile)
        m.attachCallback('ch1:value',writer.writeCh1)
        m.attachCallback('ch2:value',writer.writeCh2)

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