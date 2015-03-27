import bglib
import serial
import time
from UUID import *

# This module is designed to be used like a singleton class
# It wraps the functions of bglib in an easier to use way

ser = 0
ble = bglib.BGLib()
ble.packet_mode = False
ble.debug = False

#global definitions
uuid_service = [0x28, 0x00]  # 0x2800


#UTILITY CLASSES

class Characteristic(object):
    def __init__(self, parent, handle, uuid):
        """
        :param parent: a Peripheral instance
        :param args: args returned by ble_evt_attclient_find_information_found
        :return:
        """
        self.p = parent
        self.handle = handle
        self.uuid   = uuid
        self.byte_value = []
    def pack(self):
        """
        Subclasses should override this to serialize any instance members
        that need to go in to self.byte_value
        :return:
        """
        pass
    def unpack(self):
        """
        Subclasses should override this to unserialize any instance members
        from self.byte_value
        :return:
        """
        pass
    def write(self):
        self.pack()
        self.p.writeByHandle(self.handle,self.byte_value)
    def read(self):
        self.byte_value = self.p.readByHandle(self.handle)
        self.unpack()
    def __hash__(self):
        return self.handle
    def __str__(self):
        return str(self.handle)+":\t"+str(self.uuid)

class Peripheral(object):
    def __init__(self, args):
        """
        This is meant to be initialized from a ble_evt_gap_scan_response
        :param args: args passed to ble_evt_gap_scan_response
        :return:
        """
        self.sender = tuple(args['sender'])
        self.rssi = args['rssi']
        self.atype = args['address_type']
        self.conn_handle = -1
        self.chars = {}

        ad_services = []
        this_field = []
        bytes_left = 0
        for b in args['data']:
            if bytes_left == 0:
                bytes_left = b
                this_field = []
            else:
                this_field.append(b)
                bytes_left = bytes_left - 1
                if bytes_left == 0:
                    if this_field[0] == 0x02 or this_field[0] == 0x03: # partial or complete list of 16-bit UUIDs
                        for i in xrange((len(this_field) - 1) / 2):
                            ad_services.append(this_field[-1 - i*2 : -3 - i*2 : -1])
                    if this_field[0] == 0x04 or this_field[0] == 0x05: # partial or complete list of 32-bit UUIDs
                        for i in xrange((len(this_field) - 1) / 4):
                            ad_services.append(this_field[-1 - i*4 : -5 - i*4 : -1])
                    if this_field[0] == 0x06 or this_field[0] == 0x07: # partial or complete list of 128-bit UUIDs
                        for i in xrange((len(this_field) - 1) / 16):
                            ad_services.append(this_field[-1 - i*16 : -17 - i*16 : -1])
        l=[UUID(s) for s in ad_services]
        self.ad_services = tuple(l)
    def connect(self):
        self.conn_handle = connect(self)
    def discover(self):
        groups = discoverServiceGroups(self.conn_handle)
        print "Service Groups:"
        for group in groups:
            print UUID(group['uuid'])
        for group in groups:
            new_group = discoverCharacteristics(self.conn_handle,group['start'],group['end'])
            for c in new_group:
                # FIXME: For some reason the UUIDs are backwards
                c['uuid'].reverse()
                new_c = Characteristic(self,c['chrhandle'],UUID(c['uuid']))
                self.chars[new_c.handle] = new_c
                print new_c
    def findHandleForUUID(self,uuid):
        rval = []
        for c in self.chars.values():
            if c.uuid == uuid:
                rval.append(c)
        if len(rval) != 1:
            raise
        return rval[0]
    def readByHandle(self,char_handle):
        return read(self.conn_handle,char_handle)
    def writeByHandle(self,char_handle,payload):
        return write(self.conn_handle,char_handle,payload)
    def read(self,uuid):
        return self.readByHandle(self.findHandleForUUID(uuid))
    def write(self,uuid,payload):
        return self.writeByHandle(self.findHandleForUUID(uuid),payload)
    def enableNotify(self,uuid,enable):
        # We need to find the characteristic configuration for the provided UUID
        notify_uuid = UUID(0x2902)
        test_handle = self.findHandleForUUID(uuid) + 1
        while True:
            if test_handle-uuid > 3:
                # FIXME: I'm not sure what the error criteria should be, but if we are trying to enable
                # notifications for a characteristic that won't accept it we need to throw an error
                raise
            if self.chars[test_handle].uuid == notify_uuid:
                break
            test_handle += 1
        #test_handle now points at the characteristic config
        payload = 0
        if(enable):
            payload = (1,0)
        else:
            payload = (0,0)
        return self.writeByHandle(test_handle,payload)
    def __eq__(self, other):
        return self.sender == other.sender
    def __str__(self):
        s = ""
        l = ["%02X:"%self.sender[i] for i in range(6)]
        s+= "".join(l)
        s+= "\t%d"%self.rssi
        for service in self.ad_services:
            s+="\t"
            s+=str(service)
        return s
    def __repr__(self):
        return self.__str__()

#Public facing API

def initialize(port="COM4"):
    global ser
    if not ser:
        try:
            ser = serial.Serial(port=port, baudrate=115200, timeout=0)
            # flush buffers
            ser.flushInput()
            ser.flushOutput()
            disconnect()
            stopScan()
        except serial.SerialException as e:
            print "\n================================================================"
            print "Port error (name='%s', baud='%ld'): %s" % (port, 115200, e)
            print "================================================================"
            exit(2)

