#!/usr/bin/env python3
"""Original caller/44-byte reply producers; no backend, logger or transport stub."""
from pathlib import Path
import argparse,datetime,hashlib,json,struct,sys,traceback
STAGE=Path(__file__).resolve().parent;BASE=STAGE.parent;ROOT=BASE.parents[1]
sys.path.insert(0,str(BASE/'stage110-native-OSAL-envelope'));import osal_envelope as prev
maps=prev.maps;core=prev.prev;pp,r,im=prev.pp,prev.r,prev.im
AV,DF,MPR,LIBC=core.AV,core.DF,core.MPR,core.LIBC
SP=core.SP;DBASE=0x50000000;CBASE=core.CBASE
SELF=pp.SCRATCH+0x5000;MANAGER=pp.SCRATCH+0x6000;PCTRL=pp.SCRATCH+0x6100;VT=pp.SCRATCH+0x6200
ACK=pp.SCRATCH+0x6400;COMP=pp.SCRATCH+0x6500;WRAP=pp.SCRATCH+0x6800;DEBUG=pp.SCRATCH+0x6a00
SOURCE=0x80c70047;MANAGER_ID=0x8055001f
PRIOR=prev.STAGE/'final-receipt.json';PRIOR_SHA='e97c5e83f17c24edc8f983b0abe5541abf9947497f1126be19f04542bcdfebfb'
reg=core.reg
def sha(b):return hashlib.sha256(b).hexdigest()

