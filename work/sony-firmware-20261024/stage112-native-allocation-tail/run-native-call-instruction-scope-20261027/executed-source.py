#!/usr/bin/env python3
"""Original allocation geometry/trailer and user callback routing in guest RAM.

Kernel text remains unrelocated. Executed ranges contain only local PC-relative
branches and pure register/declared-memory operations; lookup/pool/literal and
external call sites stop before use. No real module, ioctl or scheduler runs.
"""
from pathlib import Path
import argparse,datetime,hashlib,io,json,struct,sys,traceback
from elftools.elf.elffile import ELFFile
STAGE=Path(__file__).resolve().parent;BASE=STAGE.parent;ROOT=BASE.parents[1]
sys.path.insert(0,str(BASE/'stage110-native-OSAL-envelope'));import osal_envelope as prev
core,maps=prev.prev,prev.maps;pp,r,im=prev.pp,prev.r,prev.im
OSAL,DF,MPR,LIBC=prev.OSAL,core.DF,core.MPR,core.LIBC
SP=core.SP;KBASE=0x60000000;DBASE=0x50000000;MBASE=0x70000000;CBASE=core.CBASE
MODULE=BASE/'stage47-runtime-provider-binding/official-files/nflasha15/kmod/osal_uipc.ko'
MODULE_SHA='6aa0f5c8c72f5f6cf9aa9c905fc3f3f75b8bea0dfebaf13deb632b0de088eb38'
assert hashlib.sha256(MODULE.read_bytes()).hexdigest()==MODULE_SHA
ELF=ELFFile(io.BytesIO(MODULE.read_bytes()));TEXT=ELF.get_section_by_name('.text').data()
CLIENT=pp.SCRATCH+0x7000;OUT=pp.SCRATCH+0x7800;BLOCK=pp.SCRATCH+0x8000;REPLY=pp.SCRATCH+0x9000
OBJ=pp.SCRATCH+0x1000;SOURCE=0x80c70047;OWNER=0x8055001f
PRIOR=BASE/'stage111-native-Open-reply-producer/final-receipt.json'
PRIOR_SHA='719b2d1e33d93e3021c081438ed5d9ed292626f5c4fd72ae67355dab31694438'
reg=core.reg
def sha(b):return hashlib.sha256(b).hexdigest()

