#!/usr/bin/env python3
"""Original embedded functor constructor/virtual drain in ordered guest contexts.

The constructor stops before unbound runtime memset. Two CPU contexts model one
specific schedule, not real threads/multicore/synchronization. No native return,
PC-to-LR/log/lock/HAL adapter. Resume uses exact saved/current PC and stack.
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
sys.path.insert(0,str(BASE/'stage42-encoder-state-and-lock-boundaries'))
import encoder_state as a
z,y,x,t,p,w,r,V=a.z,a.y,a.x,a.t,a.p,a.w,a.r,a.V
SM,WRAP,OUTER=a.SM,a.WRAP,a.OUTER
FIRST=a.EVENT
SECOND=a.EVENT+0x100
ALTSP=r.STACK+0x2000
RANGES=[(0x253b38,0x253dac),(0x253dac,0x253f00)]


class Guest(a.Guest):
    def __init__(self,blob,code,ro):
        super().__init__(blob,code,ro)
        self.ranges.extend((V+lo,V+hi) for lo,hi in RANGES)


def cpu(m):
    return {'pc':hex(m.uc.reg_read(r.reg.UC_ARM64_REG_PC)),
      'sp':hex(m.uc.reg_read(r.reg.UC_ARM64_REG_SP)),
      'lr':hex(m.uc.reg_read(r.reg.UC_ARM64_REG_X30)),
      'x0_to_x5':[hex(m.uc.reg_read(getattr(r.reg,'UC_ARM64_REG_X'+str(n)))) for n in range(6)]}


def current_run(m,label,start=None,registers=None):
    # Do not call reset_trace: a continuation must keep its real CPU stack/LR.
    m.reason=None;m.pcs=[];m.writes=[]
    if registers:m.regs(**registers)
    begin=m.uc.reg_read(r.reg.UC_ARM64_REG_PC) if start is None else V+start
    before=cpu(m);m.uc.emu_start(begin,0,count=20000,timeout=1000000)
    assert m.reason is not None,'native bounded run ended without boundary'
    return {'label':label,'reason':m.reason,'start_pc':hex(begin),
      'cpu_before':before,'cpu_after':cpu(m),'pcs':[hex(i) for i in m.pcs],
      'writes':m.writes,'state_after':a.snapshot(m),'native_output_or_diagnostic_adapters':False}


def construct(blob,code,ro,seed=0):
    m=Guest(blob,code,ro);m.uc.mem_write(SM,bytes([seed])*0x700)
    phase=t.original(m,'original state-machine constructor prefix',0x253b38,x0=SM)
    assert phase['reason']=='boundary: before_unbound_runtime_clear'
    assert phase['x0_to_x5'][:3]==[hex(SM+0x5a0),'0x0','0x58']
    assert int.from_bytes(m.read(SM+0x508,8),'little')==V+0x37f128
    assert int.from_bytes(m.read(SM+0x550,8),'little')==V+0x37f188
    assert int.from_bytes(m.read(SM+0x510,4),'little')==16 and int.from_bytes(m.read(SM+0x558,4),'little')==18
    assert m.read(SM+0x514,1)==m.read(SM+0x55c,1)==b'\0'
    assert int.from_bytes(m.read(SM+8,4),'little')==14
    phase.update(scope='Original constructor stores through first runtime-clear call only. Global singleton binding, both runtime clears and complete state initialization unexecuted.',
      active_byte_at_stop=m.read(SM+0xc,1)[0],queue_bytes_at_stop=m.read(SM+0x5a0,0x58).hex(),
      selected_vtables_created_by_original_stores=True)
    return m,phase


def prepared(blob,code,ro):
    m,ctor=construct(blob,code,ro)
    # Declared post-initialization state/owner fixtures. The two selected vptrs
    # remain the bytes written by the original constructor, never host-set.
    m.uc.mem_write(SM,r.p64(OUTER));w.put32(m,SM+8,6)
    m.uc.mem_write(WRAP,r.p64(SM));m.uc.mem_write(FIRST,b'\xa1'+bytes(5))
    m.uc.mem_write(SECOND,b'\xb2\xc3\xd4\xe5\xf6\x17')
    return m,ctor


def scheduled(blob,code,ro,queued_kind):
    m,ctor=prepared(blob,code,ro);events=[ctor]
    m.boundaries[V+0x252fd4]='outer_START_active_before_next_selector'
    outer=t.original(m,'outer original START-state wrapper reaches active point',0x252f38,x0=WRAP,x1=FIRST)
    events.append(outer);assert outer['reason']=='boundary: outer_START_active_before_next_selector'
    assert a.snapshot(m)['active']==1 and a.snapshot(m)['queue_count']==0
    saved_cpu=m.uc.context_save();saved_view=cpu(m)
    k=a.KINDS[queued_kind]
    nested=current_run(m,'separate guest CPU context queues '+queued_kind,k['wrapper'],
      {'x0':WRAP,'x1':SECOND,'sp':ALTSP,'x30':r.STOP})
    events.append(nested);assert nested['reason']=='returned'
    assert nested['cpu_after']['x0_to_x5'][0]=='0x1'
    pending=a.snapshot(m);assert pending['queue_count']==1
    assert pending['queued_pointers'][0]==hex(SM+k['functor'])
    assert m.read(SM+k['copy'],k['size'])==m.read(SECOND,k['size'])
    # Restore only the real saved CPU context. Nested guest RAM writes survive.
    # This is a deterministic scheduler fixture, not a fake native function exit.
    m.uc.context_restore(saved_cpu);assert cpu(m)==saved_view
    assert a.snapshot(m)==pending
    del m.boundaries[V+0x252fd4]
    body=0x253ec4 if queued_kind=='START_sys_v' else 0x253ee4
    m.boundaries[V+body]='after_native_pop_and_pending_clear_before_typed_body'
    drained=current_run(m,'resume exact outer context into queued '+queued_kind)
    events.append(drained)
    assert drained['reason']=='boundary: after_native_pop_and_pending_clear_before_typed_body'
    witness=a.snapshot(m)
    assert witness['queue_count']==0 and witness['active']==0
    assert witness['START_pending']==witness['STOP_pending']==0
    assert drained['cpu_after']['pc']==hex(V+body)
    assert int(drained['cpu_after']['sp'],16)!=r.SP
    assert hex(V+0x253db4) in drained['pcs'] and hex(V+0x253db8) in drained['pcs']
    assert m.read(SM+k['copy'],k['size'])==m.read(SECOND,k['size'])
    # A breakpoint at the native target is removed, then the exact same PC and
    # register/stack state are resumed. No saved return value is substituted.
    del m.boundaries[V+body]
    completed=current_run(m,'resume exact queued native body '+queued_kind)
    events.append(completed)
    if queued_kind=='START_sys_v':
        assert completed['reason']=='returned'
        assert completed['cpu_after']['pc']==hex(r.STOP) and int(completed['cpu_after']['sp'],16)==r.SP
        assert completed['cpu_after']['x0_to_x5'][0]=='0x1'
        assert hex(V+0x252f54) in completed['pcs']
        assert a.snapshot(m)['state']==6 and a.snapshot(m)['active']==0 and a.snapshot(m)['queue_count']==0
    else:
        # Deliberately wrong state: STOP arrives while controller is READY.
        # Native type-specific processing reaches diagnostic, never success.
        assert completed['reason']=='boundary: before_unexecuted_diagnostic_acquire'
        assert hex(V+0x2533d4) in completed['pcs'] and hex(V+0x254138) in completed['pcs']
        assert a.snapshot(m)['active']==1
    return {'queued_kind':queued_kind,'original_fragments':events,
      'outer_context_before_pause':saved_view,'pending_after_nested_native_call':pending,
      'zero_count_zero_flags_code_still_active_witness':{'state':witness,'cpu':drained['cpu_after'],
        'observed_native_typed_body_offset':hex(body),'code_exit_not_reached':True},
      'state_after_native_resume':a.snapshot(m),
      'typed_body_returned_to_original_outer_caller':queued_kind=='START_sys_v',
      'STOP_in_READY_is_explicit_invalid_order_fixture':queued_kind=='STOP_done',
      'real_threads_multicore_lock_runtime_owner_epoch_Hal_or_restore_verified':False}


def metadata(blob):
    rows=[]
    for kind,group,ti,name,typed in [('START_sys_v',0x37f118,0x330c50,0x330bd0,0x253ec4),
       ('STOP_done',0x37f178,0x330d90,0x330d10,0x253ee4)]:
        values=struct.unpack_from('<6Q',blob,group)
        assert values[0]==0 and values[1]==V+ti and values[4]==V+0x253db4 and values[5]==V+typed
        assert struct.unpack_from('<Q',blob,ti+8)[0]==V+name
        rows.append({'kind':kind,'table_header_offset':hex(group),'typeinfo_offset':hex(ti),
          'name_offset':hex(name),'type_name':r.im.cstring(blob,name),'address_point':hex(V+group+16),
          'generic_virtual_operator':hex(values[4]),'typed_virtual_body':hex(values[5])})
    return rows


def run(out):
    prior=a.STAGE/'final-receipt.json'
    assert r.im.sha(prior.read_bytes())=='f684956e041cc80761ff9f28dfc607850eb3add824e038b6ab46c6cf5aaa8ed7'
    manifest=json.loads(prior.read_text())
    for e in manifest['files']:assert r.im.sha((ROOT/e['path']).read_bytes())==e['sha256']
    image=BASE/'stage2/extraction/files/nflasha3/av-cam.bin';blob=image.read_bytes()
    assert r.im.sha(blob)==r.im.PINS['stage2/extraction/files/nflasha3/av-cam.bin']
    code,ro,_=p.object_image((p.STAGE/'scoped_writer.a64.o').read_bytes())
    meta=metadata(blob)
    _,seeded=construct(blob,code,ro,0xa5)
    assert seeded['active_byte_at_stop']==0xa5 and seeded['queue_bytes_at_stop']=='a5'*0x58
    cases=[scheduled(blob,code,ro,'START_sys_v'),scheduled(blob,code,ro,'STOP_done')]
    original_count=1+sum(len(c['original_fragments']) for c in cases)
    regions=[('original state-machine constructor prefix',0x253b38,0x253d90),
      ('unexecuted constructor final clear',0x253d90,0x253dac),
      ('generic functor operator',0x253db4,0x253dc4),
      ('typed START and STOP functor bodies',0x253ec4,0x253ef0),
      ('original queue pop and virtual call',0x2530fc,0x253158)]
    proof={'status':'PASS_ORIGINAL_CONSTRUCTOR_FUNCTOR_DRAIN_AND_ORDERED_CONTEXT_SCOPE',
      'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'metadata':meta,
      'seeded_constructor_prefix':seeded,'scheduled_cases':cases,'original_fragments':original_count,
      'source_regions':[{'name':n,'instructions':r.im.dump(blob,lo,hi,V)} for n,lo,hi in regions],
      'scheduler_scope':'Two explicit ordered guest CPU contexts via Unicorn context_save/context_restore, disjoint stacks. Not real concurrency, weak memory or runtime lock behavior. Only CPU context restored; RAM preserved.',
      'runtime_clear_and_diagnostic_output_adapters':False,
      'complete_constructor_runtime_instance_binding_or_real_Hal_restore_verified':False,
      'camera_or_remote_access_attempted':False,'goal_complete':False,'persistent_write_release':False}
    summary={k:proof[k] for k in ('status','original_fragments','complete_constructor_runtime_instance_binding_or_real_Hal_restore_verified','goal_complete','persistent_write_release')}
    summary.update(original_selected_functor_vptr_stores_executed=True,
      native_queue_pop_and_pending_clear_before_typed_body=True,
      zero_queue_zero_pending_still_has_active_native_call_stack=True,
      queued_START_native_body_returns_through_original_outer_stack=True,
      invalid_order_STOP_stops_at_diagnostic_after_flags_cleared=True,
      real_threads_multicore_and_locks_verified=False)
    assert r.im.sha(blob)==r.im.sha(image.read_bytes())
    r.im.write_json(out/'functor-drain-results.json',proof);r.im.write_json(out/'summary.json',summary)
    (out/'executed-source.py').write_bytes(Path(__file__).read_bytes())
    r.im.write_json(out/'source-receipt.json',{'script_sha256':r.im.sha(Path(__file__).read_bytes()),
      'stage42_helper_sha256':r.im.sha(Path(a.__file__).read_bytes()),'raw_harness_sha256':r.im.sha(Path(r.__file__).read_bytes()),
      'image_sha256':r.im.sha(blob),'prototype_object_sha256':r.im.sha((p.STAGE/'scoped_writer.a64.o').read_bytes()),
      'previous_manifest_sha256':r.im.sha(prior.read_bytes()),'proof_sha256':r.im.sha((out/'functor-drain-results.json').read_bytes()),
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