class AVGuest(core.Guest):
    def __init__(self,seed):
        allowed=[(0xb2d40,0xb2de0),(0xb2c4c,0xb2c80),(0xb1dfc,0xb20fc),(0x127890,0x1278d4),
            (0x13846c,0x138dd0)]
        for name in ('_ZN20InfraAvbbcMsgManager9GetOsalIdEv','_ZN15AvbbcLogManager14ConvertKey2DefEj',
            '_ZN24ExcludionEnvironmentUtil16ConvertSetSrcQidEjj','_ZN24ExcludionEnvironmentUtil18ConvertOsalSendQidEj',
            '_ZN11ObjAvbbcCmn15CheckAndHookMsgEjjN10DefBizTest8MSG_TYPEEPvj'):
            s=AV.symbols[name];allowed.append((s['va'],s['va']+s['size']))
        allowed.extend((s['va'],s['va']+s['size']) for name,s in AV.symbols.items() if name.startswith('_ZN22InfraAvbbcErrConverter') and s['size'])
        super().__init__(AV,seed,allowed)
        self.boundaries={0xb2da8:'before_unbound_status100b_getter',0x9f280:'before_unexecuted_AV_Log0',
            0x9bf10:'before_unexecuted_AV_Log1',0x9e870:'before_unexecuted_AV_printf',
            0x9e710:'before_unexecuted_next_object_allocation',0xb2c80:'after_original_Comp_constructor'}
        maps.map_image(self,DF,DBASE);maps.map_image(self,LIBC,CBASE)
        for name in ('_ZN16DataflowInfraMsgC1Ev','_ZN16DataflowInfraMsg12SetGlobalMsgEPvt',
            '_ZN16DataflowInfraMsg8SetSrcIdEj','_ZN19DataflowInfraSenderC1Ev','_ZN19DataflowInfraSender9SendASyncEjP16DataflowInfraMsg'):
            s=DF.symbols[name];self.allowed.append((DBASE+s['va'],DBASE+s['va']+s['size']))
        for name in ('memcpy','memset'):
            s=LIBC.symbols[name];self.allowed.append((CBASE+s['va'],CBASE+s['va']+s['size']))
        self.uc.mem_write(0x1b2720,struct.pack('<Q',DEBUG));self.uc.mem_write(DEBUG,bytes(4))
        self.uc.mem_write(SELF+8,struct.pack('<QQ',MANAGER,PCTRL));self.uc.mem_write(SELF+0x2c,struct.pack('<I',SOURCE))
        self.uc.mem_write(SELF+0x1b8,b'\x20');self.uc.mem_write(MANAGER+8,struct.pack('<I',MANAGER_ID))
        self.uc.mem_write(PCTRL,struct.pack('<Q',VT));self.uc.mem_write(VT+0xa0,bytes(8))
        self.images=[(bias+s['p_vaddr'],bytes(self.uc.mem_read(bias+s['p_vaddr'],s['p_memsz'])))
            for native,bias in ((AV,0),(DF,DBASE),(LIBC,CBASE)) for s in native.segments]

    def code(self,u,pc,n,user):
        if pc in self.boundaries:
            self.pcs.append(hex(pc));self.abort('boundary: '+self.boundaries[pc]);return
        symbol=AV.plt.get(pc)
        if DBASE<=pc<DBASE+0x100000:symbol=DF.plt.get(pc-DBASE)
        if symbol:
            if symbol.startswith('osal_'):
                self.pcs.append(hex(pc));self.abort('boundary: before_unexecuted_'+symbol);return
            target=None
            if symbol in DF.symbols:target=DBASE+DF.symbols[symbol]['va']
            elif symbol in ('memcpy','memset'):target=CBASE+LIBC.symbols[symbol]['va']
            if target is not None and any(a<=target<z for a,z in self.allowed):
                self.pcs.append(hex(pc));self.steps+=1
                self.calls.append({'original_symbol_binding':symbol,'PLT':hex(pc),'target':hex(target),
                    'args_x0_x3':[hex(u.reg_read(reg('x'+str(i)))) for i in range(4)],'declared_binding_not_live_loader_proof':True})
                u.reg_write(reg('pc'),target);return
        return super().code(u,pc,n,user)

    def phase(self,label,entry,outputs=(),**regs):
        before_stack=bytes(self.uc.mem_read(pp.STACK_BASE,pp.STACK_SIZE));before=bytes(self.uc.mem_read(pp.SCRATCH,0x10000))
        for name,value in regs.items():self.uc.reg_write(reg(name),value)
        self.reason=None;self.steps=0;self.pcs=[];self.calls=[];self.stores=[];self.writes=[];self.reads=[]
        self.uc.emu_start(entry,0,count=10000,timeout=1000000)
        assert self.reason and self.reason.startswith('boundary: '),(self.reason,hex(self.uc.reg_read(reg('pc'))))
        for w in self.stores:
            a,n=int(w['address'],16),w['size'];assert SP-0x800<=a and a+n<=SP or any(x<=a and a+n<=z for x,z in outputs),w
        after_stack=bytes(self.uc.mem_read(pp.STACK_BASE,pp.STACK_SIZE))
        assert after_stack[:SP-0x800-pp.STACK_BASE]==before_stack[:SP-0x800-pp.STACK_BASE]
        assert after_stack[SP-pp.STACK_BASE:]==before_stack[SP-pp.STACK_BASE:]
        after=bytes(self.uc.mem_read(pp.SCRATCH,0x10000))
        assert all(any(a<=pp.SCRATCH+i<z for a,z in outputs) for i,(a,b) in enumerate(zip(before,after)) if a!=b)
        for a,data in self.images:assert bytes(self.uc.mem_read(a,len(data)))==data
        assert all('stub' not in x for x in self.calls)
        return {'label':label,'entry':hex(entry),'reason':self.reason,'stop_pc':hex(self.uc.reg_read(reg('pc'))),
            'pcs':self.pcs,'original_calls':self.calls,'stores':self.stores,
            'whole_stack_outside_declared2048_bytes_unchanged':True,'whole_scratch_outside_outputs_unchanged':True,
            'whole_original_relocated_images_unchanged':True,'success_output_return_or_logger_adapters':False}

def capture_and_advance(m,events):
    assert events[-1]['reason']=='boundary: before_unexecuted_AV_Log1'
    obj=m.uc.reg_read(reg('x21'));state,length=struct.unpack('<IH',bytes(m.uc.mem_read(obj+8,6)))
    assert state==2 and length==44
    wire=bytes(m.uc.mem_read(obj+0x18,44));source=struct.unpack('<I',bytes(m.uc.mem_read(obj+0x10,4)))[0]
    assert source==MANAGER_ID
    events.append(m.phase('independent post-Log1 original send arguments to OSAL allocation stop',0x138b60))
    assert events[-1]['reason']=='boundary: before_unexecuted_osal_valloc_msg_wait'
    args=[m.uc.reg_read(reg('x'+str(i))) for i in range(4)]
    assert args[0]==SOURCE and args[2]==44 and args[3]==1
    assert bytes(m.uc.mem_read(obj+0x18,44))==wire
    return {'wire44_hex':wire.hex(),'Dataflow_raw_state':state,'Dataflow_length':length,
        'Dataflow_source_ID':hex(source),'destination_ID':hex(args[0]),'native_allocation_request_length':args[2],
        'wire_MID':struct.unpack_from('<I',wire,0x24)[0],'wire_subcode':struct.unpack_from('<H',wire,2)[0],
        'wire_opaque_status':struct.unpack_from('<I',wire,0x14)[0]}

