#!/usr/bin/env python3
"""Execute original HEVC middle body and real pure callees in declared RAM.

Native GP setup and ROM table; original constructor/common tail. The unresolved
channel-address MFLO and subsequent timing multiply/MMIO are not emulated.
"""
from pathlib import Path
import argparse
import datetime
import json
import struct
import sys

STAGE=Path(__file__).resolve().parent
BASE,ROOT=STAGE.parent,STAGE.parent.parents[1]
sys.path.insert(0,str(BASE/'stage83-hevc-initial-config-field-provenance'))
import config_fields as prev
im,u,reg,cs,IMAGE=prev.im,prev.u,prev.reg,prev.cs,prev.IMAGE
PRIOR_SHA='5ada501614df1d65c78910cbf64e39a4fbd64d096c4a1f2f1b9f7f04c6f98817'
INPUT_PA,COMMON,CODEC,REQUEST=0x01000000,0x81000000,0x81000100,0x81000800
SLOT_PA,SLOT,CONFIG=0x01100000,0x81100000,0x81100004
GOP_PA,GOP=0x01200000,0x81200000
STACK_PA,SP,STOP_PA,STOP=0x02000000,0x82008000,0x03000000,0x83000000
GP=0x8024eb58
LIMITS=((0x930c,0x9314),(0x200794,0x200834),(0x18cc30,0x18cc74),
        (0x18cd40,0x18cd50),(0x18cd54,0x18d62c),
        (0x19837c,0x198564),(0x18f708,0x18f82c),(0x18b168,0x18b1ec),
        (0xd866c,0xd8718))
STOPS={0x9314:'before_app_stack_or_startup',0x18cd50:'before_unresolved_output_address_MFLO',
       0x18d340:'before_timing_stack_and_multiply',0x18d5d4:'before_request1_MMIO_read',
       0xd8718:'before_GOP_base_helper',0x67ce4:'before_GOP_assertion_runtime',
       0xae50:'before_original_assertion_runtime'}


def get32(b,o):return struct.unpack_from('<I',b,o)[0]


