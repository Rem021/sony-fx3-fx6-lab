#!/usr/bin/env python3
"""Original pending consume/requeue and shared timing receiver, guest only.

No real configuration transition, task hook, timing event processing, resources,
transport, hardware, host firmware loader or camera operation.
"""
from pathlib import Path
import argparse
import datetime
import json
import struct
import sys
import traceback

ROOT=Path(__file__).resolve().parents[3]
BASE=ROOT/'work/sony-firmware-20261024'
STAGE=Path(__file__).resolve().parent
sys.path.insert(0,str(BASE/'stage29-main-frontend-open'))
import frontend_open as e
r,f,V=e.r,e.f,e.V
H_TIMING=r.ARENA+0x2b0000
REBUILT=r.ARENA+0x2c0000


def queue_then_consume(blob,label,packet,fmt,new_state):
    ranges=[(0x12c81c,0x12c834),(0x139954,0x139990),(0x13a0fc,0x13a1d4),
      (0x13d8b0,0x13db00),(0x13bc4c,0x13bd24),(0x13bb98,0x13bc44),
      (0x13bd24,0x13bdd8),(0x13d204,0x13d240),(0x13d2fc,0x13d338),
      (0x13dd50,0x13dfa0),(0x27da84,0x27da9c),(0xd80,0xeec),
      (0x168e9c,0x168f78)]+e.callback_ranges(blob,[0,new_state])
    m,binding,header=e.setup(blob,packet,fmt,0,ranges,{0x168f78:'before_wrapper_task_hook'})
    m.regs(x0=f.ENC,x1=r.HEADER,x2=0x38,x3=e.OTHER_SOURCE)
    admission=m.run(0x12c81c)
    assert admission['reason']=='returned' and m.uc.reg_read(r.reg.UC_ARM64_REG_X0)==1
    assert int.from_bytes(m.read(f.EXT+0x348,4),'little')==1
    queued=m.read(f.EXT+0x18,0x38)
    assert queued[:0x30]==header[:0x30]
    # The real event/configuration that reaches state2/8 is NOT simulated.
    # This second phase is an explicit post-transition state fixture, keeping
    # the original queued data produced by phase1.
    m.uc.mem_write(e.SM+8,struct.pack('<I',new_state))
    f.reset_trace(m);m.regs(x0=f.EXT)
    consumer=0x13d204 if new_state==2 else 0x13d2fc
    consumed=m.run(consumer)
    assert consumed['reason']=='boundary: before_wrapper_task_hook'
    assert struct.unpack('<I',m.read(f.EXT+0x348,4))[0]==0
    assert int.from_bytes(m.read(f.EXT+0x350,4),'little')==0
    assert m.read(f.EXT+0x120,0x98)==packet
    assert m.read(f.EXT+0x1b8,0x98)==packet
    assert m.read(e.SM+0x290,0x98)==packet
    assert m.read(e.SM+0xc,1)==b'\x01'
    assert m.read(e.SM+0x284,1)==b'\x01'
    assert int.from_bytes(m.read(e.SM+0x608,4),'little')==1
    assert int.from_bytes(m.read(e.SM+0x618,8),'little')==e.SM+0x278
    after=m.read(r.PACKET,0x98)
    if new_state==8:
        assert after[0x88]==1 and after[:0x88]+after[0x89:]==packet[:0x88]+packet[0x89:]
        assert m.read(e.SM+0x290+0x88,1)==packet[0x88:0x89]
    else:assert after==packet
    assert m.read(r.HEADER,0x38)==header
    return {'label':label,'constructor_binding':binding,'original_local_admission':admission,
       'post_transition_consume':consumed,'explicit_post_transition_state':new_state,
       'queued_event38_from_original_admission':queued.hex(),
       'frontend_pending_count_after':0,'lower_pending_count_after':1,
       'lower_busy_and_video_pending_flags_after':[1,1],
       'deferred_video_packet98_unchanged':True,
       'source_packet88_after':after[0x88],'deferred_packet88':packet[0x88],
       'precondition':'Original queue contents retained between phases, but transition to numeric state2/8 is an independent explicit input. Actual configuration completion/entry hook not executed or stubbed.',
       'scope':'Original consume/re-enter/nested defer/forward until task hook. Front count0 does not prove all references drained; lower event execution and hardware acceptance not performed.'}


