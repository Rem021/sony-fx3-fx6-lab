"""Strict per-helper flow frames, after live kernel peer/self-image checking.

The supervisor saves each raw672B frame before calling this decoder.
No saved file is itself a live origin proof or a camera acceptance result.
"""
from hashlib import sha256
import struct
import receipt_receiver as R

ACQUISITION_STEPS={
    0:'not_reached',201:'device_plugin',202:'device_interface_query',203:'device_open',
    204:'configuration_count',205:'active_configuration',206:'configuration_descriptor',
    207:'interface_iterator',208:'interface_plugin',209:'interface_query',210:'interface_open',
    101:'interface_number',102:'alternate_setting',103:'interface_class',104:'interface_subclass',
    105:'interface_protocol',106:'endpoint_count',111:'pipe_1',112:'pipe_2',113:'pipe_3',114:'pipe_4'}

READ0_HEADER_REASONS={
    0:'not_evaluated',1:'ok',2:'short_count',3:'size_mismatch',4:'pfunc_mismatch',
    5:'sequence_mismatch',6:'version_mismatch',7:'micon_mismatch',8:'offset_mismatch',
    9:'response_mismatch',10:'multiple_mismatch'}
READ0_HEADER_FIELDS=('size','pFunc','sequence','version','miconType','offsetType','response')

def header_mismatch_fields(mask):
    if type(mask)is not int or not 0<=mask<=0x7f:raise R.Rejected('read0 header mask bounds')
    return tuple(name for bit,name in enumerate(READ0_HEADER_FIELDS) if mask&(1<<bit))

def read0_header_record(data,op,point,status,returned,known,count):
    """Bounded non-payload header classification check. Proves no live camera state."""
    if len(data)!=672:raise R.Rejected('read0 bounds')
    body_bytes,reply_valid,reason,mask,reserved=struct.unpack_from('<IBBBB',data,208)
    if reply_valid not in (0,1) or reason not in READ0_HEADER_REASONS or mask>0x7f or reserved:
        raise R.Rejected('read0 header bounds/reserved')
    if reason in (0,1,2) and mask:raise R.Rejected('read0 non-field reason carries mask')
    if reason in range(3,10) and mask!=(1<<(reason-3)):raise R.Rejected('read0 single-field reason/mask mismatch')
    if reason==10 and (not mask or not(mask&(mask-1))):raise R.Rejected('read0 multiple reason lacks multiple bits')
    if op==5 and point==0 and (reason or mask):raise R.Rejected('read0 header reason before return')
    if op==5 and point==1:
        if not returned or status!=0:
            if reason or mask:raise R.Rejected('unreturned or failed read0 header call carries reason')
        elif not known or count!=12:
            if (reason,mask)!=(2,0):raise R.Rejected('short read0 header call misclassified')
        elif reason in (0,2):
            raise R.Rejected('full 12B read0 header call lacks field verdict')
    return dict(reason=reason,name=READ0_HEADER_REASONS[reason],mask=mask,
                fields=header_mismatch_fields(mask),body_bytes=body_bytes,reply_valid=reply_valid)

