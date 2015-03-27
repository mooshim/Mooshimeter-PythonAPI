import BGWrapper
import struct
from UUID import *

class BytePack:
    """
    Helper class to pack and unpack integers and floats from a buffer
    """
    def __init__(self,bytebuf=[]):
        self.i = 0
        self.bytes = bytebuf[:]
    def putByte(self,v):
        self.bytes.append(v)
    def put(self,v,b=1):
        if type(v) == float:
            v = struct.unpack("bbbb",struct.pack("f",v))
            for e in v:
                self.putByte(e)
        elif type(v) == int:
            while b:
                self.putByte(v&0xFF)
                v >>= 8
                b -= 1
        else:
            raise
    def get(self,b=1,t=int):
        if t == int:
            r = 0
            s = 0
            while b:
                r += self.bytes[self.i] << s
                s += 8
                self.i += 1
                b -= 1
            return r
        elif t==float:
            r = struct.unpack("f",struct.pack("bbbb",*self.bytes[self.i:self.i+4]))
            self.i += 4
            return r

class MeterSettings(BGWrapper.Characteristic):
    def __init__(self, parent, handle, uuid):
        """
        :param other: a BGWrapper.Characteristic
        :return:
        """
        super(MeterSettings,self).__init__(parent, handle, uuid)
        self.present_meter_state = 0
        self.target_meter_state  = 0
        self.trigger_setting     = 0
        self.trigger_x_offset    = 0
        self.trigger_crossing    = 0
        self.measure_settings    = 0
        self.calc_settings       = 0
        self.chset               = [0,0]
        self.adc_settings        = 0
    def pack(self):
        b = BytePack()
        b.put( self.present_meter_state )
        b.put( self.target_meter_state  )
        b.put( self.trigger_setting     )
        b.put( self.trigger_x_offset    ,2)
        b.put( self.trigger_crossing    ,3)
        b.put( self.measure_settings    )
        b.put( self.calc_settings       )
        b.put( self.chset[0]            )
        b.put( self.chset[1]            )
        b.put( self.adc_settings        )
        self.byte_value = b.bytes
    def unpack(self):
        b = BytePack(self.byte_value)
        self.present_meter_state = b.get( )
        self.target_meter_state  = b.get( )
        self.trigger_setting     = b.get( )
        self.trigger_x_offset    = b.get(2)
        self.trigger_crossing    = b.get(3)
        self.measure_settings    = b.get( )
        self.calc_settings       = b.get( )
        self.chset[0]            = b.get( )
        self.chset[1]            = b.get( )
        self.adc_settings        = b.get( )
class MeterLogSettings(BGWrapper.Characteristic):
    def __init__(self, parent, handle, uuid):
        """
        :param other: a BGWrapper.Characteristic
        :return:
        """
        super(MeterLogSettings,self).__init__(parent, handle, uuid)
        self.sd_present            = 0
        self.present_logging_state = 0
        self.logging_error         = 0
        self.file_number           = 0
        self.file_offset           = 0
        self.target_logging_state  = 0
        self.logging_period_ms     = 0
        self.logging_n_cycles      = 0
    def pack(self):
        b = BytePack()
        b.put( self.sd_present                  )
        b.put( self.present_logging_state       )
        b.put( self.logging_error               )
        b.put( self.file_number             , 2 )
        b.put( self.file_offset             , 4 )
        b.put( self.target_logging_state        )
        b.put( self.logging_period_ms       , 2 )
        b.put( self.logging_n_cycles        , 4 )
        self.byte_value = b.bytes
    def unpack(self):
        b = BytePack(self.byte_value)
        self.sd_present              = b.get( )
        self.present_logging_state   = b.get( )
        self.logging_error           = b.get( )
        self.file_number             = b.get(2)
        self.file_offset             = b.get(4)
        self.target_logging_state    = b.get( )
        self.logging_period_ms       = b.get(2)
        self.logging_n_cycles        = b.get( )
class MeterInfo(BGWrapper.Characteristic):
    def __init__(self, parent, handle, uuid):
        """
        :param other: a BGWrapper.Characteristic
        :return:
        """
        super(MeterInfo,self).__init__(parent, handle, uuid)
        self.pcb_version        = 0
        self.assembly_variant   = 0
        self.lot_number         = 0
        self.build_time         = 0
    def pack(self):
        b = BytePack()
        b.put(self.pcb_version           )
        b.put(self.assembly_variant      )
        b.put(self.lot_number        ,2  )
        b.put(self.build_time        ,4  )
        self.byte_value = b.bytes
    def unpack(self):
        b = BytePack(self.byte_value)
        self.pcb_version      = b.get(1)
        self.assembly_variant = b.get(1)
        self.lot_number       = b.get(2)
        self.build_time       = b.get(4)
