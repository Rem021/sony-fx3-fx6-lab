#!/usr/bin/env python3
"""Native error-record handling and write-finished release/event ordering."""
from pathlib import Path
import argparse,datetime,hashlib,json,struct,sys,traceback
STAGE=Path(__file__).resolve().parent;BASE=STAGE.parent;ROOT=BASE.parents[1]
sys.path.insert(0,str(BASE/'stage122-native-callback-record-and-execqueue'));import callback_queue as prev
pp,r,im,MPR,SP,reg=prev.pp,prev.r,prev.im,prev.MPR,prev.SP,prev.reg
S=pp.SCRATCH;OWNER=prev.OWNER;REQUEST=S+0xd000
PRIOR=BASE/'stage122-native-callback-record-and-execqueue/final-receipt.json'
PRIOR_SHA='515e8ece24bf3dc242732cc908c0358b9005e31745c9acefd8e66d83c24df35b'
def sha(b):return hashlib.sha256(b).hexdigest()
class Guest(prev.Guest):
    def __init__(self,seed):
        super().__init__(seed)
        self.allowed.extend([(0xfc168,0xfc29c),(0xfc3a0,0xfc43c),(0xcb508,0xcb5c0)])
        self.boundaries.update({0xfbe5c:'before_original_record_diagnostic',0xfc244:'before_original_record_callback'})
def fixture(m,seed,results,active=True,callback=True):
    src=BASE/'stage122-native-callback-record-and-execqueue/run-native-owner-queue-20261027/callback-queue-results.json'
    init=next(x for x in json.loads(src.read_text())['initializers'] if x['seed']==seed)
    raw=bytearray.fromhex(init['native384'])
    for i,result in enumerate(results):
        raw[i*96]=int(active);struct.pack_into('<II',raw,i*96+4,17+i,result)
        struct.pack_into('<Q',raw,i*96+0x10,0xd714c if callback else 0)
    m.uc.mem_write(OWNER,bytes(raw));return bytes(raw)

def aggregate(seed,values,active=True):
    m=Guest(seed)
    try:
        old=fixture(m,seed,values,active);ss=prev.prev.saved(m)
        ev=[m.phase('original aggregate result reader before lock',0xfc3a0,sp=SP,x30=pp.STOP,x0=OWNER)]
        assert ev[-1]['reason']=='boundary: before_original_record_lock'
        ev.append(m.phase('independent post-lock original first-nonzero scan before unlock',0xfc414))
        assert ev[-1]['reason']=='boundary: before_original_Codec_normalLock_unlock'
        ev.append(m.phase('independent post-unlock original aggregate reader epilogue',0xfc438))
        expected=next((x for x in values if x),0)
        assert ev[-1]['reason']=='returned' and m.uc.reg_read(reg('w0'))==expected and prev.prev.restored(m,ss)
        assert bytes(m.uc.mem_read(OWNER,384))==old
        return {'seed':seed,'declared_results':values,'declared_all_active':active,'declared_nonnull_callbacks':True,
            'native_first_nonzero':expected,'events':ev,'zero_result_not_all_callbacks_finished_proof':True,
            'actual_locks_current_records_and_lifecycle_proven':False}
    finally:m.close()

def single_error(seed,active,callback,status):
    m=Guest(seed)
    try:
        old=fixture(m,seed,[0,0,0,0],active,callback);ss=prev.prev.saved(m)
        ev=[m.phase('original single-record error handler',0xfc168,sp=SP,x30=pp.STOP,x0=OWNER,x1=status)]
        if status==0:
            assert ev[-1]['reason']=='boundary: before_original_record_diagnostic'
            ev.append(m.phase('independent post-zero-error diagnostic original return',0xfc1c8))
            assert ev[-1]['reason']=='returned' and prev.prev.restored(m,ss)
            expected=old;outcome='zero_input_no_result_or_callback_change'
        else:
            assert ev[-1]['reason']=='boundary: before_original_record_lock'
            ev.append(m.phase('independent post-lock original active/error branch before diagnostic',0xfc1e8,
                outputs=[(OWNER+8,OWNER+12)] if active else []))
            assert ev[-1]['reason']=='boundary: before_original_record_diagnostic'
            ev.append(m.phase('independent post-log original callback capture/clear before unlock',0xfc284 if active else 0xfc230,
                outputs=[(OWNER+0x10,OWNER+0x18)] if active else []))
            assert ev[-1]['reason']=='boundary: before_original_Codec_normalLock_unlock'
            ev.append(m.phase('independent post-unlock original callback decision',0xfc238))
            expected=bytearray(old)
            if active:
                struct.pack_into('<I',expected,8,status);struct.pack_into('<Q',expected,0x10,0)
            expected=bytes(expected)
            if active and callback:
                assert ev[-1]['reason']=='boundary: before_original_record_callback'
                assert (m.uc.reg_read(reg('w0')),m.uc.reg_read(reg('w1')),m.uc.reg_read(reg('x21')))==(17,status,0xd714c)
                outcome='result_stored_callback_pointer_cleared_before_unexecuted_call'
            else:
                assert ev[-1]['reason']=='returned' and prev.prev.restored(m,ss)
                outcome='no_callback_call'
        assert bytes(m.uc.mem_read(OWNER,384))==expected
        return {'seed':seed,'declared_active':active,'declared_callback':callback,'declared_error':status,
            'outcome':outcome,'events':ev,'active_flag_not_cleared_by_this_slice':True,
            'actual_callback_execution_locks_completion_or_current_instance_proven':False}
    finally:m.close()

