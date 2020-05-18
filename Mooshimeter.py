# coding=UTF-8
import BGWrapper
from UUID import *
from ConfigNode import *
from BytePack import *
import binascii

class MeterSerOut(BGWrapper.Characteristic):
    def __init__(self, meter, parent, handle, uuid):
        """
        :param other: a BGWrapper.Characteristic
        :return:
        """
        super(MeterSerOut,self).__init__(parent, handle, uuid)
        self.meter = meter
        self.seq_n = -1
        self.aggregate = []
    def pack(self):
        pass
    def interpretAggregate(self):
        while len(self.aggregate) > 0:
            try:
                b = BytePack(self.aggregate)
                shortcode = b.get()
                try:
                    node = self.meter.code_list[shortcode]
                except KeyError:
                    print('Received an unrecognized shortcode!')
                    return
                if   node.ntype == NTYPE.PLAIN    :
                    raise Exception()
                elif node.ntype == NTYPE.CHOOSER:
                    node.notification_handler(self.meter,b.get(1))
                elif node.ntype == NTYPE.LINK   :
                    raise Exception()
                elif node.ntype == NTYPE.VAL_U8 :
                    node.notification_handler(self.meter,b.get(1))
                elif node.ntype == NTYPE.VAL_U16:
                    node.notification_handler(self.meter,b.get(2))
                elif node.ntype == NTYPE.VAL_U32:
                    node.notification_handler(self.meter,b.get(4))
                elif node.ntype == NTYPE.VAL_S8 :
                    node.notification_handler(self.meter,b.get(1,signed=True))
                elif node.ntype == NTYPE.VAL_S16:
                    node.notification_handler(self.meter,b.get(2,signed=True))
                elif node.ntype == NTYPE.VAL_S32:
                    node.notification_handler(self.meter,b.get(4,signed=True))
                elif node.ntype == NTYPE.VAL_STR:
                    expecting_bytes=b.get(2)
                    if b.getBytesRemaining() < expecting_bytes:
                        return #abort!
                    node.notification_handler(self.meter,b.getBytes(expecting_bytes))
                elif node.ntype == NTYPE.VAL_BIN:
                    expecting_bytes=b.get(2)
                    if b.getBytesRemaining() < expecting_bytes:
                        return #abort!
                    node.notification_handler(self.meter,b.getBytes(expecting_bytes))
                elif node.ntype == NTYPE.VAL_FLT:
                    node.notification_handler(self.meter,b.get(4,t=float))
                else:
                    raise Exception()
                self.aggregate = self.aggregate[b.i:]
            except UnderflowException:
                # An underflow exception here does not indicate anything sinister.  It just means we had to split a packet.
                # across multiple BLE connection events.
                #print 'underflow'
                return
    def unpack(self):
        b = BytePack(self.byte_value)
        seq_n      = b.get(1) & 0xFF
        if (self.seq_n != -1) and (seq_n != (self.seq_n+1)%0x100):
            print('Received out of order packet!')
            print('Expected: %d'%(self.seq_n+1))
            print('Got     : %d'%seq_n)
        self.seq_n = seq_n
        self.aggregate += b.bytes[1:]
        # Attempt to decode a message, if we succeed pop the message off the byte queue
        self.interpretAggregate()
class MeterSerIn(BGWrapper.Characteristic):
    def __init__(self, meter, parent, handle, uuid):
        """
        :param other: a BGWrapper.Characteristic
        :return:
        """
        super(MeterSerIn,self).__init__(parent, handle, uuid)
        self.meter = meter
    def pack(self):
        pass
    def unpack(self):
        pass

def buildTree():
    # Test of config tree build
    # Abbreviations
    NF = ConfigNode
    NP = NTYPE.PLAIN
    root = NF(NP,children=[
        NF(NP,'ADMIN',children=[
            NF(NTYPE.VAL_U32,'CRC32'),
            NF(NTYPE.VAL_BIN,'TREE'),
            NF(NTYPE.VAL_STR,'DIAGNOSTIC')
        ]),
    ])
    tree = ConfigTree(root)
    tree.assignShortCodes()
    return tree

