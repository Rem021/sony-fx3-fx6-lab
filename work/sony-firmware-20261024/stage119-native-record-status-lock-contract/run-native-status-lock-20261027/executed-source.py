#!/usr/bin/env python3
"""Native status-copy and lock ownership evidence; no real locks or camera."""
from pathlib import Path
import argparse,datetime,hashlib,json,struct,sys,traceback
STAGE=Path(__file__).resolve().parent;BASE=STAGE.parent;ROOT=BASE.parents[1]
sys.path.insert(0,str(BASE/'stage118-native-parameter-notice-wait'));import notice_wait as prev
front=prev.prev.front;core,pp,r,im,MPR,SP,reg=front.core,front.pp,front.r,front.im,front.MPR,front.SP,front.reg
S=pp.SCRATCH;DST=S+0x1000;SOURCE=S+0x3000
STATUS=0x38d4f8;LOCK=0x38d478;PARAM_LOCK=0x38cc30;INTEG=0x372190
PRIOR=BASE/'stage118-native-parameter-notice-wait/final-receipt.json'
PRIOR_SHA='f98c16ef575633a342571398fc5d48fa584c8051aaa3a0f87de900601f22d027'
def sha(b):return hashlib.sha256(b).hexdigest()
def readq(m,a):return struct.unpack('<Q',bytes(m.uc.mem_read(a,8)))[0]
def saved(m):return {n:m.uc.reg_read(reg(n)) for n in ['x'+str(i) for i in range(19,30)]+['d'+str(i) for i in range(8,16)]}
def restored(m,ss):return m.uc.reg_read(reg('sp'))==SP and all(m.uc.reg_read(reg(n))==v for n,v in ss.items())

class Guest(front.Guest):
    def __init__(self,seed):
        super().__init__(seed)
        self.allowed.extend([(0xc9660,0xc9690),(0xf3d2c,0xf3edc),(0xf3f7c,0xf3fc8),
            (0xf4168,0xf41a8),(0xf41ec,0xf4230),(0xf4250,0xf4270),(0xf0fe8,0xf0ff0),
            (0xf1054,0xf105c),(0xdc554,0xdc55c),(0xd84a8,0xd84b0)])
        self.boundaries.pop(0x82f40)
        self.boundaries.update({0x7f060:'before_original_pthread_rwlock_unlock',
            0x81e90:'before_original_SetIssueEvent',0x820e0:'before_original_full_status_overload'})
        self.uc.mem_protect(0x38d000,0x1000,r.unicorn.UC_PROT_READ|r.unicorn.UC_PROT_WRITE)
        for a,v in ((0x2fae70,LOCK),(0x2faae8,STATUS),(0x2f9418,INTEG)):
            assert readq(self,a)==v,('resolved_data_symbol',hex(a),hex(readq(self,a)),hex(v))
    def code(self,u,pc,n,user):
        if pc==0x82f40:
            name='_ZN3mpr6thread6rwLock6unlockEv';assert MPR.plt[pc]==name
            target=MPR.symbols[name]['va'];assert target==0xf0fe8
            self.pcs.append(hex(pc));self.calls.append({'original_symbol_binding':name,'PLT':hex(pc),'target':hex(target),
                'scope':'Guest address binding only; original two-instruction wrapper executes. Pthread body still stops.'})
            u.reg_write(reg('pc'),target);return
        return super().code(u,pc,n,user)
    def state_fixture(self,seed):
        raw=bytearray((seed+i*17)&255 for i in range(0x88));struct.pack_into('<I',raw,0,0x53)
        self.uc.mem_write(STATUS,bytes(raw));return bytes(raw)

def ctor(seed):
    m=Guest(seed)
    try:
        e=m.phase('original status constructor and same-firmware memset',0xc9660,outputs=[(DST,DST+0x88)],abi=True,
            sp=SP,x30=pp.STOP,x0=DST)
        assert bytes(m.uc.mem_read(DST,0x88))==struct.pack('<I',0x53)+bytes(0x84)
        return {'seed':seed,'events':[e],'bytes':0x88,'header':0x53,'zeros_not_claimed_idle_or_live_slots':True}
    finally:m.close()

