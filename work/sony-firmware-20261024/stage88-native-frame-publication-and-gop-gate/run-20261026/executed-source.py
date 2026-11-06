#!/usr/bin/env python3
"""Native parent-record publication -> HEVC gate writer -> gated output copy.

Parent record/payload and object ownership are declared RAM inputs. No real
message receipt, common callback, virtual predicate, allocation or ACK faked.
"""
from pathlib import Path
import argparse
import datetime
import json
import struct
import sys

STAGE=Path(__file__).resolve().parent
BASE,ROOT=STAGE.parent,STAGE.parent.parents[1]
sys.path.insert(0,str(BASE/'stage87-native-frame-state-command-bit'))
import frame_command as old
im,u,reg,cs,IMAGE=old.im,old.u,old.reg,old.cs,old.IMAGE
PRIOR_SHA='00375ff2716f51c5c07f5f7a93e81a46bc2ad35518bf88c6628f1faced682fa9'
GOP_PA,GOP=0x01200000,0x81200000
INFRAME_PA,INFRAME=0x01300000,0x81300000
OUTFRAME_PA,OUTFRAME=0x01400000,0x81400000
OUTPACK_PA,OUTPACK=0x01500000,0x81500000
INPACK_PA,INPACK=0x01600000,0x81600000
DESC_PA,DESC=0x01700000,0x81700000
HANDLE_PA,HANDLE=0x01800000,0x81800000
MANAGER_PA,MANAGER=0x01a00000,0x81a00000
RECORD_PA,RECORD=0x01b00000,0x81b00000
BACKEND_PA,BACKEND=0x01c00000,0x81c00000
PAYLOAD_PA,PAYLOAD=0x01d00000,0x81d00000
STACK_PA,SP=0x02000000,0x82008000
LIMITS=((0x141128,0x141244),(0x1417c8,0x141814),(0x14140c,0x14150c),
        (0x1415ec,0x141664),(0x19a890,0x19a89c),
        (0xd9000,0xd9110),(0xd95a4,0xd95c8),(0xd96a4,0xd9748),(0xd9820,0xd98b8))
STOPS={0x141664:'after_native_parent_payload_copy_before_other_work',
       0x141668:'parent_event_bit4_off_before_other_work',
       0x14150c:'before_unknown_GP_input_buffer_allocation',
       0xd9110:'native_GOP_gate_set_before_unexecuted_virtual_predicate',
       0xd9204:'input_frame_bit4_off_before_other_backend_updates',
       0xd95c8:'before_unknown_GP_output_buffer_allocation',
       0xd98b8:'after_gated_copy_publication_and_source_gate_clear_before_epilogue',
       0xd98c0:'closed_GOP_gate_before_outer_epilogue'}


def word(b,o):return struct.unpack_from('<I',b,o)[0]


def declared_metadata(gop):
    # Explicit constructed input, not an actual module reply. The selected
    # fields mirror this captured trial's current geometry/mode/slice values;
    # unclassified bytes are declared zero and their acceptance is not claimed.
    m=bytearray(48)
    m[0:4]=gop[0x7c:0x80]
    m[5]=(word(gop,0x84)>>15)&1;m[6]=gop[0x8b]
    m[8:12]=gop[0xe0:0xe4];m[12]=word(gop,0xd8)&15
    m[16:48]=gop[0xf4:0x114]
    return bytes(m)


