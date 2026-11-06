#!/usr/bin/env python3
"""Couple pinned guest frontend, native parameter copy and DMM mode selector."""
from pathlib import Path
import argparse,datetime,hashlib,json,struct,sys,traceback
STAGE=Path(__file__).resolve().parent;BASE=STAGE.parent;ROOT=BASE.parents[1]
sys.path.insert(0,str(BASE/'stage117-native-audio-proxy-admission'));import audio_proxy as source
front,pp,r,im,MPR,SP,reg=source.front,source.pp,source.r,source.im,source.front.MPR,source.SP,source.reg
MODEL=pp.SCRATCH+0x8000
PRIOR=BASE/'stage124-native-Close-counter-and-cleanup/final-receipt.json'
PRIOR_SHA='cf0d96f2e08b8e20271eee98817bbcb13b654f07cde63829104cd6992879f55d'
P117=BASE/'stage117-native-audio-proxy-admission/final-receipt.json'
P117_SHA='ce06b8f2089d76a25e1b71f01ada41fde6b8e834a080fa299082f79b4f5f324b'
RESULT117=P117.parent/'run-original-helpers-and-admission-20261027/audio-proxy-results.json'
def sha(b):return hashlib.sha256(b).hexdigest()
def saved(m):return {n:m.uc.reg_read(reg(n)) for n in ['x'+str(i) for i in range(19,30)]+['d'+str(i) for i in range(8,16)]}
def restored(m,ss):return m.uc.reg_read(reg('sp'))==SP and all(m.uc.reg_read(reg(n))==v for n,v in ss.items())
class Guest(front.Guest):
    def __init__(self,seed):
        super().__init__(seed);self.uc.mem_write(front.CODE,source.IMAGE)
        self.images=[(a,d) for a,d in self.images if a!=front.CODE]+[(front.CODE,source.IMAGE)]
        self.allowed=[(a,z) for a,z in self.allowed if not(front.CODE<=a<front.CODE+0x2000)]
        self.allowed.extend([(front.CODE,front.CODE+source.SIZE),(front.CODE+0x1000,front.CODE+0x1030),
            (0xccb04,0xccb18),(0xcd5c4,0xcd700),(0x2af638,0x2af810),(0x2af9ec,0x2afa58)])
        self.boundaries.update({0xccb14:'after_original_parameter_copy_before_other_RecordStart_work',
            0xc8c70:'before_original_MPR_diagnostic',0x7cbc0:'before_original_RemoveAreaExtList',
            0x822e0:'before_original_FreeDmmExtList'})
    def code(self,u,pc,n,user):
        if pc==0x7bfd0:
            name='_ZN3mpr10DmmMemInfo19UnitTypeTableSelectEi';assert MPR.plt[pc]==name and MPR.symbols[name]['va']==0x2af638
            self.pcs.append(hex(pc));self.calls.append({'original_symbol_binding':name,'PLT':hex(pc),'target':'0x2af638'})
            u.reg_write(reg('pc'),0x2af638);return
        return super().code(u,pc,n,user)
def copy_model(m,param,word0,label):
    m.uc.mem_write(MODEL,bytes(0x240));m.uc.mem_write(MODEL,struct.pack('<I',word0))
    e=m.phase('independent post-check frame: original445-byte parameter copy '+label,0xccb04,
        outputs=[(MODEL+0x58,MODEL+0x58+0x1bd)],sp=SP,x30=pp.STOP,x19=MODEL,x1=param)
    assert e['reason']=='boundary: after_original_parameter_copy_before_other_RecordStart_work'
    assert bytes(m.uc.mem_read(MODEL+0x58,0x1bd))==bytes(m.uc.mem_read(param,0x1bd))
    return e
def mode(m,label):
    ss=saved(m);ev=[m.phase('original GetDmmModeId prologue '+label,0xcd5c4,sp=SP,x30=pp.STOP,x0=MODEL)]
    assert ev[-1]['reason']=='boundary: before_original_MPR_diagnostic'
    ev.append(m.phase('independent post-log original DMM flag computation '+label,0xcd60c))
    assert ev[-1]['reason']=='boundary: before_original_MPR_diagnostic'
    fp=m.uc.reg_read(reg('x29'));mask=struct.unpack('<I',bytes(m.uc.mem_read(fp+0x38,4)))[0]
    ev.append(m.phase('independent post-log original DMM signed-byte table lookup '+label,0xcd69c))
    assert ev[-1]['reason']=='boundary: before_original_MPR_diagnostic'
    ev.append(m.phase('independent post-log native mode return '+label,0xcd6ec))
    value=m.uc.reg_read(reg('w0'));assert ev[-1]['reason']=='returned' and restored(m,ss)
    return value,mask,ev
