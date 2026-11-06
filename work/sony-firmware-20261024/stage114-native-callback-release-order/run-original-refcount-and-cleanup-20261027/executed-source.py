#!/usr/bin/env python3
"""Original callback cleanup and distinct message/node lifetimes in guest RAM.

Native allocators provide header geometry under declared client/block inputs.
Native free/finish paths run through bounded reference arithmetic only; actual
pool services, task lookup, user copies, locks and ioctl are never executed.
"""
from pathlib import Path
import argparse,datetime,hashlib,json,struct,sys,traceback
STAGE=Path(__file__).resolve().parent;BASE=STAGE.parent;ROOT=BASE.parents[1]
sys.path.insert(0,str(BASE/'stage113-native-uipc-mapping-guards'));import mapping_guards as prev
old=prev.prev;core,pp,r,im=prev.core,prev.pp,prev.r,prev.im;reg=core.reg
KBASE,RBASE,BBASE,SP=prev.KBASE,prev.RBASE,prev.BBASE,prev.SP
MBASE=old.MBASE;CLIENT,OUT,BLOCK=old.CLIENT,old.OUT,old.BLOCK;HEADER=BLOCK+40;DATA=BLOCK+64
NODE,CTX=prev.NODE,prev.CTX;CHAIN=pp.SCRATCH+0x6800
ELF,MODULE,MODULE_SHA=prev.ELF,prev.MODULE,prev.MODULE_SHA
PRIOR=BASE/'stage113-native-uipc-mapping-guards/final-receipt.json'
PRIOR_SHA='95549373fb47a5d9c22da3b9b6b01c4431cd7a92299c1d82ee7e25981341b363'
def sha(b):return hashlib.sha256(b).hexdigest()
def q(m,a):return struct.unpack('<Q',bytes(m.uc.mem_read(a,8)))[0]
def h(m,a):return struct.unpack('<H',bytes(m.uc.mem_read(a,2)))[0]
def pq(m,a,v):m.uc.mem_write(a,struct.pack('<Q',v))
def ph(m,a,v):m.uc.mem_write(a,struct.pack('<H',v))

def images():
    text=bytearray(prev.TEXT);proof=[];sy=ELF.get_section_by_name('.symtab')
    for sec in ELF.iter_sections():
        if sec['sh_type']!='SHT_RELA' or ELF.get_section(sec['sh_info']).name!='.text':continue
        for rr in sec.iter_relocations():
            if rr['r_offset'] not in (0x47b0,0x5580):continue
            s=sy.get_symbol(rr['r_info_sym']);assert rr['r_info_type']==257 and s.name=='vpool'
            assert ELF.get_section(s['st_shndx']).name=='.bss' and s['st_value']==0x3740 and rr['r_addend']==0
            at=rr['r_offset'];assert text[at:at+8]==bytes(8);value=BBASE+s['st_value']
            text[at:at+8]=struct.pack('<Q',value)
            proof.append({'text_offset':hex(at),'type':'R_AARCH64_ABS64','symbol':s.name,
                'target_section':'.bss','original_symbol_value':hex(s['st_value']),'guest_value':hex(value)})
    assert len(proof)==2;return bytes(text),proof
TEXT,ADDED_RELOCS=images()

