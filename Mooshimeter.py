# coding=UTF-8
from UUID import *
from ConfigNode import *
from BytePack import *
import binascii

class MeterSerOut():
    def __init__(self, meter):
        """
        :param other: a BGWrapper.Characteristic
        :return:
        """
        self.meter = meter
        self.seq_n = 0
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
                    print 'Received an unrecognized shortcode!'
                    self.aggregate = self.aggregate[1:]
                    return
                if   node.ntype == NTYPE.PLAIN    :
                    raise Exception()
                elif node.ntype == NTYPE.CHOOSER:
                    node.notification_handler(b.get(1))
                elif node.ntype == NTYPE.LINK   :
                    raise Exception()
                elif node.ntype == NTYPE.VAL_U8 :
                    node.notification_handler(b.get(1))
                elif node.ntype == NTYPE.VAL_U16:
                    node.notification_handler(b.get(2))
                elif node.ntype == NTYPE.VAL_U32:
                    node.notification_handler(b.get(4))
                elif node.ntype == NTYPE.VAL_S8 :
                    node.notification_handler(b.get(1,signed=True))
                elif node.ntype == NTYPE.VAL_S16:
                    node.notification_handler(b.get(2,signed=True))
                elif node.ntype == NTYPE.VAL_S32:
                    node.notification_handler(b.get(4,signed=True))
                elif node.ntype == NTYPE.VAL_STR:
                    expecting_bytes=b.get(2)
                    if b.getBytesRemaining() < expecting_bytes:
                        return #abort!
                    node.notification_handler(b.getBytes(expecting_bytes))
                elif node.ntype == NTYPE.VAL_BIN:
                    expecting_bytes=b.get(2)
                    if b.getBytesRemaining() < expecting_bytes:
                        return #abort!
                    node.notification_handler(b.getBytes(expecting_bytes))
                elif node.ntype == NTYPE.VAL_FLT:
                    node.notification_handler(b.get(4,t=float))
                else:
                    raise Exception()
                self.aggregate = self.aggregate[b.i:]
            except UnderflowException:
                print 'underflow'
                return
    def unpack(self, payload):
        self.aggregate += payload[:]
        # Attempt to decode a message, if we succeed pop the message off the byte queue
        self.interpretAggregate()

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
    def sendToMeter(self, payload):
        b = BytePack()
        b.put(0x66) #magic byte
        b.put(len(payload)) #length to follow
        b.put(payload)
        self.serial_port.write(str(bytearray(b.bytes)))
        print b.bytes
    def receiveFromMeter(self,payload):
        self.meter_serout.unpack(payload)
    def __init__(self,ser):
        """
        Initialized instance variables
        :param ser: a Serial.serial instance
        :return:
        """
        self.serial_port = ser
        self.meter_serout = MeterSerOut(self)
        # Initial tree
        tree = buildTree()
        self.code_list = tree.getShortCodeList()
        self.tree = tree
        # Assign an expander function to the tree node
        node = self.tree.getNodeAtLongname('ADMIN:TREE')
        def expandReceivedTree(payload):
            payload_str = ''.join([chr(c) for c in payload])
            self.tree.unpack(payload_str)
            self.code_list = tree.getShortCodeList()
            tree.enumerate()
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
            print 'Node %s not found!'%node_str
            return
        if node.code == -1:
            print 'This command does not have a value associated.'
            print 'Children of this commend:'
            self.tree.enumerate(node)
        b = BytePack()
        if not payload_str:
            b.put(node.code)
        else:
            b.put(node.code+0x80)
            if   node.ntype == NTYPE.PLAIN    :
                print "This command doesn't accept a payload"
                return
            elif node.ntype == NTYPE.CHOOSER:
                b.put(int(payload_str))
            elif node.ntype == NTYPE.LINK   :
                print "This command doesn't accept a payload"
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
                print "This command doesn't accept a payload"
                return
            elif node.ntype == NTYPE.VAL_FLT:
                b.put(float(payload_str))
            else:
                raise Exception()
        self.sendToMeter(b.bytes)
    def loadTree(self):
        self.sendCommand('ADMIN:TREE')
    def attachCallback(self,node_path,notify_cb):
        if notify_cb == None:
            def doNothing(val):
                return
            notify_cb = doNothing
        node = self.tree.getNodeAtLongname(node_path)
        if node == None:
            print 'Could not find node at ' + node_path
            return
        node.notification_handler = notify_cb