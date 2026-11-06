#!/usr/bin/env python3
"""Original manager destructor branches on declared records, not physical free.

All code runs solely in a Mac-hosted Unicorn fixture. No hardware, transport
reply, code patch, or output/return replacement is used in these cases.
"""
from pathlib import Path
import argparse
import datetime
import json
import struct
import sys
import traceback

STAGE=Path(__file__).resolve().parent
sys.path.insert(0,str(STAGE.parent/'stage71-native-buffer-record-fifo'))
import buffer_record_fifo as q
c,r,im,V,n,f=q.c,q.r,q.im,q.V,q.n,q.f
BASE,ROOT=q.BASE,q.ROOT
M=q.MANAGER
DESC=M+0x209b8
CACHE=M+0x209f8
TEARDOWN=V+0x22db34
FREE=V+0x22dc28
UNIT=V+0x27c1a8
TRANSPORT=V+0x27bec8
WATCH={V+x for x in (0x22dc28,0x22e090,0x22e194,0x22dcac,
                    0x22dbb4,0x27c1a8,0x27c28c)}


def snapshot(m):
    raw=m.read(DESC,16)
    return {'master_descriptor_hex':raw.hex(),
            'master_pointer':hex(struct.unpack_from('<Q',raw)[0]),
            'master_low32':struct.unpack_from('<I',raw,8)[0],
            'master_ID':hex(struct.unpack_from('<I',raw,12)[0]),
            'first_cache32_hex':m.read(CACHE,32).hex(),
            'first_cache_ID':hex(struct.unpack('<I',m.read(M+0x20a0c,4))[0]),
            'first_cache_reference_count':struct.unpack('<I',m.read(M+0x20a10,4))[0],
            'queue':q.state(m)}


class TeardownGuest(q.QueueGuest):
    def __init__(self,*args):
        super().__init__(*args)
        self.destructor_observations=[]

    def code(self,u,pc,size,user):
        if pc in WATCH:
            rr=lambda i:u.reg_read(getattr(r.reg,'UC_ARM64_REG_X'+str(i)))
            self.destructor_observations.append({'pc':hex(pc),'LR':hex(rr(30)),
                'x0_x3':[hex(rr(i)) for i in range(4)],'state':snapshot(self)})
        return super().code(u,pc,size,user)


def linked(assets,modules,providers,adapter):
    m=TeardownGuest(assets,modules,providers,adapter);events=[n.link(m)]
    for row in m.import_bindings:
        assert m.read(int(row['actual_avcam_slot'],16),8)==r.p64(int(row['original_module_target'],16))
    assert sum(int.from_bytes(m.read(V+0x1ec+i*8,8),'little')!=0 for i in range(211))==5
    m.uc.mem_protect(V,4096,r.unicorn.UC_PROT_READ|r.unicorn.UC_PROT_EXEC)
    m.expected_data={f.f59.GUARD:1,f.f59.MUTE:0,f.f59.CAT1:1,f.f59.CAT2:1}
    for a,value in m.expected_data.items():
        assert m.blob[a-V]==0;m.uc.mem_write(a,bytes([value]))
    m.uc.mem_protect(f.f59.MUTE&-4096,4096,r.unicorn.UC_PROT_READ|r.unicorn.UC_PROT_WRITE)
    e=c.phase(m,'original mute setter for manager teardown',V+0x27d898,x0=f.f59.LOG,x1=1)
    assert e['reason']=='returned';events.append(e);m.expected_data[f.f59.MUTE]=1
    return m,events


