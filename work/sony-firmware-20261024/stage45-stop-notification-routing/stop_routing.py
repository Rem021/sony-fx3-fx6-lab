#!/usr/bin/env python3
"""Original STOP_COMP receiver/bridges/upper output-state queue, guest only.

Native constructor prefixes create selected vptrs; real factory instance and
initialization are fixtures. Receiver mandatory logs remain unexecuted and its
post-log fragment is explicitly separate. No fake runtime output or return.
"""
from pathlib import Path
import argparse
import datetime
import json
import struct
import sys
import traceback

ROOT=Path(__file__).resolve().parents[3]
BASE=ROOT/'work/sony-firmware-20261024'
STAGE=Path(__file__).resolve().parent
sys.path.insert(0,str(BASE/'stage44-stop-unmap-and-completion'))
import stop_completion as c
b,a,t,p,w,r,V=c.b,c.a,c.t,c.p,c.w,c.r,c.V
CTX=r.ARENA+0x20000
OWNER=r.ARENA+0x200000
COMP=OWNER+0x10
CODEC_CALLBACK=OWNER+0x6a20
OUTPUT_CALLBACK=CTX+0x107030
HOLDER=r.ARENA+0x250000
STATE=r.ARENA+0x260000
MESSAGE=r.ARENA+0x3f0000
RANGES=[(0x1344f8,0x134518),(0x134918,0x134938),(0x13497c,0x134998),
 (0x14f784,0x14f7b4),(0x14fc7c,0x14fc8c),(0x14ff4c,0x1501f0),
 (0x1386f4,0x138b00),(0x15391c,0x153b6c),(0x155bd0,0x155f60),
 (0x156390,0x156434),(0x1568b0,0x156b00),(0x15b28c,0x15b6ac),
 (0x24c994,0x24c9b4),(0x2547ec,0x2547f4),(0x25484c,0x254854)]


class Guest(c.Guest):
    def __init__(self,blob,code,ro):
        super().__init__(blob,code,ro)
        self.ranges.extend((V+lo,V+hi) for lo,hi in RANGES)
        for state in (13,14,15,19):
            target=struct.unpack_from('<Q',blob,0x364138+state*24+16)[0]
            self.ranges.append((target,target+8))
        self.boundaries.update({V+0x134518:'after_original_codec_callback_stores',
          V+0x134998:'after_original_component_callback_binding',
          V+0x14f7b4:'after_original_output_callback_stores'})


def snapshot(m):
    return {'state':int.from_bytes(m.read(STATE+8,4),'little'),
      'active':m.read(STATE+0xc,1)[0],'STOP_pending':m.read(STATE+0xb74,1)[0],
      'queue_count':int.from_bytes(m.read(STATE+0xd08,4),'little'),
      'queue_write':int.from_bytes(m.read(STATE+0xd0c,4),'little'),
      'queue_read':int.from_bytes(m.read(STATE+0xd10,4),'little'),
      'queue_slot0':hex(int.from_bytes(m.read(STATE+0xd18,8),'little')),
      'STOP_vptr':hex(int.from_bytes(m.read(STATE+0xb68,8),'little'))}


def setup(blob,code,ro,state,busy):
    m=Guest(blob,code,ro);events=[]
    ctor=t.original(m,'original output-state constructor prefix',0x155bd0,x0=STATE)
    assert ctor['reason']=='boundary: before_unbound_runtime_clear'
    assert ctor['x0_to_x5'][:3]==[hex(STATE+0xd18),'0x0','0x58']
    assert int.from_bytes(m.read(STATE+0xb68,8),'little')==V+0x35f408
    assert int.from_bytes(m.read(STATE+0xb70,4),'little')==18
    assert int.from_bytes(m.read(STATE+8,4),'little')==42
    events.append(ctor)
    # Explicit post-initialization owner/state/holder fixtures. Real factory
    # instances, both constructor clears, OS locks and current epoch unbound.
    m.uc.mem_write(STATE,r.p64(CTX));w.put32(m,STATE+8,state)
    m.uc.mem_write(STATE+0xc,bytes([busy]));m.uc.mem_write(HOLDER,r.p64(STATE))
    output=t.original(m,'independent original output callback constructor stores',0x14f784,x22=CTX,x0=HOLDER)
    assert output['reason']=='boundary: after_original_output_callback_stores'
    assert int.from_bytes(m.read(OUTPUT_CALLBACK,8),'little')==V+0x35edb0
    events.append(output)
    getter=t.original(m,'original output callback getter',0x14fc7c,x0=CTX)
    assert getter['reason']=='returned' and getter['x0_to_x5'][0]==hex(OUTPUT_CALLBACK)
    events.append(getter)
    codec=t.original(m,'independent original codec callback constructor stores',0x1344f8,
      x20=OWNER,x0=int(getter['x0_to_x5'][0],16))
    assert codec['reason']=='boundary: after_original_codec_callback_stores'
    assert int.from_bytes(m.read(CODEC_CALLBACK,8),'little')==V+0x35bb68
    assert int.from_bytes(m.read(OWNER+0x6a18,8),'little')==OUTPUT_CALLBACK
    events.append(codec)
    component=t.original(m,'independent original component callback binding',0x13497c,x20=COMP,x21=OWNER)
    assert component['reason']=='boundary: after_original_component_callback_binding'
    assert int.from_bytes(m.read(COMP+0xd8,8),'little')==CODEC_CALLBACK
    events.append(component)
    return m,events


