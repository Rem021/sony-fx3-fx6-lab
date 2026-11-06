#!/usr/bin/env python3
"""Original movie-event and media recording request construction; Mac offline.

All entries after logging/runtime gaps are independent bounded experiments.
No API result, heap/OSAL identity, log return or camera state is synthesized.
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
sys.path.insert(0,str(BASE/'stage102-native-app-qos-producer'))
import app_qos as prev
pp,r,im,APP=prev.pp,prev.r,prev.im,prev.APP
SP=prev.APP_SP
INPUT=pp.SCRATCH+0x100
OUTPUT=pp.SCRATCH+0x400
OBJECT=pp.SCRATCH+0x2000
PRIOR=BASE/'stage103-native-streaming-open-profile/final-receipt.json'
PRIOR_SHA='9e056f460eb6b843f588cbbfb156dc128efc2a51f3187bfb0f5e1046304e5a98'


def sha(raw):return hashlib.sha256(raw).hexdigest()


class Guest(prev.AppGuest):
    def __init__(self,seed,native=APP):
        if native is APP:
            super().__init__(seed)
        else:
            pp.StrictMicro.__init__(self,native,[])
            self.uc.mem_write(pp.STACK_BASE,bytes([seed])*pp.STACK_SIZE)
            self.uc.mem_write(pp.SCRATCH,bytes([seed^0x3c])*0x10000)
            self.boundaries={}
        self.allowed=[(0x2da8c48,0x2da8d60),(0x2db0ea4,0x2db0fa0),
            (0x2e5c5e8,0x2e5c750),(0x2e76854,0x2e76af8),
            (0x2e3f628,0x2e3f684),(0x2e3f580,0x2e3f5cc),
            (0x2e25338,0x2e25344),(0x2f6de20,0x2f6de34),
            (0x2f6dd88,0x2f6ddb0)] if native is APP else [(0xcc1c4,0xcc4d4)]
        self.boundaries.update({0x2f6ff0c:'before_original_app_logger',
            0x2f6be48:'before_original_app_diagnostic',
            0x2dd89d4:'before_key_clear_wrapper',0x2dd4ad4:'before_movie_event_wrapper',
            0x1593910:'before_original_mpr_PrepareRecStart',
            0x2f6cfc4:'before_unexecuted_trace_identity',
            0xc8c70:'before_original_mpr_logger',
            0x82e90:'before_original_media_ID_lookup'})


def caller(seed,label):
    card=label=='card';m=Guest(seed)
    try:
        pro,clear,event=(0x2da8c48,0x2da8c94,0x2da8ce8) if card else (0x2db0ea4,0x2db0ee8,0x2db0f3c)
        frame=0x60 if card else 0x50
        events=[m.phase(label+' original caller prologue',pro,stack_bytes=frame,
                        sp=SP,x0=OBJECT,x30=pp.STOP)]
        assert events[-1]['reason']=='boundary: before_original_app_logger'
        events.append(m.phase(label+' independent key-clear argument body',clear,stack_bytes=frame))
        assert events[-1]['reason']=='boundary: before_key_clear_wrapper'
        ip=m.uc.reg_read(r.reg.UC_ARM64_REG_X0);op=m.uc.reg_read(r.reg.UC_ARM64_REG_X1)
        key=bytes(m.uc.mem_read(ip,4));assert key==bytes(4)
        events.append(m.phase(label+' independent movie-event argument body',event,stack_bytes=frame))
        assert events[-1]['reason']=='boundary: before_movie_event_wrapper'
        assert m.uc.reg_read(r.reg.UC_ARM64_REG_X0)==ip and m.uc.reg_read(r.reg.UC_ARM64_REG_X1)==op
        raw=bytes(m.uc.mem_read(ip,4));assert raw==bytes(4)
        return {'label':label,'seed':seed,'key_clear_input_hex':key.hex(),
            'movie_event_input_hex':raw.hex(),'same_original_wrappers_as_other_path':True,
            'output_initialization_not_a_success_reply':True,'events':events,
            'whole_sequence_recording_or_shared_encoder_proven':False}
    finally:m.close()


def movie_event(seed):
    m=Guest(seed)
    try:
        m.uc.mem_write(INPUT,bytes(4))
        e=m.phase('original EID_MOVIE_REC request and trace prefix',0x2e3f628,
                  stack_bytes=0xb00,sp=SP,x0=INPUT,x1=OUTPUT,x30=pp.STOP)
        assert e['reason']=='boundary: before_unexecuted_trace_identity'
        raw=bytes(m.uc.mem_read(SP-0x50+0x38,0x18))
        expected=bytearray(0x18);struct.pack_into('<H',expected,2,0x3001)
        assert raw==expected
        assert bytes(m.uc.mem_read(OUTPUT,4))==bytes([seed^0x3c])*4
        return {'seed':seed,'request18_hex':raw.hex(),'original_event_ID':0x3001,
            'events':[e],'transport_reply_or_event_completion_proven':False}
    finally:m.close()


def prepare(seed,f0,f1):
    m=Guest(seed)
    try:
        inp=struct.pack('<IIII',0x11223344,0x55667788,f0,f1)
        m.uc.mem_write(INPUT,inp)
        events=[m.phase('original mpr_PrepareRecStart wrapper detail prologue',0x2e5c5e8,
            stack_bytes=0xb0,sp=SP,x0=INPUT,x1=OUTPUT,x30=pp.STOP)]
        assert events[-1]['reason']=='boundary: before_original_app_logger'
        events.append(m.phase('independent post-log prepare-media request body',0x2e5c624,stack_bytes=0xb0))
        assert events[-1]['reason']=='boundary: before_original_mpr_PrepareRecStart'
        fp=SP-0xb0;raw=bytes(m.uc.mem_read(fp+0x48,0x1c))
        ids=[x for x,f in zip((0x11223344,0x55667788),(f0,f1)) if not f]
        words=[0x6c,4,len(ids),ids[0] if ids else 0,ids[1] if len(ids)>1 else (-1 if len(ids)==1 else 0),0,0]
        expected=struct.pack('<7I',*[x&0xffffffff for x in words]);assert raw==expected
        assert bytes(m.uc.mem_read(INPUT,len(inp)))==inp
        assert bytes(m.uc.mem_read(OUTPUT,0x20))==bytes([seed^0x3c])*0x20
        return {'seed':seed,'selection_words':[f0,f1],'input10_hex':inp.hex(),
            'request1c_hex':raw.hex(),'native_media_count':len(ids),'events':events,
            'actual_media_IDs_or_PrepareRecStart_success_proven':False}
    finally:m.close()


def recstart(seed,f0,f1,index):
    m=Guest(seed)
    try:
        # IDs and opaque selector words are declared fixtures, not camera values.
        inp=struct.pack('<6IQ',0x11223344,0x55667788,f0,f1,index,0,0x1122334455667788)
        m.uc.mem_write(INPUT,inp)
        events=[m.phase('original mpr_RecStart detail prologue',0x2e76854,
            stack_bytes=0x610,sp=SP,x0=INPUT,x1=OUTPUT,x30=pp.STOP)]
        assert events[-1]['reason']=='boundary: before_original_app_logger'
        # Earlier event/lock/object/520-byte initialization stays unexecuted.
        # This entry consumes the original prologue's X19 and original frame.
        events.append(m.phase('independent media request production after runtime gap',0x2e76910,
            stack_bytes=0x610,x27=0x968b000))
        assert events[-1]['reason']=='boundary: before_original_app_diagnostic'
        raw=bytes(m.uc.mem_read(SP-0x610+0xb8,0x38))
        ids=[x for x,f in zip((0x11223344,0x55667788),(f0,f1)) if not f]
        expected=bytearray(0x38)
        struct.pack_into('<I',expected,0,6)
        struct.pack_into('<I',expected,8,len(ids))
        for n,v in enumerate(ids):struct.pack_into('<I',expected,12+n*4,v)
        if len(ids)==1:struct.pack_into('<I',expected,16,0xffffffff)
        struct.pack_into('<I',expected,0x1c,(0,90,180,270)[index])
        struct.pack_into('<Q',expected,0x28,0x1122334455667788)
        assert raw==expected
        assert bytes(m.uc.mem_read(INPUT,len(inp)))==inp
        assert bytes(m.uc.mem_read(OUTPUT,0x20))==bytes([seed^0x3c])*0x20
        return {'seed':seed,'selection_words':[f0,f1],'opaque_index':index,
            'input20_hex':inp.hex(),'request38_hex':raw.hex(),'native_media_count':len(ids),
            'opaque_parameter_word1c':(0,90,180,270)[index],'events':events,
            'actual_media_IDs_or_mpr_call_Open_codec_MUX_or_recording_proven':False}
    finally:m.close()


def check_consumer(producer):
    m=Guest(producer['seed'],pp.MPR)
    raw=bytes.fromhex(producer['request38_hex'])
    try:
        m.uc.mem_write(INPUT,raw)
        events=[m.phase('original MPR CheckRecStartInParam prologue',0xcc1c4,
            stack_bytes=0x50,sp=SP,x0=INPUT,x30=pp.STOP)]
        assert events[-1]['reason']=='boundary: before_original_mpr_logger'
        events.append(m.phase('independent post-log original media count/ID consumer',0xcc210,stack_bytes=0x50))
        count=producer['native_media_count']
        want='boundary: before_original_media_ID_lookup' if count else 'boundary: before_original_mpr_logger'
        assert events[-1]['reason']==want
        if count:assert m.uc.reg_read(r.reg.UC_ARM64_REG_W1)==struct.unpack_from('<I',raw,12)[0]
        assert bytes(m.uc.mem_read(INPUT,len(raw)))==raw
        return {'seed':producer['seed'],'selection_words':producer['selection_words'],
            'native_media_count':count,'original_app_request38_hex':raw.hex(),'events':events,
            'first_media_ID_lookup_or_zero_count_diagnostic_reached':True,
            'complete_validation_actual_ID_registry_or_recording_proven':False}
    finally:m.close()


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path,required=True);a=parser.parse_args()
    im.volume();assert sha(PRIOR.read_bytes())==PRIOR_SHA
    pm=json.loads(PRIOR.read_text())
    for f in pm['files']:
        d=(ROOT/f['path']).read_bytes();assert len(d)==f['bytes'] and sha(d)==f['sha256']
    assert (BASE/'GOAL_STATUS.json').read_bytes()==(STAGE/'goal-status-before.json').read_bytes()
    a.out.mkdir(exist_ok=False)
    (a.out/'executed-source.py').write_bytes(Path(__file__).read_bytes())
    try:
        c=[caller(seed,label) for seed in (0xa5,0xc3) for label in ('card','streaming')]
        e=[movie_event(seed) for seed in (0xa5,0xc3)]
        prep=[prepare(seed,f0,f1) for seed in (0xa5,0xc3) for f0,f1 in ((0,0),(0,1),(1,0),(1,1))]
        rec=[recstart(seed,f0,f1,1) for seed in (0xa5,0xc3) for f0,f1 in ((0,0),(0,1),(1,0),(1,1))]
        rec.extend(recstart(seed,0,0,index) for seed in (0xa5,0xc3) for index in (0,2,3))
        checks=[check_consumer(p) for p in rec[:8] if p['selection_words'] in ([0,0],[0,1],[1,1])]
        rows=c+e+prep+rec+checks
        j={'status':'PASS_SHARED_MOVIE_EVENT_SEPARATED_FROM_ORIGINAL_MPR_MEDIA_RECORDING_START',
           'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
           'original_app_sha256':prev.APP_SHA,'original_mpr_sha256':sha(pp.MPR.blob),
           'caller_arguments':c,'movie_event_packets':e,'prepare_media_packets':prep,
           'recstart_media_packets':rec,'original_MPR_consumers':checks,
           'bounded_phases':sum(len(x['events']) for x in rows),
           'all_post_gap_entries_independent_not_native_continuations':True,
           'requests_have_no_claim_of_current_camera_state_or_valid_media_IDs':True,
           'Windows_UU_camera_operations':False,'goal_complete':False,'persistent_write_release':False}
        (a.out/'movie-start-results.json').write_text(json.dumps(j,ensure_ascii=False,indent=2)+'\n')
        print(json.dumps({'status':j['status'],'bounded_phases':j['bounded_phases'],
            'caller_cases':len(c),'event_cases':len(e),'prepare_cases':len(prep),
            'start_cases':len(rec),'consumer_cases':len(checks)}))
    except BaseException:
        (a.out/'attempt-failure.json').write_text(json.dumps({'passing_result':False,'traceback':traceback.format_exc()},indent=2)+'\n')
        raise


if __name__=='__main__':main()
