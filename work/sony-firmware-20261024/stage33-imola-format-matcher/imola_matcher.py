#!/usr/bin/env python3
"""Original IMOLA preset matcher; independent guest fragments, no camera I/O.

Native diagnostic and runtime-clear calls remain unexecuted boundaries. A
post-diagnostic matcher fixture is not a full resource/channel/Open execution.
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
sys.path.insert(0,str(BASE/'stage32-resource-open-descriptor'))
import resource_descriptor as s
r,V=s.r,s.V
OWNER=r.ARENA+0x310000
PARAM=r.ARENA+0x330000
MESSAGE=r.ARENA+0x340000
META=r.ARENA+0x350000
TABLE,STRIDE,COUNT=0x395108,0x90,0x2b1


class MatcherGuest(r.RawGuest):
    """Same read-only image and write fences; enough instructions for689 rows."""
    def __init__(self,blob):
        self.rows=[]
        super().__init__(blob,[(0x225eb8,0x225ee0),(0x225fa0,0x226128)],
                         {0x27d528:'before_original_matcher_diagnostic'})

    def code(self,u,pc,size,user):
        if pc==V+0x225ff4:self.rows.append(u.reg_read(r.reg.UC_ARM64_REG_X0))
        super().code(u,pc,size,user)

    def run(self,start):
        self.uc.emu_start(V+start,0,count=50000,timeout=1000000)
        assert self.reason is not None,'bounded matcher limit reached without return/boundary'
        return {'start_offset':hex(start),'reason':self.reason,
          'stop_pc':hex(self.uc.reg_read(r.reg.UC_ARM64_REG_PC)),
          'pcs':[hex(p) for p in self.pcs],'writes':self.writes,
          'x0_to_x5':[hex(self.uc.reg_read(getattr(r.reg,'UC_ARM64_REG_X'+str(n)))) for n in range(6)],
          'instruction_limit':50000,'timeout_microseconds':1000000,
          'native_output_or_diagnostic_adapters':False}


def inventory(blob):
    rows=[]
    for i in range(COUNT):
        at=TABLE+i*STRIDE
        get=lambda p:struct.unpack_from('<I',blob,at+p)[0]
        rows.append({'index':i,'offset':hex(at),'stream_type':get(0),
          'input_frame_rate_limit':get(4),'coding_frame_rate':get(8),
          'input_scan_mode':get(0xc),'picture_quality':get(0x10),
          'chroma_format':get(0x14),'video_bit_len':get(0x18),
          'preset_id_untyped':hex(get(0x28)),
          'input_depth_list':list(struct.unpack_from('<7I',blob,at+0x40)),
          'width':struct.unpack_from('<H',blob,at+0x7e)[0],
          'height':struct.unpack_from('<H',blob,at+0x80)[0]})
    return rows


def mandatory_rows(rows,d):
    # These direct equality predicates are necessary, not sufficient: the
    # native matcher also checks input fps and appended image-input fields.
    f=s.describe(d)
    return [x for x in rows if (x['stream_type'],x['coding_frame_rate'],x['input_scan_mode'],
      x['picture_quality'],x['chroma_format'],x['video_bit_len'],x['width'],x['height'])==
      (f['coding_enum'],f['frame_enum'],f['progressive_conversion_copy'],
       f['quality_enum'],f['chroma_enum'],f['depth_enum'],f['width'],f['height'])]


def match(blob,label,descriptor,extra88,extra8c,rows):
    # The original matcher reads beyond the0x88 descriptor. These appended
    # inputs are explicit conditional fixtures, not observed camera values.
    value=descriptor+struct.pack('<4I',extra88,extra8c,0,0)
    assert len(value)==0x98
    m=MatcherGuest(blob);m.uc.mem_write(PARAM,value)
    m.regs(x0=OWNER,x1=PARAM)
    prefix=m.run(0x225eb8)
    assert prefix['reason']=='boundary: before_original_matcher_diagnostic'
    sp=m.uc.reg_read(r.reg.UC_ARM64_REG_SP)
    assert m.uc.reg_read(r.reg.UC_ARM64_REG_X19)==PARAM
    prefix.update(scope='Original matcher frame/arguments through first diagnostic; diagnostics not executed.')
    # Explicit independent post-diagnostic entry. W20=3 is the original
    # MOVW20 at0x225f94, not a fabricated backend result. Original saved frame,
    # input memory and X19 are fixture preconditions across excluded logging.
    m.regs(x20=3);s.reset_without_stack(m)
    calculation=m.run(0x225fa0)
    assert calculation['reason']=='returned'
    raw=m.uc.reg_read(r.reg.UC_ARM64_REG_W0)
    index=raw if raw<0x80000000 else raw-(1<<32)
    assert index==-1 or 0<=index<COUNT
    assert m.read(PARAM,0x98)==value
    assert m.uc.reg_read(r.reg.UC_ARM64_REG_SP)==sp+0xb0
    necessary=mandatory_rows(rows,descriptor)
    if not necessary:assert index==-1
    if index>=0:assert index in {x['index'] for x in necessary}
    calculation.update(matched_row=index,examined_row_indices=m.rows,
      precondition='Independent post-diagnostic entry0x225fa0. Original saved matcher frame/X19/input are retained fixtures, W20=3 from original0x225f94 constant. Unexecuted diagnostics are assumed not to change them; not proven neutral.',
      scope='Original table-loop return only, no channel creation/encoder/backend acceptance.')
    return {'label':label,'descriptor_hex':descriptor.hex(),
      'appended_fixture':{'raw88':extra88,'raw8c':extra8c,
        'actual_input_image_tail_not_observed':True},
      'entry_prefix':prefix,'independent_matcher':calculation,
      'necessary_equality_rows':[x['index'] for x in necessary],
      'matched_row':rows[index] if index>=0 else None,
      'full_matcher_with_diagnostics_or_hardware_executed':False}


def route(blob,label,envelope,source=0x805700f9,cid=0x2103):
    m=r.RawGuest(blob,[(0x245dac,0x246040),(0x249ad0,0x249b20)],
       {0x27d528:'before_resource_receiver_diagnostic'})
    msg=bytearray(envelope);struct.pack_into('<H',msg,0,cid)
    m.uc.mem_write(MESSAGE,bytes(msg));m.uc.mem_write(OWNER+0x18,r.p64(META))
    m.uc.mem_write(META,struct.pack('<I',0))
    m.regs(x0=OWNER,x1=MESSAGE,x2=source)
    result=m.run(0x245dac)
    assert result['reason']=='boundary: before_resource_receiver_diagnostic'
    expected=0x249b1c if cid==0x2103 and source in (0x805700f9,0x805720f9) else 0x245e5c if cid!=0x2103 else 0x245f7c
    assert m.pcs[-2]==V+expected
    assert m.read(MESSAGE,0x90)==bytes(msg)
    result.update(label=label,source_ID_fixture=hex(source),CID=hex(cid),MID='0x0100',
      diagnostic_callsite=hex(expected),
      precondition='Independent already-received packet and constructed-field channel0 fixtures; no real source/registration/transport.',
      scope='Original source/CID/channel/MID route to first receiver diagnostic only; state/process250b70 and full handler not executed.')
    return result


def dispatch(blob,descriptor):
    m=r.RawGuest(blob,[(0x21e26c,0x21e2f4),(0x27cf58,0x27cf68),(0xd80,0xeec)],
      {0x2f67c:'before_unbound_runtime_clear',0x21ecf4:'before_table_based_channel_builder',
       0x21eafc:'before_alternative_channel_builder'})
    m.uc.mem_write(PARAM,descriptor);m.regs(x0=OWNER,x1=PARAM)
    prefix=m.run(0x21e26c)
    assert prefix['reason']=='boundary: before_unbound_runtime_clear'
    assert m.read(OWNER+0xe110,0x88)==descriptor
    sp=m.uc.reg_read(r.reg.UC_ARM64_REG_SP)
    m.uc.mem_write(sp+0x78,bytes(0x88));s.reset_without_stack(m)
    selected=m.run(0x21e2c0)
    stream=s.u32(descriptor,0x18)
    expected='before_alternative_channel_builder' if stream in (22,23) else 'before_table_based_channel_builder'
    assert selected['reason']=='boundary: '+expected
    selected.update(precondition='Independent post-clear entry with explicitly zero stack buffer; runtime clear not executed.',
      scope='Original stream predicate and call choice, not full builder/channel creation.')
    return {'stream_type':stream,'entry_copy_prefix':prefix,'independent_post_clear_dispatch':selected}


def quality_controls(blob):
    result=[]
    for api_quality,expected in ((22,4),(8,6),(24,6)):
        m=r.RawGuest(blob,[(0x134fcc,0x1352f8)],{0x27d528:'before_diagnostic'})
        m.regs(x0=OWNER,x1=api_quality);case=m.run(0x134fcc)
        assert case['reason']=='returned'
        out=m.uc.reg_read(r.reg.UC_ARM64_REG_W0);assert out==expected
        result.append(dict(case,input_API_quality=api_quality,resource_quality=out,
          scope='Original quality converter only; not actual upstream model selection or bitrate.'))
    return result


def quality_names(blob,values):
    result=[]
    for v in sorted(values):
        m=r.RawGuest(blob,[(0x27dd64,0x27dd88)],{});m.regs(x0=v)
        case=m.run(0x27dd64);assert case['reason']=='returned'
        off=m.uc.reg_read(r.reg.UC_ARM64_REG_X0)-V
        result.append(dict(case,resource_quality=v,original_name=r.im.cstring(blob,off,100),
          string_offset=hex(off),scope='Original pure diagnostic name; not actual bitrate.'))
    return result


def caller_branch(blob,index):
    m=r.RawGuest(blob,[(0x21ed28,0x21ed30)],
       {0x21efc4:'no_matching_preset_path',0x21ed30:'matching_preset_row_path'})
    m.regs(x23=index&0xffffffff)
    result=m.run(0x21ed28)
    assert result['reason']=='boundary: '+('no_matching_preset_path' if index==-1 else 'matching_preset_row_path')
    result.update(index_fixture=index,
       precondition='Independent post-matcher/post-diagnostic branch with actual lookup scalar supplied as fixture; full caller and diagnostic effects unexecuted.',
       scope='Original branch consumes missing-preset return; neither arm/backend executed.')
    return result


def static_evidence(blob):
    regions=[('resource source/CID router',0x245dac,0x245f18),
      ('resource channel/MID switch',0x249ad0,0x249b64),
      ('resource Open state wrapper',0x250b70,0x250c74),
      ('common handler copy and builder choice',0x21e26c,0x21e2f4),
      ('table builder entry and return handling',0x21ecf4,0x21ed80),
      ('no-matching-preset handling',0x21efc4,0x21f048),
      ('original matcher incl excluded diagnostics',0x225eb8,0x226128),
      ('alternate-stream predicate',0x27cf58,0x27cf68),
      ('resource API quality converter',0x134fcc,0x1352f8),
      ('quality diagnostic name',0x27dd64,0x27dd88)]
    return {'regions':[{'name':n,'instructions':r.im.dump(blob,a,z,V)} for n,a,z in regions],
      'MID100_action_table':{'offset':'0x37ea48','entry0_target':hex(struct.unpack_from('<Q',blob,0x37ea48)[0])},
      'diagnostics':[{'offset':hex(off),'text':r.im.cstring(blob,off,180)} for off in (0x44331c,0x43d0f2,0x43d6ed,0x43d712)],
      'scope':'Original direct branch/data/diagnostic evidence. Actual construction/state/transport bridge from resource Open to common handler still not closed.'}


def run(out):
    prior=s.STAGE/'final-receipt.json'
    assert r.im.sha(prior.read_bytes())=='0ae57711bc1a8d5756c224de9c1666140700359789ae7a66ec9bcbc29f5807f2'
    previous=json.loads(prior.read_text())
    assert all(r.im.sha((ROOT/x['path']).read_bytes())==x['sha256'] for x in previous['files'])
    image=BASE/'stage2/extraction/files/nflasha3/av-cam.bin';blob=image.read_bytes()
    assert r.im.sha(blob)==r.im.PINS['stage2/extraction/files/nflasha3/av-cam.bin']
    old=json.loads((s.STAGE/'run-enum-bound-20261025/resource-descriptor-results.json').read_text())
    target,proxy,uhd=[bytes.fromhex(x['descriptor_hex']) for x in old['cases'][:3]]
    packet=bytearray(r.packet_variants()[0][1]);packet[0x82]=24
    candidate=s.descriptor_case(blob,'artificial MAIN API-quality24 control',bytes(packet),15)
    d=bytes.fromhex(candidate['descriptor_hex'])
    assert [i for i,(u,v) in enumerate(zip(target,d)) if u!=v]==[0x38]
    assert s.u32(d,0x38)==6
    rows=inventory(blob)
    main_hd=[x for x in rows if (x['stream_type'],x['coding_frame_rate'],x['input_scan_mode'],
      x['chroma_format'],x['video_bit_len'],x['width'],x['height'])==(14,2,0,0,1,1920,1080)]
    assert {x['picture_quality'] for x in main_hd}=={6,34,39,53}
    assert not mandatory_rows(rows,target)
    cases=[match(blob,label,value,a,b,rows) for label,value in
      [('target MAIN FH',target),('matching proxy FH',proxy),('UHD control',uhd),('artificial MAIN FF',d)]
      for a,b in ((2,10),(2,1))]
    assert all(x['independent_matcher']['matched_row']==-1 for x in cases[:2])
    assert cases[2]['independent_matcher']['matched_row']==-1
    assert cases[3]['independent_matcher']['matched_row']==607
    assert cases[6]['independent_matcher']['matched_row']==386
    env=bytes.fromhex(old['cases'][0]['independent_sender_prefix']['envelope_hex'])
    routes=[route(blob,'MAIN source',env),route(blob,'proxy source fixture',env,source=0x805720f9),
       route(blob,'wrong CID',env,cid=0x2104),route(blob,'unrecognized source',env,source=0x805700fa)]
    alternate=bytearray(target);struct.pack_into('<I',alternate,0x18,22)
    dispatches=[dispatch(blob,v) for v in (target,proxy,bytes(alternate))]
    controls=quality_controls(blob);names=quality_names(blob,{4}|{x['picture_quality'] for x in main_hd})
    branches=[caller_branch(blob,i) for i in (-1,386)]
    proof={'status':'PASS_ORIGINAL_IMOLA_TABLE_MISMATCH_AND_CONDITIONAL_FF_MATCH',
      'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
      'inventory':{'offset':hex(TABLE),'row_bytes':STRIDE,'rows':COUNT,
        'table_sha256':r.im.sha(blob[TABLE:TABLE+STRIDE*COUNT]),'all_rows':rows,
        'MAIN_HD29_42010_rows':main_hd,'target_FH_necessary_rows':[],
        'scope':'Original689-row table and mandatory equality keys. No FH row for current target across all rows; table is not whole-camera capability inventory.'},
      'artificial_quality24_descriptor':candidate,'native_matcher_cases':cases,
      'resource_route_cases':routes,'common_handler_dispatch_cases':dispatches,
      'quality_controls':controls,'quality_names':names,'caller_branch_cases':branches,
      'static_evidence':static_evidence(blob),
      'finding':'Existing target resourcequalityFH has no mandatory matching preset. MAIN HD29.97 HEVC42010 entries do exist with qualitiesFF/QT35M/QT50M/QT9M; artificial APIquality24 convertsFF and conditionally matches row386. Real bitrate and upstream consistency remain unresolved.',
      'scope':'Original guest-only route/dispatch/matcher fragments with explicit excluded-clear/log preconditions and synthetic appended fields. Not whole handler, channel creation, transport, hardware or recovery.',
      'camera_or_remote_access_attempted':False,'native_output_or_diagnostic_adapters':False,
      'modified_firmware_or_patch_exported':False,'goal_complete':False,'persistent_write_release':False}
    summary={'status':proof['status'],'original_table_rows':COUNT,'HEVC_rows':sum(x['stream_type'] in (14,21) for x in rows),
      'target_FH_necessary_matches':0,'MAIN_HD_quality_names':{x['resource_quality']:x['original_name'] for x in names},
      'artificial_FF_conditional_row':386,'native_matcher_scenarios':len(cases),
      'matcher_results':[{'label':x['label'],'tail':x['appended_fixture'],'row':x['independent_matcher']['matched_row']} for x in cases],
      'actual_16Mbps_hardware_or_restore_verified':False,'goal_complete':False,'persistent_write_release':False}
    assert r.im.sha(blob)==r.im.sha(image.read_bytes())
    r.im.write_json(out/'imola-matcher-results.json',proof);r.im.write_json(out/'summary.json',summary)
    r.im.write_json(out/'source-receipt.json',{'script':str(Path(__file__).relative_to(ROOT)),
      'script_sha256':r.im.sha(Path(__file__).read_bytes()),'stage32_helper_sha256':r.im.sha(Path(s.__file__).read_bytes()),
      'raw_harness_sha256':r.im.sha(Path(r.__file__).read_bytes()),'raw_image_sha256':r.im.sha(blob),
      'previous_manifest_sha256':r.im.sha(prior.read_bytes()),'volume_uuid':r.im.VOLUME,
      'proof_sha256':r.im.sha((out/'imola-matcher-results.json').read_bytes()),
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
