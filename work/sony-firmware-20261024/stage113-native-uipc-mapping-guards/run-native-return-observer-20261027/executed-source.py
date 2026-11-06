#!/usr/bin/env python3
"""Bounded original UIPC guards and affine pointer translation in guest RAM.

Only checked original ABS64 local relocations are applied to guest sections.
Kernel/user copies, dispatch BLR, alloc/free, locking and page remapping stop
before their call sites. Post-gap frames/statuses are independent declared
inputs, never substitutes for a running kernel or successful device operation.
"""
from pathlib import Path
import argparse,datetime,hashlib,json,struct,sys,traceback
STAGE=Path(__file__).resolve().parent;BASE=STAGE.parent;ROOT=BASE.parents[1]
sys.path.insert(0,str(BASE/'stage112-native-allocation-tail'))
import allocation_tail as prev
core,pp,r,im=prev.core,prev.pp,prev.r,prev.im
reg=core.reg;SP=core.SP;KBASE=prev.KBASE;RBASE=0x61000000;BBASE=0x62000000
MODULE,MODULE_SHA,ELF=prev.MODULE,prev.MODULE_SHA,prev.ELF
PRIOR=BASE/'stage112-native-allocation-tail/final-receipt.json'
PRIOR_SHA='220d3d748e02bba4823cecebb63deea3826df5fd51c942a1ee1ee6bc0d21afc4'
TASK=pp.SCRATCH+0x1000;CTX=pp.SCRATCH+0x2000;FILE=pp.SCRATCH+0x3000
SLOT=pp.SCRATCH+0x3100;KARG=pp.SCRATCH+0x4000;UREC=pp.SCRATCH+0x5000
PARAM=pp.SCRATCH+0x5100;OUTCELL=pp.SCRATCH+0x5200;NODE=pp.SCRATCH+0x6000
VMA=pp.SCRATCH+0x7000;MM=0x31001000;KPOOL=0x90000000;POOLSIZE=0x200000
TARGETS=[0x14b8,0x14a0,0x1488,0x1408,0x13c0,0x1288,0x10d0,0xfd0,
         0xe90,0xe78,0xc70,0x778,0x7c0,0x890,0xe60,0x760,0xb50]
def sha(b):return hashlib.sha256(b).hexdigest()
def q(m,a):return struct.unpack('<Q',bytes(m.uc.mem_read(a,8)))[0]
def pq(m,a,v):m.uc.mem_write(a,struct.pack('<Q',v&0xffffffffffffffff))
def saved(m):return {n:m.uc.reg_read(reg(n)) for n in ['x'+str(i) for i in range(19,30)]+['d'+str(i) for i in range(8,16)]}

