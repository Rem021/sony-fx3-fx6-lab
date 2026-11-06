#!/usr/bin/env python3
"""Original MAIN parameter conversion, not a complete MovieRecParam request."""
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
sys.path.insert(0,str(BASE/'stage104-native-card-recording-start-routing'))
import movie_start as prev
pp,r,im,APP=prev.pp,prev.r,prev.im,prev.APP
INPUT=pp.SCRATCH+0x100
OUTPUT=pp.SCRATCH+0x500
SP=prev.SP
PRIOR=prev.STAGE/'final-receipt.json'
PRIOR_SHA='e9b01fe5ce7b55015fd400e0af399d4d1b07b03b47a08df6192c476d4a6ef985'


def sha(raw):return hashlib.sha256(raw).hexdigest()


class Guest(prev.Guest):
    def __init__(self,seed):
        super().__init__(seed)
        self.allowed=[(0x2e6e5d8,0x2e6e628),(0x2e6ea58,0x2e6f074),(0x2e6f45c,0x2e6f4c0)]
        self.boundaries.update({0x2f6fe3c:'before_original_invalid_selector_diagnostic',
            0x2e5349c:'before_unexecuted_audio_parameter_helper'})


def one(seed,label,fmt,variant=0,quality=2,rate=15):
    m=Guest(seed)
    try:
        raw=bytearray(0x100)
        struct.pack_into('<4I',raw,0x10,rate,fmt,quality,variant)
        m.uc.mem_write(INPUT,bytes(raw))
        events=[m.phase('original mpr_SetMovieRecParam prologue '+label,0x2e6e5d8,
            stack_bytes=0xa00,sp=SP,x30=pp.STOP,x0=INPUT,x1=OUTPUT)]
        assert events[-1]['reason']=='boundary: before_original_app_logger'
        fp=m.uc.reg_read(r.reg.UC_ARM64_REG_X29)
        assert fp==SP-0x9f0 and m.uc.reg_read(r.reg.UC_ARM64_REG_X24)==INPUT
        # Earlier memset, naming, relay/proxy setup and diagnostics stay unexecuted.
        # Original frame/X24/X19 survive the original prologue; no output fixups.
        events.append(m.phase('independent original MAIN conversion '+label,0x2e6ea58,
            stack_bytes=0xa00))
        result=bytes(m.uc.mem_read(fp+0x480,12))
        accepted=events[-1]['reason']=='boundary: before_unexecuted_audio_parameter_helper'
        if label=='matrix':
            assert accepted
            expected={5:4,6:(5 if variant==0 else 7),7:(0 if variant==0 else 2),
                      8:(1 if variant==0 else 3),9:9,10:10,11:12,12:1}[fmt]
            assert struct.unpack('<3I',result)==(expected,6,3)
        else:
            assert events[-1]['reason']=='boundary: before_original_invalid_selector_diagnostic'
        assert bytes(m.uc.mem_read(INPUT,len(raw)))==bytes(raw)
        assert bytes(m.uc.mem_read(OUTPUT,0x40))==bytes([seed^0x3c])*0x40
        writes={}
        for e in events:
            for w in e['stores']:
                address=int(w['address'],16)
                if fp+0x480<=address<fp+0x48c:writes.setdefault(hex(address-(fp+0x310)),[]).append(w)
        return {'seed':seed,'label':label,'declared_selectors':{'format14':fmt,'variant1c':variant,
            'quality18':quality,'rate10':rate},'native_core_at_stop_hex':result.hex(),
            'native_core_vpc_quality_frame':list(struct.unpack('<3I',result)),
            'local_conversion_reaches_audio_boundary':accepted,'core_stores':writes,'events':events,
            'complete_MovieRecParam_initialization_Check_Open_or_camera_profile_proven':False}
    finally:m.close()


