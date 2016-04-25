#!/usr/bin/env python
import os
import socket
import struct

NLMSG_NOOP = 1
NLMSG_ERROR = 2
NLMSG_DONE = 3

NETLINK_NETFILTER=12

NLM_F_REQUEST=1
NLM_F_ROOT=0x100
NLM_F_MATCH=0x200
NLM_F_DUMP=NLM_F_ROOT|NLM_F_MATCH

class ctnl:
    MSGLEN=0
    MSGTYPE=1
    def __init__(self, next=None):
        self.length = 4*4
        self.pattern = "IHHII"
        self.nlFlags = NLM_F_REQUEST | NLM_F_DUMP
        self.nlSeq = 7
        self.nlPid = 0
        self.next = next
        self.nlSocket = socket.socket(socket.AF_NETLINK, socket.SOCK_RAW, NETLINK_NETFILTER)
        self.nlSocket.bind((os.getpid(), 0))
        #print self.nlSocket.getsockname()
    
    def send(self, subsys, type, content=None):
        self.nlType = subsys<<8 | type
        self.payload = self.next.send(content)
        self.nlHdr = struct.pack(self.pattern, len(self.payload) + self.length, self.nlType, self.nlFlags, self.nlSeq, self.nlPid)
        
        self.nlSocket.send(self.nlHdr + self.payload)
    
    def recv(self):
        while True:
            data = self.nlSocket.recv(65535)
            while len(data):
                nlHdr = struct.unpack(self.pattern, data[:self.length])
                if nlHdr[ctnl.MSGTYPE]==NLMSG_NOOP:
                    print "no-op"
                    continue
                elif nlHdr[ctnl.MSGTYPE]==NLMSG_ERROR:
                    errno = -struct.unpack("i", data[self.length:self.length+4])[0]
                    print os.strerror(errno)
                    break
                elif nlHdr[ctnl.MSGTYPE]==NLMSG_DONE:
                    #print "Done."
                    return
                
                #print "ctnl:"+str(nlHdr)
                self.next.recv(data[self.length:nlHdr[ctnl.MSGLEN]])
                data = data[nlHdr[ctnl.MSGLEN]:]
            
    def loop(self):
        self.send(NFNL_SUBSYS_CTNETLINK, IPCTNL_MSG_CT_GET_STATS_CPU)
        self.recv()
            
NFNETLINK_V0=0
class genl:
    RESID=2
    def __init__(self, res_id=0, version = 0):
        self.map = ["cpu=", "searched=", "found=", "new=", "invalid=", "ignore=", "delete=", "delete_list=", "insert=", "insert_failed=", "drop=", "early_drop=", "error=", "search_restart="]
        self.pattern = "!BBH"
        self.length = 4
        self.family = socket.AF_INET
        self.version = NFNETLINK_V0
        self.res_id = 0
    def send(self, content=None):
        return struct.pack(self.pattern, self.family, self.version, self.res_id)

    def recv(self, data):
        geHdr = struct.unpack(self.pattern, data[:self.length])
        #print "genl:"+str(geHdr)
        #print "cpu"+str(geHdr[genl.RESID])+":"
        self.res_id = geHdr[genl.RESID]
        self.attributes = self.parseAttributes(data[self.length:])
        #print "attributes:"+str(self.attributes)
        print "cpu="+str(self.res_id) + "\t" + " ".join([self.map[i]+str(self.attributes[i][0]) for i in range(1,1+len(self.attributes))])
        
    def parseAttributes(self, data):
        attrs = {}
        while len(data):
            attr_len, attr_type = struct.unpack("HH", data[:4])
            attrs[attr_type] = struct.unpack("!I", data[4:attr_len])
            attr_len = ((attr_len + 4 - 1) & ~3)
            data = data[attr_len:]
        return attrs
 
NFNL_SUBSYS_CTNETLINK=1
IPCTNL_MSG_CT_GET_STATS_CPU=4
s = ctnl(genl())
s.loop()
