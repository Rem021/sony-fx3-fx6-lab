"""Strict per-helper flow frames, after live kernel peer/self-image checking.

The supervisor saves each raw512B frame before calling this decoder.
No saved file is itself a live origin proof or a camera acceptance result.
"""
from hashlib import sha256
import struct
import receipt_receiver as R

def derived_profile(raw):
    """Independently check the raw layout claimed by native descriptor metadata."""
    if len(raw)<9 or raw[:2]!=bytes([9,2]) or struct.unpack_from('<H',raw,2)[0]!=len(raw) or raw[4]!=1 or not raw[5] or not(raw[7]&0x80):
        raise R.Rejected('wire configuration shape')
    at=9;interface=None;addresses=[];packet=None;companion_pending=False
    while at<len(raw):
        if len(raw)-at<2 or raw[at]<2 or raw[at]>len(raw)-at:raise R.Rejected('wire item bounds')
        d=raw[at:at+raw[at]];kind=d[1]
        if companion_pending and kind!=0x30:raise R.Rejected('missing SS companion')
        if kind==4:
            if len(d)!=9 or interface is not None or d[3] or d[5]!=255 or d[4]not in (2,4):raise R.Rejected('wire interface')
            interface=d
        elif kind==5:
            if interface is None or len(d)!=7 or d[2]&0x70 or not(d[2]&15) or d[3]!=2 or d[2]in addresses:raise R.Rejected('wire bulk endpoint')
            size=struct.unpack_from('<H',d,4)[0]
            if size not in (64,512,1024) or packet not in (None,size):raise R.Rejected('wire packet size')
            packet=size;addresses.append(d[2]);companion_pending=size==1024
        elif kind==0x30:
            if not companion_pending or d!=bytes([6,0x30,0,0,0,0]):raise R.Rejected('wire SS companion')
            companion_pending=False
        else:raise R.Rejected('wire descriptor kind')
        at+=len(d)
    if interface is None or companion_pending or len(addresses)!=interface[4]:raise R.Rejected('wire item count')
    ins=[a for a in addresses if a&0x80];outs=[a for a in addresses if not(a&0x80)]
    if len(ins)!=len(outs)or not ins:raise R.Rejected('wire endpoint directions')
    return(interface[2],0,255,interface[6],interface[7],len(addresses),ins[0],outs[0],packet)

