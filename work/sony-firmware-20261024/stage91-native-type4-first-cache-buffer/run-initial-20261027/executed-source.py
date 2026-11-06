#!/usr/bin/env python3
"""Original type4 pool constructor and first pending-cache buffer in RAM.

Cache maintenance and both IRQ/refcount critical-section boundaries are explicit
unexecuted gaps. Single-guest data flow does not establish runtime synchronization.
"""
from pathlib import Path
import argparse
import datetime
import json
import struct
import sys
import traceback

STAGE=Path(__file__).resolve().parent
BASE,ROOT=STAGE.parent,STAGE.parent.parents[1]
sys.path.insert(0,str(BASE/'stage90-native-metadata-copy-and-caller'))
import metadata_source as prev
im,u,reg,cs,IMAGE=prev.im,prev.u,prev.reg,prev.cs,prev.IMAGE
PRIOR_SHA='9e0c330676c0514aad65d242b1756fda6a1d310c68ae57d1018fddd6e4ac80a4'
GP,CELL=0x8024eb58,0x248e18
REG_PA,REG=0x01000000,0x81000000
ARENA_PA,ARENA=0x01100000,0x81100000
ARENA_SIZE=0x4000
CACHE_PA,CACHE=0x01200000,0x81200000
RECORD_PA,RECORD=0x01300000,0x81300000
FRAME_PA,FRAME=0x01400000,0x81400000
DESC_PA,DESC=0x01500000,0x81500000
SOURCE_PA,SOURCE=0x01600000,0x81600000
HANDLE_PA,HANDLE=0x01700000,0x81700000
STACK_PA,STACK=0x02000000,0x82000000
TRAP_PA,TRAP=0x03000000,0x83000000
ROM=IMAGE+0x2132c0
VTABLE=IMAGE+0x23c2fc
POOL_PA,POOL_MAP_SIZE=0x00c2c000,0x11000
PHYSICAL_BASE,POOL_SIZE,COUNT,BLOCK=0x00c2c140,0x10000,128,512
PROVIDER,HANDLES=ARENA,ARENA+0x40
CACHE_RECORD,CACHE_SLOT=RECORD+0x20,RECORD+0x24
SP_CTOR,SP_BIND,SP_SETUP,SP_FACTORY,SP_CACHE,SP_BULK=[STACK+x for x in (0x2000,0x4000,0x6000,0x8000,0xa000,0xe000)]
SIZES={REG_PA:4096,ARENA_PA:ARENA_SIZE,CACHE_PA:4096,RECORD_PA:4096,
       FRAME_PA:4096,DESC_PA:4096,SOURCE_PA:4096,HANDLE_PA:4096,POOL_PA:POOL_MAP_SIZE}
LIMITS=((0x5d1e8,0x5d24c),(0x67f08,0x67fa8),(0x5d43c,0x5d4a0),
    (0x5d724,0x5d734),(0x5d97c,0x5d990),(0x5d24c,0x5d304),(0x5d318,0x5d340),
    (0x5d398,0x5d3f0),(0x60538,0x60648),(0x5fb38,0x5fc18),(0x69c90,0x69c98),
    (0x13c2d8,0x13c31c),(0x1409fc,0x140a58),(0x140c08,0x140d04),
    (0x140d40,0x140da0),(0x140dd8,0x140e64),(0x5ef3c,0x5efb4),
    (0x606d0,0x60750),(0x5fff0,0x60058),(0x60068,0x600b4))
STOPS={0x5d4a0:'manager_bound_before_unexecuted_initial_provider_loop',
    0x5d734:'secondary_arena_written_before_unexecuted_registration_call',
    0x5d304:'provider_constructed_before_unexecuted_cache_maintenance',
    0x5d990:'provider_returned_and_bound_before_remaining_registration_work',
    0x13c31c:'empty_cache_record_constructed_before_remaining_constructor',
    0x140d04:'pending_flag_set_before_unexecuted_GP_IRQ_acquire',
    0x140da0:'native_allocation_result_stored_before_unexecuted_IRQ_release',
    0x140e64:'after_cache_metadata_copy_or_flag_skip_before_backend_transfer',
    0x141008:'allocation_error_before_unexecuted_failure_diagnostic'}