class Guest:
    def __init__(self,blob,source,event,on_input=True,on_output=True):
        self.blob=blob;self.gop=bytes.fromhex(source['GOP_after_hex'])
        assert len(self.gop)==4096 and word(self.gop,0xe8)&1==0
        self.metadata=declared_metadata(self.gop)
        self.uc=u.Uc(u.UC_ARCH_MIPS,u.UC_MODE_MIPS32|u.UC_MODE_LITTLE_ENDIAN)
        self.uc.ctl_set_cpu_model(reg.UC_CPU_MIPS32_24KC)
        self.md=cs.Cs(cs.CS_ARCH_MIPS,cs.CS_MODE_MIPS32|cs.CS_MODE_LITTLE_ENDIAN)
        self.initial={}
        rw=u.UC_PROT_READ|u.UC_PROT_WRITE;ro=u.UC_PROT_READ
        for at,size,prot in ((0,(len(blob)+4095)&-4096,ro|u.UC_PROT_EXEC),
            (GOP_PA,4096,rw),(INFRAME_PA,4096,rw),(OUTFRAME_PA,4096,rw),
            (INPACK_PA,4096,rw),(OUTPACK_PA,4096,rw),(DESC_PA,4096,ro),
            (HANDLE_PA,4096,ro),(MANAGER_PA,4096,rw),(RECORD_PA,4096,ro),
            (BACKEND_PA,4096,ro),(PAYLOAD_PA,4096,ro),(STACK_PA,65536,rw)):
            self.uc.mem_map(at,size,prot)
        self.uc.mem_write(0,blob)
        iframe=bytearray([0x91])*4096;iframe[0x4c4]=0
        struct.pack_into('<I',iframe,0x4c8,HANDLE+4 if on_input else 0)
        oframe=bytearray([0x92])*4096;oframe[0x4c4]=0
        struct.pack_into('<I',oframe,0x4c8,HANDLE+8 if on_output else 0)
        desc=bytearray([0xe1])*4096;struct.pack_into('<I',desc,0x10,HANDLE)
        handles=struct.pack('<4I',INFRAME_PA,INPACK_PA,OUTPACK_PA,PAYLOAD_PA)+bytes(4080)
        manager=bytearray([0x5a])*4096
        struct.pack_into('<II',manager,0xc8c,BACKEND,RECORD);struct.pack_into('<H',manager,0xca0,0x1234)
        record=bytearray([0x6b])*4096;record[0]=event;struct.pack_into('<I',record,4,HANDLE+12)
        backend=bytearray([0x3c])*4096;struct.pack_into('<I',backend,0x28,0)
        payload=bytearray([0xd2])*4096;payload[0xec:0x11c]=self.metadata
        for at,b in ((GOP_PA,self.gop),(INFRAME_PA,iframe),(OUTFRAME_PA,oframe),
            (INPACK_PA,bytes([0xb6])*4096),(OUTPACK_PA,bytes([0xc4])*4096),
            (DESC_PA,desc),(HANDLE_PA,handles),(MANAGER_PA,manager),(RECORD_PA,record),
            (BACKEND_PA,backend),(PAYLOAD_PA,payload)):
            self.initial[at]=bytes(b);self.uc.mem_write(at,bytes(b))
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
        assert ins.mnemonic not in {'syscall','break','cache','sync','mfc0','mtc0','eret',
            'wait','tlbwi','tlbwr','tlbr','tlbp','jalr'},(hex(pc),ins.mnemonic)

    def read(self,at):return bytes(self.uc.mem_read(at,4096))

    def run(self,label,entry,**regs):
        for name,value in {'sp':SP,'ra':0x83000000,**regs}.items():
            self.uc.reg_write(getattr(reg,'UC_MIPS_REG_'+name.upper()),value)
        self.reason=None;self.pcs=[];self.interrupts=[]
        self.uc.emu_start(IMAGE+entry,0,timeout=1000000,count=0)
        assert self.reason in STOPS.values() and not self.interrupts,self.reason
        assert bytes(self.uc.mem_read(0,len(self.blob)))==self.blob
        assert bytes(self.uc.mem_read(STACK_PA,65536))==bytes([0xd7])*65536
        assert self.uc.reg_read(reg.UC_MIPS_REG_SP)==SP
        for at in (DESC_PA,HANDLE_PA,MANAGER_PA,RECORD_PA,BACKEND_PA,PAYLOAD_PA):
            assert self.read(at)==self.initial[at]
        return {'label':label,'entry':hex(IMAGE+entry),'stop':self.reason,
                'pc':hex(self.uc.reg_read(reg.UC_MIPS_REG_PC)),
                'CODE_observed_PCs':[hex(x) for x in self.pcs],
                'original_image_and_all_declared_parent_inputs_unchanged':True,
                'entire_declared_stack_unchanged':True,
                'memory_read_write_hooks_installed':False,'native_interrupts':self.interrupts,
                'PC_observation_may_include_annulled_delay_slots':True,
                'MMIO_code_replacement_or_fake_return':False}