def one_case(assets,modules,providers,adapter,seed,kind):
    m,events=linked(assets,modules,providers,adapter)
    global CURRENT_GUEST
    CURRENT_GUEST=m
    m.ranges.extend([(TEARDOWN,V+0x22dd38),(V+0x22e090,V+0x22e198),
                     (UNIT,V+0x27c2b4),(q.PUSH,V+0x22db34)])
    m.boundaries[TRANSPORT]='before_unexecuted_transport_no_reply_fabricated'
    m.uc.mem_write(M,bytes([seed])*f.last.MANAGER_SIZE)
    e=c.phase(m,'original manager constructor '+kind,V+0x22cc8c,x0=M)
    assert e['reason']=='returned';events.append(e)
    assert m.read(DESC,16)==struct.pack('<QII',0,0,0xffffffff)
    assert m.read(M+0x20a00,16)==struct.pack('<QII',0,0,0xffffffff)
    # One actual native-enqueued raw numeric record in all cases. Its referent
    # is deliberately unmapped; queue bookkeeping does not attest memory.
    pointer=seed*0x0101010101010101
    word2=((seed*0x01010101)<<32)|0x12345678
    e=c.phase(m,'original enqueue of one declared ROI numeric record '+kind,q.PUSH,
              x0=M,x1=pointer,x2=word2)
    assert e['reason']=='returned' and m.uc.reg_read(r.reg.UC_ARM64_REG_X0)==0;events.append(e)
    assert q.state(m)['count']==1
    # No claim these declared descriptor/cache combinations came from a
    # successful Sony allocation. Zero ID is explicitly a negative control.
    if kind=='sentinel_with_pending_record':
        pass
    elif kind=='zero_ID_negative_control':
        m.uc.mem_write(DESC,struct.pack('<QII',pointer,0x12345678,0))
    elif kind in ('shared_reference_two','last_reference_one_boundary'):
        handle=0x12345;refs=2 if kind=='shared_reference_two' else 1
        m.uc.mem_write(DESC,struct.pack('<QII',pointer,0x12345678,handle))
        # First cache entry: +8 pointer, +16 low word, +20 handle, +24 count.
        # Keep original constructor's other bytes, including unknown fields.
        m.uc.mem_write(M+0x20a00,struct.pack('<QIII',pointer,0x12345678,handle,refs))
        if refs==1:m.boundaries[UNIT]='before_original_unit_free_request_no_transport_executed'
    else:raise AssertionError(kind)
    before=snapshot(m);arena_before=m.read(r.ARENA,r.ARENA_SIZE)
    stores=[]
    allowed=[(DESC,DESC+16),(M+0x20a00,M+0x20a14),(r.STACK,r.STACK+r.STACK_SIZE)]
    def observe(u,access,a,size,value,user):
        assert any(lo<=a and a+size<=hi for lo,hi in allowed),(hex(a),size)
        stores.append({'pc':hex(u.reg_read(r.reg.UC_ARM64_REG_PC)),
                       'address':hex(a),'bytes':size,'value_low64':hex(value&((1<<64)-1))})
    hook=m.uc.hook_add(r.unicorn.UC_HOOK_MEM_WRITE,observe)
    e=c.phase(m,'original complete manager teardown or explicit pending-free boundary '+kind,TEARDOWN,x0=M)
    events.append(e)
    m.uc.hook_del(hook)
    after=snapshot(m);arena_after=m.read(r.ARENA,r.ARENA_SIZE)
    assert after['queue']==before['queue']
    assert m.read(q.Q+16,16)==struct.pack('<2Q',pointer,word2)
    expected=bytearray(arena_before)
    def replace(address,raw):expected[address-r.ARENA:address-r.ARENA+len(raw)]=raw
    pcs=[row['pc'] for row in m.destructor_observations]
    if kind=='sentinel_with_pending_record':
        assert not pcs
        assert e['reason']=='returned' and m.uc.reg_read(r.reg.UC_ARM64_REG_X0)==0
    elif kind=='zero_ID_negative_control':
        replace(DESC,struct.pack('<QII',0,0,0xffffffff))
        assert e['reason']=='returned' and m.uc.reg_read(r.reg.UC_ARM64_REG_X0)==0
        assert hex(UNIT) in pcs and hex(V+0x27c28c) in pcs
        unit=[x for x in m.destructor_observations if x['pc']==hex(UNIT)][0]
        packet=int(unit['x0_x3'][0],16)
        assert r.STACK<=packet and packet+0x98<=r.STACK+r.STACK_SIZE
        # Observations after original helper returns, before caller clears.
        returned=[x for x in m.destructor_observations if x['pc']==hex(V+0x22dbb4)][0]
        assert returned['x0_x3'][0]=='0x1'
        assert returned['state']['master_descriptor_hex']==before['master_descriptor_hex']
        assert m.read(packet,4)==bytes(4)
    elif kind=='shared_reference_two':
        replace(DESC,struct.pack('<QII',0,0,0xffffffff))
        replace(M+0x20a10,struct.pack('<I',1))
        assert e['reason']=='returned' and m.uc.reg_read(r.reg.UC_ARM64_REG_X0)==0
        assert hex(UNIT) not in pcs
        ref=[x for x in m.destructor_observations if x['pc']==hex(V+0x22e194)][0]
        assert ref['x0_x3'][0]=='0x1'
        assert after['first_cache_ID']=='0x12345' and after['first_cache_reference_count']==1
    else:
        replace(M+0x20a00,struct.pack('<QIII',0,0,0xffffffff,0))
        assert e['reason']=='boundary: before_original_unit_free_request_no_transport_executed'
        assert after['master_descriptor_hex']==before['master_descriptor_hex']
        assert after['first_cache_ID']=='0xffffffff' and after['first_cache_reference_count']==0
        unit=[x for x in m.destructor_observations if x['pc']==hex(UNIT)][0]
        packet=int(unit['x0_x3'][0],16)
        assert r.STACK<=packet and packet+0x98<=r.STACK+r.STACK_SIZE
        assert struct.unpack('<I',m.read(packet,4))[0]==0x12345
        assert m.read(packet+8,0x90)==bytes(0x90)
        assert unit['x0_x3'][1:3]==['0x2','0x806800f3']
    assert arena_after==bytes(expected)
    assert not m.kernel_service_entries and not m.message_entries and not m.module_alloc_entries
    q.prior.assert_images(m)
    assert not m.adapter_entries and not m.writer_entries
    logs=[x['format'] for x in m.all_logs]
    assert "didn't return all RIO_MAP queue elements qsize:%d" in logs
    if kind=='zero_ID_negative_control':
        assert 'free_unit error err:0x%X\n' in logs
        assert 'destroy mem pool error vcd_sw:%d' in logs
    return {'kind':kind,'seed':seed,'declared_ROI_words':[hex(pointer),hex(word2)],
            'descriptor_cache_inputs_are_declared_not_successful_allocation_evidence':True,
            'before':before,'after':after,'queue_not_drained_or_modified':True,
            'whole_arena_unchanged_except_explicit_descriptor_cache_fields':True,
            'events':events,'original_function_observations':m.destructor_observations,
            'original_logger_raw_calls':m.all_logs,'stores_during_teardown':stores,
            'actual_physical_free_transport_reply_or_record_referent_access':False}


