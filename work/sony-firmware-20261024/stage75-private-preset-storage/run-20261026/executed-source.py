#!/usr/bin/env python3
"""Separate guest-only candidate storage from a proven original workspace.

The designated arena slot is a harness contract for one fixed controller, not
an actual camera allocation, ELF load address or shared synchronization proof.
"""
from pathlib import Path
import argparse
import datetime
import json
import struct
import subprocess
import sys
import traceback

STAGE=Path(__file__).resolve().parent
sys.path.insert(0,str(STAGE.parent/'stage74-rate-result-ABI-fix'))
import rate_abi_fix as t
c,r,im,V,n,f=t.c,t.r,t.im,t.V,t.n,t.f
BASE,ROOT=t.BASE,t.ROOT
sys.path.insert(0,str(BASE/'stage71-native-buffer-record-fifo'))
import buffer_record_fifo as q
PRIVATE=c.old.CONTROL+0x1000
NATIVE_WORKSPACE=c.COMMON+0xe010
GUARD=64


class StorageGuest(t.ABIWatchGuest):
    def __init__(self,*a):
        super().__init__(*a)
        self.prototype_limits=[(c.old.CONTROL,296),(PRIVATE,256),(c.COMMON+0xe000,8),
                               (r.STACK,r.STACK_SIZE)]


def linked(assets,modules,providers,adapter):
    m=StorageGuest(assets,modules,providers,adapter)
    m.compiled_layout=t.layout(adapter);m.result_container_size=56
    events=[n.link(m)]
    for row in m.import_bindings:
        assert m.read(int(row['actual_avcam_slot'],16),8)==r.p64(int(row['original_module_target'],16))
    m.uc.mem_write(f.f58.SITE,m.patch);m.uc.mem_write(c.SITE,m.adapter_patch)
    m.uc.mem_protect(V,4096,r.unicorn.UC_PROT_READ|r.unicorn.UC_PROT_EXEC)
    m.expected_data={f.f59.GUARD:1,f.f59.MUTE:0,f.f59.CAT1:1,f.f59.CAT2:1}
    for at,value in m.expected_data.items():assert m.blob[at-V]==0;m.uc.mem_write(at,bytes([value]))
    m.uc.mem_protect(f.f59.MUTE&-4096,4096,r.unicorn.UC_PROT_READ|r.unicorn.UC_PROT_WRITE)
    e=c.phase(m,'original mute setter for dedicated guest storage',V+0x27d898,x0=f.f59.LOG,x1=1)
    assert e['reason']=='returned';events.append(e);m.expected_data[f.f59.MUTE]=1
    lo=f.G&-4096;hi=(f.G+f.GSIZE+4095)&-4096
    m.uc.mem_protect(lo,hi-lo,r.unicorn.UC_PROT_READ|r.unicorn.UC_PROT_WRITE)
    m.boundaries[m.rate_return_pcs[0]]='after_original_rate_query_with_dedicated_guest_preset'
    return m,events


