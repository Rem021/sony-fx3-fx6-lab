#!/usr/bin/env python3
"""Native MID demux and context-owned QoS snapshot, with explicit call gaps.

Task hook lookup/call, diagnostics and parameter dump are unexecuted; this is
not the normal receive operation, a natural16M policy, or real MAIN binding.
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
sys.path.insert(0,str(BASE/'stage100-native-qos-routing-and-queue-lifetime'))
import qos_routing as prev
r,V,im=prev.r,prev.V,prev.im
STATE,QUEUE,SM_REF=prev.STATE,prev.QUEUE,prev.SM_REF
BACK,BACK_HANDLE=prev.BACK,prev.BACK_HANDLE
OWNED=STATE+0x358
MESSAGE=r.ARENA+0x80000
REPLY1,REPLY2=0x12345678,0x34567890
PRIOR=BASE/'stage100-native-qos-routing-and-queue-lifetime/final-receipt.json'
PRIOR_SHA='665534f9dee835252dc6949b10fc279310d302bfcdc9f0729aa74a8111c6481b'


def sha(raw):return hashlib.sha256(raw).hexdigest()


class Guest(prev.Guest):
    def __init__(self,blob,seed):
        super().__init__(blob,seed)
        self.ranges.extend([(V+0x177934,V+0x177ddc)])
        self.boundaries.update({
            V+0x17794c:'before_unbound_task_hook_lookup',
            V+0x17795c:'before_unexecuted_task_hook_call',
            V+0x17a9a4:'before_unexecuted_parameter_dump',
        })


def setup(blob,seed,state):
    m=Guest(blob,seed)
    # Context object addresses and its back-state binding are fixtures. The
    # original timing constructor and original state target setter execute.
    for at,value in ((prev.CFG_REF,prev.CFG),(prev.INTERFACE+0x10,prev.CODEC),
                     (prev.CODEC+0x10,prev.CFG_REF),(SM_REF,STATE)):
        m.uc.mem_write(at,r.p64(value))
    m.uc.mem_write(prev.CFG+8,b'\x02')
    events=[m.phase('complete original timing constructor',0xa6eb0,
                     [(prev.TIMING,prev.TIMING+prev.TIMING_SIZE)],
                     x0=prev.TIMING,x1=prev.CFG_REF,x2=0,x3=0,x4=prev.INTERFACE)]
    assert events[-1]['reason']=='returned'
    events.append(m.phase('original state target binder',0x17792c,
                          [(STATE+0x20,STATE+0x28)],x0=STATE,x1=prev.TIMING))
    assert events[-1]['reason']=='returned'
    data=bytearray(0x1000)
    struct.pack_into('<Q',data,0,STATE);struct.pack_into('<I',data,8,state)
    m.uc.mem_write(BACK,bytes(data));m.uc.mem_write(BACK_HANDLE,r.p64(BACK))
    m.uc.mem_write(STATE+0x18,r.p64(BACK_HANDLE))
    m.uc.mem_write(QUEUE,bytes(0x20))
    del m.boundaries[V+0x17effc]
    return m,events


def wire(seed,target=16000000,mid=0x10a):
    # CID/length are declared values, not validated by this lower demux.
    payload=prev.request(seed,target,1,0)[:0x48]
    return struct.pack('<HHHH',0x2003,mid,0x50,0)+payload


def receive_prefix(m,raw,reply):
    m.uc.mem_write(MESSAGE,raw)
    events=[m.phase('original receive prologue before unbound task hook',0x177934,
                     x0=STATE,x1=MESSAGE,x2=reply)]
    assert events[-1]['reason']=='boundary: before_unbound_task_hook_lookup'
    # This MOV has original input X1. Unknown task-hook loads/call are not
    # executed, and no register/output/return for that hook is supplied.
    events.append(m.phase('independent original message-pointer MOV before task-hook call',
                          0x177958,fresh=False))
    assert events[-1]['reason']=='boundary: before_unexecuted_task_hook_call'
    assert m.uc.reg_read(r.reg.UC_ARM64_REG_X22)==MESSAGE
    events.append(m.phase('independent post-hook original MID demultiplexer',0x177960,fresh=False))
    assert events[-1]['reason']=='boundary: before_original_logger_getter'
    mid=struct.unpack_from('<H',raw,2)[0]
    destination={0x107:0x177980,0x108:0x177bfc,0x109:0x177c8c,0x10a:0x177d28}[mid]
    assert hex(V+destination) in events[-1]['pcs']
    assert m.read(MESSAGE,len(raw))==raw
    return events


def copy_owned(m,raw,reply):
    event=m.phase('independent post-diagnostic original48-byte context snapshot',0x177d98,
                   [(OWNED,OWNED+0x4c)],fresh=False)
    assert event['reason']=='boundary: before_unexecuted_parameter_dump'
    expected=raw[8:]+struct.pack('<I',reply)
    assert m.read(OWNED,0x4c)==expected
    assert m.read(MESSAGE,len(raw))==raw
    return event,expected


def onward(m,expected):
    event=m.phase('post-dump native receive tail into original ROM event action',
                  0x177dc0,[(BACK,BACK+0x1000)],fresh=False)
    assert event['reason']=='boundary: before_original_logger_getter'
    assert m.read(OWNED,0x4c)==expected
    assert m.uc.reg_read(r.reg.UC_ARM64_REG_X1)==OWNED
    return event


def route(blob,seed,state,second=False):
    m,events=setup(blob,seed,state)
    raw=wire(seed)
    events.extend(receive_prefix(m,raw,REPLY1))
    e,expected=copy_owned(m,raw,REPLY1);events.append(e)
    # Change only the original wire buffer. This exact mutation is a host
    # experiment, not a claimed normal receive schedule or camera race.
    changed=bytearray(raw);struct.pack_into('<I',changed,16,20000000)
    m.uc.mem_write(MESSAGE,bytes(changed))
    assert m.read(OWNED,0x4c)==expected
    events.append(onward(m,expected))
    assert m.read(MESSAGE,len(raw))==bytes(changed)
    if state==3:
        assert hex(V+0x185084) in events[-1]['pcs']
        assert hex(V+0x189ce8) in events[-1]['pcs']
        # Another original entry on the lower stack; preserve the entire
        # suspended receive/event/timing frame rather than overwriting it.
        sp=m.uc.reg_read(r.reg.UC_ARM64_REG_SP)
        pending=m.read(sp,r.SP-sp)
        events.append(m.phase('independent lower forwarding using native context snapshot',
                              0x14555c,x0=prev.INTERFACE,x1=OWNED,
                              sp=prev.LOWER_SP,stack_ceiling=prev.LOWER_SP))
        assert events[-1]['reason']=='boundary: before_message_object_constructor'
        body=m.read(m.uc.reg_read(r.reg.UC_ARM64_REG_SP)+0x1a8,0x54)
        assert body==struct.pack('<HHHHI',0x2103,0x10a,0x54,0,2)+expected[:0x48]
        assert m.read(sp,r.SP-sp)==pending
        assert prev.u32(body,20)==16000000
        return {'seed':seed,'declared_numeric_state':state,'source_mutation_to':20000000,
                'context_snapshot_hex':expected.hex(),'lower_envelope_hex':body.hex(),
                'source_wire_after_hex':bytes(changed).hex(),'events':events,
                'source_mutation_does_not_change_context_copy':True,
                'suspended_original_frames_preserved':True,'MAIN_or_Hal_application_proven':False}
    assert state==1 and hex(V+0x185044) in events[-1]['pcs']
    assert hex(V+0x17df28) in events[-1]['pcs']
    # The original queue prologue and enclosing state/receive frames exist.
    # Execute diagnostic argument preparation, then independently enter the
    # queue body after unexecuted logging; do not fabricate logger returns.
    events.append(m.phase('original queue diagnostic argument preparation',0x17df50,fresh=False))
    assert events[-1]['reason']=='boundary: before_original_diagnostic'
    events.append(m.phase('post-diagnostic queue body and native state/receive return',
                          0x17dfc4,[(QUEUE,QUEUE+0x20),(BACK,BACK+0x1000)],fresh=False))
    assert events[-1]['reason']=='returned' and events[-1]['SP_after']==hex(r.SP)
    assert prev.u32(m.read(QUEUE,4))==1
    assert prev.u64(m.read(QUEUE+0x10,8))==OWNED
    assert m.read(OWNED,0x4c)==expected
    first_queue=m.read(QUEUE,0x20)
    if not second:
        return {'seed':seed,'declared_numeric_state':state,'second_receive_fixture':False,
                'context_snapshot_hex':expected.hex(),'source_wire_after_hex':bytes(changed).hex(),
                'queued_pointer':hex(OWNED),'queue_hex':first_queue.hex(),'events':events,
                'source_mutation_does_not_change_queued_context_copy':True,
                'actual_normal_serialization_or_request_completion_proven':False}
    # A second declared delivery tests buffer reuse before the downstream
    # busy-queue check. Whether the real task hook/producer can permit this
    # sequence is explicitly unproved; no Sony defect is inferred.
    raw2=wire(seed,20000000)
    events.extend(receive_prefix(m,raw2,REPLY2))
    e,expected2=copy_owned(m,raw2,REPLY2);events.append(e)
    assert m.read(QUEUE,0x20)==first_queue
    events.append(onward(m,expected2))
    events.append(m.phase('second original queue diagnostic prefix',0x17df50,fresh=False))
    assert events[-1]['reason']=='boundary: before_original_diagnostic'
    events.append(m.phase('second post-diagnostic queue check before busy logger',
                          0x17dfc4,[(QUEUE,QUEUE+0x20)],fresh=False))
    assert events[-1]['reason']=='boundary: before_original_logger_getter'
    assert m.read(QUEUE,0x20)==first_queue
    ptr=prev.u64(m.read(QUEUE+0x10,8))
    assert ptr==OWNED and m.read(ptr,0x4c)==expected2
    return {'seed':seed,'declared_numeric_state':state,'second_receive_fixture':True,
            'first_snapshot_hex':expected.hex(),'second_snapshot_hex':expected2.hex(),
            'queue_before_and_after_second_hex':first_queue.hex(),'queued_pointer':hex(ptr),
            'target_now_at_same_queued_pointer':prev.u32(expected2,8),
            'reply_word_now_at_same_queued_pointer':prev.u32(expected2,0x48),
            'events':events,'actual_second_delivery_eligibility_race_or_defect_proven':False}


def mid_control(blob,seed,mid):
    m,events=setup(blob,seed,3)
    before=m.read(OWNED,0x4c)
    raw=wire(seed,mid=mid)
    events.extend(receive_prefix(m,raw,REPLY1))
    assert m.read(OWNED,0x4c)==before
    assert hex(V+0x177d98) not in events[-1]['pcs']
    return {'seed':seed,'MID_fixture':hex(mid),'events':events,
            'context_snapshot_unchanged_before_selected_diagnostic':True,
            'whole_command_acceptance_proven':False}


def upstream_converter():
    # Existing pinned ELF reader and pure original-code emulator; no logging
    # adapter, patches, imported return or host native execution is used.
    av=r.d.AV
    assert sha(av.blob)=='87a2246084567abca0e43228b5289bc728839a13ab4251e92828ea4c463e3c26'
    symname='_ZN11ObjAvbbcCmn17ConvertCmdMidToMcEt'
    tablesym='_ZN16ObjAvbbcCmnTable16midConvTableToMcE'
    assert av.symbols[symname]=={'va':0x140eac,'size':64}
    assert av.symbols[tablesym]=={'va':0x16aff8,'size':176}
    section=av.elf.get_section_by_name('.rela.dyn')
    rel=next(x for x in section.iter_relocations() if x['r_offset']==0x1b2678)
    symbol=av.elf.get_section(section['sh_link']).get_symbol(rel['r_info_sym'])
    assert rel['r_info_type']==1025 and rel['r_addend']==0 and symbol.name==tablesym
    rows=[]
    for n in range(44):
        a,b=struct.unpack('<HH',av.read(0x16aff8+n*4,4))
        rows.append({'index':n,'input':a,'output':b})
    assert rows[-1]['input']==rows[-1]['output']==0xffff
    assert not any(x['output']==0x10a for x in rows)
    probes=[]
    for raw,expected in ((0x520,0x201),(0x529,0x107),(0x530,0x108),(0x531,0x109),
                         (0x532,0xffff),(0x10a,0xffff),(0x50a,0),(0x10529,0x107)):
        m=r.d.pp.StrictMicro(av,[(0x140eac,0x140eec)],resolve=True)
        slot=bytes(m.uc.mem_read(0x1b2678,8))
        assert struct.unpack('<Q',slot)[0]==0x16aff8
        original_table=bytes(m.uc.mem_read(0x16aff8,176))
        event=m.run(0x140eac,[0,raw])
        assert event['reason']=='returned' and not event['stores']
        value=m.uc.reg_read(r.reg.UC_ARM64_REG_X0)
        assert value==expected
        assert bytes(m.uc.mem_read(0x16aff8,176))==original_table
        assert bytes(m.uc.mem_read(0x1b2678,8))==slot
        probes.append({'input_fixture':raw,'observed_output':value,'event':event,
                       'original_table_and_resolved_slot_unchanged':True})
    return {'original_ELF_sha256':sha(av.blob),'function_symbol':symname,
            'function_VA':'0x140eac','table_symbol':tablesym,'table_VA':'0x16aff8',
            'original_symbol_bytes':176,'relocation_slot':'0x1b2678',
            'relocation_type':1025,'rows_including_terminator':rows,'probes':probes,
            'scope':'This original table with local defined-symbol relocation has no0x10a result. No claim about all firmware APIs, symbol interposition, other libraries, direct MC paths or live producer policy.',
            'natural_MAIN_16M_request_producer_proven':False}


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',required=True)
    out=Path(parser.parse_args().output).resolve()
    im.volume();assert out.parent==STAGE and not out.exists()
    assert sha(PRIOR.read_bytes())==PRIOR_SHA
    for f in json.loads(PRIOR.read_text())['files']:
        b=(ROOT/f['path']).read_bytes();assert len(b)==f['bytes'] and sha(b)==f['sha256']
    assert (STAGE/'goal-status-before.json').read_bytes()==(BASE/'GOAL_STATUS.json').read_bytes()
    blob=prev.IMAGE.read_bytes();assert sha(blob)==prev.IMAGE_SHA
    out.mkdir();(out/'executed-source.py').write_bytes(Path(__file__).read_bytes())
    try:
        routes=[route(blob,seed,state,second) for seed in (0xa5,0xc3)
                for state,second in ((3,False),(1,False),(1,True))]
        controls=[mid_control(blob,seed,mid) for seed in (0xa5,0xc3) for mid in (0x107,0x108,0x109)]
        upstream=upstream_converter()
        result={'status':'PASS_NATIVE_MID_DEMUX_CONTEXT_QOS_SNAPSHOT_AND_DECLARED_BUFFER_REUSE_SCOPE',
            'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'original_image_sha256':sha(blob),'previous_manifest_sha256':PRIOR_SHA,
            'routes':routes,'MID_controls':controls,'upstream_converter':upstream,
            'bounded_phases':sum(len(c['events']) for c in routes+controls)+len(upstream['probes']),
            'scope':'Original receive prologue/MID demux/48-byte snapshot+reply word; task-hook lookup/call, diagnostics and parameter dump are explicit unexecuted gaps. Caller graph/back state/source wire are fixtures. Native copied context request reaches ROM action and independent lower envelope or queue; second input reuse is not real scheduling proof.',
            'natural_MAIN_16M_policy_complete_receive_Hal_or_recovery_proven':False,
            'Windows_UU_camera_operations':False,'goal_complete':False,'persistent_write_release':False}
        (out/'receive-snapshot-results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
        print(json.dumps({'status':result['status'],'routes':len(routes),'MID_controls':len(controls),'converter_probes':len(upstream['probes']),
                          'phases':result['bounded_phases'],'output':str(out)}))
    except Exception:
        (out/'attempt-failure.json').write_text(json.dumps({'traceback':traceback.format_exc(),'passing_result':False},indent=2)+'\n')
        raise


if __name__=='__main__':main()
