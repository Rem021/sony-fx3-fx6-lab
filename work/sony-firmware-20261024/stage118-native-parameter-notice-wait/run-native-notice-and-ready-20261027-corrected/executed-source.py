#!/usr/bin/env python3
"""Native parameter-notice registry/future slices, no real async services."""
from pathlib import Path
import argparse,datetime,hashlib,json,struct,sys,traceback
STAGE=Path(__file__).resolve().parent;BASE=STAGE.parent;ROOT=BASE.parents[1]
sys.path.insert(0,str(BASE/'stage117-native-audio-proxy-admission'));import audio_proxy as prev
pp,r,im,APP,SP,reg=prev.pp,prev.r,prev.im,prev.APP,prev.SP,prev.reg
S=pp.SCRATCH;MAP=S+0x1000;BUCKET=S+0x2000;NODE=S+0x3000;NEW=S+0x3100;PAIR=S+0x3200
PAY=S+0x4000;PAY2=S+0x4200;PROMISE=S+0x5000;PROMISE2=S+0x5200;STATE=S+0x6000;STATE2=S+0x6200
VTABLE=S+0x7000;RESULT=S+0x8000;NOTICE=S+0x9000;OUT=S+0x9800;GLOBAL=0x968b120
PRIOR=BASE/'stage117-native-audio-proxy-admission/final-receipt.json'
PRIOR_SHA='ce06b8f2089d76a25e1b71f01ada41fde6b8e834a080fa299082f79b4f5f324b'
def sha(b):return hashlib.sha256(b).hexdigest()
def pq(m,a,v):m.uc.mem_write(a,struct.pack('<Q',v))
def q(m,a):return struct.unpack('<Q',bytes(m.uc.mem_read(a,8)))[0]
def w(m,a):return struct.unpack('<I',bytes(m.uc.mem_read(a,4)))[0]

class Guest(prev.AppGuest):
    def __init__(self,seed):
        super().__init__(seed)
        self.allowed.extend([(0x2e6e540,0x2e6e5d8),(0x2e56ce4,0x2e56d38),(0x2e57a90,0x2e57b04),
            (0x2e6c7a0,0x2e6c824),(0x2e6e478,0x2e6e540),(0x2e58088,0x2e580b0),
            (0x2bccc0c,0x2bccc98),(0x2bcce64,0x2bccee4),(0x2bccf34,0x2bccf74),
            (0x2e6f754,0x2e6f7e4),(0x2e6f9ac,0x2e6f9c4),(0x2e2a924,0x2e2a948),(0x2bcd208,0x2bcd224)])
        self.boundaries.update({0x1593ca0:'before_original_new',0x1591d30:'before_original_delete',
            0x2e6c634:'before_original_registry_insert',0x16ed554:'before_registry_mutex_lock',
            0x273879c:'before_registry_mutex_unlock_wrapper',0x2bcce64:'before_original_promise_fulfillment',
            0x2bccc28:'before_original_future_virtual_call',0x15940a0:'before_original_futex_wait',
            0x1594560:'before_original_futex_notify',0x1593840:'before_original_future_error',
            0x2bccf58:'after_original_ready_store_before_cleanup',0x2bccee0:'before_original_fulfillment_TLS_dispatch',
            0x2bccdc8:'before_original_promise_constructor',0x15944f0:'before_original_SetMovieRecParam',
            0x2bccfb4:'before_original_future_destruction'})
    def map_fixture(self,address,key,value):
        raw=bytearray(0x40);struct.pack_into('<QQQQ',raw,0,BUCKET,1,NODE if key is not None else 0,1 if key is not None else 0)
        self.uc.mem_write(address,bytes(raw));pq(self,BUCKET,address+0x10 if key is not None else 0)
        self.uc.mem_write(NODE,struct.pack('<QQQ',0,key or 0,value))
        if address==GLOBAL:
            assert any(s['p_vaddr']<=address<address+0x40<=s['p_vaddr']+s['p_memsz'] and s['p_flags']&2 for s in APP.segments)
            self.images=[(a,bytes(self.uc.mem_read(a,len(d))) if a<=address<address+0x40<=a+len(d) else d) for a,d in self.images]
    def promise_fixture(self):
        self.uc.mem_write(PROMISE,struct.pack('<QQQ',STATE,S+0x6400,RESULT))
        self.uc.mem_write(PROMISE2,struct.pack('<QQQ',STATE2,S+0x6500,RESULT+0x100))
        self.uc.mem_write(PAY,struct.pack('<QQ',PROMISE,0));self.uc.mem_write(PAY2,struct.pack('<QQ',PROMISE2,0))
        for a in (STATE,STATE2):
            self.uc.mem_write(a,bytes(0x30));pq(self,a,VTABLE);pq(self,a+8,RESULT)
        pq(self,VTABLE+0x10,S+0xa000)

