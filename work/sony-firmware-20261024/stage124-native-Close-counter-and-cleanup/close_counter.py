#!/usr/bin/env python3
"""Native Close counter decision and cleanup tail; no real shutdown proof."""
from pathlib import Path
import argparse,datetime,hashlib,json,struct,sys,traceback
STAGE=Path(__file__).resolve().parent;BASE=STAGE.parent;ROOT=BASE.parents[1]
sys.path.insert(0,str(BASE/'stage123-native-record-result-and-write-finish'));import record_finish as prev
pp,r,im,MPR,SP,reg=prev.pp,prev.r,prev.im,prev.MPR,prev.SP,prev.reg
S=pp.SCRATCH;REQUEST=S+0xc000
COUNTERS=0x376158;INFO=0x375508;FLAG=INFO+0xa6c
PRIOR=BASE/'stage123-native-record-result-and-write-finish/final-receipt.json'
PRIOR_SHA='02acc3571baa28fd1aa1204c9efe036251dbf36003af9febc7ca770f2ce724d2'
def sha(b):return hashlib.sha256(b).hexdigest()
class Guest(prev.Guest):
    def __init__(self,seed):
        super().__init__(seed)
        self.allowed.extend([(0xcf0d0,0xcf3ac),(0xce824,0xce8e4),(0xcebe0,0xcec9c)])
        self.boundaries[0x7f6f0]='before_original_Codec_EncClose'
        for a in (COUNTERS,FLAG):self.uc.mem_protect(a&~4095,4096,r.unicorn.UC_PROT_READ|r.unicorn.UC_PROT_WRITE)
        for got,value in ((0x2f9c40,COUNTERS),(0x2f9658,INFO)):
            assert prev.prev.rq(self,got)==value
    def code(self,u,pc,n,user):
        bindings={0x824c0:('_ZN3mpr16GetRecordCounterEjPh',0xce824),0x82150:('_ZN3mpr16SetRecordCounterEjh',0xcebe0)}
        if pc in bindings:
            name,target=bindings[pc];assert MPR.plt[pc]==name and MPR.symbols[name]['va']==target
            self.pcs.append(hex(pc));self.calls.append({'original_symbol_binding':name,'PLT':hex(pc),'target':hex(target),
                'scope':'Native counter body executes across explicit log/lock gaps, no output or return adapter.'})
            u.reg_write(reg('pc'),target);return
        return super().code(u,pc,n,user)
def fixture(m,index,count,mode):
    raw=bytearray(0x38);struct.pack_into('<I',raw,4,15);struct.pack_into('<I',raw,0xc,31)
    struct.pack_into('<II',raw,0x20,index,mode);m.uc.mem_write(REQUEST,bytes(raw))
    counts=bytearray(4);counts[index]=count;m.uc.mem_write(COUNTERS,bytes(counts))
    m.uc.mem_write(INFO,struct.pack('<II',1,index));m.uc.mem_write(FLAG,struct.pack('<I',0x66))
    return bytes(raw),bytes(counts)
def read_remainder(m,ev,label):
    ev.append(m.phase('independent counter getter post-log '+label,0xce87c))
    assert ev[-1]['reason']=='boundary: before_original_record_lock'
    ev.append(m.phase('independent counter post-lock native byte read '+label,0xce888))
    assert ev[-1]['reason']=='boundary: before_original_Codec_normalLock_unlock'
    ev.append(m.phase('independent counter post-unlock original diagnostic '+label,0xce8a0))
    assert ev[-1]['reason']=='boundary: before_original_MPR_diagnostic'
    ev.append(m.phase('independent counter post-log native return into original Close caller '+label,0xce8d0))

def decision(seed,index,count,mode):
    m=Guest(seed)
    try:
        raw,initial=fixture(m,index,count,mode)
        ev=[m.phase('original ExecEncClose prologue before diagnostic',0xcf0d0,sp=SP,x30=pp.STOP,x0=REQUEST)]
        assert ev[-1]['reason']=='boundary: before_original_MPR_diagnostic';fp=m.uc.reg_read(reg('x29'))
        ev.append(m.phase('independent post-log original reply48 clear before integration lock',0xcf130))
        assert ev[-1]['reason']=='boundary: before_original_record_lock' and bytes(m.uc.mem_read(fp+0x80,48))==bytes(48)
        ev.append(m.phase('independent post-integration-lock original sum loop enters native counter getter',0xcf148))
        assert ev[-1]['reason']=='boundary: before_original_MPR_diagnostic' and m.uc.reg_read(reg('x30'))==0xce87c
        read_remainder(m,ev,'sum loop')
        expected_count=count
        if mode==0 and count:
            assert ev[-1]['reason']=='boundary: before_original_MPR_diagnostic' and m.uc.reg_read(reg('x30'))==0xce87c
            read_remainder(m,ev,'selected decrement read')
            assert ev[-1]['reason']=='boundary: before_original_MPR_diagnostic' and m.uc.reg_read(reg('x30'))==0xcec3c
            ev.append(m.phase('independent setter post-log original counter lock',0xcec3c))
            assert ev[-1]['reason']=='boundary: before_original_record_lock'
            ev.append(m.phase('independent setter post-lock native byte decrement store',0xcec48,image_outputs=[(COUNTERS+index,COUNTERS+index+1)]))
            assert ev[-1]['reason']=='boundary: before_original_Codec_normalLock_unlock'
            ev.append(m.phase('independent setter post-unlock original diagnostic',0xcec5c))
            assert ev[-1]['reason']=='boundary: before_original_MPR_diagnostic'
            ev.append(m.phase('independent setter post-log native return to original Close decision',0xcec88))
            expected_count-=1
        expected=bytearray(initial);expected[index]=expected_count
        assert bytes(m.uc.mem_read(COUNTERS,4))==bytes(expected)
        remaining=count-(1 if mode==0 and count else 0)
        if remaining:
            assert ev[-1]['reason']=='boundary: before_original_MPR_diagnostic' and m.uc.reg_read(reg('x30'))==0xcf1e4
            ev.append(m.phase('independent skip-close diagnostic gap: original mode-word clear before unlock',0xcf1e4,image_outputs=[(FLAG,FLAG+4)]))
            assert ev[-1]['reason']=='boundary: before_original_Codec_normalLock_unlock'
            assert bytes(m.uc.mem_read(FLAG,4))==bytes(4);outcome='Codec_Close_bypassed_by_remaining_counter'
        else:
            assert ev[-1]['reason']=='boundary: before_original_Codec_EncClose'
            assert [m.uc.reg_read(reg('x'+str(i))) for i in range(6)]==[fp+0x60,32,15,1,0,fp+0x80]
            assert bytes(m.uc.mem_read(fp+0x60,16))==bytes(16)
            assert bytes(m.uc.mem_read(FLAG,4))==struct.pack('<I',0x66);outcome='original_single_Close_call_prepared'
        assert bytes(m.uc.mem_read(REQUEST,0x38))==raw
        return {'seed':seed,'declared_index':index,'initial_count':count,'request_control24':mode,
            'native_remaining_count':expected_count,'outcome':outcome,'events':ev,
            'sum_uses_native_GetRecordCounter_from_declared_global_bytes':True,
            'all_log_lock_Codec_call_and_real_counter_runtime_values_unexecuted':True,
            'actual_complete_Close_hardware_or_shared_owner_quiescence_proven':False}
    finally:m.close()