def static_scope(blob):
    strings=[]
    for at,expected in [(0x43e5ad,'common/imola_common_mem_mgr.cpp'),
                        (0x43e882,'destroy mem pool error vcd_sw:%d'),
                        (0x43e992,'cannnot free dmm hdl:0x%08X'),
                        (0x43e99a,'free dmm hdl:0x%08X'),
                        (0x43e9ae,'free_unit error err:0x%X\n'),
                        (0x43ea27,'[MEMMGR    ]DMM Free(unit_type:0x%X unit_handle:0x%X ref_cnt %d->%d)'),
                        (0x43ea6c,'[MEMMGR    ]DMM Free(ref_cnt == 0)')]:
        raw=blob[at:blob.index(b'\0',at,at+200)];assert raw.decode('ascii')==expected
        strings.append({'offset':hex(at),'ASCII':expected,'sha256_including_NUL':im.sha(raw+b'\0')})
    return {'original_strings':strings,'regions':[{'start':hex(a),'end':hex(z),
                'instructions':im.dump(blob,a,z,V)} for a,z in
                [(0x22cd70,0x22ce7c),(0x22cec4,0x22cf34),(0x22db34,0x22dd38),
                 (0x22e090,0x22e198),(0x27c1a8,0x27c2b4),
                 (0x21e7a4,0x21e818),(0x21e9e0,0x21ea44),
                 (0x26adbc,0x26b138)]],
            'static_output_reference_lineage':{
                'COMMON1040_to_OUTPUT58':'stage71 original independent tail observed',
                'OUTPUT_stack_base':0x78,'original_x21_set_to_OUTPUT_plus18_at':'0x21e7b4',
                'copy_at21ea14':'original memcpy 0x50 bytes OUTPUT+0x18 to a new stack block; OUTPUT+0x58 appears at block+0x40',
                'callee26adbc':'stack argument at entrySP+0x10 points to this copied block',
                'callee_block40':'original code optionally translates address and overwrites block+0x40 at26b074',
                'request_copy_at26b0e4':'0x50-byte block copied to request+0x28; pointer-slot offset0x68, following low-word offset0x70',
                'request_submit_at26b0f0':'calls27470c; neither this call nor preceding synchronization executed in this stage',
                'scope':'Static correspondence only. No returned channel, successful main request, true address mapping, hardware consumer or completion proof.'}}


