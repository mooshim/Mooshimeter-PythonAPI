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
            v = struct.unpack("BBBB",struct.pack("f",v))
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
            r = struct.unpack("f",struct.pack("BBBB",*self.bytes[self.i:self.i+4]))
            self.i += 4
            return r[0]

class MeterSettings(BGWrapper.Characteristic):
    METER_SHUTDOWN  = 0
    METER_STANDBY   = 1
    METER_PAUSED    = 2
    METER_RUNNING   = 3
    METER_HIBERNATE = 4

    METER_MEASURE_SETTINGS_ISRC_ON         = 0x01
    METER_MEASURE_SETTINGS_ISRC_LVL        = 0x02
    METER_MEASURE_SETTINGS_ACTIVE_PULLDOWN = 0x04

    METER_CALC_SETTINGS_DEPTH_LOG2 = 0x0F
    METER_CALC_SETTINGS_MEAN       = 0x10
    METER_CALC_SETTINGS_ONESHOT    = 0x20
    METER_CALC_SETTINGS_MS         = 0x40

    ADC_SETTINGS_SAMPLERATE_MASK = 0x07
    ADC_SETTINGS_GPIO_MASK = 0x30

    METER_CH_SETTINGS_PGA_MASK = 0x70
    METER_CH_SETTINGS_INPUT_MASK = 0x0F

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
    def setSampleRate(self,hz):
        """
        :param hz: Sample rate in hz.  Valid options are 125,250,500,1000,2000,4000,8000
        :return:
        """
        bval = 0
        srate = 125
        while srate < hz:
            srate *= 2
            bval  += 1
        self.adc_settings &=~self.ADC_SETTINGS_SAMPLERATE_MASK
        self.adc_settings |= bval
    def setBufferDepth(self,samples):
        """
        :param samples: Number of samples in  a single buffer.  Valid values are powers of 2 up to and including 256
        :return:
        """
        bval = 0
        while 1<<bval < samples:
            bval+=1
        self.calc_settings &= ~self.METER_CALC_SETTINGS_DEPTH_LOG2
        self.calc_settings |= bval
    def setHVRange(self,range_v):
        """
        :param range: Voltage range of the high voltage channels.  Valid values are 1.2, 60 or 600.
        :return:
        """
        self.adc_settings &=~self.ADC_SETTINGS_GPIO_MASK
        if range_v <= 1.2:
            pass
        elif range_v <= 60:
            self.adc_settings |= 0x10
        elif range_v <= 600:
            self.adc_settings |= 0x20
        return
    def attachChannelToAux(self,ch):
        """
        :param ch: Channel to attach to aux input.  Can be 0 or 1
        :return:
        """
        self.chset[ch] &=~self.METER_CH_SETTINGS_INPUT_MASK
        self.chset[ch] |= 0x09
    def detachChannelFromAux(self,ch):
        """
        :param ch: Channel to attach to aux input.  Can be 0 or 1
        :return:
        """
        self.chset[ch] &=~self.METER_CH_SETTINGS_INPUT_MASK
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
        def assignHandleAndRead(c):
            self.p.replaceCharacteristic(c)
            c.read()
        assignHandleAndRead(self.meter_info)
        assignHandleAndRead(self.meter_name)
        assignHandleAndRead(self.meter_settings)
        assignHandleAndRead(self.meter_log_settings)
        assignHandleAndRead(self.meter_sample)
    def disconnect(self):
        self.p.disconnect()
    #################
    # Data conversion
    #################

        private double getEnob(final int channel) {
        // Return a rough appoximation of the ENOB of the channel
        // For the purposes of figuring out how many digits to display
        // Based on ADS1292 datasheet and some special sauce.
        // And empirical measurement of CH1 (which is super noisy due to chopper)
        final double base_enob_table[] = {
                20.10,
                19.58,
                19.11,
                18.49,
                17.36,
                14.91,
                12.53};
        final int pga_gain_table[] = {6,1,2,3,4,8,12};
        final int samplerate_setting =meter_settings.adc_settings & ADC_SETTINGS_SAMPLERATE_MASK;
        final int buffer_depth_log2 = meter_settings.calc_settings & METER_CALC_SETTINGS_DEPTH_LOG2;
        double enob = base_enob_table[ samplerate_setting ];
        int pga_setting = meter_settings.chset[channel];
        pga_setting &= METER_CH_SETTINGS_PGA_MASK;
        pga_setting >>= 4;
        int pga_gain = pga_gain_table[pga_setting];
        // At lower sample frequencies, pga gain affects noise
        // At higher frequencies it has no effect
        double pga_degradation = (1.5/12) * pga_gain * ((6-samplerate_setting)/6.0);
        enob -= pga_degradation;
        // Oversampling adds 1 ENOB per factor of 4
        enob += ((double)buffer_depth_log2)/2.0;
        //
        if(channel == 0 && (meter_settings.chset[0] & METER_CH_SETTINGS_INPUT_MASK) == 0 ) {
            // This is compensation for a bug in RevH, where current sense chopper noise dominates
            enob -= 2;
        }
        return enob;
    }

    /**
     * Based on the ENOB and the measurement range for the given channel, determine which digits are
     * significant in the output.
     * @param channel The channel index (0 or 1)
     * @return  A SignificantDigits structure, "high" is the number of digits to the left of the decimal point and "digits" is the number of significant digits
     */

    public SignificantDigits getSigDigits(final int channel) {
        SignificantDigits retval = new SignificantDigits();
        final double enob = getEnob(channel);
        final double max = lsbToNativeUnits((1<<22),channel);
        final double max_dig  = Math.log10(max);
        final double n_digits = Math.log10(Math.pow(2.0, enob));
        retval.high = (int)(max_dig+1);
        retval.n_digits = (int) n_digits;
        return retval;
    }

    /**
     * Examines the measurement settings and converts the input (in LSB) to the voltage at the input
     * of the AFE.  Note this is at the input of the AFE, not the input of the ADC (there is a PGA)
     * between them
     * @param reading_lsb   Input reading [LSB]
     * @param channel       The channel index (0 or 1)
     * @return  Voltage at AFE input [V]
     */

    public double lsbToADCInVoltage(final int reading_lsb, final int channel) {
        // This returns the input voltage to the ADC,
        final double Vref = 2.5;
        final double pga_lookup[] = {6,1,2,3,4,8,12};
        int pga_setting=0;
        switch(channel) {
            case 0:
                pga_setting = meter_settings.chset[0] >> 4;
                break;
            case 1:
                pga_setting = meter_settings.chset[1] >> 4;
                break;
            default:
                Log.i(TAG,"Should not be here");
                break;
        }
        double pga_gain = pga_lookup[pga_setting];
        return ((double)reading_lsb/(double)(1<<23))*Vref/pga_gain;
    }

    /**
     * Converted the voltage at the input of the AFE to the voltage at the HV input by examining the
     * meter settings
     * @param adc_voltage   Voltage at the AFE [V]
     * @return  Voltage at the HV input terminal [V]
     */

    public double adcVoltageToHV(final double adc_voltage) {
        switch( (meter_settings.adc_settings & ADC_SETTINGS_GPIO_MASK) >> 4 ) {
            case 0x00:
                // 1.2V range
                return adc_voltage;
            case 0x01:
                // 60V range
                return ((10e6+160e3)/(160e3)) * adc_voltage;
            case 0x02:
                // 1000V range
                return ((10e6+11e3)/(11e3)) * adc_voltage;
            default:
                Log.w(TAG,"Invalid setting!");
                return 0.0;
        }
    }

    /**
     * Convert voltage at the input of the AFE to current through the A terminal
     * @param adc_voltage   Voltage at the AFE [V]
     * @return              Current through the A terminal [A]
     */

    public double adcVoltageToCurrent(final double adc_voltage) {
        final double rs = 1e-3;
        final double amp_gain = 80.0;
        return adc_voltage/(amp_gain*rs);
    }

    /**
     * Convert voltage at the input of the AFE to temperature
     * @param adc_voltage   Voltage at the AFE [V]
     * @return              Temperature [C]
     */

    public double adcVoltageToTemp(double adc_voltage) {
        adc_voltage -= 145.3e-3; // 145.3mV @ 25C
        adc_voltage /= 490e-6;   // 490uV / C
        return 25.0 + adc_voltage;
    }

    /**
     * Examines the meter settings to determine how much current is flowing out of the current source
     * (flows out the Active terminal)
     * @return  Current from the active terminal [A]
     */

    public double getIsrcCurrent() {
        if( 0 == (meter_settings.measure_settings & METER_MEASURE_SETTINGS_ISRC_ON) ) {
            return 0;
        }
        if( 0 != (meter_settings.measure_settings & METER_MEASURE_SETTINGS_ISRC_LVL) ) {
            return 100e-6;
        } else {
            return 100e-9;
        }
    }

    /**
     * Converts an ADC reading to the reading at the terminal input
     * @param lsb   Input reading in LSB
     * @param ch    Channel index (0 or 1)
     * @return      Value at the input terminal.  Depending on measurement settings, can be V, A or Ohms
     */

    public double lsbToNativeUnits(int lsb, final int ch) {
        double adc_volts = 0;
        final double ptc_resistance = 7.9;
        final byte channel_setting = (byte) (meter_settings.chset[ch] & METER_CH_SETTINGS_INPUT_MASK);
        if(disp_hex[ch]) {
            return lsb;
        }
        switch(channel_setting) {
            case 0x00:
                // Regular electrode input
                switch(ch) {
                    case 0:
                        // CH1 offset is treated as an extrinsic offset because it's dominated by drift in the isns amp
                        adc_volts = lsbToADCInVoltage(lsb,ch);
                        adc_volts -= offsets[0];
                        return adcVoltageToCurrent(adc_volts);
                    case 1:
                        // CH2 offset is treaded as an intrinsic offset because it's dominated by offset in the ADC itself
                        lsb -= offsets[1];
                        adc_volts = lsbToADCInVoltage(lsb,ch);
                        return adcVoltageToHV(adc_volts);
                    default:
                        Log.w(TAG,"Invalid channel");
                        return 0;
                }
            case 0x04:
                adc_volts = lsbToADCInVoltage(lsb,ch);
                return adcVoltageToTemp(adc_volts);
            case 0x09:
                // CH3 is complicated.  When measuring aux voltage, offset is dominated by intrinsic offsets in the ADC
                // When measuring resistance, offset is a resistance and must be treated as such
                final double isrc_current = getIsrcCurrent();
                if( isrc_current != 0 ) {
                    // Current source is on, apply compensation for PTC drop
                    adc_volts = lsbToADCInVoltage(lsb,ch);
                    adc_volts -= ptc_resistance*isrc_current;
                    adc_volts -= offsets[2]*isrc_current;
                } else {
                    // Current source is off, offset is intrinsic
                    lsb -= offsets[2];
                    adc_volts = lsbToADCInVoltage(lsb,ch);
                }
                if( disp_ch3_mode == CH3_MODES.RESISTANCE ) {
                    // Convert to Ohms
                    return adc_volts/isrc_current;
                } else {
                    return adc_volts;
                }
            default:
                Log.w(TAG,"Unrecognized channel setting");
                return adc_volts;
        }
    }

    /**
     *
     * @param channel The channel index (0 or 1)
     * @return A string describing what the channel is measuring
     */

    public String getDescriptor(final int channel) {
        final byte channel_setting = (byte) (meter_settings.chset[channel] & METER_CH_SETTINGS_INPUT_MASK);
        switch( channel_setting ) {
            case 0x00:
                switch (channel) {
                    case 0:
                        if(disp_ac[channel]){return "Current AC";}
                        else {return "Current DC";}
                    case 1:
                        if(disp_ac[channel]){return "Voltage AC";}
                        else {return "Voltage DC";}
                    default:
                        return "Invalid";
                }
            case 0x04:
                // Temperature sensor
                return "Temperature";
            case 0x09:
                // Channel 3 in
                switch( disp_ch3_mode ) {
                    case VOLTAGE:
                        if(disp_ac[channel]){return "Aux Voltage AC";}
                        else {return "Aux Voltage DC";}
                    case RESISTANCE:
                        return "Resistance";
                    case DIODE:
                        return "Diode Test";
                }
                break;
            default:
                Log.w(TAG,"Unrecognized setting");
        }
        return "";
    }

    /**
     *
     * @param channel The channel index (0 or 1)
     * @return A string containing the units label for the channel
     */

    public String getUnits(final int channel) {
        final byte channel_setting = (byte) (meter_settings.chset[channel] & METER_CH_SETTINGS_INPUT_MASK);
        if(disp_hex[channel]) {
            return "RAW";
        }
        switch( channel_setting ) {
            case 0x00:
                switch (channel) {
                    case 0:
                        return "A";
                    case 1:
                        return "V";
                    default:
                        return "?";
                }
            case 0x04:
                return "C";
            case 0x09:
                switch( disp_ch3_mode ) {
                    case VOLTAGE:
                        return "V";
                    case RESISTANCE:
                        return "Ω";
                    case DIODE:
                        return "V";
                }
            default:
                Log.w(TAG,"Unrecognized chset[0] setting");
                return "";
        }
    }

    /**
     *
     * @param channel The channel index (0 or 1)
     * @return        A String containing the input label of the channel (V, A, Omega or Internal)
     */

    public String getInputLabel(final int channel) {
        final byte channel_setting = (byte) (meter_settings.chset[channel] & METER_CH_SETTINGS_INPUT_MASK);
        switch( channel_setting ) {
            case 0x00:
                switch (channel) {
                    case 0:
                        return "A";
                    case 1:
                        return "V";
                    default:
                        return "?";
                }
            case 0x04:
                return "INT";
            case 0x09:
                return "Ω";
            default:
                Log.w(TAG,"Unrecognized setting");
                return "";
        }
    }

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
    my_meter.meter_settings.setBufferDepth(32)
    my_meter.meter_settings.setSampleRate(125)
    my_meter.meter_settings.calc_settings |= my_meter.meter_settings.METER_CALC_SETTINGS_MEAN
    my_meter.meter_settings.target_meter_state = my_meter.meter_settings.METER_RUNNING
    def notifyCB():
        print my_meter.meter_sample.reading_lsb[0]
        print my_meter.meter_sample.reading_lsb[1]
    my_meter.meter_sample.enableNotify(True,notifyCB)
    import time
    time.sleep(1)
    my_meter.meter_settings.write()
    while True:
        BGWrapper.idle()