def checker(seed,label,core,diagnostic):
    # This complete zero-background structure is a declared checker fixture.
    # In particular target VPC6 is NOT attributed to the original app producer.
    m=prev.Guest(seed,pp.MPR);m.allowed=[(0xcc4d4,0xcc824)]
    try:
        raw=bytearray(0x1c0);struct.pack_into('<3I',raw,0x170,*core)
        m.uc.mem_write(INPUT,bytes(raw))
        events=[m.phase('original MPR CheckMovieRecParam prologue '+label,0xcc4d4,
            stack_bytes=0x40,sp=SP,x30=pp.STOP,x0=INPUT)]
        assert events[-1]['reason']=='boundary: before_original_mpr_logger'
        events.append(m.phase('independent original MPR parameter-check body '+label,0xcc51c,
            stack_bytes=0x40))
        assert events[-1]['reason']=='boundary: before_original_mpr_logger'
        fp=SP-0x40;observed=struct.unpack('<H',bytes(m.uc.mem_read(fp+0x32,2)))[0]
        assert observed==diagnostic
        assert bytes(m.uc.mem_read(INPUT,len(raw)))==bytes(raw)
        return {'seed':seed,'label':label,'declared_core':list(core),
            'all_other_parameter_bytes_explicit_zero':True,'native_diagnostic_ID':observed,
            'final_diagnostic_branch_reached':observed==0x40f,'events':events,
            'complete_logger_checker_return_valid_configuration_or_recording_proven':False}
    finally:m.close()


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path,required=True);a=parser.parse_args()
    im.volume();assert sha(PRIOR.read_bytes())==PRIOR_SHA
    for f in json.loads(PRIOR.read_text())['files']:
        d=(ROOT/f['path']).read_bytes();assert len(d)==f['bytes'] and sha(d)==f['sha256']
    assert (BASE/'GOAL_STATUS.json').read_bytes()==(STAGE/'goal-status-before.json').read_bytes()
    a.out.mkdir(exist_ok=False);(a.out/'executed-source.py').write_bytes(Path(__file__).read_bytes())
    try:
        cases=[one(seed,'matrix',fmt,variant) for seed in (0xa5,0xc3) for fmt in range(5,13) for variant in (0,1)]
        for seed in (0xa5,0xc3):
            cases.extend([one(seed,'format_below_range',4),one(seed,'format_above_range',13),
                one(seed,'invalid_variant',6,2),one(seed,'invalid_quality',6,0,0),
                one(seed,'invalid_rate',6,0,2,12)])
        good=[c for c in cases if c['local_conversion_reaches_audio_boundary']]
        assert len(good)==32 and not any(c['native_core_vpc_quality_frame'][0]==6 for c in good)
        checks=[checker(seed,label,core,diagnostic) for seed in (0xa5,0xc3)
            for label,core,diagnostic in (
                ('declared_target_not_app_produced',(6,6,3),0x40f),
                ('original_app_core_zero_other_fields',(5,6,3),0x40f),
                ('VPC_sentinel',(13,6,3),0x402),
                ('quality_sentinel',(6,255,3),0x403),
                ('frame_sentinel',(6,6,12),0x404),
                ('synthetic_large_VPC_control',(0x7ffffffe,6,3),0x40f))]
        j={'status':'PASS_ORIGINAL_MAIN_CONVERTER_MATRIX_HAS_NO_VPC6_IN_THIS_BRANCH',
            'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'original_app_sha256':prev.prev.APP_SHA,'cases':cases,'matrix_cases':len(good),
            'negative_cases':len(cases)-len(good),'native_checker_fixtures':checks,
            'bounded_phases':sum(len(c['events']) for c in cases+checks),
            'original_diagnostic_names':['mainVideoParamComb','mainVQuality','mainFrameRate'],
            'native_MAIN_VPC_set':sorted({c['native_core_vpc_quality_frame'][0] for c in good}),
            'scope':'One original app MAIN conversion branch; explicit inputs, independent post-gap entry. Not all producers, menu reachability, valid combinations or complete normal initialization.',
            'target_candidate_vpc6_quality6_frame3_generated':False,
            'Windows_UU_camera_operations':False,'goal_complete':False,'persistent_write_release':False}
        (a.out/'main-parameter-results.json').write_text(json.dumps(j,ensure_ascii=False,indent=2)+'\n')
        print(json.dumps({k:j[k] for k in ('status','matrix_cases','negative_cases','bounded_phases','native_MAIN_VPC_set')}))
    except BaseException:
        (a.out/'attempt-failure.json').write_text(json.dumps({'passing_result':False,'traceback':traceback.format_exc()},indent=2)+'\n');raise


if __name__=='__main__':main()