def word(raw,off):return struct.unpack_from('<I',raw,off)[0]


class Guest:
    def __init__(self,blob,seed,flag,metadata):
        self.blob=blob;self.seed=seed;self.metadata=metadata
        self.uc=u.Uc(u.UC_ARCH_MIPS,u.UC_MODE_MIPS32|u.UC_MODE_LITTLE_ENDIAN)
        self.uc.ctl_set_cpu_model(reg.UC_CPU_MIPS32_24KC)
        self.md=cs.Cs(cs.CS_ARCH_MIPS,cs.CS_MODE_MIPS32|cs.CS_MODE_LITTLE_ENDIAN)
        rw=u.UC_PROT_READ|u.UC_PROT_WRITE;ro=u.UC_PROT_READ
        self.uc.mem_map(0,(len(blob)+4095)&-4096,ro|u.UC_PROT_EXEC);self.uc.mem_write(0,blob)
        # Only this known runtime global may change within the loaded image.
        self.uc.mem_protect(CELL&-4096,4096,rw)
        assert word(blob,CELL)==0
        self.cell=0
        self.initial={at:bytes([seed])*size for at,size in SIZES.items()}
        cache=bytearray(self.initial[CACHE_PA]);struct.pack_into('<III',cache,0,RECORD,0x28,0x20)
        struct.pack_into('<H',cache,0xca0,0x1234);struct.pack_into('<I',cache,0xc8c,0x81800000)
        frame=bytearray(self.initial[FRAME_PA]);frame[0x4c4]=flag;struct.pack_into('<I',frame,0x4c8,HANDLE+4)
        desc=bytearray(self.initial[DESC_PA]);struct.pack_into('<I',desc,0x10,HANDLE)
        source=bytearray(self.initial[SOURCE_PA]);source[0xec:0x11c]=metadata
        handles=struct.pack('<II',FRAME_PA,SOURCE_PA)+bytes(4088)
        for at,raw in ((CACHE_PA,cache),(FRAME_PA,frame),(DESC_PA,desc),(SOURCE_PA,source),(HANDLE_PA,handles)):
            self.initial[at]=bytes(raw)
        self.want={at:bytearray(raw) for at,raw in self.initial.items()}
        for at,size in SIZES.items():
            self.uc.mem_map(at,size,ro if at in (FRAME_PA,DESC_PA,SOURCE_PA,HANDLE_PA) else rw)
            self.uc.mem_write(at,self.initial[at])
        self.uc.mem_map(STACK_PA,65536,rw);self.stack=bytearray([0xd7])*65536
        self.uc.mem_write(STACK_PA,bytes(self.stack))
        self.uc.mem_map(TRAP_PA,4096,ro|u.UC_PROT_EXEC);self.uc.mem_write(TRAP_PA,bytes(4096))
        self.uc.hook_add(u.UC_HOOK_CODE,self.code)
        self.uc.hook_add(u.UC_HOOK_MEM_INVALID,self.invalid)
        self.uc.hook_add(u.UC_HOOK_INTR,self.interrupt)

    def invalid(self,uc,access,address,size,value,user):
        self.reason='invalid:'+hex(address);uc.emu_stop();return False

    def interrupt(self,uc,number,user):
        self.interrupts.append(number);self.reason='native_interrupt';uc.emu_stop()

    def code(self,uc,pc,size,user):
        self.pcs.append(pc)
        if pc==TRAP:self.reason='returned_via_original_jr_ra';uc.emu_stop();return
        off=pc-IMAGE
        if off in self.stops:self.reason=self.stops[off];uc.emu_stop();return
        assert len(self.pcs)<30000
        assert any(lo<=off and off+size<=hi for lo,hi in LIMITS),(hex(pc),size)
        ins=next(self.md.disasm(self.blob[off:off+size],pc),None)
        assert ins is not None,(hex(pc),self.blob[off:off+size].hex())
        if ins.mnemonic=='break':assert off==0x6057c
        else:assert ins.mnemonic not in {'syscall','cache','sync','mfc0','mtc0','eret','wait','tlbwi','tlbwr','tlbr','tlbp'},(hex(pc),ins.mnemonic)
        if ins.mnemonic=='jalr':
            target=uc.reg_read(reg.UC_MIPS_REG_V0)
            assert (off,target) in ((0x5ef98,IMAGE+0x606d0),(0x140d7c,IMAGE+0x60068)),(hex(pc),hex(target))

    def save(self,va,value):struct.pack_into('<I',self.stack,va-STACK,value&0xffffffff)

    def run(self,label,entry,sp=SP_CACHE,preserve=False,extra_stops=None,allow_interrupt=False,**regs):
        values={} if preserve else {'sp':sp,'ra':TRAP,'gp':GP,'fp':0,**{f's{i}':0 for i in range(8)}}
        for name,value in {**values,**regs}.items():self.uc.reg_write(getattr(reg,'UC_MIPS_REG_'+name.upper()),value)
        self.reason=None;self.pcs=[];self.interrupts=[];self.stops={**STOPS,**(extra_stops or {})}
        self.uc.emu_start(IMAGE+entry,0,timeout=2000000,count=0)
        if allow_interrupt:assert self.reason=='native_interrupt' and self.interrupts==[18]
        else:assert self.reason in set(self.stops.values())|{'returned_via_original_jr_ra'} and not self.interrupts,self.reason
        raw=bytes(self.uc.mem_read(0,len(self.blob)))
        assert raw[:CELL]==self.blob[:CELL] and raw[CELL+4:]==self.blob[CELL+4:] and word(raw,CELL)==self.cell
        assert bytes(self.uc.mem_read(STACK_PA,65536))==self.stack
        assert bytes(self.uc.mem_read(TRAP_PA,4096))==bytes(4096)
        for at,size in SIZES.items():assert bytes(self.uc.mem_read(at,size))==self.want[at],hex(at)
        assert self.uc.reg_read(reg.UC_MIPS_REG_GP)==GP
        return {'label':label,'entry':hex(IMAGE+entry),'stop':self.reason,
            'pc':hex(self.uc.reg_read(reg.UC_MIPS_REG_PC)),'SP':hex(self.uc.reg_read(reg.UC_MIPS_REG_SP)),
            'RA':hex(self.uc.reg_read(reg.UC_MIPS_REG_RA)),'V0':hex(self.uc.reg_read(reg.UC_MIPS_REG_V0)),
            'CODE_observed_PCs':[hex(x) for x in self.pcs],
            'all_data_regions_and_full_stack_exact_poststate_checked':True,
            'image_unchanged_except_native_registry_global':True,
            'memory_read_write_hooks_installed':False,'native_interrupts':self.interrupts,
            'PC_observation_may_include_annulled_delay_slots':True,
            'MMIO_instruction_patch_or_fake_return':False}

    def setup(self):
        es=[];r=self.want[REG_PA]
        struct.pack_into('<I',r,0,0x4d4d6772);r[4]=255
        struct.pack_into('<IIIIII',r,8,REG+0x1d8,0x980,0,0,0,0);r[0x20:0x1d8]=bytes(0x1b8)
        self.save(SP_CTOR-0x10,TRAP)
        es.append(self.run('original registry manager constructor and original memset',0x5d1e8,sp=SP_CTOR,a0=REG))
        b=SP_BIND-0x50
        for off in (0x30,0x34,0x38,0x3c,0x40,0x44):self.save(b+off,0)
        self.save(b+0x48,TRAP);self.cell=REG
        es.append(self.run('original manager magic check and runtime global binding prefix',0x5d43c,sp=SP_BIND,a0=REG))
        struct.pack_into('<III',r,0x14,ARENA,ARENA_SIZE,0)
        es.append(self.run('original secondary-arena stores before registration and IRQ work',
            0x5d724,sp=SP_SETUP,a0=REG,s0=0,s1=ARENA,s2=ARENA_SIZE))
        # Enter the type4 factory call after unexecuted table validation/IRQ work.
        factory=SP_FACTORY-0x20
        self.save(factory+0x10,REG+16);self.save(factory+0x14,ROM);self.save(factory+0x18,IMAGE+0x5d988)
        ctor=factory-0x30
        for off,val in ((0x10,PROVIDER),(0x14,REG+0x14),(0x18,16),(0x1c,0),(0x20,IMAGE+0x5d3e8)):
            self.save(ctor+off,val)
        self.save(ctor-0x20+0x10,IMAGE+0x6055c)
        struct.pack_into('<I',r,0x1c,0xe40)
        arena=self.want[ARENA_PA]
        for off,val in ((0,VTABLE),(4,4),(8,PHYSICAL_BASE),(0xc,POOL_SIZE),(0x10,COUNT),
            (0x14,HANDLES),(0x18,HANDLES),(0x20,0),(0x24,0),(0x2c,0),(0x30,0),(0x34,BLOCK)):
            struct.pack_into('<I',arena,off,val)
        struct.pack_into('<H',arena,0x1c,COUNT);struct.pack_into('<H',arena,0x28,0)
        for i in range(COUNT):
            struct.pack_into('<7I',arena,0x40+i*28,PHYSICAL_BASE+i*BLOCK,BLOCK,0,PROVIDER,
                             HANDLES+(i+1)*28 if i+1<COUNT else 0,0,0)
        es.append(self.run('original type4 factory and complete fixed-provider constructor before cache maintenance',
                          0x5d97c,sp=SP_FACTORY,s1=ROM,s2=16,t0=REG))
        assert es[-1]['stop']==STOPS[0x5d304]
        assert self.uc.reg_read(reg.UC_MIPS_REG_S0)==PROVIDER
        # No CACHE instruction is executed or replaced; the gap stays explicit.
        struct.pack_into('<I',r,0x30,PROVIDER)
        es.append(self.run('original post-cache factory tail returns and binds actual provider result',0x5d318,preserve=True))
        assert es[-1]['stop']==STOPS[0x5d990] and es[-1]['SP']==hex(SP_FACTORY)
        assert self.uc.reg_read(reg.UC_MIPS_REG_V0)==PROVIDER
        self.want[RECORD_PA][0x20]=0;self.want[RECORD_PA][0x24:0x28]=bytes(4)
        struct.pack_into('<I',self.want[CACHE_PA],8,0x28)
        struct.pack_into('<I',self.want[CACHE_PA],0xc90,CACHE_RECORD)
        es.append(self.run('original empty eight-byte pending-cache record allocation',0x13c2d8,s1=CACHE))
        return es

    def expected_allocation(self,requested=0x11c):
        a=self.want[ARENA_PA];free=struct.unpack_from('<H',a,0x1c)[0]
        if not free:return 0
        handle=word(a,0x18);off=handle-ARENA
        struct.pack_into('<H',a,0x1c,free-1);struct.pack_into('<I',a,0x18,word(a,off+0x10))
        struct.pack_into('<I',a,off+4,requested);a[off+8]=1
        struct.pack_into('<I',a,off+0x10,0);a[off+0x14]=0
        return handle

    def allocation_stack(self,sp,caller_ra,s1,s0):
        dispatch=sp-0x50
        for off,val in ((0x40,s0),(0x44,s1),(0x48,caller_ra)):self.save(dispatch+off,val)
        provider=dispatch-0x20
        for off,val in ((0x10,s0),(0x14,s1),(0x18,IMAGE+0x5efa0)):self.save(provider+off,val)
        pop=provider-0x20
        self.save(pop+0x10,0x11c);self.save(pop+0x14,IMAGE+0x60724)

    def exhaust(self):
        es=[];handles=[]
        for i in range(COUNT):
            handle=self.expected_allocation();assert handle==HANDLES+i*28
            self.allocation_stack(SP_BULK,TRAP,0,0)
            e=self.run('original dispatcher exhaustion allocation '+str(i+1),0x5ef3c,sp=SP_BULK,a0=4,a1=0x11c)
            assert e['stop']=='returned_via_original_jr_ra' and int(e['V0'],16)==handle
            es.append(e);handles.append(handle)
        assert struct.unpack_from('<H',self.want[ARENA_PA],0x1c)[0]==0
        return es,handles

    def writer_prefix(self,flag):
        struct.pack_into('<H',self.want[CACHE_PA],0xca0,0x1235)
        if flag:self.want[RECORD_PA][0x20]|=0x10
        e=self.run('original source-frame pending-cache writer through first missing buffer',
                   0x1409fc,s2=CACHE,s4=DESC)
        assert e['stop']==STOPS[0x140d04 if flag else 0x140e64]
        return e

    def cache_allocate(self,release=False):
        if release:
            # Original d40 body decrements ref1->0, calls the original provider
            # free method, then allocates again. No host writes are applied.
            a=self.want[ARENA_PA];handle=word(self.want[RECORD_PA],0x24);off=handle-ARENA
            assert a[off+8]==1
            a[off+8]=0
            struct.pack_into('<I',a,off+0x10,word(a,0x18))
            struct.pack_into('<I',a,0x18,handle)
            struct.pack_into('<H',a,0x1c,struct.unpack_from('<H',a,0x1c)[0]+1)
        allocated=self.expected_allocation()
        struct.pack_into('<I',self.want[RECORD_PA],0x24,allocated)
        self.allocation_stack(SP_CACHE,IMAGE+0x140d94,CACHE_RECORD,0xb1020000)
        e=self.run('original existing-reference release and native type4 reallocation' if release else
            'original first-cache allocation and returned-handle store after unexecuted IRQ acquire',0x140d40,preserve=True)
        assert e['stop']==STOPS[0x140da0]
        status=self.uc.reg_read(reg.UC_MIPS_REG_S0)
        assert status==(0 if allocated else 0xb1020001)
        assert int(e['V0'],16)==allocated and e['SP']==hex(SP_CACHE)
        return e,allocated,status

    def transfer(self,allocated):
        if allocated:
            offset=PHYSICAL_BASE-POOL_PA
            self.want[POOL_PA][offset+0xec:offset+0x11c]=self.metadata
        e=self.run('original post-IRQ-release result branch and physical-buffer metadata copy',0x140dd8,preserve=True)
        assert e['stop']==STOPS[0x140e64 if allocated else 0x141008]
        return e