def target(assets,modules,providers,adapter,seed,descriptor):
    m,events=linked(assets,modules,providers,adapter)
    global CURRENT_GUEST
    CURRENT_GUEST=m
    c.prepare(m,events,descriptor,seed,None)
    assert PRIVATE==0x113a1000
    assert PRIVATE>=f.last.FACTORY+f.last.FACTORY_SIZE and PRIVATE>=c.old.CONTROL+296
    before=m.read(NATIVE_WORKSPACE,256)
    other=c.COMMON+0xe518;other_before=m.read(other,0xe518)
    m.uc.mem_write(PRIVATE-GUARD,bytes([seed])*(256+2*GUARD))
    guard_before=m.read(PRIVATE-GUARD,256+2*GUARD)
    e=c.phase(m,'same original queued FH request publishes to dedicated guest buffer',V+0x22f34c,x0=f.last.CTX)
    events.append(e);assert e['reason']=='boundary: after_original_rate_query_with_dedicated_guest_preset'
    assert m.real_returns[0]['W0']==386
    assert m.read(c.COMMON+0xe000,8)==r.p64(PRIVATE)
    original=m.blob[0x3c5798:0x3c5898];private=m.read(PRIVATE,256)
    assert [i for i,(a,b) in enumerate(zip(original,private)) if a!=b]==[0xb0,0xb1,0xb2]
    query=m.query_proof;assert query and query['saved_LR_unchanged'] and query['full_frame_outside_container_unchanged']
    assert not query['stores_outside_declared_container']
    assert query['decoded_trace_target_CPB']==[25999360,16000000,26000000]
    pc=m.rate_return_pcs[0];m.boundaries.pop(pc)
    e=c.phase(m,'same corrected adapter forwards original channel arguments',pc,independent=False)
    events.append(e);assert e['reason']=='boundary: before_original_buffer_channel_preparation'
    assert m.admitted_channel_entries[0]['x0_x3']==m.adapter_entries[0]['x0_x3']
    m.boundaries.pop(c.SONY['sony_channel'])
    e=c.phase(m,'same original channel request from dedicated guest preset to kernel boundary',c.SONY['sony_channel'],independent=False)
    events.append(e);assert e['reason']=='boundary: before_original_unexecuted_kernel_service'
    assert m.kernel_service_entries[0]['names']==['_raw_spin_lock_irqsave']
    assert m.read(NATIVE_WORKSPACE,256)==before
    assert m.read(other,0xe518)==other_before
    guard_after=m.read(PRIVATE-GUARD,256+2*GUARD)
    assert guard_after[:GUARD]==guard_before[:GUARD] and guard_after[-GUARD:]==guard_before[-GUARD:]
    assert m.read(c.COMMON+0xe110,136)==descriptor
    assert c.old.control(m)['live']==c.old.control(m)['phase']==1
    assert any(PRIVATE<=int(w['address'],16)<PRIVATE+256 for w in m.prototype_stores)
    assert not any(NATIVE_WORKSPACE<=int(w['address'],16)<NATIVE_WORKSPACE+256 for w in m.prototype_stores)
    c.assert_images(m)
    return {'seed':seed,'events':events,'dedicated_guest_buffer':hex(PRIVATE),'private256_hex':private.hex(),
        'original_common_workspace_before_hex':before.hex(),'original_common_workspace_after_hex':m.read(NATIVE_WORKSPACE,256).hex(),
        'original_common_workspace_untouched':True,'entire_other_common_unchanged':True,
        'guards_before_hex':guard_before.hex(),'guards_after_hex':guard_after.hex(),
        'compiled_writer_stores':m.prototype_stores,'original_query_frame_proof':query,
        'channel_entry_observations':m.admitted_channel_entries,'resource_messages':m.message_entries,
        'kernel_service_boundary':m.kernel_service_entries,'control_at_stop':c.old.control(m),
        'real_camera_owned_allocation_shared_lock_consumers_or_recording':False}


