#!/usr/bin/env python3
"""Original app QoS packet producer and explicit byte handoff, offline only.

The observed callers are streaming/SRT, not a proven card MAIN route. Logging,
OSAL identity allocation, actual Dataflow send/reply and real state/instance
bindings remain unexecuted. No device, network stream or deployment is run.
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
sys.path.insert(0,str(BASE/'stage101-native-qos-receive-snapshot'))
import receive_snapshot as src
r,im=src.r,src.im
pp=r.d.pp
APP=pp.APP
APP_SHA='545c5053a74e04ffbf2bbaaf80f558092dd545ed2298b2395ca547dbba58290f'
PRIOR=BASE/'stage101-native-qos-receive-snapshot/final-receipt.json'
PRIOR_SHA='b3761c58d773ede3f1a7e47e63d22617cbf8ab062c5bcb315f2e9e982206f292'
APP_SP=pp.STACK_BASE+0x20000
INPUT=pp.SCRATCH+0x100
OUTPUT=pp.SCRATCH+0x200
META=pp.SCRATCH+0x400


def sha(raw):return hashlib.sha256(raw).hexdigest()


class AppGuest(pp.StrictMicro):
    def __init__(self,seed):
        super().__init__(APP,[(0x2df20cc,0x2df219c),(0x2de7070,0x2de70a8)])
        self.uc.mem_write(pp.STACK_BASE,bytes([seed])*pp.STACK_SIZE)
        self.uc.mem_write(pp.SCRATCH,bytes([seed^0x3c])*0x10000)
        self.boundaries={0x2f6ff0c:'before_original_app_logger',
                         0x1593d20:'before_unexecuted_osal_subsystem_id'}

    def code(self,u,pc,size,user):
        if pc in self.boundaries:
            self.pcs.append(hex(pc));self.abort('boundary: '+self.boundaries[pc]);return
        return super().code(u,pc,size,user)

    def phase(self,label,start,stack_top=APP_SP,stack_bytes=0xc0,scratch_outputs=(),**regs):
        before_stack=bytes(self.uc.mem_read(pp.STACK_BASE,pp.STACK_SIZE))
        before_scratch=bytes(self.uc.mem_read(pp.SCRATCH,0x10000))
        for name,value in regs.items():self.uc.reg_write(getattr(r.reg,'UC_ARM64_REG_'+name.upper()),value)
        self.reason=None;self.steps=0;self.pcs=[];self.stores=[];self.writes=[];self.calls=[]
        self.uc.emu_start(start,0,count=2000,timeout=1000000)
        assert self.reason is not None,'bounded phase did not reach boundary'
        low=stack_top-stack_bytes
        for w in self.stores:
            at,n=int(w['address'],16),w['size']
            assert low<=at and at+n<=stack_top or any(a<=at and at+n<=z for a,z in scratch_outputs),w
        after_stack=bytes(self.uc.mem_read(pp.STACK_BASE,pp.STACK_SIZE))
        assert after_stack[:low-pp.STACK_BASE]==before_stack[:low-pp.STACK_BASE]
        assert after_stack[stack_top-pp.STACK_BASE:]==before_stack[stack_top-pp.STACK_BASE:]
        after_scratch=bytes(self.uc.mem_read(pp.SCRATCH,0x10000))
        changed=[pp.SCRATCH+n for n,(a,b) in enumerate(zip(before_scratch,after_scratch)) if a!=b]
        assert all(any(a<=p<z for a,z in scratch_outputs) for p in changed)
        assert not self.calls,'no import or native-return adapters are admitted in these phases'
        return {'label':label,'entry':hex(start),'reason':self.reason,
                'stop_pc':hex(self.uc.reg_read(r.reg.UC_ARM64_REG_PC)),
                'SP_after':hex(self.uc.reg_read(r.reg.UC_ARM64_REG_SP)),
                'FP_after':hex(self.uc.reg_read(r.reg.UC_ARM64_REG_X29)),
                'pcs':self.pcs,'stores':self.stores,
                'whole_stack_outside_declared_frame_unchanged':True,
                'whole_scratch_outside_declared_outputs_unchanged':True,
                'mapped_original_ELF_guest_readonly_and_no_patch_or_resolution_requested':True,
                'imports_logs_or_return_adapters_executed':False}

    def close(self):
        for h in self.hooks:self.uc.hook_del(h)


def build(seed,value):
    m=AppGuest(seed)
    try:
        m.uc.mem_write(INPUT,struct.pack('<I',value))
        events=[m.phase('original mc_enc_set_qos prologue before first logger',0x2df20cc,
                        sp=APP_SP,x30=pp.STOP,x0=INPUT,x1=OUTPUT)]
        assert events[-1]['reason']=='boundary: before_original_app_logger'
        fp=m.uc.reg_read(r.reg.UC_ARM64_REG_X29)
        assert fp==APP_SP-0xc0 and m.uc.reg_read(r.reg.UC_ARM64_REG_X25)==INPUT
        # Independent post-log/OSAL-init entry. No logger, identity allocator
        # or result is skipped by a fabricated return or synthesized value.
        events.append(m.phase('independent original complete80-byte packet production',0x2df213c))
        assert events[-1]['reason']=='boundary: before_original_app_logger'
        packet=bytes(m.uc.mem_read(fp+0x70,0x50))
        expected=bytearray(0x50)
        struct.pack_into('<HHHH',expected,0,0x2003,0x10a,0x50,1)
        expected[12]=1
        target=(value*1000)&0xffffffff
        struct.pack_into('<I',expected,16,target)
        assert packet==bytes(expected)
        assert bytes(m.uc.mem_read(INPUT,4))==struct.pack('<I',value)
        assert bytes(m.uc.mem_read(OUTPUT,4))==bytes([seed^0x3c])*4
        return {'seed':seed,'declared_input_word':value,'native_target_word':target,
                'message50_hex':packet.hex(),'events':events,
                'no_OSAL_reply_identity_or_success_result_synthesized':True,
                'normal_wrapper_send_reply_state_MAIN_or_encoding_proven':False}
    finally:m.close()


def meta_prefix(seed):
    m=AppGuest(seed)
    try:
        e=m.phase('original metadata initializer prefix before OSAL identity lookup',0x2de7070,
                  stack_top=APP_SP,stack_bytes=0x20,scratch_outputs=[(META,META+8)],
                  sp=APP_SP,x30=pp.STOP,x0=META,x1=2)
        assert e['reason']=='boundary: before_unexecuted_osal_subsystem_id'
        value=bytes(m.uc.mem_read(META,8))
        assert value==struct.pack('<II',0,2)
        return {'seed':seed,'events':[e],'first8_after_hex':value.hex(),
                'OSAL_subsystem_dynamic_id_and_normal_metadata_not_completed':True,
                'constant2_not_claimed_encoder_channel':True}
    finally:m.close()


def handoff(blob,producer):
    packet=bytes.fromhex(producer['message50_hex'])
    seed=producer['seed'];target=producer['native_target_word']
    m,events=src.setup(blob,seed,3)
    events.extend(src.receive_prefix(m,packet,src.REPLY1))
    e,snapshot=src.copy_owned(m,packet,src.REPLY1);events.append(e)
    events.append(src.onward(m,snapshot))
    assert hex(src.V+0x189ce8) in events[-1]['pcs']
    sp=m.uc.reg_read(r.reg.UC_ARM64_REG_SP);pending=m.read(sp,r.SP-sp)
    events.append(m.phase('independent lower forwarding of original app-produced request',
                          0x14555c,x0=src.prev.INTERFACE,x1=src.OWNED,
                          sp=src.prev.LOWER_SP,stack_ceiling=src.prev.LOWER_SP))
    assert events[-1]['reason']=='boundary: before_message_object_constructor'
    envelope=m.read(m.uc.reg_read(r.reg.UC_ARM64_REG_SP)+0x1a8,0x54)
    assert envelope==struct.pack('<HHHHI',0x2103,0x10a,0x54,0,2)+packet[8:]
    assert src.prev.u32(envelope,20)==target
    assert m.read(sp,r.SP-sp)==pending
    return {'seed':seed,'declared_app_input_word':producer['declared_input_word'],
            'native_target_word':target,'app_message_hex':packet.hex(),
            'context_snapshot_hex':snapshot.hex(),'lower_envelope_hex':envelope.hex(),
            'events':events,'raw_body_copied_between_guests_without_host_field_edits':True,
            'declared_receiver_reply_word':src.REPLY1,'declared_receiver_numeric_state':3,
            'declared_lower_channel':2,'channel_not_inferred_from_OSAL_constant2':True,
            'pending_original_action_frames_preserved':True,
            'actual_transport_target_MAIN_format_or_Hal_application_proven':False}


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',required=True)
    out=Path(parser.parse_args().output).resolve()
    im.volume();assert out.parent==STAGE and not out.exists()
    assert sha(PRIOR.read_bytes())==PRIOR_SHA
    for f in json.loads(PRIOR.read_text())['files']:
        raw=(ROOT/f['path']).read_bytes();assert len(raw)==f['bytes'] and sha(raw)==f['sha256']
    assert (STAGE/'goal-status-before.json').read_bytes()==(BASE/'GOAL_STATUS.json').read_bytes()
    assert sha(APP.blob)==sha(APP.path.read_bytes())==APP_SHA
    blob=src.prev.IMAGE.read_bytes();assert sha(blob)==src.prev.IMAGE_SHA
    out.mkdir();(out/'executed-source.py').write_bytes(Path(__file__).read_bytes())
    try:
        producers=[build(seed,n) for seed in (0xa5,0xc3) for n in (16000,20000,0,16000000)]
        metadata=[meta_prefix(seed) for seed in (0xa5,0xc3)]
        copies=[handoff(blob,p) for p in producers if p['declared_input_word'] in (16000,20000)]
        for n in (16000,20000,0,16000000):
            assert len({p['message50_hex'] for p in producers if p['declared_input_word']==n})==1
        result={'status':'PASS_ORIGINAL_APP_QOS_PACKET_PRODUCTION_AND_EXPLICIT_RECEIVER_BYTE_HANDOFF',
            'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'previous_manifest_sha256':PRIOR_SHA,'original_app_sha256':APP_SHA,
            'original_avcam_sha256':sha(blob),'producer_cases':producers,
            'metadata_prefix_cases':metadata,'handoff_cases':copies,
            'bounded_phases':sum(len(c['events']) for c in producers+metadata+copies),
            'scope':'Original app prologue and independent packet-building body, no logging/OSAL allocation/send/reply. Source inputs are fixtures. Actual produced bytes feed separate avcam guests with explicit task-hook/log/dump gaps, reply ID/numeric state/channel fixtures. Observed original call sites are streaming/SRT; no natural card MAIN instance or target HEVC mode proof.',
            'natural_target_MAIN_HEVC_stream_or_recovery_proven':False,
            'Windows_UU_camera_operations':False,'goal_complete':False,'persistent_write_release':False}
        (out/'app-qos-results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
        print(json.dumps({'status':result['status'],'producer_cases':len(producers),
                          'metadata_cases':len(metadata),'handoffs':len(copies),
                          'bounded_phases':result['bounded_phases'],'output':str(out)}))
    except Exception:
        (out/'attempt-failure.json').write_text(json.dumps({'traceback':traceback.format_exc(),'passing_result':False},indent=2)+'\n')
        raise


if __name__=='__main__':main()