class FlowReceiver:
    def __init__(self,identity,nonce,grant):
        self.identity=identity;self.nonce=bytes(nonce);self.grant=sha256(grant.encode('ascii')).digest()
        self.previous=bytes(32);self.count=0;self.pending=None;self.complete=False;self.terminal=False;self.rows=[]
        self.calls={};self.body_bytes=0;self.body_tag=None;self.location=None;self.nodes={};self.pending_subject=None
        self.control_only=False;self.descriptor=None

    def descriptor_record(self,data):
        control,total,copied=struct.unpack_from('<III',data,252)
        policy,configs=struct.unpack_from('<II',data,308)
        raw=data[320:320+copied]
        if control>1 or copied>128 or any(data[320+copied:448]) or any(data[316:320]):raise R.Rejected('descriptor bounds/reserved')
        if sha256(raw).digest()!=data[264:296]:raise R.Rejected('descriptor raw digest')
        if copied>=9 and struct.unpack_from('<H',raw,2)[0]!=total:raise R.Rejected('descriptor declared length')
        if not control:
            profile=struct.unpack_from('<8BHBB',data,296)
            number,alt,cls,sub,proto,eps,epin,epout,packet,pin,pout=profile
            if policy or copied!=total or not 9<=copied<=128 or configs&255!=1 or not(configs>>8&255) or configs>>16 or raw[5]!=(configs>>8&255):raise R.Rejected('descriptor acceptance metadata')
            if alt or cls!=255 or eps not in (2,4) or not 0x81<=epin<=0x8f or not 1<=epout<=15 or packet not in (64,512,1024) or not 1<=pin<=eps or not 1<=pout<=eps or pin==pout:raise R.Rejected('descriptor pipe profile')
            if tuple(profile[:9])!=derived_profile(raw):raise R.Rejected('raw wire differs from claimed profile')
        elif policy!=7:raise R.Rejected('control-only path lacks explicit policy mismatch')
        self.control_only=bool(control);self.descriptor=data[252:448]

    def accept(self,data):
        if len(data)!=512 or data[:8]!=b'FX3FLOW2' or self.terminal:raise R.Rejected('flow size/magic/terminal')
        schema,point,sequence,op,status=struct.unpack_from('<IIQII',data,8)
        if schema!=2 or point not in range(4) or sequence!=self.count+1 or sequence>512:raise R.Rejected('flow schema/sequence')
        if struct.unpack_from('<IIQQ',data,32)!=(self.identity.uid,self.identity.pid,self.identity.sec,self.identity.usec):raise R.Rejected('flow helper incarnation')
        if data[56:72]!=self.nonce or data[72:104]!=self.grant:raise R.Rejected('flow nonce/grant')
        if data[448:480]!=self.previous or sha256(data[:480]).digest()!=data[480:]:raise R.Rejected('flow chain/digest')
        if self.descriptor is not None and data[252:448]!=self.descriptor:raise R.Rejected('descriptor changed after binding')
        returned,known,count,raw,pending,vendor=struct.unpack_from('<IIIiII',data,104)
        if status>8 or returned>1 or known>1 or vendor>1:raise R.Rejected('flow bounded native fields')
        if point==0:
            if self.pending is not None or op not in range(1,12) or pending!=op or returned or known or count or raw:raise R.Rejected('flow call-before')
            registry,location,product=struct.unpack_from('<QII',data,160);vid=product&65535;pid=product>>16;tag=data[176:208]
            if not registry or not location or vid!=0x054c or pid not in (0x0da1,0x0336) or tag==bytes(32):raise R.Rejected('flow current-node identity')
            if self.body_tag is None:self.body_tag=tag;self.location=location
            if self.body_tag!=tag or self.location!=location:raise R.Rejected('flow body/port changed')
            if pid in self.nodes and self.nodes[pid]!=registry and op!=9:raise R.Rejected('flow stale generation')
            if op!=9:self.nodes[pid]=registry
            self.pending_subject=data[152:208]
            self.pending=op
        elif point==1:
            if self.pending!=op or op not in range(1,12):raise R.Rejected('flow unmatched return')
            if op==11:
                if data[160:208]!=self.pending_subject[8:]:raise R.Rejected('discovery changed physical subject')
                if status==0:self.descriptor_record(data)
            elif data[152:208]!=self.pending_subject:raise R.Rejected('flow return changed call subject')
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
            if op in (50,52):
                if self.pending is not None or (taken,normal,disposed,retained,finished,driver)!=(1,1,1,0,1,1):raise R.Rejected('flow incomplete terminal state')
                expected_service={11:1,10:1,8:1}if op==52 else{11:1,1:1,2:7,3:7,4:1,5:1,7:1,8:1}
                for pid,expected in [(0x0da1,{1:1,2:7,3:7,8:1,9:1}),(0x0336,expected_service)]:
                    if any(self.calls.get((pid,kind),0)!=n for kind,n in expected.items()):raise R.Rejected('flow missing native exchanges')
                if op==50:
                    if self.control_only or self.body_bytes!=88 or struct.unpack_from('<II',data,208)!=(88,1):raise R.Rejected('flow missing bounded read')
                elif not self.control_only or self.body_bytes or any(self.calls.get((0x0336,k),0)for k in [1,2,3,4,5,6,7]) or any(data[208:248]):raise R.Rejected('control-only flow performed data work')
                if self.nodes.get(0x0da1)==self.nodes.get(0x0336):raise R.Rejected('flow generation reused')
                self.complete=True
            elif op!=51:raise R.Rejected('flow terminal kind')
            self.terminal=True
        self.count=sequence;self.previous=data[480:]
        self.rows.append(dict(sequence=sequence,op=op,point=point,status=status,returned=returned,count=count,raw_return=raw,
                              camera_authentication_proven=False,camera_threads_proven=False))
        return self.rows[-1]
