#!/usr/bin/env python3
"""Declared object graph, native frame boolean and command-bit consumption.

The GOP gate remains zero. The copy-only post-gate entry is explicitly an
analysis input assembly, not evidence that real dispatch reaches it.
"""
from pathlib import Path
import argparse
import datetime
import json
import struct
import sys

STAGE=Path(__file__).resolve().parent
BASE,ROOT=STAGE.parent,STAGE.parent.parents[1]
sys.path.insert(0,str(BASE/'stage86-hevc-vui-mode-conversion'))
import vui_mode as prev
im,u,reg,cs,IMAGE=prev.im,prev.u,prev.reg,prev.a.cs,prev.IMAGE
PRIOR_SHA='98bc21668344a77d70e42e00ca06c3adc35e7668da23026f85c48dc4528d4cd1'
GOP_PA,GOP=0x01200000,0x81200000
FRAME_PA,FRAME=0x01300000,0x81300000
OWNER_PA,OWNER=0x01400000,0x81400000
PACK_PA,PACK=0x01500000,0x81500000
META_PA,META=0x01600000,0x81600000
CMD_PA,CMD=0x01700000,0x81700000
HANDLE_PA,HANDLE=0x01800000,0x81800000
STACK_PA,PRODUCER_SP,COMMAND_SP=0x02000000,0x82006000,0x8200a000
STOP_PA,STOP=0x03000000,0x83000000
DATA=CMD+0x2c04
LIMITS=((0x1351b0,0x1351c0),(0x131818,0x131888),(0x131ac0,0x131afc),
        (0xd96a4,0xd9738),(0x15d30c,0x15d3d4),(0x15d7b4,0x15d7d4),
        (0x15e360,0x15e544))
STOPS={0x131888:'native_frame_handle_resolved_before_other_header_work',
       0x131afc:'after_native_frame_boolean_store_before_other_work',
       0xd9738:'after_copy156_before_other_frame_metadata',
       0x15d3d4:'native_command_frame_and_buffer_links_before_unexecuted_middle',
       0x15d7d4:'after_native_command_leaf_return_before_other_helpers'}


def word(b,o):return struct.unpack_from('<I',b,o)[0]