class Guest(prev.Guest):
    def __init__(self,seed):
        super().__init__(seed)
        self.uc.mem_write(KBASE,TEXT)
        self.images=[(a,d) for a,d in self.images if a!=KBASE]+[(KBASE,TEXT)]
        old.prev.maps.map_image(self,old.MPR,MBASE)
        self.images.extend((MBASE+s['p_vaddr'],bytes(self.uc.mem_read(MBASE+s['p_vaddr'],s['p_memsz']))) for s in old.MPR.segments)
        self.allowed.extend((KBASE+a,KBASE+z) for a,z in [(0x3248,0x3518),(0x4650,0x47a0),
            (0x53c8,0x5574),(0x36e8,0x38f8),(0x968,0x9a8),(0xa70,0xa7c)])
        self.allowed.extend([(0x6970,0x6ad8),(0x3f28,0x3fb0),(0x3260,0x3318),
            (MBASE+0x2859ec,MBASE+0x285a0c)])
        self.boundaries.update({KBASE+a:n for a,n in {
            0x2938:'before_dynamic_client_lookup',0x32d8:'before_allocator_global_pool_reference',
            0x3420:'before_allocator_private_pool_call',0x3508:'before_allocator_fixed_block_call',
            0x3498:'before_allocator_configuration_log',0x4720:'before_message_private_pool_free',
            0x4768:'before_message_global_pool_free',0x478c:'before_message_fixed_block_free',
            0x5400:'before_finish_callback_lock',0x54e0:'before_finish_callback_unlock',
            0x54c4:'before_finish_private_pool_free',0x5558:'before_finish_global_pool_free',
            0x5568:'before_finish_fixed_block_free',0x29d8:'before_callback_node_retirement',
            0x2ee8:'before_missing_client_creation',0x35b8:'before_callback_chain_dispatch',
            0x382c:'before_next_callback_BLR',0x37a8:'before_next_message_private_free',
            0x38e4:'before_next_message_global_free',0x38f0:'before_next_message_fixed_free',
            0x984:'before_pending_node_unlock',0x998:'before_sync_pending_wake',
            0xa78:'before_pending_node_finish_callback_call'}.items()})
        self.boundaries.update({0x2530:'before_user_ioctl',0x2800:'before_user_cancel_type',0x32f0:'before_user_callback_BLR'})
        self.header_reads=[];self.hooks.append(self.uc.hook_add(r.unicorn.UC_HOOK_MEM_READ,self.observe_header))

    def observe_header(self,u,access,a,n,value,user):
        if BLOCK<=a<BLOCK+128 or a<BLOCK and a+n>BLOCK:
            self.header_reads.append({'pc':hex(u.reg_read(reg('pc'))),'offset':a-BLOCK,'size':n})

    def code(self,u,pc,n,user):
        if pc==MBASE+0x83370:
            assert old.MPR.plt[0x83370]=='osal_free_msg'
            target=old.OSAL.symbols['osal_free_msg']['va']
            self.pcs.append(hex(pc));self.steps+=1;self.calls.append({'original_MPR_PLT_binding':'osal_free_msg',
                'PLT':hex(pc),'target':hex(target),'args_x0_x1':[hex(u.reg_read(reg('x'+str(i)))) for i in range(2)]})
            u.reg_write(reg('pc'),target);return
        return super().code(u,pc,n,user)

    def phase(self,label,entry,outputs=(),abi=None,absolute=False,**regs):
        bs=bytes(self.uc.mem_read(pp.STACK_BASE,pp.STACK_SIZE));bc=bytes(self.uc.mem_read(pp.SCRATCH,0x10000))
        for k,v in regs.items():self.uc.reg_write(reg(k),v)
        self.reason=None;self.steps=0;self.pcs=[];self.calls=[];self.stores=[];self.writes=[];self.reads=[];self.header_reads=[]
        self.uc.emu_start(entry if absolute else KBASE+entry,0,count=2000,timeout=1000000)
        assert self.reason=='returned' or self.reason and self.reason.startswith('boundary: '),(self.reason,hex(self.uc.reg_read(reg('pc'))))
        for w in self.stores:
            a,n=int(w['address'],16),w['size'];assert SP-0x800<=a and a+n<=SP or any(x<=a and a+n<=z for x,z in outputs),w
        ass=bytes(self.uc.mem_read(pp.STACK_BASE,pp.STACK_SIZE));assert ass[:SP-0x800-pp.STACK_BASE]==bs[:SP-0x800-pp.STACK_BASE] and ass[SP-pp.STACK_BASE:]==bs[SP-pp.STACK_BASE:]
        ac=bytes(self.uc.mem_read(pp.SCRATCH,0x10000));assert all(any(a<=pp.SCRATCH+i<z for a,z in outputs) for i,(a,b) in enumerate(zip(bc,ac)) if a!=b)
        for a,d in self.images:assert bytes(self.uc.mem_read(a,len(d)))==d
        for c in self.calls:
            assert 'stub' not in c
            assert 'return_instruction' in c or c.get('original_MPR_PLT_binding')=='osal_free_msg' or c.get('symbol')=='u_osal_free_msg',c
        if abi:
            assert self.reason=='returned' and self.uc.reg_read(reg('sp'))==SP
            assert all(self.uc.reg_read(reg(k))==v for k,v in abi.items())
        return {'label':label,'entry':hex(entry if absolute else KBASE+entry),'reason':self.reason,
            'stop_pc':hex(self.uc.reg_read(reg('pc'))),'pcs':self.pcs,'stores':self.stores,
            'native_returns_and_original_symbol_bindings':self.calls,'declared_block_reads':self.header_reads,
            'return_u32_if_returned':self.uc.reg_read(reg('w0')) if self.reason=='returned' else None,
            'whole_images_unchanged':True,'scratch_outside_outputs_unchanged':True,'stack_outside2048_unchanged':True,
            'native_saved_registers_verified_on_return':bool(abi),'actual_services_or_success_return_adapters':False}

