from Mooshimeter import *
import threading
import time
import serial

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
    # Set up the lower level to talk to a buspirate
    port = "COM10"
    try:
        ser = serial.Serial(port=port, baudrate=115200, timeout=0)
        # flush buffers
        ser.flushInput()
        ser.flushOutput()
    except serial.SerialException as e:
        print "\n================================================================"
        print "Port error (name='%s', baud='%ld'): %s" % (port, 115200, e)
        print "================================================================"
        exit(2)

    # We're talking to a bus pirate.  Set it up to read hacked Mooshimeter UART through SD
    def sendAndWait(payload):
        ser.write(payload+'\n')
        time.sleep(0.05)
    sendAndWait('#') #Reset
    sendAndWait('m') #mode
    sendAndWait('3') #uart
    sendAndWait('9') #115200
    sendAndWait('1') #8 bit, no parity
    sendAndWait('1') #1 stop bit
    sendAndWait('1') #Receive polarity idle high
    sendAndWait('2') #Transmit idle asserted (no hiz)
    sendAndWait('(1)') #start bridge macro
    sendAndWait('y') #Yes we're sure we want to start the bridge macro


    inputthread = InputThread()
    inputthread.start()
    cmd_queue = []
    def addToQueue(s):
        cmd_queue.append(s)
    inputthread.cb = addToQueue
    main_meter = Mooshimeter(ser)

    class MeterInputThread(threading.Thread):
        def __init__(self):
            super(MeterInputThread, self).__init__()
        def run(self):
            while 1:
                bytes = ser.inWaiting()
                if bytes:
                    s = ser.read(bytes)
                    main_meter.receiveFromMeter(map(ord,s))
    meter_thread = MeterInputThread()
    meter_thread.start()

    #main_meter.loadTree()
    # Wait for us to load the command tree
    while main_meter.tree.getNodeAtLongname('SAMPLING:TRIGGER')==None:
        time.sleep(1)
        main_meter.loadTree()
    # Unlock the meter by writing the correct CRC32 value
    # The CRC32 node's value is written when the tree is received
    main_meter.sendCommand('admin:crc32 '+str(main_meter.tree.getNodeAtLongname('admin:crc32').value))
    main_meter.sendCommand('sampling:rate 0')       # Rate 125Hz
    main_meter.sendCommand('sampling:depth 3')      # Depth 256
    main_meter.sendCommand('ch1:mapping 0')         # CH1 select current input
    main_meter.sendCommand('ch1:range_i 0')         # CH1 10A range
    main_meter.sendCommand('ch2:mapping 0')         # CH2 select voltage input
    main_meter.sendCommand('ch2:range_i 1')         # CH2 Voltage 600V range
    #main_meter.sendCommand('log:on 2')         # CH2 Voltage 600V range

    main_meter.sendCommand('sampling:trigger 3')    # Trigger trickle

    #main_meter.tree.getNodeAtLongname('')

    last_heartbeat_time = time.time()
    samples_in_row = 0

    def printCH1Value(val):
        pass
        #print "Received CH1: %f"%val
    def printCH2Value(val):
        global last_heartbeat_time
        global samples_in_row
        new_time = time.time()
        dtms = (new_time-last_heartbeat_time)*1000
        if dtms < 100:
            samples_in_row+=1
        else:
            samples_in_row = 0;
        print "dt: %0.1fms : N : %d"%(dtms,samples_in_row)
        last_heartbeat_time = new_time
        print "Received CH2: %f"%val
    main_meter.attachCallback('ch1:value',printCH1Value)
    main_meter.attachCallback('ch2:value',printCH2Value)

    while True:
        if len(cmd_queue):
            cmd = cmd_queue.pop(0)
            # Carve out a special case for disconnect
            if cmd=='XXX':
                pass
            else:
                main_meter.sendCommand(cmd)