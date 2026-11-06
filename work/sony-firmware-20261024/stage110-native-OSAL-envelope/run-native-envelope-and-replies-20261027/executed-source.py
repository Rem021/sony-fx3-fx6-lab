#!/usr/bin/env python3
"""Original receive framing/metadata and reply matching, with transport stops.

An independent post-receive input contains an explicit envelope, pointer and
error input. No receive, free, mutex, condition or kernel return is fabricated.
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
sys.path.insert(0,str(BASE/'stage108-original-Dataflow-copy'))
import dataflow_copy as prev
sys.path.insert(0,str(BASE/'stage109-native-ParameterControl'))
import parameter_control as maps
pp,r,im=prev.pp,prev.r,prev.im
DF,MPR=prev.DF,prev.MPR
SP=prev.SP
OSAL_SHA='09ebf5980237fc473077dc844763dcb00cba423f431646e3be7c0ca49ea70ff3'
OSAL=prev.assets.PinnedNative(STAGE/'inputs/libosal_uipc.so',OSAL_SHA)
OBASE=0x40000000
ENVELOPE=pp.SCRATCH+0x3000
MESSAGE=ENVELOPE+0x18
OBJ=prev.OBJ
CMD=prev.CMD
REPLY=pp.SCRATCH+0x4000
SOURCE=0x80c70047
QUEUE=0x8055001f
PRIOR=maps.STAGE/'final-receipt.json'
PRIOR_SHA='2f37447990c96a2cbf001d723a13d727e3cfb3aaaa2d7305b111a57c70d93846'


def sha(data):return hashlib.sha256(data).hexdigest()


def reg(name):return prev.reg(name)


class ReceiveGuest(prev.Guest):
    def __init__(self,seed):
        super().__init__(DF,seed,[(0x31f58,0x31f7c),(0x31ff4,0x32194),
            (0x3128c,0x31318),(0x31358,0x31368),(0x33920,0x33bec)])
        maps.map_image(self,OSAL,OBASE)
        self.images.extend((OBASE+s['p_vaddr'],bytes(self.uc.mem_read(OBASE+s['p_vaddr'],s['p_memsz']))) for s in OSAL.segments)
        for name in ('osal_set_msg_src','osal_get_msg_src','osal_msg_size'):
            s=OSAL.symbols[name];self.allowed.append((OBASE+s['va'],OBASE+s['va']+s['size']))
        self.boundaries.update({0x30850:'before_unexecuted_OSAL_receive',0x30e80:'before_unexecuted_OSAL_message_free'})

    def code(self,u,pc,n,user):
        if pc in (0x30880,0x30630):
            name=DF.plt[pc];assert name in ('osal_get_msg_src','osal_msg_size')
            target=OBASE+OSAL.symbols[name]['va']
            self.pcs.append(hex(pc));self.steps+=1
            self.calls.append({'original_user_OSAL_binding':name,'PLT':hex(pc),'target':hex(target),
                'pointer_x0':hex(u.reg_read(reg('x0'))),'declared_PC_binding_not_live_loader_proof':True})
            u.reg_write(reg('pc'),target);return
        return super().code(u,pc,n,user)


def receive(seed,header,label,length=48,source=SOURCE,marker=False,get=True):
    m=ReceiveGuest(seed)
    try:
        data=bytearray(header+bytes([seed^0x5a])*max(0,length-48))
        if marker:struct.pack_into('<I',data,4,0xa0a0a0a0)
        data=bytes(data[:length]);assert len(data)==length
        m.uc.mem_write(ENVELOPE,bytes([seed])*0x18+data)
        m.uc.mem_write(MESSAGE-8,struct.pack('<I',length))
        events=[m.phase('original Dataflow message constructor',0x31f58,outputs=[(OBJ,OBJ+0x198)],
            sp=SP,x30=pp.STOP,x0=OBJ)]
        events.append(m.phase('original user OSAL source setter on declared envelope',OBASE+OSAL.symbols['osal_set_msg_src']['va'],
            outputs=[(MESSAGE-12,MESSAGE-8)],sp=SP,x30=pp.STOP,x0=MESSAGE,x1=source))
        envelope_before=bytes(m.uc.mem_read(ENVELOPE,0x18+length))
        events.append(m.phase('original ReceiveASync prologue to transport boundary',0x33964,
            complete=False,sp=SP,x30=pp.STOP,x0=pp.SCRATCH+0x1000,x1=QUEUE,x2=OBJ,x3=0xffffffff))
        assert events[-1]['reason']=='boundary: before_unexecuted_OSAL_receive'
        fp=m.uc.reg_read(reg('x29'));assert fp==SP-0x60
        # New independent phase input, not a write presented as receive output.
        m.uc.mem_write(fp+0x50,struct.pack('<Q',MESSAGE))
        events.append(m.phase('independent post-receive envelope/error input; original translator, metadata, copy and classification',0x3399c,
            outputs=[(OBJ,OBJ+0x198)],complete=False,x0=0))
        assert events[-1]['reason']=='boundary: before_unexecuted_OSAL_message_free'
        assert (m.uc.reg_read(reg('x0')),m.uc.reg_read(reg('x1')))==(QUEUE,MESSAGE)
        obj=bytes(m.uc.mem_read(OBJ,0x198));state=struct.unpack_from('<I',obj,8)[0]
        copied=min(length,384);stored=struct.unpack_from('<H',obj,12)[0]
        assert state==(1 if marker and source==0x00550001 else 2)
        if state==2:assert stored==copied
        assert obj[0x18:0x18+copied]==data[:copied]
        assert struct.unpack_from('<I',obj,0x10)[0]==source
        get_result=None
        if get:
            assert state==2 and length<=48
            events.append(m.phase('independent original GetMsg on native ReceiveASync-produced object before any real free',0x32070,
                outputs=[(OBJ,OBJ+0x198),(CMD+8,CMD+8+length)],sp=SP,x30=pp.STOP,x0=OBJ,x1=CMD+8,x2=48))
            assert events[-1]['return_u32_if_returned']==0
            received=bytes(m.uc.mem_read(CMD,0x38));assert received[8:8+length]==data
            assert received[8+length:]==bytes([seed^0x3c])*(48-length)
            assert bytes(m.uc.mem_read(OBJ+8,4))==bytes(4)
            assert bytes(m.uc.mem_read(OBJ+12,2))==bytes(2)
            assert bytes(m.uc.mem_read(OBJ+0x10,4))==bytes(4)
            assert bytes(m.uc.mem_read(OBJ+0x18,copied))==bytes(copied)
            get_result={'received38_hex':received.hex(),'copied_len':length,'native_return':0,
                'all48_bytes_present':length==48,'native_object_state_length_source_and_stored_inline_bytes_cleared':True}
        assert bytes(m.uc.mem_read(ENVELOPE,0x18+length))==envelope_before
        assert not any('_SetGlobalMsg' in str(c) for e in events for c in e['original_calls_and_returns'])
        return {'seed':seed,'label':label,'declared_OSAL_payload_length':length,'declared_source_ID':hex(source),
            'declared_queue_ID':hex(QUEUE),'declared_marker_control':marker,'native_message_state':state,
            'native_stored_length_u16_when_raw':stored if state==2 else None,'native_copy_length':copied,
            'inline_copied_hex':obj[0x18:0x18+copied].hex(),'GetMsg':get_result,'events':events,
            'envelope_unchanged_by_receive_metadata_and_copy':True,
            'GetMsg_is_independent_from_unexecuted_OSAL_free_and_unwind':True,
            'actual_transport_envelope_allocation_free_full_ReceiveASync_or_MAIN_proven':False}
    finally:m.close()


class ReplyGuest(prev.Guest):
    def __init__(self,seed):
        super().__init__(MPR,seed,[(0x27df44,0x27e0cc),(0x27e168,0x27e20c),
            (0x27f494,0x27fa34),(0x27de88,0x27deac),(0x28593c,0x285acc)])
        self.boundaries={0x7c5f0:'before_unexecuted_reply_mutex_lock',0x83370:'before_unexecuted_reply_OSAL_free',
            0x80460:'before_unexecuted_expected_event_store',0x81d30:'before_unexecuted_condition_signal'}

    def declare_expected(self,factor):
        a=struct.unpack('<Q',bytes(self.uc.mem_read(0x2faf38,8)))[0]
        b=struct.unpack('<Q',bytes(self.uc.mem_read(0x2f9fe8,8)))[0]
        assert a and b and a!=b
        self.uc.mem_write(a,struct.pack('<I',factor));self.uc.mem_write(b,struct.pack('<Q',REPLY))
        self.images=[(addr,bytes(self.uc.mem_read(addr,len(old)))) for addr,old in self.images]
        return {'factor_slot':hex(a),'payload_pointer_slot':hex(b),'factor':factor,'payload_pointer':hex(REPLY),
            'explicit_global_input_not_actual_SetExpectedCodecEvent_execution':True}


def expectation(seed,header,provided):
    m=ReplyGuest(seed)
    try:
        m.uc.mem_write(MESSAGE,header);fp=SP-0x80
        event=m.phase('independent original sender expectation branch '+('provided reply pointer' if provided else 'null caller reply pointer'),0x27e168,
            complete=False,sp=fp,x29=fp,x30=pp.STOP,x19=MESSAGE,x20=REPLY if provided else 0)
        assert event['reason']=='boundary: before_unexecuted_expected_event_store'
        factor=m.uc.reg_read(reg('w0'));out=m.uc.reg_read(reg('x1'))
        assert factor==(0x1001 if provided else 1) and out==(REPLY if provided else fp+0x50)
        return {'seed':seed,'declared_caller_reply_pointer_provided':provided,'native_expected_factor':factor,
            'native_reply_storage_pointer':hex(out),'events':[event],
            'actual_expectation_store_send_wait_or_current_call_mode_proven':False}
    finally:m.close()


def reply(seed,header,label,expected,subcode,msgid=0x4e0):
    m=ReplyGuest(seed)
    try:
        declared=m.declare_expected(expected)
        packet=bytearray(header);struct.pack_into('<H',packet,2,subcode);struct.pack_into('<I',packet,0x24,msgid)
        packet=bytes(packet);m.uc.mem_write(MESSAGE,packet)
        events=[m.phase('original callback classification and expected-event comparison '+label,0x28593c,
            complete=False,sp=SP,x30=pp.STOP,x0=MESSAGE,x1=0)]
        converted=2 if msgid!=0x4e0 else (0x1001 if subcode==1 else 1)
        matched=expected==converted and expected!=2
        if converted==2:
            route='ignore_unrecognized_then_free'
            assert events[-1]['reason']=='boundary: before_unexecuted_reply_OSAL_free'
        else:
            assert events[-1]['reason']=='boundary: before_unexecuted_reply_mutex_lock'
            route='expected_reply_copy' if matched else 'async_event_queue'
            lr=m.uc.reg_read(reg('x30'));assert lr==(0x285998 if matched else 0x285a68)
            if matched:
                events.append(m.phase('independent post-lock native48-byte reply copy to declared expected storage',0x285998,
                    outputs=[(REPLY,REPLY+48)],complete=False))
                assert events[-1]['reason']=='boundary: before_unexecuted_expected_event_store'
                assert bytes(m.uc.mem_read(REPLY,48))==packet
                assert (m.uc.reg_read(reg('w0')),m.uc.reg_read(reg('x1')))==(2,0)
        assert bytes(m.uc.mem_read(MESSAGE,48))==packet
        return {'seed':seed,'label':label,'declared_expected':declared,'declared_reply_ID':hex(msgid),
            'declared_reply_subcode':subcode,'native_route':route,'original_converted_factor':converted,
            'copied_reply48_hex':bytes(m.uc.mem_read(REPLY,48)).hex() if matched else None,
            'declared_packet48_hex':packet.hex(),'events':events,
            'actual_reply_generation_transport_mutex_state_clear_signal_or_payload_release_proven':False}
    finally:m.close()


def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    im.volume();assert sha(PRIOR.read_bytes())==PRIOR_SHA
    for f in json.loads(PRIOR.read_text())['files']:
        raw=(ROOT/f['path']).read_bytes();assert len(raw)==f['bytes'] and sha(raw)==f['sha256']
    assert (BASE/'GOAL_STATUS.json').read_bytes()==(STAGE/'goal-status-before.json').read_bytes()
    a.out.mkdir(exist_ok=False);(a.out/'executed-source.py').write_bytes(Path(__file__).read_bytes())
    try:
        source=prev.STAGE/'run-native-payload-and-header-20261027/dataflow-results.json'
        origin=json.loads((maps.STAGE/'run-original-table-and-storage-20261027/parameter-control-results.json').read_text())
        assert sha(source.read_bytes())==origin['source_sha256']
        old=json.loads(source.read_text());rc=[];expect=[];replies=[]
        for seed in (0xa5,0xc3):
            rows=[c for c in old['messages'] if c['seed']==seed and c['header_complete']]
            for c in rows:rc.append(receive(seed,bytes.fromhex(c['original_header30_hex']),'original_header48'))
            header=bytes.fromhex(rows[0]['original_header30_hex'])
            rc.extend([receive(seed,header,'short_declared_envelope16',length=16),
                receive(seed,header,'declared400_capped384',length=400,get=False),
                receive(seed,header,'synthetic_marker_nonpublic_state1',source=0x00550001,marker=True,get=False),
                receive(seed,header,'synthetic_marker_recognized_source_raw2',source=0x00c00695,marker=True,get=False)])
            expect.extend(expectation(seed,header,provided) for provided in (False,True))
            replies.extend(reply(seed,header,*args) for args in [
                ('matching_specific',0x1001,1),('matching_generic',1,2),('mismatched',0x1003,1),
                ('reserved_expected2',2,1),('unknown_reply',0x1001,1,0xdeadbeef)])
        phases=sum(len(c['events']) for c in rc+expect+replies)
        result={'status':'PASS_NATIVE_USER_OSAL_METADATA_RECEIVE_CLASSIFICATION_AND_REPLY_MATCH_SCOPE',
            'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'original_user_OSAL_sha256':OSAL_SHA,'source':str(source.relative_to(ROOT)),'source_sha256':sha(source.read_bytes()),
            'receive_cases':rc,'sender_expectation_cases':expect,'reply_cases':replies,'bounded_phases':phases,
            'actual_receive_free_mutex_condition_or_success_return_adapters_executed':False,
            'Windows_UU_camera_operations':False,'goal_complete':False,'persistent_write_release':False}
        (a.out/'osal-envelope-results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
        print(json.dumps({'status':result['status'],'receive_cases':len(rc),'sender_expectations':len(expect),'reply_cases':len(replies),'bounded_phases':phases}))
    except BaseException:
        (a.out/'attempt-failure.json').write_text(json.dumps({'passing_result':False,'traceback':traceback.format_exc()},indent=2)+'\n');raise


if __name__=='__main__':main()
