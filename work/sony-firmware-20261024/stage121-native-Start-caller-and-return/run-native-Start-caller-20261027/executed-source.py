#!/usr/bin/env python3
"""Native Start caller and post-wait return layers; no real service success."""
from pathlib import Path
import argparse,datetime,hashlib,json,struct,sys,traceback
STAGE=Path(__file__).resolve().parent;BASE=STAGE.parent;ROOT=BASE.parents[1]
sys.path.insert(0,str(BASE/'stage120-native-start-slot-publication'));import slot_publication as prev
pp,r,im,MPR,SP,reg=prev.pp,prev.r,prev.im,prev.MPR,prev.SP,prev.reg
S=pp.SCRATCH;EXEC=S+0x1000;PARAM=S+0x3000;HEADER=S+0x4000;REPLY=S+0x5000
PRIOR=BASE/'stage120-native-start-slot-publication/final-receipt.json'
PRIOR_SHA='d13abe6665ea70fac7129e9602473f70b1c937dc580e994b6c60b4c224fa0493'
def sha(b):return hashlib.sha256(b).hexdigest()
def saved(m):return prev.prev.saved(m)
def restored(m,ss):return prev.prev.restored(m,ss)

class Guest(prev.Guest):
    def __init__(self,seed):
        super().__init__(seed)
        self.allowed.extend([(0xca6e4,0xca7b0),(0xca4a4,0xca5c4),(0x27e0cc,0x27e244),
            (0x27fd64,0x27fee8),(0x27df44,0x27e0cc),(0x27f494,0x27fa34)])
        self.boundaries.update({0x136468:'before_original_GPS_helper',0x81340:'before_original_Codec_EncStart',
            0x7e350:'before_original_OSAL_allocation',0x82b20:'before_original_cond_wait',
            0x7d8b0:'before_original_sender_mutex_unlock',0x27dba8:'before_original_Codec_logger',
            0x80ef0:'before_original_Codec_normalLock_unlock'})
    def code(self,u,pc,n,user):
        if pc==0x7fb80:
            name='_ZN3mpr16SetEncStartParamERNS_14execEncStart_tEP17AvbbcApi_EncStart'
            assert MPR.plt[pc]==name and MPR.symbols[name]['va']==0xca4a4
            self.pcs.append(hex(pc));self.calls.append({'original_symbol_binding':name,'PLT':hex(pc),'target':'0xca4a4',
                'scope':'Original parameter builder executes; logging remains explicit gaps.'})
            u.reg_write(reg('pc'),0xca4a4);return
        return super().code(u,pc,n,user)