def routed_case(blob,code,ro,state,busy):
    m,events=setup(blob,code,ro,state,busy)
    packet=struct.pack('<HHII',0x2103,0x113,12,7);m.uc.mem_write(MESSAGE,packet)
    prefix=t.original(m,'original STOP_COMP receiver prefix state'+str(state),0x1386f4,x0=COMP,x1=MESSAGE)
    assert prefix['reason']=='boundary: before_unexecuted_diagnostic_acquire'
    assert hex(V+0x1388a0) in prefix['pcs']
    assert snapshot(m)['queue_count']==0
    events.append(prefix)
    # Independent continuation with captured input/frame, not an execution of
    # the mandatory logger or a claim that its effects/return were reproduced.
    regs={f'x{i}':m.uc.reg_read(getattr(r.reg,'UC_ARM64_REG_X'+str(i))) for i in range(19,22)}
    regs['sp']=m.uc.reg_read(r.reg.UC_ARM64_REG_SP)
    prefix['captured_inputs_for_separate_post_log_fragment']={k:hex(v) for k,v in regs.items()}
    if busy:m.boundaries[V+0x153928]='before_upper_wrapper_boolean_conversion'
    continuation=t.original(m,'separate original post-log STOP_COMP routing',0x1388dc,**regs)
    events.append(continuation)
    for pc in (0x134924,0x14ff4c,0x14ff54,0x1500a4,0x15391c,0x153938):
        assert hex(V+pc) in continuation['pcs'],hex(pc)
    after=snapshot(m)
    if busy:
        assert continuation['reason']=='boundary: before_upper_wrapper_boolean_conversion'
        assert continuation['x0_to_x5'][0]=='0x1'
        assert after['state']==state and after['active']==1 and after['queue_count']==1 and after['STOP_pending']==1
        assert after['queue_slot0']==hex(STATE+0xb68)
        del m.boundaries[V+0x153928]
        finished=b.current_run(m,'resume exact native wrapper conversion and receiver return')
        # The shared CPU-continuation helper snapshots the earlier imola SM;
        # this stage reports its own distinct sfmc_enc output-state object.
        finished['state_after']=snapshot(m)
        events.append(finished)
        assert finished['reason']=='returned'
        assert finished['cpu_after']['x0_to_x5'][0]=='0x0'
        assert int(finished['cpu_after']['sp'],16)==r.SP
        assert snapshot(m)==after
    else:
        assert continuation['reason']=='boundary: before_unexecuted_diagnostic_acquire'
        assert hex(V+0x156ad4) in continuation['pcs']
        assert hex(V+0x156390) not in continuation['pcs']
        assert after['state']==state and after['active']==1 and after['queue_count']==0
    return {'input_state':state,'busy_fixture':bool(busy),'original_fragments':events,
      'state_after':snapshot(m),'receiver_message_hex':packet.hex(),
      'original_vptrs_written_by_native_constructor_fragments_not_host_set':True,
      'internal_queue_result1_then_original_wrapper_result0':bool(busy),
      'scope':'Original receiver prefix, then separate post-log routing on captured frame into constructor-written original callbacks and declared output-state/holder fixtures. Real factory, full construction, logs, actual queue/owner selection, epoch, concurrency and hardware unbound.',
      'complete_STOP_or_recording_chain_idle_or_safe_restore_verified':False}


