#!/usr/bin/env python3
"""Original VUI flag -> real caller/prologue -> mode body -> declared GOP.

Keep the native mode frame across the unexecuted address-translation/MADD gap.
Only output-slot and codec addresses are explicitly bound after that gap.
"""
from pathlib import Path
import argparse
import datetime
import json
import struct
import sys

STAGE=Path(__file__).resolve().parent
BASE,ROOT=STAGE.parent,STAGE.parent.parents[1]
sys.path.insert(0,str(BASE/'stage85-hevc-slice-layout-production'))
import slice_layout as p
a,im,u,reg,IMAGE=p.a,p.im,p.u,p.reg,p.IMAGE
PRIOR_SHA='e931f46b42e9c5e149a58708597f1344fadff451944da4742f296e6a6f22d584'
PARAM_PA,PARAM=a.SLOT_PA+0x18c,a.SLOT+0x18c
EXTRA_LIMITS=((0x18ee08,0x18f5d4),(0x18bca0,0x18bcac),
              (0x18d62c,0x18d650),(0x18d6a0,0x18d8cc))
STOPS={**p.STOPS,0x18d650:'before_mode_MMIO_address_prefix',
       0x18bcac:'native_mode_return_to_original_caller'}


class Guest(p.Guest):
    def code(self,uc,pc,size,user):
        self.pcs.append(pc);off=pc-IMAGE
        if pc==a.STOP:self.reason='returned';uc.emu_stop();return
        if off in STOPS:self.reason=STOPS[off];uc.emu_stop();return
        assert len(self.pcs)<6000
        assert any(lo<=off and off+size<=hi for lo,hi in a.LIMITS+p.EXTRA_LIMITS+EXTRA_LIMITS),(hex(pc),size)
        ins=next(self.md.disasm(self.blob[off:off+size],pc),None)
        assert ins is not None,(hex(pc),self.blob[off:off+size].hex())
        if off in a.CALIBRATED_BREAK_SITES:
            assert ins.mnemonic=='break' and self.blob[off:off+4].hex()=='cd010000'
            return
        assert ins.mnemonic not in {'syscall','break','cache','sync','mfc0','mtc0',
              'eret','wait','tlbwi','tlbwr','tlbr','tlbp','jalr'},(hex(pc),ins.mnemonic,ins.op_str)

    def run(self,label,entry,allowed_config=False,allowed_params=False,allowed_gop=False,
            resume_native_frame=False,**regs):
        initial={} if resume_native_frame else {'sp':a.SP,'ra':a.STOP}
        for name,value in {**initial,**regs}.items():
            self.uc.reg_write(getattr(reg,'UC_MIPS_REG_'+name.upper()),value)
        sp_before=self.uc.reg_read(reg.UC_MIPS_REG_SP)
        stack=bytes(self.uc.mem_read(a.STACK_PA,65536))
        slot=bytes(self.uc.mem_read(a.SLOT_PA,0x4000));gop=bytes(self.uc.mem_read(a.GOP_PA,4096))
        self.pcs=[];self.reason=None;self.interrupts=[]
        self.uc.emu_start(IMAGE+entry,0,timeout=1000000,count=0)
        assert self.reason in {'returned',*STOPS.values()},self.reason
        assert not self.interrupts
        assert bytes(self.uc.mem_read(0,len(self.blob)))==self.blob
        assert bytes(self.uc.mem_read(a.INPUT_PA,4096))==self.input
        after_stack=bytes(self.uc.mem_read(a.STACK_PA,65536))
        lo,hi=a.SP-IMAGE-a.STACK_PA-0x400,a.SP-IMAGE-a.STACK_PA+0x90
        assert after_stack[:lo]==stack[:lo] and after_stack[hi:]==stack[hi:]
        after_slot=bytes(self.uc.mem_read(a.SLOT_PA,0x4000));after_gop=bytes(self.uc.mem_read(a.GOP_PA,4096))
        allowed=set()
        if allowed_config:allowed.update(range(4,0xe4))
        if allowed_params:allowed.update(range(0x18c,0x2b0))
        assert all(x==y or i in allowed for i,(x,y) in enumerate(zip(slot,after_slot)))
        if not allowed_gop:assert after_gop==gop
        sp_after=self.uc.reg_read(reg.UC_MIPS_REG_SP)
        assert sp_after==a.SP-(0x20 if self.reason=='before_mode_MMIO_address_prefix' else 0)
        return {'label':label,'entry':hex(IMAGE+entry),'stop':self.reason,
                'pc':hex(self.uc.reg_read(reg.UC_MIPS_REG_PC)),
                'CODE_observed_PCs':[hex(x) for x in self.pcs],
                'SP_before':hex(sp_before),'SP_after':hex(sp_after),
                'resume_native_frame_without_SP_RA_reset':resume_native_frame,
                'whole_original_image_and_input_unchanged':True,
                'all_slot_bytes_outside_explicit_config_or_VUI_windows_unchanged':True,
                'stack_outside_declared_scratch_window_unchanged':True,
                'memory_read_write_hooks_installed':False,'code_MMIO_or_return_adapter':False,
                'native_interrupts':self.interrupts,
                'PC_observation_may_include_annulled_delay_slots':True,
                'config_after_hex':after_slot[4:0xe4].hex(),
                'VUI_parameters_after_hex':after_slot[0x18c:0x2b0].hex()}