def producer(seed,label,audio,mask,seq,flags):
    m=Guest(seed)
    try:
        raw=bytearray(56);raw[1]=mask;raw[2]=seq;struct.pack_into('<I',raw,4,3)
        struct.pack_into('<I',raw,8,audio);struct.pack_into('<I',raw,0x10,15)
        raw[0x1c],raw[0x1d]=flags;struct.pack_into('<Q',raw,0x20,S+0x7000)
        raw[0x28]=raw[0x29]=1;struct.pack_into('<Q',raw,0x30,S+0x8000);m.uc.mem_write(EXEC,bytes(raw))
        ev=[m.phase('original single-stream ExecEncStart prologue before diagnostic',0xca6e4,sp=SP,x30=pp.STOP,x0=EXEC)]
        assert ev[-1]['reason']=='boundary: before_original_MPR_diagnostic'
        fp=m.uc.reg_read(reg('x29'));assert fp==SP-0x210
        ev.append(m.phase('independent post-log original48-byte reply clear before GPS helper',0xca73c))
        assert ev[-1]['reason']=='boundary: before_original_GPS_helper'
        assert bytes(m.uc.mem_read(fp+0x50,48))==bytes(48)
        ev.append(m.phase('independent post-GPS frame; original128-byte clear and original Start builder prologue',0xca770))
        assert ev[-1]['reason']=='boundary: before_original_MPR_diagnostic'
        assert bytes(m.uc.mem_read(fp+0x110,128))==bytes(128)
        ev.append(m.phase('independent builder post-log original scalar fields before end diagnostic',0xca4f0))
        assert ev[-1]['reason']=='boundary: before_original_MPR_diagnostic'
        ev.append(m.phase('independent builder post-log native return to original ExecEncStart callsite',0xca5b4))
        assert ev[-1]['reason']=='boundary: before_original_Codec_EncStart'
        assert [m.uc.reg_read(reg('x'+str(i))) for i in range(6)]==[fp+0x110,0x20,15,1,0,fp+0x50]
        payload=bytes(m.uc.mem_read(fp+0x110,128));expected=bytearray(128)
        struct.pack_into('<II',expected,0xc,1,1);struct.pack_into('<II',expected,0x2c,90000,90000)
        expected[0x40]=int(audio!=1);expected[0x44]=1
        expected[0x58]=(flags[0]^1) if not flags[1] else 1
        expected[0x5a]=mask;expected[0x5c]=seq;struct.pack_into('<I',expected,0x64,1)
        assert payload==bytes(expected) and bytes(m.uc.mem_read(EXEC,56))==bytes(raw)
        return {'seed':seed,'label':label,'declared_exec56':bytes(raw).hex(),'native_Start128':payload.hex(),
            'native_call_args':{'CodecType':0x20,'FileFormat':15,'count':1,'ViewId':0,'reply_bytes':48,'reply_pointer_nonnull':True},
            'mask_at_Start5a':mask,'sequence_byte_at_Start5c':seq,'events':ev,
            'original_GPS_metadata_logging_and_Codec_Start_unexecuted':True,
            'no_actual_full_request_producer_or_Main_profile_epoch_hardware_acceptance':True}
    finally:m.close()

def return_layers(seed,reply_status,wait_status):
    m=Guest(seed)
    try:
        packet=bytearray(48);struct.pack_into('<H',packet,2,3);struct.pack_into('<I',packet,0x14,reply_status)
        struct.pack_into('<I',packet,0x24,0x4e0);m.uc.mem_write(REPLY,bytes(packet));m.uc.mem_write(HEADER,bytes(48))
        ss=saved(m)
        ev=[m.phase('original sender prologue before OSAL allocation',0x27e0cc,sp=SP,x30=pp.STOP,x0=HEADER,x1=REPLY)]
        assert ev[-1]['reason']=='boundary: before_original_OSAL_allocation'
        sync=prev.prev.readq(m,0x2f9b50);assert sync==0x3b4e00
        ev.append(m.phase('independent post-send frame; original wait call sets transport boolean candidate',0x27e20c,
            x19=sync,x20=sync+8,x21=0x2f9000))
        assert ev[-1]['reason']=='boundary: before_original_cond_wait' and m.uc.reg_read(reg('w19'))==1
        ev.append(m.phase('independent declared condition-wait result, no claim of actual wake or matched reply',0x27e21c,x0=wait_status))
        if wait_status:
            assert ev[-1]['reason']=='boundary: before_original_Codec_logger' and m.uc.reg_read(reg('w19'))==0
            ev.append(m.phase('independent post-error-log sender frame before mutex unlock',0x27e1f0))
        assert ev[-1]['reason']=='boundary: before_original_sender_mutex_unlock'
        ev.append(m.phase('independent post-mutex-unlock original sender epilogue',0x27e1fc))
        transport=m.uc.reg_read(reg('w0'));assert ev[-1]['reason']=='returned' and transport==int(wait_status==0) and restored(m,ss)
        assert bytes(m.uc.mem_read(REPLY,48))==bytes(packet)
        ss=saved(m)
        ev.append(m.phase('original Codec EncStart prologue before logger',0x27fd64,sp=SP,x30=pp.STOP,
            x0=PARAM,x1=0x20,x2=15,x3=1,x4=0,x5=REPLY))
        assert ev[-1]['reason']=='boundary: before_original_Codec_logger'
        ev.append(m.phase('independent post-send EncStart frame consumes original post-wait transport boolean',0x27fed8,x0=transport))
        assert ev[-1]['reason']=='boundary: before_original_Codec_normalLock_unlock'
        ev.append(m.phase('independent post-normalLock-unlock original Codec return-code diagnostic',0x27fe30))
        assert ev[-1]['reason']=='boundary: before_original_Codec_logger'
        ev.append(m.phase('independent post-log original Codec EncStart epilogue',0x27fe64))
        status=m.uc.reg_read(reg('w0'));assert ev[-1]['reason']=='returned' and status==(0 if transport else 2) and restored(m,ss)
        assert bytes(m.uc.mem_read(REPLY,48))==bytes(packet)
        return {'seed':seed,'declared_reply_status14':reply_status,'declared_wait_return':wait_status,
            'native_post_wait_sender_bool':transport,'native_Codec_post_send_status':status,'synthetic_reply48':bytes(packet).hex(),
            'events':ev,'all_send_wait_unlock_logging_and_reply_arrival_are_unexecuted_gaps':True,
            'not_a_complete_Send_or_EncStart_or_hardware_failure_success_demonstration':True,
            'wrapper_return_alone_does_not_establish_reply_or_encoder_success':True}
    finally:m.close()