def profile(c):
    seed=c['seed'];m=Guest(seed)
    try:
        front.fixture(m,seed,0x2e6f9b0);original=bytes.fromhex(c['native_param_hex']);m.uc.mem_write(front.SRC,original)
        e=m.phase('pinned stage117 compiled guest frontend produces target-type6 values',source.ENTRY,
            outputs=[(front.DST,front.DST+0x1c0)],abi=True,sp=SP,x30=pp.STOP,
            x0=front.GATE,x1=front.SRC,x2=front.DST,x3=0x2e6f9b0,x4=front.EPOCH)
        assert e['return_u32_if_returned']==0
        candidate=bytes(m.uc.mem_read(front.DST,0x1c0));expected=bytearray(original);struct.pack_into('<I',expected,0x170,6)
        assert candidate==bytes(expected) and bytes(m.uc.mem_read(front.SRC,0x1c0))==original
        ev=[e];pairs=[]
        for word0 in (1,2):
            ev.append(copy_model(m,front.SRC,word0,'original type5'));a,am,ee=mode(m,'original type5');ev.extend(ee)
            before=bytes(m.uc.mem_read(MODEL,0x240))
            ev.append(copy_model(m,front.DST,word0,'candidate type6'));b,bm,ee=mode(m,'candidate type6');ev.extend(ee)
            after=bytes(m.uc.mem_read(MODEL,0x240));changed=[i for i,(x,y) in enumerate(zip(before,after)) if x!=y]
            assert changed==[0x1c8] and a==b and am==bm
            assert a==({1:21,2:25}[word0] if c['label']=='proxy_disabled' else {1:31,2:32}[word0])
            pairs.append({'declared_Model_word0':word0,'original_type':5,'candidate_type':6,'native_flag_mask':am,
                'native_original_mode':a,'native_candidate_mode':b,'actual_changed_Model_byte_offsets':[hex(i) for i in changed]})
        return {'seed':seed,'source_label':c['label'],'frontend_native_candidate448':candidate.hex(),
            'native_param_source_sha256':sha(original),'pairs':pairs,'events':ev,
            'earlier_omitted_initializers_real_Model_word0_and_live_configuration_unproven':True,
            'same_DMM_mode_not_allocation_buffer_or_hardware_acceptance_proof':True,
            'actual_FRONT_gate_hook_and_Main_recording_unproven':True}
    finally:m.close()
def table_and_free(seed,modeid):
    m=Guest(seed)
    try:
        ev=[m.phase('original UnitTypeTableSelect on declared mode ID',0x2af638,abi=True,sp=SP,x30=pp.STOP,x0=modeid&0xffffffff)]
        ptr=m.uc.reg_read(reg('x0'));valid=0<=modeid<=38;assert bool(ptr)==valid
        word8=struct.unpack('<I',MPR.read(ptr+8,4))[0] if ptr else None
        ev.append(m.phase('original FreeDmmMemory(mode,7) before actual removal or native no-op return',0x2af9ec,
            abi=not valid,sp=SP,x30=pp.STOP,x0=modeid&0xffffffff,x1=7))
        if valid:
            assert ev[-1]['reason']=='boundary: before_original_RemoveAreaExtList' and m.uc.reg_read(reg('w0'))==word8
            result=None
        else:
            result=m.uc.reg_read(reg('w0'));assert ev[-1]['reason']=='returned' and result==int(modeid>38)
        return {'seed':seed,'declared_mode':modeid,'native_table_pointer_ELF':hex(ptr),'original_table_word8':word8,
            'native_free_return_for_noop_only':result,'events':ev,
            'actual_area_removal_ExtList_free_allocated_memory_or_runtime_table_proven':False,
            'invalid_positive_mode_true_return_not_memory_release_proof':True}
    finally:m.close()
def run(out):
    im.volume()
    for p,h in ((PRIOR,PRIOR_SHA),(P117,P117_SHA)):
        assert sha(p.read_bytes())==h
        for x in json.loads(p.read_text())['files']:
            q=ROOT/x['path'];assert q.stat().st_size==x['bytes'] and sha(q.read_bytes())==x['sha256']
    assert (BASE/'GOAL_STATUS.json').read_bytes()==(STAGE/'goal-status-before.json').read_bytes()
    out.mkdir();(out/'executed-source.py').write_bytes(Path(__file__).read_bytes())
    j={'status':'RUNNING','created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source_sha256':sha(Path(__file__).read_bytes()),
        'stage117_source_result_sha256':sha(RESULT117.read_bytes()),'profiles':[],'table_free_cases':[],
        'goal_complete':False,'persistent_write_release':False,'camera_Windows_UU_operations':False,
        'actual_DMM_allocation_release_MAIN_hardware_or_recovery_proven':False}
    try:
        sj=json.loads(RESULT117.read_text())
        for c in sj['caller_cases']:
            if c['label'] in ('proxy_disabled','HEVC16','HEVC9','AVC6'):j['profiles'].append(profile(c))
        modes=sorted({x['native_candidate_mode'] for c in j['profiles'] for x in c['pairs']})
        for seed in (0xa5,0xc3):
            for value in modes+[39,-1]:j['table_free_cases'].append(table_and_free(seed,value))
        j['bounded_phases']=sum(len(c['events']) for k in ('profiles','table_free_cases') for c in j[k])
        j['status']='PASS_NATIVE_FRONTEND_DMM_MODE_CONSISTENCY_NOT_ALLOCATION_OR_RECORDING'
        (out/'frontend-DMM-results.json').write_text(json.dumps(j,ensure_ascii=False,indent=2)+'\n')
        print(json.dumps({'profiles':len(j['profiles']),'pairs':sum(len(c['pairs']) for c in j['profiles']),
            'table_free_cases':len(j['table_free_cases']),'bounded_phases':j['bounded_phases'],'status':j['status']}))
    except Exception:
        j['status']='FAILED_NO_PASSING_RESULT';j['error']=traceback.format_exc()
        (out/'attempt-failure.json').write_text(json.dumps(j,ensure_ascii=False,indent=2)+'\n');raise
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);run(p.parse_args().out)
