#!/usr/bin/env python3
"""Bounded original HEVC config fields, from captured builder bytes.

Independent original fragments; no complete initialization, MMIO value,
multiply-accumulate instruction, call return or hardware completion invented.
"""
from pathlib import Path
import argparse
import datetime
import json
import struct
import sys

STAGE=Path(__file__).resolve().parent
BASE,ROOT=STAGE.parent,STAGE.parent.parents[1]
sys.path.insert(0,str(BASE/'stage80-vcd-pending-and-timing'))
import pending_timing as p
im,u,reg,cs,IMAGE=p.im,p.u,p.reg,p.cs,p.IMAGE
SOURCE=BASE/'stage50-native-start-geometry/run-corrected-20261025/start-geometry-results.json'
SOURCE_SHA='62b66fd3d48ebc6db8afdb0c6eb95303ab3dd18b374c70436f6725310c16900d'
PRIOR_SHA='672b2c7a8144c5f2ff15595ef30ea5ecb377819edbe9f48dab4dc2864fabfc4e'
INPUT_PA,COMMON,CODEC=0x01000000,0x81000000,0x81000100
CONFIG_PA,CONFIG,GOP_PA,GOP=0x01100000,0x81100000,0x01200000,0x81200000
STACK_PA,SP=0x02000000,0x82008000
LIMITS=((0x18cd8c,0x18cdf4),(0x18d144,0x18d1c8),(0xd866c,0xd8718))
STOPS={0x18cdf4:'before_chroma_helper',0x18d1c8:'after_three_rate_words',
       0xd8718:'after_GOP_copy_before_base_helper',0x67ce4:'before_original_assertion_runtime'}


def get32(b,o):return struct.unpack_from('<I',b,o)[0]


class Guest:
    def __init__(self,blob,common,codec,seed):
        self.blob=blob
        self.uc=u.Uc(u.UC_ARCH_MIPS,u.UC_MODE_MIPS32|u.UC_MODE_LITTLE_ENDIAN)
        self.uc.ctl_set_cpu_model(reg.UC_CPU_MIPS32_24KC)
        self.md=cs.Cs(cs.CS_ARCH_MIPS,cs.CS_MODE_MIPS32|cs.CS_MODE_LITTLE_ENDIAN)
        for at,size,prot in ((0,(len(blob)+4095)&-4096,u.UC_PROT_READ|u.UC_PROT_EXEC),
                             (INPUT_PA,4096,u.UC_PROT_READ),
                             (CONFIG_PA,4096,u.UC_PROT_READ|u.UC_PROT_WRITE),
                             (GOP_PA,4096,u.UC_PROT_READ|u.UC_PROT_WRITE),
                             (STACK_PA,65536,u.UC_PROT_READ|u.UC_PROT_WRITE)):
            self.uc.mem_map(at,size,prot)
        self.uc.mem_write(0,blob)
        self.input=common+bytes(256-len(common))+codec+bytes(4096-256-len(codec))
        self.uc.mem_write(INPUT_PA,self.input)
        self.uc.mem_write(CONFIG_PA,bytes([seed])*4096)
        self.uc.mem_write(GOP_PA,bytes([0xb6])*4096)
        self.uc.mem_write(STACK_PA,bytes([0xd7])*65536)
        self.uc.hook_add(u.UC_HOOK_CODE,self.code)
        self.uc.hook_add(u.UC_HOOK_MEM_INVALID,self.invalid)

    def invalid(self,uc,access,at,size,value,user):
        self.reason='invalid:'+hex(at);uc.emu_stop();return False

    def code(self,uc,pc,size,user):
        self.pcs.append(pc)
        off=pc-IMAGE
        if off in STOPS:
            self.reason=STOPS[off];uc.emu_stop();return
        assert len(self.pcs)<2000
        assert any(lo<=off and off+size<=hi for lo,hi in LIMITS),(hex(pc),size)
        ins=next(self.md.disasm(self.blob[off:off+size],pc),None)
        assert ins is not None and ins.mnemonic not in {
            'syscall','break','cache','sync','mfc0','mtc0','eret','wait',
            'tlbwi','tlbwr','tlbr','tlbp','jalr'}

    def run(self,label,entry,**regs):
        for name,val in {'sp':SP,'ra':0x83000000,**regs}.items():
            self.uc.reg_write(getattr(reg,'UC_MIPS_REG_'+name.upper()),val)
        stack=bytes(self.uc.mem_read(STACK_PA,65536))
        # Independent entry. If the GOP callee opens a frame, check its actual
        # saved slots; never synthesize a matching epilogue or base-helper return.
        expected_stack=bytearray(stack)
        if entry==0xd866c:
            for o,r in ((0x10,'s0'),(0x14,'s1'),(0x18,'ra')):
                struct.pack_into('<I',expected_stack,SP-IMAGE-STACK_PA-0x20+o,
                                 self.uc.reg_read(getattr(reg,'UC_MIPS_REG_'+r.upper())))
        self.reason=None;self.pcs=[]
        self.uc.emu_start(IMAGE+entry,0,timeout=1000000,count=0)
        assert self.reason in STOPS.values(),self.reason
        assert bytes(self.uc.mem_read(0,len(self.blob)))==self.blob
        assert bytes(self.uc.mem_read(INPUT_PA,4096))==self.input
        assert bytes(self.uc.mem_read(STACK_PA,65536))==bytes(expected_stack)
        assert self.uc.reg_read(reg.UC_MIPS_REG_SP)==SP-(0x20 if entry==0xd866c else 0)
        return {'label':label,'entry':hex(IMAGE+entry),'stop':self.reason,
                'pc':hex(self.uc.reg_read(reg.UC_MIPS_REG_PC)),
                'pcs':[hex(x) for x in self.pcs],
                'original_image_and_readonly_input_unchanged':True,
                'complete_stack_matches_only_native_prologue_stores':True,
                'memory_read_write_hooks_installed':False,
                'return_or_MMIO_adapter':False}


