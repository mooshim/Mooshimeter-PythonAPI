import BGWrapper
from Mooshimeter import Mooshimeter

from operator import attrgetter

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
    def connectToMeterAndStream(p):
        m = Mooshimeter(p)
        m.connect()
        # Apply some default settings
        m.meter_settings.setBufferDepth(32) #samples
        m.meter_settings.setSampleRate(125) #Hz
        m.meter_settings.setHVRange(60) #volts
        # Calculate the mean
        m.meter_settings.calc_settings |= m.meter_settings.METER_CALC_SETTINGS_MEAN
        # Calculate the RMS as well
        m.meter_settings.calc_settings |= m.meter_settings.METER_CALC_SETTINGS_MS
        # Ensure we don't accidentally tell the Mooshimeter to reboot
        m.meter_settings.target_meter_state = m.meter_settings.present_meter_state
        # Send the ADC settings
        m.meter_settings.write()
        # Set the meter state
        m.meter_settings.target_meter_state = m.meter_settings.METER_RUNNING
        def notifyCB():
            #This will be called every time a new sample is received
            print "Connection: ", m.p.conn_handle
            print "%.4f"%m.lsbToNativeUnits(m.meter_sample.reading_lsb[0],0), m.getUnits(0)
            print "%.4f"%m.lsbToNativeUnits(m.meter_sample.reading_lsb[1],1), m.getUnits(1)
        # Enable streaming
        m.meter_sample.enableNotify(True,notifyCB)
        m.meter_settings.write()

    # Connect to the meter with the strongest signal
    meters = sorted(meters, key=attrgetter('rssi'),reverse=True)
    connectToMeterAndStream(meters[0])
    while True:
        # This call checks the serial port and processes new data
        BGWrapper.idle()