#!/usr/bin/env python3
"""Original STOP/unmap/completion fragments on explicit offline guest fixtures.

Mandatory logs, locks, PCIATU service and queue send are boundaries, never
replaced. Independent mid-function fragments are not full transitions/actions.
No actual camera state, message producer, epoch, hardware or recovery is bound.
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
sys.path.insert(0,str(BASE/'stage43-native-functor-drain'))
import functor_drain as b
a,z,x,t,p,w,r,V=b.a,b.z,b.x,b.t,b.p,b.w,b.r,b.V
OUTER=a.OUTER
MAP=OUTER+0x31f70
CHANNEL=r.ARENA+0x3d0000
EXTRA=[(0x24cb90,0x24cda0),(0x22e638,0x22e8c0),(0x246144,0x24614c)]


class Guest(b.Guest):
    def __init__(self,blob,code,ro):
        super().__init__(blob,code,ro)
        self.ranges.extend((V+lo,V+hi) for lo,hi in EXTRA)
        for pc in (0x24cb90,0x24cbb0):self.boundaries.pop(V+pc,None)
        self.boundaries.update({V+0x2f604:'before_unexecuted_pciatu_unmap_service',
          V+0x27d568:'before_unexecuted_variadic_diagnostic',
          V+0x27dab4:'before_unexecuted_completion_queue_send',
          V+0x21c114:'before_independent_keyed_parameter_return'})


def setup(blob,code,ro):
    m=Guest(blob,code,ro)
    m.uc.mem_write(OUTER,r.p64(CHANNEL));w.put32(m,CHANNEL,7)
    m.uc.mem_write(MAP,r.p64(CHANNEL));w.put32(m,MAP+8,0x4242)
    return m


def full_stop_prefixes(blob,code,ro):
    cases=[]
    for state,action,target in ((8,0x24cb90,10),(9,0x24cbb0,4)):
        m=setup(blob,code,ro);a.fixture(m,state=state)
        phase=a.event(m,'original legal-state STOP wrapper '+str(state),'STOP_done',True)
        assert phase['reason']=='boundary: before_unexecuted_diagnostic_acquire'
        assert a.snapshot(m)['state']==state and a.snapshot(m)['active']==1
        assert hex(V+0x253f44) in phase['pcs'] and hex(V+action) not in phase['pcs']
        cases.append({'from_state':state,'table_destination_only':target,'selected_action':hex(action),
          'original_fragments':[phase],'mandatory_transition_diagnostic_not_executed':True,
          'state_store_action_and_entry_not_executed':True,'completed_transition':False})
    return cases


def action_prefixes(blob,code,ro):
    cases=[]
    for state,entry in ((8,0x24cb90),(9,0x24cbb0)):
        m=setup(blob,code,ro)
        phase=t.original(m,'independent original STOP action prefix '+str(state),entry,x0=OUTER,x1=a.EVENT)
        assert phase['reason']=='boundary: before_unexecuted_runtime_lock_wait'
        assert phase['x0_to_x5'][:2]==['0x4242','0xffffffff']
        assert hex(V+0x22e638) in phase['pcs']
        assert hex(V+0x22e65c) not in phase['pcs']
        assert int.from_bytes(m.read(MAP+0x34,4),'little')==0
        cases.append({'from_state_table':state,'entry':hex(entry),'original_fragments':[phase],
          'map_object':hex(MAP),'object_offset_from_outer':'0x31f70',
          'scope':'Independent action prefix; actual runtime lock acquisition and entire action unexecuted.',
          'hardware_stop_or_unmap_completed':False})
    return cases


def map_state(m):
    return {'mapped_flag':m.read(MAP+0xc,1)[0],
      'handle_u32':int.from_bytes(m.read(MAP+0x1c,4),'little'),
      'unmap_entry_counter_u32':int.from_bytes(m.read(MAP+0x34,4),'little'),
      'guard_held_byte':m.read(r.SP+0x38,1)[0]}


def unmap_tails(blob,code,ro):
    cases=[]
    for name,flag,handle,held,counter in (
       ('not_mapped',0,0x1234,0,4),('invalid_handle',1,0xffffffff,0,4),
       ('mapped_valid_handle',1,0x1234,0,4),('local_clear_before_unlock',0,0x1234,1,0xffffffff)):
        m=setup(blob,code,ro)
        m.uc.mem_write(MAP+0xc,bytes([flag]));w.put32(m,MAP+0x1c,handle);w.put32(m,MAP+0x34,counter)
        m.uc.mem_write(r.SP+0x30,r.p64(MAP+8)+bytes([held])+bytes(7))
        # Declared saved-frame input for this independent mid-function tail.
        # The original epilogue, never a host return adapter, reloads this LR.
        m.uc.mem_write(r.SP+0x60,struct.pack('<QQ',0,r.STOP))
        before=map_state(m)
        phase=t.original(m,'independent post-log unmap fragment '+name,0x22e6b8,x19=MAP)
        after=map_state(m)
        assert after['unmap_entry_counter_u32']==(counter+1)&0xffffffff
        if name=='mapped_valid_handle':
            assert phase['reason']=='boundary: before_unexecuted_pciatu_unmap_service'
            assert phase['x0_to_x5'][0]=='0x1234'
            assert after['mapped_flag']==1 and after['handle_u32']==handle
        else:
            assert after['mapped_flag']==0 and after['handle_u32']==0xffffffff
            assert hex(V+0x2f604) not in phase['pcs']
            if held:
                assert phase['reason']=='boundary: before_unexecuted_runtime_lock_release'
                assert phase['x0_to_x5'][0]=='0x4242' and after['guard_held_byte']==0
            else:
                assert phase['reason']=='returned' and phase['x0_to_x5'][0]=='0x1'
        cases.append({'case':name,'original_fragments':[phase],'before':before,'after':after,
          'scope':'Independent 0x22e6b8 post-diagnostic input fixture: real earlier lock/logs not executed; guard-held is a declared fixture, not acquired lock evidence.',
          'counter_increment_not_service_success_or_code_exit_receipt':True,
          'actual_lock_unmap_unlock_or_hardware_completion_verified':False})
    return cases


def stop_fields(blob,code,ro):
    cases=[]
    for seq,forced in ((0xff,1),(0,0x56)):
        m=setup(blob,code,ro)
        message=bytearray(0x80);message[2]=3;message[3]=0
        struct.pack_into('<H',message,4,0x1234);message[0xa]=seq;message[0xb]=forced
        m.uc.mem_write(x.MESSAGE,bytes(message));m.uc.mem_write(x.OUTPUT,bytes([0xa5])*8)
        w.put32(m,w.A+0x18,1);m.uc.mem_write(w.A+0x30,r.p64(x.MESSAGE))
        parsed=t.original(m,'original STOP parser prefix seq'+str(seq),0x225934,x0=w.A,x1=x.OUTPUT)
        assert parsed['reason']=='boundary: before_independent_keyed_parameter_return'
        assert m.read(x.OUTPUT,6)==bytes.fromhex('00a53412')+bytes([seq,forced])
        assert int(parsed['x0_to_x5'][2],16)==seq
        formatted=t.original(m,'independent original STOP field formatter seq'+str(seq),0x24cc14,
          x19=OUTER,x20=x.OUTPUT,x21=V+0x443dc5)
        assert formatted['reason']=='boundary: before_unexecuted_variadic_diagnostic'
        ptr=int.from_bytes(m.read(r.SP,8),'little')
        assert ptr==V+0x445022
        values=[int.from_bytes(m.read(r.SP+i,4),'little') for i in (8,0x10)]
        assert values==[seq,forced]
        cases.append({'seq_id':seq,'forced_stop_flag_byte':forced,'original_fragments':[parsed,formatted],
          'parser_result_hex':m.read(x.OUTPUT,6).hex(),'same_seq_byte_passed_as_parameter_map_key':True,
          'native_diagnostic_format':r.im.cstring(blob,ptr-V),'native_diagnostic_arguments':values,
          'scope':'Original parser prefix followed by a separate post-log formatting fragment on the parsed output. Actual diagnostic, keyed returns, high-level action and message origin/generation not executed.',
          'request_or_configuration_generation_binding_proven':False})
    return cases


def completion_packet(blob,code,ro):
    m=setup(blob,code,ro)
    built=t.original(m,'independent original STOP_COMP packet construction',0x24cc54,x19=OUTER)
    assert built['reason']=='boundary: before_unexecuted_diagnostic_acquire'
    packet=m.read(r.SP+0x20,12);cid,mid,length,channel=struct.unpack('<HHII',packet)
    assert (cid,mid,length,channel)==(0x2103,0x113,12,7)
    w.put32(m,OUTER+0x754,0x777)
    send=t.original(m,'independent original STOP_COMP send preparation',0x24cd1c,x19=OUTER)
    assert send['reason']=='boundary: before_unexecuted_completion_queue_send'
    assert send['x0_to_x5'][:3]==['0x777',hex(r.SP+0x20),'0xc']
    assert m.read(r.SP+0x20,12)==packet
    return {'original_fragments':[built,send],'packet_hex':packet.hex(),
      'cid':hex(cid),'mid':hex(mid),'length':length,'channel_id_fixture':channel,
      'packet_contains_seq_id_or_configuration_epoch':False,
      'scope':'Two independent fragments separated by unexecuted mandatory diagnostics. Packet is a guest fixture result; actual queue send, receiver and higher correlation are unexecuted.',
      'actual_completion_published_or_hardware_idle_verified':False}


def run(out):
    prior=b.STAGE/'final-receipt.json';raw=prior.read_bytes()
    assert r.im.sha(raw)=='b94fd89c56f8e3e52a005fb0227730844f5a74e02bd7296be6e8409297da7d0b'
    for e in json.loads(raw)['files']:assert r.im.sha((ROOT/e['path']).read_bytes())==e['sha256']
    image=BASE/'stage2/extraction/files/nflasha3/av-cam.bin';blob=image.read_bytes()
    assert r.im.sha(blob)==r.im.PINS['stage2/extraction/files/nflasha3/av-cam.bin']
    code,ro,_=p.object_image((p.STAGE/'scoped_writer.a64.o').read_bytes())
    parts={'legal_STOP_wrapper_prefixes':full_stop_prefixes(blob,code,ro),
      'independent_STOP_action_prefixes':action_prefixes(blob,code,ro),
      'independent_post_log_unmap_cases':unmap_tails(blob,code,ro),
      'STOP_result_field_binding':stop_fields(blob,code,ro),
      'independent_completion_packet':completion_packet(blob,code,ro)}
    def fragments(item):
        if isinstance(item,dict):
            for k,v in item.items():
                if k=='original_fragments':yield from v
                else:yield from fragments(v)
        elif isinstance(item,list):
            for v in item:yield from fragments(v)
    traces=list(fragments(parts))
    regions=[('legal STOP table wrappers',0x25591c,0x25594c),
      ('STOP state8 action',0x24cb90,0x24cbb0),('STOP state9 action',0x24cbb0,0x24cda0),
      ('PCIATU unmap function',0x22e638,0x22e8c0),('STOP parser field copy',0x225970,0x2259d4),
      ('transition action ordering',0x2534f0,0x253578)]
    proof={'status':'PASS_ORIGINAL_STOP_UNMAP_FIELDS_AND_NOTIFICATION_WITHIN_DECLARED_FRAGMENT_SCOPE',
      'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),**parts,
      'source_regions':[{'name':name,'instructions':r.im.dump(blob,lo,hi,V)} for name,lo,hi in regions],
      'unmap_source_file':r.im.cstring(blob,0x43ea8f),
      'unmap_entry_diagnostic':r.im.cstring(blob,0x43ecee),
      'unmap_error_diagnostic':r.im.cstring(blob,0x43ed6a),
      'completion_diagnostic':r.im.cstring(blob,0x44505b),
      'original_fragments':len(traces),
      'original_guest_store_count':sum(len(e['writes']) for e in traces),
      'unique_observed_PC_count':len({pc for e in traces for pc in e['pcs']}),
      'native_output_log_lock_unmap_or_send_adapters':False,
      'compiled_prototype_invoked':False,'full_STOP_transition_action_or_hardware_idle_verified':False,
      'camera_or_remote_access_attempted':False,'goal_complete':False,'persistent_write_release':False}
    summary={k:proof[k] for k in ('status','original_fragments','original_guest_store_count','unique_observed_PC_count',
      'full_STOP_transition_action_or_hardware_idle_verified','goal_complete','persistent_write_release')}
    summary.update(STOP_action_calls_PCIATU_unmap_not_a_hardware_stop_receipt=True,
      seq_id_is_u8_and_also_local_parameter_key=True,
      forced_stop_flag_byte_bound_to_original_diagnostic=True,
      STOP_COMP_packet_channel_only_no_seq_or_epoch=True,
      local_mapping_and_guard_flags_not_runtime_completion_receipts=True)
    assert r.im.sha(image.read_bytes())==r.im.sha(blob)
    r.im.write_json(out/'stop-completion-results.json',proof);r.im.write_json(out/'summary.json',summary)
    (out/'executed-source.py').write_bytes(Path(__file__).read_bytes())
    r.im.write_json(out/'source-receipt.json',{'script_sha256':r.im.sha(Path(__file__).read_bytes()),
      'prior_helper_sha256':r.im.sha(Path(b.__file__).read_bytes()),'image_sha256':r.im.sha(blob),
      'previous_manifest_sha256':r.im.sha(raw),'volume_uuid':r.im.VOLUME,
      'proof_sha256':r.im.sha((out/'stop-completion-results.json').read_bytes()),
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