def calibrate(blob,metadata):
    out=[]
    for count in (128,1,0):
        m=Guest(blob,0xa5,0x10,metadata);struct.pack_into('<I',m.want[ARENA_PA],0,VTABLE)
        e=m.run('original DIVU/BEQL/BREAK observer calibration',0x6056c,
            a3=count,a1=POOL_SIZE,s2=PROVIDER,v0=VTABLE,
            extra_stops={0x60580:'calibrated_before_following_constructor_work'},allow_interrupt=count==0)
        assert hex(IMAGE+0x6057c) in e['CODE_observed_PCs']
        if count:assert m.uc.reg_read(reg.UC_MIPS_REG_LO)==POOL_SIZE//count
        out.append({'declared_divisor':count,'quotient':m.uc.reg_read(reg.UC_MIPS_REG_LO) if count else None,'event':e})
    return out


def one(blob,metadata,seed,kind):
    flag=0 if kind=='event_off' else 0x10
    m=Guest(blob,seed,flag,metadata);events=m.setup();exhausted=[]
    if kind=='exhausted':
        es,exhausted=m.exhaust();events+=es
    events.append(m.writer_prefix(flag));allocated=None;status=None;reused=None
    if flag:
        e,allocated,status=m.cache_allocate();events.append(e)
        events.append(m.transfer(allocated))
        if kind=='normal_reuse':
            first=allocated;e,reused,status=m.cache_allocate(release=True);events.append(e)
            assert reused==first
            events.append(m.transfer(reused))
    return {'seed':seed,'kind':kind,'declared_source_frame_flag':flag,
        'native_first_cache_handle':allocated,'native_reacquired_handle':reused,'native_allocation_status':status,
        'exhausted_by_native_allocations':exhausted,
        'remaining_free_blocks':struct.unpack_from('<H',m.want[ARENA_PA],0x1c)[0],
        'final_pages':{hex(at):bytes(raw).hex() for at,raw in m.want.items()},'events':events,
        'native_registry_pointer':m.cell,'declared_metadata48_hex':metadata.hex(),
        'unexecuted_gaps':['registration checks and IRQ acquisition before type4 factory',
            'factory cache maintenance','cache caller IRQ acquisition and IRQ release'],
        'actual_runtime_sync_ownership_dispatch_MAIN_hardware_or_recovery_proven':False,
        'host_supplied_cache_handle_free_count_or_return_value':False}