class MeterSample(BGWrapper.Characteristic):
    def __init__(self, parent, handle, uuid):
        """
        :param other: a BGWrapper.Characteristic
        :return:
        """
        super(MeterSample,self).__init__(parent, handle, uuid)
        self.reading_lsb = [0,0]
        self.reading_ms  = [0,0]
    def pack(self):
        b = BytePack()
        b.put( self.reading_lsb[0],3)
        b.put( self.reading_lsb[1],3)
        b.put( self.reading_ms[0], t=float)
        b.put( self.reading_ms[1], t=float)
        self.byte_value = b.bytes
    def unpack(self):
        b = BytePack(self.byte_value)
        self.reading_lsb[0] = b.get(3)
        self.reading_lsb[1] = b.get(3)
        self.reading_ms[0]  = b.get(t=float)
        self.reading_ms[1]  = b.get(t=float)
class MeterName(BGWrapper.Characteristic):
        def __init__(self, parent, handle, uuid):
            """
            :param other: a BGWrapper.Characteristic
            :return:
            """
            super(MeterName,self).__init__(parent, handle, uuid)
            self.name = "Mooshimeter V.1"
        def pack(self):
            self.byte_value = [ord(c) for c in self.name]
        def unpack(self):
            str(bytearray(self.byte_value))
class Mooshimeter(object):
    class mUUID:
        """
        Static declarations of UUID values in the meter
        """
        METER_SERVICE      = UUID("1BC5FFA0-0200-62AB-E411-F254E005DBD4")
        METER_INFO         = UUID("1BC5FFA1-0200-62AB-E411-F254E005DBD4")
        METER_NAME         = UUID("1BC5FFA2-0200-62AB-E411-F254E005DBD4")
        METER_SETTINGS     = UUID("1BC5FFA3-0200-62AB-E411-F254E005DBD4")
        METER_LOG_SETTINGS = UUID("1BC5FFA4-0200-62AB-E411-F254E005DBD4")
        METER_UTC_TIME     = UUID("1BC5FFA5-0200-62AB-E411-F254E005DBD4")
        METER_SAMPLE       = UUID("1BC5FFA6-0200-62AB-E411-F254E005DBD4")
        METER_CH1BUF       = UUID("1BC5FFA7-0200-62AB-E411-F254E005DBD4")
        METER_CH2BUF       = UUID("1BC5FFA8-0200-62AB-E411-F254E005DBD4")
        METER_CAL          = UUID("1BC5FFA9-0200-62AB-E411-F254E005DBD4")
        METER_LOG_DATA     = UUID("1BC5FFAA-0200-62AB-E411-F254E005DBD4")
        METER_TEMP         = UUID("1BC5FFAB-0200-62AB-E411-F254E005DBD4")
        METER_BAT          = UUID("1BC5FFAC-0200-62AB-E411-F254E005DBD4")
        OAD_SERVICE_UUID   = UUID("1BC5FFC0-0200-62AB-E411-F254E005DBD4")
        OAD_IMAGE_IDENTIFY = UUID("1BC5FFC1-0200-62AB-E411-F254E005DBD4")
        OAD_IMAGE_BLOCK    = UUID("1BC5FFC2-0200-62AB-E411-F254E005DBD4")
        OAD_REBOOT         = UUID("1BC5FFC3-0200-62AB-E411-F254E005DBD4")

        _class_by_uuid = {
            METER_INFO:MeterInfo,
            METER_SETTINGS:MeterSettings,
            METER_LOG_SETTINGS:MeterLogSettings,
            METER_SAMPLE:MeterSample
        }

        def classForUUID(self,uuid):
            if self._class_by_uuid.has_key(uuid):
                return self._class_by_uuid[uuid]
            return 0

    def __init__(self, peripheral):
        """
        Initialized instance variables
        :param peripheral: a BGWrapper.Peripheral instance
        :return:
        """
        self.p = peripheral
        self.meter_info         = MeterInfo(       peripheral,0,self.mUUID.METER_INFO)
        self.meter_name         = MeterName(       peripheral,0,self.mUUID.METER_NAME)
        self.meter_settings     = MeterSettings(   peripheral,0,self.mUUID.METER_SETTINGS)
        self.meter_log_settings = MeterLogSettings(peripheral,0,self.mUUID.METER_LOG_SETTINGS)
        self.meter_sample       = MeterSample(     peripheral,0,self.mUUID.METER_SAMPLE)
    def connect(self):
        self.p.connect()
        self.p.discover()
        handles_by_uuid = dict((c.uuid,c.handle) for c in self.p.chars.values())
        def assignHandleAndRead(c):
            c.handle = handles_by_uuid[c.uuid]
            c.read()
        assignHandleAndRead(self.meter_info)
        assignHandleAndRead(self.meter_name)
        assignHandleAndRead(self.meter_settings)
        assignHandleAndRead(self.meter_log_settings)
        assignHandleAndRead(self.meter_sample)

if __name__=="__main__":
    BGWrapper.initialize()
    scan_results = BGWrapper.scan(3)
    meters = []
    for p in scan_results:
        if Mooshimeter.mUUID.METER_SERVICE in p.ad_services:
            meters.append(p)
    #meters = filter(lambda(p):Mooshimeter.mUUID.METER_SERVICE in p.ad_services, scan_results)
    if len(meters) == 0:
        print "No Mooshimeters found"
        exit(0)
    closest = meters[0]
    for s in meters:
        print s
        if s.rssi > closest.rssi:
            closest = s
    my_meter = Mooshimeter(closest)
    my_meter.connect()