class Guest:
    def __init__(self,blob,source,raw_flag,legacy_u16):
        self.blob=blob;self.source=source
        self.uc=u.Uc(u.UC_ARCH_MIPS,u.UC_MODE_MIPS32|u.UC_MODE_LITTLE_ENDIAN)
        self.uc.ctl_set_cpu_model(reg.UC_CPU_MIPS32_24KC)
        self.md=cs.Cs(cs.CS_ARCH_MIPS,cs.CS_MODE_MIPS32|cs.CS_MODE_LITTLE_ENDIAN)
        maps=((0,(len(blob)+4095)&-4096,u.UC_PROT_READ|u.UC_PROT_EXEC),
              (GOP_PA,4096,u.UC_PROT_READ),(FRAME_PA,4096,u.UC_PROT_READ|u.UC_PROT_WRITE),
              (OWNER_PA,4096,u.UC_PROT_READ|u.UC_PROT_WRITE),(PACK_PA,4096,u.UC_PROT_READ|u.UC_PROT_WRITE),
              (META_PA,4096,u.UC_PROT_READ),(CMD_PA,0x9000,u.UC_PROT_READ|u.UC_PROT_WRITE),
              (HANDLE_PA,4096,u.UC_PROT_READ),(STACK_PA,65536,u.UC_PROT_READ|u.UC_PROT_WRITE),
              (STOP_PA,4096,u.UC_PROT_READ|u.UC_PROT_EXEC))
        for at,size,prot in maps:self.uc.mem_map(at,size,prot)
        self.uc.mem_write(0,blob)
        self.gop=bytes.fromhex(source['GOP_after_hex']);assert len(self.gop)==4096 and word(self.gop,0xe8)&1==0
        self.uc.mem_write(GOP_PA,self.gop)
        self.frame=bytearray([0x91])*4096;self.frame[0x4c4]=0;struct.pack_into('<I',self.frame,0x4c8,HANDLE+4)
        self.owner=bytearray([0x72])*4096;self.owner[0x36]=raw_flag
        self.packet=bytes([0xb6])*4096
        self.meta=bytearray([0xed])*4096
        for at,value in ((0x10,0x01020304),(0x14,0x05060708),(0x18,0x090a0b0c),(0x110,HANDLE)):
            struct.pack_into('<I',self.meta,at,value)
        self.handles=struct.pack('<II',FRAME_PA,PACK_PA)+bytes(4088)
        self.command=bytearray([source['seed']])*0x9000
        struct.pack_into('<H',self.command,4+0x68,legacy_u16)
        for at,b in ((FRAME_PA,self.frame),(OWNER_PA,self.owner),(PACK_PA,self.packet),
                     (META_PA,self.meta),(HANDLE_PA,self.handles),(CMD_PA,self.command)):
            self.uc.mem_write(at,bytes(b))
        self.uc.mem_write(STACK_PA,bytes([0xd7])*65536)
        self.uc.hook_add(u.UC_HOOK_CODE,self.code)
        self.uc.hook_add(u.UC_HOOK_MEM_INVALID,self.invalid)
        self.uc.hook_add(u.UC_HOOK_INTR,self.interrupt)

    def invalid(self,uc,access,at,size,value,user):
        self.reason='invalid:'+hex(at);uc.emu_stop();return False

    def interrupt(self,uc,number,user):
        self.interrupts.append(number);self.reason='native_interrupt';uc.emu_stop()

    def code(self,uc,pc,size,user):
        self.pcs.append(pc);off=pc-IMAGE
        if off in STOPS:self.reason=STOPS[off];uc.emu_stop();return
        assert len(self.pcs)<20000
        assert any(lo<=off and off+size<=hi for lo,hi in LIMITS),(hex(pc),size)
        ins=next(self.md.disasm(self.blob[off:off+size],pc),None)
        assert ins is not None,(hex(pc),self.blob[off:off+size].hex())
        assert ins.mnemonic not in {'syscall','break','cache','sync','mfc0','mtc0',
                'eret','wait','tlbwi','tlbwr','tlbr','tlbp','jalr'},(hex(pc),ins.mnemonic)

    def run(self,label,entry,anchor,independent=False,**regs):
        values={'sp':anchor,'ra':STOP} if independent else {}
        for name,value in {**values,**regs}.items():
            self.uc.reg_write(getattr(reg,'UC_MIPS_REG_'+name.upper()),value)
        before=bytes(self.uc.mem_read(STACK_PA,65536));sp=self.uc.reg_read(reg.UC_MIPS_REG_SP)
        self.reason=None;self.pcs=[];self.interrupts=[]
        self.uc.emu_start(IMAGE+entry,0,timeout=2000000,count=0)
        assert self.reason in STOPS.values() and not self.interrupts,self.reason
        after=bytes(self.uc.mem_read(STACK_PA,65536))
        lo,hi=anchor-IMAGE-STACK_PA-0x400,anchor-IMAGE-STACK_PA+0x90
        assert before[:lo]==after[:lo] and before[hi:]==after[hi:]
        for at,b in ((0,self.blob),(GOP_PA,self.gop),(META_PA,bytes(self.meta)),(HANDLE_PA,self.handles)):
            assert bytes(self.uc.mem_read(at,len(b)))==b
        return {'label':label,'entry':hex(IMAGE+entry),'stop':self.reason,
                'pc':hex(self.uc.reg_read(reg.UC_MIPS_REG_PC)),
                'SP_before':hex(sp),'SP_after':hex(self.uc.reg_read(reg.UC_MIPS_REG_SP)),
                'independent_entry':independent,'CODE_observed_PCs':[hex(x) for x in self.pcs],
                'original_image_GOP_metadata_handles_unchanged':True,
                'stack_outside_this_entry_scratch_window_unchanged':True,
                'memory_read_write_hooks_installed':False,'native_interrupts':self.interrupts,
                'PC_observation_may_include_annulled_delay_slots':True,
                'MMIO_code_replacement_or_fake_return':False}


