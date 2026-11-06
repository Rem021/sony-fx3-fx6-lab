#!/usr/bin/env python3
"""Native pre-encoder slot publication, with explicit selection/lock gaps."""
from pathlib import Path
import argparse,datetime,hashlib,json,struct,sys,traceback
STAGE=Path(__file__).resolve().parent;BASE=STAGE.parent;ROOT=BASE.parents[1]
sys.path.insert(0,str(BASE/'stage119-native-record-status-lock-contract'));import record_status as prev
front,pp,r,im,MPR,SP,reg=prev.front,prev.pp,prev.r,prev.im,prev.MPR,prev.SP,prev.reg
S=pp.SCRATCH;INFO=S+0x1000;VECTOR=S+0x3000;PAIRS=S+0x4000;PAIR=S+0x5000
PRIOR=BASE/'stage119-native-record-status-lock-contract/final-receipt.json'
PRIOR_SHA='ec47dc9a30caf94e901b867e789cd471a785757f05e39e4ddf427910ce0d5b23'
BINDINGS={0x82ea0:('_ZN3mpr25getMovieRecStatusOutParamC1Ev',0xc9660),
    0x832c0:('_ZN3mpr26GetMovieRecStatusForUpdateEPNS_25getMovieRecStatusOutParamE',0xf41ec),
    0x7fd30:('_ZN3mpr17SetMovieRecStatusERKNS_25getMovieRecStatusOutParamEb',0xf3d2c)}
def sha(b):return hashlib.sha256(b).hexdigest()

class Guest(prev.Guest):
    def __init__(self,seed):
        super().__init__(seed)
        self.allowed.extend([(0xdc168,0xdc194),(0xdc194,0xdc1e8),(0xdc46c,0xdc4c8)])
        self.boundaries.update({0xc8c70:'before_original_MPR_diagnostic',
            0xdc09c:'before_original_vector_reallocation',0xdc4c8:'after_status_set_before_selected_count_store'})
    def code(self,u,pc,n,user):
        if pc in BINDINGS:
            name,target=BINDINGS[pc];assert MPR.plt[pc]==name and MPR.symbols[name]['va']==target
            self.pcs.append(hex(pc));self.calls.append({'original_symbol_binding':name,'PLT':hex(pc),'target':hex(target),
                'scope':'Same-ELF native function executes; no output/return adapter. Actual locks/services still stop.'})
            u.reg_write(reg('pc'),target);return
        return super().code(u,pc,n,user)

CASES=(('single',((0,1),)),('mixed',((1,1),(3,0))),
    ('four_out_of_order',((3,1),(2,1),(1,0),(0,1))),
    ('duplicate_structural_control_not_natural_selection',((1,1),(1,0),(2,1))))