def registration(seed,existing):
    m=Guest(seed)
    try:
        m.map_fixture(MAP,existing,PAY);m.uc.mem_write(PAIR,struct.pack('<QQ',0x1004,PAY2))
        before=bytes(m.uc.mem_read(MAP,0x40));oldnode=bytes(m.uc.mem_read(NODE,24))
        ev=[m.phase('original registration helper before allocating a node',0x2e6e540,
            sp=SP,x30=pp.STOP,x0=MAP,x1=PAIR)]
        assert ev[-1]['reason']=='boundary: before_original_new' and m.uc.reg_read(reg('x0'))==24
        ev.append(m.phase('independent allocated-node input; original key copy and bucket lookup',0x2e6e55c,
            outputs=[(NEW,NEW+24)],x0=NEW))
        assert bytes(m.uc.mem_read(NEW,24))==struct.pack('<QQQ',0,0x1004,PAY2)
        if existing==0x1004:
            assert ev[-1]['reason']=='boundary: before_original_delete'
            assert m.uc.reg_read(reg('x0'))==NEW
            ev.append(m.phase('independent post-delete frame; original duplicate-key return',0x2e6e5a0))
            assert ev[-1]['reason']=='returned' and m.uc.reg_read(reg('x0'))==NODE and m.uc.reg_read(reg('x1'))==0
            outcome='existing_node_and_value_retained_before_unknown_lifecycle'
        else:
            assert ev[-1]['reason']=='boundary: before_original_registry_insert'
            assert [m.uc.reg_read(reg('x'+str(i))) for i in range(4)]==[MAP,0,0x1004,NEW]
            outcome='missing_key_requests_insertion_not_executed'
        assert bytes(m.uc.mem_read(MAP,0x40))==before and bytes(m.uc.mem_read(NODE,24))==oldnode
        return {'seed':seed,'existing_key':existing,'incoming_key':0x1004,'incoming_value':hex(PAY2),'existing_value':hex(PAY),
            'outcome':outcome,'events':ev,'actual_new_delete_registry_publish_serialization_or_epoch_proven':False}
    finally:m.close()

def notice(seed,present,status,opaque,alternate=False):
    m=Guest(seed)
    try:
        m.promise_fixture();value=PAY2 if alternate else PAY;promise=PROMISE2 if alternate else PROMISE
        m.map_fixture(GLOBAL,0x1004 if present else 0x1005,value)
        record=struct.pack('<III',0x1004,opaque,status);m.uc.mem_write(NOTICE,record)
        oldp=bytes(m.uc.mem_read(promise,24));oldnode=bytes(m.uc.mem_read(NODE,24))
        ev=[m.phase('original LoadMovieFinishedParam callback prologue before log',0x2e6e478,
            sp=SP,x30=pp.STOP,x0=NOTICE)]
        assert ev[-1]['reason']=='boundary: before_original_app_logger'
        ev.append(m.phase('independent post-log callback reaches registry mutex',0x2e6e4b0))
        assert ev[-1]['reason']=='boundary: before_registry_mutex_lock'
        ev.append(m.phase('independent post-lock callback looks up event key and moves registered promise',0x2e6e4c0,
            outputs=[(value+8,value+12),(promise,promise+24)]))
        if present:
            assert ev[-1]['reason']=='boundary: before_original_promise_fulfillment'
            assert w(m,value+8)==status and bytes(m.uc.mem_read(promise,24))==bytes(24)
            temp=m.uc.reg_read(reg('x0'));assert bytes(m.uc.mem_read(temp,24))==oldp
            result='registered_promise_moved_before_unexecuted_fulfillment'
        else:
            assert ev[-1]['reason']=='boundary: before_registry_mutex_unlock_wrapper'
            assert bytes(m.uc.mem_read(promise,24))==oldp and w(m,value+8)==0
            result='no_matching_key_no_promise_move'
        assert bytes(m.uc.mem_read(NOTICE,12))==record and bytes(m.uc.mem_read(NODE,24))==oldnode
        return {'seed':seed,'matching_registry_key':present,'notice_key':0x1004,'notice_result_word8':status,
            'opaque_word4_not_claimed_epoch':opaque,'alternate_registered_model_pointer':alternate,
            'registered_value':hex(value),'registered_promise':hex(promise),'result':result,'events':ev,
            'complete_registry_erase_or_actual_fulfillment_encoder_configuration_identity_proven':False}
    finally:m.close()