def error_reply(seed,status):
    m=AVGuest(seed)
    try:
        events=[m.phase('original ExecErrorCommand zeroes reply storage before unbound status getter',0xb2d40,
            sp=SP,x30=pp.STOP,x0=SELF)]
        assert events[-1]['reason']=='boundary: before_unbound_status100b_getter'
        fp=m.uc.reg_read(reg('x29'));assert fp==SP-0x60
        m.uc.mem_write(fp+0x2c,struct.pack('<I',status))
        events.append(m.phase('independent declared status input; original reply construction and manager framing',0xb2dac))
        out=capture_and_advance(m,events)
        assert (out['wire_MID'],out['wire_subcode'],out['wire_opaque_status'])==(0x4e0,1,status)
        return {'seed':seed,'producer':'ExecErrorCommand','declared_status_input':status,**out,'events':events,
            'status_input_not_real_getter_return_or_hardware_result':True,'actual_status_getter_logs_allocation_or_send_executed':False}
    finally:m.close()

def child_reply(seed,template,kind):
    m=AVGuest(seed)
    try:
        # ErrorCommand's original44-byte packet is an explicit template input to
        # these child methods, not proof of their normal backend input producer.
        storage=bytes([seed])*8+template+bytes([seed])*4;assert len(storage)==56
        m.uc.mem_write(WRAP,storage)
        if kind=='Ack':
            events=[m.phase('independent original parent post-allocation Ack constructor arguments and constructor',0xb2c4c,
                outputs=[(ACK,ACK+0x28)],sp=SP,x29=SP,x30=pp.STOP,x0=ACK,x19=SELF)]
            assert events[-1]['reason']=='boundary: before_unexecuted_next_object_allocation'
            assert struct.unpack('<HHB',bytes(m.uc.mem_read(ACK+0x20,5)))==(0x8502,0,1)
            entry,after,obj=0xb1dfc,0xb1e94,ACK
        else:
            events=[m.phase('independent original parent post-allocation Comp constructor arguments and constructor',0xb2c70,
                outputs=[(COMP,COMP+0x20)],sp=SP,x29=SP,x30=pp.STOP,x0=COMP,x19=SELF)]
            assert events[-1]['reason']=='boundary: after_original_Comp_constructor'
            entry,after,obj=0xb2014,0xb2098,COMP
        events.append(m.phase('original '+kind+' ExecCmd conversion and subcode handling to log boundary',entry,
            outputs=[(WRAP,WRAP+56)],sp=SP,x30=pp.STOP,x0=obj,x1=WRAP))
        assert events[-1]['reason']=='boundary: before_unexecuted_AV_Log0'
        events.append(m.phase('independent post-Log0 '+kind+' original manager message framing',after))
        out=capture_and_advance(m,events)
        assert out['wire_MID']==0x4e0 and out['wire_subcode']==(0 if kind=='Ack' else 1)
        assert bytes(m.uc.mem_read(WRAP,8))==storage[:8] and bytes(m.uc.mem_read(WRAP+52,4))==storage[52:]
        return {'seed':seed,'producer':kind,'template44_hex':template.hex(),'template_origin':'independent ErrorCommand output fixture',
            **out,'events':events,'actual_normal_child_input_hardware_event_log_allocation_or_send_proven':False}
    finally:m.close()

class MPRGuest(core.Guest):
    def __init__(self,seed):
        super().__init__(MPR,seed,[(0xd18d8,0xd1954),(0xd1b74,0xd1b80),(0xd1ba4,0xd1bc0),
            (0xab3ac,0xab3bc),(0x27f494,0x27fa34)])
        self.boundaries={0xc8c70:'before_original_ExecEncOpen_logger',0x7c5f0:'before_unexecuted_normal_mutex_lock',
            0x7d8b0:'before_unexecuted_normal_mutex_unlock',0x7c350:'before_unexecuted_Codec_EncOpen'}
        # Bind wrapper ranges from original symbols rather than guessed offsets.
        for name in ('_ZN3mpr6thread10normalLock4lockEv','_ZN3mpr6thread10normalLock6unlockEv'):
            s=MPR.symbols[name];self.allowed.append((s['va'],s['va']+s['size']))

