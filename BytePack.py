import struct

class UnderflowException(Exception):
    pass

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
            # Is it iterable?  Try it, assuming it's a list of bytes
            for byte in v:
                self.putByte(byte)
    def get(self,b=1,t=int,signed=False):
        if t == int:
            if b > self.getBytesRemaining():
                raise UnderflowException()
            r = 0
            s = 0
            top_b = 0
            while b:
                top_b = self.bytes[self.i]
                r += top_b << s
                s += 8
                self.i += 1
                b -= 1
            # Sign extend
            if signed and top_b & 0x80:
                    r -= 1 << s
            return r
        elif t==float:
            if 4 > self.getBytesRemaining():
                raise UnderflowException()
            r = struct.unpack("f",struct.pack("BBBB",*self.bytes[self.i:self.i+4]))
            self.i += 4
            return r[0]
    def getBytes(self, max_bytes=0):
        if max_bytes == 0:
            rval = self.bytes[self.i:]
        else:
            rval = self.bytes[self.i:self.i+max_bytes]
        self.i += len(rval)
        return rval
    def getBytesRemaining(self):
        return len(self.bytes) - self.i