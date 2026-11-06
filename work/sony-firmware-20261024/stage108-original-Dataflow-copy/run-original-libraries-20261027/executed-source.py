#!/usr/bin/env python3
"""Bounded original Dataflow messages and receiver pointer use; no device I/O.

Two same-firmware libc imports bind to their original A64 functions in a guest
address space. This is an explicit binding fixture, not Sony's dynamic loader.
Separate AV guest experiments receive bytes, not transport/process authority.
"""
from pathlib import Path
import argparse
import datetime
import hashlib
import json
import struct
import sys
import traceback

STAGE=Path(__file__).resolve().parent
BASE=STAGE.parent
ROOT=BASE.parents[1]
sys.path.insert(0,str(BASE/'stage106-native-MPR-Open-fields'))
import mpr_open as prev
sys.path.insert(0,str(BASE/'stage23-encoder-boundary'))
import encoder_boundary as assets
pp,r,im=prev.pp,prev.r,prev.im
SP=prev.SP
PRIOR=BASE/'stage107-native-fixed-message-area/final-receipt.json'
PRIOR_SHA='a30d39b6f5d6f43700de1de54bd852881fcfa93d56ddf9b5e6da72d5b8e7dbf3'
DF_SHA='5d6a9be3ba359cffb1a1894bb667071e0f0e2fe2749b6c5e36ce8364e57eae2a'
LIBC_SHA='f9104526eb7e5d2ea533c1a209bb0b83e69367f569e4c966895c8e106e6382c9'
DF=assets.PinnedNative(STAGE/'inputs/dataflowInfraFramework.so',DF_SHA)
LIBC=assets.PinnedNative(STAGE/'inputs/libc-2.25.so',LIBC_SHA)
AV=assets.AV
CBASE=0x20000000
OBJ=pp.SCRATCH+0x100
SOURCE=pp.SCRATCH+0x800
SRCID_OUT=pp.SCRATCH+0x900
VBASE=pp.SCRATCH+0x2000
SELF=pp.SCRATCH+0x5000
PCONTROL=pp.SCRATCH+0x6000
VTABLE=pp.SCRATCH+0x6100
CMD=pp.SCRATCH+0x8000
LIBC_IMPORTS={0x30460:'memcpy',0x30760:'memset'}


def sha(d):return hashlib.sha256(d).hexdigest()


def reg(name):return getattr(r.reg,'UC_ARM64_REG_'+name.upper())