def caller(seed):
    m=MPRGuest(seed)
    try:
        execution=pp.SCRATCH+0x1000;m.uc.mem_write(execution+0x77c,struct.pack('<I',15))
        events=[m.phase('original ExecEncOpen prologue and saved reply buffer address',0xd18d8,
            complete=False,sp=SP,x30=pp.STOP,x0=execution)]
        assert events[-1]['reason']=='boundary: before_original_ExecEncOpen_logger'
        fp=m.uc.reg_read(reg('x29'));assert fp==SP-0x1c0 and m.uc.reg_read(reg('x23'))==fp+0x60
        events.append(m.phase('independent post-log original reply buffer zeroing before normal lock',0xd1930,complete=False))
        assert events[-1]['reason']=='boundary: before_unexecuted_normal_mutex_lock'
        assert bytes(m.uc.mem_read(fp+0x60,48))==bytes(48)
        events.append(m.phase('independent original DMM-scope normal unlock before Open preparation',0xd1b74,complete=False))
        assert events[-1]['reason']=='boundary: before_unexecuted_normal_mutex_unlock'
        events.append(m.phase('independent original single-stream EncOpen argument block',0xd1ba4,complete=False))
        assert events[-1]['reason']=='boundary: before_unexecuted_Codec_EncOpen'
        args=[m.uc.reg_read(reg('x'+str(i))) for i in range(6)]
        assert args==[fp+0x90,0x20,15,1,0,fp+0x60]
        return {'seed':seed,'original_single_stream_arguments':[hex(x) for x in args],
            'nonnull_reply_pointer_from_original_prologue':hex(args[5]),'reply_storage48_zeroed_by_native_code':True,
            'events':events,'logs_locks_DMM_builders_Codec_EncOpen_or_actual_call_proven':False}
    finally:m.close()

def classify(seed,wire):
    m=MPRGuest(seed)
    try:
        mid=struct.unpack_from('<I',wire,0x24)[0];sub=struct.unpack_from('<H',wire,2)[0]
        e=m.phase('original MPR classifier on AV-produced44-byte packet fields',0x27f494,
            sp=SP,x30=pp.STOP,x0=mid,x1=sub)
        factor=e['return_u32_if_returned'];assert factor==(1 if sub==0 else 0x1001)
        return {'seed':seed,'wire44_sha256':sha(wire),'MID':mid,'subcode':sub,'original_factor':factor,
            'opaque_status':struct.unpack_from('<I',wire,0x14)[0],'events':[e],
            'no44_to48_copy_or_real_callback_transport_claim':True}
    finally:m.close()

def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    im.volume();assert sha(PRIOR.read_bytes())==PRIOR_SHA
    for f in json.loads(PRIOR.read_text())['files']:
        data=(ROOT/f['path']).read_bytes();assert len(data)==f['bytes'] and sha(data)==f['sha256']
    assert (BASE/'GOAL_STATUS.json').read_bytes()==(STAGE/'goal-status-before.json').read_bytes()
    a.out.mkdir(exist_ok=False);(a.out/'executed-source.py').write_bytes(Path(__file__).read_bytes())
    try:
        callers=[];produced=[];classified=[]
        for seed in (0xa5,0xc3):
            callers.append(caller(seed))
            for status in (0,2):
                e=error_reply(seed,status);produced.append(e);wire=bytes.fromhex(e['wire44_hex'])
                produced.extend(child_reply(seed,wire,kind) for kind in ('Ack','Comp'))
        for c in produced:classified.append(classify(c['seed'],bytes.fromhex(c['wire44_hex'])))
        phases=sum(len(c['events']) for c in callers+produced+classified)
        j={'status':'PASS_NATIVE_SINGLE_STREAM_REPLY_POINTER_AND44_BYTE_PRODUCER_CLASSIFICATION_SCOPE',
            'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'callers':callers,
            'produced':produced,'classified':classified,'bounded_phases':phases,
            'normal_MC_backend_child_input_and44_wire_to48_storage_lifetime_proven':False,
            'actual_logger_getter_mutex_allocator_OSAL_send_or_success_return_adapters_executed':False,
            'Windows_UU_camera_operations':False,'goal_complete':False,'persistent_write_release':False}
        (a.out/'open-reply-results.json').write_text(json.dumps(j,ensure_ascii=False,indent=2)+'\n')
        print(json.dumps({'status':j['status'],'callers':len(callers),'produced':len(produced),'classified':len(classified),'bounded_phases':phases}))
    except BaseException:
        (a.out/'attempt-failure.json').write_text(json.dumps({'passing_result':False,'traceback':traceback.format_exc()},indent=2)+'\n');raise
if __name__=='__main__':main()