def trial(seed,label,rows):
    m=Guest(seed)
    try:
        # Artificial value records; no real slot/media or feasibility result.
        initial=bytearray(0x88);struct.pack_into('<I',initial,0,0x53)
        for i in range(4):initial[4+i*16]=1;struct.pack_into('<I',initial,8+i*16,0x100+i)
        m.uc.mem_write(prev.STATUS,bytes(initial));m.uc.mem_write(INFO,bytes(0x240))
        m.uc.mem_write(VECTOR,struct.pack('<QQQ',PAIRS,PAIRS,PAIRS+32));ev=[]
        for i,(slot,flag) in enumerate(rows):
            record=struct.pack('<IB3x',slot,flag);m.uc.mem_write(PAIR,record)
            ev.append(m.phase('original8-byte pair append with declared existing vector capacity',0xdc168,
                outputs=[(VECTOR+8,VECTOR+16),(PAIRS+i*8,PAIRS+(i+1)*8)],abi=True,
                sp=SP,x30=pp.STOP,x0=VECTOR,x1=PAIR))
            assert ev[-1]['reason']=='returned' and prev.readq(m,VECTOR+8)==PAIRS+(i+1)*8
            assert bytes(m.uc.mem_read(PAIRS+i*8,8))==record
        vector_bytes=bytes(m.uc.mem_read(VECTOR,24));pair_bytes=bytes(m.uc.mem_read(PAIRS,len(rows)*8))
        ev.append(m.phase('original GetStartSlotId prologue before first diagnostic',0xdc194,
            sp=SP,x30=pp.STOP,x0=INFO))
        assert ev[-1]['reason']=='boundary: before_original_MPR_diagnostic'
        caller_fp=m.uc.reg_read(reg('x29'));assert caller_fp==SP-0x120 and m.uc.reg_read(reg('x20'))==caller_fp+0x98
        # Native vector bytes are carried into an independently declared
        # post-selection frame; actual converter/feasibility/selection omitted.
        m.uc.mem_write(caller_fp+0x80,vector_bytes);m.uc.reg_write(reg('x21'),sum(flag for slot,flag in rows))
        ev.append(m.phase('independent accepted selection frame calls native constructor and ForUpdate getter before write lock',0xdc46c))
        assert ev[-1]['reason']=='boundary: before_original_write_lock' and m.uc.reg_read(reg('x0'))==prev.LOCK+8
        assert bytes(m.uc.mem_read(caller_fp+0x98,0x88))==struct.pack('<I',0x53)+bytes(0x84)
        ev.append(m.phase('independent post-lock native copy returns to original caller loop, then native status writer before unlock',0xf420c,
            image_outputs=[(prev.STATUS,prev.STATUS+0x88)]))
        assert ev[-1]['reason']=='boundary: before_original_pthread_rwlock_unlock'
        expected=bytearray(initial)
        for slot,flag in rows:expected[0xc+slot*16]=flag
        assert bytes(m.uc.mem_read(caller_fp+0x98,0x88))==bytes(expected)
        assert bytes(m.uc.mem_read(prev.STATUS,0x88))==bytes(expected)
        changed=[i for i,(a,b) in enumerate(zip(initial,expected)) if a!=b]
        assert changed==[0xc+i*16 for i in range(4) if expected[0xc+i*16]]
        setter_fp=m.uc.reg_read(reg('x29'));event=bytes(m.uc.mem_read(setter_fp+0x20,16))
        flags=[int(bool(expected[0xc+i*16])) for i in range(4)]+[0]*5
        assert event==struct.pack('<I',0x1004)+bytes(flags)+bytes(3)
        ev.append(m.phase('independent post-unlock native status notification preparation before SetIssueEvent',0xf3e80))
        assert ev[-1]['reason']=='boundary: before_original_SetIssueEvent'
        assert [m.uc.reg_read(reg('x'+str(i))) for i in range(3)]==[0x1004,setter_fp+0x20,16]
        assert bytes(m.uc.mem_read(VECTOR,24))==vector_bytes and bytes(m.uc.mem_read(PAIRS,len(rows)*8))==pair_bytes
        assert bytes(m.uc.mem_read(INFO,0x240))==bytes(0x240)
        return {'seed':seed,'label':label,'declared_slot_boolean_pairs':[list(x) for x in rows],
            'original_pair_append_bytes':pair_bytes.hex(),'original_pair_vector':vector_bytes.hex(),
            'native_status_before':bytes(initial).hex(),'native_status_after':bytes(expected).hex(),
            'actual_changed_status_offsets':[hex(i) for i in changed],'native_prepared_event16':event.hex(),
            'events':ev,'selection_source_is_explicit_fixture_not_real_media_or_feasibility':True,
            'post_log_post_selection_and_post_lock_are_independent_frames':True,
            'Open_Start_queue_or_hardware_not_executed':True,'actual_idle_epoch_or_encoder_running_proven':False,
            'no_actual_notification_or_complete_GetStartSlotId_return':True}
    finally:m.close()

def run(out):
    im.volume();assert sha(PRIOR.read_bytes())==PRIOR_SHA
    for x in json.loads(PRIOR.read_text())['files']:
        p=ROOT/x['path'];assert p.stat().st_size==x['bytes'] and sha(p.read_bytes())==x['sha256']
    assert (BASE/'GOAL_STATUS.json').read_bytes()==(STAGE/'goal-status-before.json').read_bytes()
    out.mkdir();(out/'executed-source.py').write_bytes(Path(__file__).read_bytes())
    j={'status':'RUNNING','created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'source_sha256':sha(Path(__file__).read_bytes()),'cases':[],'goal_complete':False,'persistent_write_release':False,
        'camera_Windows_UU_operations':False,'actual_MAIN_recording_current_state_or_recovery_proven':False}
    try:
        for seed in (0xa5,0xc3):
            for label,rows in CASES:j['cases'].append(trial(seed,label,rows))
        j['bounded_phases']=sum(len(c['events']) for c in j['cases'])
        j['status']='PASS_NATIVE_SLOT_STATUS_PUBLICATION_PRECEDES_THIS_RECSTART_QUEUE_NOT_ENCODER_COMPLETION'
        (out/'slot-publication-results.json').write_text(json.dumps(j,ensure_ascii=False,indent=2)+'\n')
        print(json.dumps({'cases':len(j['cases']),'bounded_phases':j['bounded_phases'],'status':j['status']}))
    except Exception:
        j['status']='FAILED_NO_PASSING_RESULT';j['error']=traceback.format_exc()
        (out/'attempt-failure.json').write_text(json.dumps(j,ensure_ascii=False,indent=2)+'\n');raise
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);run(p.parse_args().out)