class Guest(pp.StrictMicro):
    def __init__(self,native,seed,ranges):
        super().__init__(native,ranges,resolve=True)
        self.uc.mem_write(pp.STACK_BASE,bytes([seed])*pp.STACK_SIZE)
        self.uc.mem_write(pp.SCRATCH,bytes([seed^0x3c])*0x10000)
        for i in range(19,30):self.uc.reg_write(reg('x'+str(i)),0x38000000+seed*0x1000+i*0x10)
        for i in range(8,16):self.uc.reg_write(reg('d'+str(i)),0x1234567800000000+seed*256+i)
        self.images=[]
        self.boundaries={}
        self.reads=[]
        self.hooks.append(self.uc.hook_add(r.unicorn.UC_HOOK_MEM_READ,self.observe))
        if native is DF:
            self.boundaries[0x3109c]='unexecuted_logging_backend'
            pages=set()
            for s in LIBC.segments:
                pages.update(range((CBASE+s['p_vaddr'])&~4095,(CBASE+s['p_vaddr']+s['p_memsz']+4095)&~4095,4096))
            runs=[]
            for a in sorted(pages):
                if runs and runs[-1][1]==a:runs[-1][1]=a+4096
                else:runs.append([a,a+4096])
            for a,z in runs:self.uc.mem_map(a,z-a)
            for s in LIBC.segments:self.uc.mem_write(CBASE+s['p_vaddr'],s.data())
            for a,z in runs:self.uc.mem_protect(a,z-a,r.unicorn.UC_PROT_READ|r.unicorn.UC_PROT_EXEC)
            for name in LIBC_IMPORTS.values():
                sym=LIBC.symbols[name];self.allowed.append((CBASE+sym['va'],CBASE+sym['va']+sym['size']))
            self.images.extend((CBASE+s['p_vaddr'],bytes(self.uc.mem_read(CBASE+s['p_vaddr'],s['p_memsz']))) for s in LIBC.segments)
        else:
            self.boundaries.update({0x138f00:'after_original_receive_prefix',
                0xb2998:'before_first_unbound_ParameterControl_vcall',
                0xb29d8:'before_second_unbound_ParameterControl_vcall'})
        self.images.extend((s['p_vaddr'],bytes(self.uc.mem_read(s['p_vaddr'],s['p_memsz']))) for s in native.segments)

    def observe(self,u,access,at,n,value,user):
        if VBASE<=at and at+n<=VBASE+0x98:
            self.reads.append({'pc':hex(u.reg_read(reg('pc'))),'raw98_offset':hex(at-VBASE),
                'size':n,'bytes':bytes(u.mem_read(at,n)).hex()})

    def code(self,u,pc,n,user):
        if pc in self.boundaries:
            self.pcs.append(hex(pc));self.abort('boundary: '+self.boundaries[pc]);return
        if self.n is DF and pc in LIBC_IMPORTS:
            name=LIBC_IMPORTS[pc];assert DF.plt[pc]==name
            target=CBASE+LIBC.symbols[name]['va']
            self.pcs.append(hex(pc));self.steps+=1
            self.calls.append({'same_firmware_original_import':name,'PLT':hex(pc),'guest_target':hex(target),
                'original_libc_symbol_VA':hex(LIBC.symbols[name]['va']),
                'args_x0_x2':[hex(u.reg_read(reg('x'+str(i)))) for i in range(3)],
                'PC_binding_only_no_return_or_output_adapter':True})
            u.reg_write(reg('pc'),target);return
        return super().code(u,pc,n,user)

    def phase(self,label,entry,outputs=(),complete=True,**regs):
        before_stack=bytes(self.uc.mem_read(pp.STACK_BASE,pp.STACK_SIZE))
        before_scratch=bytes(self.uc.mem_read(pp.SCRATCH,0x10000))
        for name,value in regs.items():self.uc.reg_write(reg(name),value)
        saved={name:self.uc.reg_read(reg(name)) for name in
            ['x'+str(i) for i in range(19,30)]+['d'+str(i) for i in range(8,16)]}
        self.reason=None;self.steps=0;self.pcs=[];self.calls=[];self.stores=[];self.writes=[];self.reads=[]
        self.uc.emu_start(entry,0,count=5000,timeout=1000000)
        assert self.reason is not None,'instruction/time limit without observed boundary'
        assert self.reason=='returned' if complete else self.reason.startswith('boundary: '),self.reason
        if complete:
            assert self.uc.reg_read(reg('sp'))==SP
            assert all(self.uc.reg_read(reg(name))==value for name,value in saved.items()),'callee-saved ABI'
        for w in self.stores:
            a,n=int(w['address'],16),w['size']
            assert SP-0x200<=a and a+n<=SP or any(x<=a and a+n<=z for x,z in outputs),w
        after_stack=bytes(self.uc.mem_read(pp.STACK_BASE,pp.STACK_SIZE))
        assert after_stack[:SP-0x200-pp.STACK_BASE]==before_stack[:SP-0x200-pp.STACK_BASE]
        assert after_stack[SP-pp.STACK_BASE:]==before_stack[SP-pp.STACK_BASE:]
        after_scratch=bytes(self.uc.mem_read(pp.SCRATCH,0x10000))
        assert all(any(a<=pp.SCRATCH+i<z for a,z in outputs)
            for i,(a,b) in enumerate(zip(before_scratch,after_scratch)) if a!=b)
        for a,data in self.images:assert bytes(self.uc.mem_read(a,len(data)))==data
        assert all('stub' not in c for c in self.calls)
        return {'label':label,'entry':hex(entry),'reason':self.reason,
            'stop_pc':hex(self.uc.reg_read(reg('pc'))),'return_u32_if_returned':self.uc.reg_read(reg('w0')) if complete else None,
            'pcs':self.pcs,'original_calls_and_returns':self.calls,'stores':self.stores,'raw98_reads':self.reads,
            'callee_saved_X19_X29_D8_D15_preserved_on_complete_return':complete,
            'whole_stack_outside_declared_512_bytes_unchanged':True,
            'whole_scratch_outside_declared_outputs_unchanged':True,
            'whole_original_relocated_images_unchanged':True,
            'output_return_logging_or_vcall_adapters':False}

    def close(self):
        for h in self.hooks:self.uc.hook_del(h)