def cleanup_tail(seed,free_result):
    m=Guest(seed)
    try:
        fixture(m,0,0,0)
        ev=[m.phase('original Close prologue for independent post-DMM-free tail frame',0xcf0d0,sp=SP,x30=pp.STOP,x0=REQUEST)]
        ev.append(m.phase('independent declared FreeDmmMemory boolean, not actual memory release',0xcf2d4,
            image_outputs=[(FLAG,FLAG+4)],x0=free_result))
        if not free_result:
            assert ev[-1]['reason']=='boundary: before_original_MPR_diagnostic'
            ev.append(m.phase('independent post-free-error diagnostic original common mode-word clear',0xcf1e4,image_outputs=[(FLAG,FLAG+4)]))
        assert ev[-1]['reason']=='boundary: before_original_Codec_normalLock_unlock'
        assert bytes(m.uc.mem_read(FLAG,4))==bytes(4)
        return {'seed':seed,'declared_FreeDmmMemory_low_byte':free_result,'native_mode_word_cleared':True,'events':ev,
            'mode_word_zero_not_DMM_release_or_full_Close_completion_proof':True,'actual_free_or_Codec_completion_proven':False}
    finally:m.close()

def classification(seed,kind):
    m=Guest(seed)
    try:
        start,a,b,expected={'Close_expect':(0x27df44,0x210,4,0x1006),
            'synthetic_sub9':(0x27f494,0x4e0,9,0x1006),'synthetic_sub8':(0x27f494,0x4e0,8,1)}[kind]
        e=m.phase('original pure Close classification '+kind,start,abi=True,sp=SP,x30=pp.STOP,x0=a,x1=b)
        assert e['return_u32_if_returned']==expected
        return {'seed':seed,'kind':kind,'inputs':[a,b],'native_factor':expected,'events':[e],
            'actual_Close_reply_generation_or_arrival_proven':False}
    finally:m.close()

def run(out):
    im.volume();assert sha(PRIOR.read_bytes())==PRIOR_SHA
    for x in json.loads(PRIOR.read_text())['files']:
        p=ROOT/x['path'];assert p.stat().st_size==x['bytes'] and sha(p.read_bytes())==x['sha256']
    assert (BASE/'GOAL_STATUS.json').read_bytes()==(STAGE/'goal-status-before.json').read_bytes()
    out.mkdir();(out/'executed-source.py').write_bytes(Path(__file__).read_bytes())
    j={'status':'RUNNING','created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source_sha256':sha(Path(__file__).read_bytes()),
        'decision_cases':[],'cleanup_cases':[],'classifier_cases':[],'goal_complete':False,'persistent_write_release':False,
        'camera_Windows_UU_operations':False,'actual_Close_global_quiescence_MAIN_recording_or_recovery_proven':False}
    try:
        for seed in (0xa5,0xc3):
            for idx,count,mode in ((0,0,0),(1,1,0),(2,2,0),(3,255,1)):j['decision_cases'].append(decision(seed,idx,count,mode))
            for v in (0,1):j['cleanup_cases'].append(cleanup_tail(seed,v))
            for kind in ('Close_expect','synthetic_sub9','synthetic_sub8'):j['classifier_cases'].append(classification(seed,kind))
        j['bounded_phases']=sum(len(c['events']) for k in ('decision_cases','cleanup_cases','classifier_cases') for c in j[k])
        j['status']='PASS_NATIVE_CLOSE_COUNTER_DECISION_AND_CLEANUP_SCOPE_NOT_FULL_SHUTDOWN'
        (out/'close-counter-results.json').write_text(json.dumps(j,ensure_ascii=False,indent=2)+'\n')
        print(json.dumps({'bounded_phases':j['bounded_phases'],'status':j['status']}))
    except Exception:
        j['status']='FAILED_NO_PASSING_RESULT';j['error']=traceback.format_exc()
        (out/'attempt-failure.json').write_text(json.dumps(j,ensure_ascii=False,indent=2)+'\n');raise
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);run(p.parse_args().out)