def state_name(blob,state):
    return r.im.cstring(blob,struct.unpack_from('<Q',blob,0xbdb7a0+state*8)[0]-V)


def selector_cases(blob,code,ro):
    cases=[]
    for kind,table in (('codec_stop_comp_v',0x363d48),('codec_stop_comp_a',0x364138)):
        for state in (13,14,15,19):
            row=struct.unpack_from('<3Q',blob,table+state*24)
            m=Guest(blob,code,ro);event=t.original(m,kind+' original next selector state'+str(state),row[2]-V)
            assert event['reason']=='returned';dest=int(event['x0_to_x5'][0],16)
            expected={('codec_stop_comp_v',13):15,('codec_stop_comp_v',14):19,
              ('codec_stop_comp_a',13):14,('codec_stop_comp_a',15):19}.get((kind,state),43)
            assert dest==expected
            cases.append({'kind':kind,'from_state':state,'from_name':state_name(blob,state),
              'destination_state':dest,'destination_name':state_name(blob,dest),
              'guard':hex(row[0]-V),'action':hex(row[1]-V),'selector':hex(row[2]-V),
              'original_fragments':[event],'only_selector_not_completed_transition':True})
    return cases


def other_STOP_COMP_origin(blob,code,ro):
    rows=[];events=[]
    assert r.im.cstring(blob,struct.unpack_from('<Q',blob,0xbdde38+5*8)[0]-V)=='resource_video_enc_stop_param_t'
    for state,action,selector in ((6,0x2547e4,0x2547ec),(10,0x254844,0x25484c)):
        row=struct.unpack_from('<3Q',blob,0x37f868+state*24)
        assert row[1]==V+action and row[2]==V+selector
        assert r.im.dump(blob,action,action+8,V)[1]['asm']=='b #'+hex(V+0x24c94c)
        m=Guest(blob,code,ro);event=t.original(m,'original lower STOP-command selector state'+str(state),selector)
        assert event['reason']=='returned' and event['x0_to_x5'][0]=='0x4'
        events.append(event);rows.append({'input_state':state,'action':'0x24c94c','selector_destination_only':4})
    m=Guest(blob,code,ro);m.uc.mem_write(c.OUTER,r.p64(c.CHANNEL));w.put32(m,c.CHANNEL,7)
    built=t.original(m,'independent original STOP-command completion packet',0x24c994,x19=c.OUTER)
    events.append(built);assert built['reason']=='boundary: before_unexecuted_diagnostic_acquire'
    packet=m.read(r.SP+0x10,12)
    old=json.loads((c.STAGE/'run-20261025/stop-completion-results.json').read_text())
    assert packet.hex()==old['independent_completion_packet']['packet_hex']
    return {'event':'resource_video_enc_stop_param_t','event_table':'0x37f868',
      'rows':rows,'original_fragments':events,'packet_hex':packet.hex(),
      'packet_identical_to_enc_stop_done_action_for_same_channel':True,
      'scope':'Original lower STOP-command table/selector and a separate post-log packet construction. Real command, full transition/action, hardware completion and actual send unexecuted.',
      'packet_alone_does_not_prove_a_fresh_enc_stop_done_event':True}


def metadata(blob):
    result=[]
    for group in (0x35bb58,0x35eda0,0x35f3f8):
        ti=struct.unpack_from('<Q',blob,group+8)[0]-V;name=struct.unpack_from('<Q',blob,ti+8)[0]-V
        result.append({'vtable_header_offset':hex(group),'address_point':hex(V+group+16),
          'typeinfo_offset':hex(ti),'type_name':r.im.cstring(blob,name)})
    assert 'codec_stop_comp_v' in result[2]['type_name']
    assert struct.unpack_from('<Q',blob,0x35c2a0+(0x113-0x10e)*8)[0]==V+0x1388a0
    assert struct.unpack_from('<Q',blob,0x35ec78+(0x1c-10)*8)[0]==V+0x1500a4
    return result


