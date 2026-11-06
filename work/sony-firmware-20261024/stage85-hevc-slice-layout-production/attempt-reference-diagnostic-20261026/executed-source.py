#!/usr/bin/env python3
"""Fresh original HEVC body then native slice-layout dispatch, no device I/O."""
from pathlib import Path
import argparse
import datetime
import json
import struct
import sys

STAGE=Path(__file__).resolve().parent
BASE,ROOT=STAGE.parent,STAGE.parent.parents[1]
sys.path.insert(0,str(BASE/'stage84-hevc-native-config-body'))
import native_body as a
im,u,reg,cs,IMAGE=a.im,a.u,a.reg,a.cs,a.IMAGE
PRIOR_SHA='33cfb85162fe38893b0acb62282eee5b5ba1813cf103316892aa887e7917c667'
EXTRA_LIMITS=((0x18ebd4,0x18ebe0),(0x18ebe4,0x18ec34),(0x18ed04,0x18ed94),
              (0x1a279c,0x1a2864),(0x1a2920,0x1a3168))
STOPS={**a.STOPS,0x18ebe0:'before_unresolved_slice_output_MFLO',
       0x18ec34:'after_native_type2_slice_return_before_parent_epilogue'}


class Guest(a.Guest):
    def code(self,uc,pc,size,user):
        self.pcs.append(pc);off=pc-IMAGE
        if pc==a.STOP:self.reason='returned';uc.emu_stop();return
        if off in STOPS:self.reason=STOPS[off];uc.emu_stop();return
        assert len(self.pcs)<5000
        assert any(lo<=off and off+size<=hi for lo,hi in a.LIMITS+EXTRA_LIMITS),(hex(pc),size)
        ins=next(self.md.disasm(self.blob[off:off+size],pc),None)
        assert ins is not None,(hex(pc),self.blob[off:off+size].hex())
        if off in a.CALIBRATED_BREAK_SITES:
            assert ins.mnemonic=='break' and self.blob[off:off+4].hex()=='cd010000'
            return
        assert ins.mnemonic not in {'syscall','break','cache','sync','mfc0','mtc0',
              'eret','wait','tlbwi','tlbwr','tlbr','tlbp','jalr'},(hex(pc),ins.mnemonic,ins.op_str)

    def run(self,label,entry,allowed_slot=False,allowed_gop=False,**regs):
        for name,value in {'sp':a.SP,'ra':a.STOP,**regs}.items():
            self.uc.reg_write(getattr(reg,'UC_MIPS_REG_'+name.upper()),value)
        stack=bytes(self.uc.mem_read(a.STACK_PA,65536))
        slot=bytes(self.uc.mem_read(a.SLOT_PA,0x4000));gop=bytes(self.uc.mem_read(a.GOP_PA,4096))
        self.pcs=[];self.reason=None;self.interrupts=[]
        self.uc.emu_start(IMAGE+entry,0,timeout=1000000,count=0)
        assert self.reason in {'returned',*STOPS.values()},self.reason
        assert not self.interrupts
        assert bytes(self.uc.mem_read(0,len(self.blob)))==self.blob
        assert bytes(self.uc.mem_read(a.INPUT_PA,4096))==self.input
        # Native slice helper + descriptor + recursive partition frames need
        # this declared scratch window. None of its saved returns are supplied.
        after_stack=bytes(self.uc.mem_read(a.STACK_PA,65536))
        lo,hi=a.SP-IMAGE-a.STACK_PA-0x400,a.SP-IMAGE-a.STACK_PA+0x90
        assert after_stack[:lo]==stack[:lo] and after_stack[hi:]==stack[hi:]
        after_slot=bytes(self.uc.mem_read(a.SLOT_PA,0x4000));after_gop=bytes(self.uc.mem_read(a.GOP_PA,4096))
        if allowed_slot:assert after_slot[:4]==slot[:4] and after_slot[0xe4:]==slot[0xe4:]
        else:assert after_slot==slot
        if not allowed_gop:assert after_gop==gop
        assert self.uc.reg_read(reg.UC_MIPS_REG_SP)==a.SP-(0x20 if entry==0xd866c else 0)
        return {'label':label,'entry':hex(IMAGE+entry),'stop':self.reason,
                'pc':hex(self.uc.reg_read(reg.UC_MIPS_REG_PC)),
                'CODE_observed_PCs':[hex(x) for x in self.pcs],
                'SP_after':hex(self.uc.reg_read(reg.UC_MIPS_REG_SP)),
                'whole_original_image_and_input_unchanged':True,
                'all_other_channel_and_manager_bytes_unchanged':True,
                'stack_outside_declared_scratch_window_unchanged':True,
                'memory_read_write_hooks_installed':False,'code_MMIO_or_return_adapter':False,
                'native_interrupts':self.interrupts,
                'PC_observation_may_include_annulled_delay_slots':True,
                'config_after_hex':after_slot[4:0xe4].hex()}