def allocate_shape(m,flags,pool):
    m.uc.mem_write(CLIENT,bytes(0x40));m.uc.mem_write(CLIENT,bytes([flags]));pq(m,CLIENT+0x30,pool)
    abi=prev.saved(m)
    e=[m.phase('original allocator prologue to unexecuted client lookup',0x3248,sp=SP,x30=pp.STOP,
        x0=old.SOURCE,x1=OUT,x2=44,x3=0)]
    assert e[-1]['reason']=='boundary: before_dynamic_client_lookup'
    e.append(m.phase('independent declared client; original allocation geometry',0x3294,x21=CLIENT))
    assert e[-1]['reason'] in ['boundary: before_allocator_global_pool_reference','boundary: before_allocator_private_pool_call']
    assert m.uc.reg_read(reg('w25'))==128
    e.append(m.phase('independent128-byte block; original header, refcount and trailer generation',0x32f0,
        outputs=[(BLOCK,BLOCK+128),(CLIENT+2,CLIENT+4),(OUT,OUT+8)],abi=abi,x0=BLOCK))
    assert q(m,OUT)==DATA and h(m,HEADER+10)==1 and h(m,CLIENT+2)==1
    assert bytes(m.uc.mem_read(DATA+44,4))==bytes.fromhex('77777777')
    return e

def free_path(seed,flags,pool,refs,tail=0x77777777):
    m=Guest(seed)
    try:
        ev=allocate_shape(m,flags,pool);ph(m,HEADER+10,refs);m.uc.mem_write(DATA+44,struct.pack('<I',tail))
        before=bytes(m.uc.mem_read(BLOCK,128));abi=prev.saved(m)
        ev.append(m.phase('original exported free entry to dynamic client lookup',0x4650,
            sp=SP,x30=pp.STOP,x0=old.SOURCE,x1=DATA))
        assert ev[-1]['reason']=='boundary: before_dynamic_client_lookup'
        ev.append(m.phase('independent dynamic-client lookup result; original reference decrement/free selection',0x4734,
            outputs=[(HEADER+10,HEADER+12),(CLIENT+2,CLIENT+4)],abi=abi if refs>1 else None,x0=CLIENT))
        assert h(m,HEADER+10)==refs-1 and h(m,CLIENT+2)==(1 if refs>1 else 0)
        after=bytes(m.uc.mem_read(BLOCK,128));expected=bytearray(before);struct.pack_into('<H',expected,50,refs-1)
        assert after==bytes(expected)
        if refs>1:
            assert ev[-1]['reason']=='returned' and ev[-1]['return_u32_if_returned']==0
            outcome='reference_retained_no_pool_call';args=None
        else:
            private=not flags&8 and bool(pool)
            assert ev[-1]['reason']=='boundary: '+('before_message_private_pool_free' if private else 'before_message_global_pool_free')
            args=[m.uc.reg_read(reg('x'+str(i))) for i in range(3)]
            assert args==[pool if private else BBASE+0x3740,BLOCK,128]
            outcome='last_reference_to_pool_free_boundary'
        return {'seed':seed,'declared_client_flags':flags,'declared_private_pool':hex(pool),'declared_refs':refs,
            'declared_tail':hex(tail),'header_ref_after':refs-1,'client_count_after':h(m,CLIENT+2),
            'outcome':outcome,'native_pool_free_args':args,'events':ev,'actual_pool_free_or_reuse_executed':False,
            'free_slice_checks_trailer':any(x['offset']==108 for x in ev[-1]['declared_block_reads'])}
    finally:m.close()

def missing_client(seed):
    m=Guest(seed)
    try:
        abi=prev.saved(m)
        ev=[m.phase('original free entry before client lookup',0x4650,sp=SP,x30=pp.STOP,x0=old.SOURCE,x1=DATA)]
        ev.append(m.phase('independent absent client result; original free error return',0x4734,abi=abi,x0=0))
        assert ev[-1]['return_u32_if_returned']==0xfffffc00 and not ev[-1]['declared_block_reads']
        return {'seed':seed,'events':ev,'actual_lookup_executed':False}
    finally:m.close()

