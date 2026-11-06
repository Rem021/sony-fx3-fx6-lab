#!/usr/bin/env python3
"""Original HEVC preset selection and default-rate decode, immutable image.

No invented HAL/cache parameter bytes, firmware mutation, actual channel/HAL
application, camera access, restore or persistent patch. An independently
selected-row fixture does not execute the whole channel constructor.
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
sys.path.insert(0,str(BASE/'stage34-qos-request-and-feedback'))
import qos_paths as u
r,V=u.r,u.V
COMMON=r.ARENA+0x100000
DESC=r.ARENA+0x310000
BLOCK=r.ARENA+0x320000
RESULT=r.ARENA+0x330000
REPLY=r.ARENA+0x340000
PARAM=r.ARENA+0x350000
CREATE_TABLE=0x395108
PRESETS=0x3c4a98


class PresetGuest(r.RawGuest):
    def __init__(self,blob):
        self.preset_indices=[]
        super().__init__(blob,[(0x21edc8,0x21eeb8),(0x2261a4,0x226364),
          (0x22c3cc,0x22c430),(0x27da84,0x27da9c),(0xd80,0xeec),
          (0x225b7c,0x225e40),(0x246154,0x246200),(0x22c324,0x22c334)],
          {0x21dd54:'before_actual_buffer_and_channel_preparation',
           0x27d528:'before_original_error_diagnostic'})

    def code(self,uc,pc,size,user):
        if pc==V+0x226208:self.preset_indices.append(uc.reg_read(r.reg.UC_ARM64_REG_X13))
        super().code(uc,pc,size,user)

    def run(self,start):
        self.uc.emu_start(V+start,0,count=20000,timeout=1000000)
        assert self.reason is not None,'bounded preset loop limit reached'
        return {'start_offset':hex(start),'reason':self.reason,
          'stop_pc':hex(self.uc.reg_read(r.reg.UC_ARM64_REG_PC)),
          'pcs':[hex(p) for p in self.pcs],'writes':self.writes,
          'x0_to_x5':[hex(self.uc.reg_read(getattr(r.reg,'UC_ARM64_REG_X'+str(n)))) for n in range(6)],
          'instruction_limit':20000,'timeout_microseconds':1000000,
          'native_output_or_diagnostic_adapters':False}


def presets(blob):
    rows=[]
    for i in range(1024):
        at=PRESETS+i*0x100;assert at+0x100<=len(blob)
        stream=struct.unpack_from('<I',blob,at)[0]
        if stream==25:return rows,at
        rows.append({'index':i,'offset':hex(at),'stream_type':stream,
          'preset_id':hex(struct.unpack_from('<I',blob,at+0x20)[0]),
          'record_sha256':r.im.sha(blob[at:at+0x100]),
          'target_scale_byte_ac':blob[at+0xac],
          'target_value_minus1_b0':struct.unpack_from('<I',blob,at+0xb0)[0],
          'trace_scale_word_b4':struct.unpack_from('<I',blob,at+0xb4)[0],
          'trace_value_minus1_b8':struct.unpack_from('<I',blob,at+0xb8)[0]})
    raise AssertionError('No original type25 sentinel in bounded preset inventory')


def decode_case(blob,label,table_index,descriptor,expected):
    at=CREATE_TABLE+table_index*0x90
    ident=struct.unpack_from('<I',blob,at+0x28)[0]
    stream=struct.unpack_from('<I',descriptor,0x18)[0]
    assert struct.unpack_from('<I',blob,at)[0]==stream
    m=PresetGuest(blob)
    m.uc.mem_write(DESC,descriptor)
    u.put32(m,COMMON+0xe128,stream);u.put32(m,COMMON+0xe130,0)
    m.regs(x19=COMMON,x20=BLOCK,x21=DESC,x26=V+at,x22=ident)
    selected=m.run(0x21edc8)
    assert selected['reason']=='boundary: before_actual_buffer_and_channel_preparation'
    assert m.preset_indices==list(range(316))
    ptr=int.from_bytes(m.read(COMMON+0xe000,8),'little')
    off=ptr-V
    assert PRESETS<=off<PRESETS+316*0x100 and (off-PRESETS)%0x100==0
    assert struct.unpack_from('<I',blob,off+0x20)[0]==ident
    assert int.from_bytes(m.read(COMMON+0xe470,4),'little')==ident
    assert m.read(COMMON+0xdff8,8)==bytes(8) and m.read(COMMON+0xe008,8)==bytes(8)
    assert struct.unpack_from('<HH',m.read(BLOCK+8,4))==(
      struct.unpack_from('<H',descriptor,8)[0],struct.unpack_from('<H',descriptor,10)[0])
    selected.update(preset_id=hex(ident),selected_original_pointer=hex(ptr),
      selected_original_record_offset=hex(off),selected_original_record_hex=blob[off:off+0x100].hex(),
      examined_preset_indices=m.preset_indices,
      precondition='Independent post-match/post-diagnostic channel-builder fragment. Original row, preset-id and descriptor are supplied from earlier bounded matcher evidence; original saved context and non-interlaced field are fixtures. Earlier constructor/state/log effects not executed.',
      scope='Original row marshalling, native module predicate and full static preset lookup; stops before actual buffer/channel preparation. No whole Open or backend.')

    # No synthetic HAL parameters: decoder consumes the exact original pointer
    # produced by the native selector. The original firmware data stays RX.
    u.q.s.t.f.reset_trace(m);m.regs(x0=COMMON,x8=RESULT)
    decoded=m.run(0x225b7c);assert decoded['reason']=='returned'
    values=struct.unpack_from('<3Q',m.read(RESULT,24))
    assert values[:2]==tuple(expected)
    assert m.read(ptr,0x100)==blob[off:off+0x100]
    decoded.update(trace_default=values[0],target_default=values[1],cpb_default=values[2],
      source_pointer=hex(ptr),source_is_original_static_preset=True,
      precondition='Independent original default-query helper on original selector-created context; no HAL query, actual encoder or post-QoS feedback.',
      scope='Original static preset default decode; not measured bitrate or actual current encoder state.')

    u.q.s.t.f.reset_trace(m);u.put32(m,PARAM+0x738,stream)
    m.regs(x0=PARAM,x1=REPLY,x2=RESULT)
    reply=m.run(0x246154);assert reply['reason']=='returned'
    payload=m.read(REPLY,0x48)
    assert struct.unpack_from('<3Q',payload,0x20)==values
    reply.update(Open_comp_payload_hex=payload.hex(),
      precondition='Independent original completion marshaler with static-default decode as input; no actual completion event or reply transport.',
      scope='Original reply-field copy only; no live bitrate readback.')
    return {'label':label,'CreateCh_table_row':table_index,'preset_id':hex(ident),
      'input_descriptor_hex':descriptor.hex(),'original_row_and_preset_selection':selected,
      'independent_static_default_decode':decoded,'independent_reply_marshalling':reply,
      'whole_Open_actual_Hal_or_recording_verified':False}


def static_evidence(blob):
    regions=[('CreateCh row id and call to preset selector',0x21ed28,0x21eeb8),
      ('module selector',0x22c3cc,0x22c430),
      ('original preset selector',0x2261a4,0x226364),
      ('default pointer decoder',0x225b7c,0x225e40),
      ('Open-completion marshaller',0x246154,0x246200),
      ('default-query wrapper with unexecuted mutex/channel',0x22ba98,0x22baf0),
      ('normal timing constructor child binding',0x193e40,0x193e94),
      ('normal timing Open child choice',0x194d24,0x194d74),
      ('normal low-frame-rate implementation',0x18e5d4,0x18e694),
      ('earlier timing helper is synchronization submission',0x18d7ac,0x18d7f0),
      ('sync manager singleton source',0x1ad048,0x1ad0a4)]
    labels=[0x420720,0x42088e,0x424baf,0x4180ae,0x41818e,0x4181b9]
    return {'regions':[{'name':name,'instructions':r.im.dump(blob,a,z,V)} for name,a,z in regions],
      'bounded_original_diagnostic_labels':[{'offset':hex(p),'text':r.im.cstring(blob,p,180)} for p in labels],
      'scope_refinement':['common+e000 can point directly to original static HEVC preset data; previous synthetic HAL/cache exercise did not identify actual source. Original producer now bound for this branch.',
        'Earlier owner+278 strategy and1302 chain belong to timing/synchronization path. Constructor-selected normal progressive child has explicit timing deadline implementation; do not assume it is the MAIN bitrate producer.',
        'No claim that static default query is live HAL rate readback or that no later code can change runtime state.'],
      'clear_dispatch_unresolved':{'header20_pointer':hex(struct.unpack_from('<Q',blob,0x20)[0]),
        'API_slot_file_offset':'0x85c','original_slot_value':hex(struct.unpack_from('<Q',blob,0x85c)[0]),
        'scope':'Original slot zero, actual runtime binding not observed. No clear implementation supplied.'}}


def run(out):
    prior=u.STAGE/'final-receipt.json'
    assert r.im.sha(prior.read_bytes())=='cafe34fad1bb82ae1a6d0415945085d12e94bbae355ce3fbffcc51c8ff689d73'
    verified={}
    for name in ('stage33-imola-format-matcher','stage34-qos-request-and-feedback'):
        manifest=json.loads((BASE/name/'final-receipt.json').read_text())
        assert all(r.im.sha((ROOT/v['path']).read_bytes())==v['sha256'] for v in manifest['files'])
        verified[name]=len(manifest['files'])
    image=BASE/'stage2/extraction/files/nflasha3/av-cam.bin';blob=image.read_bytes()
    assert r.im.sha(blob)==r.im.PINS['stage2/extraction/files/nflasha3/av-cam.bin']
    rows,sentinel=presets(blob);assert len(rows)==316 and sentinel==0x3d8698
    old=json.loads((u.q.STAGE/'run-20261025/imola-matcher-results.json').read_text())
    ff=bytes.fromhex(old['artificial_quality24_descriptor']['descriptor_hex'])
    candidates=[('MAIN FF',386,ff,(25999360,24498176))]
    for label,i,qual,expected in [('MAIN QT35M',488,39,(34996224,33000000)),
        ('MAIN QT50M',529,34,(57999360,50000000)),('MAIN QT9M',583,53,(9999360,8800000))]:
        d=bytearray(ff);struct.pack_into('<I',d,0x38,qual)
        candidates.append((label,i,bytes(d),expected))
    previous=json.loads((u.q.s.STAGE/'run-enum-bound-20261025/resource-descriptor-results.json').read_text())
    candidates.extend([('proxy FH',607,bytes.fromhex(previous['cases'][1]['descriptor_hex']),(16000000,16000000)),
      ('UHD QT150M control',431,bytes.fromhex(previous['cases'][2]['descriptor_hex']),(159989760,150000000))])
    cases=[decode_case(blob,*v) for v in candidates]
    sharing={c['preset_id']:[i for i in range(689) if struct.unpack_from('<I',blob,CREATE_TABLE+i*0x90+0x28)[0]==int(c['preset_id'],16)] for c in cases}
    proof={'status':'PASS_ORIGINAL_STATIC_HEVC_PRESET_BINDING_AND_DEFAULT_RATES',
      'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
      'preset_table':{'offset':hex(PRESETS),'record_bytes':0x100,'records':rows,
        'sentinel_offset':hex(sentinel),'sentinel_type':25,
        'table_including_sentinel_sha256':r.im.sha(blob[PRESETS:sentinel+0x100])},
      'cases':cases,'CreateCh_rows_sharing_same_preset_id':sharing,
      'static_evidence':static_evidence(blob),'prior_manifest_files_verified':verified,
      'key_finding':'Original MAIN FF preset19450 selects static HEVC record13 and decodes target24498176/trace25999360, not16000000. Proxy FH preset1c26b decodes16000000. No actual channel or recording.',
      'scope':'Independent original post-match channel-builder fragment through full static lookup, original default decode and reply copy. No synthetic parameter records, whole Open/HAL/bitstream or recovery.',
      'native_output_or_diagnostic_adapters':False,'synthetic_Hal_parameter_records_used':False,
      'camera_or_remote_access_attempted':False,'modified_firmware_or_patch_exported':False,
      'actual_16Mbps_main_or_restore_verified':False,'goal_complete':False,'persistent_write_release':False}
    summary={'status':proof['status'],'preset_records':316,'scenarios':len(cases),'bounded_phases':len(cases)*3,
      'defaults':[{'label':c['label'],'preset_id':c['preset_id'],
       'target':c['independent_static_default_decode']['target_default'],
       'trace':c['independent_static_default_decode']['trace_default']} for c in cases],
      'MAIN_FF_default_not16M':True,'static_query_not_live_rate_readback':True,
      'actual_hardware_or_restore_verified':False,'goal_complete':False,'persistent_write_release':False}
    assert r.im.sha(blob)==r.im.sha(image.read_bytes())
    r.im.write_json(out/'preset-default-results.json',proof);r.im.write_json(out/'summary.json',summary)
    r.im.write_json(out/'source-receipt.json',{'script':str(Path(__file__).relative_to(ROOT)),
      'script_sha256':r.im.sha(Path(__file__).read_bytes()),'stage34_helper_sha256':r.im.sha(Path(u.__file__).read_bytes()),
      'raw_harness_sha256':r.im.sha(Path(r.__file__).read_bytes()),'image_sha256':r.im.sha(blob),
      'previous_manifest_sha256':r.im.sha(prior.read_bytes()),'volume_uuid':r.im.VOLUME,
      'proof_sha256':r.im.sha((out/'preset-default-results.json').read_bytes()),
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