def saved_registers(m):
    return {name:m.uc.reg_read(getattr(reg,'UC_MIPS_REG_'+name))
            for name in ('S0','S1','S2','S3','S4','S5','S6','S7','FP','GP')}


def reference_layout(rows,number):
    # Independent integer partition expectation for the captured one-range,
    # four-slice input only. This is not substituted for any guest callee.
    assert number==4 and rows==68
    half=(rows+1)//2
    leaves=[half]
    for _ in range(number.bit_length()-1):
        leaves=[x for n in leaves for x in (n//2,n-n//2)]
    return [2*x for x in leaves]+[0]*12


def one(blob,source,seed,kind):
    codec=bytearray.fromhex(source['codec_hex']);common=bytes.fromhex(source['common_hex'])
    req6=0;edits=[]
    if kind=='target20M':
        old=codec[0x2c:0x30].hex();struct.pack_into('<I',codec,0x2c,((20000000//64)-1)<<8)
        edits.append({'buffer':'codec','offset':'0x2c','before':old,'after':codec[0x2c:0x30].hex()})
    elif kind=='request6_1':req6=1
    else:assert kind=='captured'
    m=Guest(blob,common,bytes(codec),seed,0,req6);events=[]
    events.append(m.run('independent original application GP pair',0x930c))
    assert m.uc.reg_read(reg.UC_MIPS_REG_GP)==a.GP
    events.append(m.run('complete original parameter constructor',0x200794,allowed_slot=True,a0=a.CONFIG))
    events.append(m.run('independent common header tail after address gap',0x18cc30,allowed_slot=True,
                        t1=a.SLOT,a2=a.CONFIG,t2=0,t5=a.COMMON,a1=a.CODEC))
    events.append(m.run('original HEVC field loads before unresolved output MFLO',0x18cd40,s5=a.CODEC))
    events.append(m.run('continuous original HEVC body with native helper returns',0x18cd54,
                        allowed_slot=True,a0=a.SLOT,s2=a.COMMON,s5=a.CODEC,s6=a.REQUEST,s7=a.SLOT,fp=0))
    assert events[-1]['stop']=='before_timing_stack_and_multiply'
    body=bytes(m.uc.mem_read(a.SLOT_PA+4,0xe0))
    assert body[0xb0:0xd0]==bytes([seed])*32
    events.append(m.run('original source prefix for slice geometry before output MFLO',
                        0x18ebd4,a1=a.CODEC,a3=a.COMMON))
    assert events[-1]['stop']=='before_unresolved_slice_output_MFLO'
    assert m.uc.reg_read(reg.UC_MIPS_REG_V1)==struct.unpack_from('<H',codec,0xc)[0]+15
    assert m.uc.reg_read(reg.UC_MIPS_REG_V0)==common[0]
    saved=saved_registers(m)
    # Independent post-MFLO entry declares only the output/manager address and
    # channel index. V0/V1 and source pointers remain original prefix outputs.
    events.append(m.run('original type2 dispatch and complete native slice-layout call tree',
                        0x18ebe4,allowed_slot=True,a0=a.SLOT,t1=a.SLOT,t0=0))
    assert events[-1]['stop']=='after_native_type2_slice_return_before_parent_epilogue'
    assert saved_registers(m)==saved
    after=bytes(m.uc.mem_read(a.SLOT_PA+4,0xe0))
    assert after[:0xb0]==body[:0xb0] and after[0xd0:]==body[0xd0:]
    fields=struct.unpack_from('<16H',after,0xb0)
    rows=struct.unpack_from('<H',body,0x3a)[0]+1
    expected=reference_layout(rows,body[0x10])
    assert list(fields)==expected and sum(fields[:8])==rows and not any(fields[8:]),{
        'actual':list(fields),'expected':expected,'rows':rows,
        'descriptor':bytes(m.uc.mem_read(a.SP-IMAGE-0x40,0x28)).hex()}
    # Caller-owned descriptor stays above the nested frames; read retained
    # original stores after all real callees have returned, outside callbacks.
    descriptor=bytes(m.uc.mem_read(a.SP-IMAGE-0x40,0x28))
    assert struct.unpack('<10I',descriptor)==(0,67,4,0,0,0,68,0,4,0)
    required=(0x18ed04,0x1a279c,0x1a2800,0x1a2920,0x1a2fc4,0x1a2d4c,0x1a27f8)
    assert all(hex(IMAGE+x) in events[-1]['CODE_observed_PCs'] for x in required)
    events.append(m.run('independent original GOP copy after native slice production',
                        0xd866c,allowed_gop=True,a0=a.GOP,a1=a.CONFIG))
    assert events[-1]['stop']=='before_GOP_base_helper'
    want=bytearray([0xb6])*4096;want[0x78:0x114]=after[0x34:0xd0]
    gop=bytes(m.uc.mem_read(a.GOP_PA,4096));assert gop==bytes(want)
    assert gop[0xf4:0x114]==after[0xb0:0xd0]
    assert a.get32(gop,0xc8)==a.get32(codec,0x2c)
    return {'source_label':source['label'],'seed':seed,'kind':kind,'source_edits':edits,
            'common_input_hex':common.hex(),'codec_input_hex':codec.hex(),
            'declared_request':{'0':0,'5':0,'6':req6,'other_bytes':'0xed_unknown_trial_values'},
            'config_before_slice_hex':body.hex(),'config_after_slice_hex':after.hex(),
            'native_descriptor_after_return_hex':descriptor.hex(),
            'slice_layout_u16':list(fields),'reference_layout_u16':expected,
            'first_group_sum_in_16pixel_block_rows':sum(fields[:8]),
            'second_group_sum_in_16pixel_block_rows':sum(fields[8:]),
            'native_callee_saved_registers_preserved':True,
            'GOP_after_hex':gop.hex(),'events':events,
            'actual_runtime_dispatch_address_translation_complete_timing_MAIN_or_encoding':False,
            'source_builder_and_request_are_fixtures_not_camera_capture':True}


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',required=True);out=Path(parser.parse_args().output)
    im.volume();assert not out.exists()
    prior=BASE/'stage84-hevc-native-config-body/final-receipt.json';assert im.sha(prior.read_bytes())==PRIOR_SHA
    for r in json.loads(prior.read_text())['files']:
        raw=(ROOT/r['path']).read_bytes();assert len(raw)==r['bytes'] and im.sha(raw)==r['sha256']
    assert (STAGE/'goal-status-before.json').read_bytes()==(BASE/'GOAL_STATUS.json').read_bytes()
    assert im.sha(a.prev.SOURCE.read_bytes())==a.prev.SOURCE_SHA
    sources=json.loads(a.prev.SOURCE.read_text())['cases'][:3]
    blob=a.prev.p.a.v.VCD_PATH.read_bytes();assert im.sha(blob)==im.PINS[str(a.prev.p.a.v.VCD_PATH.relative_to(BASE))]
    source_name=blob[0x23a7c4:].split(b'\0',1)[0].decode()
    assert source_name.endswith('/slice_split_line_calculator/slice_split_line_calculator.cxx')
    cases=[one(blob,s,seed,'captured') for seed in (0xa5,0xc3) for s in sources]
    cases += [one(blob,sources[0],seed,kind) for seed in (0xa5,0xc3) for kind in ('target20M','request6_1')]
    pairs=[]
    for kind in ('captured','target20M','request6_1'):
        left,right=(next(c for c in cases if c['seed']==seed and c['kind']==kind and c['source_label']==sources[0]['label'])
                    for seed in (0xa5,0xc3))
        aa,bb=(bytes.fromhex(c['config_after_slice_hex']) for c in (left,right))
        deps=[{'offset':hex(i),'xor_mask':hex(x^y),'A5':hex(x),'C3':hex(y)}
              for i,(x,y) in enumerate(zip(aa,bb)) if x!=y]
        block=[x for x in deps if 0x34<=int(x['offset'],16)<0xd0]
        assert len(block)==7
        pairs.append({'kind':kind,'remaining_config_old_seed_dependency':deps,
                      'remaining_GOP_block_old_seed_dependency':block,
                      'native_slice32_equal_across_seeds':aa[0xb0:0xd0]==bb[0xb0:0xd0],
                      'all_other_bits_initialized_or_hardware_validity_proven':False})
    result={'status':'PASS_NATIVE_TYPE2_SLICE_PRODUCTION_CLEARS_32BYTE_OLD_SEED_DEPENDENCY',
            'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'source_receipt':{'script_sha256':im.sha(Path(__file__).read_bytes()),
                              'prior_runner_sha256':im.sha((a.STAGE/'native_body.py').read_bytes()),
                              'VCD_sha256':im.sha(blob),'stage50_result_sha256':a.prev.SOURCE_SHA,
                              'prior_manifest_sha256':PRIOR_SHA},
            'original_source_name':source_name,'original_source_name_file_offset':'0x23a7c4',
            'cases':cases,'old_seed_dependency_pairs':pairs,
            'bounded_phases':sum(len(c['events']) for c in cases),
            'scope':'Fresh captured-fixture HEVC body then original type2 slice dispatch after explicit unresolved address gaps. '
                    'All nested helper calls/returns native. No actual request capture, full conversion, timing or MAIN/hardware binding.',
            'Windows_UU_camera_operations':False,'goal_complete':False,'persistent_write_release':False}
    out.mkdir();im.write_json(out/'slice-layout-results.json',result)
    (out/'executed-source.py').write_bytes(Path(__file__).read_bytes())
    print(json.dumps({'status':result['status'],'cases':len(cases),'bounded_phases':result['bounded_phases'],
                      'slice16_u16':cases[0]['slice_layout_u16'],'remaining_GOP_old_seed_dependency_bytes':7,
                      'output':str(out)}))


if __name__=='__main__':main()
