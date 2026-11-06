#!/usr/bin/env python3
"""Original timing Open preparation and shared parameter writers, guest only.

No live transition, timing clock, input-component preparation, resource request,
hardware encoder, host firmware loader, camera interface or restore operation.
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
r,V=f.r,f.V
OWNER=f.TIMING_NORMAL
INPUT_IF=f.ENC+0x110878
EVENT,CONFIG_EVENT=(r.ARENA+n for n in (0x2c0000,0x2d0000))
TAG=0x12345678
OPEN_RANGES=[(0x194de8,0x194ef4),(0x194d24,0x194de8),(0x1a25a8,0x1a261c),(0xd80,0xeec)]


def fields(packet):
    return {'codec66':packet[0x66],'width':int.from_bytes(packet[0x68:0x6a],'little'),
      'height':int.from_bytes(packet[0x6a:0x6c],'little'),'frame80':packet[0x80],
      'progressive81':packet[0x81],'quality82':packet[0x82],
      'raw64':packet[0x64],'raw89':packet[0x89]}


def event(m,where,packet,fmt,tag=TAG):
    header=r.seed(m,packet,fmt)
    value=bytearray(header[8:0x30])+bytearray(packet)+bytearray(0x18)
    struct.pack_into('<Q',value,8,where+0x28)
    struct.pack_into('<I',value,0xc0,tag)
    m.uc.mem_write(where,bytes(value))
    return bytes(value)


def setup(blob):
    m=r.RawGuest(blob,OPEN_RANGES+[(0x1956e0,0x195724)],
       {0x1454f4:'before_input_if_preparation',0x195724:'before_configuration_command_builder',
        0x27d528:'before_original_timing_error_diagnostic'})
    # Only fields required by these post-transition action fragments, all based
    # on original constructor stores. This is not full native construction.
    for at,value in [(OWNER,V+0x3711c0),(OWNER+8,f.CTX),(OWNER+0x20,INPUT_IF),
       (OWNER+0x3f8,V+0x371358),(OWNER+0x420,V+0x3713a0),(OWNER+0x448,V+0x370dd0),
       (f.CTX,r.CONFIG),(f.CTX+8,f.ENC+8)]:m.uc.mem_write(at,r.p64(value))
    return m


def open_action(blob,label,packet,fmt,m=None):
    m=m or setup(blob)
    original=event(m,EVENT,packet,fmt)
    f.reset_trace(m);m.regs(x0=OWNER,x1=EVENT)
    result=m.run(0x194de8)
    assert m.read(OWNER+0x38,0x98)==packet
    assert m.read(EVENT,0xd8)==original
    if packet[0x80]>=10:
        assert result['reason']=='boundary: before_original_timing_error_diagnostic'
        result.update(label=label,input_fields=fields(packet),prepared_event=None,
           scope='Original packet copy reached invalid-frame timing diagnostic; diagnostic and failure handling not executed.')
        return result
    assert result['reason']=='boundary: before_input_if_preparation'
    assert m.uc.reg_read(r.reg.UC_ARM64_REG_X0)==INPUT_IF
    expected_iface=OWNER+(0x3f8 if packet[0x81]==0 else 0x448 if packet[0x80]<=3 else 0x420)
    actual_iface=int.from_bytes(m.read(OWNER+0x470,8),'little');assert actual_iface==expected_iface
    mode=2 if packet[0x64]==1 else 3 if packet[0x89]==1 else 0
    assert int.from_bytes(m.read(OWNER+0x28,4),'little')==mode
    assert int.from_bytes(m.read(OWNER+0x2c,4),'little')==fmt
    ptr=m.uc.reg_read(r.reg.UC_ARM64_REG_X1);prepared=m.read(ptr,0xd4)
    assert prepared[0x28:0xc0]==packet
    assert int.from_bytes(prepared[8:16],'little')==ptr+0x28
    assert int.from_bytes(prepared[0x10:0x14],'little')==0x98
    assert prepared[0x1c]==fmt
    nominal=struct.unpack_from('<I',blob,0x314860+packet[0x80]*4)[0]
    tail=list(struct.unpack_from('<5I',prepared,0xc0))
    assert tail==[TAG,mode,nominal,1,int.from_bytes(packet[0x86:0x88],'little')]
    result.update(label=label,input_fields=fields(packet),FileFormat_after=fmt,
       selected_timing_interface_offset=hex(actual_iface-OWNER),mode_scalar=mode,
       nominal_rate_scalar=nominal,prepared_event_hex=prepared.hex(),
       prepared_event_video98_unchanged=True,prepared_event_tail_words=tail,
       scope='Original numeric-state2 Open action on independent post-transition/constructed-field fixtures through first input_if call. No input_if preparation, resource or hardware acceptance.')
    return result


def config_prefix(m,packet,fmt):
    original=event(m,CONFIG_EVENT,packet,fmt,tag=0)
    f.reset_trace(m);m.regs(x0=OWNER,x1=CONFIG_EVENT)
    result=m.run(0x1956e0)
    assert result['reason']=='boundary: before_configuration_command_builder'
    assert m.read(OWNER+0x38,0x98)==packet
    assert int.from_bytes(m.read(OWNER+0x2c,4),'little')==fmt
    assert m.read(CONFIG_EVENT,0xd8)==original
    result.update(video_fields_after=fields(packet),FileFormat_after=fmt,
       scope='Original SET_REC_FORMAT owner copy prefix only; command-builder/remaining configuration side effects not executed.')
    return result


def writer_order(blob,target,fmt):
    alternate=bytearray(target)
    alternate[0x66]=0
    struct.pack_into('<HH',alternate,0x68,3840,2160)
    alternate[0x80]=5
    alternate=bytes(alternate)
    m=setup(blob)
    before=config_prefix(m,alternate,5)
    opened=open_action(blob,'target after alternate config prefix',target,fmt,m)
    assert m.read(OWNER+0x38,0x98)==target
    after=config_prefix(m,alternate,5)
    assert m.read(OWNER+0x38,0x98)==alternate
    return {'alternate_configuration_prefix':before,'target_Open_action':opened,
       'alternate_configuration_prefix_after_Open':after,
       'shared_video_storage':'timing_normal+0x38, size0x98',
       'shared_FileFormat_storage':'timing_normal+0x2c',
       'precondition':'Artificial order of independent original action prefixes; alternate packet/FileFormat5 is a marked fixture, not a validated actual SET_REC_FORMAT message. Actual timing state order/guards and rest of config action unexecuted.',
       'scope':'Demonstrates overlapping whole-packet writes, not a real race, wrong runtime order or required patch strategy.'}


def static_evidence(blob):
    types=[r.im.vtable(blob,off,name) for off,name in [
      (0x371348,'N8sfmc_enc6timing17sfmc_enc_timing_iILNS0_9my_mode_tE6EEE'),
      (0x371390,'N8sfmc_enc6timing17sfmc_enc_timing_iILNS0_9my_mode_tE7EEE'),
      (0x370dc0,'N8sfmc_enc6timing17sfmc_enc_timing_iILNS0_9my_mode_tE8EEE'),
      (0x33f420,'N8sfmc_enc17sfmc_enc_input_ifE')]]
    regions=[('original Open action',0x194de8,0x194ef4),
      ('progressive/frame timing-interface selector',0x194d24,0x194de8),
      ('nominal frame helper',0x1a25a8,0x1a261c),
      ('SET_REC_FORMAT same-owner packet copy',0x1956e0,0x195724),
      ('input_if first setup',0x1454f4,0x145530),('input_if next command',0x145530,0x145554),
      ('input_if constructor and dependency fields',0xa6e34,0xa6e8c),
      ('normal timing constructor callback field',0x193d88,0x193dac),
      ('normal timing child-interface stores',0x193e40,0x193e94)]
    return {'types':types,'nominal_rate_table_offset':'0x314860',
      'nominal_rate_table':list(struct.unpack_from('<10I',blob,0x314860)),
      'regions':[{'name':n,'instructions':r.im.dump(blob,a,z,V)} for n,a,z in regions],
      'next_input_component_calls':['0x134568','0x1466d8 ->0x148d3c','0x141524','0x145530 ->0x1345dc'],
      'scope':'Original static binding and call anchors; actual input component/resource initialization or hardware not observed.'}


def run(out):
    prior=BASE/'stage30-frontend-pending-consumption/final-receipt.json'
    assert r.im.sha(prior.read_bytes())=='63ca2e08204f9bd1ed8457806e494a3834b79f17304707a2c0b07f6951d64871'
    for name in ('stage25-mc-image-map','stage26-mc-open-routing','stage28-main-frontend-binding','stage30-frontend-pending-consumption'):
        manifest=json.loads((BASE/name/'final-receipt.json').read_text())
        assert all(r.im.sha((ROOT/v['path']).read_bytes())==v['sha256'] for v in manifest['files'])
    blob=(BASE/'stage2/extraction/files/nflasha3/av-cam.bin').read_bytes()
    assert r.im.sha(blob)==r.im.PINS['stage2/extraction/files/nflasha3/av-cam.bin']
    target,proxy,uhd,invalid=r.packet_variants()
    variations=[target,proxy,uhd]
    for label,off,value in [('invalid codec only',0x66,0xff),('raw64=1',0x64,1),
             ('raw89=1',0x89,1),('interlace flag fixture',0x81,0)]:
        b=bytearray(target[1]);b[off]=value;variations.append((label,bytes(b),15))
    variations.append(invalid)
    cases=[open_action(blob,*item) for item in variations]
    ordering=writer_order(blob,target[1],target[2])
    proof={'status':'PASS_ORIGINAL_TIMING_OPEN_PREPARATION_AND_SHARED_WRITER_SCOPE_ONLY',
      'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
      'Open_action_cases':cases,'independent_writer_order_fixture':ordering,
      'static_evidence':static_evidence(blob),
      'findings':[
        'Target HD/frame3/progressive1 selects timing interface+0x448 and nominal scalar30; factory UHD/frame5 selects+0x420 and60. These choices are not codec/resolution capability checks.',
        'Original Open action copies0x98 video bytes unchanged, preserves outer FileFormat15/18, computes local mode and constructs a0xd4 event with owned packet pointer before0x1454f4 sfmc_enc_input_if preparation.',
        'Invalid codec alone still reaches that input boundary; invalid frame enum reaches an original diagnostic. Neither observation establishes actual unsupported-format handling or hardware acceptance.',
        'SET_REC_FORMAT prefix0x1956e0 and Open action0x194de8 write the same owner video+0x38 and FileFormat+0x2c. Artificial prefix ordering demonstrates overwrite coverage, not actual runtime order, a race or a bug.',
        'Actual input component preparation, command, resource/VCD, clock/state/merge policy and replies remain unexecuted.'],
      'scope':'Independent post-transition/constructed-field Open action and artificial writer-order fixtures. No real state transitions, valid full configuration, backend outputs, resources or hardware.',
      'native_output_adapters':False,'camera_or_remote_access_attempted':False,
      'input_if_resource_clock_hardware_or_restore_executed':False,
      'modified_firmware_or_patch_exported':False,'goal_complete':False,'persistent_write_release':False}
    summary={'status':proof['status'],'Open_action_scenarios':len(cases),
      'shared_writer_order_scenarios':1,'shared_writer_order_phases':3,
      'target_interface_offset':'0x448','target_nominal_rate':30,
      'target_video_packet_unchanged_before_input_if':True,
      'shared_whole_video_and_FileFormat_storage':True,
      'actual_hardware_or_restore_verified':False,'goal_complete':False,'persistent_write_release':False}
    assert r.im.sha(blob)==r.im.sha((BASE/'stage2/extraction/files/nflasha3/av-cam.bin').read_bytes())
    r.im.write_json(out/'timing-parameter-results.json',proof);r.im.write_json(out/'summary.json',summary)
    r.im.write_json(out/'source-receipt.json',{'script':str(Path(__file__).relative_to(ROOT)),
      'script_sha256':r.im.sha(Path(__file__).read_bytes()),'constructor_helper_sha256':r.im.sha(Path(f.__file__).read_bytes()),
      'raw_guest_harness_sha256':r.im.sha(Path(r.__file__).read_bytes()),'raw_map_helper_sha256':r.im.sha(Path(r.im.__file__).read_bytes()),
      'raw_image_sha256':r.im.sha(blob),'previous_manifest_sha256':r.im.sha(prior.read_bytes()),
      'packet_source_sha256':r.im.sha((BASE/'stage23-encoder-boundary/run-corrected-20261025/encoder-boundary-results.json').read_bytes()),
      'volume_uuid':r.im.VOLUME,'result_sha256':r.im.sha((out/'timing-parameter-results.json').read_bytes()),
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
