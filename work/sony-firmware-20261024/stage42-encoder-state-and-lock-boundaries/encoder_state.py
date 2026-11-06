#!/usr/bin/env python3
"""Original encoder state events and lock boundaries on guest fixtures only.

No actual runtime lock operation, unbound action, logging return or HAL response
is simulated. Table destinations are distinct from completed state transitions.
Busy acceptance may leave copied event/functor data pending after buffer return.
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
sys.path.insert(0,str(BASE/'stage41-main-start-result-cycle'))
import start_result_cycle as z
y,x,t,p,w,r,V=z.y,z.x,z.t,z.p,z.w,z.r,z.V
SM=r.ARENA+0x240000
WRAP=r.ARENA+0x23f000
EVENT=r.ARENA+0x23e000
OUTER=r.ARENA+0x280000
GUARD=r.ARENA+0x23d000
LOCKROOT=x.IFACE-0x20e10
RANGES=[(0x252f38,0x25317c),(0x2533b8,0x2535f4),(0x2555bc,0x25573c),
 (0x25585c,0x2559dc),(0x253f00,0x253fe8),(0x254138,0x25420c),
 (0x24c5ec,0x24c640),(0x24c924,0x24c944),(0x22b628,0x22b69c),(0x27dc14,0x27dc90)]
KINDS={'START_sys_v':{'entry':0x252f54,'wrapper':0x252f38,'table':0x3806d8,'flag':0x514,'self':0x518,'copy':0x520,'functor':0x508,'size':1,'event':16},
       'STOP_done':{'entry':0x2533d4,'wrapper':0x2533b8,'table':0x380978,'flag':0x55c,'self':0x560,'copy':0x568,'functor':0x550,'size':6,'event':18}}


class Guest(z.Guest):
    def __init__(self,blob,code,ro):
        super().__init__(blob,code,ro)
        self.ranges.extend((V+a,V+b) for a,b in RANGES)
        self.boundaries.update({V+0x2ef4c:'before_unexecuted_runtime_lock_wait',
          V+0x2ef60:'before_unexecuted_runtime_lock_release',
          V+0x22e1e4:'before_unbound_ready_resource_helper',
          V+0x24cb90:'before_unbound_STOP_infra_action',
          V+0x24cbb0:'before_unbound_STOP_idle_action'})


def fixture(m,state=6,busy=0,count=0,write=0,read=0):
    m.uc.mem_write(SM,bytes(0x700));m.uc.mem_write(WRAP,r.p64(SM))
    m.uc.mem_write(SM,r.p64(OUTER));w.put32(m,SM+8,state)
    m.uc.mem_write(SM+0xc,bytes([busy]));w.put32(m,SM+0x590,count)
    w.put32(m,SM+0x594,write);w.put32(m,SM+0x598,read)
    m.uc.mem_write(EVENT,b'\xa1\xb2\xc3\xd4\xe5\xf6')
    m.uc.mem_write(OUTER+0x31fb0,b'\0')


def snapshot(m):
    return {'state':int.from_bytes(m.read(SM+8,4),'little'),'active':m.read(SM+0xc,1)[0],
      'START_pending':m.read(SM+0x514,1)[0],'STOP_pending':m.read(SM+0x55c,1)[0],
      'START_event_hex':m.read(SM+0x520,1).hex(),'STOP_event_hex':m.read(SM+0x568,6).hex(),
      'queue_count':int.from_bytes(m.read(SM+0x590,4),'little'),
      'queue_write':int.from_bytes(m.read(SM+0x594,4),'little'),
      'queue_read':int.from_bytes(m.read(SM+0x598,4),'little'),
      'queued_pointers':[hex(int.from_bytes(m.read(SM+0x5a0+i*8,8),'little')) for i in range(10)]}


def event(m,label,kind,wrapped=False):
    k=KINDS[kind]
    phase=t.original(m,label,k['wrapper'] if wrapped else k['entry'],x0=WRAP if wrapped else SM,x1=EVENT)
    phase.update(state_after=snapshot(m),kind=kind,
      scope='Original state-event helper on synthetic controller/state/active flags; no actual worker generation, hardware state, native constructor or runtime lock.')
    return phase


def names_and_targets(blob,code,ro):
    states=[];events=[];targets=[]
    for n in range(16):
        ptr=struct.unpack_from('<Q',blob,0xbddee0+n*8)[0]
        states.append({'index':n,'pointer':hex(ptr),'name':r.im.cstring(blob,ptr-V)})
    for n in range(21):
        ptr=struct.unpack_from('<Q',blob,0xbdde38+n*8)[0]
        events.append({'index':n,'pointer':hex(ptr),'name':r.im.cstring(blob,ptr-V)})
    assert states[5]['name']=='ENC_READY_WAIT' and states[6]['name']=='ENC_READY'
    assert states[8]['name']=='ENC_STOP_WAIT' and states[10]['name']=='ENC_INFRA_STOP_WAIT' and states[4]['name']=='ENC_IDLE'
    assert events[16]['name']=='enc_sys_v_t' and events[18]['name']=='enc_stop_done_t'
    for kind,k in KINDS.items():
        for n in range(16):
            pointers=struct.unpack_from('<3Q',blob,k['table']+n*24)
            m=Guest(blob,code,ro);phase=t.original(m,kind+' original next-state selector'+str(n),pointers[2]-V)
            assert phase['reason']=='returned';target=int(phase['x0_to_x5'][0],16);assert 0<=target<16
            targets.append({'kind':kind,'from_state':n,'guard':hex(pointers[0]),'action':hex(pointers[1]),
              'next_state_function':hex(pointers[2]),'next_state':target,'original_fragment':phase,
              'not_completed_transition_or_action':True})
    assert next(c for c in targets if c['kind']=='START_sys_v' and c['from_state']==5)['next_state']==6
    assert next(c for c in targets if c['kind']=='STOP_done' and c['from_state']==8)['next_state']==10
    assert next(c for c in targets if c['kind']=='STOP_done' and c['from_state']==9)['next_state']==4
    return states,events,targets


def state_cases(blob,code,ro):
    cases=[]
    for kind in KINDS:
        k=KINDS[kind]
        for mode in ('busy','busy_wrapper','duplicate','full','wrap'):
            m=Guest(blob,code,ro)
            fixture(m,state=5 if kind=='START_sys_v' else 8,busy=1,
              count=10 if mode=='full' else 0,write=9 if mode=='wrap' else 0,read=9 if mode=='wrap' else 0)
            if mode=='duplicate':m.uc.mem_write(SM+k['flag'],b'\1')
            phase=event(m,kind+' '+mode,kind,mode=='busy_wrapper');s=snapshot(m)
            assert phase['reason']=='returned';ret=int(phase['x0_to_x5'][0],16)
            if mode=='duplicate':assert ret==9 and s['state']==15 and s['queue_count']==0
            else:
                assert ret==1 and s[kind.split('_')[0]+'_pending']==1
                assert m.read(SM+k['copy'],k['size'])==m.read(EVENT,k['size'])
                assert int.from_bytes(m.read(SM+k['self'],8),'little')==SM
                if mode=='full':assert s['queue_count']==10
                else:
                    assert s['queue_count']==1 and s['queue_write']==(0 if mode=='wrap' else 1)
                    assert s['queued_pointers'][9 if mode=='wrap' else 0]==hex(SM+k['functor'])
            cases.append({'case':kind+' '+mode,'original_fragments':[phase],
              'return_value':ret,'state_after':s,'functor_constructor_vptr_drain_and_actual_active_event_unbound':True})
    for mode,initial in (('already_READY',6),('READY_WAIT_resource_flag0',5),('READY_WAIT_resource_flag1',5),('INITIAL_PSEUDO',14),('ERROR',15)):
        m=Guest(blob,code,ro);fixture(m,state=initial)
        if mode.endswith('flag1'):m.uc.mem_write(OUTER+0x31fb0,b'\1')
        phase=event(m,mode,'START_sys_v',True);s=snapshot(m)
        if mode.endswith('flag1'):assert phase['reason']=='boundary: before_unbound_ready_resource_helper'
        else:
            assert phase['reason']=='returned';ret=int(phase['x0_to_x5'][0],16)
            assert ret==(0 if initial in (14,15) else 1)
            assert s['state']==(15 if initial in (14,15) else initial)
            if initial not in (14,15):assert s['active']==0 and s['queue_count']==0
        cases.append({'case':mode,'original_fragments':[phase],'state_after':s,
          'actual_ready_hardware_or_full_resource_action_verified':False})
    return cases


def cross_layer(blob,code,ro,descriptor):
    old=z.Guest
    try:
        z.Guest=Guest;m,original,prototypes,_,copied,_=z.setup(blob,code,ro,descriptor)
    finally:z.Guest=old
    z.publish(m,original,3)
    released=x.cleanup(m,original,'original STOP low-level cleanup before busy upper state')
    assert released['reason']=='returned' and released['state_after']['pool_count']==4
    assert released['state_after']['index_roots']==['0x0']*4
    fixture(m,state=8,busy=1)
    stop_data=m.read(x.OUTPUT,6);m.uc.mem_write(EVENT,stop_data)
    queued=event(m,'original upper STOP event queues after local parameter return','STOP_done',True);original.append(queued)
    assert queued['reason']=='returned' and queued['x0_to_x5'][0]=='0x1'
    assert snapshot(m)['queue_count']==1 and snapshot(m)['STOP_pending']==1
    assert m.read(SM+0x568,6)==stop_data
    assert int.from_bytes(m.read(t.POOL,4),'little')==4
    assert [m.read(at,0x400) for at in x.BUFFERS]==copied
    return {'original_fragments':original,'prototype_events':prototypes,'state_after':snapshot(m),
      'original_STOP_result_hex':stop_data.hex(),'low_level_four_parameter_buffers_returned':True,
      'upper_STOP_event_remains_pending_after_local_return':True,
      'actual_outer_active_event_or_shared_synchronization_not_observed':True}


def locks(blob,code,ro):
    cases=[]
    m=Guest(blob,code,ro);w.put32(m,LOCKROOT,0x1234)
    phase=t.original(m,'original locked START wrapper stops before runtime wait',0x22b628,x0=LOCKROOT,x1=0,x2=x.OUTPUT)
    assert phase['reason']=='boundary: before_unexecuted_runtime_lock_wait'
    assert hex(V+0x2304a0) not in phase['pcs']
    assert int(phase['x0_to_x5'][0],16)==0x1234
    cases.append({'case':'lock_wait','original_fragments':[phase],'actual_lock_acquired':False})
    for held in (0,1):
        m=Guest(blob,code,ro);w.put32(m,LOCKROOT,0x1234)
        m.uc.mem_write(GUARD,r.p64(LOCKROOT)+bytes([held])+bytes(7))
        phase=t.original(m,'original guard release flag'+str(held),0x27dc6c,x0=GUARD)
        assert phase['reason']==('boundary: before_unexecuted_runtime_lock_release' if held else 'returned')
        assert m.read(GUARD+8,1)==b'\0'
        cases.append({'case':'release_flag'+str(held),'original_fragments':[phase],
          'actual_runtime_release_performed':False,
          'guard_byte_zero_alone_is_not_runtime_unlock_evidence':True})
    return cases


def run(out):
    prior=z.STAGE/'final-receipt.json'
    assert r.im.sha(prior.read_bytes())=='1763489123b8381c6971de92661e965ad0e9517b292dc7993b6750c42c16fff9'
    manifest=json.loads(prior.read_text())
    for e in manifest['files']:assert r.im.sha((ROOT/e['path']).read_bytes())==e['sha256']
    image=BASE/'stage2/extraction/files/nflasha3/av-cam.bin';blob=image.read_bytes()
    assert r.im.sha(blob)==r.im.PINS['stage2/extraction/files/nflasha3/av-cam.bin']
    code,ro,_=p.object_image((p.STAGE/'scoped_writer.a64.o').read_bytes())
    descriptor=bytes.fromhex(json.loads((w.v.u.q.STAGE/'run-20261025/imola-matcher-results.json').read_text())['artificial_quality24_descriptor']['descriptor_hex'])
    states,events,targets=names_and_targets(blob,code,ro)
    state_controls=state_cases(blob,code,ro);cross=cross_layer(blob,code,ro,descriptor);lock_controls=locks(blob,code,ro)
    original_count=len(targets)+sum(len(c['original_fragments']) for c in state_controls+lock_controls)+len(cross['original_fragments'])
    regions=[('original START state-event helper',0x252f38,0x25317c),('original STOP state-event helper',0x2533b8,0x2535f4),
      ('original START table functions',0x2555bc,0x25573c),('original STOP table functions',0x25585c,0x2559dc),
      ('original START readiness guard prefix',0x24c5ec,0x24c640),('original false guard return',0x24c924,0x24c944),
      ('original locked START wrapper',0x22b628,0x22b69c),('original lock guard helpers',0x27dc14,0x27dc90)]
    proof={'status':'PASS_ORIGINAL_ENCODER_STATE_EVENT_QUEUE_AND_RUNTIME_LOCK_BOUNDARY_SCOPE',
      'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'state_names':states,'event_names':events,
      'next_state_selectors':targets,'state_controls':state_controls,'cross_layer_STOP':cross,'lock_controls':lock_controls,
      'original_fragments':original_count,'compiled_prototype_calls':len(cross['prototype_events']),
      'source_regions':[{'name':n,'instructions':r.im.dump(blob,a,end,V)} for n,a,end in regions],
      'actual_lock_action_full_transitions_current_epoch_Hal_or_physical_recovery_bound':False,
      'runtime_or_diagnostic_output_adapters':False,'camera_or_remote_access_attempted':False,
      'goal_complete':False,'persistent_write_release':False}
    summary={k:proof[k] for k in ('status','original_fragments','compiled_prototype_calls',
      'actual_lock_action_full_transitions_current_epoch_Hal_or_physical_recovery_bound','goal_complete','persistent_write_release')}
    summary.update(named_states=len(states),named_events=len(events),original_next_state_selectors=len(targets),
      state_controls=len(state_controls),lock_controls=len(lock_controls),
      upper_STOP_can_remain_queued_after_four_low_level_buffer_returns=True,
      wrapper_true_may_mean_queued_or_ready_guard_false_no_state_change=True,
      queue_full_control_sets_pending_copy_without_new_queue_entry=True,
      actual_runtime_lock_calls_stopped_not_mocked=True)
    assert r.im.sha(blob)==r.im.sha(image.read_bytes())
    r.im.write_json(out/'encoder-state-results.json',proof);r.im.write_json(out/'summary.json',summary)
    (out/'executed-source.py').write_bytes(Path(__file__).read_bytes())
    r.im.write_json(out/'source-receipt.json',{'script_sha256':r.im.sha(Path(__file__).read_bytes()),
      'stage41_helper_sha256':r.im.sha(Path(z.__file__).read_bytes()),'stage40_helper_sha256':r.im.sha(Path(y.__file__).read_bytes()),
      'stage39_helper_sha256':r.im.sha(Path(x.__file__).read_bytes()),'raw_harness_sha256':r.im.sha(Path(r.__file__).read_bytes()),
      'image_sha256':r.im.sha(blob),'prototype_object_sha256':r.im.sha((p.STAGE/'scoped_writer.a64.o').read_bytes()),
      'previous_manifest_sha256':r.im.sha(prior.read_bytes()),'proof_sha256':r.im.sha((out/'encoder-state-results.json').read_bytes()),
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
