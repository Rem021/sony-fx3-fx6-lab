#!/usr/bin/env python3
"""Private MAIN16M data fixture through original preset parameter packing.

The fixture's guarded pointer/rate changes are HOST setup of guest RAM, not an
implemented native firmware hook. Original image stays RX. No live constructor,
buffer/channel/HAL submission, module, camera, restore or persistent patch.
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
sys.path.insert(0,str(BASE/'stage35-hevc-preset-defaults'))
import preset_defaults as v
r,V=v.r,v.V
f=v.u.q.s.t.f
A=r.ARENA+0x100000
B=r.ARENA+0x180000
DESC=r.ARENA+0x300000
INPUT=r.ARENA+0x310000
RESULT=r.ARENA+0x311000
ROWBLOCK=r.ARENA+0x312000
PACKETS=[r.ARENA+0x320000+i*0x1000 for i in range(6)]
PRESET=V+0x3c5798
COPY=A+0xe010
ID=0x19450
RATE=16000000
RANGES=[(0x21e26c,0x21e2c0),(0x21edc8,0x21eeb8),(0x2261a4,0x226364),
 (0x22c3cc,0x22c430),(0x27da84,0x27da9c),(0xd80,0xeec),
 (0x225b7c,0x225e40),(0x221fd0,0x22211c)]


class CandidateGuest(r.RawGuest):
    def __init__(self,blob):
        super().__init__(blob,RANGES,{0x2f67c:'before_unbound_runtime_clear',
           0x21dd54:'before_actual_buffer_and_channel_preparation',
           0x22211c:'after_rate_fields_before_other_parameter_inputs',
           0x27d528:'before_unexpected_original_diagnostic'})

    def run(self,start):
        self.uc.emu_start(V+start,0,count=20000,timeout=1000000)
        assert self.reason is not None,'bounded guest execution limit reached'
        return {'start_offset':hex(start),'reason':self.reason,
          'stop_pc':hex(self.uc.reg_read(r.reg.UC_ARM64_REG_PC)),
          'pcs':[hex(p) for p in self.pcs],'writes':self.writes,
          'x0_to_x5':[hex(self.uc.reg_read(getattr(r.reg,'UC_ARM64_REG_X'+str(n)))) for n in range(6)],
          'native_output_or_diagnostic_adapters':False}


def phase(m,label,start,**regs):
    f.reset_trace(m);m.regs(**regs);result=m.run(start)
    result['label']=label
    return result


def put32(m,at,value):m.uc.mem_write(at,struct.pack('<I',value))


def selection(m,owner,label):
    result=phase(m,label,0x21edc8,x19=owner,x20=ROWBLOCK,x21=DESC,
       x26=V+v.CREATE_TABLE+386*0x90,x22=ID)
    assert result['reason']=='boundary: before_actual_buffer_and_channel_preparation'
    assert int.from_bytes(m.read(owner+0xe000,8),'little')==PRESET
    assert int.from_bytes(m.read(owner+0xe470,4),'little')==ID
    result.update(precondition='Independent post-match/post-log row386 fragment on partial owner fixture; actual state/constructor/channel not executed.',
       scope='Original row marshalling and complete preset selection only.')
    return result


def prepare(m,owner,label):
    result=phase(m,label,0x21e26c,x0=owner,x1=DESC)
    assert result['reason']=='boundary: before_unbound_runtime_clear'
    assert m.read(owner+0xe110,0x88)==m.read(DESC,0x88)
    result.update(scope='Original descriptor copy before runtime clear; rest of construction/Open unexecuted.')
    return result


def default_query(m,owner,label,expected):
    result=phase(m,label,0x225b7c,x0=owner,x8=RESULT)
    assert result['reason']=='returned'
    values=struct.unpack_from('<3Q',m.read(RESULT,24))
    assert values==(25999360,expected,26000000)
    result.update(trace=values[0],target=values[1],cpb=values[2],
       source_pointer=hex(int.from_bytes(m.read(owner+0xe000,8),'little')),
       scope='Original selected-record decoder only; no actual current HAL rate readback.')
    return result


def pack(m,owner,dest,label,expected):
    # Explicit independent post-helper/post-diagnostic caller inputs. Only the
    # three rate words and preceding scalar copies are executed, not the full
    # constructor or later firmware command/HAL submission.
    m.uc.mem_write(dest,bytes([0xa5])*0x40)
    result=phase(m,label,0x221fd0,x21=owner,x22=dest,x20=INPUT)
    assert result['reason']=='boundary: after_rate_fields_before_other_parameter_inputs'
    value=m.read(dest,0x38);words=struct.unpack_from('<3I',value,0x2c)
    trace=((words[1]>>8)+1)<<(6+(words[1]&255))
    target=((words[0]>>8)+1)<<(6+(words[0]&255))
    cpb=((words[2]>>8)+1)<<(4+(words[2]&255))
    assert (trace,target,cpb)==(25999360,expected,26000000)
    result.update(partial_parameter_block_hex=value.hex(),target_word=hex(words[0]),
       trace_word=hex(words[1]),cpb_word=hex(words[2]),decoded_target=target,
       precondition='Independent original HEVC packing fragment0x221fd0. Owner/preset pointer, parameter output and input field+d0=0 are explicit fixtures. Earlier helpers/logs and all later fields/firmware/HAL not executed.',
       scope='Original selected-record read and packed rate fields only, not accepted whole packet or hardware.')
    return result


def guard(m,blob):
    # Guard only the OFFLINE fixture mutation. This is not a native admission,
    # reference-lifetime, state, code-publication or physical camera policy.
    data=m.read(A+0xe110,0x88)
    expected=(0,2,1920,1080,14,2,0,6,0,1)
    actual=(struct.unpack_from('<I',data,0)[0],struct.unpack_from('<I',data,4)[0],
      struct.unpack_from('<H',data,8)[0],struct.unpack_from('<H',data,10)[0],
      struct.unpack_from('<I',data,0x18)[0],struct.unpack_from('<I',data,0x24)[0],
      struct.unpack_from('<I',data,0x28)[0],struct.unpack_from('<I',data,0x38)[0],
      struct.unpack_from('<I',data,0x78)[0],struct.unpack_from('<I',data,0x7c)[0])
    assert actual==expected
    assert int.from_bytes(m.read(A+0xe470,4),'little')==ID
    assert int.from_bytes(m.read(A+0xe000,8),'little')==PRESET
    assert m.read(PRESET,0x100)==blob[0x3c5798:0x3c5898]
    assert COPY+0x100==A+0xe110


def static_evidence(blob):
    regions=[('original parameter copy and rates packing',0x221fd0,0x22211c),
      ('surrounding unexecuted helper/log before packing',0x221ec0,0x221fd0),
      ('unexecuted next fields and later branches',0x22211c,0x222240),
      ('existing private buffer path for a different streaming mode',0x226364,0x2265e4),
      ('preset selector',0x2261a4,0x226364),
      ('original input descriptor copy',0x21e26c,0x21e2c0),
      ('selected record decoder',0x225b7c,0x225e40)]
    return {'regions':[{'name':name,'instructions':r.im.dump(blob,a,z,V)} for name,a,z in regions],
      'existing_private_buffer_scope':'0x226364 copies another streaming template to common+e010; this is not native MAIN FF cloning support. This stage calls only generic original memcpy for its explicit FF data fixture.',
      'rate_destination_offsets':{'target':'partial_parameter_block+0x2c','trace':'partial_parameter_block+0x30','cpb':'partial_parameter_block+0x34'},
      'scope':'Original byte/packing/layout anchors only; all actual construction/state/lifetime/HAL semantics remain outside these independent fragments.'}


def run(out):
    prior=v.STAGE/'final-receipt.json'
    assert r.im.sha(prior.read_bytes())=='aa0312ec3026f1ade12d375777ed6255a763ac7ddfc16c07a4b813b1285ff0c3'
    manifest=json.loads(prior.read_text());assert all(r.im.sha((ROOT/e['path']).read_bytes())==e['sha256'] for e in manifest['files'])
    image=BASE/'stage2/extraction/files/nflasha3/av-cam.bin';blob=image.read_bytes()
    assert r.im.sha(blob)==r.im.PINS['stage2/extraction/files/nflasha3/av-cam.bin']
    old=json.loads((v.u.q.STAGE/'run-20261025/imola-matcher-results.json').read_text())
    descriptor=bytes.fromhex(old['artificial_quality24_descriptor']['descriptor_hex'])
    source=blob[0x3c5798:0x3c5898]
    assert descriptor[0x18]==14 and source[0]==14
    m=CandidateGuest(blob);m.uc.mem_write(DESC,descriptor)
    phases=[]
    for owner,name,dest in ((A,'A',PACKETS[0]),(B,'B',PACKETS[1])):
        phases.extend((prepare(m,owner,name+' descriptor-copy prefix'),selection(m,owner,name+' original preset selection'),
          default_query(m,owner,name+' original default',24498176),pack(m,owner,dest,name+' original pack',24498176)))
    baseline_A=m.read(PACKETS[0],0x38);baseline_B=m.read(PACKETS[1],0x38)
    assert baseline_A==baseline_B
    guard(m,blob)
    copied=phase(m,'A copy FF record using original memcpy',0xd80,x0=COPY,x1=PRESET,x2=0x100)
    assert copied['reason']=='returned' and m.read(COPY,0x100)==source
    copied.update(scope='Original generic memcpy to object-local RAM in a new explicit fixture; not an implemented native MAIN writer/admission policy.')
    phases.append(copied)
    # Explicit candidate-fixture pointer setup, NOT an executed firmware hook.
    m.uc.mem_write(A+0xe000,r.p64(COPY))
    phases.append(default_query(m,A,'A unchanged private copy default',24498176))
    phases.append(pack(m,A,PACKETS[2],'A unchanged private copy pack',24498176))
    assert m.read(PACKETS[2],0x38)==baseline_A

    assert RATE%64==0 and 0<RATE//64-1<=0xffffff and m.read(COPY+0xac,1)==b'\0'
    # Explicit experiment input mutation: only one uint32 target coefficient.
    put32(m,COPY+0xb0,RATE//64-1)
    candidate=m.read(COPY,0x100)
    changed=[i for i,(a,b) in enumerate(zip(source,candidate)) if a!=b]
    assert changed and all(0xb0<=i<0xb4 for i in changed)
    phases.append(default_query(m,A,'A candidate16M selected-record decode',RATE))
    phases.append(pack(m,A,PACKETS[3],'A candidate16M pack',RATE))
    candidate_packet=m.read(PACKETS[3],0x38)
    changed_packet=[i for i,(a,b) in enumerate(zip(baseline_A,candidate_packet)) if a!=b]
    assert changed_packet and all(0x2c<=i<0x30 for i in changed_packet)
    phases.append(default_query(m,B,'B default after A candidate',24498176))
    phases.append(pack(m,B,PACKETS[4],'B pack after A candidate',24498176))
    assert m.read(PACKETS[4],0x38)==baseline_B
    assert m.read(PRESET,0x100)==source

    # Actual ORIGINAL selector rewires A to immutable default. Previously
    # prepared parameter blocks and private copy are intentionally retained.
    phases.append(selection(m,A,'A original selector re-entry'))
    phases.append(default_query(m,A,'A default after pointer re-selection',24498176))
    assert m.read(PACKETS[3],0x38)==candidate_packet and m.read(COPY,0x100)==candidate
    phases.append(pack(m,A,PACKETS[5],'A fresh pack after pointer re-selection',24498176))
    assert m.read(PACKETS[5],0x38)==baseline_A and len(phases)==18
    assert m.read(DESC,0x88)==descriptor and m.read(B+0xe110,0x88)==descriptor
    proof={'status':'PASS_PRIVATE_FF16M_DATA_FIXTURE_ORIGINAL_PACKING_AND_PENDING_SCOPE',
      'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
      'phases':phases,'original_record_sha256':r.im.sha(source),
      'candidate_data_fixture':{'owner':'A','source_preset_id':'0x19450','destination_offset':'common+0xe010',
        'record_hex':candidate.hex(),'changed_source_byte_offsets':[hex(i) for i in changed],
        'target_coefficient':RATE//64-1,'original_trace_and_CPB_preserved':True,
        'producer':'Explicit host-controlled guest fixture pointer/uint32 mutation; not a native firmware hook or module.'},
      'packing':{'baseline_hex':baseline_A.hex(),'candidate_hex':candidate_packet.hex(),
        'changed_output_byte_offsets':[hex(i) for i in changed_packet],
        'original_target':24498176,'candidate_target':RATE,'other_owner_target':24498176,
        'only_target_word_changed':True},
      'pointer_reselection':{'native_original_selector_executed':True,
        'default_query_after':24498176,'fresh_packing_after':24498176,
        'previous_candidate_packet_still16000000':True,'private_copy_still_candidate':True,
        'scope':'Pointer/default reset only; not native recovery, safe-point/drain/reference proof or hardware rollback.'},
      'static_evidence':static_evidence(blob),
      'scope':'Original fragments consume explicit per-instance FF data copy and pack16M target, trace/CPB/other owner/source unchanged. No full constructor, actual writer/admission/state/generation/lifetime, whole valid packet/HAL/Open/recording/restore.',
      'native_output_or_diagnostic_adapters':False,'native_MAIN_copy_writer_implemented':False,
      'camera_or_remote_access_attempted':False,'bootable_firmware_loadable_module_or_device_patch_exported':False,
      'actual_hardware_or_restore_verified':False,'goal_complete':False,'persistent_write_release':False}
    summary={'status':proof['status'],'bounded_executions':18,
      'original_FF_default':24498176,'candidate_partial_parameter_target':RATE,
      'other_owner_unchanged':True,'only_target_word_changed':True,
      'pointer_reset_leaves_prepared_candidate_packet':True,
      'native_writer_or_actual_Hal_recording_or_restore_verified':False,
      'goal_complete':False,'persistent_write_release':False}
    assert r.im.sha(blob)==r.im.sha(image.read_bytes())
    r.im.write_json(out/'private-preset-results.json',proof);r.im.write_json(out/'summary.json',summary)
    r.im.write_json(out/'source-receipt.json',{'script':str(Path(__file__).relative_to(ROOT)),
      'script_sha256':r.im.sha(Path(__file__).read_bytes()),'stage35_helper_sha256':r.im.sha(Path(v.__file__).read_bytes()),
      'raw_harness_sha256':r.im.sha(Path(r.__file__).read_bytes()),'image_sha256':r.im.sha(blob),
      'previous_manifest_sha256':r.im.sha(prior.read_bytes()),'volume_uuid':r.im.VOLUME,
      'proof_sha256':r.im.sha((out/'private-preset-results.json').read_bytes()),
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