def run(out):
    assert (BASE/'GOAL_STATUS.json').read_bytes()==(STAGE/'goal-status-before.json').read_bytes()
    manifest=BASE/'stage71-native-buffer-record-fifo/final-receipt.json'
    assert im.sha(manifest.read_bytes())=='0418d0922bf7b2b6fd433009d01e6072ca20c894a114bb2378a4a71b1ebbf101'
    for row in json.loads(manifest.read_text())['files']:
        assert im.sha((ROOT/row['path']).read_bytes())==row['sha256']
    modules,providers,kernel=c.d.link.build()
    code,ro,_=f.f58.object_image((f.f58.STAGE/'run-post-loader-patch-20261026/match_adapter.a64.o').read_bytes())
    wcode,wro,functions,_=c.old.object_image((c.old.STAGE/'run-bounded-stores-20261026/resource_alias.a64.o').read_bytes())
    blob=(BASE/'stage2/extraction/files/nflasha3/av-cam.bin').read_bytes()
    assert im.sha(blob)==im.PINS['stage2/extraction/files/nflasha3/av-cam.bin']
    liro=(n.STAGE/'official-files/nflasha15/kmod/liro.ko').read_bytes()
    adapter=c.object_image((c.STAGE/'run-same-instance-slices-20261026/channel_adapter.a64.o').read_bytes())
    assets=blob,liro,kernel,code,ro,wcode,wro,functions
    kinds=('sentinel_with_pending_record','zero_ID_negative_control',
           'shared_reference_two','last_reference_one_boundary')
    cases=[one_case(assets,modules,providers,adapter,seed,kind) for seed in (0xa5,0xc3) for kind in kinds]
    result={'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'status':'PASS_ORIGINAL_MANAGER_LOCAL_EXIT_SCOPE_NOT_PHYSICAL_RELEASE',
            'cases':cases,'bounded_fragments':sum(len(x['events']) for x in cases),
            'static_scope':static_scope(blob),
            'source_receipt':{'script_sha256':im.sha(Path(__file__).read_bytes()),
                'original_queue_helper_sha256':im.sha((q.STAGE/'buffer_record_fifo.py').read_bytes()),
                'runner_sha256':im.sha((c.STAGE/'channel_callpath.py').read_bytes()),
                'avcam_sha256':im.sha(blob),'LIRO_sha256':im.sha(liro),'kernel_sha256':im.sha(kernel),
                'previous_manifest_sha256':im.sha(manifest.read_bytes())},
            'conclusions':['Original local manager exit logs a pending ROI record and leaves the queue unchanged in all declared cases.',
                'With no active master ID it returns0 without calling the free helper.',
                'Declared zero-ID negative control takes original unit-free rejection; helper returns1, caller logs error, clears master descriptor and still returns0.',
                'Declared cache reference2 is decremented to1; helper skips unit-free request, caller clears master descriptor and returns0. This does not imply a leak or bug.',
                'Declared last reference1 clears cached pointer/lowword/ID/count before reaching the original unit-free request entry. Stop before request body; master descriptor remains active at that boundary.',
                'No result establishes successful allocation, physical deallocation, consumers completed, hardware recording, WBI or independent rescue.'],
            'Windows_UU_camera_operations':False,'actual_main_recording_or_recovery':False,
            'goal_complete':False,'persistent_write_release':False}
    im.write_json(out/'manager-teardown-results.json',result)
    (out/'executed-source.py').write_bytes(Path(__file__).read_bytes())
    print(json.dumps({'status':result['status'],'cases':len(cases),
                      'bounded_fragments':result['bounded_fragments'],'physical_release_proven':False}))


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--output',required=True);args=ap.parse_args()
    im.volume();out=Path(args.output).resolve();assert STAGE in out.parents and not out.exists();out.mkdir()
    try:run(out)
    except Exception:
        (out/'attempt-source.py').write_bytes(Path(__file__).read_bytes())
        im.write_json(out/'attempt-failure.json',{'traceback':traceback.format_exc(),'passing_result':False})
        if 'CURRENT_GUEST' in globals():
            m=CURRENT_GUEST
            im.write_json(out/'failure-state.json',{'pc':hex(m.uc.reg_read(r.reg.UC_ARM64_REG_PC)),
                'reason':m.reason,'last_pcs':[hex(x) for x in m.pcs[-12:]],
                'state':snapshot(m),'original_function_observations':m.destructor_observations})
        raise


if __name__=='__main__':main()