def wait_state(seed,ready):
    m=Guest(seed)
    try:
        m.promise_fixture();m.uc.mem_write(STATE+0x10,struct.pack('<I',ready))
        ev=[m.phase('original future wait entry before unknown virtual call',0x2bccc0c,
            sp=SP,x30=pp.STOP,x0=STATE,x19=0x33001900,x20=0x33002000)]
        assert ev[-1]['reason']=='boundary: before_original_future_virtual_call'
        ev.append(m.phase('independent post-vcall frame; original ready test or futex-wait preparation',0x2bccc2c,
            outputs=[(STATE+0x10,STATE+0x14)]))
        if ready&0x7fffffff==1:
            assert ev[-1]['reason']=='returned' and m.uc.reg_read(reg('x0'))==RESULT
            assert m.uc.reg_read(reg('sp'))==SP and m.uc.reg_read(reg('x19'))==0x33001900 and m.uc.reg_read(reg('x20'))==0x33002000
            assert w(m,STATE+0x10)==ready;outcome='ready_returns_result_pointer'
        else:
            assert ev[-1]['reason']=='boundary: before_original_futex_wait' and w(m,STATE+0x10)==ready|0x80000000
            assert m.uc.reg_read(reg('x0'))==STATE+0x10;outcome='unready_marks_waiter_before_futex'
        return {'seed':seed,'declared_ready_word':ready,'outcome':outcome,'events':ev,
            'actual_thread_wait_wake_vcall_or_codec_Open_Start_proven':False}
    finally:m.close()

def fulfill_slice(seed,waiting,flag):
    m=Guest(seed)
    try:
        m.promise_fixture();m.uc.mem_write(STATE+0x10,struct.pack('<I',waiting));m.boundaries.pop(0x2bcce64)
        ev=[m.phase('original promise fulfillment prefix before unbound TLS dispatch',0x2bcce64,
            sp=SP,x30=pp.STOP,x0=PROMISE)]
        assert ev[-1]['reason']=='boundary: before_original_fulfillment_TLS_dispatch'
        fp=m.uc.reg_read(reg('x29'));m.uc.mem_write(fp+0x27,bytes([flag]))
        ev.append(m.phase('independent post-once status flag; original ready store or error branch',0x2bccf34,
            outputs=[(STATE+0x10,STATE+0x14)]))
        if flag:
            assert w(m,STATE+0x10)==1
            assert ev[-1]['reason']=='boundary: '+('before_original_futex_notify' if waiting&0x80000000 else 'after_original_ready_store_before_cleanup')
        else:assert ev[-1]['reason']=='boundary: before_original_future_error' and w(m,STATE+0x10)==waiting
        return {'seed':seed,'declared_waiting_word':waiting,'independent_post_once_success_byte':flag,'events':ev,
            'actual_TLS_call_once_provider_callback_notify_or_cleanup_proven':False}
    finally:m.close()

