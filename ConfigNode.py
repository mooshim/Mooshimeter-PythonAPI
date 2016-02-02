import msgpack
import zlib

class NTYPE:
    PLAIN   =0  # May be an informational node, or a choice in a chooser
    CHOOSER =1  # The children of a CHOOSER can only be selected by one CHOOSER, and a CHOOSER can only select one child
    LINK    =2  # A link to somewhere else in the tree
    COPY    =3  # In a fully inflated tree, this value will not appear.  It's an instruction to the inflater to copy the value
    VAL_U8  =4  # These nodes have readable and writable values of the type specified
    VAL_U16 =5  # These nodes have readable and writable values of the type specified
    VAL_U32 =6  # These nodes have readable and writable values of the type specified
    VAL_S8  =7  # These nodes have readable and writable values of the type specified
    VAL_S16 =8  # These nodes have readable and writable values of the type specified
    VAL_S32 =9  # These nodes have readable and writable values of the type specified
    VAL_STR =10 # These nodes have readable and writable values of the type specified
    VAL_BIN =11 # These nodes have readable and writable values of the type specified
    VAL_FLT =12 # These nodes have readable and writable values of the type specified

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
    def __init__(self,ntype=-1,name='',children=None):
        self.code = -1
        self.ntype = ntype
        self.name=name
        self.children=[]
        self.parent = None
        self.tree = None
        self.notification_handler = self.defaultNotificationHandler
        if children!=None:
            for c in children:
                if issubclass(c.__class__,ConfigNode):
                    self.children.append(c)
                else:
                    self.children.append(nodeFactory(NTYPE.PLAIN,str(c)))
    def defaultNotificationHandler(self,new_val):
        if self.ntype == NTYPE.CHOOSER:
            try:
                s = str(self.children[new_val])
            except:
                print "Meter sent a choice that's out of range!"
                s = str(new_val)
        else:
            s = str(new_val)
        print self.getLongName()+':'+s
    def pack(self):
        l = []
        return msgpack.packb(self.packToEndOfList(l))
    def unpack(self,arg):
        l = msgpack.unpackb(arg)
        self.unpackFromFrontOfList(l)
    def unpackFromFrontOfList(self,l):
        raise Exception()
    def packToEndOfList(self,l):
        raise Exception()
    def __str__(self):
        s = ''
        if self.code != -1:
            s += str(self.code) + ':'
        s += self.name
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
    def getLongName(self,rval=None,sep=':'):
        if rval==None:
            rval = self.name
        else:
            rval = sep.join((self.name,rval))
        if self.parent == None:
            return rval[1:]
        else:
            return self.parent.getLongName(rval)
    def needsShortCode(self):
        return False
    def assignShortCode(self,code):
        self.code=code

class StructuralNode(ConfigNode):
    def unpackFromFrontOfList(self,l):
        if l[0] != self.ntype:
            print 'Wrong node type!'
            raise Exception()
        l.pop(0)
        self.name=l.pop(0)
        self.children = []
        children_packed=l.pop(0)
        while len(children_packed):
            ntype = children_packed[0]
            NClass = NodesByType[ntype]
            n_instance = NClass(ntype)
            n_instance.unpackFromFrontOfList(children_packed)
            self.children.append(n_instance)
    def packToEndOfList(self,l):
        l.append(self.ntype)
        l.append(self.name)
        children_packed = []
        for c in self.children:
            c.packToEndOfList(children_packed)
        l.append(children_packed)
    def needsShortCode(self):
        return self.ntype==NTYPE.CHOOSER

class RefNode(ConfigNode):
    def __init__(self,ntype=-1,name='',path=None):
        super(RefNode, self).__init__(ntype,name,None)
        self.path = path
    def unpackFromFrontOfList(self,l):
        if l[0] != self.ntype:
            print 'Wrong node type!'
            raise Exception()
        l.pop(0)
        self.path = l.pop(0)
    def packToEndOfList(self,l):
        l.append(self.ntype)
        l.append(self.path)
    def __str__(self):
        s = ''
        if self.ntype == NTYPE.COPY:
            s += 'COPY: '+ str(self.path)
        if self.ntype == NTYPE.LINK:
            s += 'LINK:'+ str(self.path) + ':' + str(self.tree.getNodeAtLongname(self.path).getPath())
        return s

class ValueNode(ConfigNode):
    def unpackFromFrontOfList(self,l):
        if l[0] != self.ntype:
            print 'Wrong node type!'
            raise Exception()
        l.pop(0)
        self.name = l.pop(0)
    def packToEndOfList(self,l):
        l.append(self.ntype)
        l.append(self.name)
    def needsShortCode(self):
        return True

NodesByType = [
    StructuralNode,
    StructuralNode,
    RefNode,
    RefNode,
    ValueNode,
    ValueNode,
    ValueNode,
    ValueNode,
    ValueNode,
    ValueNode,
    ValueNode,
    ValueNode,
    ValueNode,
]

def nodeFactory(*args,**kwargs):
    return (NodesByType[args[0]](*args,**kwargs))

class ConfigTree(object):
    def __init__(self, root=None):
        self.root=root
    def enumerate(self,n=None,indent=0):
        if n == None:
            n=self.root
        print indent*'  ' + str(n)
        for c in n.children:
            self.enumerate(c,indent+1)
    def pack(self):
        l = []
        self.root.packToEndOfList(l)
        plain = msgpack.packb(l)
        compressed = zlib.compress(plain)
        return compressed
    def unpack(self,compressed):
        plain = zlib.decompress(compressed)
        l = msgpack.unpackb(plain)
        self.root = nodeFactory(l[0])
        self.root.unpackFromFrontOfList(l)
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
        tokens = longname.split(':')
        n = self.root
        if longname == '':
            return n
        for token in tokens:
            found=False
            for c in n.children:
                #if c.name == token:
                if c.name.startswith(token):
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