def run(out):
    prior=c.STAGE/'final-receipt.json';raw=prior.read_bytes()
    assert r.im.sha(raw)=='f781c38ed0abb4b5bf2eeb36e909d0e787e1f30486e0864c768bc3c293597e64'
    for e in json.loads(raw)['files']:assert r.im.sha((ROOT/e['path']).read_bytes())==e['sha256']
    image=BASE/'stage2/extraction/files/nflasha3/av-cam.bin';blob=image.read_bytes()
    assert r.im.sha(blob)==r.im.PINS['stage2/extraction/files/nflasha3/av-cam.bin']
    code,ro,_=p.object_image((p.STAGE/'scoped_writer.a64.o').read_bytes())
    parts={'routed_cases':[routed_case(blob,code,ro,13,1),routed_case(blob,code,ro,13,0),routed_case(blob,code,ro,14,0)],
      'original_completion_selectors':selector_cases(blob,code,ro),
      'other_STOP_COMP_origin':other_STOP_COMP_origin(blob,code,ro)}
    def fragments(item):
        if isinstance(item,dict):
            for k,v in item.items():
                if k=='original_fragments':yield from v
                else:yield from fragments(v)
        elif isinstance(item,list):
            for v in item:yield from fragments(v)
    traces=list(fragments(parts))
    regions=[('STOP_COMP receiver',0x1386f4,0x138760),('receiver post-log dispatch',0x1388dc,0x1388f0),
      ('codec callback constructor stores',0x1344f8,0x134518),('codec component callback binding',0x13497c,0x134998),
      ('codec callback thunk',0x134924,0x134938),('output callback constructor stores',0x14f784,0x14f7b4),
      ('output callback event dispatch',0x14ff4c,0x14ff78),('event1c branch',0x1500a4,0x1500bc),
      ('upper STOP event processor',0x15391c,0x153b6c),('upper constructor prefix',0x155bd0,0x155f60),
      ('other STOP-command packet producer',0x24c94c,0x24c9b4),('lower STOP table binding',0x251710,0x251750)]
    proof={'status':'PASS_ORIGINAL_STOP_COMP_ROUTING_AND_OUTPUT_QUEUE_WITHIN_DECLARED_OFFLINE_SCOPE',
      'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),**parts,'metadata':metadata(blob),
      'source_regions':[{'name':name,'instructions':r.im.dump(blob,lo,hi,V)} for name,lo,hi in regions],
      'original_fragments':len(traces),'original_guest_store_count':sum(len(e['writes']) for e in traces),
      'unique_observed_PC_count':len({pc for e in traces for pc in e['pcs']}),
      'native_output_log_lock_or_HAL_adapters':False,'compiled_prototype_invoked':False,
      'full_STOP_action_transition_runtime_owner_epoch_Hal_or_recovery_verified':False,
      'camera_or_remote_access_attempted':False,'goal_complete':False,'persistent_write_release':False}
    summary={k:proof[k] for k in ('status','original_fragments','original_guest_store_count','unique_observed_PC_count',
      'full_STOP_action_transition_runtime_owner_epoch_Hal_or_recovery_verified','goal_complete','persistent_write_release')}
    summary.update(MID113_to_event1c_to_codec_stop_comp_v_original_callbacks=True,
      busy_event_queued_before_wrapper0_receiver_return=True,
      video_completion_can_leave_non_STOPPED_table_state=True,
      audio_and_video_completion_order_has_distinct_intermediate_states=True,
      same_completion_packet_has_another_original_STOP_command_producer=True)
    assert r.im.sha(image.read_bytes())==r.im.sha(blob)
    r.im.write_json(out/'stop-routing-results.json',proof);r.im.write_json(out/'summary.json',summary)
    (out/'executed-source.py').write_bytes(Path(__file__).read_bytes())
    r.im.write_json(out/'source-receipt.json',{'script_sha256':r.im.sha(Path(__file__).read_bytes()),
      'prior_helper_sha256':r.im.sha(Path(c.__file__).read_bytes()),'image_sha256':r.im.sha(blob),
      'previous_manifest_sha256':r.im.sha(raw),'volume_uuid':r.im.VOLUME,
      'proof_sha256':r.im.sha((out/'stop-routing-results.json').read_bytes()),
      'summary_sha256':r.im.sha((out/'summary.json').read_bytes())})
    print(json.dumps(summary,ensure_ascii=False))


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',required=True)
    args=parser.parse_args();r.im.volume();out=Path(args.output).resolve()
    assert STAGE in out.parents and not out.exists();out.mkdir()
    try:run(out)
    except Exception:
        (out/'attempt-source.py').write_bytes(Path(__file__).read_bytes())
        r.im.write_json(out/'attempt-failure.json',{'traceback':traceback.format_exc(),'passing_result':False});raise


if __name__=='__main__':main()