def empty_consume(blob,packet,fmt):
    m,binding,_=e.setup(blob,packet,fmt,2,[(0x13d204,0x13d240)],{})
    m.regs(x0=f.EXT)
    result=m.run(0x13d204);assert result['reason']=='returned' and not result['writes']
    return {'constructor_binding':binding,'empty_consumer':result,
       'scope':'Independent empty frontend slot, not a global quiescence or safe restore test.'}


def rec_format_receiver(blob,packet,fmt,tag):
    m,binding,_=e.setup(blob,packet,fmt,0,
        [(0x13bb78,0x13bb88),(0x194ba8,0x194bbc)],
        {0x19bd84:'timing_normal_SET_REC_FORMAT_processor_entry'})
    raw=bytearray(0xd8)
    struct.pack_into('<I',raw,0xc0,tag)
    m.uc.mem_write(REBUILT,bytes(raw))
    m.uc.mem_write(f.TIMING_NORMAL+0x478,r.p64(H_TIMING))
    m.regs(x0=f.EXT,x1=REBUILT)
    result=m.run(0x13bb78)
    assert result['reason']=='boundary: timing_normal_SET_REC_FORMAT_processor_entry'
    assert m.uc.reg_read(r.reg.UC_ARM64_REG_X0)==H_TIMING
    assert m.uc.reg_read(r.reg.UC_ARM64_REG_X1)==REBUILT
    assert int.from_bytes(m.read(f.TIMING_NORMAL+0x34,4),'little')==tag
    assert m.read(REBUILT,0xd8)==bytes(raw)
    return {'constructor_binding':binding,'original_interface_dispatch':result,
       'untyped_input_word_c0':hex(tag),'timing_word34_after':hex(tag),
       'shared_handle_field':'timing_normal+0x478',
       'precondition':'Independent call at SET_REC_FORMAT action after excluded state transition; payload is an untyped fixture, not a validated real rebuild.',
       'scope':'Original interface and handle forwarding only; actual SET_REC_FORMAT timing processing, payload interpretation and hardware not executed.'}


def static_evidence(blob):
    main_vptr=0x3711c0
    assert struct.unpack_from('<Q',blob,main_vptr+0x108)[0]==V+0x194ba8
    entry=[struct.unpack_from('<Q',blob,0x35c868+i*8)[0]-V for i in range(13)]
    assert entry[2]==0x13fbec and entry[8]==0x13fc3c
    regions=[('pending consumer on state2 entry',0x13d204,0x13d240),
      ('pending consumer on state8 entry',0x13d2fc,0x13d338),
      ('entry hook consumer calls',0x13fbb4,0x13fc7c),
      ('entry diagnostic helper excluded',0x13fc94,0x13fd0c),
      ('nested video event busy/defer path',0x13dd50,0x13de9c),
      ('Open copy/state8 flag sequence',0x13bd24,0x13bdd8),
      ('SET_REC_FORMAT owner action dispatch',0x13bb78,0x13bb88),
      ('normal timing SET_REC_FORMAT handle forwarding',0x194ba8,0x194bbc),
      ('normal timing Open uses same handle',0x193f24,0x193f60)]
    return {'entry_state_table_offset':'0x35c868','entry_state_targets':[hex(p) for p in entry],
      'common_timing_handle_field':'timing_normal+0x478',
      'timing_Open_processor':'0x19841c','timing_SET_REC_FORMAT_processor':'0x19bd84',
      'common_handle_scope':'Original callbacks load the same owner field; actual initialized handle/state and merge behavior not observed.',
      'regions':[{'name':n,'instructions':r.im.dump(blob,a,z,V)} for n,a,z in regions]}


