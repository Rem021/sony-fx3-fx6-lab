#!/usr/bin/env python3
"""Original gated HEVC frame-parameter copy and explicit sequential update.

Captured trial GOP/backend bytes are declared inputs, not initialized live
objects. The virtual predicate/outer callback and allocator remain unexecuted.
CODE-only observation preserves all source bytes, guards and stopping limits.
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
sys.path.insert(0,str(BASE/'stage81-hevc-qos-consumer-and-release'))
import hevc_consumer as q
p,im,u,reg,IMAGE=q.p,q.im,q.u,q.reg,q.IMAGE
GOP_PA,GOP=q.GOP_PA,q.GOP
FRAME_PA,FRAME=0x01300000,0x81300000
FH_PA,FH=0x01400000,0x81400000
PACK_PA=0x01500000


class Guest(q.Guest):
    def __init__(self,blob,source80,gop81,handle=True,closed=False):
        super().__init__(blob,source80)
        body=bytearray.fromhex(gop81['GOP_after_hex'])
        if closed:
            flags=struct.unpack_from('<I',body,0xe8)[0]&~1
            struct.pack_into('<I',body,0xe8,flags)
        self.uc.mem_write(GOP_PA,bytes(body))
        for at,prot in ((FRAME_PA,u.UC_PROT_READ|u.UC_PROT_WRITE),
                        (FH_PA,u.UC_PROT_READ),(PACK_PA,u.UC_PROT_READ|u.UC_PROT_WRITE)):
            self.uc.mem_map(at,4096,prot)
        frame=bytearray([source80['seed']])*4096
        frame[0x4c4]=0
        struct.pack_into('<I',frame,0x4c8,FH if handle else 0)
        self.uc.mem_write(FRAME_PA,bytes(frame))
        self.uc.mem_write(FH_PA,struct.pack('<I',PACK_PA))
        self.uc.mem_write(PACK_PA,bytes([0xb6])*4096)

    def code(self,uc,pc,size,user):
        self.pcs.append(pc)
        if len(self.pcs)>20000:return self.stop('boundary: instruction_limit')
        if pc==p.STOP:return self.stop('returned')
        limits={0xd95c8:'before_unknown_GP_frame_allocation_state',
                0xd98b8:'after_frame_publication_before_outer_epilogue',
                0xd98c0:'closed_gate_before_outer_epilogue',
                0xd9214:'before_other_HEVC_updates',0xd9470:'after_target_before_other_fields'}
        if pc-IMAGE in limits:return self.stop('boundary: '+limits[pc-IMAGE])
        off=pc-IMAGE
        assert any(a<=off and off+size<=z for a,z in (
            (0xd95a4,0xd95c8),(0xd96a4,0xd9748),(0xd9820,0xd98b8),
            (0xd9204,0xd9214),(0xd9454,0xd94cc),
            (0x19bd44,0x19bda4),(0x19bff4,0x19c000)))
        ins=next(self.md.disasm(self.blob[off:off+size],pc),None)
        assert ins is not None and ins.mnemonic not in {
            'syscall','break','cache','sync','mfc0','mtc0','eret','wait','tlbwi','tlbwr','tlbr','tlbp'}

    def phase_checked(self,label,entry,**regs):
        e=self.start(label,entry,**regs)
        assert bytes(self.uc.mem_read(FH_PA,4096))==struct.pack('<I',PACK_PA)+bytes(4092)
        return e


def pack(m,label):
    before=bytes(m.uc.mem_read(GOP_PA,4096))
    frame=bytes(m.uc.mem_read(FRAME_PA,4096))
    old=bytes(m.uc.mem_read(PACK_PA,4096))
    control=bytes(m.uc.mem_read(p.CTX_PA,4096))
    qos=bytes(m.uc.mem_read(p.OUTPUT_PA,4096))
    e=m.phase_checked(label,0xd95a4,s1=GOP,s2=FRAME)
    expected_gop=bytearray(before);expected_frame=bytearray(frame);expected_packet=bytearray(old)
    enabled=bool(struct.unpack_from('<I',before,0xe8)[0]&1)
    handle=bool(struct.unpack_from('<I',frame,0x4c8)[0])
    if not enabled:
        assert e['reason']=='boundary: closed_gate_before_outer_epilogue'
    elif not handle:
        assert e['reason']=='boundary: before_unknown_GP_frame_allocation_state'
    else:
        assert e['reason']=='boundary: after_frame_publication_before_outer_epilogue'
        expected_packet[0x14:0xb0]=before[0x78:0x114]
        expected_packet[0xec:0x11c]=before[0xbf4:0xc24]
        expected_frame[0x4c4]|=0x10
        struct.pack_into('<I',expected_gop,0xe8,struct.unpack_from('<I',before,0xe8)[0]&~1)
        assert all(hex(IMAGE+pc) in e['pcs'] for pc in (0xd96f4,0xd9720,0xd9870,0xd98a4,0xd98b4))
    after_gop=bytes(m.uc.mem_read(GOP_PA,4096))
    after_frame=bytes(m.uc.mem_read(FRAME_PA,4096))
    packet=bytes(m.uc.mem_read(PACK_PA,4096))
    assert after_gop==bytes(expected_gop) and after_frame==bytes(expected_frame) and packet==bytes(expected_packet)
    assert bytes(m.uc.mem_read(p.CTX_PA,4096))==control and bytes(m.uc.mem_read(p.OUTPUT_PA,4096))==qos
    assert e['SP_before']==e['SP_after']==hex(p.SP)
    return {'event':e,'source_gate_before':enabled,'frame_handle_present':handle,
            'source_gate_after':bool(struct.unpack_from('<I',after_gop,0xe8)[0]&1),
            'frame_parameter_bit10_after':bool(after_frame[0x4c4]&0x10),
            'copied156_and48':enabled and handle,
            'source_GOP_before_hex':before.hex(),'source_GOP_after_hex':after_gop.hex(),
            'frame_before_hex':frame.hex(),'frame_after_hex':after_frame.hex(),
            'packet_before_hex':old.hex(),'packet_after_hex':packet.hex(),
            'decoded_packet_target':p.a.decode(struct.unpack_from('<I',packet,0x64)[0]) if enabled and handle else None,
            'unclassified_copied_bytes_not_a_complete_valid_hardware_request':True}


def one(blob,source80,gop81,kind):
    m=Guest(blob,source80,gop81,handle=kind!='missing_handle',closed=kind=='closed_gate')
    global CURRENT_GUEST
    CURRENT_GUEST=m
    result=pack(m,'independent original HEVC gated frame-parameter handoff '+kind)
    if kind=='normal':assert result['decoded_packet_target']==gop81['decoded_GOP_target_after']
    return {'seed':source80['seed'],'source_label':gop81['source_label'],'kind':kind,'steps':[result],
            'full_callback_current_MAIN_driver_or_hardware_recording_proven':False}


def sequential(blob,source20,gop16):
    # Deliberately declared sequential input: old GOP16 with a captured20M
    # backend update waiting. No claim that actual camera scheduling permits it.
    m=Guest(blob,source20,gop16)
    global CURRENT_GUEST
    CURRENT_GUEST=m
    first=pack(m,'declared sequence copies original16M GOP parameters')
    assert first['decoded_packet_target']==16000000
    old_packet=bytes(m.uc.mem_read(PACK_PA,4096))
    old_frame=bytes(m.uc.mem_read(FRAME_PA,4096))
    before=bytes(m.uc.mem_read(GOP_PA,4096))
    e=m.phase_checked('independent original HEVC consumer applies captured20M update after handoff',
                      0xd9204,s0=GOP,s1=q.BACKEND)
    assert e['reason']=='boundary: after_target_before_other_fields'
    after=bytes(m.uc.mem_read(GOP_PA,4096));expected=bytearray(before)
    struct.pack_into('<I',expected,0xc8,((20000000//64)-1)<<8)
    assert after==bytes(expected)
    assert bytes(m.uc.mem_read(PACK_PA,4096))==old_packet and bytes(m.uc.mem_read(FRAME_PA,4096))==old_frame
    assert struct.unpack_from('<I',after,0xe8)[0]&1==0
    third=pack(m,'independent re-entry while original GOP gate remains clear')
    assert not third['copied156_and48'] and bytes(m.uc.mem_read(PACK_PA,4096))==old_packet
    return {'seed':source20['seed'],'kind':'declared_old16_then_native20_sequence',
            'first_handoff':first,'native_update':e,'reentry':third,
            'new_GOP_target':p.a.decode(struct.unpack_from('<I',after,0xc8)[0]),
            'old_packet_target':p.a.decode(struct.unpack_from('<I',old_packet,0x64)[0]),
            'old_packet_and_frame_metadata_unchanged':True,
            'natural_runtime_order_legal_reentry_bug_or_hardware_observation_proven':False}


def run(out):
    prior=BASE/'stage81-hevc-qos-consumer-and-release/final-receipt.json'
    assert im.sha(prior.read_bytes())=='26f40c19ae81f315d2656a9bf7f6ab066205703409871b07d5a870f6f3acfd5e'
    for row in json.loads(prior.read_text())['files']:assert im.sha((ROOT/row['path']).read_bytes())==row['sha256']
    assert (BASE/'GOAL_STATUS.json').read_bytes()==(STAGE/'goal-status-before.json').read_bytes()
    src81=prior.parent/'run-20261026/hevc-consumer-results.json'
    src80=BASE/'stage80-vcd-pending-and-timing/run-final-observer-20261026/pending-timing-results.json'
    a81=json.loads(src81.read_text())['target_cases'];a80=json.loads(src80.read_text())['cases']
    blob=p.a.v.VCD_PATH.read_bytes();assert im.sha(blob)==im.PINS[str(p.a.v.VCD_PATH.relative_to(BASE))]
    cases=[];sequences=[]
    for seed in (0xa5,0xc3):
        g16=next(x for x in a81 if x['seed']==seed and x['source_label']=='explicit target16M' and x['declared_control'] is None)
        g20=next(x for x in a81 if x['seed']==seed and x['source_label']=='explicit target20M override control' and x['declared_control'] is None)
        s16=next(x for x in a80 if x['seed']==seed and x['label']=='explicit target16M')
        s20=next(x for x in a80 if x['seed']==seed and x['label']=='explicit target20M override control')
        cases.extend([one(blob,s16,g16,'normal'),one(blob,s20,g20,'normal'),
                      one(blob,s20,g20,'closed_gate'),one(blob,s20,g20,'missing_handle')])
        sequences.append(sequential(blob,s20,g16))
    result={
        'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'status':'PASS_NATIVE_HEVC_FRAME_PARAMETER_COPY_AND_DECLARED_PACKET_LIFETIME',
        'cases':cases,'sequences':sequences,'bounded_phases':len(cases)+3*len(sequences),
        'source_receipt':{'script_sha256':im.sha(Path(__file__).read_bytes()),
                          'prior_runner_sha256':im.sha((q.STAGE/'hevc_consumer.py').read_bytes()),
                          'stage81_result_sha256':im.sha(src81.read_bytes()),'stage80_result_sha256':im.sha(src80.read_bytes()),
                          'VCD_sha256':im.sha(blob)},
        'original_regions':[{'start':hex(a),'end':hex(z),'instructions':p.a.v.mips_dump(blob,a,z)} for a,z in (
            (0xd9558,0xd95c8),(0xd96a4,0xd9748),(0xd9820,0xd98b8),
            (0xd9204,0xd9214),(0xd9454,0xd94cc))],
        'scope':[
            'Independent post-predicate fragment uses captured trial GOP/backend bytes and declared frame/handle/buffer. Original predicate/full callback/allocator are not executed.',
            'Original gated handoff copies156 bytes from GOP78 to buffer14,48 bytes from GOPbf4 to bufferec; target GOPc8 lands at buffer64. Then frame bit10 set and GOP gate bit0 cleared.',
            'Closed-gate control writes nothing; missing handle stops before original GP allocator input.',
            'Explicit old16/new20 sequence leaves old copied16M packet while original HEVC consumer updates GOP20M; gate-clear reentry does not produce a new packet. Not actual scheduling, legal reentrancy or a Sony bug claim.',
            'Unclassified bytes copied unchanged. No complete valid hardware command, actual MAIN, shared sync/config epoch, encoder rate-control calculation/bitstream or recovery proof.'],
        'Windows_UU_camera_operations':False,'goal_complete':False,'persistent_write_release':False,
    }
    im.write_json(out/'frame-handoff-results.json',result)
    (out/'executed-source.py').write_bytes(Path(__file__).read_bytes())
    print(json.dumps({'status':result['status'],'cases':len(cases),'sequences':len(sequences),
                      'bounded_phases':result['bounded_phases'],'hardware_recording_proven':False}))


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--output',required=True);args=ap.parse_args()
    im.volume();out=Path(args.output).resolve();assert STAGE in out.parents and not out.exists();out.mkdir()
    try:run(out)
    except Exception:
        (out/'attempt-source.py').write_bytes(Path(__file__).read_bytes())
        im.write_json(out/'attempt-failure.json',{'traceback':traceback.format_exc(),'passing_result':False})
        if 'CURRENT_GUEST' in globals():
            m=CURRENT_GUEST;im.write_json(out/'failure-state.json',{'pc':hex(m.uc.reg_read(reg.UC_MIPS_REG_PC)),
                'reason':m.reason,'last_pcs':[hex(x) for x in m.pcs[-24:]]})
        raise


if __name__=='__main__':main()