def startScan():
    # set scan parameters
    ble.send_command(ser, ble.ble_cmd_gap_set_scan_parameters(0xC8, 0xC8, 1))
    ble.check_activity(ser)
    # start scanning now
    ble.send_command(ser, ble.ble_cmd_gap_discover(1))
    ble.check_activity(ser)

def stopScan():
    ble.send_command(ser, ble.ble_cmd_gap_end_procedure())
    ble.check_activity(ser)

def scan(duration,stop_after=0):
    results = []
    def scan_response_handler(bglib_instance, args):
        found=False
        for resp in results:
            if tuple(args['sender']) == resp.sender:
                resp.rssi = args['rssi']
                found=True
        if not found:
            results.append(Peripheral(args))
    ble.ble_evt_gap_scan_response += scan_response_handler
    start_time = time.time()
    startScan()
    while time.time()-start_time < duration and (not stop_after or len(results) < stop_after):
        ble.check_activity(ser)
    stopScan()
    ble.ble_evt_gap_scan_response -= scan_response_handler
    return results

def connect(scan_result):
    #Connects and returns connection handle
    sr = scan_result
    # Connection intervals have units of 1.25ms
    ble.send_command(ser, ble.ble_cmd_gap_connect_direct(sr.sender, sr.atype, 30, 60, 0x100, 0))
    # Check for the command response
    ble.check_activity(ser)
    # Wait for connection state change
    # TODO: timeout?
    result = []
    def cb(bglib_instance, args):
        if (args['flags'] & 0x05) == 0x05:
            print "Connected to %s" % ':'.join(['%02X' % b for b in args['address'][::-1]])
            print "Interval: %dms"%(args['conn_interval']/1.25)
            result.append(args['connection'])
    ble.ble_evt_connection_status += cb
    while len(result) == 0:
        ble.check_activity(ser)
    ble.ble_evt_connection_status -= cb
    return result[0]

def discoverServiceGroups(conn):
        ble.send_command(ser, ble.ble_cmd_attclient_read_by_group_type(conn, 0x0001, 0xFFFF, list(reversed(uuid_service))))
        # Get command response
        ble.check_activity(ser)
        service_groups = []
        finish = []
        def found_cb(bglib_instance, args):
            service_groups.append(args)
        def finished_cb(bglib_instance, args):
            finish.append(0)
        ble.ble_evt_attclient_group_found += found_cb
        ble.ble_evt_attclient_procedure_completed += finished_cb
        while not len(finish):
            ble.check_activity(ser)
        ble.ble_evt_attclient_group_found -= found_cb
        ble.ble_evt_attclient_procedure_completed -= finished_cb
        return service_groups

def discoverCharacteristics(conn, handle_start, handle_end):
        ble.send_command(ser, ble.ble_cmd_attclient_find_information(conn, handle_start, handle_end))
        # Get command response
        ble.check_activity(ser)
        chars = []
        finish = []
        def found_cb(bglib_instance, args):
            chars.append(args)
        def finished_cb(bglib_instance, args):
            finish.append(0)
        ble.ble_evt_attclient_find_information_found += found_cb
        ble.ble_evt_attclient_procedure_completed += finished_cb
        while not len(finish):
            ble.check_activity(ser)
        ble.ble_evt_attclient_find_information_found -= found_cb
        ble.ble_evt_attclient_procedure_completed -= finished_cb
        return chars

def disconnect():
    ble.send_command(ser, ble.ble_cmd_connection_disconnect(0))
    ble.check_activity(ser)

def read(conn, handle):
    ble.send_command(ser, ble.ble_cmd_attclient_read_by_handle(conn,handle))
    result  = []
    payload = []
    fail = []
    def resultHandler(bglib_instance, args):
        result.append(args['result'])
    def payloadHandler(bglib_instance, args):
        payload.append(args['value'])
    def failHandler(bglib_instance, args):
        fail.append(0)
    ble.ble_rsp_attclient_read_by_handle += resultHandler
    ble.ble_evt_attclient_attribute_value += payloadHandler
    ble.ble_evt_attclient_procedure_completed += failHandler
    while 1:
        ble.check_activity(ser)
        if len(result) and result[0]:
            #There was a read error
            break
        elif len(fail):
            #Command was processed correctly but we still failed
            break
        elif len(payload):
            break
    ble.ble_rsp_attclient_read_by_handle -= resultHandler
    ble.ble_evt_attclient_attribute_value -= payloadHandler
    ble.ble_evt_attclient_procedure_completed -= failHandler
    if result[0] or len(fail):
        return []
    return payload[0]

def write(conn, handle, value):
    ble.send_command(ser, ble.ble_cmd_attclient_attribute_write(conn,handle,value))
    ble.check_activity(ser)

def enableNotify(conn, handle, enable):
    pass
    #ble.send_command(ser, ble.ble_cmd_attclient_attribute_write(connection_handle, att_handle_measurement_ccc, [0x01, 0x00]))
    ble.check_activity(ser)

# add handler for BGAPI timeout condition (hopefully won't happen)
def timeoutHandler(bglib_instance,args):
    print "TIMEOUT"
    exit(1)
ble.on_timeout += timeoutHandler

if __name__ == '__main__':
    initialize()
    scan_results = scan(3)
    if len(scan_results) == 0:
        print "No devices found"
        exit(0)
    closest = scan_results[0]
    for s in scan_results:
        print s
        if s.rssi > closest.rssi:
            closest = s
    closest.connect()
    closest.discover()