def finish_path(seed,kind):
    m=Guest(seed)
    try:
        broadcast=kind!='nonbroadcast';flags=3 if broadcast else 2;refs=2 if kind=='broadcast_ref2' else 1
        if not broadcast:refs=0
        m.uc.mem_write(CLIENT,bytes(0x40));m.uc.mem_write(CLIENT,bytes([flags]));ph(m,CLIENT+2,1 if broadcast else 0)
        pq(m,CLIENT+0x20,CHAIN if broadcast and kind!='broadcast_no_chain' else 0);pq(m,CHAIN,0)
        m.uc.mem_write(NODE,bytes(0x38));m.uc.mem_write(NODE+0x18,bytes([1,8]));ph(m,NODE+0x1a,0x47)
        m.uc.mem_write(BLOCK,bytes(128));ph(m,HEADER+10,refs)
        m.uc.mem_write(HEADER+8,bytes([2,0x40]));before=bytes(m.uc.mem_read(BLOCK,128))
        ev=[m.phase('original finish_callback entry to dynamic lookup',0x53c8,sp=SP,x30=pp.STOP,x0=NODE,x1=HEADER)]
        assert ev[-1]['reason']=='boundary: before_dynamic_client_lookup'
        ev.append(m.phase('independent client result; original finish_callback reaches lock boundary',0x5500,x0=CLIENT))
        assert ev[-1]['reason']=='boundary: before_finish_callback_lock'
        ev.append(m.phase('independent post-lock frame; original node count and selected message-reference path',0x5404,
            outputs=[(NODE+0x18,NODE+0x19),(CLIENT,CLIENT+4),(HEADER+10,HEADER+12)]))
        if kind=='broadcast_ref1':
            assert ev[-1]['reason']=='boundary: before_finish_global_pool_free'
            assert [m.uc.reg_read(reg('x'+str(i))) for i in range(3)]==[BBASE+0x3740,BLOCK,128]
        else:assert ev[-1]['reason']=='boundary: before_finish_callback_unlock'
        expected_refs=refs-1 if kind in ('broadcast_ref1','broadcast_ref2') else refs
        assert h(m,HEADER+10)==expected_refs and bytes(m.uc.mem_read(NODE+0x18,1))==b'\0'
        if kind in ('nonbroadcast','broadcast_no_chain'):
            assert not ev[-1]['declared_block_reads'] and bytes(m.uc.mem_read(BLOCK,128))==before
        return {'seed':seed,'kind':kind,'declared_client_flags':flags,'declared_refs':refs,
            'header_ref_after':expected_refs,'node_pending_count_after':0,'events':ev,
            'nonbroadcast_message_ref_not_dereferenced_in_declared_empty_queue':kind=='nonbroadcast',
            'actual_lock_queue_service_pool_free_or_callback_runtime_proven':False}
    finally:m.close()

def user_cleanup(seed):
    m=Guest(seed)
    try:
        # Independent common cleanup; earlier callback state, copies, signal and
        # locks remain separate unexecuted dependencies, not bypassed success.
        fp=SP-0x80
        e=m.phase('independent MPR common cleanup; original OSAL free wrapper to ioctl boundary',MBASE+0x2859ec,
            absolute=True,sp=fp,x29=fp,x30=pp.STOP,x19=DATA)
        assert e['reason']=='boundary: before_user_ioctl'
        assert m.uc.reg_read(reg('x1'))&0xffffffff==0x8000000b
        record=m.uc.reg_read(reg('x2'));assert struct.unpack('<I',bytes(m.uc.mem_read(record,4)))[0]==old.SOURCE and q(m,record+8)==DATA
        return {'seed':seed,'original_QID':hex(old.SOURCE),'original_free_operation_low32':'0x8000000b',
            'message_pointer':hex(DATA),'events':[e],'FD_from_ELF_initial_storage_not_open_device':True,
            'actual_ioctl_or_previous_callback_completion_proven':False}
    finally:m.close()