def native_workspace(assets,modules,providers,adapter,seed,descriptor):
    m,events=q.linked(assets,modules,providers,adapter)
    global CURRENT_GUEST
    CURRENT_GUEST=m
    m.ranges.extend([(V+0x226364,V+0x2265e4),(V+0x27da84,V+0x27da88)])
    m.uc.mem_write(c.COMMON,bytes([seed])*0xe518)
    e=c.phase(m,'independent original common constructor for native workspace usage',V+0x21d9e0,x0=c.COMMON)
    assert e['reason']=='returned';events.append(e)
    m.uc.mem_write(c.COMMON+0xe110,descriptor)
    m.uc.mem_write(PRIVATE-GUARD,bytes([seed])*(256+2*GUARD))
    external_before=m.read(PRIVATE-GUARD,256+2*GUARD)
    metadata_before=m.read(c.old.CONTROL,296)
    before=m.read(c.COMMON,0xe518);arena_before=m.read(r.ARENA,r.ARENA_SIZE)
    stores=[]
    allowed=[(c.COMMON+0xdff8,c.COMMON+0xe010),(NATIVE_WORKSPACE,NATIVE_WORKSPACE+256),
             (c.COMMON+0xe458,c.COMMON+0xe45c),(r.STACK,r.STACK+r.STACK_SIZE)]
    def observe(u,access,address,size,value,user):
        assert any(a<=address and address+size<=z for a,z in allowed),(hex(address),size)
        stores.append({'pc':hex(u.reg_read(r.reg.UC_ARM64_REG_PC)),'address':hex(address),'bytes':size})
    hook=m.uc.hook_add(r.unicorn.UC_HOOK_MEM_WRITE,observe)
    e=c.phase(m,'independent native create-start-param entry with declared type2',V+0x226364,
              sp=r.STACK+0x2000,x0=c.COMMON,x1=0,x2=0,x3=2)
    events.append(e);assert e['reason']=='returned',e['reason'];m.uc.hook_del(hook)
    after=m.read(c.COMMON,0xe518);arena_after=m.read(r.ARENA,r.ARENA_SIZE)
    assert before[0xe010:0xe110]!=after[0xe010:0xe110]
    assert m.read(c.COMMON+0xe000,8)==r.p64(NATIVE_WORKSPACE)
    assert m.read(c.COMMON+0xe110,136)==descriptor
    assert m.read(PRIVATE-GUARD,256+2*GUARD)==external_before
    assert m.read(c.old.CONTROL,296)==metadata_before
    a=c.COMMON-r.ARENA;z=a+0xe518
    assert arena_before[:a]==arena_after[:a] and arena_before[z:]==arena_after[z:]
    changed=[i for i,(a,b) in enumerate(zip(before,after)) if a!=b]
    assert all(any(a-c.COMMON<=i<z-c.COMMON for a,z in allowed[:-1]) for i in changed)
    assert not m.kernel_service_entries and not m.message_entries and not m.module_alloc_entries
    q.prior.assert_images(m)
    return {'seed':seed,'events':events,'original_workspace_before_hex':before[0xe010:0xe110].hex(),
        'original_workspace_after_hex':after[0xe010:0xe110].hex(),'original_selected_pointer':hex(NATIVE_WORKSPACE),
        'actual_native_stores':stores,'changed_COMMON_offsets':changed,
        'dedicated_guest_buffer_and_controller_unchanged':True,'source_descriptor_unchanged':True,
        'native_original_callsite':hex(V+0x21ebb8),'independent_entry_not_target_natural_path':True,
        'runtime_concurrency_mutual_exclusion_or_actual_target_mode_interference_proven':False}


