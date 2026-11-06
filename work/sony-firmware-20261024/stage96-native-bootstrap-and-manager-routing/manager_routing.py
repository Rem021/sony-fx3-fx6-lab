#!/usr/bin/env python3
"""Original bootstrap prefix, two native allocations/classes and manager routing.

Factory suffix is pre-lock-binding only. Selection callbacks are NOT completed;
subsequent frame-event entry tests independent data routing, not valid scheduling.
"""
from pathlib import Path
import argparse,datetime,json,struct,sys,traceback
STAGE=Path(__file__).resolve().parent
BASE,ROOT=STAGE.parent,STAGE.parent.parents[1]
sys.path.insert(0,str(BASE/'stage95-native-gop-controller-construction-and-dispatch'))
import controller_dispatch as prev
old=prev.old
im,u,reg,cs,IMAGE=prev.im,prev.u,prev.reg,prev.cs,prev.IMAGE
PRIOR_SHA='57f0fc88da75fc18e4519e8b6d305b3d3bd482fcac39b3a73e357f76f8db8bbd'
MGR_PA,MGR=0x06000000,0x86000000
MSG_PA,MSG=0x06100000,0x86100000
FRAME_MSG_PA,FRAME_MSG=0x06200000,0x86200000
SP_FACTORY,SP_SELECT,SP_EVENT,SP_BOOT=[old.STACK+x for x in (0x8000,0xa000,0xe000,0x2000)]
STOPS={0x7a35c:'original_factory_suffix_bound_both_objects_before_remaining_parent_validation',
    0xd4b8:'native_bound_allocator_lock_wrapper_before_unexecuted_RTOS',
    0x7af58:'original_selector1_stored_current_object_before_unexecuted_mode_callback',
    0x7b74c:'original_selector2_stored_current_object_before_unexecuted_mode_callback',
    0x1a9a84:'message_length_mismatch_before_unexecuted_diagnostic',
    0x143fc0:'manager_selected_frame_handler_reached_original_parent_before_GP_lock_ID',
    0x61f3c:'original_boot_table_second_callback_before_unexecuted_component_initializer'}
LIMITS=((0x67d34,0x67d68),(0xd530,0xd550),(0x699bc,0x69aec),(0x69b24,0x69bb8),
    (0x69ca0,0x69cbc),(0x69d84,0x69dcc),(0x7a304,0x7a35c),(0x143e98,0x143ebc),
    (0x1447a8,0x144820),(0x145300,0x1453b0),(0x1f8a1c,0x1f8a38),(0x1f8a64,0x1f8a80),
    (0x7aed4,0x7af58),(0x7b6cc,0x7b74c),(0x7b08c,0x7b104),(0x143f98,0x143fc0),
    (0x5c49c,0x5c4a4),(0x5c784,0x5c7d8),(0xa054,0xa05c))