class Guest(core.Guest):
    def __init__(self,seed):
        super().__init__(OSAL,seed,[(0x67b0,0x6970),(0x3e98,0x3f28),(0x6b78,0x6dac),
            (0x3cd8,0x3d68),(0x3260,0x3390),(0x7e20,0x7e28)])
        size=(len(TEXT)+4095)&~4095;self.uc.mem_map(KBASE,size,r.unicorn.UC_PROT_READ|r.unicorn.UC_PROT_EXEC)
        self.uc.mem_write(KBASE,TEXT)
        for native,bias in ((DF,DBASE),(MPR,MBASE),(LIBC,CBASE)):maps.map_image(self,native,bias)
        self.allowed.extend([(KBASE+0x3248,KBASE+0x3518),(DBASE+0x33ef4,DBASE+0x33f20),
            (MBASE+0x285998,MBASE+0x2859c0)])
        s=LIBC.symbols['memcpy'];self.allowed.append((CBASE+s['va'],CBASE+s['va']+s['size']))
        self.boundaries={KBASE+0x2938:'before_unexecuted_kernel_client_lookup',
            KBASE+0x32d8:'before_unexecuted_kernel_global_pool_reference',
            KBASE+0x3420:'before_unexecuted_kernel_private_pool_call',
            KBASE+0x3508:'before_unexecuted_kernel_fixed_block_call',
            0x2530:'before_unexecuted_ioctl',0x2800:'before_unexecuted_pthread_cancel_type',
            0x32f0:'before_original_user_callback_BLR',DBASE+0x30780:'before_unexecuted_OSAL_send',
            MBASE+0x80460:'before_unexecuted_MPR_expected_state_clear'}
        self.images=[(s['p_vaddr'],bytes(self.uc.mem_read(s['p_vaddr'],s['p_memsz']))) for s in OSAL.segments]
        self.images.extend((bias+s['p_vaddr'],bytes(self.uc.mem_read(bias+s['p_vaddr'],s['p_memsz'])))
            for native,bias in ((DF,DBASE),(MPR,MBASE),(LIBC,CBASE)) for s in native.segments)
        self.images.append((KBASE,TEXT))

    def code(self,u,pc,n,user):
        if pc in self.boundaries:
            self.pcs.append(hex(pc));self.abort('boundary: '+self.boundaries[pc]);return
        if DBASE<=pc<DBASE+0x100000:
            name=DF.plt.get(pc-DBASE);target=None
            if name=='memcpy':target=CBASE+LIBC.symbols[name]['va']
            elif name=='osal_set_msg_src':target=OSAL.symbols[name]['va']
            if target is not None:
                self.pcs.append(hex(pc));self.steps+=1
                self.calls.append({'original_symbol_binding':name,'PLT':hex(pc),'target':hex(target),
                    'args_x0_x2':[hex(u.reg_read(reg('x'+str(i)))) for i in range(3)]})
                u.reg_write(reg('pc'),target);return
        return super().code(u,pc,n,user)

    def phase(self,label,entry,outputs=(),abi=None,**regs):
        bs=bytes(self.uc.mem_read(pp.STACK_BASE,pp.STACK_SIZE));bc=bytes(self.uc.mem_read(pp.SCRATCH,0x10000))
        for name,value in regs.items():self.uc.reg_write(reg(name),value)
        self.reason=None;self.steps=0;self.pcs=[];self.calls=[];self.stores=[];self.writes=[];self.reads=[]
        self.uc.emu_start(entry,0,count=5000,timeout=1000000)
        assert self.reason and (self.reason=='returned' or self.reason.startswith('boundary: ')),(self.reason,hex(self.uc.reg_read(reg('pc'))))
        for w in self.stores:
            a,n=int(w['address'],16),w['size'];assert SP-0x800<=a and a+n<=SP or any(x<=a and a+n<=z for x,z in outputs),w
        ass=bytes(self.uc.mem_read(pp.STACK_BASE,pp.STACK_SIZE))
        assert ass[:SP-0x800-pp.STACK_BASE]==bs[:SP-0x800-pp.STACK_BASE] and ass[SP-pp.STACK_BASE:]==bs[SP-pp.STACK_BASE:]
        ac=bytes(self.uc.mem_read(pp.SCRATCH,0x10000))
        assert all(any(a<=pp.SCRATCH+i<z for a,z in outputs) for i,(a,b) in enumerate(zip(bc,ac)) if a!=b)
        for a,data in self.images:assert bytes(self.uc.mem_read(a,len(data)))==data
        if abi:
            assert self.reason=='returned' and self.uc.reg_read(reg('sp'))==SP
            assert all(self.uc.reg_read(reg(k))==v for k,v in abi.items())
        assert all('stub' not in c for c in self.calls)
        return {'label':label,'entry':hex(entry),'reason':self.reason,'stop_pc':hex(self.uc.reg_read(reg('pc'))),
            'pcs':self.pcs,'original_calls':self.calls,'stores':self.stores,
            'whole_stack_outside_declared2048_bytes_unchanged':True,'whole_scratch_outside_outputs_unchanged':True,
            'whole_mapped_images_and_unrelocated_kernel_text_unchanged':True,
            'native_saved_registers_restored_on_return_after_independent_inputs':bool(abi),
            'actual_lookup_pool_ioctl_thread_or_success_return_adapters':False}

def saved(m):return {n:m.uc.reg_read(reg(n)) for n in ['x'+str(i) for i in range(19,30)]+['d'+str(i) for i in range(8,16)]}

