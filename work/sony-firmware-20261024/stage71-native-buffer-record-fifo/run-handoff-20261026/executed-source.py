#!/usr/bin/env python3
"""Independent original handoff tail, explicitly not a completed target request."""
from pathlib import Path
import argparse
import datetime
import json
import struct
import sys
import traceback
import buffer_record_fifo as q

STAGE=q.STAGE
c,r,im,V,n,f=q.c,q.r,q.im,q.V,q.n,q.f
BASE,ROOT=q.BASE,q.ROOT
COMMON=c.COMMON
STOP=V+0x21ef60


def one_case(assets,modules,providers,adapter,seed):
    m,events=q.linked(assets,modules,providers,adapter)
    global CURRENT_GUEST
    CURRENT_GUEST=m
    m.ranges.extend([(q.POP,V+0x22db34),(V+0x21ef30,STOP)])
    m.boundaries[STOP]='after_original_record_handoff_and12byte_clear_before_flag_branch'
    m.uc.mem_write(q.MANAGER,bytes([seed])*f.last.MANAGER_SIZE)
    e=c.phase(m,'original manager constructor for independent handoff',V+0x22cc8c,x0=q.MANAGER)
    assert e['reason']=='returned';events.append(e)
    m.uc.mem_write(COMMON,bytes([seed])*0xe518)
    e=c.phase(m,'original common constructor for independent handoff',V+0x21d9e0,x0=COMMON)
    assert e['reason']=='returned';events.append(e)
    e=c.phase(m,'original manager setter on explicitly constructed common',V+0x22c99c,x0=COMMON,x1=q.MANAGER)
    assert e['reason']=='returned';events.append(e)
    pointer=seed*0x0101010101010101
    raw_second=((seed*0x01010101)<<32)|0x12345678
    record=(pointer,raw_second)
    m.uc.mem_write(q.OUTPUT,b'\x5a'*128)
    cache_values=(0x2222333344445555,0x6666777788889999)
    m.uc.mem_write(q.OUTPUT+0x48,struct.pack('<2Q',*cache_values))
    writes=[];allowed=[(q.Q,q.Q+q.Q_USED),(COMMON+0x1040,COMMON+0x1050),
                      (COMMON+0xddc0,COMMON+0xddd0),(q.OUTPUT,q.OUTPUT+128),
                      (r.STACK,r.STACK+r.STACK_SIZE)]
    def observe(u,access,a,size,value,user):
        assert any(lo<=a and a+size<=hi for lo,hi in allowed),(hex(a),size)
        writes.append({'pc':hex(u.reg_read(r.reg.UC_ARM64_REG_PC)),'address':hex(a),'bytes':size})
    hook=m.uc.hook_add(r.unicorn.UC_HOOK_MEM_WRITE,observe)
    e=c.phase(m,'original enqueue declared numeric record for independent handoff',q.PUSH,
              x0=q.MANAGER,x1=pointer,x2=raw_second)
    assert e['reason']=='returned' and m.uc.reg_read(r.reg.UC_ARM64_REG_X0)==0;events.append(e)
    e=c.phase(m,'original dequeue copies both raw words into common1040',q.POP,
              x0=q.MANAGER,x1=COMMON+0x1040)
    assert e['reason']=='returned' and m.uc.reg_read(r.reg.UC_ARM64_REG_X0)==0;events.append(e)
    assert m.read(COMMON+0x1040,16)==struct.pack('<2Q',*record) and q.state(m)['count']==0
    before_common=m.read(COMMON,0xe518);before_output=m.read(q.OUTPUT,128)
    e=c.phase(m,'independent original copy-to-output and partial clear tail',V+0x21ef30,x19=COMMON,x20=q.OUTPUT)
    events.append(e);assert e['reason']=='boundary: after_original_record_handoff_and12byte_clear_before_flag_branch'
    after_common=m.read(COMMON,0xe518);after_output=m.read(q.OUTPUT,128)
    expected_common=bytearray(before_common);expected_common[0x1040:0x104c]=bytes(12)
    expected_common[0xddc0:0xddd0]=struct.pack('<2Q',*cache_values)
    expected_output=bytearray(before_output)
    expected_output[0x58:0x60]=struct.pack('<Q',pointer)
    expected_output[0x60:0x64]=struct.pack('<I',raw_second&0xffffffff)
    assert after_common==bytes(expected_common) and after_output==bytes(expected_output)
    assert after_common[0x104c:0x1050]==before_common[0x104c:0x1050]==struct.pack('<I',raw_second>>32)
    assert struct.unpack_from('<Q',after_output,0x58)[0]==pointer
    assert q.state(m)['count']==0
    m.uc.hook_del(hook)
    q.prior.assert_images(m)
    assert not m.module_alloc_entries and not m.kernel_service_entries and not m.message_entries
    return {'seed':seed,'declared_numeric_record':[hex(x) for x in record],
            'record_origin_is_fixture_not_a_trusted_allocated_buffer':True,
            'before_common16_hex':before_common[0x1040:0x1050].hex(),
            'after_common16_hex':after_common[0x1040:0x1050].hex(),
            'after_output_pointer':hex(struct.unpack_from('<Q',after_output,0x58)[0]),
            'after_output_second_low32':hex(struct.unpack_from('<I',after_output,0x60)[0]),
            'common_upper32_retained_hex':after_common[0x104c:0x1050].hex(),
            'output_full128_hex':after_output.hex(),'queue_state':q.state(m),'actual_stores':writes,'events':events,
            'only_declared_common_and_output_fields_changed':True,'standalone_tail_entry':True,
            'original_channel_allocation_return_or_later_flag_branch_executed':False,
            'actual_output_consumer_completion_or_pointer_referent_access':False}