class Guest(prev.Guest):
    def __init__(self,blob,metadata,seed,selector=1,value=0,valid=True,bound=False):
        super().__init__(blob,seed,0,metadata,'base',bound)
        self.selector,self.value,self.valid=selector,value,valid
        self.heap_head=prev.HEAP;self.allocations=[];self.objects=None
        for pa in (MGR_PA,MSG_PA,FRAME_MSG_PA):
            self.uc.mem_map(pa,4096,u.UC_PROT_READ|u.UC_PROT_WRITE)
            raw=bytearray([seed])*4096
            if pa==MGR_PA:struct.pack_into('<I',raw,8,old.SRC);struct.pack_into('<II',raw,0x10,old.OWNER,0)
            elif pa==MSG_PA:
                struct.pack_into('<H',raw,6,(0x70 if selector==1 else 0xe0)+(0 if valid else -1))
                raw[0x23 if selector==1 else 0x36]=value
            else:
                struct.pack_into('<H',raw,6,0x8c);raw[8:8+0x8c]=self.want[old.SRC_PA][:0x8c]
            self.uc.mem_write(pa,bytes(raw));self.want[pa]=raw;self.sizes[pa]=4096

    def code(self,uc,pc,size,user):
        self.pcs.append(pc)
        if pc==old.TRAP:self.reason='returned_via_original_jr_ra';uc.emu_stop();return
        off=pc-IMAGE
        if off==0x143f98:
            self.entries.append({'point':'original_frame_parent_entry',
                **{n:hex(uc.reg_read(getattr(reg,'UC_MIPS_REG_'+n.upper()))) for n in ('a0','a1','sp','ra')}})
        if off in STOPS:self.reason=STOPS[off];uc.emu_stop();return
        assert len(self.pcs)<20000 and any(lo<=off and off+size<=hi for lo,hi in LIMITS),(hex(pc),size)
        ins=next(self.md.disasm(self.blob[off:off+size],pc),None);assert ins is not None,hex(pc)
        assert ins.mnemonic not in {'break','syscall','cache','sync','mfc0','mtc0','eret','wait','tlbwi','tlbwr','tlbr','tlbp'},(hex(pc),ins.mnemonic)
        if ins.mnemonic=='jalr':
            target=uc.reg_read(reg.UC_MIPS_REG_V0)
            allowed={0x69adc:{IMAGE+0xd4b8},0x7b0fc:{IMAGE+0x143f98},0x5c7c8:{IMAGE+0xa054,IMAGE+0x61f3c}}
            assert off in allowed and target in allowed[off],(hex(pc),hex(target))
            self.indirect.append({'call_PC':hex(pc),'target':hex(target),
                'A0':hex(uc.reg_read(reg.UC_MIPS_REG_A0)),'S1':hex(uc.reg_read(reg.UC_MIPS_REG_S1))})

    def run(self,label,entry,sp=SP_FACTORY,preserve=False,**regs):
        initial={} if preserve else {'sp':sp,'ra':old.TRAP,'gp':old.GP,'fp':0,**{f's{i}':0 for i in range(8)}}
        for name,value in {**initial,**regs}.items():self.uc.reg_write(getattr(reg,'UC_MIPS_REG_'+name.upper()),value)
        self.reason=None;self.pcs=[];self.interrupts=[];self.indirect=[];self.entries=[]
        self.uc.emu_start(IMAGE+entry,0,timeout=2000000,count=0)
        assert self.reason in set(STOPS.values())|{'returned_via_original_jr_ra'} and not self.interrupts,self.reason
        image=bytearray(self.blob)
        for at,value in {prev.prev.CELL:self.cell,**self.image_words}.items():struct.pack_into('<I',image,at,value)
        assert bytes(self.uc.mem_read(0,len(self.blob)))==bytes(image)
        assert bytes(self.uc.mem_read(old.STACK_PA,65536))==self.stack
        for at,raw in self.want.items():assert self.read(at)==bytes(raw),hex(at)
        assert bytes(self.uc.mem_read(old.TRAP_PA,4096))==bytes(4096)
        return {'label':label,'entry':hex(IMAGE+entry),'stop':self.reason,
            **{n.upper():hex(self.uc.reg_read(getattr(reg,'UC_MIPS_REG_'+n.upper()))) for n in ('pc','sp','ra','v0','s0','s1')},
            'CODE_observed_PCs':[hex(p) for p in self.pcs],'indirect_calls':self.indirect,'native_entries':self.entries,
            'image_all_regions_and_entire_stack_exact_poststate_checked':True,
            'memory_read_write_hooks_installed':False,'native_interrupts':self.interrupts,
            'PC_observation_may_include_annulled_delay_slots':True,'MMIO_instruction_patch_or_fake_return':False}

    def allocate_expected(self,n,sp,return_pc,s0,s1):
        head=self.heap_head
        for off,value in ((-0x10,return_pc),(-0x30,s0),(-0x2c,IMAGE+0x69cb0),
                          (-0x50,s0),(-0x4c,s1),(-0x48,IMAGE+0x69d9c)):
            self.save(sp+off,value)
        if self.bind_callbacks:return None
        for off,value in ((-0x70,head),(-0x6c,n),(-0x68,IMAGE+0x69ad4)):self.save(sp+off,value)
        h=self.want[prev.HEAP_PA];at=head-prev.HEAP;available=old.word(h,at)&~1
        aligned=(n+15)&-16;new=head+aligned+0x10
        struct.pack_into('<I',h,at,aligned);struct.pack_into('<I',h,at+8,new)
        struct.pack_into('<III',h,new-prev.HEAP,(available-aligned-0x10)|1,head,0)
        self.heap_head=new;ptr=head+0x10
        self.allocations.append({'request':n,'aligned':aligned,'header':hex(head),'result':hex(ptr)})
        return ptr

    def initialize_object_expected(self,obj,private,kind):
        h=self.want[prev.HEAP_PA];at=obj-prev.HEAP
        struct.pack_into('<III',h,at,IMAGE+(0x2422b4 if kind=='ringC4' else 0x242264),old.OWNER,0)
        struct.pack_into('<H',h,at+0xc,struct.unpack_from('<H',self.want[old.SRC_PA],2)[0])
        struct.pack_into('<II',h,at+0x10,0,private)
        if kind=='ringC4':
            fields={0x78:private,0x7c:private,0x80:0,0x84:0,0xb0:private+0x88,0xbc:0,0xb4:private+0x88,0xb8:0};byte=0xc0
        else:
            fields={0x3c8:0,0x3cc:0,0x3c0:private,0x3c4:private,0x51c:0,0x518:0,0x510:private+0x3d0,0x514:private+0x3d0};byte=0x520
            for off,value in {0x858:0,0x84c:obj+0x18,0x1aec:0,0x850:obj+0x18,0x1c28:0,
                0x1ae0:obj+0x85c,0x854:0,0x1ae4:obj+0x85c,0x1ae8:0,0x1c1c:obj+0x1af0,0x1c20:obj+0x1af0,0x1c24:0}.items():
                struct.pack_into('<I',h,at+off,value)
        for off,value in fields.items():struct.pack_into('<I',h,private-prev.HEAP+off,value)
        h[private-prev.HEAP+byte]=0

    def factory_suffix(self):
        c4=self.allocate_expected(0x18,SP_FACTORY,IMAGE+0x7a30c,0,old.SRC)
        if not self.bind_callbacks:
            child=SP_FACTORY-0x20
            self.save(child+0x14,IMAGE+0x7a324);self.save(child+0x10,0)
            pc4=self.allocate_expected(0xc4,child,IMAGE+0x1447d0,c4,c4)
            self.save(child-0x10,IMAGE+0x144804)
            self.initialize_object_expected(c4,pc4,'ringC4')
            struct.pack_into('<I',self.want[MGR_PA],0x18,c4)
            c524=self.allocate_expected(0x1c2c,SP_FACTORY,IMAGE+0x7a334,0,c4)
            self.save(child+0x14,IMAGE+0x7a34c);self.save(child+0x10,c524)
            p524=self.allocate_expected(0x524,child,IMAGE+0x145328,c524,c4)
            self.save(child-0x10,IMAGE+0x14535c)
            self.initialize_object_expected(c524,p524,'ring524')
            struct.pack_into('<II',self.want[MGR_PA],0x1c,c524,c4);self.objects={'ringC4':c4,'ring524':c524}
        e=self.run('original manager factory suffix allocates both objects and private buffers',0x7a304,
            s0=0,s1=old.SRC,s2=MGR,s3=0,s4=old.OWNER)
        assert e['stop']==STOPS[0xd4b8 if self.bind_callbacks else 0x7a35c]
        return e

    def select(self):
        base=SP_SELECT-0x50
        for off,value in ((0x44,0),(0x40,0),(0x48,old.TRAP)):self.save(base+off,value)
        if not self.valid:
            self.save(base+0x10,0);self.save(base+0x14,0)
        else:
            use_large=self.value==1 if self.selector==1 else self.value!=0
            selected=self.objects['ring524' if use_large else 'ringC4']
            struct.pack_into('<I',self.want[MGR_PA],0x20,selected)
        e=self.run('original length-checked selector '+str(self.selector),0x7aed4 if self.selector==1 else 0x7b6cc,
            sp=SP_SELECT,a0=MGR,a1=MSG)
        stop=0x1a9a84 if not self.valid else 0x7af58 if self.selector==1 else 0x7b74c
        assert e['stop']==STOPS[stop]
        return e

    def frame_routing(self):
        base=SP_EVENT-0x70
        for off,value in ((0x58,0),(0x54,0),(0x50,0),(0x60,old.TRAP),(0x5c,0)):self.save(base+off,value)
        body=base-0x60
        for off,value in ((0x50,0),(0x48,FRAME_MSG),(0x44,FRAME_MSG+8),(0x54,IMAGE+0x7b104),(0x4c,0),(0x40,0x8c)):
            self.save(body+off,value)
        e=self.run('independent original frame-message routing through current manager pointer',0x7b08c,
            sp=SP_EVENT,a0=MGR,a1=FRAME_MSG)
        assert e['stop']==STOPS[0x143fc0] and len(e['native_entries'])==1
        assert e['native_entries'][0]['a0']==hex(old.word(self.want[MGR_PA],0x20))
        assert e['native_entries'][0]['a1']==hex(FRAME_MSG+8)
        return e

    def boot_prefix(self):
        base=SP_BOOT-0x20
        for off,value in ((0x18,IMAGE+0x5c4a4),(0x14,0),(0x10,0)):self.save(base+off,value)
        e=self.run('original RTOS initialization caller and original table iterator prefix',0x5c49c,sp=SP_BOOT)
        assert e['stop']==STOPS[0x61f3c]
        assert [x['target'] for x in e['indirect_calls']]==[hex(IMAGE+0xa054),hex(IMAGE+0x61f3c)]
        return e