def geometry(seed,qid,length,wire=None):
    m=Guest(seed)
    try:
        baseline=saved(m);m.uc.mem_write(CLIENT,bytes(0x40))
        events=[m.phase('original kernel inner allocator prologue to dynamic-client lookup',KBASE+0x3248,
            sp=SP,x30=pp.STOP,x0=qid,x1=OUT,x2=length,x3=0)]
        assert events[-1]['reason']=='boundary: before_unexecuted_kernel_client_lookup'
        events.append(m.phase('independent declared client flags0 pool0; original allocation geometry',KBASE+0x3294,x21=CLIENT))
        assert events[-1]['reason']=='boundary: before_unexecuted_kernel_global_pool_reference'
        aligned=m.uc.reg_read(reg('w20'));block=m.uc.reg_read(reg('w25'));sum_=m.uc.reg_read(reg('w23'))
        negative=bool(qid&0x80000000);overhead=0x83 if negative else 0x5b
        assert aligned==(length+3)&~3 and sum_==aligned+overhead and block==(sum_&~63)
        events.append(m.phase('independent declared pool block; original header, trailer and pointer stores',KBASE+0x32f0,
            outputs=[(BLOCK,BLOCK+block),(CLIENT+2,CLIENT+4),(OUT,OUT+8)],abi=baseline,x0=BLOCK))
        assert events[-1]['reason']=='returned'
        ptr=struct.unpack('<Q',bytes(m.uc.mem_read(OUT,8)))[0]
        assert ptr==BLOCK+24+(40 if negative else 0)
        assert struct.unpack('<I',bytes(m.uc.mem_read(ptr-8,4)))[0]==length
        assert bytes(m.uc.mem_read(ptr+aligned,4))==bytes.fromhex('77777777')
        assert ptr+aligned+4<=BLOCK+block
        assert struct.unpack('<H',bytes(m.uc.mem_read(CLIENT+2,2)))[0]==1
        before_payload=bytes(m.uc.mem_read(ptr,aligned));assert before_payload==bytes([seed^0x3c])*aligned
        out={'seed':seed,'declared_qid':hex(qid),'declared_client_flags':0,'declared_client_pool_pointer':0,
            'requested_length':length,'native_aligned_length':aligned,'native_block_size_request':block,
            'native_data_offset_from_pool_block':ptr-BLOCK,'native_payload_pointer':hex(ptr),
            'native_trailer_offset_from_payload':aligned,'native_trailer_hex':'77777777',
            'bytes_from_payload_to_block_end':BLOCK+block-ptr,'native_length_metadata':length,
            'native_counter_after':1,'events':events,
            'actual_kernel_client_registry_pool_allocation_or_user_mapping_proven':False}
        if wire is not None:
            assert length==44 and qid==SOURCE and len(wire)==44
            # Explicit previously observed Dataflow object fields, not a live object.
            m.uc.mem_write(OBJ+0x18,wire);m.uc.mem_write(OBJ+0x10,struct.pack('<I',OWNER))
            fp=SP-0x80;m.uc.mem_write(fp+0x48,struct.pack('<Q',ptr))
            flow=[m.phase('independent original Dataflow sender post-allocation copy/source fields',DBASE+0x33ef4,
                outputs=[(ptr,ptr+44),(ptr-12,ptr-8)],sp=fp,x29=fp,x30=pp.STOP,x19=OBJ,x21=44,x22=SOURCE)]
            assert flow[-1]['reason']=='boundary: before_unexecuted_OSAL_send'
            assert bytes(m.uc.mem_read(ptr,48))==wire+bytes.fromhex('77777777')
            flow.append(m.phase('original user callback worker prologue before cancellation setup',0x3260,sp=SP,x30=pp.STOP,x0=0))
            assert flow[-1]['reason']=='boundary: before_unexecuted_pthread_cancel_type'
            fp2=m.uc.reg_read(reg('x29'));assert fp2==SP-0x180
            flow.append(m.phase('independent post-cancel original worker ioctl arguments',0x32ac))
            assert flow[-1]['reason']=='boundary: before_unexecuted_ioctl'
            # Explicit notification input after a stopped ioctl; never a fabricated output.
            m.uc.mem_write(fp2+0x60,struct.pack('<QQQ',MBASE+0x28593c,0,ptr))
            flow.append(m.phase('independent notification record; original pointer delivery before callback',0x32e8))
            assert flow[-1]['reason']=='boundary: before_original_user_callback_BLR'
            assert [m.uc.reg_read(reg('x'+str(i))) for i in range(3)]==[ptr,0,MBASE+0x28593c]
            fp3=SP-0x100;m.uc.mem_write(fp3+0x40,struct.pack('<Q',REPLY))
            flow.append(m.phase('independent original MPR post-lock48-byte reply copy on declared kernel-shaped storage',MBASE+0x285998,
                outputs=[(REPLY,REPLY+48)],sp=fp3,x29=fp3,x19=ptr))
            assert flow[-1]['reason']=='boundary: before_unexecuted_MPR_expected_state_clear'
            assert bytes(m.uc.mem_read(REPLY,48))==wire+bytes.fromhex('77777777')
            assert bytes(m.uc.mem_read(ptr,48))==wire+bytes.fromhex('77777777')
            out['independent_flow']={'wire44_hex':wire.hex(),'native_reply48_hex':bytes(m.uc.mem_read(REPLY,48)).hex(),
                'declared_callback_load_bias':hex(MBASE),'declared_callback_offset':'0x28593c',
                'native_user_dispatch_pointer_equals_payload_pointer':True,'native_copy_in_declared_block_extent':True,
                'events':flow,'actual_ioctl_callback_thread_mutex_or_mapping_continuity_proven':False}
        return out
    finally:m.close()

