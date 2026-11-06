#!/usr/bin/env python3
"""Bounded original Open state-machine admission/queue evidence, guest only.

No transition hooks, Open action, diagnostic-output adapter, resources, transport,
hardware, host firmware loader, camera interface or persistent patch.
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
sys.path.insert(0,str(BASE/'stage26-mc-open-routing'))
import mc_open_routing as r
from capstone import Cs, CS_ARCH_ARM64, CS_MODE_ARM

V=r.V
HANDLE,SM,EVENT=(r.ARENA+n for n in (0x210000,0x220000,0x230000))
TABLE=0x36c4f8


class CaptureGuest(r.RawGuest):
    def __init__(self,*args,**kwargs):
        self.processor_returns=[]
        super().__init__(*args,**kwargs)

    def code(self,u,pc,size,user):
        if pc==V+0x17eb70:
            self.processor_returns.append(u.reg_read(r.reg.UC_ARM64_REG_X0))
        return super().code(u,pc,size,user)


def seed(m,packet,fmt,state=0,busy=0,pending=0,count=0,index=0):
    # This is an independent event fixture: known header/packet plus explicitly
    # untyped trailing bytes. It is not captured real state or a native output.
    header=r.seed(m,packet,fmt)
    event=bytearray(header[8:0x30])+bytearray(packet)+bytearray(range(0xa0,0xb8))
    assert len(event)==0xd8
    struct.pack_into('<Q',event,8,EVENT+0x28)
    m.uc.mem_write(EVENT,bytes(event));m.uc.mem_write(HANDLE,r.p64(SM))
    m.uc.mem_write(SM,r.p64(r.NORMAL))
    m.uc.mem_write(SM+8,struct.pack('<I',state));m.uc.mem_write(SM+0xc,bytes([busy]))
    m.uc.mem_write(SM+0x35c,bytes([pending]))
    m.uc.mem_write(SM+0xc28,struct.pack('<III',count,index,0))
    m.uc.mem_write(SM+0xc38,b'\xa5'*80)
    return bytes(event)


def processor_case(blob,label,packet,fmt,state=0,busy=0,pending=0,count=0,index=0):
    m=CaptureGuest(blob,[(0x17eb64,0x17edb0),(0x27da84,0x27da9c),(0xd80,0xeec),
        (0x184a2c,0x184a34),(0x184a4c,0x184a5c),(0x184a64,0x184a6c)],
        {0x184cc0:'before_state_exit_hook',0x184c34:'before_invalid_event_diagnostic',
         0x1849a0:'before_reentrant_event_diagnostic'})
    event=seed(m,packet,fmt,state,busy,pending,count,index)
    m.regs(x0=HANDLE,x1=EVENT)
    result=m.run(0x17eb64)
    queue=m.read(SM+0xc38,80)
    fields=struct.unpack('<III',m.read(SM+0xc28,12))
    if state in (0x15,0x16):
        assert result['reason']=='returned'
        assert m.processor_returns==[3 if state==0x15 else 4]
        assert m.uc.reg_read(r.reg.UC_ARM64_REG_X0)==0
        assert int.from_bytes(m.read(SM+8,4),'little')==0x16
    elif busy and pending:
        assert result['reason']=='boundary: before_reentrant_event_diagnostic'
        assert not m.processor_returns
    elif busy:
        assert result['reason']=='returned' and m.processor_returns==[1]
        assert m.uc.reg_read(r.reg.UC_ARM64_REG_X0)==0
        assert m.read(SM+0x368,0xd8)==event
        assert m.read(SM+0x35c,1)==b'\x01'
        if count==10:
            assert fields==(count,index,0) and queue==b'\xa5'*80
        else:
            assert fields==(count+1,(index+1)%10,0)
            assert struct.unpack_from('<Q',queue,index*8)[0]==SM+0x350
        # Original memcpy copies the embedded pointer unchanged, not rebased.
        assert int.from_bytes(m.read(SM+0x370,8),'little')==EVENT+0x28
    elif state==0:
        assert result['reason']=='boundary: before_state_exit_hook'
        assert m.uc.reg_read(r.reg.UC_ARM64_REG_X22)==1
    else:
        assert state==1 and result['reason']=='boundary: before_invalid_event_diagnostic'
        assert m.uc.reg_read(r.reg.UC_ARM64_REG_X22)==0x16
    assert m.read(EVENT,0xd8)==event
    result.update(label=label,explicit_input={'state_index':state,'busy':busy,
       'pending_event_flag':pending,'queue_count':count,'queue_write_index':index},
       raw_processor_returns=m.processor_returns,
       wrapper_zero_test_value=m.uc.reg_read(r.reg.UC_ARM64_REG_X0) if result['reason']=='returned' else None,
       queue_count_write_read_after=list(fields),
       event_copied_to_pending_storage=bool(busy and not pending and state not in (0x15,0x16)),
       embedded_pointer_rebased=False if busy and not pending and state not in (0x15,0x16) else None,
       input_event_unchanged=True,
       scope='Original numeric state/queue behavior on independent fixtures. Unknown hooks and action bodies stop before execution; no format or hardware acceptance.')
    return result


def action_selection(blob,label,packet,fmt):
    m=r.RawGuest(blob,[(0x17ecf8,0x17ed18),(0x184a34,0x184a4c)],
                 {0x17b794:'normal_owner_Open_virtual_dispatch_entry'})
    event=seed(m,packet,fmt,state=1)
    m.regs(x19=SM,x20=0,x21=EVENT,x22=1,x23=V+TABLE)
    result=m.run(0x17ecf8)
    assert result['reason']=='boundary: normal_owner_Open_virtual_dispatch_entry'
    assert m.uc.reg_read(r.reg.UC_ARM64_REG_X0)==r.NORMAL
    assert m.uc.reg_read(r.reg.UC_ARM64_REG_X1)==EVENT
    assert m.read(EVENT,0xd8)==event
    result.update(label=label,
       precondition='Independent post-transition fragment, old numeric state0/new1. Exit/entry hooks and state update were not executed or supplied as successful returns.',
       scope='Original table action selects owner callback entry only. Its interface virtual slot and actual Open action remain unexecuted.')
    return result


def diagnostic_audit(blob):
    md=Cs(CS_ARCH_ARM64,CS_MODE_ARM)
    results=[]
    for label,start,end in [('Open parameter dump',0x178aac,0x1798ec),
                            ('header dump helper',0x17e528,0x17e8b8)]:
        rows=list(md.disasm(blob[start:end],V+start));calls={};non_stack=[]
        assert sum(i.size for i in rows)==end-start
        for instruction in rows:
            if instruction.mnemonic=='bl':
                key=hex(int(instruction.op_str[1:],16)-V)
                calls[key]=calls.get(key,0)+1
            if instruction.mnemonic.startswith(('st','cas','swp')) and '[sp' not in instruction.op_str:
                non_stack.append({'offset':hex(instruction.address-V),'asm':instruction.mnemonic+' '+instruction.op_str})
        assert not non_stack
        assert set(calls)<={'0x27d528','0x27d568','0x17e528','0x17e8b8'}
        results.append({'name':label,'start':hex(start),'end_exclusive':hex(end),
          'instruction_count':len(rows),'call_counts':calls,'non_stack_store_instructions':non_stack})
    return {'functions':results,
      'caller_return_use':'After0x177b98 call, nonnull branch overwritesX0 at0x177ba4; null branch overwritesX0 at0x1786a8. No acceptance test of this return.',
      'scope':'Own-body static direct-call/store audit only; diagnostics not executed and no universal side-effect-free claim for logging backends.'}


def static_evidence(blob):
    regions=[('state-machine processor and zero-test wrapper',0x17eb64,0x17edb0),
      ('state0 guard/action/next and state1 next',0x184a2c,0x184a6c),
      ('normal owner Open virtual dispatch',0x17b794,0x17b7a4),
      ('original copy wrapper',0x27da84,0x27da9c),
      ('caller after dump through first address conversion',0x177b90,0x177bfc),
      ('caller FSM submission and subsequent acknowledgement',0x1786a8,0x178748)]
    table=[]
    for state in range(22):
        values=struct.unpack_from('<3Q',blob,TABLE+24*state)
        table.append({'state':state,'guard_action_next':[hex(v) for v in values]})
    assert table[0]['guard_action_next']==[hex(V+p) for p in (0x184a2c,0x184a34,0x184a4c)]
    return {'Open_state_table_offset':hex(TABLE),'Open_state_table':table,
       'regions':[{'name':n,'instructions':r.im.dump(blob,a,z,V)} for n,a,z in regions],
       'diagnostic_audit':diagnostic_audit(blob),
       'unresolved_action_interface':'0x17b794 loads owner+0x20, then its vtable+0x10. The live interface and target implementation are not bound by these guest fixtures.'}


def run(out):
    previous=BASE/'stage26-mc-open-routing/final-receipt.json'
    assert r.im.sha(previous.read_bytes())=='3885a86a39c712cf5b8e1bff81d2c61e5db925a7a98078da06028945b2b76858'
    assert all(r.im.sha((ROOT/f['path']).read_bytes())==f['sha256'] for f in json.loads(previous.read_text())['files'])
    receipt=json.loads((r.STAGE/'run-20261025/source-receipt.json').read_text())
    assert r.im.sha(Path(r.__file__).read_bytes())==receipt['script_sha256']
    blob=(BASE/'stage2/extraction/files/nflasha3/av-cam.bin').read_bytes()
    assert r.im.sha(blob)==r.im.PINS['stage2/extraction/files/nflasha3/av-cam.bin']
    variants=r.packet_variants();target,proxy,_,invalid=variants
    cases=[processor_case(blob,*v) for v in (target,proxy,invalid)]
    cases.extend(processor_case(blob,target[0]+' '+name,target[1],target[2],**args) for name,args in [
       ('state1',{'state':1}),('state0x15',{'state':0x15}),('state0x16',{'state':0x16}),
       ('busy queue empty',{'busy':1}),('busy queue wrap',{'busy':1,'count':9,'index':9}),
       ('busy queue full',{'busy':1,'count':10}),('busy pending already set',{'busy':1,'pending':1})])
    actions=[action_selection(blob,*v) for v in (target,invalid)]
    evidence=static_evidence(blob)
    proof={'status':'PASS_ORIGINAL_STATE_ADMISSION_QUEUE_AND_ACTION_SELECTION_ONLY',
      'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
      'state_processor_cases':cases,'independent_post_transition_action_cases':actions,
      'static_evidence':evidence,
      'findings':[
        '0x178aac own body and0x17e528 helper have only stack stores and diagnostic/name-lookup calls. Caller does not test their return as format acceptance. Actual next Open behavior is submitted through0x17eb64.',
        'Numeric state0 selects next1 and a constant-true guard, but original execution stops before transition hooks. Target/proxy/invalid video fields do not determine this local choice.',
        'Raw processor returns3(state0x15),4(state0x16) and1(deferred busy path) all become wrapper zero-test value0. These are not hardware Open result codes; queued busy and error-like states cannot be distinguished by this wrapper value alone.',
        'Busy/pending-clear copies0xd8 bytes before checking queue count10, sets pending flag, appends a functor only when count is not10 and wraps write index. Embedded parameter pointer remains pointed at original event storage, not the deferred copy.',
        'Independent post-transition action0 resolves to normal owner virtual dispatch0x17b794; live interface target, full action and resource/hardware replies remain unexecuted.'],
      'event_fixture_scope':'Known0x28 header and0x98 video packet plus synthetic untyped trailing0x18 bytes; not actual captured event/object state.',
      'scope':'Independent bounded original numeric-state/queue fragments, not complete Open, concurrent queue operation, safe-point/lifetime implementation or hardware acceptance.',
      'transition_hooks_actions_diagnostics_resources_transport_hardware_executed':False,
      'native_output_adapters':False,'camera_or_remote_access_attempted':False,
      'modified_firmware_or_patch_exported':False,'goal_complete':False,'persistent_write_release':False}
    summary={'status':proof['status'],'state_processor_cases':len(cases),
      'post_transition_action_selection_cases':len(actions),
      'diagnostic_function_bodies_audited':2,'deferred_copy_size':'0xd8',
      'deferred_embedded_pointer_rebased':False,'actual_hardware_acceptance_verified':False,
      'camera_or_remote_access_attempted':False,'goal_complete':False,'persistent_write_release':False}
    assert r.im.sha(blob)==r.im.sha((BASE/'stage2/extraction/files/nflasha3/av-cam.bin').read_bytes())
    r.im.write_json(out/'encoder-state-machine-results.json',proof);r.im.write_json(out/'summary.json',summary)
    r.im.write_json(out/'source-receipt.json',{'script':str(Path(__file__).relative_to(ROOT)),
      'script_sha256':r.im.sha(Path(__file__).read_bytes()),'raw_guest_harness_sha256':receipt['script_sha256'],
      'raw_image_sha256':r.im.sha(blob),'previous_manifest_sha256':r.im.sha(previous.read_bytes()),
      'packet_source_sha256':r.im.sha((BASE/'stage23-encoder-boundary/run-corrected-20261025/encoder-boundary-results.json').read_bytes()),
      'volume_uuid':r.im.VOLUME,'result_sha256':r.im.sha((out/'encoder-state-machine-results.json').read_bytes()),
      'summary_sha256':r.im.sha((out/'summary.json').read_bytes())})
    print(json.dumps(summary,ensure_ascii=False))


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',required=True)
    args=parser.parse_args();r.im.volume();out=Path(args.output).resolve()
    assert STAGE in out.parents and not out.exists();out.mkdir()
    try:run(out)
    except Exception:
        with (out/'attempt-source.py').open('xb') as f:f.write(Path(__file__).read_bytes())
        r.im.write_json(out/'attempt-failure.json',{'traceback':traceback.format_exc(),'passing_result':False});raise


if __name__=='__main__':main()