def getter(seed,update):
    m=Guest(seed)
    try:
        data=m.state_fixture(seed);ss=saved(m)
        start=0xf41ec if update else 0xf3f7c;post=0xf420c if update else 0xf3f9c
        ev=[m.phase('original '+('ForUpdate writer' if update else 'Internal reader')+' getter before lock',start,
            sp=SP,x30=pp.STOP,x0=DST)]
        assert ev[-1]['reason']=='boundary: '+('before_original_write_lock' if update else 'before_original_read_lock')
        assert m.uc.reg_read(reg('x0'))==LOCK+8
        ev.append(m.phase('independent post-lock original136-byte copy'+(' and native return retaining lock ownership contract' if update else ' before unlock'),
            post,outputs=[(DST,DST+0x88)]))
        assert bytes(m.uc.mem_read(DST,0x88))==data and bytes(m.uc.mem_read(STATUS,0x88))==data
        if update:
            assert ev[-1]['reason']=='returned' and m.uc.reg_read(reg('w0'))==0 and restored(m,ss)
            assert 0x82f40 not in [int(pc,16) for e in ev for pc in e['pcs']]
        else:
            assert ev[-1]['reason']=='boundary: before_original_pthread_rwlock_unlock' and m.uc.reg_read(reg('x0'))==LOCK+8
            ev.append(m.phase('independent post-unlock original getter epilogue',0xf3fb8))
            assert ev[-1]['reason']=='returned' and m.uc.reg_read(reg('w0'))==0 and restored(m,ss)
        return {'seed':seed,'ForUpdate':update,'status_bytes':data.hex(),'copy_bytes':0x88,
            'lock_object':hex(LOCK),'pthread_lock_pointer':hex(LOCK+8),'events':ev,
            'original_return_does_not_prove_actual_lock_or_live_state':True,
            'ForUpdate_not_a_read_only_diagnostic_candidate':update,'source_not_real_camera_status':True}
    finally:m.close()

def explicit_unlock(seed):
    m=Guest(seed)
    try:
        e=m.phase('original explicit status-unlock API and rwLock wrapper stop before pthread',0xf4250,sp=SP,x30=pp.STOP)
        assert e['reason']=='boundary: before_original_pthread_rwlock_unlock' and m.uc.reg_read(reg('x0'))==LOCK+8
        return {'seed':seed,'events':[e],'no_actual_unlock_or_ownership_claim':True}
    finally:m.close()

def setter(seed,kind):
    m=Guest(seed)
    try:
        old=m.state_fixture(seed);new=bytearray(old);force=kind=='forced_unchanged';flags=[0]*9
        if kind=='global_word44':struct.pack_into('<I',new,0x44,struct.unpack_from('<I',new,0x44)[0]^1);flags[4]=1
        elif kind=='first_group_row2':new[0x24]^=1;flags[2]=1
        elif kind=='second_group_row3':struct.pack_into('<I',new,0x7c,struct.unpack_from('<I',new,0x7c)[0]^1);flags[8]=1
        elif kind=='ignored_padding5':new[5]^=1
        elif kind=='ignored_header0':struct.pack_into('<I',new,0,0x1234)
        elif kind not in ('unchanged','forced_unchanged'):raise ValueError(kind)
        m.uc.mem_write(SOURCE,bytes(new));ss=saved(m);changed=any(flags)
        if force:flags=[1]*9
        ev=[m.phase('independent pre-held-update-lock contract: original status compare, conditional copy, and unlock wrapper',0xf3d2c,
            image_outputs=[(STATUS,STATUS+0x88)],sp=SP,x30=pp.STOP,x0=SOURCE,x1=int(force))]
        assert ev[-1]['reason']=='boundary: before_original_pthread_rwlock_unlock' and m.uc.reg_read(reg('x0'))==LOCK+8
        assert bytes(m.uc.mem_read(STATUS,0x88))==(bytes(new) if changed else old)
        fp=m.uc.reg_read(reg('x29'));event=bytes(m.uc.mem_read(fp+0x20,16))
        assert event==struct.pack('<I',0x1004)+bytes(flags)+bytes(3)
        if changed or force:
            ev.append(m.phase('independent post-unlock notification arguments before queuing',0xf3e80))
            assert ev[-1]['reason']=='boundary: before_original_SetIssueEvent'
            assert [m.uc.reg_read(reg('x'+str(i))) for i in range(3)]==[0x1004,fp+0x20,16]
        else:
            ev.append(m.phase('independent post-unlock no-notification epilogue',0xf3ed8))
            assert ev[-1]['reason']=='returned' and m.uc.reg_read(reg('w0'))==0 and restored(m,ss)
        assert bytes(m.uc.mem_read(SOURCE,0x88))==bytes(new)
        assert not any(int(pc,16) in (0x81860,0x82530) for e in ev for pc in e['pcs'])
        return {'seed':seed,'kind':kind,'force_input':force,'native_compared_field_changed':changed,
            'global_copied':changed,'notification_prepared':changed or force,'event_flags':flags,'event16':event.hex(),
            'events':ev,'preheld_lock_is_declared_not_acquired':True,'header_padding_not_validated_by_this_slice':True,
            'no_actual_event_dispatch_recording_or_epoch_proof':True}
    finally:m.close()

