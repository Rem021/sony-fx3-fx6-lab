"""Strict per-helper flow frames, after live kernel peer/self-image checking.

The supervisor saves each raw672B frame before calling this decoder.
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
        self.port=None;self.source_node=None;self.service_node=None;self.return_node=None;self.service_kind=0
        self.witness_state=0;self.observations=0;self.window=None

    def association(self,data,op,point,status):
        physical,logical=struct.unpack_from('<QQ',data,448);kind,flags=struct.unpack_from('<II',data,464)
        source,service,returned_node,armed,deadline,service_ns,return_ns=struct.unpack_from('<7Q',data,488)
        state,observations=struct.unpack_from('<II',data,544);origin=data[552:584];last=struct.unpack_from('<Q',data,584)[0]
        registry,location,product=struct.unpack_from('<QII',data,160);vid=product&65535;pid=product>>16;tag=data[176:208]
        if any(data[592:608]) or state>6 or observations>50 or kind>2:raise R.Rejected('association fields')
        if not state:
            if any(data[448:608]) or self.witness_state or point in (0,1):raise R.Rejected('uninitialized association')
            return
        if data[472:488]!=self.nonce or not source or origin==bytes(32):raise R.Rejected('association source scope')
        if self.source_node is None:
            if state!=1 or pid!=0x0da1 or kind!=1 or tag!=origin or registry!=source or not physical or not logical or not location:
                raise R.Rejected('MSC serial baseline required before transition')
            self.source_node=source;self.port=physical;self.location=location;self.body_tag=origin
        if source!=self.source_node or origin!=self.body_tag:raise R.Rejected('origin serial context changed')
        before=self.witness_state
        if state!=before and not(before==0 and state==1):
            transition={(1,2):(60,2),(2,3):(61,2),(3,4):(62,2),(4,5):(63,2)}
            if state!=6 and transition.get((before,state))!=(op,point):raise R.Rejected('association transition without marker')
        if state in (1,2,3,4,5) and flags!={1:1,2:3,3:7,4:15,5:31}[state]:raise R.Rejected('association flags')
        if state==1:
            if any([service,returned_node,armed,deadline,service_ns,return_ns,last,observations]):raise R.Rejected('premature transition fields')
        elif state!=6:
            if not armed or not armed<deadline or deadline-armed>5_000_000_000 or not armed<=last<deadline:
                raise R.Rejected('transition window')
            if state in (3,4,5) and (not service or service==source or not service_ns):raise R.Rejected('missing service observation')
            if state==5 and (not returned_node or returned_node in (source,service) or not armed<=return_ns<deadline):raise R.Rejected('missing returned MSC observation')
        if (op,point) in [(60,2),(62,2)]:
            if observations or self.pending is not None:raise R.Rejected('armed transition while call pending')
            if op==60 and any(self.calls.get((0x0da1,k),0)!=n for k,n in {1:1,2:7,3:7,8:1}.items()):raise R.Rejected('transition before MSC exchange/disposal')
            if op==62 and (self.calls.get((0x0336,8),0)!=1 or self.calls.get((0x0336,7),0)+self.calls.get((0x0336,10),0)!=1):raise R.Rejected('return before SERVICE end/disposal')
            self.window=(armed,deadline);self.observations=0
        elif op in (61,63) and point==2:
            if observations!=self.observations+1:raise R.Rejected('missing cache sample')
            self.observations=observations
        elif observations!=self.observations:raise R.Rejected('cache sample count changed outside observation')
        if state in (2,3,4,5) and self.window!=(armed,deadline):raise R.Rejected('transition deadline changed')
        if service:
            if self.service_node not in (None,service):raise R.Rejected('service node changed')
            self.service_node=service
        if state!=6 and registry:
            if physical!=self.port or not logical or vid!=0x054c:raise R.Rejected('physical anchor changed')
            if pid==0x0336:
                if kind==2:
                    if any(tag):raise R.Rejected('fabricated SERVICE serial tag')
                elif kind!=1 or tag!=origin:raise R.Rejected('unexpected SERVICE serial')
                if state in (3,4):
                    if registry!=service or self.service_kind not in (0,kind):raise R.Rejected('service subject changed')
                    self.service_kind=kind
            elif pid!=0x0da1 or kind!=1 or tag!=origin or location!=self.location:raise R.Rejected('MSC serial or location changed')
            elif state==5:
                if registry!=returned_node:raise R.Rejected('returned node differs')
                self.return_node=registry
            elif registry!=source:raise R.Rejected('unexpected MSC node before return')
        if point in (0,1) and (state==6 or not registry or not physical or not logical or (pid==0x0336 and state!=3) or (pid==0x0da1 and state not in (1,5))):
            raise R.Rejected('I/O subject lacks valid association')
        self.witness_state=state

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
        if len(data)!=672 or data[:8]!=b'FX3FLOW3' or self.terminal:raise R.Rejected('flow size/magic/terminal')
        schema,point,sequence,op,status=struct.unpack_from('<IIQII',data,8)
        if schema!=3 or point not in range(4) or sequence!=self.count+1 or sequence>512:raise R.Rejected('flow schema/sequence')
        if struct.unpack_from('<IIQQ',data,32)!=(self.identity.uid,self.identity.pid,self.identity.sec,self.identity.usec):raise R.Rejected('flow helper incarnation')
        if data[56:72]!=self.nonce or data[72:104]!=self.grant:raise R.Rejected('flow nonce/grant')
        if data[608:640]!=self.previous or sha256(data[:640]).digest()!=data[640:]:raise R.Rejected('flow chain/digest')
        if self.descriptor is not None and data[252:448]!=self.descriptor:raise R.Rejected('descriptor changed after binding')
        returned,known,count,raw,pending,vendor=struct.unpack_from('<IIIiII',data,104)
        if status>8 or returned>1 or known>1 or vendor>1:raise R.Rejected('flow bounded native fields')
        self.association(data,op,point,status)
        if point==0:
            if self.pending is not None or op not in range(1,12) or pending!=op or returned or known or count or raw:raise R.Rejected('flow call-before')
            registry,location,product=struct.unpack_from('<QII',data,160);vid=product&65535;pid=product>>16;tag=data[176:208]
            if not registry or not location or vid!=0x054c or pid not in (0x0da1,0x0336):raise R.Rejected('flow current-node association')
            if pid in self.nodes and self.nodes[pid]!=registry and op!=9:raise R.Rejected('flow stale generation')
            if op!=9:self.nodes[pid]=registry
            self.pending_subject=(data[152:208],data[448:472])
            self.pending=op
        elif point==1:
            if self.pending!=op or op not in range(1,12):raise R.Rejected('flow unmatched return')
            if op==11:
                if data[160:208]!=self.pending_subject[0][8:] or data[448:472]!=self.pending_subject[1]:raise R.Rejected('discovery changed physical subject')
                if status==0:self.descriptor_record(data)
            elif (data[152:208],data[448:472])!=self.pending_subject:raise R.Rejected('flow return changed call subject')
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
                if self.witness_state!=5 or not self.return_node or not self.service_kind:raise R.Rejected('complete flow lacks return serial observation')
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
        self.count=sequence;self.previous=data[640:]
        self.rows.append(dict(sequence=sequence,op=op,point=point,status=status,returned=returned,count=count,raw_return=raw,
                              identity_basis='CONTROLLED_PHYSICAL_PORT' if self.service_kind==2 else 'SERIAL_CONTEXT',
                              camera_authentication_proven=False,camera_threads_proven=False))
        return self.rows[-1]
