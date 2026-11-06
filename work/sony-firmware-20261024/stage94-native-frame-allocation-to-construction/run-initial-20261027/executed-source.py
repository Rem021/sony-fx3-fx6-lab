#!/usr/bin/env python3
"""Native type4+type5 allocation, original parent descriptor and frame ctor.

Registration/cache-maintenance/IRQ gaps remain explicit. Raw metadata is a
declared input referring to the native type4 allocation, not a real message.
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
sys.path.insert(0,str(BASE/'stage93-native-frame-header-and-crop-reconciliation'))
import frame_crop as prev
old=prev.old
im,u,reg,cs,IMAGE=prev.im,prev.u,prev.reg,prev.cs,prev.IMAGE
PRIOR_SHA='9925f524b68926aa7874e1793a08afb4dff653583cef7c6e8841a8e0daa14e3c'
REG_PA,REG=0x04000000,0x84000000
ARENA_PA,ARENA=0x04100000,0x84100000
ARENA_SIZE=0x4000
POOL_PA,POOL_SIZE=0x00c2c000,0x38000
CELL=0x248e18
VTABLE=IMAGE+0x23c2fc
P4,H4,PHYS4=ARENA,ARENA+0x40,0x00c2c140
P5,H5,PHYS5=ARENA+0xe40,ARENA+0xe80,0x00c3c140
FRAME=IMAGE+PHYS5
BODY_SP=prev.prev.SP_CALL
PARENT_SP=BODY_SP+0x60
SP_MGR,SP_SOURCE,SP_BIND,SP_SETUP,SP_FACTORY,SP_BULK=[old.STACK+x for x in (0x2000,0x3000,0x4000,0x5000,0x8000,0xe000)]
SPECS={4:{'rom':IMAGE+0x2132c0,'provider':P4,'handles':H4,'physical':PHYS4,'bytes':0x10000,'block':0x200},
       5:{'rom':IMAGE+0x2132d0,'provider':P5,'handles':H5,'physical':PHYS5,'bytes':0x27800,'block':0x4f0}}
STOPS={**prev.STOPS,
    0x5d4a0:'native_manager_bound_before_unexecuted_bootstrap',
    0x5d734:'native_secondary_arena_stored_before_unexecuted_registration',
    0x5d304:'native_provider_constructed_before_unexecuted_cache_maintenance',
    0x5d990:'native_factory_return_bound_before_remaining_registration',
    0x143fc0:'native_parent_frame_saved_before_unexecuted_GP_lock_ID_read',
    0x143ff8:'native_descriptor_and_empty_frame_slot_before_unexecuted_lock_ID_store',
    0x144090:'native_frame_allocation_handle_stored_before_unexecuted_IRQ_release',
    0x144334:'native_frame_allocation_failure_before_unexecuted_diagnostic'}
LIMITS=prev.LIMITS+((0x5d1e8,0x5d24c),(0x5d43c,0x5d4a0),(0x5d724,0x5d734),
    (0x5d978,0x5d990),(0x5d24c,0x5d304),(0x5d318,0x5d340),(0x5d398,0x5d3f0),
    (0x60538,0x60648),(0x5fb38,0x5fc18),(0x69c90,0x69c98),(0x5ef3c,0x5efb4),
    (0x606d0,0x60750),(0x5fff0,0x60058),(0x143f98,0x143fc0),(0x143fc4,0x143ff8),
    (0x144030,0x144090),(0x1440c8,0x144124))


def constructor_bytes(seed):
    # Same original constructor write plan reviewed in stage93; preserved
    # holes now come from the allocated physical pool, not a declared frame.
    f=bytearray([seed])*0x4f0
    for at in (0,1,2,0x14,0x38,0x39,0x3a,0x3b,0x3c,0x3d,0x44,0x58,0x6c,
               0xd0,0xd1,0xd2,0xd3,0xd4,0xd5,0xd6,0x438,0x439,0x4c4,0x4d0,
               0x4d8,0x4d9,0x4da,0x4db,0x4dc):f[at]=0
    f[4:0x14]=bytes(16);f[0xa4:0xb2]=bytes(14)
    for at in (0x18,0x1c,0x20,0x24,0x28,0x2c,0x30,0x34,0x40,0x48,0x4c,0x50,0x54,
               0x5c,0x60,0x64,0x68,0x70,0x74,0x78,0x7c,0x80,0x84,0x88,0x8c,
               0x90,0x94,0x98,0x9c,0xb4,0xb8,0xc0,0xdc,
               0x3e8,0x3ec,0x3f0,0x3f4,0x3f8,0x3fc,0x400,0x404,
               0x408,0x40c,0x410,0x414,0x418,0x41c,0x420,0x428,0x42c,0x430,0x434,
               0x468,0x46c,0x478,0x47c,0x480,0x484,0x490,0x494,0x498,0x49c,
               0x4a0,0x4a4,0x4a8,0x4ac,0x4b0,0x4b4,0x4b8,0x4bc,0x4c0,0x4c8,0x4cc,
               0x4d4,0x4e8):struct.pack_into('<I',f,at,0)
    for at in (0xd8,0xe0,0x4e4):struct.pack_into('<H',f,at,0)
    for at in (0xa0,0xc8,0xcc):struct.pack_into('<I',f,at,0xffffffff)
    f[0xbc]=1;f[0x4e0:0x4e4]=bytes([15])*4
    for lo,hi in ((0xe8,0x143),(0x144,0x27c),(0x280,0x3e8),(0x440,0x468)):f[lo:hi]=bytes(hi-lo)
    struct.pack_into('<I',f,0x43c,old.GP-0x5d58)
    for at in (0x470,0x474,0x488,0x48c):struct.pack_into('<I',f,at,1)
    return f


class Guest(prev.Guest):
    def __init__(self,blob,seed,flag,metadata):
        super().__init__(blob,seed,1,flag,(120,68));self.seed=seed
        self.sizes={at:len(raw) for at,raw in self.want.items()}
        for at,size in ((REG_PA,4096),(ARENA_PA,ARENA_SIZE),(POOL_PA,POOL_SIZE)):
            self.uc.mem_map(at,size,u.UC_PROT_READ|u.UC_PROT_WRITE)
            raw=bytearray([seed])*size
            if at==POOL_PA:raw[PHYS4-POOL_PA+0xec:PHYS4-POOL_PA+0x11c]=metadata
            self.uc.mem_write(at,bytes(raw));self.want[at]=raw;self.sizes[at]=size
        raw=bytearray(self.want[old.SRC_PA]);struct.pack_into('<I',raw,0x54,H4)
        self.want[old.SRC_PA]=raw;self.uc.mem_write(old.SRC_PA,bytes(raw))
        self.uc.mem_protect(old.FRAME_PA,4096,u.UC_PROT_READ)
        self.uc.mem_protect(CELL&-4096,4096,u.UC_PROT_READ|u.UC_PROT_WRITE)
        assert old.word(blob,CELL)==0;self.cell=0
        self.constructor_expected=bytes(constructor_bytes(seed))

    def read(self,at):return bytes(self.uc.mem_read(at,self.sizes[at]))

    def code(self,uc,pc,size,user):
        self.pcs.append(pc)
        if pc==old.TRAP:self.reason='returned_via_original_jr_ra';uc.emu_stop();return
        off=pc-IMAGE
        if off in self.stops:self.reason=self.stops[off];uc.emu_stop();return
        assert len(self.pcs)<30000
        assert any(lo<=off and off+size<=hi for lo,hi in LIMITS),(hex(pc),size)
        ins=next(self.md.disasm(self.blob[off:off+size],pc),None)
        assert ins is not None,(hex(pc),self.blob[off:off+size].hex())
        if ins.mnemonic=='break':assert off in (0x6057c,0x13489c)
        else:assert ins.mnemonic not in {'syscall','cache','sync','mfc0','mtc0','eret','wait','tlbwi','tlbwr','tlbr','tlbp'},(hex(pc),ins.mnemonic)
        if ins.mnemonic=='jalr':
            assert off==0x5ef98 and uc.reg_read(reg.UC_MIPS_REG_V0)==IMAGE+0x606d0
        if off==0x66bb8:
            self.geometry_arguments.append({n:uc.reg_read(getattr(reg,'UC_MIPS_REG_'+n.upper())) for n in ('a0','a1','a2')})
        if off==0x1f8550:
            address=uc.reg_read(reg.UC_MIPS_REG_A0);assert address==FRAME
            self.frame_checkpoints.append({'point':'original_constructor_entry','A0':hex(address)})
        if off==0x144124:
            raw=bytes(uc.mem_read(PHYS5,0x4f0));assert raw==self.constructor_expected
            assert old.word(raw,0x4c8)==0 and raw[0x4c4]==0
            self.frame_checkpoints.append({'point':'constructor_return_to_original_parent',
                'frame_VA':hex(FRAME),'frame_sha256':im.sha(raw),'parameter_handle':0,'update_flag':0})

    def run(self,label,entry,sp=prev.prev.SP_SEL,preserve=False,remove_stops=(),**regs):
        initial={} if preserve else {'sp':sp,'ra':old.TRAP,'gp':old.GP,'fp':0,**{f's{i}':0 for i in range(8)}}
        for name,value in {**initial,**regs}.items():self.uc.reg_write(getattr(reg,'UC_MIPS_REG_'+name.upper()),value)
        self.reason=None;self.pcs=[];self.interrupts=[];self.geometry_arguments=[];self.frame_checkpoints=[]
        self.stops=dict(STOPS)
        for off in remove_stops:self.stops.pop(off)
        self.uc.emu_start(IMAGE+entry,0,timeout=2000000,count=0)
        assert self.reason in set(self.stops.values())|{'returned_via_original_jr_ra'} and not self.interrupts,self.reason
        raw=bytes(self.uc.mem_read(0,len(self.blob)))
        assert raw[:CELL]==self.blob[:CELL] and raw[CELL+4:]==self.blob[CELL+4:] and old.word(raw,CELL)==self.cell
        assert bytes(self.uc.mem_read(old.STACK_PA,65536))==self.stack
        for at,raw in self.want.items():assert self.read(at)==bytes(raw),hex(at)
        assert bytes(self.uc.mem_read(old.TRAP_PA,4096))==bytes(4096)
        return {'label':label,'entry':hex(IMAGE+entry),'stop':self.reason,
            'pc':hex(self.uc.reg_read(reg.UC_MIPS_REG_PC)),'SP':hex(self.uc.reg_read(reg.UC_MIPS_REG_SP)),
            'RA':hex(self.uc.reg_read(reg.UC_MIPS_REG_RA)),'V0':hex(self.uc.reg_read(reg.UC_MIPS_REG_V0)),
            'CODE_observed_PCs':[hex(x) for x in self.pcs],
            'native_geometry_helper_arguments':self.geometry_arguments,'frame_checkpoints':self.frame_checkpoints,
            'all_regions_and_entire_stack_exact_poststate_checked':True,
            'image_unchanged_except_native_registry_global':True,
            'memory_read_write_hooks_installed':False,'native_interrupts':self.interrupts,
            'PC_observation_may_include_annulled_delay_slots':True,'MMIO_instruction_patch_or_fake_return':False}

    def setup_pools(self):
        es=[];r=self.want[REG_PA]
        struct.pack_into('<I',r,0,0x4d4d6772);r[4]=255
        struct.pack_into('<6I',r,8,REG+0x1d8,0x980,0,0,0,0);r[0x20:0x1d8]=bytes(0x1b8)
        self.save(SP_MGR-0x10,old.TRAP)
        es.append(self.run('original manager constructor',0x5d1e8,sp=SP_MGR,a0=REG))
        base=SP_BIND-0x50
        for off in (0x30,0x34,0x38,0x3c,0x40,0x44):self.save(base+off,0)
        self.save(base+0x48,old.TRAP);self.cell=REG
        es.append(self.run('original manager runtime-global binding prefix',0x5d43c,sp=SP_BIND,a0=REG))
        struct.pack_into('<III',r,0x14,ARENA,ARENA_SIZE,0)
        es.append(self.run('original secondary-arena stores',0x5d724,sp=SP_SETUP,a0=REG,s0=0,s1=ARENA,s2=ARENA_SIZE))
        for kind in (4,5):
            s=SPECS[kind];index=kind*4;provider=s['provider'];handles=s['handles'];rom=s['rom']
            base=SP_FACTORY-0x20
            self.save(base+0x10,REG+index);self.save(base+0x14,rom);self.save(base+0x18,IMAGE+0x5d988)
            ctor=base-0x30
            for off,value in ((0x10,provider),(0x14,REG+0x14),(0x18,index),(0x1c,0),(0x20,IMAGE+0x5d3e8)):
                self.save(ctor+off,value)
            self.save(ctor-0x20+0x10,IMAGE+0x6055c)
            struct.pack_into('<I',r,0x1c,handles-ARENA+128*28)
            arena=self.want[ARENA_PA];at=provider-ARENA
            for off,value in ((0,VTABLE),(4,kind),(8,s['physical']),(0xc,s['bytes']),(0x10,128),
                (0x14,handles),(0x18,handles),(0x20,0),(0x24,0),(0x2c,0),(0x30,0),(0x34,s['block'])):
                struct.pack_into('<I',arena,at+off,value)
            struct.pack_into('<H',arena,at+0x1c,128);struct.pack_into('<H',arena,at+0x28,0)
            for i in range(128):
                struct.pack_into('<7I',arena,handles-ARENA+i*28,s['physical']+i*s['block'],s['block'],0,provider,
                                 handles+(i+1)*28 if i<127 else 0,0,0)
            es.append(self.run('original type'+str(kind)+' factory and constructor before cache work',
                              0x5d978,sp=SP_FACTORY,s1=rom,s2=index,t0=REG))
            assert es[-1]['stop']==STOPS[0x5d304]
            struct.pack_into('<I',r,0x20+index,provider)
            es.append(self.run('original post-cache factory return and type'+str(kind)+' registry store',0x5d318,preserve=True))
            assert es[-1]['stop']==STOPS[0x5d990]
        return es

    def expected_allocate(self,kind,request):
        s=SPECS[kind];a=self.want[ARENA_PA];at=s['provider']-ARENA
        free=struct.unpack_from('<H',a,at+0x1c)[0]
        if not free:return 0
        handle=old.word(a,at+0x18);off=handle-ARENA
        struct.pack_into('<H',a,at+0x1c,free-1);struct.pack_into('<I',a,at+0x18,old.word(a,off+0x10))
        struct.pack_into('<I',a,off+4,request);a[off+8]=1;struct.pack_into('<I',a,off+0x10,0);a[off+0x14]=0
        return handle

    def allocation_stack(self,kind,request,sp,return_pc,s0,s1):
        dispatch=sp-0x50
        for off,value in ((0x40,s0),(0x44,s1),(0x48,return_pc)):self.save(dispatch+off,value)
        provider=dispatch-0x20
        for off,value in ((0x10,SPECS[kind]['provider']),(0x14,request),(0x18,IMAGE+0x5efa0)):self.save(provider+off,value)
        self.save(provider-0x20+0x10,request);self.save(provider-0x20+0x14,IMAGE+0x60724)

    def allocate_source(self):
        actual=self.expected_allocate(4,0x11c);assert actual==H4
        self.allocation_stack(4,0x11c,SP_SOURCE,old.TRAP,0,0)
        e=self.run('original type4 source-parameter allocation matching declared metadata reference',
            0x5ef3c,sp=SP_SOURCE,a0=4,a1=0x11c)
        assert int(e['V0'],16)==H4 and e['stop']=='returned_via_original_jr_ra'
        return e

    def exhaust_frames(self):
        es=[];handles=[]
        for i in range(128):
            handle=self.expected_allocate(5,0x4f0);assert handle==H5+i*28
            self.allocation_stack(5,0x4f0,SP_BULK,old.TRAP,0,0)
            e=self.run('original type5 exhaustion request '+str(i+1),0x5ef3c,sp=SP_BULK,a0=5,a1=0x4f0)
            assert int(e['V0'],16)==handle and e['stop']=='returned_via_original_jr_ra'
            es.append(e);handles.append(handle)
        return es,handles

    def parent_allocate(self):
        es=[]
        for off in (0x40,0x44,0x48,0x4c,0x50):self.save(BODY_SP+off,0)
        self.save(BODY_SP+0x54,old.TRAP)
        es.append(self.run('original parent prologue before lock-ID read',0x143f98,sp=PARENT_SP,a0=old.INSTANCE,a1=old.SRC))
        src=self.want[old.SRC_PA]
        self.stack[BODY_SP+0x10-old.STACK]=src[0];self.stack[BODY_SP+0x11-old.STACK]=src[1]
        struct.pack_into('<H',self.stack,BODY_SP+0x12-old.STACK,struct.unpack_from('<H',src,2)[0])
        self.save(BODY_SP+0x14,old.word(src,4));self.save(BODY_SP+0x18,old.word(src,8))
        self.stack[BODY_SP+0x1c-old.STACK]=src[0xc];self.save(BODY_SP+0x20,0)
        es.append(self.run('original parent descriptor stores after unexecuted GP read',0x143fc4,preserve=True))
        handle=self.expected_allocate(5,0x4f0)
        self.save(BODY_SP+0x20,handle)
        self.allocation_stack(5,0x4f0,BODY_SP,IMAGE+0x144084,0xb1020000,old.SRC)
        es.append(self.run('original empty frame slot to native type5 allocation and handle store',0x144030,preserve=True))
        assert es[-1]['stop']==STOPS[0x144090]
        assert self.uc.reg_read(reg.UC_MIPS_REG_S0)==(0 if handle else 0xb1020001)
        return es,handle

    def finish_parent(self,flag,handle):
        if not handle:
            e=self.run('original failed allocation status branch before diagnostic',0x1440c8,preserve=True,remove_stops=(0x131888,))
            assert e['stop']==STOPS[0x144334] and not e['frame_checkpoints']
            return e,None
        f=bytearray(self.constructor_expected);o=self.want[old.OWNER_PA];src=self.want[old.SRC_PA]
        before_owner=bytes(o)
        # The original caller passes the native handle's physical address to
        # the constructor. These are expected saves, never host CPU returns.
        ctor=BODY_SP-0x20
        self.save(ctor+0x10,0);self.save(ctor+0x14,IMAGE+0x144124)
        for off,value in ((0x10,FRAME),(0x14,old.SRC),(0x18,old.INSTANCE),(0x1c,IMAGE+0x1f8680)):
            self.save(ctor-0x20+off,value)
        if flag:
            self.save(BODY_SP-0x10,IMAGE+0x1441c8);self.save(BODY_SP-0x30,IMAGE+0x134fa0)
            data,classes,_=self.expected_geometry((120,68),1)
            self.geometry_stack(BODY_SP-0x40,old.OWNER+0x10,old.OWNER+8,0,old.SRC,old.INSTANCE,IMAGE+0x131e68,classes)
        base=BODY_SP-0x80
        self.save(BODY_SP-0x10,IMAGE+0x1441d8)
        for off,value in ((0x40,0),(0x44,old.SRC),(0x48,old.INSTANCE),(0x4c,0),
                          (0x50,BODY_SP+0x20),(0x54,0),(0x58,0),(0x5c,IMAGE+0x1351c0)):
            self.save(base+off,value)
        self.save(base-0x20+0x10,FRAME);self.save(base-0x20+0x14,IMAGE+0x131898)
        f[0]=src[2];f[1]=0;f[2]=int(o[0x2a]!=0)
        struct.pack_into('<4H',f,4,120,68,68,68)
        word=prev.ins(old.word(f,0xc),1,18,2)&0xfffff
        word=prev.ins(word,struct.unpack_from('<H',o,0x98)[0]+1,16,2);struct.pack_into('<I',f,0xc,word)
        struct.pack_into('<HH',f,0x10,1920,1088)
        value=prev.ins(old.word(f,0x2c),old.word(o,0x98),0,1)
        value=prev.ins(value&0xffffff8f,0,29,3);table=self.blob[0x248cc4:0x248cc7]
        value=prev.ins(value,table[o[8]],21,2);value=prev.ins(value,table[o[9]],23,1)
        struct.pack_into('<I',f,0x2c,value)
        value=prev.ins(old.word(f,0x30),o[0x31],30,1);value=prev.ins(value,o[0x32],31,1)
        struct.pack_into('<I',f,0x30,prev.ins(value,o[0xf],12,4))
        f[0x4d8]=f[0x4d9]=0;f[0x38:0x3b]=o[0xa:0xd]
        f[0x3b]=(o[0xd]+o[0xe])&255;f[0x3c]=f[0x39];f[0x3d]=f[0x3b]
        f[0x14:0x28]=before_owner[0x80:0x94]
        flagword=(old.word(self.stack,base+0x10-old.STACK)&0xffffff00)|1
        for off,value in ((0x10,flagword),(0x14,old.word(src,0x10)),(0x18,old.word(src,0x14)),(0x1c,old.word(src,0x18)),(0x20,0)):
            self.save(base+off,value)
        struct.pack_into('<5I',f,0x6c,flagword,old.word(src,0x10),old.word(src,0x14),old.word(src,0x18),0)
        struct.pack_into('<5I',o,0x80,flagword,old.word(src,0x10),old.word(src,0x14),old.word(src,0x18),0)
        f[0x4da]=int(o[0x36]!=0);f[0x4db]=int(o[0x35]!=0)
        struct.pack_into('<I',o,0x98,(1-old.word(before_owner,0x98))&0xffffffff)
        if flag:f[0x4c4]=flag;struct.pack_into('<I',f,0x4c8,H4)
        else:
            struct.pack_into('<H',f,0xc,struct.unpack_from('<H',o,0x28)[0])
            if o[0x37]:f[0x4d0]=1
        offset=PHYS5-POOL_PA;self.want[POOL_PA][offset:offset+0x4f0]=f
        e=self.run('original allocated-frame translation, constructor, geometry and header without interior gap',
                   0x1440c8,preserve=True,remove_stops=(0x131888,))
        assert e['stop']==prev.STOPS[0x131c20 if flag else 0x1441e4]
        assert len(e['frame_checkpoints'])==2
        return e,bytes(f)


def one(blob,seed,flag,exhaust,metadata):
    m=Guest(blob,seed,flag,metadata);events=m.setup_pools();events.append(m.allocate_source())
    events.append(m.defaults());e,_=m.classify_and_build((120,68),1);events.append(e)
    events.append(m.prepare_geometry((120,68),1))
    preallocated=[]
    if exhaust:
        es,preallocated=m.exhaust_frames();events+=es
    es,handle=m.parent_allocate();events+=es;e,frame=m.finish_parent(flag,handle);events.append(e)
    a=m.want[ARENA_PA]
    return {'seed':seed,'declared_update_byte50':flag,'frame_pool_exhausted':exhaust,
        'native_parameter_handle':H4,'native_frame_handle':handle,'native_frame_VA':hex(FRAME) if handle else None,
        'native_type4_reference_byte':a[H4-ARENA+8],
        'native_type5_reference_byte':a[H5-ARENA+8],
        'native_free_type4':struct.unpack_from('<H',a,P4-ARENA+0x1c)[0],
        'native_free_type5':struct.unpack_from('<H',a,P5-ARENA+0x1c)[0],
        'preallocated_frame_handles':preallocated,'frame_after_hex':frame.hex() if frame else None,
        'final_regions':{hex(at):bytes(raw).hex() for at,raw in m.want.items()},'events':events,
        'raw_metadata_still_declared_not_real_message':True,
        'host_sets_frame_address_descriptor_handle_free_count_or_return_value':False,
        'unexecuted_boundaries':['registration/validation/IRQ before factory','factory cache maintenance',
            '143fc0 GP lock-ID read','143ff8..14402c lock-ID save/IRQ acquire','144090..1440c4 IRQ release',
            'new parameter reference increment or external virtual-table dispatch'],
        'actual_MAIN_IRQ_sync_HEVC_video_or_recovery_proven':False}


def main():
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);out=Path(p.parse_args().output)
    im.volume();assert not out.exists()
    prior=BASE/'stage93-native-frame-header-and-crop-reconciliation/final-receipt.json'
    assert im.sha(prior.read_bytes())==PRIOR_SHA
    for f in json.loads(prior.read_text())['files']:
        raw=(ROOT/f['path']).read_bytes();assert len(raw)==f['bytes'] and im.sha(raw)==f['sha256']
    assert (STAGE/'goal-status-before.json').read_bytes()==(BASE/'GOAL_STATUS.json').read_bytes()
    source_receipt=BASE/'stage91-native-type4-first-cache-buffer/final-receipt.json'
    assert im.sha(source_receipt.read_bytes())==json.loads((BASE/'stage92-native-geometry-builder-and-IRQ-scope/final-receipt.json').read_text())['previous_manifest_sha256']
    for f in json.loads(source_receipt.read_text())['files']:
        raw=(ROOT/f['path']).read_bytes();assert len(raw)==f['bytes'] and im.sha(raw)==f['sha256']
    source=BASE/'stage91-native-type4-first-cache-buffer/run-corrected-call-frame-20261027/type4-cache-results.json'
    metadata=bytes.fromhex(json.loads(source.read_text())['cases'][0]['declared_metadata48_hex'])
    assert len(metadata)==48 and struct.unpack_from('<HH',metadata)==(119,67)
    blob_path=BASE/'stage2/extraction/files/nflasha15/codec/vcd_firmware_imola2.bin'
    blob=blob_path.read_bytes();assert im.sha(blob)==im.PINS[str(blob_path.relative_to(BASE))]
    for kind,s in SPECS.items():assert struct.unpack_from('<4I',blob,s['rom']-IMAGE)==(kind,s['physical'],s['bytes'],128)
    assert old.app_gp(blob)==old.GP
    out.mkdir();(out/'executed-source.py').write_bytes(Path(__file__).read_bytes());cases=[]
    try:
        for seed in (0xa5,0xc3):
            for flag in (0,0x10):cases.append(one(blob,seed,flag,False,metadata))
        cases.append(one(blob,0xa5,0x10,True,metadata))
    except Exception:
        im.write_json(out/'failed-attempt.json',{'traceback':traceback.format_exc(),'completed_cases':len(cases)})
        raise
    j={'status':'PASS_NATIVE_TYPE5_FRAME_ALLOCATION_THROUGH_ORIGINAL_CONSTRUCTION_WITH_EXPLICIT_IRQ_GAPS',
        'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'source_receipt':{'script_sha256':im.sha(Path(__file__).read_bytes()),'VCD_sha256':im.sha(blob),
            'prior_manifest_sha256':PRIOR_SHA,'stage91_result_sha256':im.sha(source.read_bytes())},
        'cases':cases,'bounded_phases':sum(len(c['events']) for c in cases),
        'scope':'Two ROM-defined native pools; original type5 caller constructs descriptor/slot, allocates, translates physical address, '
            'and executes frame constructor/header in one guest. Native type4 parameter buffer is referenced by declared metadata. '
            'Registration/cache/IRQ gaps, new reference and external dispatch remain unexecuted; no real MAIN, video or recovery.',
        'Windows_UU_camera_operations':False,'goal_complete':False,'persistent_write_release':False}
    im.write_json(out/'frame-allocation-results.json',j)
    print(json.dumps({'status':j['status'],'cases':len(cases),'bounded_phases':j['bounded_phases'],'output':str(out)}))


if __name__=='__main__':main()