def run(out):
    prior=t.STAGE/'final-receipt.json';assert im.sha(prior.read_bytes())=='97807cfbfd33a2cedb88a71e579dec44b4b40264e66fdb63ab39502e91621a13'
    for x in json.loads(prior.read_text())['files']:assert im.sha((ROOT/x['path']).read_bytes())==x['sha256']
    assert (BASE/'GOAL_STATUS.json').read_bytes()==(STAGE/'goal-status-before.json').read_bytes()
    compiles=[]
    for source in ('resource_alias','channel_adapter'):
        cmd=['/usr/bin/clang',*c.old.old.FLAGS,'-c',str(STAGE/(source+'.c')),'-o',str(out/(source+'.a64.o'))]
        done=subprocess.run(cmd,capture_output=True,text=True)
        compiles.append({'command':cmd,'returncode':done.returncode,'stdout':done.stdout,'stderr':done.stderr})
        assert done.returncode==0 and not done.stderr
    im.write_json(out/'compile-receipts.json',compiles)
    adapter=c.object_image((out/'channel_adapter.a64.o').read_bytes())
    modules,providers,kernel=c.d.link.build()
    code,ro,_=f.f58.object_image((f.f58.STAGE/'run-post-loader-patch-20261026/match_adapter.a64.o').read_bytes())
    wcode,wro,functions,_=c.old.object_image((out/'resource_alias.a64.o').read_bytes())
    assert functions['fx3_candidate']==c.old.CODE
    blob=(BASE/'stage2/extraction/files/nflasha3/av-cam.bin').read_bytes();assert im.sha(blob)==im.PINS['stage2/extraction/files/nflasha3/av-cam.bin']
    liro=(n.STAGE/'official-files/nflasha15/kmod/liro.ko').read_bytes()
    assets=blob,liro,kernel,code,ro,wcode,wro,functions;inputs=c.d.p.inputs();descriptor=inputs[0][1]
    targets=[target(assets,modules,providers,adapter,seed,descriptor) for seed in (0xa5,0xc3)]
    native=[native_workspace(assets,modules,providers,adapter,seed,descriptor) for seed in (0xa5,0xc3)]
    controls=[c.one_case(assets,modules,providers,adapter,'UHD dedicated-buffer regression',inputs[3][1],0xc3,431),
              c.one_case(assets,modules,providers,adapter,'closed gate dedicated-buffer regression',descriptor,0xc3,386,True,'closed')]
    result={'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'status':'PASS_NATIVE_WORKSPACE_IDENTIFIED_GUEST_PRESET_STORAGE_SEPARATED',
        'targets':targets,'independent_native_workspace_cases':native,'regression_controls':controls,
        'bounded_fragments':sum(len(x['events']) for x in targets+native+controls),
        'original_regions':[{'start':hex(a),'end':hex(z),'instructions':im.dump(blob,a,z,V)} for a,z in
            [(0x226364,0x2265e4),(0x21eb84,0x21ebc0),(0x21dc10,0x21dc48),(0x27da84,0x27da88)]],
        'source_receipt':{'script_sha256':im.sha(Path(__file__).read_bytes()),
            'new_writer_source_sha256':im.sha((STAGE/'resource_alias.c').read_bytes()),
            'fixed56_adapter_source_sha256':im.sha((STAGE/'channel_adapter.c').read_bytes()),
            'new_writer_object_sha256':im.sha((out/'resource_alias.a64.o').read_bytes()),
            'adapter_object_sha256':im.sha((out/'channel_adapter.a64.o').read_bytes()),
            'rate_ABI_observer_sha256':im.sha((t.STAGE/'rate_abi_fix.py').read_bytes()),
            'avcam_sha256':im.sha(blob),'LIRO_sha256':im.sha(liro),'kernel_sha256':im.sha(kernel)},
        'scope':['COMMONe010..e10f is used by an original create-start-param path, not established exclusive scratch for our code.',
            'Independent original entry proves native use, not that current target naturally enters it or collides at runtime.',
            'Dedicated guest slot113a1000 is restricted to one fixed controller113a0000; not an actual allocator or camera physical address.',
            'Target56-byte result container retained; original workspace, otherCOMMON and64-byte guards remain intact in bounded target path.',
            'No real allocation, shared lock, all-consumer completion, channel return, WBI, main recording or recovery is established.'],
        'Windows_UU_camera_operations':False,'goal_complete':False,'persistent_write_release':False}
    im.write_json(out/'private-storage-results.json',result)
    (out/'executed-source.py').write_bytes(Path(__file__).read_bytes())
    for name in ('resource_alias.c','channel_adapter.c'):(out/('compiled-'+name)).write_bytes((STAGE/name).read_bytes())
    print(json.dumps({'status':result['status'],'bounded_fragments':result['bounded_fragments'],
                      'targets':2,'native_workspace_cases':2,'controls':2,'real_allocation_proven':False}))


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--output',required=True);args=ap.parse_args()
    im.volume();out=Path(args.output).resolve();assert STAGE in out.parents and not out.exists();out.mkdir()
    try:run(out)
    except Exception:
        (out/'attempt-source.py').write_bytes(Path(__file__).read_bytes())
        im.write_json(out/'attempt-failure.json',{'traceback':traceback.format_exc(),'passing_result':False})
        if 'CURRENT_GUEST' in globals():
            m=CURRENT_GUEST;im.write_json(out/'failure-state.json',{'pc':hex(m.uc.reg_read(r.reg.UC_ARM64_REG_PC)),
                'reason':m.reason,'last_pcs':[hex(x) for x in m.pcs[-12:]]})
        raise


if __name__=='__main__':main()