def local_images():
    """No loader execution: apply exact ELF-defined local data-pointer fixups."""
    text=bytearray(prev.TEXT);ro=bytearray(ELF.get_section_by_name('.rodata').data())
    sy=ELF.get_section_by_name('.symtab');proof=[]
    wanted_text={0x5b8:('.rodata',0x318),0x7b8:('.bss',0x50),
                 0xb48:('.bss',0x50),0xd68:('.bss',0x50)}
    for sec in ELF.iter_sections():
        if sec['sh_type']!='SHT_RELA':continue
        dst=ELF.get_section(sec['sh_info']).name
        for rr in sec.iter_relocations():
            at=rr['r_offset']
            if not (dst=='.text' and at in wanted_text or dst=='.rodata' and 0x340<=at<0x3c8):continue
            s=sy.get_symbol(rr['r_info_sym']);target=ELF.get_section(s['st_shndx']).name
            add=rr['r_addend'];assert rr['r_info_type']==257 and not s.name
            if dst=='.text':
                assert (target,add)==wanted_text[at]
                value=({'.rodata':RBASE,'.bss':BBASE}[target])+add;image=text
            else:
                assert target=='.text' and (at-0x340)%8==0 and add==TARGETS[(at-0x340)//8]
                value=KBASE+add;image=ro
            assert image[at:at+8]==bytes(8)
            image[at:at+8]=struct.pack('<Q',value)
            proof.append({'section':dst,'offset':hex(at),'type':'R_AARCH64_ABS64',
                'target_section':target,'original_addend':hex(add),'guest_value':hex(value)})
    assert len(proof)==21
    return bytes(text),bytes(ro),proof
TEXT,RODATA,RELOCS=local_images()

class Guest(core.Guest):
    def __init__(self,seed,userbase=0x40000000,owner=MM,limit=0x10000000000):
        super().__init__(prev.OSAL,seed,[])
        for a,data in ((KBASE,TEXT),(RBASE,RODATA)):
            self.uc.mem_map(a,(len(data)+4095)&~4095,r.unicorn.UC_PROT_READ|r.unicorn.UC_PROT_EXEC)
            self.uc.mem_write(a,data)
        self.uc.mem_map(BBASE,(ELF.get_section_by_name('.bss')['sh_size']+4095)&~4095,r.unicorn.UC_PROT_READ)
        pq(self,BBASE+0x50+0x40,KPOOL)
        self.images.extend([(KBASE,TEXT),(RBASE,RODATA),
            (BBASE,bytes(self.uc.mem_read(BBASE,ELF.get_section_by_name('.bss')['sh_size'])))])
        self.allowed.extend((KBASE+a,KBASE+z) for a,z in
            [(0x4d8,0x5b4),(0x778,0x7b8),(0xc70,0xd68),(0x9f0,0xa28),
             (0xd70,0xd9c),(0xe00,0xe20)])
        self.boundaries={KBASE+a:n for a,n in {
            0x530:'before_dispatch_user_copy',0x580:'before_original_dispatch_BLR',
            0x590:'before_owner_mismatch_logging',0xcbc:'before_allocation_parameter_user_copy',
            0xcd8:'before_kernel_allocator_call',0xd28:'before_error_path_free_call',
            0xd48:'before_allocation_result_user_copy',0x7a0:'before_kernel_free_call',
            0xa24:'before_callback_spin_unlock',0xd9c:'after_exact_mapping_size_guard_before_PFN_math',
            0xe20:'before_mapping_size_error_logging'}.items()}
        self.uc.mem_write(TASK,bytes(0x600));self.uc.mem_write(CTX,bytes(0x200))
        pq(self,TASK+8,limit);pq(self,TASK+0x2d8,MM)
        pq(self,CTX+0x28,owner);pq(self,CTX+0x30,userbase)
        pq(self,FILE+8,SLOT);pq(self,SLOT,CTX)
        self.uc.reg_write(reg('sp_el0'),TASK)
        assert self.uc.reg_read(reg('sp_el0'))==TASK

    def phase(self,label,entry,outputs=(),abi=None,**regs):
        bs=bytes(self.uc.mem_read(pp.STACK_BASE,pp.STACK_SIZE));bc=bytes(self.uc.mem_read(pp.SCRATCH,0x10000))
        for n,v in regs.items():self.uc.reg_write(reg(n),v)
        self.reason=None;self.steps=0;self.pcs=[];self.calls=[];self.stores=[];self.writes=[];self.reads=[]
        self.uc.emu_start(KBASE+entry,0,count=1000,timeout=1000000)
        assert self.reason=='returned' or self.reason and self.reason.startswith('boundary: '),(self.reason,hex(self.uc.reg_read(reg('pc'))))
        for w in self.stores:
            a,n=int(w['address'],16),w['size']
            assert SP-0x800<=a and a+n<=SP or any(x<=a and a+n<=z for x,z in outputs),w
        ass=bytes(self.uc.mem_read(pp.STACK_BASE,pp.STACK_SIZE))
        assert ass[:SP-0x800-pp.STACK_BASE]==bs[:SP-0x800-pp.STACK_BASE] and ass[SP-pp.STACK_BASE:]==bs[SP-pp.STACK_BASE:]
        ac=bytes(self.uc.mem_read(pp.SCRATCH,0x10000))
        assert all(any(a<=pp.SCRATCH+i<z for a,z in outputs) for i,(a,b) in enumerate(zip(bc,ac)) if a!=b)
        for a,data in self.images:assert bytes(self.uc.mem_read(a,len(data)))==data
        assert all(set(c)=={'return_instruction','return_x0'} for c in self.calls)
        assert self.uc.reg_read(reg('sp_el0'))==TASK
        if abi:
            assert self.reason=='returned' and self.uc.reg_read(reg('sp'))==SP
            assert all(self.uc.reg_read(reg(k))==v for k,v in abi.items())
        return {'label':label,'entry_offset':hex(entry),'reason':self.reason,
            'stop_pc':hex(self.uc.reg_read(reg('pc'))),'pcs':self.pcs,'stores':self.stores,'native_returns':self.calls,
            'return_u32_if_returned':self.uc.reg_read(reg('w0')) if self.reason=='returned' else None,
            'all_mapped_images_unchanged':True,'scratch_outside_declared_outputs_unchanged':True,
            'stack_outside_declared2048_bytes_unchanged':True,'SP_EL0_fixture_unchanged':True,
            'saved_registers_verified_on_full_native_return':bool(abi),
            'executed_external_services_or_return_adapters':False}

def dispatch(seed,op,mapped=True,owner=True,ptr=UREC,limit=0x10000000000,copyfault=False):
    m=Guest(seed,userbase=0x40000000 if mapped else 0,owner=MM if owner else MM+0x1000,limit=limit)
    try:
        abi=saved(m);pq(m,KARG,op);pq(m,KARG+8,ptr)
        events=[m.phase('original ioctl dispatcher entry and user-record range guard',0x4d8,
            sp=SP,x30=pp.STOP,x0=FILE,x1=KARG)]
        if events[-1]['reason']=='returned':
            assert events[-1]['return_u32_if_returned']==0xffffffea
            assert m.uc.reg_read(reg('sp'))==SP and all(m.uc.reg_read(reg(k))==v for k,v in abi.items())
            outcome='user_record_range_rejected'
        else:
            assert events[-1]['reason']=='boundary: before_dispatch_user_copy'
            fp=m.uc.reg_read(reg('x29'));assert fp==SP-0x30 and m.uc.reg_read(reg('x20'))==CTX
            assert [m.uc.reg_read(reg('x'+str(i))) for i in range(3)]==[fp+0x20,ptr,16]
            if copyfault:
                events.append(m.phase('independent declared nonzero copy remainder; original rejection',0x534,abi=abi,x0=1))
                assert events[-1]['return_u32_if_returned']==0xffffffea;outcome='declared_copy_fault_rejected'
            else:
                # No fake user-copy return: skip its return check; give this phase
                # its own explicit copied-record input and original saved frame.
                m.uc.mem_write(fp+0x20,struct.pack('<I',prev.SOURCE));pq(m,fp+0x28,PARAM)
                events.append(m.phase('independent copied-record input; original opcode/mapping/owner guards and table',0x538))
                masked=op&0x7fffffff
                if masked>16 or not mapped and masked!=16:
                    assert events[-1]['return_u32_if_returned']==0xffffffea;outcome='opcode_or_mapping_rejected'
                elif not owner:
                    assert events[-1]['reason']=='boundary: before_owner_mismatch_logging';outcome='owner_mismatch_route'
                else:
                    assert events[-1]['reason']=='boundary: before_original_dispatch_BLR'
                    assert m.uc.reg_read(reg('x3'))==KBASE+TARGETS[masked]
                    assert [m.uc.reg_read(reg('x'+str(i))) for i in range(3)]==[prev.SOURCE,PARAM,CTX]
                    outcome='original_table_target_before_call'
                if events[-1]['reason']=='returned':
                    assert m.uc.reg_read(reg('sp'))==SP and all(m.uc.reg_read(reg(k))==v for k,v in abi.items())
        return {'seed':seed,'declared_opcode':hex(op),'declared_mapping_present':mapped,'declared_owner_matches':owner,
            'declared_user_record_pointer':hex(ptr),'declared_address_limit':hex(limit),'outcome':outcome,'events':events,
            'actual_copy_dispatch_registration_mapping_or_process_binding_proven':False}
    finally:m.close()

def allocation_entry(seed,kind):
    ptr=PARAM;limit=0x10000000000
    if kind=='short_limit':limit=ptr+15
    if kind=='exact_limit':limit=ptr+16
    if kind=='wrap':ptr=0xfffffffffffffff8;limit=0xffffffffffffffff
    m=Guest(seed,limit=limit)
    try:
        abi=saved(m)
        events=[m.phase('original allocation handler parameter range/prologue before user copy',0xc70,
            sp=SP,x30=pp.STOP,x0=prev.SOURCE,x1=ptr,x2=CTX)]
        if kind in ('short_limit','wrap'):
            assert events[-1]['return_u32_if_returned']==0xfffffc00 and all(m.uc.reg_read(reg(k))==v for k,v in abi.items())
            outcome='parameter_range_rejected'
        else:
            assert events[-1]['reason']=='boundary: before_allocation_parameter_user_copy'
            fp=m.uc.reg_read(reg('x29'));assert fp==SP-0x40
            assert [m.uc.reg_read(reg('x'+str(i))) for i in range(3)]==[fp+0x30,ptr,16]
            m.uc.mem_write(fp+0x30,struct.pack('<QII',0 if kind=='null_outcell' else OUTCELL,44,1))
            events.append(m.phase('independent parameter record after unexecuted user copy; original outcell and allocator args',0xcc4,
                abi=abi if kind=='null_outcell' else None))
            if kind=='null_outcell':assert events[-1]['return_u32_if_returned']==0xfffffc00;outcome='null_outcell_rejected'
            else:
                assert events[-1]['reason']=='boundary: before_kernel_allocator_call'
                assert [m.uc.reg_read(reg('x'+str(i))) for i in range(4)]==[prev.SOURCE,fp+0x20,44,1]
                outcome='original_allocator_args_before_call'
        return {'seed':seed,'case':kind,'outcome':outcome,'events':events,'actual_user_copy_or_allocation':False}
    finally:m.close()

def mapping_flow(seed,base,offset,index):
    m=Guest(seed,userbase=base)
    try:
        ev=[m.phase('original allocation handler prologue to parameter-copy stop for independent frame',0xc70,
            sp=SP,x30=pp.STOP,x0=prev.SOURCE,x1=PARAM,x2=CTX)]
        assert ev[-1]['reason']=='boundary: before_allocation_parameter_user_copy'
        fp=m.uc.reg_read(reg('x29'));pq(m,fp+0x20,KPOOL+offset);pq(m,fp+0x30,OUTCELL)
        ev.append(m.phase('independent kernel-data and outcell input; original user-pointer conversion/range guard',0xce0))
        assert ev[-1]['reason']=='boundary: before_allocation_result_user_copy'
        user=q(m,fp+0x28);assert user==base+offset
        assert [m.uc.reg_read(reg('x'+str(i))) for i in range(3)]==[OUTCELL,fp+0x28,8]
        fp2=SP-0x70;callback=0x7028593c;context=0x13570000+seed
        ev.append(m.phase('independent pending callback fields; original notification user-pointer conversion',0x9f0,
            outputs=[(CTX+(index<<5)+0x78,CTX+(index<<5)+0x88)],
            sp=fp2,x29=fp2,x30=pp.STOP,x19=CTX,x20=index,x21=CTX+0x10,
            x1=NODE,x2=context,x3=KPOOL+offset-24,x4=callback))
        assert ev[-1]['reason']=='boundary: before_callback_spin_unlock'
        assert struct.unpack('<QQQ',bytes(m.uc.mem_read(fp2+0x50,24)))==(callback,context,user)
        assert q(m,CTX+(index<<5)+0x78)==NODE and q(m,CTX+(index<<5)+0x80)==KPOOL+offset-24
        ev.append(m.phase('independent user-pointer input; original free inverse/range guard before free service',0x778,
            sp=SP,x29=SP-0x200,x30=pp.STOP,x0=prev.SOURCE,x1=user,x2=CTX))
        assert ev[-1]['reason']=='boundary: before_kernel_free_call'
        assert m.uc.reg_read(reg('x1'))==KPOOL+offset
        return {'seed':seed,'declared_userbase':hex(base),'declared_kernelpool':hex(KPOOL),'declared_data_offset':offset,
            'worker_index':index,'original_alloc_user_pointer':hex(user),'original_callback_user_pointer':hex(user),
            'original_free_kernel_pointer':hex(KPOOL+offset),'events':ev,
            'independent_slices_not_real_allocation_queue_user_mapping_or_lifetime':True}
    finally:m.close()

def free_boundary(seed,offset):
    base=0x40000000;m=Guest(seed,userbase=base)
    try:
        abi=saved(m);e=m.phase('original free single-pointer offset guard and inverse conversion',0x778,
            sp=SP,x30=pp.STOP,x0=prev.SOURCE,x1=base+offset,x2=CTX)
        valid=0<=offset<POOLSIZE
        if valid:
            assert e['reason']=='boundary: before_kernel_free_call' and m.uc.reg_read(reg('x1'))==KPOOL+offset
        else:
            assert e['return_u32_if_returned']==0xfffffc00 and m.uc.reg_read(reg('sp'))==SP
            assert all(m.uc.reg_read(reg(k))==v for k,v in abi.items())
        return {'seed':seed,'declared_pointer_offset':offset,'native_range_admitted_before_free':valid,'events':[e],
            'single_pointer_check_not_object_extent_refcount_or_generation_validation':True,'actual_free_executed':False}
    finally:m.close()

def mmap_guard(seed,length):
    m=Guest(seed)
    try:
        pq(m,VMA,0x48000000);pq(m,VMA+8,0x48000000+length)
        e=m.phase('original mmap exact2MiB range guard before PFN services/logging',0xd70,
            sp=SP,x30=pp.STOP,x0=FILE,x1=VMA)
        assert e['reason']=='boundary: '+('after_exact_mapping_size_guard_before_PFN_math' if length==POOLSIZE else 'before_mapping_size_error_logging')
        assert m.uc.reg_read(reg('x3'))==length and q(m,CTX+0x30)==0x40000000
        return {'seed':seed,'declared_length':length,'exact_length_admitted_before_PFN_math':length==POOLSIZE,
            'events':[e],'actual_PFN_math_remap_or_mapping_creation':False}
    finally:m.close()

def mmap_status(seed,status):
    m=Guest(seed)
    try:
        abi=saved(m);pq(m,VMA,0x48000000);pq(m,VMA+8,0x48200000)
        ev=[m.phase('original mmap prologue and exact size guard; stop before PFN math',0xd70,
            sp=SP,x30=pp.STOP,x0=FILE,x1=VMA)]
        ev.append(m.phase('independent declared remap status input; original conditional context-base publication',0xe00,
            outputs=[(CTX+0x30,CTX+0x38)],abi=abi,x0=status&0xffffffff))
        expected=0x48000000 if status==0 else 0x40000000
        assert q(m,CTX+0x30)==expected and ev[-1]['return_u32_if_returned']==(0 if status==0 else 0xfffffff5)
        return {'seed':seed,'independent_declared_remap_status':status,'context_base_after':hex(expected),
            'events':ev,'actual_remap_success_or_failure_not_simulated':True}
    finally:m.close()

def run(out):
    im.volume();assert sha(PRIOR.read_bytes())==PRIOR_SHA
    for f in json.loads(PRIOR.read_text())['files']:
        p=ROOT/f['path'];assert p.stat().st_size==f['bytes'] and sha(p.read_bytes())==f['sha256']
    assert (BASE/'GOAL_STATUS.json').read_bytes()==(STAGE/'goal-status-before.json').read_bytes()
    out.mkdir();(out/'executed-source.py').write_bytes(Path(__file__).read_bytes())
    result={'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'RUNNING',
        'source':str(Path(__file__).relative_to(ROOT)),'source_sha256':sha(Path(__file__).read_bytes()),
        'module_sha256':MODULE_SHA,'local_ABS64_relocations':RELOCS,
        'dispatch_cases':[],'allocation_entry_cases':[],'mapping_flows':[],'free_range_cases':[],
        'mmap_length_cases':[],'mmap_status_cases':[],
        'goal_complete':False,'persistent_write_release':False,'Windows_UU_camera_operations':False,
        'real_ioctl_kernel_services_mapping_hardware_or_recovery_proven':False}
    try:
        for seed in (0x28,0x59):
            for op in (8,10,11,13,16):result['dispatch_cases'].append(dispatch(seed,0x80000000|op))
            for kw in [dict(op=10,mapped=False),dict(op=16,mapped=False),dict(op=17),dict(op=10,owner=False),
                dict(op=10,copyfault=True),dict(op=10,limit=UREC+15),dict(op=10,limit=UREC+16),
                dict(op=10,ptr=0xfffffffffffffff8,limit=0xffffffffffffffff)]:
                result['dispatch_cases'].append(dispatch(seed,**kw))
            for kind in ('ordinary','exact_limit','short_limit','wrap','null_outcell'):
                result['allocation_entry_cases'].append(allocation_entry(seed,kind))
            for offset,index in ((64,0),(0x2040,3)):
                result['mapping_flows'].append(mapping_flow(seed,0x40000000 if seed==0x28 else 0x48000000,offset,index))
            for offset in (-1,0,64,POOLSIZE-1,POOLSIZE):result['free_range_cases'].append(free_boundary(seed,offset))
            for length in (POOLSIZE-4096,POOLSIZE,POOLSIZE+4096):result['mmap_length_cases'].append(mmap_guard(seed,length))
            for status in (0,-1):result['mmap_status_cases'].append(mmap_status(seed,status))
        groups=('dispatch_cases','allocation_entry_cases','mapping_flows','free_range_cases','mmap_length_cases','mmap_status_cases')
        result['bounded_phases']=sum(len(c['events']) for k in groups for c in result[k])
        result['status']='PASS_ORIGINAL_DISPATCH_MAPPING_GUARDS_AND_DECLARED_AFFINE_POINTER_SLICES'
        (out/'mapping-guard-results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
        print(json.dumps({k:len(result[k]) for k in groups}|{'bounded_phases':result['bounded_phases'],'status':result['status']}))
    except Exception:
        result['status']='FAILED_NO_PASSING_RESULT';result['error']=traceback.format_exc()
        (out/'attempt-failure.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');raise

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);run(p.parse_args().out)
