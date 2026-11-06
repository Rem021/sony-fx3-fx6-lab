"""Strict per-helper flow frames, after live kernel peer/self-image checking.

The supervisor saves each raw512B frame before calling this decoder.
No saved file is itself a live origin proof or a camera acceptance result.
"""
from hashlib import sha256
import struct
import receipt_receiver as R

class FlowReceiver:
    def __init__(self,identity,nonce,grant):
        self.identity=identity;self.nonce=bytes(nonce);self.grant=sha256(grant.encode('ascii')).digest()
        self.previous=bytes(32);self.count=0;self.pending=None;self.complete=False;self.terminal=False;self.rows=[]
        self.calls={};self.body_bytes=0;self.body_tag=None;self.location=None;self.nodes={};self.pending_subject=None

    def accept(self,data):
        if len(data)!=512 or data[:8]!=b'FX3FLOW1' or self.terminal:raise R.Rejected('flow size/magic/terminal')
        schema,point,sequence,op,status=struct.unpack_from('<IIQII',data,8)
        if schema!=1 or point not in range(4) or sequence!=self.count+1 or sequence>512:raise R.Rejected('flow schema/sequence')
        if struct.unpack_from('<IIQQ',data,32)!=(self.identity.uid,self.identity.pid,self.identity.sec,self.identity.usec):raise R.Rejected('flow helper incarnation')
        if data[56:72]!=self.nonce or data[72:104]!=self.grant:raise R.Rejected('flow nonce/grant')
        if data[448:480]!=self.previous or sha256(data[:480]).digest()!=data[480:]:raise R.Rejected('flow chain/digest')
        if any(data[252:448]):raise R.Rejected('flow reserved/proof bytes')
        returned,known,count,raw,pending,vendor=struct.unpack_from('<IIIiII',data,104)
        if status>8 or returned>1 or known>1 or vendor>1:raise R.Rejected('flow bounded native fields')
        if point==0:
            if self.pending is not None or op not in range(1,10) or pending!=op or returned or known or count or raw:raise R.Rejected('flow call-before')
            registry,location,product=struct.unpack_from('<QII',data,160);vid=product&65535;pid=product>>16;tag=data[176:208]
            if not registry or not location or vid!=0x054c or pid not in (0x0da1,0x0336) or tag==bytes(32):raise R.Rejected('flow current-node identity')
            if self.body_tag is None:self.body_tag=tag;self.location=location
            if self.body_tag!=tag or self.location!=location:raise R.Rejected('flow body/port changed')
            if pid in self.nodes and self.nodes[pid]!=registry and op!=9:raise R.Rejected('flow stale generation')
            if op!=9:self.nodes[pid]=registry
            self.pending_subject=data[152:208]
            self.pending=op
        elif point==1:
            if self.pending!=op or op not in range(1,10):raise R.Rejected('flow unmatched return')
            if data[152:208]!=self.pending_subject:raise R.Rejected('flow return changed call subject')
            if returned:
                if pending:raise R.Rejected('returned call still marked pending')
                self.pending=None
                pid=struct.unpack_from('<I',data,172)[0]>>16
                self.calls[pid,op]=self.calls.get((pid,op),0)+1
                if op==6:
                    if not known or not 0<count<=88:raise R.Rejected('flow body progress')
                    self.body_bytes+=count
        elif point==3:
            taken,normal,disposed,retained,finished=struct.unpack_from('<5I',data,132)
            driver=struct.unpack_from('<I',data,248)[0]
            if op==50:
                if self.pending is not None or (taken,normal,disposed,retained,finished,driver)!=(1,1,1,0,1,1):raise R.Rejected('flow incomplete terminal state')
                for pid,expected in [(0x0da1,{1:1,2:7,3:7,8:1,9:1}),(0x0336,{1:1,2:7,3:7,4:1,5:1,7:1,8:1})]:
                    if any(self.calls.get((pid,kind),0)!=n for kind,n in expected.items()):raise R.Rejected('flow missing native exchanges')
                if self.body_bytes!=88 or struct.unpack_from('<II',data,208)!=(88,1):raise R.Rejected('flow missing bounded read')
                if self.nodes.get(0x0da1)==self.nodes.get(0x0336):raise R.Rejected('flow generation reused')
                self.complete=True
            elif op!=51:raise R.Rejected('flow terminal kind')
            self.terminal=True
        self.count=sequence;self.previous=data[480:]
        self.rows.append(dict(sequence=sequence,op=op,point=point,status=status,returned=returned,count=count,raw_return=raw,
                              camera_authentication_proven=False,camera_threads_proven=False))
        return self.rows[-1]