def run(out):
    assert (BASE/'GOAL_STATUS.json').read_bytes()==(STAGE/'goal-status-before.json').read_bytes()
    modules,providers,kernel=c.d.link.build()
    matchobj=f.f58.STAGE/'run-post-loader-patch-20261026/match_adapter.a64.o'
    code,ro,_=f.f58.object_image(matchobj.read_bytes())
    wcode,wro,functions,_=c.old.object_image((c.old.STAGE/'run-bounded-stores-20261026/resource_alias.a64.o').read_bytes())
    blob=(BASE/'stage2/extraction/files/nflasha3/av-cam.bin').read_bytes();assert im.sha(blob)==im.PINS['stage2/extraction/files/nflasha3/av-cam.bin']
    liro=(n.STAGE/'official-files/nflasha15/kmod/liro.ko').read_bytes()
    adapter=c.object_image((c.STAGE/'run-same-instance-slices-20261026/channel_adapter.a64.o').read_bytes())
    assets=blob,liro,kernel,code,ro,wcode,wro,functions
    cases=[one_case(assets,modules,providers,adapter,seed) for seed in (0xa5,0xc3)]
    result={'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'status':'PASS_INDEPENDENT_ORIGINAL_HANDOFF_OUTPUT_RETAINED_COMMON12_CLEARED',
            'cases':cases,'bounded_fragments':sum(len(x['events']) for x in cases),
            'original_tail_instructions':im.dump(blob,0x21ef30,0x21ef60,V),
            'source_receipt':{'script_sha256':im.sha(Path(__file__).read_bytes()),
                              'queue_helper_sha256':im.sha((STAGE/'buffer_record_fifo.py').read_bytes()),
                              'runner_sha256':im.sha((c.STAGE/'channel_callpath.py').read_bytes()),
                              'avcam_sha256':im.sha(blob),'LIRO_sha256':im.sha(liro),'kernel_sha256':im.sha(kernel)},
            'conclusions':['Queue emptiness and a cleared COMMON pointer do not remove the copied output pointer in this bounded execution.',
                           'Only the low32 bits of the second raw queue word are copied/cleared on this path; upper32 semantics are not assigned.',
                           'This standalone tail does not execute the earlier channel allocator, later flag branch, caller/consumer, hardware or restoration.',
                           'Target static row386 has flag0. This independent record-input experiment is not proof that the target takes the flag1 dequeue path.'],
            'Mac_offline_only':True,'actual_ownership_or_full_Close_or_recovery_verified':False,
            'goal_complete':False,'persistent_write_release':False}
    im.write_json(out/'handoff-tail-results.json',result)
    (out/'executed-source.py').write_bytes(Path(__file__).read_bytes())
    print(json.dumps({'status':result['status'],'cases':2,'bounded_fragments':result['bounded_fragments'],
                      'common_bytes_cleared':12,'output_pointer_retained':True,'actual_ownership_verified':False}))


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--output',required=True);args=ap.parse_args()
    im.volume();out=Path(args.output).resolve();assert STAGE in out.parents and not out.exists();out.mkdir()
    try:run(out)
    except Exception:
        (out/'attempt-source.py').write_bytes(Path(__file__).read_bytes())
        im.write_json(out/'attempt-failure.json',{'traceback':traceback.format_exc(),'passing_result':False})
        raise


if __name__=='__main__':main()