def branch(seed,flag):
    m=Guest(seed)
    try:
        m.uc.mem_write(NOTICE+0x5f,bytes([flag]))
        e=m.phase('independent original app parameter-save branch selection',0x2e6f754,
            sp=SP,x30=pp.STOP,x24=NOTICE,x19=MAP,x22=PROMISE)
        assert e['reason']=='boundary: '+('before_original_SetMovieRecParam' if flag==0 else 'before_original_promise_constructor')
        return {'seed':seed,'declared_input5f':flag,'events':[e],'flag_not_proven_idle_or_recording_state':True}
    finally:m.close()

def post_set(seed,raw_status):
    m=Guest(seed)
    try:
        m.promise_fixture();fp=SP-0x9f0;pq(m,fp+0x70,OUT)
        e=m.phase('independent original post-Set/error-conversion frame: result write before optional wait',0x2e6f7c8,
            outputs=[(OUT,OUT+4)],sp=SP-0xa00,x29=fp,x30=pp.STOP,x0=0 if raw_status==0 else 44,
            x19=raw_status,x25=PROMISE)
        assert w(m,OUT)==(0 if raw_status==0 else 44)
        assert e['reason']=='boundary: '+('before_original_future_virtual_call' if raw_status==0 else 'before_original_future_destruction')
        return {'seed':seed,'declared_raw_Set_status':raw_status,'independent_model_status':0 if raw_status==0 else 44,
            'events':[e],'actual_Set_conversion_return_or_original_app_completion_proven':False}
    finally:m.close()

def run(out):
    im.volume();assert sha(PRIOR.read_bytes())==PRIOR_SHA
    for x in json.loads(PRIOR.read_text())['files']:
        p=ROOT/x['path'];assert p.stat().st_size==x['bytes'] and sha(p.read_bytes())==x['sha256']
    assert (BASE/'GOAL_STATUS.json').read_bytes()==(STAGE/'goal-status-before.json').read_bytes()
    out.mkdir();(out/'executed-source.py').write_bytes(Path(__file__).read_bytes())
    j={'status':'RUNNING','created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'source':str(Path(__file__).relative_to(ROOT)),'source_sha256':sha(Path(__file__).read_bytes()),
        'registration_cases':[],'notice_cases':[],'wait_cases':[],'fulfill_cases':[],'branch_cases':[],'post_Set_cases':[],
        'goal_complete':False,'persistent_write_release':False,'Windows_UU_camera_operations':False,
        'actual_async_transaction_config_epoch_or_MAIN_recording_recovery_proven':False}
    try:
        for seed in (0xa5,0xc3):
            for existing in (0x1004,None,0x1005):j['registration_cases'].append(registration(seed,existing))
            for status in (0,7):
                for opaque in (0x1111,0x2222):j['notice_cases'].append(notice(seed,True,status,opaque))
            j['notice_cases'].append(notice(seed,True,0,0x1111,True));j['notice_cases'].append(notice(seed,False,0,0x1111))
            for ready in (0,1,0x80000001):j['wait_cases'].append(wait_state(seed,ready))
            for waiting,flag in ((0,1),(0x80000000,1),(0,0)):j['fulfill_cases'].append(fulfill_slice(seed,waiting,flag))
            for flag in (0,1,2):j['branch_cases'].append(branch(seed,flag))
            for raw in (0,7):j['post_Set_cases'].append(post_set(seed,raw))
        groups=('registration_cases','notice_cases','wait_cases','fulfill_cases','branch_cases','post_Set_cases')
        j['bounded_phases']=sum(len(c['events']) for k in groups for c in j[k])
        j['status']='PASS_NATIVE_LOAD_PARAMETER_NOTICE_WAIT_SCOPE_NOT_CODEC_OR_EPOCH_PROOF'
        (out/'notice-wait-results.json').write_text(json.dumps(j,ensure_ascii=False,indent=2)+'\n')
        print(json.dumps({k:len(j[k]) for k in groups}|{'bounded_phases':j['bounded_phases'],'status':j['status']}))
    except Exception:
        j['status']='FAILED_NO_PASSING_RESULT';j['error']=traceback.format_exc()
        (out/'attempt-failure.json').write_text(json.dumps(j,ensure_ascii=False,indent=2)+'\n');raise
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);run(p.parse_args().out)