class Guest:
    def __init__(self,blob,common,codec,seed,req5,req6):
        self.blob=blob
        self.uc=u.Uc(u.UC_ARCH_MIPS,u.UC_MODE_MIPS32|u.UC_MODE_LITTLE_ENDIAN)
        self.uc.ctl_set_cpu_model(reg.UC_CPU_MIPS32_24KC)
        self.md=cs.Cs(cs.CS_ARCH_MIPS,cs.CS_MODE_MIPS32|cs.CS_MODE_LITTLE_ENDIAN)
        for at,size,prot in ((0,(len(blob)+4095)&-4096,u.UC_PROT_READ|u.UC_PROT_EXEC),
                             (INPUT_PA,4096,u.UC_PROT_READ),
                             (SLOT_PA,0x4000,u.UC_PROT_READ|u.UC_PROT_WRITE),
                             (GOP_PA,4096,u.UC_PROT_READ|u.UC_PROT_WRITE),
                             (STACK_PA,65536,u.UC_PROT_READ|u.UC_PROT_WRITE),
                             (STOP_PA,4096,u.UC_PROT_READ|u.UC_PROT_EXEC)):
            self.uc.mem_map(at,size,prot)
        self.uc.mem_write(0,blob)
        data=bytearray([0xed])*4096
        data[:64]=common;data[0x100:0x2c0]=codec
        data[0x800]=0;data[0x805]=req5;data[0x806]=req6
        self.input=bytes(data);self.uc.mem_write(INPUT_PA,self.input)
        self.uc.mem_write(SLOT_PA,bytes([seed])*0x4000)
        self.uc.mem_write(GOP_PA,bytes([0xb6])*4096)
        self.uc.mem_write(STACK_PA,bytes([0xd7])*65536)
        self.uc.hook_add(u.UC_HOOK_CODE,self.code)
        self.uc.hook_add(u.UC_HOOK_MEM_INVALID,self.invalid)

    def invalid(self,uc,access,at,size,value,user):
        self.reason='invalid:'+hex(at);uc.emu_stop();return False

    def code(self,uc,pc,size,user):
        self.pcs.append(pc);off=pc-IMAGE
        if pc==STOP:self.reason='returned';uc.emu_stop();return
        if off in STOPS:self.reason=STOPS[off];uc.emu_stop();return
        assert len(self.pcs)<5000
        assert any(lo<=off and off+size<=hi for lo,hi in LIMITS),(hex(pc),size)
        ins=next(self.md.disasm(self.blob[off:off+size],pc),None)
        assert ins is not None,(hex(pc),self.blob[off:off+size].hex())
        assert ins.mnemonic not in {'syscall','break','cache','sync','mfc0','mtc0',
                                   'eret','wait','tlbwi','tlbwr','tlbr','tlbp','jalr'}

    def run(self,label,entry,allowed_slot=False,allowed_gop=False,**regs):
        for name,value in {'sp':SP,'ra':STOP,**regs}.items():
            self.uc.reg_write(getattr(reg,'UC_MIPS_REG_'+name.upper()),value)
        stack=bytes(self.uc.mem_read(STACK_PA,65536))
        slot=bytes(self.uc.mem_read(SLOT_PA,0x4000));gop=bytes(self.uc.mem_read(GOP_PA,4096))
        self.pcs=[];self.reason=None
        self.uc.emu_start(IMAGE+entry,0,timeout=1000000,count=0)
        assert self.reason in {'returned',*STOPS.values()},self.reason
        assert bytes(self.uc.mem_read(0,len(self.blob)))==self.blob
        assert bytes(self.uc.mem_read(INPUT_PA,4096))==self.input
        after_stack=bytes(self.uc.mem_read(STACK_PA,65536))
        lo,hi=SP-IMAGE-STACK_PA-0x80,SP-IMAGE-STACK_PA+0x90
        assert after_stack[:lo]==stack[:lo] and after_stack[hi:]==stack[hi:]
        after_slot=bytes(self.uc.mem_read(SLOT_PA,0x4000));after_gop=bytes(self.uc.mem_read(GOP_PA,4096))
        if allowed_slot:
            # Header/codec/timing constructor extent only; all other channels
            # and manager state stay byte-identical. No caller state created.
            assert slot[:4]==after_slot[:4] and slot[0xe4:]==after_slot[0xe4:]
        else:assert after_slot==slot
        if not allowed_gop:assert after_gop==gop
        assert self.uc.reg_read(reg.UC_MIPS_REG_SP)==SP-(0x20 if entry==0xd866c else 0)
        return {'label':label,'entry':hex(IMAGE+entry),'stop':self.reason,
                'pc':hex(self.uc.reg_read(reg.UC_MIPS_REG_PC)),
                'pcs':[hex(x) for x in self.pcs],
                'SP_after':hex(self.uc.reg_read(reg.UC_MIPS_REG_SP)),
                'whole_original_image_and_input_unchanged':True,
                'all_other_channel_and_manager_bytes_unchanged':True,
                'stack_outside_declared_scratch_window_unchanged':True,
                'memory_read_write_hooks_installed':False,'code_MMIO_or_return_adapter':False,
                'config_after_hex':after_slot[4:0xe4].hex(),
                'config_changed_offsets':[hex(i) for i,(x,y) in enumerate(zip(slot[4:0xe4],after_slot[4:0xe4])) if x!=y]}


