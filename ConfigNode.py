import zlib
import CArrayWriter

class NTYPE:
    PLAIN   =0  # May be an informational node, or a choice in a chooser
    LINK    =1  # A link to somewhere else in the tree
    CHOOSER =2  # The children of a CHOOSER can only be selected by one CHOOSER, and a CHOOSER can only select one child
    VAL_U8  =3  # These nodes have readable and writable values of the type specified
    VAL_U16 =4  # These nodes have readable and writable values of the type specified
    VAL_U32 =5  # These nodes have readable and writable values of the type specified
    VAL_S8  =6  # These nodes have readable and writable values of the type specified
    VAL_S16 =7  # These nodes have readable and writable values of the type specified
    VAL_S32 =8  # These nodes have readable and writable values of the type specified
    VAL_STR =9  # These nodes have readable and writable values of the type specified
    VAL_BIN =10 # These nodes have readable and writable values of the type specified
    VAL_FLT =11 # These nodes have readable and writable values of the type specified

    c_type_dict = {CHOOSER:'uint8',
                   VAL_U8 :'uint8',
                   VAL_U16:'uint16',
                   VAL_U32:'uint32',
                   VAL_S8 :'int8',
                   VAL_S16:'int16',
                   VAL_S32:'int32',
                   VAL_STR:'string_t',
                   VAL_BIN:'bin_t',
                   VAL_FLT:'float',}

    # Provide a reverse name lookup
    code_list = []
    def initCodeList(self):
        tmp = dict([(code,name) for (name,code) in NTYPE.__dict__.items() if type(code)==int])
        for i in range(len(tmp.keys())):
            NTYPE.code_list.append(tmp[i])
NTYPE().initCodeList()

class ConfigNode(object):
    def __init__(self,ntype=-1,name='',value=None,children=None):
        self.code = -1
        self.ntype = ntype
        self.name=name
        self.children=[]
        self.parent = None
        self.tree = None
        self.value = value
        def default_handler(payload):
            print str(self) + ' default handler caught: ' + str(payload)
        self.notification_handler = default_handler
        if children!=None:
            for c in children:
                if issubclass(c.__class__,ConfigNode):
                    self.children.append(c)
                else:
                    self.children.append(ConfigNode(NTYPE.PLAIN,str(c)))
    def __str__(self):
        s = ''
        if self.code != -1:
            s += str(self.code) + ':'
        s+=NTYPE.code_list[self.ntype]+":"
        s += self.name
        if self.value != None:
            s+=":"+str(self.value)
        return s
    def getIndex(self):
        return self.parent.children.index(self)
    def getPath(self,rval=None):
        if rval==None:
            rval = []
        if self.parent != None:
            self.parent.getPath(rval)
            rval.append(self.getIndex())
        return tuple(rval)
    def getLongName(self,rval=None,sep='_'):
        if rval==None:
            rval = self.name
        else:
            rval = sep.join((self.name,rval))
        if self.parent == None:
            return rval[1:]
        else:
            return self.parent.getLongName(rval)
    def needsShortCode(self):
        return not (self.ntype in (NTYPE.PLAIN,NTYPE.LINK))
    def assignShortCode(self,code):
        self.code=code

class ConfigTree(object):
    def __init__(self, root=None):
        self.root=root
    def enumerate(self,n=None,indent=0):
        if n == None:
            n=self.root
        print indent*'  ' + str(n)
        for c in n.children:
            self.enumerate(c,indent+1)
    def serialize(self):
        # Decided not to use msgpack for simplicity.  We have such a reductive structure we can do it
        # more easily ourselves
        r = bytearray()
        def on_each(node):
            r.append(node.ntype)
            r.append(len(node.name))
            [r.append(ord(c)) for c in node.name]
            r.append(len(node.children))
        self.walk(on_each)
        return r.decode('ascii')
    def deserialize(self, bytes):
        ntype = bytes[0]
        nlen  = bytes[1]
        name  = bytes[2:2+nlen].decode('ascii')
        n_children = bytes[2+nlen]
        del bytes[:3+nlen]
        return ConfigNode(ntype,name,children=[self.deserialize(bytes) for x in range(n_children)])
    def pack(self):
        #self.root.packToEndOfList(l)
        #plain = msgpack.packb(l)
        plain = self.serialize()
        print "PLAIN BYTES:",len(plain)
        compressed = zlib.compress(plain)
        print "COMPRESSED BYTES:",len(compressed)
        return compressed
    def unpack(self,compressed):
        plain = zlib.decompress(compressed)
        bytes = bytearray(plain)
        self.root = self.deserialize(bytes)
        self.assignShortCodes()
    def assignShortCodes(self):
        # TODO: Rename this function... it's become a general reference refresher for the tree
        g_code = [0]
        def on_each(node):
            node.tree = self
            for c in node.children:
                c.parent = node
            if node.needsShortCode():
                node.assignShortCode(g_code[0])
                g_code[0] += 1
        self.walk(on_each)
    def getNodeAtLongname(self,longname):
        longname = longname.upper()
        tokens = longname.split(':')
        n = self.root
        for token in tokens:
            found=False
            for c in n.children:
                if c.name == token:
                    n = c
                    found=True
                    break
            if not found:
                return None
        return n
    def getNodeAtPath(self,path):
        n = self.root
        for i in path:
            n = n.children[i]
        return n
    def walk(self,call_on_each,node=None,*args):
        if node == None:
            node = self.root
            call_on_each(node)
        for c in node.children:
            call_on_each(c)
            self.walk(call_on_each,c,*args)
    def getShortCodeList(self):
        rval={}
        def for_each(node):
            if node.code != -1:
                rval[node.code]=node
        self.walk(for_each)
        return rval
    def __align(self,lines,token):
        max_pos = 0
        for line in lines:
            i=line.find(token)
            max_pos=max(i,max_pos)
        # We know how deep to go, add spaces
        for i in range(len(lines)):
            line_parts = lines[i].split(token,1)
            line_parts[0] += (max_pos-len(line_parts[0]))*' '
            new_line = token.join(line_parts)
            lines[i]=new_line
    def writeCHeader(self,f):
        f.write('#pragma once\n')
        f.write('typedef enum {\n')
        lines = []
        for code, node in self.getShortCodeList().items():
            line = '  CMD_'+node.getLongName()+'='+str(code)+','+'//'+NTYPE.code_list[node.ntype]
            if node.ntype == NTYPE.CHOOSER:
                line += ': ' + ','.join([str(c) for c in node.children])
            line += '\n'
            lines.append(line)
        lines.append('  N_CMD_CODES=%d//For reference\n'%len(lines))
        self.__align(lines,'=')
        self.__align(lines,'//')
        for line in lines:
            f.write(line)
        f.write('} cmd_code_t;\n')

        packed = self.pack()
        CArrayWriter.writeHeader(f,'config_tree_packed',packed)

        f.write('extern const unsigned long config_tree_crc32;\n')
    def writeCDec(self,f):
        f.write('#pragma once\n')
        packed = self.pack()
        CArrayWriter.writeAsCArray(f,'config_tree_packed',packed)

        crc32 = zlib.crc32(packed)
        # adapt for wart in zlib.crc32... signed ints
        if crc32 < 0:
            crc32 += 0x100000000

        f.write('const unsigned long config_tree_crc32 = 0x%0X;\n'%crc32)
