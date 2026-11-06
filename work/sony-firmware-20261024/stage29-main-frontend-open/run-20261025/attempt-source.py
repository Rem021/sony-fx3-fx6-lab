#!/usr/bin/env python3
"""MAIN frontend queue/copy and SET_REC_FORMAT fragments, original guest only.

No actual initialized camera state, source identity, frontend completion, task
hook, reconfiguration subevent, clock, resources, hardware or restore.
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
sys.path.insert(0,str(BASE/'stage28-main-frontend-binding'))
import main_frontend_binding as f
r=f.r;V=f.V
SM,EVENT,REC,OUT=(r.ARENA+n for n in (0x2a0000,0x270000,0x280000,0x290000))
MC_ID=0x805700f9
OTHER_SOURCE=0x810b0768
TABLE=0x35ce58


def callback_ranges(blob,states):
    ranges=[]
    for state in states:
        guard,action,nxt=struct.unpack_from('<3Q',blob,TABLE+24*state)
        ranges.extend([(guard-V,guard-V+8),(action-V,action-V+24),(nxt-V,nxt-V+8)])
    return ranges


def setup(blob,packet,fmt,state,extra,stops):
    m,binding,header=f.setup(blob,0,packet,fmt,extra,stops)
    m.uc.mem_write(f.FSM_HANDLE,r.p64(SM))
    m.uc.mem_write(SM,r.p64(f.EXT))
    m.uc.mem_write(SM+8,struct.pack('<I',state))
    m.uc.mem_write(SM+0xc,b'\x00')
    m.uc.mem_write(SM+0x608,bytes(12))
    m.uc.mem_write(f.EXT+0x348,bytes(12))
    return m,binding,header


def flow(blob,label,packet,fmt,state=0,source=OTHER_SOURCE):
    ranges=[(0x12c81c,0x12c834),(0x139954,0x139990),(0x13a0fc,0x13a1d4),
      (0x13d8b0,0x13db00),(0x13bc4c,0x13bd24),(0x13bb98,0x13bc44),
      (0xd80,0xeec),(0x168e9c,0x168f78)]+callback_ranges(blob,[state])
    m,binding,header=setup(blob,packet,fmt,state,ranges,
       {0x168f78:'before_wrapper_task_hook',0x13dd50:'before_frontend_video_subevent',
        0x13dfa0:'before_frontend_cache_subevent'})
    raw_return=[]
    def observe(u,pc,size,user):
        if pc==V+0x13d8bc:raw_return.append(u.reg_read(r.reg.UC_ARM64_REG_X0))
    m.uc.hook_add(r.unicorn.UC_HOOK_CODE,observe)
    m.regs(x0=f.ENC,x1=r.HEADER,x2=0x38,x3=source)
    result=m.run(0x12c81c)
    if state in (0,1) and source!=MC_ID:
        assert result['reason']=='returned' and raw_return==[0]
        assert m.uc.reg_read(r.reg.UC_ARM64_REG_X0)==1
        assert int.from_bytes(m.read(f.EXT+0x348,4),'little')==1
        queued=m.read(f.EXT+0x18,0x38)
        assert queued[:0x30]==header[:0x30]
        assert struct.unpack('<II',queued[0x30:])==(0x38,source)
        assert int.from_bytes(m.read(f.EXT+0x358,8),'little')==f.EXT+0x18
        assert int.from_bytes(m.read(f.EXT+0x28,8),'little')==r.PACKET
        assert m.read(SM+0xc,1)==b'\x00'
        phase='locally queued; no hardware action'
    elif source==MC_ID:
        assert result['reason']=='boundary: before_wrapper_task_hook'
        assert int.from_bytes(m.read(f.EXT+0x348,4),'little')==0
        phase='same-MC-ID branch forwarded to wrapper before task hook'
    else:
        assert state==2 and result['reason']=='boundary: before_frontend_video_subevent'
        assert m.read(f.EXT+0x120,0x98)==packet
        assert m.read(f.EXT+0x1b8,0x98)==packet
        copied=m.uc.reg_read(r.reg.UC_ARM64_REG_X1)
        assert m.read(copied,0x98)==packet
        phase='original video packet copied unchanged; subevent not executed'
    assert m.read(r.HEADER,0x38)==header and m.read(r.PACKET,0x98)==packet
    result.update(label=label,state_fixture=state,source_argument_fixture=hex(source),
       actual_source_ID_observed=False,constructor_binding=binding,
       raw_frontend_processor_returns=raw_return,
       phase_meaning=phase,source_header_and_packet_unchanged=True,
       precondition='Original final constructor binding plus independent ready/busy-free frontend state fixture. Actual init, source identity, OSAL and physical/shared pointer transport not executed.',
       scope='Local frontend control/queue/copy only. A returned wrapper1 can mean queued request, not encoder Open success.')
    return result


def post_subevent_flag(blob,packet,fmt):
    ranges=[(0x13bda4,0x13bdc4),(0x168e9c,0x168f78)]
    m,binding,header=setup(blob,packet,fmt,8,ranges,{0x168f78:'before_wrapper_task_hook'})
    event=header[:0x30]+struct.pack('<II',0x38,OTHER_SOURCE)
    m.uc.mem_write(EVENT,event)
    m.regs(x19=EVENT,x20=f.EXT,x21=r.PACKET)
    result=m.run(0x13bda4)
    assert result['reason']=='boundary: before_wrapper_task_hook'
    after=m.read(r.PACKET,0x98)
    assert after[0x88]==1 and after[:0x88]+after[0x89:]==packet[:0x88]+packet[0x89:]
    result.update(constructor_binding=binding,state_action_numeric_index=8,
       raw_packet88_after=1,other_packet_bytes_unchanged=True,
       precondition='Independent fragment after unexecuted0x13dd50/0x13dfa0 subevent. No subevent result or side effect is assumed successful.',
       scope='Original raw88 store and wrapper forwarding only; prior subevent, task hook and cache-state processing not executed.')
    return result


def frame_conversion(blob,num,den,progressive,expected):
    m=r.RawGuest(blob,[(0x13ad70,0x13ae4c)],{})
    m.uc.mem_write(REC+8,struct.pack('<III',num,den,progressive))
    m.regs(x1=REC)
    result=m.run(0x13ad70);assert result['reason']=='returned'
    value=m.uc.reg_read(r.reg.UC_ARM64_REG_X0);assert value==expected
    result.update(input_rational=[num,den],raw_progressive_input=progressive,
       converted_enum=value,
       scope='Original SET_REC_FORMAT helper with integer quotient. Output enum only, not hardware timebase or support.')
    return result


def dimensions(blob,width,height):
    m=r.RawGuest(blob,[(0x13a2bc,0x13a2dc)],{0x13a2dc:'before_next_format_field_helper'})
    m.uc.mem_write(REC+0xc,struct.pack('<II',width,height))
    m.regs(x21=REC,x19=OUT)
    result=m.run(0x13a2bc);assert result['reason']=='boundary: before_next_format_field_helper'
    actual=struct.unpack('<HH',m.read(OUT+0x90,4));assert actual==(width,height)
    result.update(source_width_height=[width,height],output_width_height=list(actual),
       output_field_offsets=['0x90','0x92'],relative_video_packet_offsets=['0x68','0x6a'],
       precondition='Independent rebuild fragment; earlier diagnostics, clear and format-identity helpers not executed.',
       scope='Original dimension stores from a SET_REC_FORMAT fixture, not full rebuild or active encoder geometry.')
    return result


def static_evidence(blob):
    table=[]
    for state in range(13):
        values=struct.unpack_from('<3Q',blob,TABLE+24*state)
        table.append({'state':state,'guard_action_next':[hex(v) for v in values]})
    identities=[list(struct.unpack_from('<4I',blob,0x39325c+i*16)) for i in range(16)]
    regions=[('frontend Open processor',0x13d8b0,0x13db00),
      ('state0/1 Open queue action',0x13bc4c,0x13bd24),
      ('state2 video copy and forwarding',0x13bb98,0x13bc44),
      ('state8 video copy flag and forwarding',0x13bd24,0x13bdd8),
      ('SET_REC_FORMAT distinct-message selector',0x139954,0x139990),
      ('SET_REC_FORMAT handler and builder call',0x139ee8,0x139fc4),
      ('rebuild header and format/dimension stores',0x13a248,0x13a320),
      ('rebuild final format store',0x13a420,0x13a464),
      ('rebuild FileFormat identity helper',0x13ab1c,0x13abdc),
      ('rebuild rational-to-enum helper',0x13ad70,0x13ae4c)]
    assert r.im.cstring(blob,0x4184cc)=='[EXT ISP IF][RcvBB]SET_REC_FORMAT'
    return {'Open_state_table_offset':hex(TABLE),'Open_state_table':table,
      'SET_REC_FORMAT_diagnostic':r.im.cstring(blob,0x4184cc),
      'SET_REC_FORMAT_identity_table_offset':'0x39325c',
      'SET_REC_FORMAT_raw_result_and_three_selector_rows':identities,
      'identity_outputs_include_MAIN15_or_proxy18':any(v[0] in (15,18) for v in identities),
      'identity_table_scope':'One exact-match rebuild helper; absence here is not global HEVC rejection or proof all MAIN Opens use this rebuild.',
      'regions':[{'name':n,'instructions':r.im.dump(blob,a,z,V)} for n,a,z in regions]}


def run(out):
    prior=BASE/'stage28-main-frontend-binding/final-receipt.json'
    assert r.im.sha(prior.read_bytes())=='0b156a8f81a1de1b4077638b5325dda8a396fce249f43a072e444c2d8359e96c'
    for stage in ('stage25-mc-image-map','stage26-mc-open-routing','stage28-main-frontend-binding'):
        previous=json.loads((BASE/stage/'final-receipt.json').read_text())
        assert all(r.im.sha((ROOT/v['path']).read_bytes())==v['sha256'] for v in previous['files'])
    blob=(BASE/'stage2/extraction/files/nflasha3/av-cam.bin').read_bytes()
    assert r.im.sha(blob)==r.im.PINS['stage2/extraction/files/nflasha3/av-cam.bin']
    target,_,uhd,invalid=r.packet_variants()
    flows=[flow(blob,*target),flow(blob,*invalid),flow(blob,*target,state=1),
      flow(blob,*target,source=MC_ID),flow(blob,*target,state=2),
      flow(blob,*uhd,state=2),flow(blob,*invalid,state=2)]
    flag=post_subevent_flag(blob,target[1],target[2])
    frames=[frame_conversion(blob,*v) for v in [(30000,1001,1,3),(30,1,1,5),(60000,1001,1,5),(25,1,1,2)]]
    dims=[dimensions(blob,*v) for v in [(1920,1080),(3840,2160)]]
    proof={'status':'PASS_ORIGINAL_MAIN_FRONTEND_QUEUE_COPY_AND_REBUILD_FRAGMENTS_ONLY',
      'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
      'frontend_flows':flows,'independent_post_subevent_flag':flag,
      'SET_REC_FORMAT_frame_helper_cases':frames,'SET_REC_FORMAT_dimension_cases':dims,
      'static_evidence':static_evidence(blob),
      'findings':[
        'Under numeric frontend state0/1 and a different-MC-ID source fixture, Open is copied into a local pending slot and frontend wrapper returns1 without hardware action. Same-ID branch forwards to state wrapper/task hook.',
        'Under numeric state2 fixture, target/stockUHD/invalid video packets are copied unchanged into two frontend stores and a subevent argument. Reconfiguration subevent and later forwarding remain unexecuted.',
        'State8 action contains a raw packet88=1 store after an unexecuted subevent. Independent suffix preserves all other packet bytes, but does not prove prior subevent has no effects.',
        'Separate CID0x8003/MID1 has original SET_REC_FORMAT diagnostic and invokes a rebuild helper. Dimension stores use its input fields, not hardcoded4K. Actual ordering and interaction with original MAIN Open remain unobserved.',
        'One rebuild FileFormat table has no outputs15/18; this is not a global encoding capability table or a demonstrated HEVC rejection.',
        'Rebuild frame helper maps30000/1001 to3 but exact30/1 to default5; this local enum result is not actual hardware60fps or camera rejection. Exact30.000 remains separate.'],
      'scope':'Independent partial-construction/numeric-state/post-subevent/rebuild fixtures. No real initialization, source identity, transport, full frontend reconfiguration, resource or hardware acceptance.',
      'actual_reconfiguration_subevents_task_clock_resource_hardware_executed':False,
      'native_output_adapters':False,'camera_or_remote_access_attempted':False,
      'modified_firmware_or_patch_exported':False,'goal_complete':False,'persistent_write_release':False}
    summary={'status':proof['status'],'frontend_flow_scenarios':len(flows),
      'post_subevent_flag_scenarios':1,'rebuild_frame_helper_cases':len(frames),
      'rebuild_dimension_cases':len(dims),'returned_frontend1_can_mean_queued_only':True,
      'target_packet_unchanged_in_state2_copy_fragment':True,
      'full_MAIN_rebuild_order_or_hardware_verified':False,'goal_complete':False,'persistent_write_release':False}
    assert r.im.sha(blob)==r.im.sha((BASE/'stage2/extraction/files/nflasha3/av-cam.bin').read_bytes())
    r.im.write_json(out/'frontend-open-results.json',proof);r.im.write_json(out/'summary.json',summary)
    r.im.write_json(out/'source-receipt.json',{'script':str(Path(__file__).relative_to(ROOT)),
      'script_sha256':r.im.sha(Path(__file__).read_bytes()),'frontend_harness_sha256':r.im.sha(Path(f.__file__).read_bytes()),
      'raw_guest_harness_sha256':r.im.sha(Path(r.__file__).read_bytes()),'raw_map_helper_sha256':r.im.sha(Path(r.im.__file__).read_bytes()),
      'raw_image_sha256':r.im.sha(blob),'previous_manifest_sha256':r.im.sha(prior.read_bytes()),
      'packet_source_sha256':r.im.sha((BASE/'stage23-encoder-boundary/run-corrected-20261025/encoder-boundary-results.json').read_bytes()),
      'volume_uuid':r.im.VOLUME,'result_sha256':r.im.sha((out/'frontend-open-results.json').read_bytes()),
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