def case(blob,source,seed,control):
    common=bytearray.fromhex(source['common_hex']);codec=bytearray.fromhex(source['codec_hex'])
    assert len(common)==64 and len(codec)==448 and codec[0]==2
    edits=[]
    if control=='target20M':
        old=codec[0x2c:0x30].hex();struct.pack_into('<I',codec,0x2c,((20000000//64)-1)<<8)
        edits.append({'buffer':'codec','offset':'0x2c','before':old,'after':codec[0x2c:0x30].hex()})
    elif control in ('width_guard','height_guard'):
        off,blocks=(0xc,541) if control=='width_guard' else (0x10,513)
        old=common[off:off+4].hex();struct.pack_into('<I',common,off,blocks*16)
        edits.append({'buffer':'common','offset':hex(off),'before':old,'after':common[off:off+4].hex()})
    else:assert control is None
    m=Guest(blob,bytes(common),bytes(codec),seed)
    expected=bytearray([seed])*4096
    first=m.run('independent native HEVC geometry packing',0x18cd8c,
                s1=CONFIG,s2=COMMON,s3=CODEC+0x18)
    expected[0x34:0x37]=codec[0x1f:0x22];expected[0x37]=0
    width=sum(get32(common,o) for o in (0xc,0x14,0x18))
    height=sum(get32(common,o) for o in (0x10,0x1c,0x20))
    geometry=(((width+15)&0xffffffff)>>4)-1,(((height+15)&0xffffffff)>>4)-1
    struct.pack_into('<HH',expected,0x38,*(x&65535 for x in geometry))
    assert bytes(m.uc.mem_read(CONFIG_PA,4096))==bytes(expected)
    assert bytes(m.uc.mem_read(GOP_PA,4096))==bytes([0xb6])*4096
    second=m.run('independent native HEVC three rate-word packing',0x18d144,s1=CONFIG,s3=CODEC+0x18)
    for dest,src in ((0x80,0x30),(0x84,0x2c),(0x88,0x34)):
        expected[dest:dest+4]=codec[src:src+4]
    struct.pack_into('<I',expected,0x8c,get32(expected,0x8c)&~7)
    assert bytes(m.uc.mem_read(CONFIG_PA,4096))==bytes(expected)
    assert bytes(m.uc.mem_read(GOP_PA,4096))==bytes([0xb6])*4096
    third=m.run('independent original GOP constructor validates and copies classified fields',
                0xd866c,a0=GOP,a1=CONFIG)
    good=geometry[0]<540 and geometry[1]<512
    want=bytearray([0xb6])*4096
    if good:
        assert third['stop']=='after_GOP_copy_before_base_helper'
        want[0x78:0x114]=expected[0x34:0xd0]
        assert get32(want,0xc8)==get32(codec,0x2c)
    else:assert third['stop']=='before_original_assertion_runtime'
    assert bytes(m.uc.mem_read(CONFIG_PA,4096))==bytes(expected)
    assert bytes(m.uc.mem_read(GOP_PA,4096))==bytes(want)
    return {'source_label':source['label'],'seed':seed,'declared_control':control,
            'source_edits':edits,'source_stage50_original_codec_sha256':im.sha(bytes.fromhex(source['codec_hex'])),
            'common_input_hex':common.hex(),'codec_input_hex':codec.hex(),
            'geometry_pixel_sums':[width,height],'packed_block_counts_minus_one':list(geometry),
            'native_GOP_copy_accepted':good,'decoded_target_input':p.a.decode(get32(codec,0x2c)),
            'decoded_GOP_target':p.a.decode(get32(want,0xc8)) if good else None,
            'config_after_hex':expected.hex(),'GOP_after_hex':want.hex(),
            'events':[first,second,third],
            'three_independent_entries_not_one_full_initialization':True,
            'other_unclassified_bytes_are_declared_old_values':True,
            'full_valid_request_current_MAIN_hardware_or_recovery':False}


def main():
    args=argparse.ArgumentParser();args.add_argument('--output',required=True);out=Path(args.parse_args().output)
    im.volume();assert not out.exists();assert im.sha(SOURCE.read_bytes())==SOURCE_SHA
    prior=BASE/'stage82-hevc-frame-parameter-handoff/final-receipt.json'
    assert im.sha(prior.read_bytes())==PRIOR_SHA
    for f in json.loads(prior.read_text())['files']:
        raw=(ROOT/f['path']).read_bytes();assert len(raw)==f['bytes'] and im.sha(raw)==f['sha256']
    assert (STAGE/'goal-status-before.json').read_bytes()==(BASE/'GOAL_STATUS.json').read_bytes()
    blob=p.a.v.VCD_PATH.read_bytes();assert im.sha(blob)==im.PINS[str(p.a.v.VCD_PATH.relative_to(BASE))]
    sources=json.loads(SOURCE.read_text())['cases'][:3]
    assert [x['label'] for x in sources]==['selected1_raw5','selected1_raw6','selected1_unrelated_row_changed']
    cases=[case(blob,x,seed,control) for seed in (0xa5,0xc3) for x in sources for control in (None,'target20M')]
    cases += [case(blob,sources[0],seed,control) for seed in (0xa5,0xc3) for control in ('width_guard','height_guard')]
    text_ranges=[(0x18ba74,0x18ba94),(0x18bd60,0x18bda0),(0x18cd34,0x18ce00),
                 (0x18bca4,0x18bcb4),(0x18d144,0x18d1c8),(0xd866c,0xd8720)]
    disasm=[]
    md=cs.Cs(cs.CS_ARCH_MIPS,cs.CS_MODE_MIPS32|cs.CS_MODE_LITTLE_ENDIAN)
    for lo,hi in text_ranges:
        for off in range(lo,hi,4):
            ins=list(md.disasm(blob[off:off+4],IMAGE+off))
            disasm.append({'offset':hex(off),'bytes':blob[off:off+4].hex(),
                           'text':' ; '.join(z.mnemonic+' '+z.op_str for z in ins) or 'UNDECODED_NOT_EXECUTED'})
    result={'status':'PASS_BOUNDED_NATIVE_HEVC_INITIAL_GEOMETRY_RATE_TO_GOP_FIELDS',
            'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'source_receipt':{'script_sha256':im.sha(Path(__file__).read_bytes()),
                              'VCD_sha256':im.sha(blob),'stage50_result_sha256':SOURCE_SHA,
                              'prior_manifest_sha256':PRIOR_SHA},
            'dispatch_static':{'raw_codec_type2_primary_converter':'0x8018cc74',
                                'raw_codec_type1_primary_converter':'0x8018d8cc',
                                'type2_subsequent_profile_converter':'0x8018d62c',
                                'not_executed':['MMIO 0xbe000064','undecoded multiply-accumulate words',
                                                'full initial converter','runtime assertion and base helper']},
            'field_mapping':{'target':['raw codec +0x2c','HEVC initial config +0x84','GOP +0xc8'],
                             'geometry':'sum baseband dimensions and padding; ceil(sum/16)-1; config+0x38/+0x3a'},
            'cases':cases,'bounded_phases':sum(len(x['events']) for x in cases),
            'original_instruction_disassembly_per_word':disasm,
            'scope':'Captured stage50 fixture builder output, not a real-camera capture or current compiled writer. '
                    'Declared independent fragment entries and trial old output bytes, not a complete initialization or valid hardware request.',
            'Windows_UU_camera_operations':False,'goal_complete':False,'persistent_write_release':False}
    out.mkdir();im.write_json(out/'config-field-results.json',result)
    (out/'executed-source.py').write_bytes(Path(__file__).read_bytes())
    print(json.dumps({'status':result['status'],'cases':len(cases),'phases':result['bounded_phases'],
                      'output':str(out)},ensure_ascii=False))


if __name__=='__main__':main()