def one(blob,source,event,kind):
    m=Guest(blob,source,event,kind!='missing_input_handle',kind!='missing_output_handle')
    want_iframe=bytearray(m.initial[INFRAME_PA]);want_oframe=bytearray(m.initial[OUTFRAME_PA])
    want_in=bytearray(m.initial[INPACK_PA]);want_out=bytearray(m.initial[OUTPACK_PA]);want_gop=bytearray(m.gop)
    events=[]
    events.append(m.run('original backend predicate and parent record publication checks',0x141128,s2=MANAGER,s4=DESC))
    struct.pack_into('<H',want_iframe,0xe0,0x1234)
    if event&0x10:want_iframe[0x4c4]|=0x10
    missing_input=kind=='missing_input_handle' and bool(event&0x10)
    if missing_input:
        assert events[-1]['stop']=='before_unknown_GP_input_buffer_allocation'
    elif event&0x10:
        assert events[-1]['stop']=='after_native_parent_payload_copy_before_other_work'
        want_in[0xec:0x11c]=m.metadata
    else:assert events[-1]['stop']=='parent_event_bit4_off_before_other_work'
    assert m.read(INFRAME_PA)==bytes(want_iframe) and m.read(INPACK_PA)==bytes(want_in)
    assert m.read(GOP_PA)==bytes(want_gop) and m.read(OUTFRAME_PA)==bytes(want_oframe) and m.read(OUTPACK_PA)==bytes(want_out)
    snapshots=[{'phase':'parent_publication','GOP_gate':bool(word(want_gop,0xe8)&1),
                'input_frame_flag4':bool(want_iframe[0x4c4]&0x10),'input_payload_copied':bool(event&0x10) and not missing_input}]
    if not missing_input:
        events.append(m.run('original HEVC input metadata ingestion and gate writer after unexecuted common callback',
                            0xd9000,s0=GOP,s3=INFRAME))
        if event&0x10:
            assert events[-1]['stop']=='native_GOP_gate_set_before_unexecuted_virtual_predicate'
            want_gop[0xbf4:0xc24]=m.metadata;want_gop[0x7c:0x80]=m.metadata[:4]
            struct.pack_into('<I',want_gop,0x84,(word(want_gop,0x84)&~(1<<15))|((m.metadata[5]&1)<<15))
            want_gop[0x8b]=m.metadata[6];want_gop[0xe0:0xe4]=m.metadata[8:12]
            struct.pack_into('<I',want_gop,0xd8,(word(want_gop,0xd8)&~15)|(m.metadata[12]&15))
            struct.pack_into('<I',want_gop,0xe8,word(want_gop,0xe8)|1)
            want_gop[0xf4:0x114]=m.metadata[16:48]
        else:assert events[-1]['stop']=='input_frame_bit4_off_before_other_backend_updates'
        assert m.read(GOP_PA)==bytes(want_gop)
        assert m.read(INFRAME_PA)==bytes(want_iframe) and m.read(INPACK_PA)==bytes(want_in)
        snapshots.append({'phase':'native_HEVC_ingestion','GOP_gate':bool(word(want_gop,0xe8)&1)})
        before_pack=bytes(want_gop)
        events.append(m.run('original GOP gate and existing output-handle check through copy and clear',
                            0xd95a4,s1=GOP,s2=OUTFRAME))
        copied=bool(event&0x10) and kind!='missing_output_handle'
        if copied:
            assert events[-1]['stop']=='after_gated_copy_publication_and_source_gate_clear_before_epilogue'
            want_out[0x14:0xb0]=want_gop[0x78:0x114];want_out[0xec:0x11c]=want_gop[0xbf4:0xc24]
            want_oframe[0x4c4]|=0x10
            struct.pack_into('<I',want_gop,0xe8,word(want_gop,0xe8)&~1)
            assert word(want_out,0x84)&1==1 and word(want_out,0x64)==word(m.gop,0xc8)
        elif event&0x10:
            assert events[-1]['stop']=='before_unknown_GP_output_buffer_allocation'
        else:assert events[-1]['stop']=='closed_GOP_gate_before_outer_epilogue'
        assert m.read(GOP_PA)==bytes(want_gop) and m.read(OUTFRAME_PA)==bytes(want_oframe) and m.read(OUTPACK_PA)==bytes(want_out)
        assert m.read(INFRAME_PA)==bytes(want_iframe) and m.read(INPACK_PA)==bytes(want_in)
        snapshots.append({'phase':'gated_output_copy','GOP_gate':bool(word(want_gop,0xe8)&1),
                          'output_publication_flag4':bool(want_oframe[0x4c4]&0x10),'copied156_and48':copied})
    else:before_pack=None;copied=False
    return {'seed':source['seed'],'source_kind':source['kind'],'source_label':source['source_label'],
            'declared_parent_event_byte':event,'kind':kind,'declared_metadata48_hex':m.metadata.hex(),
            'source_GOP_hex':m.gop.hex(),'GOP_before_pack_hex':before_pack.hex() if before_pack else None,
            'GOP_after_hex':bytes(want_gop).hex(),'input_frame_after_hex':bytes(want_iframe).hex(),
            'input_packet_after_hex':bytes(want_in).hex(),'output_frame_after_hex':bytes(want_oframe).hex(),
            'output_packet_after_hex':bytes(want_out).hex(),'snapshots':snapshots,'events':events,
            'native_gates_not_host_set_on_GOP_or_frames':True,
            'decoded_output_target':old.prev.a.prev.p.a.decode(word(want_out,0x64)) if copied else None,
            'actual_parent_record_production_common_and_virtual_callbacks_lifetime_dispatch_or_MAIN':False,
            'real_allocation_ownership_ACK_hardware_or_recovery':False}


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',required=True);out=Path(parser.parse_args().output)
    im.volume();assert not out.exists()
    prior=BASE/'stage87-native-frame-state-command-bit/final-receipt.json';assert im.sha(prior.read_bytes())==PRIOR_SHA
    for r in json.loads(prior.read_text())['files']:
        raw=(ROOT/r['path']).read_bytes();assert len(raw)==r['bytes'] and im.sha(raw)==r['sha256']
    assert (STAGE/'goal-status-before.json').read_bytes()==(BASE/'GOAL_STATUS.json').read_bytes()
    source_path=BASE/'stage86-hevc-vui-mode-conversion/run-20261026/vui-mode-results.json'
    sources=json.loads(source_path.read_text())['cases']
    blob=old.prev.a.prev.p.a.v.VCD_PATH.read_bytes();assert im.sha(blob)==im.PINS[str(old.prev.a.prev.p.a.v.VCD_PATH.relative_to(BASE))]
    get=lambda seed,kind:next(c for c in sources if c['seed']==seed and c['kind']==kind and c['source_label']=='selected1_raw5')
    cases=[one(blob,get(seed,k),event,'normal') for seed in (0xa5,0xc3) for k in ('captured','target20M') for event in (0,0x10)]
    cases += [one(blob,get(seed,'captured'),0x10,k) for seed in (0xa5,0xc3) for k in ('missing_input_handle','missing_output_handle')]
    result={'status':'PASS_NATIVE_PARENT_PUBLICATION_HEVC_GATE_SET_AND_GATED_COPY_CLEAR',
            'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'source_receipt':{'script_sha256':im.sha(Path(__file__).read_bytes()),'VCD_sha256':im.sha(blob),
                              'prior_manifest_sha256':PRIOR_SHA,'stage86_result_sha256':im.sha(source_path.read_bytes())},
            'cases':cases,'bounded_phases':sum(len(c['events']) for c in cases),
            'scope':'Declared backend-empty manager, event record, constructed metadata48 and owned handles. '
                    'Native publisher sets input flag; HEVC gate writer then actual gate check/copy clears it. '
                    'Entries remain after unexecuted common/virtual/ownership paths, with two declared frame objects; '
                    'no real module record, allocation, scheduling, ACK, MAIN or hardware proof.',
            'Windows_UU_camera_operations':False,'goal_complete':False,'persistent_write_release':False}
    out.mkdir();im.write_json(out/'gate-event-results.json',result)
    (out/'executed-source.py').write_bytes(Path(__file__).read_bytes())
    print(json.dumps({'status':result['status'],'cases':len(cases),'bounded_phases':result['bounded_phases'],
                      'output':str(out)}))


if __name__=='__main__':main()
