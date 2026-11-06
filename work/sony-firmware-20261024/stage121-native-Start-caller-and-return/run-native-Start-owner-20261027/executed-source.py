#!/usr/bin/env python3
"""Native post-Start callback-record association; no real owner or callbacks."""
from pathlib import Path
import argparse,datetime,hashlib,json,struct,sys,traceback
STAGE=Path(__file__).resolve().parent;sys.path.insert(0,str(STAGE));import start_caller as t
OWNER=t.S+0x8000
def sha(b):return hashlib.sha256(b).hexdigest()
class Guest(t.Guest):
    def __init__(self,seed):
        super().__init__(seed);self.allowed.extend([(0xca7b0,0xca81c),(0xfc4c0,0xfc54c)])
        self.boundaries.update({0x7dfa0:'before_original_callback_records_lock',0xfc29c:'before_original_error_fanout'})
def trial(seed,status):
    m=Guest(seed)
    try:
        raw=bytearray(56);struct.pack_into('<Q',raw,0x30,OWNER);m.uc.mem_write(t.EXEC,bytes(raw))
        old=bytes((seed+i*7)&255 for i in range(0x180));m.uc.mem_write(OWNER,old)
        ev=[m.phase('original ExecEncStart prologue before diagnostic, declared callback-record pointer',0xca6e4,
            sp=t.SP,x30=t.pp.STOP,x0=t.EXEC)]
        assert ev[-1]['reason']=='boundary: before_original_MPR_diagnostic'
        ev.append(m.phase('independent declared Codec return; native caller chooses callback registration or error path',0xca7b0,x0=status))
        callback=t.prev.prev.readq(m,0x2fad98);assert callback==0xd714c
        if status==0:
            assert ev[-1]['reason']=='boundary: before_original_callback_records_lock'
            ev.append(m.phase('independent post-lock native four callback-pointer stores before unlock',0xfc534,
                outputs=[(OWNER+i*0x60+0x10,OWNER+i*0x60+0x18) for i in range(4)]))
            assert ev[-1]['reason']=='boundary: before_original_Codec_normalLock_unlock'
            expected=bytearray(old)
            for i in range(4):struct.pack_into('<Q',expected,i*0x60+0x10,callback)
            assert bytes(m.uc.mem_read(OWNER,0x180))==bytes(expected)
            outcome='four_error_callback_pointers_prepared'
        else:
            assert ev[-1]['reason']=='boundary: before_original_MPR_diagnostic'
            ev.append(m.phase('independent post-error-diagnostic original pointer/code handoff before fanout',0xca7e8))
            assert ev[-1]['reason']=='boundary: before_original_error_fanout'
            assert m.uc.reg_read(t.reg('x0'))==OWNER and m.uc.reg_read(t.reg('w1'))==status
            assert bytes(m.uc.mem_read(OWNER,0x180))==old;outcome='same_record_pointer_and_error_code_before_fanout'
        assert bytes(m.uc.mem_read(t.EXEC,56))==bytes(raw)
        return {'seed':seed,'declared_Codec_return':status,'outcome':outcome,'callback_record_stride':0x60,
            'callback_record_count':4,'callback_symbol':'mpr::NotifyMovieRecError','callback_ELF_VA':hex(callback),
            'events':ev,'actual_owner_active_records_error_delivery_and_recording_instance_proven':False,
            'all_thread_lock_unlock_logging_error_fanout_and_callback_bodies_unexecuted':True}
    finally:m.close()
def run(out):
    t.im.volume();assert (t.BASE/'GOAL_STATUS.json').read_bytes()==(STAGE/'goal-status-before.json').read_bytes()
    src=STAGE/'run-native-Start-caller-20261027/start-caller-results.json';j0=json.loads(src.read_text())
    assert j0['status']=='PASS_NATIVE_START_CALLER_RETURN_LAYERS_NOT_HARDWARE_COMPLETION'
    out.mkdir();(out/'executed-source.py').write_bytes(Path(__file__).read_bytes())
    j={'status':'RUNNING','created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'source_sha256':sha(Path(__file__).read_bytes()),'prior_Start_results_sha256':sha(src.read_bytes()),'cases':[],
        'camera_Windows_UU_operations':False,'actual_Start_hardware_or_recovery_proven':False}
    try:
        for seed in (0xa5,0xc3):
            for status in (0,2):j['cases'].append(trial(seed,status))
        j['bounded_phases']=sum(len(c['events']) for c in j['cases'])
        j['status']='PASS_NATIVE_START_CALLBACK_RECORD_POINTER_HANDOFF_NOT_REAL_INSTANCE_BINDING'
        (out/'start-owner-results.json').write_text(json.dumps(j,ensure_ascii=False,indent=2)+'\n')
        print(json.dumps({'cases':len(j['cases']),'bounded_phases':j['bounded_phases'],'status':j['status']}))
    except Exception:
        j['status']='FAILED_NO_PASSING_RESULT';j['error']=traceback.format_exc()
        (out/'attempt-failure.json').write_text(json.dumps(j,ensure_ascii=False,indent=2)+'\n');raise
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);run(p.parse_args().out)