def run(out):
    prior=BASE/'stage29-main-frontend-open/final-receipt.json'
    assert r.im.sha(prior.read_bytes())=='4865eda16b3f7c7f105fc9ccd4780aa3416d020e869448b80c432759ad6b14ef'
    for stage in ('stage25-mc-image-map','stage26-mc-open-routing','stage28-main-frontend-binding','stage29-main-frontend-open'):
        previous=json.loads((BASE/stage/'final-receipt.json').read_text())
        assert all(r.im.sha((ROOT/v['path']).read_bytes())==v['sha256'] for v in previous['files'])
    blob=(BASE/'stage2/extraction/files/nflasha3/av-cam.bin').read_bytes()
    assert r.im.sha(blob)==r.im.PINS['stage2/extraction/files/nflasha3/av-cam.bin']
    target,_,uhd,invalid=r.packet_variants()
    queued=[queue_then_consume(blob,*case,state) for case,state in [(target,2),(uhd,2),(invalid,2),(target,8)]]
    empty=empty_consume(blob,target[1],target[2])
    cfg=[rec_format_receiver(blob,target[1],target[2],tag) for tag in (0,0x10203040)]
    proof={'status':'PASS_ORIGINAL_PENDING_REENTRY_DEFER_AND_COMMON_RECEIVER_ONLY',
      'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
      'queue_then_post_transition_consume_cases':queued,'independent_empty_consume':empty,
      'independent_rec_format_receiver_cases':cfg,'static_evidence':static_evidence(blob),
      'findings':[
        'Original state-entry table2/8 points to consumers that pop frontend Open pending and re-enter its FSM. Entry diagnostic/configuration transition remains unexecuted.',
        'Retained original queue data consumed under explicit state2/8 fixtures clears frontend count, but nested video subevent is deferred because the same FSM is busy. It copies original0x98 packet toSM+0x290 and leaves a lower pending functor/count before wrapper task hook.',
        'For state8, source packet88 becomes1 after the lower deferred copy; that copy retains original packet88. No claim of a bug or full consumer semantics without later actions and ownership constraints.',
        'SET_REC_FORMAT action resolves via original timing_normal slot0x108 to0x194ba8 then0x19bd84, using timing+0x478. Normal Open also uses that field to reach0x19841c, identifying a concrete common consumer for subsequent merge analysis.',
        'Neither frontend count0, wrapper1 nor retained scalar/video fields prove hardware Open or safe restore. Actual source, live states, transition/task hooks, timing/resource/VCD and replies remain missing.'],
      'scope':'Independent partial-construction/admission/post-transition/receiver-entry fixtures. Explicit host seed of numeric post-transition state is not original transition execution; no successful backend outputs supplied.',
      'configuration_transition_entry_diagnostic_task_timing_resource_hardware_executed':False,
      'native_output_adapters':False,'camera_or_remote_access_attempted':False,
      'modified_firmware_or_patch_exported':False,'goal_complete':False,'persistent_write_release':False}
    summary={'status':proof['status'],'queue_then_consume_scenarios':len(queued),
      'independent_empty_consume_scenarios':1,'common_receiver_entry_scenarios':len(cfg),
      'frontend_count0_lower_pending1':True,'deferred_video98_retained':True,
      'common_timing_Open_and_SET_REC_FORMAT_handle_identified':True,
      'actual_merge_or_hardware_verified':False,'goal_complete':False,'persistent_write_release':False}
    assert r.im.sha(blob)==r.im.sha((BASE/'stage2/extraction/files/nflasha3/av-cam.bin').read_bytes())
    r.im.write_json(out/'pending-consumption-results.json',proof);r.im.write_json(out/'summary.json',summary)
    r.im.write_json(out/'source-receipt.json',{'script':str(Path(__file__).relative_to(ROOT)),
      'script_sha256':r.im.sha(Path(__file__).read_bytes()),'frontend_flow_harness_sha256':r.im.sha(Path(e.__file__).read_bytes()),
      'constructor_harness_sha256':r.im.sha(Path(f.__file__).read_bytes()),'raw_guest_harness_sha256':r.im.sha(Path(r.__file__).read_bytes()),
      'raw_map_helper_sha256':r.im.sha(Path(r.im.__file__).read_bytes()),'raw_image_sha256':r.im.sha(blob),
      'previous_manifest_sha256':r.im.sha(prior.read_bytes()),
      'packet_source_sha256':r.im.sha((BASE/'stage23-encoder-boundary/run-corrected-20261025/encoder-boundary-results.json').read_bytes()),
      'volume_uuid':r.im.VOLUME,'result_sha256':r.im.sha((out/'pending-consumption-results.json').read_bytes()),
      'summary_sha256':r.im.sha((out/'summary.json').read_bytes())})
    print(json.dumps(summary,ensure_ascii=False))


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',required=True)
    args=parser.parse_args();r.im.volume();out=Path(args.output).resolve()
    assert STAGE in out.parents and not out.exists();out.mkdir()
    try:run(out)
    except Exception:
        with (out/'attempt-source.py').open('xb') as h:h.write(Path(__file__).read_bytes())
        r.im.write_json(out/'attempt-failure.json',{'traceback':traceback.format_exc(),'passing_result':False});raise


if __name__=='__main__':main()