class Mooshimeter(object):
    class mUUID:
        """
        Static declarations of UUID values in the meter
        """
        METER_SERVICE      = UUID("1BC5FFA0-0200-62AB-E411-F254E005DBD4")
        METER_SERIN        = UUID("1BC5FFA1-0200-62AB-E411-F254E005DBD4")
        METER_SEROUT       = UUID("1BC5FFA2-0200-62AB-E411-F254E005DBD4")

        OAD_SERVICE_UUID   = UUID("1BC5FFC0-0200-62AB-E411-F254E005DBD4")
        OAD_IMAGE_IDENTIFY = UUID("1BC5FFC1-0200-62AB-E411-F254E005DBD4")
        OAD_IMAGE_BLOCK    = UUID("1BC5FFC2-0200-62AB-E411-F254E005DBD4")
        OAD_REBOOT         = UUID("1BC5FFC3-0200-62AB-E411-F254E005DBD4")

    def sendToMeter(self, payload):
        if len(payload) > 19:
            raise Exception("Not implemented!  Payload too long!")
        # Put in the sequence number
        b = BytePack()
        b.put(0) # seq n
        b.put(payload)
        self.meter_serin.byte_value = b.bytes
        self.meter_serin.write()

    def __init__(self, peripheral):
        """
        Initialized instance variables
        :param peripheral: a BGWrapper.Peripheral instance
        :return:
        """
        self.p = peripheral
        self.meter_serin  = MeterSerIn( self,self.p,0,self.mUUID.METER_SERIN)
        self.meter_serout = MeterSerOut(self,self.p,0,self.mUUID.METER_SEROUT)
        # Initial tree
        tree = buildTree()
        self.code_list = tree.getShortCodeList()
        self.tree = tree
        # Assign an expander function to the tree node
        node = self.tree.getNodeAtLongname('ADMIN:TREE')
        def expandReceivedTree(meter,payload):
            payload_str = bytes(payload)
            self.tree.unpack(payload_str)
            self.code_list = tree.getShortCodeList()
            # If you want to be super verbose...
            #tree.enumerate()
            # Calculate the CRC32 of received tree
            crc_node = self.tree.getNodeAtLongname('ADMIN:CRC32')
            crc_node.value = binascii.crc32(payload_str)
        node.notification_handler=expandReceivedTree
    def sendCommand(self,cmd):
        if type(cmd) != str:
            return
        # cmd might contain a payload, in which case split it out
        try:
            node_str, payload_str = cmd.split(' ',1)
        except ValueError:
            node_str = cmd
            payload_str = None
        node = self.tree.getNodeAtLongname(node_str)
        if node == None:
            print('Node %s not found!'%node_str)
            return
        if node.code == -1:
            print('This command does not have a value associated.')
            print('Children of this commend:')
            self.tree.enumerate(node)
        b = BytePack()
        if not payload_str:
            b.put(node.code)
        else:
            b.put(node.code+0x80)
            if   node.ntype == NTYPE.PLAIN    :
                print("This command doesn't accept a payload")
                return
            elif node.ntype == NTYPE.CHOOSER:
                b.put(int(payload_str))
            elif node.ntype == NTYPE.LINK   :
                print("This command doesn't accept a payload")
                return
            elif node.ntype == NTYPE.VAL_U8 :
                b.put(int(payload_str))
            elif node.ntype == NTYPE.VAL_U16:
                b.put(int(payload_str),2)
            elif node.ntype == NTYPE.VAL_U32:
                b.put(int(payload_str),4)
            elif node.ntype == NTYPE.VAL_S8 :
                b.put(int(payload_str))
            elif node.ntype == NTYPE.VAL_S16:
                b.put(int(payload_str),2)
            elif node.ntype == NTYPE.VAL_S32:
                b.put(int(payload_str),4)
            elif node.ntype == NTYPE.VAL_STR:
                b.put(len(payload_str),2)
                b.put(payload_str)
            elif node.ntype == NTYPE.VAL_BIN:
                print("This command doesn't accept a payload")
                return
            elif node.ntype == NTYPE.VAL_FLT:
                b.put(float(payload_str))
            else:
                raise Exception()
        self.sendToMeter(b.bytes)
    def loadTree(self):
        self.sendCommand('ADMIN:TREE')
    def connect(self):
        self.p.connect()
        self.p.discover()
        def assignHandle(c):
            self.p.replaceCharacteristic(c)
        assignHandle(self.meter_serout)
        assignHandle(self.meter_serin)
        wrap=[0]
        def tmp_cb():
            #print "Packet %d"%wrap[0]
            wrap[0]+=1
        self.meter_serout.enableNotify(True,tmp_cb)
    def disconnect(self):
        BGWrapper.disconnect(self.p.conn_handle)
    def getUUIDString(self):
        return self.p.getUUIDString()
    def attachCallback(self,node_path,notify_cb):
        if notify_cb == None:
            def doNothing(meter,val):
                return
            notify_cb = doNothing
        node = self.tree.getNodeAtLongname(node_path)
        if node == None:
            print('Could not find node at ' + node_path)
            return
        node.notification_handler = notify_cb