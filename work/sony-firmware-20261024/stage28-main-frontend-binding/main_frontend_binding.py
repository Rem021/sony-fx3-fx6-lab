#!/usr/bin/env python3
"""Original factory/constructor bindings and MAIN frontend entry, guest only.

Post-allocation/partial-construction fixtures; no actual allocator, full object
construction, live current state, address transport, FSM action or hardware.
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
sys.path.insert(0,str(BASE/'stage26-mc-open-routing'))
import mc_open_routing as r

V=r.V
ENC=r.ENCODER
CTX=ENC+0x70
EXT=ENC+0x116588
WRAP=ENC+0x116988
NORMAL,CACHE=WRAP+0x18,WRAP+0x690
TIMING=ENC+0x115a10
TIMING_NORMAL=ENC+0x115fd8
CURRENT=ENC+0x116980
FSM_HANDLE=r.ARENA+0x240000
EVENT=r.ARENA+0x230000
NEW_OBJECT=r.ARENA+0x250000
INIT_RANGES=[(0xa6274,0xa62c4),(0x12c920,0x12c930),(0x13a5c4,0x13a5dc),
    (0x169108,0x169134),(0x17792c,0x177934),(0x169260,0x169268)]


def reset_trace(m):
    m.reason=None;m.pcs=[];m.writes=[]
    m.regs(sp=r.SP,x30=r.STOP)


def factory_arguments(blob,index):
    start,end=(0xa5748,0xa5840) if index==0 else (0xa584c,0xa594c)
    m=r.RawGuest(blob,[(start,end)],{0xa598c:'before_McApp_constructor'})
    m.regs(x0=NEW_OBJECT,x25=0x805700fa,x24=0x806800f3,x26=0)
    result=m.run(start)
    assert result['reason']=='boundary: before_McApp_constructor'
    actual=[m.uc.reg_read(getattr(r.reg,'UC_ARM64_REG_X'+str(i))) for i in range(3)]
    expected=0x805700f9 if index==0 else 0x805720f9
    assert actual==[NEW_OBJECT,index,expected]
    result.update(factory_index=index,McApp_argument0_to2=[hex(v) for v in actual],
       precondition='Independent post-allocation fragment. X0 is a synthetic allocation precondition; allocator and constructor not run. PreservedW25=0x805700fa comes from original factory prefix.',
       unlisted_constructor_arguments='Unrelated prior registers are explicit zero fixtures; no claim to reproduce their actual runtime values.',
       scope='Original index/MC-ID constructor marshalling only; actual queue creation/registration not executed.')
    return result


def setup(blob,index,packet,fmt,extra_ranges,boundaries):
    boundaries=dict(boundaries);boundaries[0xa62c4]='constructor_binding_fragment_end'
    m=r.RawGuest(blob,INIT_RANGES+extra_ranges,boundaries)
    header=r.seed(m,packet,fmt)
    m.uc.mem_write(r.CONFIG+8,struct.pack('<II',index,0x805700f9 if index==0 else 0x805720f9))
    for at,value in [(CTX,r.CONFIG),(CTX+8,ENC+8),
         (CURRENT,0),(EXT,V+0x35c7e8),(EXT+0x338,WRAP),(EXT+0x3f0,FSM_HANDLE),
         (WRAP,V+0x367b20),(WRAP+0x10,NORMAL),(NORMAL,V+0x36bca8),(CACHE,V+0x367d38),
         (TIMING,V+0x370c10),(TIMING+8,CTX),(TIMING_NORMAL,V+0x3711c0),(TIMING_NORMAL+8,CTX)]:
        m.uc.mem_write(at,r.p64(value))
    m.regs(x25=CTX,x19=ENC,x28=WRAP,x29=EXT,x21=CURRENT,x27=TIMING,x26=TIMING_NORMAL)
    binding=m.run(0xa6274)
    assert binding['reason']=='boundary: constructor_binding_fragment_end'
    current=EXT if index==0 else WRAP
    timing=TIMING_NORMAL if index==0 else TIMING
    assert int.from_bytes(m.read(CURRENT,8),'little')==current
    assert int.from_bytes(m.read(NORMAL+0x20,8),'little')==timing
    assert int.from_bytes(m.read(CACHE+0x20,8),'little')==timing
    if index==0:assert int.from_bytes(m.read(EXT+0x10,8),'little')==timing
    binding.update(index_fixture=index,current_state_pointer=hex(current),
       current_state_type='sfmc_enc_ext_isp_if' if index==0 else 'sfmc_enc_state',
       normal_and_cache_action_interface=hex(timing),
       action_interface_type='sfmc_enc_timing_normal' if index==0 else 'sfmc_enc_timing',
       scope='Original final constructor selection/setter fragment on explicitly partially constructed fixtures. Full constructors, instance state and live objects not executed.')
    assert m.read(r.HEADER,0x38)==header
    reset_trace(m)
    return m,binding,header


def dispatch(blob,label,packet,fmt,index):
    ranges=[(0x12c81c,0x12c834),(0x139954,0x139990),(0x13a0fc,0x13a1d4),
       (0xd80,0xeec),(0x168e9c,0x168f78)]
    m,binding,header=setup(blob,index,packet,fmt,ranges,
       {0x13d8b0:'external_ISP_Open_state_machine_entry',0x168f78:'normal_wrapper_task_hook_entry'})
    m.regs(x0=ENC,x1=r.HEADER,x2=0x38,x3=0x805700f9 if index==0 else 0x805720f9)
    result=m.run(0x12c81c)
    assert result['reason']=='boundary: '+('external_ISP_Open_state_machine_entry' if index==0 else 'normal_wrapper_task_hook_entry')
    if index==0:
        event=m.uc.reg_read(r.reg.UC_ARM64_REG_X1)
        assert m.read(event,0x30)==header[:0x30]
        assert struct.unpack('<II',m.read(event+0x30,8))==(0x38,0x805700f9)
        result.update(external_ISP_event_size='0x38',
          event_header30_copied_unchanged=True,event_length_source_fixture=['0x38','0x805700f9'])
    assert m.read(r.HEADER,0x38)==header and m.read(r.PACKET,0x98)==packet
    result.update(label=label,index_fixture=index,constructor_binding=binding,
      actual_sender_ID_observed=False,
      precondition='Independent post-address-transport call into encoder. Message pointer is already valid guest virtual memory; actual MC transport and sender identity not exercised.',
      scope='Original selected frontend dispatch and bounded header event construction; no frontend FSM processing or format validation.')
    return result


def action_callback(blob,index,packet,fmt):
    ranges=[(0x17b794,0x17b7a4),(0x193f24,0x193f40),(0x189950,0x189968)]
    m,binding,_=setup(blob,index,packet,fmt,ranges,
        {0x27fa04:'before_original_clock_query',0x27d528:'before_timing_diagnostic'})
    event=bytearray(0x28)+bytearray(packet)
    struct.pack_into('<Q',event,8,EVENT+0x28)
    m.uc.mem_write(EVENT,bytes(event));m.regs(x0=NORMAL,x1=EVENT)
    result=m.run(0x17b794)
    assert result['reason']=='boundary: '+('before_original_clock_query' if index==0 else 'before_timing_diagnostic')
    assert int.from_bytes(m.read(NORMAL+0x20,8),'little')==(TIMING_NORMAL if index==0 else TIMING)
    if index==0:assert m.uc.reg_read(r.reg.UC_ARM64_REG_X0)==ENC+8
    result.update(index_fixture=index,constructor_binding=binding,
      resolved_Open_callback_offset='0x193f24' if index==0 else '0x189950',
      precondition='Independent call at normal-owner action dispatch, not reached by executing previous FSM transition or external-ISP frontend completion.',
      scope='Original interface virtual dispatch after original binding fragment; clock/diagnostic and actual timing state-machine Open not executed.')
    return result


def static_evidence(blob):
    tables=[r.im.vtable(blob,off,name) for off,name in [
      (0x35c7d8,'N8sfmc_enc19sfmc_enc_ext_isp_ifE'),
      (0x370c00,'N8sfmc_enc15sfmc_enc_timingE'),
      (0x3711b0,'N8sfmc_enc22sfmc_enc_timing_normalE')]]
    regions=[('factory preserved MC constant',0xa4fe0,0xa5004),
      ('factory index0 args through constructor call',0xa5748,0xa5840),
      ('factory index1 args through constructor call',0xa584c,0xa594c),
      ('constructor index and MC-ID field stores',0xa5a90,0xa5aa4),
      ('encoder current state and timing binding',0xa6274,0xa62c4),
      ('external-ISP forwarding setter',0x13a5c4,0x13a5dc),
      ('wrapper setter and child setters',0x169108,0x169134),
      ('normal child setter',0x17792c,0x177934),('cache child setter',0x169260,0x169268),
      ('external-ISP ordinary message dispatch',0x13a0fc,0x13a1d4),
      ('external-ISP message entry',0x139954,0x139990),
      ('normal owner action dispatch',0x17b794,0x17b7a4),
      ('normal timing Open callback',0x193f24,0x193f60)]
    return {'tables':tables,'regions':[{'name':n,'instructions':r.im.dump(blob,a,z,V)} for n,a,z in regions],
       'external_ISP_command_table':[hex(struct.unpack_from('<Q',blob,0x35c6b0+8*i)[0]) for i in range(5)],
       'main_frontend_Open_processor':'0x13d8b0 ->0x13d8cc',
       'timing_normal_continuation':'0x193f24 queries original clock0x27fa04, stores result at timing+0x5a0, then forwards to0x19841c. Clock and continuation not executed.',
       'scope':'Pinned static construction and table relationships, not a readout of actual initialized camera state or OSAL registration.'}


def run(out):
    prior=BASE/'stage27-encoder-state-machine/final-receipt.json'
    assert r.im.sha(prior.read_bytes())=='4b493ffbd24787ac933f098f6a0806f77a9578eab21be437c5977f8eddb74a5e'
    for stage in ('stage25-mc-image-map','stage26-mc-open-routing','stage27-encoder-state-machine'):
        manifest=json.loads((BASE/stage/'final-receipt.json').read_text())
        assert all(r.im.sha((ROOT/f['path']).read_bytes())==f['sha256'] for f in manifest['files'])
    blob=(BASE/'stage2/extraction/files/nflasha3/av-cam.bin').read_bytes()
    assert r.im.sha(blob)==r.im.PINS['stage2/extraction/files/nflasha3/av-cam.bin']
    variants=r.packet_variants();target,proxy,_,invalid=variants
    factory=[factory_arguments(blob,i) for i in (0,1)]
    paths=[dispatch(blob,*target,0),dispatch(blob,*proxy,1),dispatch(blob,*invalid,0)]
    callbacks=[action_callback(blob,i,target[1],target[2]) for i in (0,1)]
    proof={'status':'PASS_ORIGINAL_FACTORY_FRONTEND_AND_TIMING_BINDING_ONLY',
      'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
      'factory_argument_cases':factory,'post_constructor_dispatch_cases':paths,
      'independent_action_callback_cases':callbacks,'static_evidence':static_evidence(blob),
      'findings':[
        'Original constructor-call prefixes pass index0/MC-ID0x805700f9 and index1/MC-ID0x805720f9; constructor stores index at+8 and MC-ID at+0xc. Allocation, whole construction, queue registration and actual sender still unverified.',
        'Final encoder-constructor selection uses external-ISP frontend for index0 and state wrapper for nonzero index. Earlier direct-normal-state fixtures do not prove the default complete MAIN frontend path.',
        'Original setters bind normal/cache owner action interfaces to timing_normal for index0 via external-ISP forwarding, and timing for index1 via wrapper setter.',
        'Post-construction index0 Open enters external-ISP processor0x13d8b0 after copying0x30 header bytes and appending length/source fixtures; index1 reaches wrapper task hook. Video enums invalid or target do not select a different frontend in these fragments.',
        'Normal-owner Open action now resolves to timing_normal0x193f24(index0) or timing0x189950(index1). Actual clock, frontend completion, timing FSM, resource requests and hardware replies remain unexecuted.'],
      'scope':'7 scenarios/12 bounded phases on independent partial-construction and post-transport fixtures; no end-to-end initialization, physical transport, frontend completion or hardware encoding.',
      'full_constructor_allocator_OSAL_registration_executed':False,
      'actual_clock_frontend_FSM_timing_FSM_or_hardware_executed':False,
      'native_output_adapters':False,'camera_or_remote_access_attempted':False,
      'modified_firmware_or_patch_exported':False,'goal_complete':False,'persistent_write_release':False}
    summary={'status':proof['status'],'factory_argument_cases':len(factory),
      'post_constructor_dispatch_cases':len(paths),'independent_action_callback_cases':len(callbacks),
      'bounded_scenarios':len(factory)+len(paths)+len(callbacks),'bounded_phases':len(factory)+2*len(paths)+2*len(callbacks),
      'index0_MC_ID':'0x805700f9','index0_initial_frontend':'sfmc_enc_ext_isp_if',
      'index0_normal_Open_callback':'0x193f24 sfmc_enc_timing_normal',
      'actual_hardware_or_recovery_verified':False,'goal_complete':False,'persistent_write_release':False}
    assert r.im.sha(blob)==r.im.sha((BASE/'stage2/extraction/files/nflasha3/av-cam.bin').read_bytes())
    r.im.write_json(out/'main-frontend-binding-results.json',proof);r.im.write_json(out/'summary.json',summary)
    r.im.write_json(out/'source-receipt.json',{'script':str(Path(__file__).relative_to(ROOT)),
       'script_sha256':r.im.sha(Path(__file__).read_bytes()),'raw_guest_harness_sha256':r.im.sha(Path(r.__file__).read_bytes()),
       'raw_map_helper_sha256':r.im.sha(Path(r.im.__file__).read_bytes()),'raw_image_sha256':r.im.sha(blob),
       'previous_manifest_sha256':r.im.sha(prior.read_bytes()),
       'packet_source_sha256':r.im.sha((BASE/'stage23-encoder-boundary/run-corrected-20261025/encoder-boundary-results.json').read_bytes()),
       'volume_uuid':r.im.VOLUME,'result_sha256':r.im.sha((out/'main-frontend-binding-results.json').read_bytes()),
       'summary_sha256':r.im.sha((out/'summary.json').read_bytes())})
    print(json.dumps(summary,ensure_ascii=False))


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',required=True)
    args=parser.parse_args();r.im.volume();out=Path(args.output).resolve()
    assert STAGE in out.parents and not out.exists();out.mkdir()
    try:run(out)
    except Exception:
        with (out/'attempt-source.py').open('xb') as f:f.write(Path(__file__).read_bytes())
        r.im.write_json(out/'attempt-failure.json',{'traceback':traceback.format_exc(),'passing_result':False});raise


if __name__=='__main__':main()