def acquisition_record(data,op,point,status,returned,call_raw):
    """Format evidence only. Does not create live origin or prove device access."""
    if len(data)!=672:raise R.Rejected('acquisition bounds')
    step,raw=struct.unpack_from('<Ii',data,592)
    if step not in ACQUISITION_STEPS or (not step and raw):raise R.Rejected('acquisition step/raw shape')
    if op==11 and point==0 and (step or raw):raise R.Rejected('acquisition evidence before call')
    if op==11 and point==1 and returned:
        if raw!=call_raw:raise R.Rejected('acquisition raw differs from returned call')
        if status==0 and not step:raise R.Rejected('successful acquisition lacks a native substep')
    disposition,open_raw=struct.unpack_from('<Ii',data,600)
    if disposition not in (0,1,2):raise R.Rejected('device open disposition')
    if (disposition==1 and open_raw)or(disposition==2 and open_raw!=-536870203):raise R.Rejected('device capability/raw mismatch')
    if (step in (0,201,202)) and (disposition or open_raw):raise R.Rejected('device open before its substep')
    if step==203 and open_raw!=raw:raise R.Rejected('device open substep raw mismatch')
    if step==203 and disposition!=(1 if open_raw==0 else 2 if open_raw==-536870203 else 0):raise R.Rejected('device open result misclassified')
    if step and step not in (201,202,203)and not disposition:raise R.Rejected('later acquisition without device access disposition')
    return dict(step=step,name=ACQUISITION_STEPS[step],raw_return=raw,
                device_open_disposition=disposition,device_open_raw=open_raw)

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
        self.last_data=None;self.acquisition=None;self.read0_header=None;self.body_hmac=None

    def idle_held_exit_evidence(self):
        """Flow-shape check only, alongside a private native idle-exit record.
        Does not prove live peer origin, camera return, or native pointers."""
        if not self.terminal or self.complete or self.pending is not None or self.last_data is None:return False
        expected={(0x0da1,1):1,(0x0da1,2):7,(0x0da1,3):7,(0x0da1,8):1}
        if self.calls!=expected or self.service_node or self.return_node or self.descriptor is not None:return False
        if self.witness_state not in (2,6):return False
        if struct.unpack_from('<6I',self.last_data,128)!=(1,1,0,0,1,0):return False
        disposals=[r for r in self.rows if r['op']==8 and r['point']==1]
        return len(disposals)==1 and disposals[0]['returned']==1 and disposals[0]['status'] in (0,5)

    def association(self,data,op,point,status):
        physical,logical=struct.unpack_from('<QQ',data,448);kind,flags=struct.unpack_from('<II',data,464)
        source,service,returned_node,armed,deadline,service_ns,return_ns=struct.unpack_from('<7Q',data,488)
        state,observations=struct.unpack_from('<II',data,544);origin=data[552:584];last=struct.unpack_from('<Q',data,584)[0]
        registry,location,product=struct.unpack_from('<QII',data,160);vid=product&65535;pid=product>>16;tag=data[176:208]
        if state>6 or observations>50 or kind>2:raise R.Rejected('association fields')
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
        elif op in (64,65) and point==2:
            if state!=6 or status!=4 or observations!=self.observations or self.pending is not None:
                raise R.Rejected('invalid expired-window marker')
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
        if len(data)!=672 or data[:8]!=b'FX3FLOW6' or self.terminal:raise R.Rejected('flow size/magic/terminal')
        schema,point,sequence,op,status=struct.unpack_from('<IIQII',data,8)
        if schema!=6 or point not in range(4) or sequence!=self.count+1 or sequence>512:raise R.Rejected('flow schema/sequence')
        if struct.unpack_from('<IIQQ',data,32)!=(self.identity.uid,self.identity.pid,self.identity.sec,self.identity.usec):raise R.Rejected('flow helper incarnation')
        if data[56:72]!=self.nonce or data[72:104]!=self.grant:raise R.Rejected('flow nonce/grant')
        if data[608:640]!=self.previous or sha256(data[:640]).digest()!=data[640:]:raise R.Rejected('flow chain/digest')
        if self.descriptor is not None and data[252:448]!=self.descriptor:raise R.Rejected('descriptor changed after binding')
        returned,known,count,raw,pending,vendor=struct.unpack_from('<IIIiII',data,104)
        if status>8 or returned>1 or known>1 or vendor>1:raise R.Rejected('flow bounded native fields')
        acquisition=acquisition_record(data,op,point,status,returned,raw)
        if self.acquisition is not None and acquisition!=self.acquisition:raise R.Rejected('acquisition metadata changed after return')
        if op==11 and point==1 and returned:self.acquisition=acquisition
        elif self.acquisition is None and acquisition['step']:raise R.Rejected('acquisition evidence before returned acquisition')
        read0=read0_header_record(data,op,point,status,returned,known,count)
        if self.read0_header is not None and (read0['reason'],read0['mask'])!=(self.read0_header['reason'],self.read0_header['mask']):
            raise R.Rejected('read0 header metadata changed after return')
        if self.read0_header is not None and self.read0_header['reason']!=1 and op in (6,7,50):
            raise R.Rejected('flow continued after read0 header rejection')
        if op==5 and point==1:
            if self.read0_header is not None or self.calls.get((0x0336,4),0)!=1 or self.control_only:
                raise R.Rejected('unexpected read0 header return')
            self.read0_header=dict(reason=read0['reason'],name=read0['name'],mask=read0['mask'],fields=read0['fields'])
        elif self.read0_header is None and (read0['reason'] or read0['mask']):
            raise R.Rejected('read0 header evidence before returned header read')
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
                    if self.read0_header is None or self.read0_header['reason']!=1 or not known or not 0<count<=88 or self.body_bytes+count>88:
                        raise R.Rejected('flow body progress')
                    if status==0:self.body_bytes+=count
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
                    if self.control_only or self.body_bytes!=88 or struct.unpack_from('<IBBBB',data,208)!=(88,1,1,0,0) or not any(data[216:248]):
                        raise R.Rejected('flow missing bounded read')
                elif not self.control_only or self.body_bytes or any(self.calls.get((0x0336,k),0)for k in [1,2,3,4,5,6,7]) or any(data[208:248]):raise R.Rejected('control-only flow performed data work')
                if self.nodes.get(0x0da1)==self.nodes.get(0x0336):raise R.Rejected('flow generation reused')
                self.complete=True
            elif op!=51:raise R.Rejected('flow terminal kind')
            self.terminal=True
        if self.body_bytes<88 or (op==6 and point in (0,1)):
            if read0['body_bytes'] or read0['reply_valid'] or any(data[216:248]):raise R.Rejected('premature read0 body receipt')
        else:
            if (read0['body_bytes'],read0['reply_valid'],read0['reason'],read0['mask'])!=(88,1,1,0) or not any(data[216:248]):
                raise R.Rejected('missing or invalid read0 body receipt')
            if self.body_hmac is not None and data[216:248]!=self.body_hmac:raise R.Rejected('read0 body HMAC changed')
            self.body_hmac=bytes(data[216:248])
        self.count=sequence;self.previous=data[640:];self.last_data=bytes(data)
        self.rows.append(dict(sequence=sequence,op=op,point=point,status=status,returned=returned,count=count,raw_return=raw,
                              identity_basis='CONTROLLED_PHYSICAL_PORT' if self.service_kind==2 else 'SERIAL_CONTEXT',
                              camera_authentication_proven=False,camera_threads_proven=False,acquisition=acquisition,
                              read0_header=self.read0_header))
        return self.rows[-1]
