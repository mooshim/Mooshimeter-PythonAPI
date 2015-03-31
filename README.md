# Mooshimeter-PythonAPI
A python API relying on the BLED112 to talk to the Mooshimeter

Example.py:
This script is meant to demonstrate use of the Mooshimeter and BGWrapper classes.
The script does the following:
- Scan for BLE devices
- Filter for Mooshimeters
- Connect to the Mooshimeter with strongest signal
- Configure the meter to read Voltage in 60V range and Current in 10A range
- Begin streaming data and printing the results to the console