def one(blob,source,seed,kind):
    common=bytes.fromhex(source['common_hex']);codec=bytearray.fromhex(source['codec_hex'])
    edits=[];req5=req6=0
    if kind=='target20M':
        old=codec[0x2c:0x30].hex();struct.pack_into('<I',codec,0x2c,((20000000//64)-1)<<8)
        edits.append({'offset':'0x2c','old':old,'new':codec[0x2c:0x30].hex()})
    elif kind=='table_index2':
        edits.append({'offset':'0xe','old':codec[0xe:0xf].hex(),'new':'02'});codec[0xe]=2
    elif kind=='request6_1':req6=1
    elif kind=='request5_2':req5=2
    elif kind=='request5_1_MMIO_boundary':req5=1
    else:assert kind=='captured'
    m=Guest(blob,common,bytes(codec),seed,req5,req6);events=[]
    # Only the literal GP instructions are run. Hardware startup, CP0 and real
    # app/task context are not entered. This does not infer initialized globals.
    events.append(m.run('independent original application GP setup pair',0x930c))
    assert m.uc.reg_read(reg.UC_MIPS_REG_GP)==GP
    assert blob[GP-IMAGE-0x6248:GP-IMAGE-0x6248+5]==bytes([0,1,4,2,3])
    events.append(m.run('complete original plain parameter constructor',0x200794,allowed_slot=True,a0=CONFIG))
    assert events[-1]['stop']=='returned'
    # Independent common-header tail after its unexecuted MMIO/address prefix.
    events.append(m.run('independent original common header tail',0x18cc30,allowed_slot=True,
                        t1=SLOT,a2=CONFIG,t2=0,t5=COMMON,a1=CODEC))
    assert events[-1]['stop']=='returned'
    header=bytes(m.uc.mem_read(SLOT_PA+4,0xe0))
    events.append(m.run('original HEVC input-prefix loads before unresolved address MFLO',
                        0x18cd40,s5=CODEC))
    assert events[-1]['stop']=='before_unresolved_output_address_MFLO'
    assert m.uc.reg_read(reg.UC_MIPS_REG_S3)==CODEC+0x18
    assert m.uc.reg_read(reg.UC_MIPS_REG_V0)==codec[0x23]
    assert m.uc.reg_read(reg.UC_MIPS_REG_V1)==codec[0x1e]
    # Independent post-MFLO entry with the declared slot address in A0.
    # Do NOT set LO/HI, execute unknown MADD or call this the full function.
    events.append(m.run('continuous original HEVC body and native pure helper returns',
                        0x18cd54,allowed_slot=True,a0=SLOT,s2=COMMON,s5=CODEC,
                        s6=REQUEST,s7=SLOT,fp=0))
    body=bytes(m.uc.mem_read(SLOT_PA+4,0xe0))
    complete=kind!='request5_1_MMIO_boundary'
    assert events[-1]['stop']==('before_timing_stack_and_multiply' if complete else 'before_request1_MMIO_read')
    assert m.uc.reg_read(reg.UC_MIPS_REG_GP)==GP
    if complete:
        assert struct.unpack_from('<HH',body,0x38)==(119,67)
        assert get32(body,0x84)==get32(codec,0x2c)
        assert body[0x75]==(4 if kind=='table_index2' else 0)
        needed=(0x19837c,0x198528,0x198478,0x18f708,0x18b168)
        assert all(hex(IMAGE+x) in events[-1]['pcs'] for x in needed)
        events.append(m.run('independent original HEVC GOP constructor copy',0xd866c,
                            allowed_gop=True,a0=GOP,a1=CONFIG))
        assert events[-1]['stop']=='before_GOP_base_helper'
        want=bytearray([0xb6])*4096;want[0x78:0x114]=body[0x34:0xd0]
        assert bytes(m.uc.mem_read(GOP_PA,4096))==bytes(want)
    else:
        assert bytes(m.uc.mem_read(GOP_PA,4096))==bytes([0xb6])*4096
    return {'source_label':source['label'],'seed':seed,'kind':kind,
            'source_codec_sha256':im.sha(bytes.fromhex(source['codec_hex'])),
            'codec_input_hex':codec.hex(),'common_input_hex':common.hex(),
            'declared_request_bytes':{'0':0,'5':req5,'6':req6,'other_bytes':'0xed_unknown_trial_values'},
            'source_edits':edits,'header_after_hex':header.hex(),'config_after_hex':body.hex(),
            'GOP_after_hex':bytes(m.uc.mem_read(GOP_PA,4096)).hex(),
            'continuous_body_reached_timing_boundary':complete,
            'decoded_config_target':prev.p.a.decode(get32(body,0x84)) if complete else None,
            'events':events,'full_converter_actual_address_translation_MAIN_or_hardware':False,
            'not_an_actual_Start_header_or_camera_memory_capture':True,
            'unknown_old_bytes_and_preserved_bits_not_claimed_initialized':True}


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',required=True);out=Path(parser.parse_args().output)
    im.volume();assert not out.exists()
    prior=BASE/'stage83-hevc-initial-config-field-provenance/final-receipt.json'
    assert im.sha(prior.read_bytes())==PRIOR_SHA
    for r in json.loads(prior.read_text())['files']:
        raw=(ROOT/r['path']).read_bytes();assert len(raw)==r['bytes'] and im.sha(raw)==r['sha256']
    assert (STAGE/'goal-status-before.json').read_bytes()==(BASE/'GOAL_STATUS.json').read_bytes()
    assert im.sha(prev.SOURCE.read_bytes())==prev.SOURCE_SHA
    sources=json.loads(prev.SOURCE.read_text())['cases'][:3]
    blob=prev.p.a.v.VCD_PATH.read_bytes();assert im.sha(blob)==im.PINS[str(prev.p.a.v.VCD_PATH.relative_to(BASE))]
    assert blob[0x930c:0x9314].hex()=='25801c3c58eb9c27'
    cases=[one(blob,x,seed,'captured') for seed in (0xa5,0xc3) for x in sources]
    cases += [one(blob,sources[0],seed,kind) for seed in (0xa5,0xc3)
              for kind in ('target20M','table_index2','request6_1','request5_2','request5_1_MMIO_boundary')]
    pairs=[]
    for kind in ('captured','target20M','table_index2','request6_1','request5_2'):
        a,b=(next(c for c in cases if c['kind']==kind and c['source_label']==sources[0]['label'] and c['seed']==seed)
             for seed in (0xa5,0xc3))
        aa,bb=(bytes.fromhex(c['config_after_hex']) for c in (a,b))
        pairs.append({'kind':kind,'old_seed_dependency_xor_by_offset':[
            {'offset':hex(i),'xor_mask':hex(x^y),'A5':hex(x),'C3':hex(y)}
            for i,(x,y) in enumerate(zip(aa,bb)) if x!=y],
            'scope':'Two seed patterns show concrete retained dependencies, not a complete uninitialized-bit proof.'})
    result={'status':'PASS_NATIVE_HEVC_BODY_PURE_CALLEES_AND_ROM_TABLE_WITH_EXPLICIT_ADDRESS_GAP',
            'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'source_receipt':{'script_sha256':im.sha(Path(__file__).read_bytes()),
                              'prior_manifest_sha256':PRIOR_SHA,'stage50_result_sha256':prev.SOURCE_SHA,
                              'VCD_sha256':im.sha(blob)},
            'GP_evidence':{'entry':'0x8000930c','two_instructions_hex':blob[0x930c:0x9314].hex(),
                           'native_GP':hex(GP),'ROM_table_offset':'0x248910','ROM_table5_hex':'0001040203',
                           'boot_GP_is_different_and_not_used':True,'hardware_startup_executed':False},
            'dialect_reference':{'url':'https://fuchsia.googlesource.com/third_party/binutils-gdb/+/refs/tags/gdb-16.1-release/opcodes/mips-opc.c',
                                 'blob':'7b1aa5f71a0816ef3fac036ee260a8b1acbac703',
                                 'observation':'0x0000001c MADD and 0x70000026 MTIC match Allegrex-family opcode entries; no processor identity or hardware-state inference.',
                                 'ISA_extensions_or_interrupt_instructions_executed':False},
            'cases':cases,'old_seed_dependency_pairs':pairs,
            'bounded_phases':sum(len(c['events']) for c in cases),
            'scope':'Independent constructor/common/prefix/body/GOP entries in declared RAM. All body helper returns native. '
                    'A0 output address explicitly supplied after unexecuted MFLO; request bytes5/6 are fixtures, not captured Start bytes. '
                    'No full conversion, actual address translation, timing, current MAIN, hardware or recovery.',
            'Windows_UU_camera_operations':False,'goal_complete':False,'persistent_write_release':False}
    out.mkdir();im.write_json(out/'native-body-results.json',result)
    (out/'executed-source.py').write_bytes(Path(__file__).read_bytes())
    print(json.dumps({'status':result['status'],'cases':len(cases),'phases':result['bounded_phases'],
                      'retained_dependency_bytes_in_first_pair':len(pairs[0]['old_seed_dependency_xor_by_offset']),
                      'output':str(out)}))


if __name__=='__main__':main()