def user_ioctl(seed,kind):
    m=Guest(seed)
    try:
        if kind=='allocate':entry=0x67b0;args={'x0':SOURCE,'x1':OUT,'x2':44,'x3':1}
        else:entry=0x6b78;args={'x0':SOURCE,'x1':OUT,'x2':MBASE+0x28593c,'x3':0}
        event=m.phase('original user '+kind+' wrapper marshals arguments to ioctl stop',entry,sp=SP,x30=pp.STOP,**args)
        assert event['reason']=='boundary: before_unexecuted_ioctl'
        record=m.uc.reg_read(reg('x2'));qid=struct.unpack('<I',bytes(m.uc.mem_read(record,4)))[0]
        parm=struct.unpack('<Q',bytes(m.uc.mem_read(record+8,8)))[0];assert qid==SOURCE
        if kind=='allocate':
            values=struct.unpack('<QII',bytes(m.uc.mem_read(parm,16)));assert values==(OUT,44,1)
        else:
            assert struct.unpack('<Q',bytes(m.uc.mem_read(record+16,8)))[0]==OUT
            values=struct.unpack('<QQ',bytes(m.uc.mem_read(parm+8,16)));assert values==(MBASE+0x28593c,0)
        return {'seed':seed,'kind':kind,'native_ioctl_operation_low32':hex(m.uc.reg_read(reg('x1'))&0xffffffff),
            'native_qid':hex(qid),'native_parameter_values':list(values),'events':[event],
            'FD_from_ELF_initial_storage_not_actual_open_device':True,'actual_ioctl_or_device_handle_opened':False}
    finally:m.close()

class InitGuest(core.Guest):
    def __init__(self,seed):
        super().__init__(MPR,seed,[(0x27ddc8,0x27de88)])
        s=MPR.symbols['_ZN3mpr6thread10normalLock4lockEv'];self.allowed.append((s['va'],s['va']+s['size']))
        self.boundaries={0x7c5f0:'before_unexecuted_Init_mutex_lock',0x83530:'before_unexecuted_OSAL_callback_registration'}

def callback_registration(seed):
    m=InitGuest(seed)
    try:
        ev=[m.phase('original Codec Init prologue before lock',0x27ddc8,complete=False,sp=SP,x30=pp.STOP)]
        assert ev[-1]['reason']=='boundary: before_unexecuted_Init_mutex_lock'
        ev.append(m.phase('independent Init registration arguments after unexecuted thread setup',0x27de34,complete=False))
        assert ev[-1]['reason']=='boundary: before_unexecuted_OSAL_callback_registration'
        a=[m.uc.reg_read(reg('x'+str(i))) for i in range(4)]
        assert a==[SOURCE,SP-0x70+0x40,0x28593c,0]
        return {'seed':seed,'original_registration_arguments':[hex(x) for x in a],'events':ev,
            'actual_Init_lock_thread_create_registration_or_current_callback_proven':False}
    finally:m.close()

def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    im.volume();assert sha(PRIOR.read_bytes())==PRIOR_SHA
    for f in json.loads(PRIOR.read_text())['files']:
        b=(ROOT/f['path']).read_bytes();assert len(b)==f['bytes'] and sha(b)==f['sha256']
    assert (BASE/'GOAL_STATUS.json').read_bytes()==(STAGE/'goal-status-before.json').read_bytes()
    a.out.mkdir(exist_ok=False);(a.out/'executed-source.py').write_bytes(Path(__file__).read_bytes())
    try:
        source=PRIOR.parent/'run-native-constructor-boundaries-20261027/open-reply-results.json';old=json.loads(source.read_text())
        rows=[];ioctls=[];regs=[]
        for seed in (0xa5,0xc3):
            wire=bytes.fromhex(next(c for c in old['produced'] if c['seed']==seed and c['producer']=='ExecErrorCommand' and c['declared_status_input']==2)['wire44_hex'])
            for qid in (SOURCE,0x00c70047):
                for length in (44,45,48):rows.append(geometry(seed,qid,length,wire if qid==SOURCE and length==44 else None))
            ioctls.extend(user_ioctl(seed,kind) for kind in ('allocate','register'));regs.append(callback_registration(seed))
        phases=sum(len(c['events'])+len(c.get('independent_flow',{}).get('events',[])) for c in rows)+sum(len(c['events']) for c in ioctls+regs)
        j={'status':'PASS_ORIGINAL_KERNEL_GEOMETRY_TRAILER_AND_DECLARED_USER_CALLBACK_STORAGE_SCOPE',
            'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'kernel_module_sha256':MODULE_SHA,
            'source':str(source.relative_to(ROOT)),'source_sha256':sha(source.read_bytes()),
            'geometry_cases':rows,'user_ioctl_argument_cases':ioctls,'callback_registration_cases':regs,'bounded_phases':phases,
            'actual_kernel_registry_pool_user_mapping_ioctl_callback_thread_or_hardware_proven':False,
            'Windows_UU_camera_operations':False,'goal_complete':False,'persistent_write_release':False}
        (a.out/'allocation-tail-results.json').write_text(json.dumps(j,ensure_ascii=False,indent=2)+'\n')
        print(json.dumps({'status':j['status'],'geometry_cases':len(rows),'bounded_phases':phases}))
    except BaseException:
        (a.out/'attempt-failure.json').write_text(json.dumps({'passing_result':False,'traceback':traceback.format_exc()},indent=2)+'\n');raise
if __name__=='__main__':main()