def dataflow(seed,header,stored_len,capacity):
    m=Guest(DF,seed,[(0x31f58,0x321a0),(0x32200,0x32210),(0x3128c,0x31318)])
    try:
        m.uc.mem_write(SOURCE,header)
        events=[m.phase('original DataflowInfraMsg constructor',0x31f58,
            outputs=[(OBJ,OBJ+0x198)],sp=SP,x30=pp.STOP,x0=OBJ)]
        constructed=bytes(m.uc.mem_read(OBJ,0x198))
        events.append(m.phase('original SetGlobalMsg and same-firmware memcpy',0x31f7c,
            outputs=[(OBJ,OBJ+0x198)],sp=SP,x30=pp.STOP,x0=OBJ,x1=SOURCE,x2=stored_len))
        assert events[-1]['return_u32_if_returned']==0
        loaded=bytes(m.uc.mem_read(OBJ,0x198))
        assert struct.unpack_from('<I',loaded,8)[0]==2 and struct.unpack_from('<H',loaded,0xc)[0]==stored_len
        assert loaded[0x18:0x18+stored_len]==header[:stored_len]
        assert loaded[0x18+stored_len:]==constructed[0x18+stored_len:]
        srcid=0x235a0000+seed
        events.append(m.phase('original SetSrcId',0x32194,outputs=[(OBJ+0x10,OBJ+0x14)],
            sp=SP,x30=pp.STOP,x0=OBJ,x1=srcid))
        events.append(m.phase('original GetSrcId before consumption',0x32200,outputs=[(SRCID_OUT,SRCID_OUT+4)],
            sp=SP,x30=pp.STOP,x0=OBJ,x1=SRCID_OUT))
        assert struct.unpack('<I',bytes(m.uc.mem_read(SRCID_OUT,4)))[0]==srcid
        before=bytes(m.uc.mem_read(CMD,0x38))
        events.append(m.phase('original GetMsg, Clear, memcpy, memset and native log early return',0x32070,
            outputs=[(CMD+8,CMD+8+min(stored_len,capacity)),(OBJ,OBJ+0x198)],
            sp=SP,x30=pp.STOP,x0=OBJ,x1=CMD+8,x2=capacity))
        assert events[-1]['return_u32_if_returned']==0
        copied=min(stored_len,capacity)
        received=bytes(m.uc.mem_read(CMD,0x38));cleared=bytes(m.uc.mem_read(OBJ,0x198))
        assert received[:8]==before[:8] and received[8:8+copied]==header[:copied]
        assert received[8+copied:]==before[8+copied:]
        assert struct.unpack_from('<I',cleared,8)[0]==0 and struct.unpack_from('<H',cleared,0xc)[0]==0
        assert struct.unpack_from('<I',cleared,0x10)[0]==0
        assert cleared[0x18:0x18+stored_len]==bytes(stored_len)
        assert cleared[0x18+stored_len:]==constructed[0x18+stored_len:]
        events.append(m.phase('original repeated GetMsg on consumed state0',0x32070,
            sp=SP,x30=pp.STOP,x0=OBJ,x1=CMD+8,x2=capacity))
        assert events[-1]['return_u32_if_returned']==0xffffffe5
        assert bytes(m.uc.mem_read(CMD,0x38))==received
        assert bytes(m.uc.mem_read(SOURCE,0x30))==header
        imports=[c['same_firmware_original_import'] for e in events for c in e['original_calls_and_returns']
            if 'same_firmware_original_import' in c]
        assert imports==['memcpy','memcpy','memset']
        return {'seed':seed,'declared_stored_len':stored_len,'declared_capacity':capacity,'copied_len':copied,
            'original_header30_hex':header.hex(),'received38_before_prefix_hex':received.hex(),
            'native_return0_is_not_complete_header_length_evidence':True,
            'header_complete':stored_len==capacity==0x30,'native_state_length_srcid_and_stored_payload_cleared':True,
            'message_object_after_clear_hex':cleared.hex(),'events':events,
            'same_firmware_imports_in_execution_order':imports,
            'actual_ReceiveASync_transport_Sony_loader_payload_ownership_or_runtime_mapping_proven':False}
    finally:m.close()


def consume(seed,received,raw,view):
    m=Guest(AV,seed,[(0x138ee8,0x138f00),(0xb2958,0xb29dc)])
    try:
        # Explicit inter-guest handoff of original GetMsg bytes; no shared process claim.
        m.uc.mem_write(CMD,received);m.uc.mem_write(VBASE,raw)
        # Declared graph only supplies readable vtable fields. Both targets stay zero
        # and native BLR instructions are never executed or returned from.
        m.uc.mem_write(SELF+0x10,struct.pack('<Q',PCONTROL))
        m.uc.mem_write(PCONTROL,struct.pack('<Q',VTABLE))
        m.uc.mem_write(VTABLE+0x10,bytes(8));m.uc.mem_write(VTABLE+0x60,bytes(8))
        events=[m.phase('independent original ReceiveCommand prefix after exact native Dataflow bytes',0x138ee8,
            outputs=[(CMD,CMD+6)],complete=False,sp=SP,x30=pp.STOP,x20=CMD)]
        assert events[-1]['reason']=='boundary: after_original_receive_prefix'
        command=bytes(m.uc.mem_read(CMD,0x38));assert struct.unpack_from('<3H',command)==(0x7000,0x9000,0x38)
        assert command[6:]==received[6:]
        events.append(m.phase('original SetParameter prologue to first unbound virtual call',0xb2958,
            complete=False,sp=SP,x30=pp.STOP,x0=SELF,x1=CMD))
        assert events[-1]['reason']=='boundary: before_first_unbound_ParameterControl_vcall'
        assert m.uc.reg_read(reg('x4'))==0
        events.append(m.phase('independent original post-vcall pointer and ViewId consumption',0xb299c,
            outputs=[(SELF+0x1b8,SELF+0x1b9)],complete=False))
        assert events[-1]['reason']=='boundary: before_second_unbound_ParameterControl_vcall'
        assert m.uc.reg_read(reg('x3'))==0
        pointer=m.uc.reg_read(reg('x20'));tag=m.uc.reg_read(reg('w23'))
        assert pointer==VBASE and tag==(0x805720f9 if view==1 else 0x805700f9)
        assert bytes(m.uc.mem_read(SELF+0x1b8,1))==command[0x20:0x21]
        assert events[-1]['raw98_reads']==[{'pc':'0xb29c0','raw98_offset':'0x64','size':1,'bytes':raw[0x64:0x65].hex()}]
        assert bytes(m.uc.mem_read(CMD,0x38))==command and bytes(m.uc.mem_read(VBASE,0x98))==raw
        return {'seed':seed,'declared_view':view,'command38_hex':command.hex(),
            'native_loaded_virtual_pointer':hex(pointer),'native_selected_opaque_tag':hex(tag),
            'native_CodecType_copy':command[0x20],'events':events,
            'two_vcall_targets_explicit_zero_and_both_calls_unexecuted':True,
            'post_vcall_phase_is_independent_input_not_fabricated_vcall_return':True,
            'actual_process_map_ParameterControl_admission_Open_or_hardware_proven':False}
    finally:m.close()