def one(blob,source,seed,kind):
    codec=bytearray.fromhex(source['codec_hex']);common=bytes.fromhex(source['common_hex'])
    edits=[];req6=0
    if kind=='target20M':
        old=codec[0x2c:0x30].hex();struct.pack_into('<I',codec,0x2c,((20000000//64)-1)<<8)
        edits.append({'offset':'0x2c','before':old,'after':codec[0x2c:0x30].hex()})
    elif kind=='VUI_source_bit8_clear':
        old=codec[0x88:0x8c].hex();struct.pack_into('<I',codec,0x88,a.get32(codec,0x88)&~0x100)
        edits.append({'offset':'0x88','before':old,'after':codec[0x88:0x8c].hex()})
    elif kind=='source_enum0':
        edits.append({'offset':'0x67','before':codec[0x67:0x68].hex(),'after':'00'});codec[0x67]=0
    elif kind=='request6_1':req6=1
    else:assert kind=='captured'
    assert codec[0x64]==1
    m=Guest(blob,common,bytes(codec),seed,0,req6);events=[]
    events.append(m.run('independent original application GP pair',0x930c))
    events.append(m.run('complete original parameter constructor',0x200794,allowed_config=True,a0=a.CONFIG))
    events.append(m.run('independent common header tail after address gap',0x18cc30,allowed_config=True,
                        t1=a.SLOT,a2=a.CONFIG,t2=0,t5=a.COMMON,a1=a.CODEC))
    events.append(m.run('original HEVC prefix before output MFLO',0x18cd40,s5=a.CODEC))
    events.append(m.run('continuous original HEVC body with native helper returns',0x18cd54,
                        allowed_config=True,a0=a.SLOT,s2=a.COMMON,s5=a.CODEC,s6=a.REQUEST,s7=a.SLOT,fp=0))
    events.append(m.run('original slice source prefix before output MFLO',0x18ebd4,a1=a.CODEC,a3=a.COMMON))
    events.append(m.run('original type2 slice dispatch and complete native call tree',0x18ebe4,
                        allowed_config=True,a0=a.SLOT,t1=a.SLOT,t0=0))
    before_vui=bytes(m.uc.mem_read(PARAM_PA,292))
    config_before_vui=bytes(m.uc.mem_read(a.SLOT_PA+4,0xe0))
    saved=p.saved_registers(m)
    events.append(m.run('complete original VUI parser on captured-fixture codec bytes',0x18ee08,
                        allowed_params=True,a0=a.SLOT,a1=a.CODEC+0x88,a2=PARAM))
    assert events[-1]['stop']=='returned' and p.saved_registers(m)==saved
    parsed=bytes(m.uc.mem_read(PARAM_PA,292))
    assert bytes(m.uc.mem_read(a.SLOT_PA+4,0xe0))==config_before_vui
    flag=(a.get32(parsed,4)>>23)&1
    assert flag==((a.get32(codec,0x88)>>8)&1)
    saved=p.saved_registers(m)
    events.append(m.run('original caller loads native VUI flag, JAL and real mode prologue',
                        0x18bca0,a0=a.SLOT,a1=a.REQUEST,v1=a.SLOT))
    assert events[-1]['stop']=='before_mode_MMIO_address_prefix'
    assert m.uc.reg_read(reg.UC_MIPS_REG_S1)==flag
    frame=bytes(m.uc.mem_read(a.SP-IMAGE-0x20,0x20))
    assert struct.unpack_from('<4I',frame,0x10)==(saved['S0'],saved['S1'],saved['S2'],IMAGE+0x18bcac)
    # Keep SP, RA, all native saved slots and S1 from the actual prologue.
    # A2 was the flag at function entry, then would become a translated codec
    # pointer. Declare that pointer after the unexecuted address/MADD gap;
    # never replace the flag already copied natively into S1.
    events.append(m.run('mode core resumes native frame with declared post-gap addresses',
                        0x18d6a0,allowed_config=True,resume_native_frame=True,a0=a.SLOT,a2=a.CODEC))
    assert events[-1]['stop']=='native_mode_return_to_original_caller'
    assert p.saved_registers(m)==saved
    assert bytes(m.uc.mem_read(a.SP-IMAGE-0x20,0x20))==frame
    after=bytes(m.uc.mem_read(a.SLOT_PA+4,0xe0))
    expected=bytearray(config_before_vui)
    enum=0x13 if codec[0x67]==19 else 1
    assert codec[0x67] in (0,19)
    struct.pack_into('<I',expected,0x90,(a.get32(expected,0x90)&~0x3fc)|(enum<<2))
    if codec[0x67]==19:expected[0x1c]=1
    expected[0x23]=(3 if flag else 1) if codec[0x67]==19 else (2 if flag else 0)
    if req6==1:expected[0x23]=0
    assert after==bytes(expected),{'kind':kind,'flag':flag,'source67':codec[0x67],
        'delta':[(hex(i),hex(x),hex(y)) for i,(x,y) in enumerate(zip(after,expected)) if x!=y]}
    assert bytes(m.uc.mem_read(PARAM_PA,292))==parsed
    saved=p.saved_registers(m)
    events.append(m.run('complete original zero-mode GOP constructor after VUI-driven conversion',
                        0xd866c,allowed_gop=True,a0=a.GOP,a1=a.CONFIG))
    assert events[-1]['stop']=='returned' and p.saved_registers(m)==saved
    want=bytearray([0xb6])*4096;want[0x78:0x114]=after[0x34:0xd0]
    want[0x174:0x184]=after[0xd0:0xe0]
    want[0x118]=after[0x14]&1;want[0x119]=(after[0x14]>>1)&1
    want[0x158]=after[0x22];want[0x15a:0x15c]=after[0xb0:0xb2]
    gop=bytes(m.uc.mem_read(a.GOP_PA,4096));assert gop==bytes(want)
    assert (a.get32(gop,0xd4)>>2)&255==enum
    assert a.get32(gop,0xc8)==a.get32(codec,0x2c)
    return {'source_label':source['label'],'seed':seed,'kind':kind,'source_edits':edits,
            'codec_input_hex':codec.hex(),'common_input_hex':common.hex(),
            'declared_request':{'0':0,'5':0,'6':req6,'other_bytes':'0xed_unknown_trial_values'},
            'config_before_mode_hex':config_before_vui.hex(),'config_after_mode_hex':after.hex(),
            'VUI_parameters_before_hex':before_vui.hex(),'VUI_parameters_after_hex':parsed.hex(),
            'native_VUI_flag_bit23':flag,'source_codec_VUI_bit8':(a.get32(codec,0x88)>>8)&1,
            'mode_entry_original_saved_frame_hex':frame.hex(),
            'original_prologue_frame_kept_through_native_epilogue_return':True,
            'native_callee_saved_registers_preserved':True,
            'output_packed_mode_enum':enum,'output_aux_byte23':after[0x23],
            'GOP_after_hex':gop.hex(),'GOP_update_gate_bit0':bool(a.get32(gop,0xe8)&1),
            'events':events,'source_builder_request_and_slot_are_fixtures_not_camera_capture':True,
            'full_original_address_translation_MADD_timing_MAIN_hardware_or_recovery':False}


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',required=True);out=Path(parser.parse_args().output)
    im.volume();assert not out.exists()
    prior=BASE/'stage85-hevc-slice-layout-production/final-receipt.json';assert im.sha(prior.read_bytes())==PRIOR_SHA
    for row in json.loads(prior.read_text())['files']:
        raw=(ROOT/row['path']).read_bytes();assert len(raw)==row['bytes'] and im.sha(raw)==row['sha256']
    assert (STAGE/'goal-status-before.json').read_bytes()==(BASE/'GOAL_STATUS.json').read_bytes()
    assert im.sha(a.prev.SOURCE.read_bytes())==a.prev.SOURCE_SHA
    sources=json.loads(a.prev.SOURCE.read_text())['cases'][:3]
    blob=a.prev.p.a.v.VCD_PATH.read_bytes();assert im.sha(blob)==im.PINS[str(a.prev.p.a.v.VCD_PATH.relative_to(BASE))]
    cases=[one(blob,s,seed,'captured') for seed in (0xa5,0xc3) for s in sources]
    cases += [one(blob,sources[0],seed,kind) for seed in (0xa5,0xc3)
              for kind in ('target20M','VUI_source_bit8_clear','source_enum0','request6_1')]
    pairs=[]
    for kind in ('captured','target20M','VUI_source_bit8_clear','source_enum0','request6_1'):
        left,right=(next(c for c in cases if c['seed']==seed and c['kind']==kind and c['source_label']==sources[0]['label'])
                    for seed in (0xa5,0xc3))
        aa,bb=(bytes.fromhex(c['config_after_mode_hex']) for c in (left,right))
        deps=[{'offset':hex(i),'xor_mask':hex(x^y),'A5':hex(x),'C3':hex(y)}
              for i,(x,y) in enumerate(zip(aa,bb)) if x!=y]
        block=[x for x in deps if 0x34<=int(x['offset'],16)<0xd0]
        assert len(block)==5
        pairs.append({'kind':kind,'remaining_config_old_seed_dependency':deps,
                      'remaining_GOP_block_old_seed_dependency':block,
                      'all_other_bits_initialized_or_hardware_validity_proven':False})
    result={'status':'PASS_NATIVE_VUI_FLAG_TO_MODE_FRAME_RETURN_AND_GOP_COPY',
            'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'source_receipt':{'script_sha256':im.sha(Path(__file__).read_bytes()),
                              'prior_runner_sha256':im.sha((p.STAGE/'slice_layout.py').read_bytes()),
                              'VCD_sha256':im.sha(blob),'stage50_result_sha256':a.prev.SOURCE_SHA,
                              'prior_manifest_sha256':PRIOR_SHA},
            'cases':cases,'old_seed_dependency_pairs':pairs,
            'bounded_phases':sum(len(c['events']) for c in cases),
            'scope':'Complete original VUI leaf, real caller load/JAL/prologue and preserved native mode frame; '
                    'address/MMIO/MADD block remains unexecuted with explicit post-gap slot/codec bindings. '
                    'No actual Start capture, full initialization, timing, MAIN or hardware/recovery.',
            'Windows_UU_camera_operations':False,'goal_complete':False,'persistent_write_release':False}
    out.mkdir();im.write_json(out/'vui-mode-results.json',result)
    (out/'executed-source.py').write_bytes(Path(__file__).read_bytes())
    print(json.dumps({'status':result['status'],'cases':len(cases),'bounded_phases':result['bounded_phases'],
                      'remaining_GOP_old_seed_dependency_bytes':5,'output':str(out)}))


if __name__=='__main__':main()