def one(blob,metadata,seed,kind,selector=1,value=0,valid=True):
    m=Guest(blob,metadata,seed,selector,value,valid,kind=='bound_factory');es=[]
    if kind=='boot_prefix':es.append(m.boot_prefix())
    else:
        es.append(m.heap_init())
        if kind=='bound_factory':es.append(m.callback_binding())
        es.append(m.factory_suffix())
        if kind=='routing':
            es.append(m.select())
            if valid:es.append(m.frame_routing())
    return {'seed':seed,'kind':kind,'selector':selector,'declared_selector_byte':value,'valid_message_length':valid,
        'objects':{k:hex(v) for k,v in (m.objects or {}).items()},'native_allocations':m.allocations,
        'current_manager_pointer':hex(old.word(m.want[MGR_PA],0x20)),
        'heap_callbacks_bound':m.bind_callbacks,'image_words':{hex(k):hex(v) for k,v in {prev.prev.CELL:m.cell,**m.image_words}.items()},
        'final_regions':{hex(at):bytes(raw).hex() for at,raw in m.want.items()},'events':es,
        'factory_prefix_owner_callback_config_and_heap_arena_declared':True,
        'mode_callback_completion_and_valid_scheduling_order_proven':False,
        'frame_routing_is_independent_declared_entry_not_mode_transition_completion':True,
        'actual_MAIN_HEVC_hardware_RTOS_boot_or_recovery_proven':False}


