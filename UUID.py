# Utility class
class UUID:
    def __init__(self, initializer):
        if type(initializer) == type(""):
            #String input
            self.bytes = self.__stringToBytes(initializer)
        elif type(initializer) == type(1):
            # Integer initialized, assume a 2 byte UUID
            self.bytes = (initializer&0xFF, (initializer>>8)&0xFF)
        else:
            #Byte array input
            self.bytes = tuple(initializer)
    def __stringToBytes(self, arg):
        arg = arg.upper()
        arg = arg.replace("-","")
        l = [int(arg[i:i+2],16) for i in range(0,len(arg),2)]
        return tuple(l)
    def __bytesToString(self, bytes):
        l = ["%02X"%bytes[i] for i in range(len(bytes))]
        if len(bytes) == 16:
            l = ["%02X"%bytes[i] for i in range(16)]
            l.insert( 4,'-')
            l.insert( 7,'-')
            l.insert(10,'-')
            l.insert(13,'-')
        return ''.join(l)
    def asString(self):
        return self.__bytesToString(self.bytes)
    def __eq__(self, other):
        return self.bytes==other.bytes
    def __hash__(self):
        return self.asString().__hash__()
    def __str__(self):
        return self.asString()
    def __repr__(self):
        return self.asString()