def integ(seed,api):
    m=Guest(seed)
    try:
        site,name={'SetMovieRecParam':(0xf1054,'x21'),'RecStart':(0xdc554,'x23'),'RecStop':(0xd84a8,'x24')}[api]
        e=m.phase('independent '+api+' frame loads same native g_integApiMutex before pthread lock',site,
            sp=SP,x30=pp.STOP,**{name:0x2f9000})
        assert e['reason']=='boundary: before_original_setter_mutex' and m.uc.reg_read(reg('x0'))==INTEG
        return {'seed':seed,'API':api,'events':[e],'original_mutex_object':hex(INTEG),
            'actual_mutual_exclusion_current_thread_all_writers_or_start_completion_proven':False}
    finally:m.close()

def public(seed):
    m=Guest(seed)
    try:
        e=m.phase('original public no-input GetMovieRecStatus wrapper before full overload',0xf4168,
            sp=SP,x30=pp.STOP,x0=DST)
        assert e['reason']=='boundary: before_original_full_status_overload' and m.uc.reg_read(reg('x1'))==DST
        a=m.uc.reg_read(reg('x0'));assert bytes(m.uc.mem_read(a,0x30))==struct.pack('<I',0x52)+bytes(0x2c)
        return {'seed':seed,'events':[e],'input48':bytes(m.uc.mem_read(a,0x30)).hex(),
            'public_overload_logs_media_rate_check_and_internal_getter_unexecuted':True}
    finally:m.close()

def run(out):
    im.volume();assert sha(PRIOR.read_bytes())==PRIOR_SHA
    for x in json.loads(PRIOR.read_text())['files']:
        p=ROOT/x['path'];assert p.stat().st_size==x['bytes'] and sha(p.read_bytes())==x['sha256']
    assert (BASE/'GOAL_STATUS.json').read_bytes()==(STAGE/'goal-status-before.json').read_bytes()
    out.mkdir();(out/'executed-source.py').write_bytes(Path(__file__).read_bytes())
    groups=('constructors','getters','explicit_unlocks','setters','integration_mutex_sites','public_wrappers')
    j={'status':'RUNNING','created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'source_sha256':sha(Path(__file__).read_bytes()),**{k:[] for k in groups},
        'goal_complete':False,'persistent_write_release':False,'camera_Windows_UU_operations':False,
        'actual_record_idle_configuration_epoch_MAIN_encoding_or_recovery_proven':False}
    try:
        for seed in (0xa5,0xc3):
            j['constructors'].append(ctor(seed))
            for update in (False,True):j['getters'].append(getter(seed,update))
            j['explicit_unlocks'].append(explicit_unlock(seed))
            for k in ('unchanged','forced_unchanged','global_word44','first_group_row2','second_group_row3','ignored_padding5','ignored_header0'):
                j['setters'].append(setter(seed,k))
            for api in ('SetMovieRecParam','RecStart','RecStop'):j['integration_mutex_sites'].append(integ(seed,api))
            j['public_wrappers'].append(public(seed))
        j['bounded_phases']=sum(len(c['events']) for k in groups for c in j[k])
        j['status']='PASS_NATIVE_RECORD_STATUS_COPY_LOCK_CONTRACT_NOT_LIVE_IDLE_OR_EPOCH'
        (out/'record-status-results.json').write_text(json.dumps(j,ensure_ascii=False,indent=2)+'\n')
        print(json.dumps({k:len(j[k]) for k in groups}|{'bounded_phases':j['bounded_phases'],'status':j['status']}))
    except Exception:
        j['status']='FAILED_NO_PASSING_RESULT';j['error']=traceback.format_exc()
        (out/'attempt-failure.json').write_text(json.dumps(j,ensure_ascii=False,indent=2)+'\n');raise
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);run(p.parse_args().out)