def classify(seed,kind):
    m=Guest(seed)
    try:
        start,a,b,expected={'Start_expect':(0x27df44,0x210,1,0x1003),
            'synthetic_comp_sub3':(0x27f494,0x4e0,3,0x1003),'synthetic_sub2':(0x27f494,0x4e0,2,1)}[kind]
        e=m.phase('original pure event classification '+kind,start,abi=True,sp=SP,x30=pp.STOP,x0=a,x1=b)
        assert e['return_u32_if_returned']==expected
        return {'seed':seed,'kind':kind,'input':[a,b],'native_factor':expected,'events':[e],
            'actual_Start_reply_producer_or_current_expected_event_unproven':True}
    finally:m.close()

def run(out):
    im.volume();assert sha(PRIOR.read_bytes())==PRIOR_SHA
    for x in json.loads(PRIOR.read_text())['files']:
        p=ROOT/x['path'];assert p.stat().st_size==x['bytes'] and sha(p.read_bytes())==x['sha256']
    assert (BASE/'GOAL_STATUS.json').read_bytes()==(STAGE/'goal-status-before.json').read_bytes()
    out.mkdir();(out/'executed-source.py').write_bytes(Path(__file__).read_bytes())
    j={'status':'RUNNING','created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'source_sha256':sha(Path(__file__).read_bytes()),'producer_cases':[],'return_cases':[],'classifier_cases':[],
        'goal_complete':False,'persistent_write_release':False,'camera_Windows_UU_operations':False,
        'actual_Start_hardware_profile_file_backup_or_recovery_proven':False}
    try:
        for seed in (0xa5,0xc3):
            j['producer_cases'].append(producer(seed,'single_audio',1,1,7,(1,1)))
            j['producer_cases'].append(producer(seed,'other_audio_and_sequence_byte',2,3,255,(0,0)))
            for rs in (0,2):
                for ws in (0,5):j['return_cases'].append(return_layers(seed,rs,ws))
            for k in ('Start_expect','synthetic_comp_sub3','synthetic_sub2'):j['classifier_cases'].append(classify(seed,k))
        j['bounded_phases']=sum(len(c['events']) for k in ('producer_cases','return_cases','classifier_cases') for c in j[k])
        j['status']='PASS_NATIVE_START_CALLER_RETURN_LAYERS_NOT_HARDWARE_COMPLETION'
        (out/'start-caller-results.json').write_text(json.dumps(j,ensure_ascii=False,indent=2)+'\n')
        print(json.dumps({'producer_cases':len(j['producer_cases']),'return_cases':len(j['return_cases']),
            'classifier_cases':len(j['classifier_cases']),'bounded_phases':j['bounded_phases'],'status':j['status']}))
    except Exception:
        j['status']='FAILED_NO_PASSING_RESULT';j['error']=traceback.format_exc()
        (out/'attempt-failure.json').write_text(json.dumps(j,ensure_ascii=False,indent=2)+'\n');raise
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);run(p.parse_args().out)
