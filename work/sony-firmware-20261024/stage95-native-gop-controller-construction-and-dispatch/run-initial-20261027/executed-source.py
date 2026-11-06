#!/usr/bin/env python3
"""Native controller constructors, heap-origin and actual vtable dispatch.

Zero allocator callbacks are the original image's pre-binding state, NOT a
normal-runtime assumption. Original callback binding controls stop at the
native lock wrapper, before inventing any synchronization or return.
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
sys.path.insert(0,str(BASE/'stage94-native-frame-allocation-to-construction'))
import frame_allocation as prev
old=prev.old
im,u,reg,cs,IMAGE=prev.im,prev.u,prev.reg,prev.cs,prev.IMAGE
PRIOR_SHA='7ba9bbe1637028b1ca79aa81fc5d71501c8a4e151818661c94757c79cd111efd'
HEAP_PA,HEAP=0x05000000,0x85000000
HEAP_SIZE=0x10000
HEAP_HEAD,BEFORE_ALLOC,AFTER_ALLOC=0x248e94,0x248e98,0x248e9c
SP_HEAP,SP_OBJECT=old.STACK+0xb000,old.STACK+0xc000
KINDS={
    'base':{'entry':0x143e98,'vtable':0x242304,'slot38':0x1f87c0,'request':0},
    'ring524':{'entry':0x1451f4,'vtable':0x242264,'slot38':0x1464dc,'request':0x524},
    'ringC4':{'entry':0x1446f4,'vtable':0x2422b4,'slot38':0x1450fc,'request':0xc4}}
STOPS={**prev.STOPS,
    0xd4b8:'original_bound_allocator_lock_wrapper_before_unexecuted_RTOScall',
    0x1441fc:'base_noop_returned_before_original_frame_reference_release',
    0x134e6c:'native_owner_forwarder_before_unbound_trace_global_read',
    0x1465a4:'native_ring_receiver_before_unclassified_raw_geometry_and_pixel_payload'}
LIMITS=prev.LIMITS+((0x67d34,0x67d68),(0xd530,0xd550),(0x143e98,0x143ebc),
    (0x1451f4,0x1452a8),(0x1446f4,0x14475c),(0x69ca0,0x69cbc),(0x69d84,0x69dcc),
    (0x699bc,0x69aec),(0x69b24,0x69bb8),(0x1441e4,0x1441fc),
    (0x1f87c0,0x1f87c8),(0x1450fc,0x145118),(0x134e38,0x134e6c),(0x1464dc,0x1465a4))


class Guest(prev.Guest):
    def __init__(self,blob,seed,flag,metadata,kind,bind_callbacks):
        super().__init__(blob,seed,flag,metadata)
        self.kind=kind;self.spec=KINDS[kind];self.bind_callbacks=bind_callbacks
        self.image_words={HEAP_HEAD:0,BEFORE_ALLOC:0,AFTER_ALLOC:0}
        assert all(old.word(blob,k)==0 for k in self.image_words)
        self.uc.mem_map(HEAP_PA,HEAP_SIZE,u.UC_PROT_READ|u.UC_PROT_WRITE)
        heap=bytes([seed])*HEAP_SIZE
        self.uc.mem_write(HEAP_PA,heap);self.want[HEAP_PA]=bytearray(heap);self.sizes[HEAP_PA]=HEAP_SIZE
        self.uc.mem_protect(old.INSTANCE_PA,4096,u.UC_PROT_READ|u.UC_PROT_WRITE)
        self.uc.mem_map(old.INSTANCE_PA+4096,4096,u.UC_PROT_READ|u.UC_PROT_WRITE)
        tail=bytes([0x62])*4096;self.uc.mem_write(old.INSTANCE_PA+4096,tail)
        self.want[old.INSTANCE_PA].extend(tail);self.sizes[old.INSTANCE_PA]=8192

    def code(self,uc,pc,size,user):
        self.pcs.append(pc)
        if pc==old.TRAP:self.reason='returned_via_original_jr_ra';uc.emu_stop();return
        off=pc-IMAGE
        if off==self.spec['slot38']:
            self.dispatch_checkpoints.append({'point':'native_slot38_receiver_entry','target':hex(pc),
                **{n:hex(uc.reg_read(getattr(reg,'UC_MIPS_REG_'+n.upper()))) for n in ('a0','a1','a2','sp','ra')}})
        if off in self.stops:self.reason=self.stops[off];uc.emu_stop();return
        assert len(self.pcs)<30000
        assert any(lo<=off and off+size<=hi for lo,hi in LIMITS),(hex(pc),size)
        ins=next(self.md.disasm(self.blob[off:off+size],pc),None)
        assert ins is not None,(hex(pc),self.blob[off:off+size].hex())
        if ins.mnemonic=='break':assert off in (0x6057c,0x13489c)
        else:assert ins.mnemonic not in {'syscall','cache','sync','mfc0','mtc0','eret','wait','tlbwi','tlbwr','tlbr','tlbp'},(hex(pc),ins.mnemonic)
        if ins.mnemonic=='jalr':
            expected={0x5ef98:IMAGE+0x606d0,0x69adc:IMAGE+0xd4b8,0x1441e8:IMAGE+self.spec['slot38']}
            assert off in expected and uc.reg_read(reg.UC_MIPS_REG_V0)==expected[off],hex(pc)
        if off==0x66bb8:
            self.geometry_arguments.append({n:uc.reg_read(getattr(reg,'UC_MIPS_REG_'+n.upper())) for n in ('a0','a1','a2')})
        if off==0x1f8550:
            address=uc.reg_read(reg.UC_MIPS_REG_A0);assert address==prev.FRAME
            self.frame_checkpoints.append({'point':'original_constructor_entry','A0':hex(address)})
        if off==0x144124:
            raw=bytes(uc.mem_read(prev.PHYS5,0x4f0));assert raw==self.constructor_expected
            self.frame_checkpoints.append({'point':'constructor_return_to_original_parent',
                'frame_VA':hex(prev.FRAME),'frame_sha256':im.sha(raw),'parameter_handle':old.word(raw,0x4c8),'update_flag':raw[0x4c4]})

    def run(self,label,entry,sp=prev.prev.prev.SP_SEL,preserve=False,remove_stops=(),**regs):
        initial={} if preserve else {'sp':sp,'ra':old.TRAP,'gp':old.GP,'fp':0,**{f's{i}':0 for i in range(8)}}
        for name,value in {**initial,**regs}.items():self.uc.reg_write(getattr(reg,'UC_MIPS_REG_'+name.upper()),value)
        self.reason=None;self.pcs=[];self.interrupts=[];self.geometry_arguments=[];self.frame_checkpoints=[];self.dispatch_checkpoints=[]
        self.stops=dict(STOPS)
        for off in remove_stops:self.stops.pop(off)
        self.uc.emu_start(IMAGE+entry,0,timeout=2000000,count=0)
        assert self.reason in set(self.stops.values())|{'returned_via_original_jr_ra'} and not self.interrupts,self.reason
        expected_image=bytearray(self.blob)
        for at,value in {prev.CELL:self.cell,**self.image_words}.items():struct.pack_into('<I',expected_image,at,value)
        assert bytes(self.uc.mem_read(0,len(self.blob)))==bytes(expected_image)
        assert bytes(self.uc.mem_read(old.STACK_PA,65536))==self.stack
        for at,raw in self.want.items():assert self.read(at)==bytes(raw),hex(at)
        assert bytes(self.uc.mem_read(old.TRAP_PA,4096))==bytes(4096)
        return {'label':label,'entry':hex(IMAGE+entry),'stop':self.reason,
            **{n.upper():hex(self.uc.reg_read(getattr(reg,'UC_MIPS_REG_'+n.upper()))) for n in ('pc','sp','ra','v0')},
            'CODE_observed_PCs':[hex(x) for x in self.pcs],
            'native_geometry_helper_arguments':self.geometry_arguments,'frame_checkpoints':self.frame_checkpoints,
            'dispatch_checkpoints':self.dispatch_checkpoints,
            'all_regions_and_entire_stack_exact_poststate_checked':True,
            'image_unchanged_except_native_registry_and_heap_globals':True,
            'memory_read_write_hooks_installed':False,'native_interrupts':self.interrupts,
            'PC_observation_may_include_annulled_delay_slots':True,'MMIO_instruction_patch_or_fake_return':False}

    def heap_init(self):
        self.image_words[HEAP_HEAD]=HEAP
        struct.pack_into('<III',self.want[HEAP_PA],0,HEAP_SIZE-0x10|1,0,0)
        e=self.run('complete original heap initializer with declared aligned arena',0x67d34,sp=SP_HEAP,a0=HEAP,a1=HEAP_SIZE-0x10)
        assert e['stop']=='returned_via_original_jr_ra'
        return e

    def callback_binding(self):
        self.image_words[BEFORE_ALLOC]=IMAGE+0xd4b8;self.image_words[AFTER_ALLOC]=IMAGE+0xd4d8
        e=self.run('complete original allocator callback binding, not host callback injection',0xd530,sp=SP_HEAP)
        assert e['stop']=='returned_via_original_jr_ra'
        return e

    def expected_constructor_stack(self):
        if self.kind=='base':return
        sp=SP_OBJECT-0x20
        if self.kind=='ring524':
            self.save(sp+0x18,old.TRAP);self.save(sp+0x14,0);self.save(sp+0x10,0)
            original_return=IMAGE+0x145220;s0,s1=0,old.INSTANCE
        else:
            self.save(sp+0x14,old.TRAP);self.save(sp+0x10,0)
            original_return=IMAGE+0x14471c;s0,s1=old.INSTANCE,0
        self.save(sp-0x20+0x10,original_return)
        self.save(sp-0x40+0x10,s0);self.save(sp-0x40+0x14,IMAGE+0x69cb0)
        self.save(sp-0x60+0x10,s0);self.save(sp-0x60+0x14,s1);self.save(sp-0x60+0x18,IMAGE+0x69d9c)
        if not self.bind_callbacks:
            inner=sp-0x80
            self.save(inner+0x10,HEAP);self.save(inner+0x14,self.spec['request']);self.save(inner+0x18,IMAGE+0x69ad4)

    def expected_heap_allocate(self):
        heap=self.want[HEAP_PA];n=(self.spec['request']+15)&-16
        next_head=HEAP+n+0x10
        struct.pack_into('<I',heap,0,n);struct.pack_into('<I',heap,8,next_head)
        struct.pack_into('<III',heap,n+0x10,(HEAP_SIZE-0x20-n)|1,HEAP,0)
        return HEAP+0x10

    def construct_controller(self):
        o=self.want[old.INSTANCE_PA];source=self.want[old.SRC_PA]
        struct.pack_into('<III',o,0,IMAGE+self.spec['vtable'],old.OWNER,0)
        struct.pack_into('<H',o,0xc,struct.unpack_from('<H',source,2)[0]);struct.pack_into('<I',o,0x10,0)
        self.expected_constructor_stack()
        if self.kind!='base' and not self.bind_callbacks:
            h=self.expected_heap_allocate();struct.pack_into('<I',o,0x14,h);heap=self.want[HEAP_PA]
            def store(at,value):struct.pack_into('<I',heap,h-HEAP+at,value)
            if self.kind=='ring524':
                for at,value in ((0x3c8,0),(0x3cc,0),(0x3c0,h),(0x3c4,h),
                                 (0x51c,0),(0x518,0),(0x510,h+0x3d0),(0x514,h+0x3d0)):store(at,value)
                heap[h-HEAP+0x520]=0
                for at,value in ((0x858,0),(0x84c,old.INSTANCE+0x18),(0x1aec,0),(0x850,old.INSTANCE+0x18),
                                 (0x1c28,0),(0x1ae0,old.INSTANCE+0x85c),(0x854,0),(0x1ae4,old.INSTANCE+0x85c),
                                 (0x1ae8,0),(0x1c1c,old.INSTANCE+0x1af0),(0x1c20,old.INSTANCE+0x1af0),(0x1c24,0)):
                    struct.pack_into('<I',o,at,value)
            else:
                for at,value in ((0x78,h),(0x7c,h),(0x80,0),(0x84,0),(0xb0,h+0x88),
                                 (0xbc,0),(0xb4,h+0x88),(0xb8,0)):store(at,value)
                heap[h-HEAP+0xc0]=0
        e=self.run('original '+self.kind+' constructor '+('with native lock callbacks bound' if self.bind_callbacks else 'in original pre-callback single-context state'),
            self.spec['entry'],sp=SP_OBJECT,a0=old.INSTANCE,a1=old.SRC,a2=old.OWNER,a3=0)
        assert e['stop']==(STOPS[0xd4b8] if self.bind_callbacks else 'returned_via_original_jr_ra')
        if not self.bind_callbacks:assert e['SP']==hex(SP_OBJECT)
        return e

    def dispatch(self):
        if self.kind=='base':pass
        elif self.kind=='ringC4':
            self.save(prev.BODY_SP-0x10,IMAGE+0x1441f0)
            base=prev.BODY_SP-0x50
            for off,value in ((0x28,old.INSTANCE),(0x24,old.SRC),(0x20,0),(0x2c,IMAGE+0x14510c)):self.save(base+off,value)
        else:
            base=prev.BODY_SP-0x1c0
            for off,value in ((0x1b4,0),(0x1b0,prev.BODY_SP+0x20),(0x1ac,0),(0x1b8,IMAGE+0x1441f0),
                              (0x1a8,old.INSTANCE),(0x1a4,old.SRC),(0x1a0,0),(0x20,old.GP-0x6184)):
                self.save(base+off,value)
        e=self.run('original parent slot38 dispatch through natively installed vtable',0x1441e4,preserve=True,remove_stops=(0x1441e4,))
        stop={'base':0x1441fc,'ringC4':0x134e6c,'ring524':0x1465a4}[self.kind]
        assert e['stop']==STOPS[stop] and len(e['dispatch_checkpoints'])==1
        cp=e['dispatch_checkpoints'][0]
        assert cp['a0']==hex(old.INSTANCE) and cp['a1']==hex(prev.BODY_SP+0x10) and cp['a2']==hex(old.SRC)
        assert cp['sp']==hex(prev.BODY_SP) and cp['ra']==hex(IMAGE+0x1441f0)
        return e


def one(blob,metadata,seed,kind,flag,callbacks):
    m=Guest(blob,seed,flag,metadata,kind,callbacks);es=m.setup_pools();es.append(m.allocate_source())
    es.append(m.defaults());e,_=m.classify_and_build((120,68),1);es.append(e);es.append(m.prepare_geometry((120,68)))
    es.append(m.heap_init())
    if callbacks:es.append(m.callback_binding())
    es.append(m.construct_controller());frame=None
    if not callbacks:
        more,handle=m.parent_allocate();assert handle==prev.H5;es+=more
        e,frame=m.finish_parent(flag,handle);es.append(e)
        if not flag:es.append(m.dispatch())
    return {'seed':seed,'controller_kind':kind,'declared_update_byte50':flag,'native_callbacks_bound':callbacks,
        'native_vtable_VA':hex(IMAGE+m.spec['vtable']),'native_slot38_target':hex(IMAGE+m.spec['slot38']),
        'controller_constructor_completed':not callbacks,
        'private_heap_buffer_VA':hex(HEAP+0x10) if kind!='base' and not callbacks else None,
        'private_heap_request_bytes':m.spec['request'],'private_heap_allocation_completed':kind!='base' and not callbacks,
        'actual_slot38_dispatch_executed':not callbacks and not flag,
        'new_parameter_reference_completed':False,
        'image_words':{hex(k):hex(v) for k,v in {prev.CELL:m.cell,**m.image_words}.items()},
        'final_regions':{hex(at):bytes(raw).hex() for at,raw in m.want.items()},
        'frame_after_hex':frame.hex() if frame else None,'events':es,
        'raw_metadata_owner_history_heap_arena_and_callback_A3_are_declared':True,
        'zero_callbacks_are_pre_binding_image_state_not_normal_runtime':not callbacks,
        'actual_RTOS_locks_MAIN_HEVC_video_audio_or_recovery_proven':False}


def main():
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);out=Path(p.parse_args().output)
    im.volume();assert not out.exists()
    prior=BASE/'stage94-native-frame-allocation-to-construction/final-receipt.json'
    assert im.sha(prior.read_bytes())==PRIOR_SHA
    for f in json.loads(prior.read_text())['files']:
        raw=(ROOT/f['path']).read_bytes();assert len(raw)==f['bytes'] and im.sha(raw)==f['sha256']
    assert (STAGE/'goal-status-before.json').read_bytes()==(BASE/'GOAL_STATUS.json').read_bytes()
    previous_result=prior.parent/'run-initial-20261027/frame-allocation-results.json'
    source=json.loads(previous_result.read_text())['cases'][0]
    pool=bytes.fromhex(source['final_regions'][hex(prev.POOL_PA)])
    at=prev.PHYS4-prev.POOL_PA+0xec;metadata=pool[at:at+48]
    assert struct.unpack_from('<HH',metadata)==(119,67)
    path=BASE/'stage2/extraction/files/nflasha15/codec/vcd_firmware_imola2.bin';blob=path.read_bytes()
    assert im.sha(blob)==im.PINS[str(path.relative_to(BASE))]
    for k,spec in KINDS.items():
        assert old.word(blob,spec['vtable']+0x10)==IMAGE+0x143f98
        assert old.word(blob,spec['vtable']+0x38)==IMAGE+spec['slot38']
    out.mkdir();(out/'executed-source.py').write_bytes(Path(__file__).read_bytes());cases=[]
    try:
        for seed in (0xa5,0xc3):
            cases.append(one(blob,metadata,seed,'base',0,False))
            for kind in ('ring524','ringC4'):
                for flag in (0,0x10):cases.append(one(blob,metadata,seed,kind,flag,False))
                cases.append(one(blob,metadata,seed,kind,0,True))
    except Exception:
        im.write_json(out/'failed-attempt.json',{'traceback':traceback.format_exc(),'completed_cases':len(cases)})
        raise
    j={'status':'PASS_NATIVE_CONTROLLER_HEAP_CONSTRUCTION_AND_CLASS_SPECIFIC_DISPATCH_WITH_RUNTIME_CALLBACK_STOP',
        'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'source_receipt':{'script_sha256':im.sha(Path(__file__).read_bytes()),'VCD_sha256':im.sha(blob),
            'prior_manifest_sha256':PRIOR_SHA,'stage94_result_sha256':im.sha(previous_result.read_bytes())},
        'cases':cases,'bounded_phases':sum(len(c['events']) for c in cases),
        'scope':'Original heap init and complete three controller constructors in pre-callback state; derived runtime callback binding controls stop before actual RTOS lock. '
            'Original allocated frame reaches correct slot38 through constructor-written vtable with update off; update on stops before reference sharing. '
            'No complete runtime construction, source production, IRQ, MAIN encoding or recovery.',
        'Windows_UU_camera_operations':False,'goal_complete':False,'persistent_write_release':False}
    im.write_json(out/'controller-dispatch-results.json',j)
    print(json.dumps({'status':j['status'],'cases':len(cases),'bounded_phases':j['bounded_phases'],'output':str(out)}))


if __name__=='__main__':main()