def one(blob,source,raw_flag,legacy_u16):
    m=Guest(blob,source,raw_flag,legacy_u16);events=[]
    events.append(m.run('original wrapper/frame producer prefix resolves declared frame handle',
                        0x1351b0,PRODUCER_SP,independent=True,a0=OWNER,a1=META+0x100,a2=META))
    assert m.uc.reg_read(reg.UC_MIPS_REG_S0)==FRAME and m.uc.reg_read(reg.UC_MIPS_REG_S1)==OWNER
    assert m.uc.reg_read(reg.UC_MIPS_REG_S4)==META
    assert m.uc.reg_read(reg.UC_MIPS_REG_SP)==PRODUCER_SP-0x80
    # Other producer header/format work is unexecuted. Bind its timestamp-source
    # address and literal input explicitly; keep native S0/S1/S4 and saved frame.
    events.append(m.run('original source-byte boolean and frame4da store',0x131ac0,
                        PRODUCER_SP,a1=META+0x10,a2=1))
    want_frame=bytearray(m.frame);want_frame[0x4da]=int(raw_flag!=0)
    want_owner=bytearray(m.owner)
    struct.pack_into('<IIIII',want_owner,0x80,0xd7d7d701,0x01020304,0x05060708,0x090a0b0c,0)
    assert bytes(m.uc.mem_read(FRAME_PA,4096))==bytes(want_frame)
    assert bytes(m.uc.mem_read(OWNER_PA,4096))==bytes(want_owner)
    producer_saved=bytes(m.uc.mem_read(PRODUCER_SP-IMAGE-0x80,0x80))
    # Explicit post-gate copy-only entry. The source gate and frame publication
    # flag are STILL ZERO: this is not a naturally dispatched frame update.
    events.append(m.run('independent post-gate copy assembles analysis packet only',0xd96a4,
                        COMMAND_SP,independent=True,s6=FRAME+0x4c4,s4=GOP+0x78,s2=FRAME))
    want_packet=bytearray(m.packet);want_packet[0x14:0xb0]=m.gop[0x78:0x114]
    assert bytes(m.uc.mem_read(PACK_PA,4096))==bytes(want_packet)
    events.append(m.run('original command prefix copies legacy image and resolves same frame/packet handles',
                        0x15d30c,COMMAND_SP,independent=True,a0=CMD,a1=FRAME+0x4c4,a2=FRAME,a3=0))
    assert m.uc.reg_read(reg.UC_MIPS_REG_S0)==PACK+0x14
    assert m.uc.reg_read(reg.UC_MIPS_REG_S5)==CMD and m.uc.reg_read(reg.UC_MIPS_REG_S6)==DATA
    assert word(bytes(m.uc.mem_read(COMMAND_SP-IMAGE-0x50+0x10,4)),0)==FRAME
    want_cmd=bytearray(m.command);want_cmd[0x2c04:0x5804]=m.command[4:0x2c04]
    struct.pack_into('<I',want_cmd,0,DATA)
    assert bytes(m.uc.mem_read(CMD_PA,0x9000))==bytes(want_cmd)
    before_cmd=bytes(want_cmd);before_packet=bytes(want_packet)
    # Original command middle is not run. Its S0/S5 and frame stack pointer
    # were genuinely produced by the prefix; legacy command fields are fixtures.
    events.append(m.run('original frame-bit overwrite and complete native command leaf return',
                        0x15d7b4,COMMAND_SP))
    struct.pack_into('<I',want_packet,0x84,(word(want_packet,0x84)&~2)|(int(raw_flag!=0)<<1))
    packet=bytes(m.uc.mem_read(PACK_PA,4096));command=bytes(m.uc.mem_read(CMD_PA,0x9000))
    assert packet==bytes(want_packet)
    allowed=set(range(0x2c04+0x778,0x2c04+0x790))
    assert all(x==y or i in allowed for i,(x,y) in enumerate(zip(before_cmd,command)))
    source=packet[0x14:0xb0]
    assert source[0x15]==1
    expected_bit13=bool(raw_flag) or legacy_u16==0x220
    assert bool(word(command,0x2c04+0x780)&0x2000)==expected_bit13
    assert bytes(m.uc.mem_read(FRAME_PA,4096))==bytes(want_frame)
    assert bytes(m.uc.mem_read(OWNER_PA,4096))==bytes(want_owner)
    assert bytes(m.uc.mem_read(PRODUCER_SP-IMAGE-0x80,0x80))==producer_saved
    assert m.uc.reg_read(reg.UC_MIPS_REG_SP)==COMMAND_SP-0x50
    assert word(packet,0x64)==word(m.gop,0xc8)
    assert want_frame[0x4c4]==0 and word(m.gop,0xe8)&1==0
    return {'source_label':m.source['source_label'],'source_kind':m.source['kind'],'seed':m.source['seed'],
            'raw_owner36_fixture':raw_flag,'normalized_frame4da':int(raw_flag!=0),
            'legacy_command_u16_68_fixture':legacy_u16,
            'producer_original_saved_frame_preserved_during_independent_command_entries':True,
            'frame_after_hex':bytes(want_frame).hex(),'owner_after_hex':bytes(want_owner).hex(),
            'packet_before_overwrite_hex':before_packet.hex(),'packet_after_hex':packet.hex(),
            'command_before_leaf_hex':before_cmd.hex(),'command_after_hex':command.hex(),
            'command_bit13_after':expected_bit13,'GOP_source_hex':m.gop.hex(),
            'GOP_gate_and_frame_publication_remain_zero':True,
            'decoded_target':prev.a.prev.p.a.decode(word(packet,0x64)),
            'events':events,
            'actual_source_owner36_producer_real_dispatch_or_complete_command_validity':False,
            'hardware_recording_or_recovery_proven':False}


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',required=True);out=Path(parser.parse_args().output)
    im.volume();assert not out.exists()
    prior=BASE/'stage86-hevc-vui-mode-conversion/final-receipt.json';assert im.sha(prior.read_bytes())==PRIOR_SHA
    for r in json.loads(prior.read_text())['files']:
        raw=(ROOT/r['path']).read_bytes();assert len(raw)==r['bytes'] and im.sha(raw)==r['sha256']
    assert (STAGE/'goal-status-before.json').read_bytes()==(BASE/'GOAL_STATUS.json').read_bytes()
    source_path=prior.parent/'run-20261026/vui-mode-results.json';sources=json.loads(source_path.read_text())['cases']
    blob=prev.a.prev.p.a.v.VCD_PATH.read_bytes();assert im.sha(blob)==im.PINS[str(prev.a.prev.p.a.v.VCD_PATH.relative_to(BASE))]
    get=lambda seed,kind:next(c for c in sources if c['seed']==seed and c['kind']==kind and c['source_label']=='selected1_raw5')
    cases=[one(blob,get(seed,'captured'),raw,width) for seed in (0xa5,0xc3)
           for raw in (0,1,2,255) for width in (0,0x220)]
    cases += [one(blob,get(seed,'target20M'),raw,0) for seed in (0xa5,0xc3) for raw in (0,1)]
    dependencies=[]
    for raw in (0,1):
        left,right=(next(c for c in cases if c['seed']==seed and c['source_kind']=='captured'
                         and c['raw_owner36_fixture']==raw and c['legacy_command_u16_68_fixture']==0) for seed in (0xa5,0xc3))
        aa,bb=(bytes.fromhex(c['packet_after_hex']) for c in (left,right))
        changed=[hex(i) for i,(x,y) in enumerate(zip(aa,bb)) if x!=y]
        assert changed==['0x56','0x57','0x76','0x77']
        dependencies.append({'raw_owner36':raw,'remaining_packet_seed_dependency_offsets':changed,
                             'entire_request_or_other_bits_proven_initialized':False})
    result={'status':'PASS_NATIVE_FRAME_BOOLEAN_TO_PARAMETER_OVERRIDE_AND_COMMAND_BIT',
            'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'source_receipt':{'script_sha256':im.sha(Path(__file__).read_bytes()),
                              'prior_result_sha256':im.sha(source_path.read_bytes()),
                              'prior_manifest_sha256':PRIOR_SHA,'VCD_sha256':im.sha(blob)},
            'cases':cases,'packet_old_seed_dependencies':dependencies,
            'bounded_phases':sum(len(c['events']) for c in cases),
            'scope':'Declared owner/frame/handle graph and timestamp/legacy-command inputs. Original prefixes resolve pointers; '
                    'native boolean store and command leaf operate on them. Copy entered independently AFTER unexecuted gate, '
                    'which remains0; producer middle and command middle are not executed. No real dispatcher/MAIN/hardware proof.',
            'Windows_UU_camera_operations':False,'goal_complete':False,'persistent_write_release':False}
    out.mkdir();im.write_json(out/'frame-command-results.json',result)
    (out/'executed-source.py').write_bytes(Path(__file__).read_bytes())
    print(json.dumps({'status':result['status'],'cases':len(cases),'bounded_phases':result['bounded_phases'],
                      'remaining_packet_seed_dependency_bytes':4,'output':str(out)}))


if __name__=='__main__':main()