def main():
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);out=Path(p.parse_args().output)
    im.volume();assert not out.exists()
    prior=BASE/'stage90-native-metadata-copy-and-caller/final-receipt.json'
    assert im.sha(prior.read_bytes())==PRIOR_SHA
    for f in json.loads(prior.read_text())['files']:
        raw=(ROOT/f['path']).read_bytes();assert len(raw)==f['bytes'] and im.sha(raw)==f['sha256']
    assert (STAGE/'goal-status-before.json').read_bytes()==(BASE/'GOAL_STATUS.json').read_bytes()
    blob_path=prev.prev.old.old.prev.a.prev.p.a.v.VCD_PATH
    blob=blob_path.read_bytes();assert im.sha(blob)==im.PINS[str(blob_path.relative_to(BASE))]
    assert prev.app_gp(blob)==GP and struct.unpack_from('<4I',blob,0x2132c0)==(4,PHYSICAL_BASE,POOL_SIZE,COUNT)
    assert word(blob,0x23c30c)==IMAGE+0x606d0 and word(blob,0x23c304)==IMAGE+0x60068
    source=BASE/'stage86-hevc-vui-mode-conversion/run-20261026/vui-mode-results.json'
    case=next(c for c in json.loads(source.read_text())['cases'] if c['seed']==0xa5 and c['kind']=='captured' and c['source_label']=='selected1_raw5')
    metadata=prev.prev.old.declared_metadata(bytes.fromhex(case['GOP_after_hex']))
    out.mkdir();(out/'executed-source.py').write_bytes(Path(__file__).read_bytes())
    cases=[]
    try:
        probes=calibrate(blob,metadata)
        for seed,kind in ((0xa5,'normal_reuse'),(0xc3,'normal'),(0xa5,'exhausted'),(0xc3,'event_off')):
            cases.append(one(blob,metadata,seed,kind))
    except Exception:
        im.write_json(out/'failed-attempt.json',{'traceback':traceback.format_exc(),'completed_cases':len(cases)})
        raise
    j={'status':'PASS_NATIVE_TYPE4_POOL_FIRST_CACHE_HANDLE_COPY_EXHAUSTION_AND_REUSE_WITH_EXPLICIT_GAPS',
        'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'source_receipt':{'script_sha256':im.sha(Path(__file__).read_bytes()),'VCD_sha256':im.sha(blob),
            'prior_manifest_sha256':PRIOR_SHA,'stage86_result_sha256':im.sha(source.read_bytes())},
        'ROM_type4_descriptor':{'file_offset':'0x2132c0','type':4,'physical_base':hex(PHYSICAL_BASE),
            'region_bytes':POOL_SIZE,'blocks':COUNT,'native_block_bytes':BLOCK,'cache_request_bytes':0x11c},
        'observer_calibration':probes,'cases':cases,'bounded_phases':sum(len(c['events']) for c in cases),
        'scope':'Original constructors, type4 native virtual allocation/free and cache first-handle store/48-byte copy in declared quiescent RAM. '
            'Cache maintenance and original critical-section work remain unexecuted, no instruction replacements or fake returns. '
            'Source-frame flag/payload and arena availability are declared. No actual MAIN, synchronization, hardware, camera or recovery acceptance.',
        'Windows_UU_camera_operations':False,'goal_complete':False,'persistent_write_release':False}
    im.write_json(out/'type4-cache-results.json',j)
    print(json.dumps({'status':j['status'],'cases':len(cases),'calibrations':len(probes),
        'bounded_phases':j['bounded_phases'],'output':str(out)}))


if __name__=='__main__':main()
