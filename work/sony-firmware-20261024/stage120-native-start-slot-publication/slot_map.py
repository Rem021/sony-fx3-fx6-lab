#!/usr/bin/env python3
"""Original GetSlotID lookup/registration side effect, guest map only."""
from pathlib import Path
import argparse,datetime,hashlib,json,struct,sys,traceback
STAGE=Path(__file__).resolve().parent;sys.path.insert(0,str(STAGE));import slot_publication as t
MAP=t.S+0x7000
def sha(b):return hashlib.sha256(b).hexdigest()
def run(out):
    t.im.volume();assert (t.BASE/'GOAL_STATUS.json').read_bytes()==(STAGE/'goal-status-before.json').read_bytes()
    source=STAGE/'run-native-slot-publication-20261027/slot-publication-results.json';sj=json.loads(source.read_text())
    assert sj['status']=='PASS_NATIVE_SLOT_STATUS_PUBLICATION_PRECEDES_THIS_RECSTART_QUEUE_NOT_ENCODER_COMPLETION'
    out.mkdir();(out/'executed-source.py').write_bytes(Path(__file__).read_bytes())
    j={'status':'RUNNING','created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'source_sha256':sha(Path(__file__).read_bytes()),'publication_result_sha256':sha(source.read_bytes()),
        'cases':[],'camera_Windows_UU_operations':False,'actual_media_slot_identity_proven':False}
    try:
        for seed in (0xa5,0xc3):
            m=t.Guest(seed);m.allowed.append((0x9a95c,0x9a9c0))
            try:
                raw=bytearray((seed+i*13)&255 for i in range(0x200));ids=[0x10,0x20,0xffffffff,0xffffffff]
                for i,v in enumerate(ids):struct.pack_into('<I',raw,i*0x80+0x7c,v)
                m.uc.mem_write(MAP,bytes(raw))
                for label,mediaid,slot,write in (('existing',0x20,1,False),('first_registration',0x30,2,True),
                    ('repeat_lookup',0x30,2,False),('last_free_registration',0x40,3,True),('full_no_match',0x50,0xffffffff,False)):
                    before=bytes(m.uc.mem_read(MAP,0x200));expected=bytearray(before)
                    outputs=[]
                    if write:
                        a=MAP+slot*0x80+0x7c;outputs=[(a,a+4)];struct.pack_into('<I',expected,slot*0x80+0x7c,mediaid)
                    e=m.phase('original GetSlotID '+label+' on declared converter records',0x9a95c,outputs=outputs,abi=True,
                        sp=t.SP,x30=t.pp.STOP,x0=MAP,x1=mediaid)
                    assert e['reason']=='returned' and m.uc.reg_read(t.reg('w0'))==slot
                    after=bytes(m.uc.mem_read(MAP,0x200));assert after==bytes(expected)
                    j['cases'].append({'seed':seed,'label':label,'declared_mediaid':mediaid,'native_slot_u32':slot,
                        'native_registration_write':write,'before_sha256':sha(before),'after_sha256':sha(after),
                        'map_bytes_outside_ID_field_unchanged':True,'events':[e],
                        'Get_name_does_not_establish_read_only_semantics':True,'actual_media_table_or_card_identity_proven':False})
            finally:m.close()
        j['bounded_phases']=sum(len(c['events']) for c in j['cases'])
        j['status']='PASS_NATIVE_GETSLOTID_CAN_REGISTER_MAPPING_NOT_READ_ONLY'
        (out/'slot-map-results.json').write_text(json.dumps(j,ensure_ascii=False,indent=2)+'\n')
        print(json.dumps({'cases':len(j['cases']),'bounded_phases':j['bounded_phases'],'status':j['status']}))
    except Exception:
        j['status']='FAILED_NO_PASSING_RESULT';j['error']=traceback.format_exc()
        (out/'attempt-failure.json').write_text(json.dumps(j,ensure_ascii=False,indent=2)+'\n');raise
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);run(p.parse_args().out)