def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    im.volume();assert sha(PRIOR.read_bytes())==PRIOR_SHA
    for f in json.loads(PRIOR.read_text())['files']:
        data=(ROOT/f['path']).read_bytes();assert len(data)==f['bytes'] and sha(data)==f['sha256']
    assert (BASE/'GOAL_STATUS.json').read_bytes()==(STAGE/'goal-status-before.json').read_bytes()
    a.out.mkdir(exist_ok=False);(a.out/'executed-source.py').write_bytes(Path(__file__).read_bytes())
    try:
        source=PRIOR.parent/'run-copy-argument-checkpoint-20261027/fixed-area-results.json'
        profiles=BASE/'stage106-native-MPR-Open-fields/run-negative-boundaries-20261027/mpr-open-results.json'
        prior=json.loads(source.read_text());old=json.loads(profiles.read_text());rows=[];consumers=[]
        for seed in (0xa5,0xc3):
            c=next(c for c in prior['cases'] if c['seed']==seed and c['mode']=='normal_declared_mapping')
            raw=bytes.fromhex(next(p for p in old['produced'] if p['seed']==seed and p['label']=='target_HEVC_HD420')['raw98_hex'])
            for h in c['messages'][:2]:
                assert h['count']==1 and h['native_virtual_pointer']==hex(VBASE)
                header=bytes.fromhex(h['copied_header30_hex'])
                result=dataflow(seed,header,0x30,0x30);rows.append(result)
                consumers.append(consume(seed,bytes.fromhex(result['received38_before_prefix_hex']),raw,h['declared_view']))
            header=bytes.fromhex(c['messages'][0]['copied_header30_hex'])
            rows.extend([dataflow(seed,header,0x10,0x30),dataflow(seed,header,0x30,0x10)])
        phases=sum(len(x['events']) for x in rows+consumers)
        j={'status':'PASS_ORIGINAL_DATAFLOW_COPY_CLEAR_AND_BOUNDED_AV_POINTER_USE_NOT_RUNTIME_TRANSPORT',
            'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'dataflow_sha256':DF_SHA,'same_firmware_libc_sha256':LIBC_SHA,'av_sha256':sha(AV.blob),
            'header_source':str(source.relative_to(ROOT)),'header_source_sha256':sha(source.read_bytes()),
            'profile_source':str(profiles.relative_to(ROOT)),'profile_source_sha256':sha(profiles.read_bytes()),
            'messages':rows,'AV_consumers':consumers,'bounded_phases':phases,
            'partial_header_controls_not_forwarded_to_AV':True,
            'native_memcpy_memset_no_output_or_return_adapters':True,
            'actual_payload_copy_ReceiveASync_process_mapping_main_record_or_recovery_proven':False,
            'Windows_UU_camera_operations':False,'goal_complete':False,'persistent_write_release':False}
        (a.out/'dataflow-results.json').write_text(json.dumps(j,ensure_ascii=False,indent=2)+'\n')
        print(json.dumps({'status':j['status'],'messages':len(rows),'AV_consumers':len(consumers),'bounded_phases':phases}))
    except BaseException:
        (a.out/'attempt-failure.json').write_text(json.dumps({'passing_result':False,'traceback':traceback.format_exc()},indent=2)+'\n');raise


if __name__=='__main__':main()
