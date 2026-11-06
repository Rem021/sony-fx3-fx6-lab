#!/usr/bin/env python3
"""Original MAIN START-result reader/peek and START-to-STOP guest cycle.

Inbound messages/registry/current state are explicit fixtures. Receiver prefix
and post-diagnostic continuation remain separate. No actual transport, error
enum, request generation, HAL, camera backup/restore or completion hook is bound.
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
sys.path.insert(0,str(BASE/'stage40-response-types-and-publication'))
import response_publication as y
x,t,p,w,r,V=y.x,y.t,y.p,y.w,y.r,y.V
FLAG=x.OUTPUT+0x20
TYPE=x.OUTPUT+0x21
EXTRA=[(0x2249cc,0x224a90),(0x228b64,0x228b7c),(0x2304a0,0x2304a8),
       (0x22c528,0x22c550)]


class Guest(y.Guest):
    def __init__(self,blob,code,ro):
        super().__init__(blob,code,ro)
        self.ranges.extend((V+a,V+z) for a,z in EXTRA)


def setup(blob,code,ro,descriptor):
    old=y.Guest
    try:
        y.Guest=Guest;result=y.setup(blob,code,ro,descriptor,0)
    finally:y.Guest=old
    return result


def state(m):
    return {'parameter_pool_count':int.from_bytes(m.read(t.POOL,4),'little'),
      'parameter_index_roots':[hex(int.from_bytes(m.read(at,8),'little')) for at in x.MAPS],
      'pending_count':int.from_bytes(m.read(w.A+0x18,4),'little'),
      'pending_write_index':int.from_bytes(m.read(w.A+0x1c,4),'little'),
      'pending_read_index':int.from_bytes(m.read(w.A+0x20,4),'little'),
      'message_pool_count':int.from_bytes(m.read(x.RETURN_POOL,4),'little'),
      'message_pool_write_index':int.from_bytes(m.read(x.RETURN_POOL+4,4),'little'),
      'message_pool_read_index':int.from_bytes(m.read(x.RETURN_POOL+8,4),'little')}


def peek(m,events,label):
    m.uc.mem_write(FLAG,b'\xa5\xa5')
    event=t.original(m,label,0x22c528,x0=w.A,x1=FLAG,x2=TYPE)
    assert event['reason']=='returned' and event['x0_to_x5'][0]=='0x0'
    flag,kind=m.read(FLAG,2);assert flag==int(state(m)['pending_count']!=0)
    event.update(has_pending=flag,type_output=kind,
      type_output_untouched_when_empty=not flag and kind==0xa5,
      scope='Original count/type peek only: x0return0 is not presence, type output unchanged when flag0.')
    events.append(event);return flag,kind


def publish(m,events,kind,key=0,byte3=0):
    inbound=bytearray(0x90);inbound[0x11]=0;inbound[0x12]=kind;inbound[0x13]=byte3
    struct.pack_into('<H',inbound,0x14,0x1234);inbound[0x1a]=key;inbound[0x1b]=0x56
    m.uc.mem_write(y.RAW,bytes(inbound))
    prefix=t.original(m,'original receive prefix type'+str(kind),0x2280c0,x0=x.IFACE,x1=y.RAW)
    events.append(prefix);assert prefix['reason']=='boundary: before_unexecuted_response_diagnostic'
    regs={f'x{i}':m.uc.reg_read(getattr(r.reg,'UC_ARM64_REG_X'+str(i))) for i in range(19,29)}
    regs['sp']=m.uc.reg_read(r.reg.UC_ARM64_REG_SP)
    prefix['captured_post_diagnostic_fixture_registers']={k:hex(v) for k,v in regs.items()}
    suffix=t.original(m,'independent original post-diagnostic publish type'+str(kind),0x22814c,**regs)
    events.append(suffix);assert suffix['reason']=='returned',suffix['reason']
    assert m.read(x.MESSAGE,0x80)==bytes(inbound[0x10:])
    suffix['scope']='Separate original continuation with captured fixtures; mandatory diagnostic and raw transport not executed.'
    return bytes(inbound)


def start_reader(m,events,label,wrapped=True):
    m.uc.mem_write(x.OUTPUT,bytes([0xa5])*8)
    event=t.original(m,label,0x2304a0 if wrapped else 0x2249d0,
      **({'x0':x.IFACE-0x390,'x1':0,'x2':x.OUTPUT} if wrapped else {'x0':w.A,'x1':x.OUTPUT}))
    assert event['reason']=='returned' and event['x0_to_x5'][0]=='0x0'
    event.update(output_hex=m.read(x.OUTPUT,8).hex(),state_after=state(m),
      scope='Original START_DONE reader; wrapped path executes original+0x390 adjustment/owner lookup. No actual high-level state-machine caller or epoch validation.')
    events.append(event);return event


def cycle(blob,code,ro,descriptor):
    m,events,prototypes,assembled,copied,_=setup(blob,code,ro,descriptor)
    initial=state(m);assert peek(m,events,'empty native peek before START')==(0,0xa5)
    publish(m,events,0)
    assert peek(m,events,'native peek after START publication')==(1,0)
    read=start_reader(m,events,'original wrapped MAIN START reader')
    after_start=state(m)
    assert read['output_hex']=='00a5341200a5a5a5'
    assert after_start['pending_count']==0 and after_start['message_pool_count']==1
    assert after_start['parameter_pool_count']==0
    assert after_start['parameter_index_roots']==[hex(n) for n in x.NODES]
    assert [m.read(at,0x400) for at in x.BUFFERS]==copied
    assert peek(m,events,'empty native peek after START consumption')==(0,0xa5)
    publish(m,events,3)
    assert peek(m,events,'native peek after STOP publication')==(1,3)
    stopped=x.cleanup(m,events,'original STOP reader in same owner cycle')
    assert stopped['reason']=='returned' and stopped['x0_to_x5'][0]=='0x0'
    after_stop=state(m)
    assert after_stop['pending_count']==0 and after_stop['message_pool_count']==1
    assert after_stop['parameter_pool_count']==4 and after_stop['parameter_index_roots']==['0x0']*4
    assert after_stop['pending_read_index']==after_stop['pending_write_index']==2
    assert after_stop['message_pool_read_index']==2 and after_stop['message_pool_write_index']==3
    assert [m.read(at,0x400) for at in x.BUFFERS]==copied
    assert peek(m,events,'empty native peek after STOP consumption')==(0,0xa5)
    return {'original_fragments':events,'prototype_events':prototypes,'initial_state':initial,
      'after_START_consumer':after_start,'after_STOP_consumer':after_stop,
      'codec_target':assembled['target'],'same_message_buffer_natively_returned_then_reborrowed':True,
      'parameter_copies_retained_after_START_returned_after_STOP':True,
      'raw_messages_registry_and_generation_are_fixtures':True,
      'actual_Hal_recording_or_recovery_verified':False}


def controls(blob,code,ro,descriptor):
    cases=[]
    for kind in ('wrong_type','different_key','nonzero_byte3','message_pool_full','empty_with_fallback'):
        m,events,prototypes,_,copied,_=setup(blob,code,ro,descriptor)
        message_type=3 if kind=='wrong_type' else 0
        inbound=publish(m,events,message_type,key=1 if kind=='different_key' else 0,byte3=7 if kind=='nonzero_byte3' else 0)
        if kind=='message_pool_full':w.put32(m,x.RETURN_POOL,0x100)
        if kind=='empty_with_fallback':
            # Explicit detached/current-message fixture, not a demonstrated
            # receive transition or an authorized call contract for MAIN.
            w.put32(m,w.A+0x18,0);m.uc.mem_write(w.A+0x1030,r.p64(x.MESSAGE))
        before=state(m);presence=peek(m,events,kind+' original peek')
        event=start_reader(m,events,kind+' deliberate direct START reader',False)
        after=state(m)
        assert after['parameter_pool_count']==0 and after['parameter_index_roots']==[hex(n) for n in x.NODES]
        assert [m.read(at,0x400) for at in x.BUFFERS]==copied
        if kind=='wrong_type':
            assert presence==(1,3) and after==before and event['output_hex']=='a5'*8
        else:
            assert after['pending_count']==0
            assert m.read(x.OUTPUT,1)==inbound[0x13:0x14]
            assert m.read(x.OUTPUT+2,2)==inbound[0x14:0x16]
            assert m.read(x.OUTPUT+4,1)==inbound[0x1a:0x1b]
            assert after['message_pool_count']==(0x100 if kind=='message_pool_full' else 1)
            if kind=='empty_with_fallback':assert presence==(0,0xa5)
        cases.append({'control':kind,'original_fragments':events,'prototype_events':prototypes,
          'before_reader':before,'after_reader':after,'peek':{'has_pending':presence[0],'type_output':presence[1]},
          'scope':'Explicit boundary fixtures and deliberately called low-level reader. Not proof actual upper caller misuses it, source trust, error enum or request correlation.',
          'actual_error_or_stale_reply_failure_on_camera':False})
    return cases


def run(out):
    prior=y.STAGE/'final-receipt.json'
    assert r.im.sha(prior.read_bytes())=='c1faf520990b248bb660e7a43d7b139947b462b39b433007279b6b17eb75907f'
    manifest=json.loads(prior.read_text())
    for e in manifest['files']:assert r.im.sha((ROOT/e['path']).read_bytes())==e['sha256']
    image=BASE/'stage2/extraction/files/nflasha3/av-cam.bin';blob=image.read_bytes()
    assert r.im.sha(blob)==r.im.PINS['stage2/extraction/files/nflasha3/av-cam.bin']
    code,ro,_=p.object_image((p.STAGE/'scoped_writer.a64.o').read_bytes())
    descriptor=bytes.fromhex(json.loads((w.v.u.q.STAGE/'run-20261025/imola-matcher-results.json').read_text())['artificial_quality24_descriptor']['descriptor_hex'])
    sequence=cycle(blob,code,ro,descriptor);negative=controls(blob,code,ro,descriptor)
    original_count=len(sequence['original_fragments'])+sum(len(c['original_fragments']) for c in negative)
    prototype_count=len(sequence['prototype_events'])+sum(len(c['prototype_events']) for c in negative)
    regions=[('original START reader and related peek thunk',0x2249cc,0x224a90),
      ('original pending type peek',0x22c528,0x22c550),('original owner-lookup START wrapper',0x228b64,0x228b7c),
      ('original outer owner adjustment',0x2304a0,0x2304a8)]
    proof={'status':'PASS_ORIGINAL_MAIN_START_READER_PEEK_AND_SAME_OWNER_START_STOP_CYCLE_SCOPE',
      'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'cycle':sequence,'controls':negative,
      'original_fragments':original_count,'compiled_prototype_calls':prototype_count,
      'source_regions':[{'name':name,'instructions':r.im.dump(blob,a,z,V)} for name,a,z in regions],
      'actual_message_transport_high_level_caller_request_epoch_error_enum_Hal_or_recovery_bound':False,
      'runtime_or_diagnostic_output_adapters':False,'camera_or_remote_access_attempted':False,
      'goal_complete':False,'persistent_write_release':False}
    summary={k:proof[k] for k in ('status','original_fragments','compiled_prototype_calls',
      'actual_message_transport_high_level_caller_request_epoch_error_enum_Hal_or_recovery_bound','goal_complete','persistent_write_release')}
    summary.update(controls=len(negative),START_consumes_message_without_releasing_four_parameter_copies=True,
      STOP_later_returns_four_parameter_copies_in_same_owner=True,
      native_peek_presence_and_type_are_outputs_not_return0=True,
      low_level_START_reader_no_expected_key_argument_or_epoch_check_in_executed_body=True,
      empty_queue_low_level_reader_can_use_explicit_fallback_fixture=True)
    assert r.im.sha(blob)==r.im.sha(image.read_bytes())
    r.im.write_json(out/'start-result-cycle-results.json',proof);r.im.write_json(out/'summary.json',summary)
    (out/'executed-source.py').write_bytes(Path(__file__).read_bytes())
    r.im.write_json(out/'source-receipt.json',{'script_sha256':r.im.sha(Path(__file__).read_bytes()),
      'stage40_helper_sha256':r.im.sha(Path(y.__file__).read_bytes()),'stage39_helper_sha256':r.im.sha(Path(x.__file__).read_bytes()),
      'stage38_helper_sha256':r.im.sha(Path(t.__file__).read_bytes()),'raw_harness_sha256':r.im.sha(Path(r.__file__).read_bytes()),
      'image_sha256':r.im.sha(blob),'prototype_object_sha256':r.im.sha((p.STAGE/'scoped_writer.a64.o').read_bytes()),
      'previous_manifest_sha256':r.im.sha(prior.read_bytes()),'proof_sha256':r.im.sha((out/'start-result-cycle-results.json').read_bytes()),
      'summary_sha256':r.im.sha((out/'summary.json').read_bytes()),'volume_uuid':r.im.VOLUME})
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