def main():
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);out=Path(p.parse_args().output)
    im.volume();assert not out.exists()
    prior=BASE/'stage95-native-gop-controller-construction-and-dispatch/final-receipt.json'
    assert im.sha(prior.read_bytes())==PRIOR_SHA
    for f in json.loads(prior.read_text())['files']:
        raw=(ROOT/f['path']).read_bytes();assert len(raw)==f['bytes'] and im.sha(raw)==f['sha256']
    assert (STAGE/'goal-status-before.json').read_bytes()==(BASE/'GOAL_STATUS.json').read_bytes()
    source=prior.parent/'run-corrected-geometry-argument-20261027/controller-dispatch-results.json'
    case=json.loads(source.read_text())['cases'][0];pool=bytes.fromhex(case['final_regions'][hex(prev.prev.POOL_PA)])
    at=prev.prev.PHYS4-prev.prev.POOL_PA+0xec;metadata=pool[at:at+48]
    path=BASE/'stage2/extraction/files/nflasha15/codec/vcd_firmware_imola2.bin';blob=path.read_bytes()
    assert im.sha(blob)==im.PINS[str(path.relative_to(BASE))]
    out.mkdir();(out/'executed-source.py').write_bytes(Path(__file__).read_bytes());cases=[]
    try:
        for seed in (0xa5,0xc3):
            cases.append(one(blob,metadata,seed,'boot_prefix'))
            for selector,values in ((1,(0,1,2)),(2,(0,1,255))):
                for value in values:cases.append(one(blob,metadata,seed,'routing',selector,value))
            cases.append(one(blob,metadata,seed,'bound_factory'))
        for selector in (1,2):cases.append(one(blob,metadata,0xa5,'routing',selector,1,False))
    except Exception:
        im.write_json(out/'failed-attempt.json',{'traceback':traceback.format_exc(),'completed_cases':len(cases)})
        raise
    j={'status':'PASS_NATIVE_BOOT_ITERATOR_PREFIX_FACTORY_SUFFIX_SELECTORS_AND_FRAME_ROUTING_WITH_EXPLICIT_GAPS',
        'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'source_receipt':{'script_sha256':im.sha(Path(__file__).read_bytes()),'VCD_sha256':im.sha(blob),
            'prior_manifest_sha256':PRIOR_SHA,'stage95_result_sha256':im.sha(source.read_bytes())},
        'cases':cases,'bounded_phases':sum(len(c['events']) for c in cases),
        'Windows_UU_camera_operations':False,'goal_complete':False,'persistent_write_release':False}
    im.write_json(out/'manager-routing-results.json',j)
    print(json.dumps({'status':j['status'],'cases':len(cases),'bounded_phases':j['bounded_phases'],'output':str(out)}))


if __name__=='__main__':main()