def pending_cleanup(seed):
    m=Guest(seed)
    try:
        ev=[m.phase('original user worker prologue before cancellation setup',0x3260,absolute=True,sp=SP,x30=pp.STOP,x0=0)]
        ev.append(m.phase('independent post-cancel worker frame; first receive ioctl arguments',0x32ac,absolute=True))
        assert ev[-1]['reason']=='boundary: before_user_ioctl'
        fp=m.uc.reg_read(reg('x29'));m.uc.mem_write(fp+0x60,struct.pack('<QQQ',MBASE+0x28593c,0,DATA))
        ev.append(m.phase('independent post-callback frame; original worker enters next receive ioctl',0x32f4,absolute=True,x0=0x1234))
        assert ev[-1]['reason']=='boundary: before_user_ioctl' and m.uc.reg_read(reg('x1'))&0xffffffff==0x8000000d
        assert q(m,fp+0x70)==DATA
        m.uc.mem_write(NODE,bytes(0x38));m.uc.mem_write(NODE+0x19,b'\x08')
        pq(m,CTX+0x78,NODE);pq(m,CTX+0x80,HEADER)
        kfp=SP-0x70
        ev.append(m.phase('independent pending worker slot; original clear before unlocking',0x968,
            outputs=[(CTX+0x78,CTX+0x80)],sp=kfp,x29=kfp,x30=pp.STOP,x0=0,x19=CTX,x20=0,x21=CTX+0x10))
        assert ev[-1]['reason']=='boundary: before_pending_node_unlock' and q(m,CTX+0x78)==0
        ev.append(m.phase('independent post-unlock frame; original async pending-node finish arguments',0x988))
        assert ev[-1]['reason']=='boundary: before_pending_node_finish_callback_call'
        assert [m.uc.reg_read(reg('x'+str(i))) for i in range(2)]==[NODE,HEADER]
        return {'seed':seed,'next_user_operation_low32':'0x8000000d','pending_slot_cleared_before_finish_call':True,
            'original_finish_args':[hex(NODE),hex(HEADER)],'events':ev,
            'node_record_lifetime_is_not_message_data_lease':True,'actual_receive_unlock_finish_continuity_proven':False}
    finally:m.close()

def run(out):
    im.volume();assert sha(PRIOR.read_bytes())==PRIOR_SHA
    for f in json.loads(PRIOR.read_text())['files']:
        p=ROOT/f['path'];assert p.stat().st_size==f['bytes'] and sha(p.read_bytes())==f['sha256']
    assert (BASE/'GOAL_STATUS.json').read_bytes()==(STAGE/'goal-status-before.json').read_bytes()
    out.mkdir();(out/'executed-source.py').write_bytes(Path(__file__).read_bytes())
    j={'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'RUNNING',
        'source':str(Path(__file__).relative_to(ROOT)),'source_sha256':sha(Path(__file__).read_bytes()),
        'module_sha256':MODULE_SHA,'added_original_local_ABS64':ADDED_RELOCS,
        'free_cases':[],'tail_controls':[],'missing_client_cases':[],'finish_cases':[],'user_cleanup_cases':[],'pending_cleanup_cases':[],
        'goal_complete':False,'persistent_write_release':False,'Windows_UU_camera_operations':False,
        'real_kernel_service_message_lifetime_MAIN_or_recovery_proven':False}
    try:
        for seed in (0x31,0x62):
            for flags,pool in ((0,0),(0,0x33000000),(8,0x33000000)):
                for refs in (1,2):j['free_cases'].append(free_path(seed,flags,pool,refs))
            j['tail_controls'].append(free_path(seed,0,0,1,0x12345678))
            j['missing_client_cases'].append(missing_client(seed))
            for kind in ('nonbroadcast','broadcast_ref1','broadcast_ref2','broadcast_no_chain'):j['finish_cases'].append(finish_path(seed,kind))
            j['user_cleanup_cases'].append(user_cleanup(seed));j['pending_cleanup_cases'].append(pending_cleanup(seed))
        groups=('free_cases','tail_controls','missing_client_cases','finish_cases','user_cleanup_cases','pending_cleanup_cases')
        j['bounded_phases']=sum(len(c['events']) for k in groups for c in j[k])
        j['status']='PASS_ORIGINAL_MESSAGE_RELEASE_AND_DISTINCT_PENDING_CALLBACK_NODE_SCOPE'
        (out/'release-order-results.json').write_text(json.dumps(j,ensure_ascii=False,indent=2)+'\n')
        print(json.dumps({k:len(j[k]) for k in groups}|{'bounded_phases':j['bounded_phases'],'status':j['status']}))
    except Exception:
        j['status']='FAILED_NO_PASSING_RESULT';j['error']=traceback.format_exc()
        (out/'attempt-failure.json').write_text(json.dumps(j,ensure_ascii=False,indent=2)+'\n');raise
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);run(p.parse_args().out)