def notifier(seed,values):
    m=Guest(seed)
    try:
        old=fixture(m,seed,values);m.uc.mem_write(REQUEST,bytes(0x58));prev.pq(m,REQUEST+0x50,OWNER)
        request=bytes(m.uc.mem_read(REQUEST,0x58));expected=next((x for x in values if x),0)
        ev=[m.phase('original NotifyAllMovieWriteFinishedParam prologue before diagnostic',0xcb508,
            sp=SP,x30=pp.STOP,x0=REQUEST)]
        assert ev[-1]['reason']=='boundary: before_original_MPR_diagnostic'
        fp=m.uc.reg_read(reg('x29'))
        ev.append(m.phase('independent post-log native notifier enters aggregate reader before lock',0xcb558))
        assert ev[-1]['reason']=='boundary: before_original_record_lock'
        ev.append(m.phase('independent post-aggregate-lock original result scan before unlock',0xfc414))
        assert ev[-1]['reason']=='boundary: before_original_Codec_normalLock_unlock'
        ev.append(m.phase('independent post-aggregate-unlock native return/result save and release wrapper before lock',0xfc438))
        assert ev[-1]['reason']=='boundary: before_original_record_lock'
        assert bytes(m.uc.mem_read(fp+0x40,8))==struct.pack('<II',0x100a,expected)
        ev.append(m.phase('independent post-release-lock original free argument',0xfc060))
        assert ev[-1]['reason']=='boundary: before_original_record_free' and m.uc.reg_read(reg('x0'))==OWNER
        ev.append(m.phase('independent post-free frame without actual allocator execution; original unlock argument',0xfc068))
        assert ev[-1]['reason']=='boundary: before_original_Codec_normalLock_unlock'
        ev.append(m.phase('independent post-release-unlock original notifier event preparation before SetIssueEvent',0xfc070))
        assert ev[-1]['reason']=='boundary: before_original_SetIssueEvent'
        assert [m.uc.reg_read(reg('x'+str(i))) for i in range(3)]==[0x100a,fp+0x40,8]
        assert bytes(m.uc.mem_read(fp+0x40,8))==struct.pack('<II',0x100a,expected)
        assert bytes(m.uc.mem_read(OWNER,384))==old and bytes(m.uc.mem_read(REQUEST,0x58))==request
        return {'seed':seed,'declared_results':values,'native_prepared_event8':struct.pack('<II',0x100a,expected).hex(),
            'native_aggregate':expected,'native_record_free_argument':hex(OWNER),'events':ev,
            'all_free_thread_log_signal_event_and_upstream_finish_gate_unexecuted':True,
            'event_has_type_and_result_not_record_snapshot_or_config_epoch':True,
            'no_claim_real_records_released_or_all_async_users_finished':True}
    finally:m.close()

def run(out):
    im.volume();assert sha(PRIOR.read_bytes())==PRIOR_SHA
    for x in json.loads(PRIOR.read_text())['files']:
        p=ROOT/x['path'];assert p.stat().st_size==x['bytes'] and sha(p.read_bytes())==x['sha256']
    assert (BASE/'GOAL_STATUS.json').read_bytes()==(STAGE/'goal-status-before.json').read_bytes()
    out.mkdir();(out/'executed-source.py').write_bytes(Path(__file__).read_bytes())
    j={'status':'RUNNING','created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source_sha256':sha(Path(__file__).read_bytes()),
        'aggregate_cases':[],'error_cases':[],'notifier_cases':[],'goal_complete':False,'persistent_write_release':False,
        'camera_Windows_UU_operations':False,'actual_MAIN_hardware_quiescence_free_restore_or_rescue_proven':False}
    try:
        for seed in (0xa5,0xc3):
            for vals,active in (([0,0,0,0],True),([0,2,7,0],True),([9,0,0,2],True),([0,0,0,5],True),([0,7,0,0],False)):
                j['aggregate_cases'].append(aggregate(seed,vals,active))
            for active,callback,status in ((True,True,2),(True,False,7),(False,True,2),(True,True,0)):
                j['error_cases'].append(single_error(seed,active,callback,status))
            for vals in ([0,0,0,0],[0,2,0,0]):j['notifier_cases'].append(notifier(seed,vals))
        j['bounded_phases']=sum(len(c['events']) for k in ('aggregate_cases','error_cases','notifier_cases') for c in j[k])
        j['status']='PASS_NATIVE_RECORD_RESULT_AND_WRITE_FINISH_SCOPE_NOT_GLOBAL_QUIESCENCE'
        (out/'record-finish-results.json').write_text(json.dumps(j,ensure_ascii=False,indent=2)+'\n')
        print(json.dumps({'bounded_phases':j['bounded_phases'],'status':j['status']}))
    except Exception:
        j['status']='FAILED_NO_PASSING_RESULT';j['error']=traceback.format_exc()
        (out/'attempt-failure.json').write_text(json.dumps(j,ensure_ascii=False,indent=2)+'\n');raise
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);run(p.parse_args().out)
