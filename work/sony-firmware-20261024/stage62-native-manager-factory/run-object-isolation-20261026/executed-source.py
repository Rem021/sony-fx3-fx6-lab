#!/usr/bin/env python3
"""Native manager/factory constructors and free queues in bounded RAM.

No OS singleton, task startup, real allocator return, camera or persistent I/O.
The external queued request/header and initialized muted logger remain fixtures.
"""
from pathlib import Path
import argparse
import datetime
import json
import struct
import sys
import traceback

STAGE=Path(__file__).resolve().parent
BASE=STAGE.parent
ROOT=BASE.parents[1]
sys.path.insert(0,str(BASE/'stage61-native-row-channel'))
import row_channel as prev
r,im,V,n,p=prev.r,prev.im,prev.V,prev.n,prev.p
MANAGER=r.ARENA+0x20000
MANAGER_SIZE=0x20a70
CTX=p.CTX
FACTORY=CTX+0x390
FACTORY_SIZE=0xa34b0
MESSAGE=r.ARENA+0x300000
IDENTITY=r.ARENA+0x310000
COMMON=FACTORY+0x40
HANDLER=COMMON-8
PRIOR_SHA='459907b4abbd2324a3ee068a45666982ffc66191544dcded9d4f3775d45db7b1'
EXTRA=[(0x22cc8c,0x22ce7c),(0x226d2c,0x226ee0),(0x226fb4,0x22704c),
  (0x2270d4,0x227578),(0x22c99c,0x22c9a4),
  (0x2186dc,0x2189bc),(0x2189dc,0x218a48),(0x21cd10,0x21cec0),
  (0x22d394,0x22d5cc),(0x22de54,0x22e044)]


class Guest(prev.Guest):
    def __init__(self,*assets):
        super().__init__(*assets)
        self.ranges.extend((V+a,V+z) for a,z in EXTRA)
        self.boundaries.pop(V+0x226d78,None)
        self.boundaries.pop(V+0x22d394)
        self.boundaries[V+0x27bdb4]='before_original_unexecuted_resource_provider'
        self.manager_bindings=[];self.all_clears=[];self.common_ctors=[];self.proxy_ctors=[]
        self.provider_entries=[]

    def code(self,u,pc,size,user):
        reg=lambda i:u.reg_read(getattr(r.reg,'UC_ARM64_REG_X'+str(i)))
        if pc==V+0x22c99c:
            self.manager_bindings.append({'pc':hex(pc),'object':hex(reg(0)),
              'manager':hex(reg(1)),'caller':hex(reg(30))})
        if pc==V+0x2f67c:
            self.all_clears.append({'pc':hex(pc),'destination':hex(reg(0)),
              'fill':reg(1),'size':reg(2),'caller':hex(reg(30))})
        if pc==V+0x21d9e0:self.common_ctors.append(hex(reg(0)))
        if pc==V+0x2186dc:self.proxy_ctors.append(hex(reg(0)))
        if pc==V+0x27bdb4:
            self.provider_entries.append({'pc':hex(pc),'LR':hex(reg(30)),
              'SP':hex(u.reg_read(r.reg.UC_ARM64_REG_SP)),
              'x0_x5':[hex(reg(i)) for i in range(6)],'body_executed':False,
              'provider_return_adapter':False})
        if pc==V+0x22d394:
            # stage61 stopped before this body. Here it really executes, so do
            # not inherit that stage's "body_executed:false" observation.
            self.channel_entries.append({'pc':hex(pc),'LR':hex(reg(30)),
              'SP':hex(u.reg_read(r.reg.UC_ARM64_REG_SP)),
              'x0_x4':[hex(reg(i)) for i in range(5)],'body_executed':True,
              'acquisition_return_adapter':False})
            return prev.prev.Guest.code(self,u,pc,size,user)
        return super().code(u,pc,size,user)


def phase(m,label,start,**regs):
    global LAST_PHASE
    e=prev.phase(m,label,start,**regs);LAST_PHASE=e
    return e


def linked(assets):
    m=Guest(*assets);events=[n.link(m)]
    m.uc.mem_write(prev.prev.prev.SITE,m.patch)
    m.uc.mem_protect(V,4096,r.unicorn.UC_PROT_READ|r.unicorn.UC_PROT_EXEC)
    g=prev.prev
    m.expected_data={g.GUARD:1,g.MUTE:0,g.CAT1:1,g.CAT2:1}
    for at,value in m.expected_data.items():
        assert m.blob[at-V]==0;m.uc.mem_write(at,bytes([value]))
    m.uc.mem_protect(g.MUTE&~4095,4096,r.unicorn.UC_PROT_READ|r.unicorn.UC_PROT_WRITE)
    e=phase(m,'original mute setter1 on declared logger input',0x27d898,x0=g.LOG,x1=1)
    assert e['reason']=='returned';events.append(e);m.expected_data[g.MUTE]=1
    return m,events


def word(m,at):return struct.unpack('<I',m.read(at,4))[0]


def isolated_constructor(m,label,start,object_at,object_size,**regs):
    before=m.read(r.ARENA,r.ARENA_SIZE)
    e=phase(m,label,start,**regs)
    assert e['reason']=='returned',e['reason']
    assert e['SP_before']==e['SP_after']==hex(r.SP)
    after=m.read(r.ARENA,r.ARENA_SIZE)
    lo=object_at-r.ARENA;hi=lo+object_size
    assert before[:lo]==after[:lo] and before[hi:]==after[hi:]
    e['full_guest_arena_outside_constructed_object_unchanged']=True
    e['constructed_object_range']=[hex(object_at),hex(object_at+object_size)]
    return e


def one_case(assets,label,descriptor,seed,expected):
    m,events=linked(assets)
    m.uc.mem_write(MANAGER,bytes([seed])*MANAGER_SIZE)
    m.uc.mem_write(CTX,bytes(0x390))
    m.uc.mem_write(FACTORY,bytes([seed])*FACTORY_SIZE)
    e=isolated_constructor(m,'complete original channel manager constructor '+label,
      0x22cc8c,MANAGER,MANAGER_SIZE,x0=MANAGER)
    events.append(e);assert e['reason']=='returned',e['reason']
    manager_clears=list(m.all_clears)
    assert len(manager_clears)==25
    for i in range(4):
        at=MANAGER+0x20a00+i*0x20
        assert m.read(at,8)==bytes(8) and word(m,at+8)==0 and word(m,at+12)==0xffffffff
    e=isolated_constructor(m,'complete original factory six main two proxy constructors and native binding '+label,
      0x226d2c,FACTORY,FACTORY_SIZE,x0=FACTORY,x1=MANAGER)
    events.append(e);assert e['reason']=='returned',e['reason']
    assert m.common_ctors==[hex(COMMON+i*0xe518) for i in range(6)]
    assert m.proxy_ctors==[hex(FACTORY+0x56080+i*0x269b0) for i in range(2)]
    objects=[COMMON+i*0xe518 for i in range(6)]+[FACTORY+0x56080+i*0x269b0 for i in range(2)]
    assert [x['object'] for x in m.manager_bindings]==[hex(x) for x in objects]
    assert all(x['manager']==hex(MANAGER) and m.read(obj+0x10a0,8)==r.p64(MANAGER)
      for x,obj in zip(m.manager_bindings,objects))
    assert m.read(FACTORY,8)==r.p64(MANAGER)
    e=isolated_constructor(m,'complete original factory reset free IDs slots and map-node queues '+label,
      0x2270d4,FACTORY,FACTORY_SIZE,x0=FACTORY)
    events.append(e);assert e['reason']=='returned',e['reason']
    assert not m.all_logs
    assert word(m,FACTORY+8)==8 and word(m,FACTORY+0x55ec8)==6
    assert [word(m,FACTORY+0x14+i*4) for i in range(8)]==list(range(8))
    assert [struct.unpack('<Q',m.read(FACTORY+0x55ed8+i*8,8))[0] for i in range(6)]==[
      HANDLER+i*0xe518 for i in range(6)]
    tree=FACTORY+0x55f10
    assert word(m,tree+0x120)==6
    assert struct.unpack('<Q',m.read(tree+0x130,8))[0]==tree+0x30
    assert all(m.read(obj+0x10a0,8)==r.p64(MANAGER) for obj in objects)
    initialized={'free_ids':word(m,FACTORY+8),'free_main_slots':word(m,FACTORY+0x55ec8),
      'free_proxy_slots':word(m,FACTORY+0xa33d8),'free_main_map_nodes':word(m,tree+0x120)}
    # External request source and partial dispatcher header remain declared.
    # No host writes to the now-native ID/slot/node queues or manager pointers.
    m.uc.mem_write(CTX+0x108,struct.pack('<I',1));m.uc.mem_write(CTX+0x118,r.p64(MESSAGE))
    m.uc.mem_write(MESSAGE,bytes(0xc0));m.uc.mem_write(MESSAGE+8,r.p64(IDENTITY))
    m.uc.mem_write(IDENTITY,struct.pack('<I',p.UID));m.uc.mem_write(MESSAGE+0x20,descriptor)
    m.uc.mem_write(r.SP-0x2000,bytes([seed])*0x3000)
    e=phase(m,'queued request on native initialized factory and real bound manager '+label,
      0x22f34c,x0=CTX)
    events.append(e)
    assert e['reason']=='boundary: before_original_buffer_channel_preparation',e['reason']
    assert m.real_returns[0]['W0']==expected
    assert m.bridge_entries[0]['owner']==hex(COMMON)
    assert word(m,FACTORY+8)==7 and word(m,FACTORY+0x55ec8)==5 and word(m,tree+0x120)==5
    assert m.read(tree,8)==r.p64(tree+0x30)
    assert m.read(tree+0x30+0x20,8)==r.p64(HANDLER)
    assert m.read(COMMON+0xe110,136)==descriptor
    source=int(m.bridge_entries[0]['source'],16);raw=m.read(source,152)
    assert raw[:136]==descriptor
    m.boundaries.pop(V+0x21dd54)
    e=phase(m,'same request native manager cache lookup and resource-provider entry '+label,
      0x21dd54,independent=False)
    events.append(e)
    assert e['reason']=='boundary: before_original_unexecuted_resource_provider',e['reason']
    assert len(m.channel_entries)==len(m.provider_entries)==1
    assert m.channel_entries[0]['x0_x4'][0]==hex(MANAGER)
    assert m.channel_entries[0]['body_executed']
    assert m.provider_entries[0]['LR']==hex(V+0x22d3fc)
    assert m.provider_entries[0]['x0_x5'][0]=='0x61003c'
    assert m.provider_entries[0]['x0_x5'][2:] == ['0x470','0x11','0x0','0x806800f3']
    assert hex(V+0x22de54) in e['pcs'] and hex(V+0x22de98) in e['pcs']
    assert m.read(source,152)==raw and m.read(COMMON+0xe110,136)==descriptor
    prev.prev.assert_image(m)
    return {'label':label,'seed':seed,'expected_native_row':expected,
      'native_manager':hex(MANAGER),'native_common':hex(COMMON),'native_handler':hex(HANDLER),
      'manager_constructor_real_memset_calls':manager_clears,
      'original_common_constructors':m.common_ctors,'original_proxy_constructors':m.proxy_ctors,
      'native_manager_bindings':m.manager_bindings,'native_free_queues_initialized':initialized,
      'queue_counts_after_request':{'ids':word(m,FACTORY+8),'main_slots':word(m,FACTORY+0x55ec8),
        'main_map_nodes':word(m,tree+0x120)},
      'channel_entries':m.channel_entries,'provider_entries':m.provider_entries,
      'actual_matcher_returns':m.real_returns,'source98_hex':raw.hex(),
      'original_diagnostics':m.all_logs,'events':events,
      'external_request_and_partial_dispatcher_logger_are_fixtures':True,
      'real_OS_singleton_task_threads_locks_provider_Hal_recording_or_recovery':False,
      'independent_private16M_writer_or_actual_writer_hook_executed_here':False}


def run(out):
    prior=prev.STAGE/'final-receipt.json';assert im.sha(prior.read_bytes())==PRIOR_SHA
    for row in json.loads(prior.read_text())['files']:assert im.sha((ROOT/row['path']).read_bytes())==row['sha256']
    assert (BASE/'GOAL_STATUS.json').read_bytes()==(STAGE/'goal-status-before.json').read_bytes()
    obj=prev.prev.prev.STAGE/'run-post-loader-patch-20261026/match_adapter.a64.o'
    code,ro,_=prev.prev.prev.object_image(obj.read_bytes())
    wobj=prev.old.STAGE/'run-bounded-stores-20261026/resource_alias.a64.o'
    wcode,wro,functions,_=prev.old.object_image(wobj.read_bytes())
    blob=(BASE/'stage2/extraction/files/nflasha3/av-cam.bin').read_bytes()
    assert im.sha(blob)==im.PINS['stage2/extraction/files/nflasha3/av-cam.bin']
    module=(n.STAGE/'official-files/nflasha15/kmod/liro.ko').read_bytes()
    kernel=(n.STAGE/'official-files/nflasha3/vmlinux.bin').read_bytes()
    assets=blob,module,kernel,code,ro,wcode,wro,functions
    inp=p.inputs();cases=[one_case(assets,'target FH priorA5',inp[0][1],0xa5,386),
      one_case(assets,'target FH priorC3',inp[0][1],0xc3,386),
      one_case(assets,'stock UHD control',inp[3][1],0xc3,431)]
    proof={'status':'PASS_NATIVE_MANAGER_FACTORY_QUEUES_TO_PROVIDER_BOUNDARY',
      'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
      'bounded_fragments':sum(len(c['events']) for c in cases),'cases':cases,
      'original_regions':[{'start':hex(a),'end':hex(z),'instructions':im.dump(blob,a,z,V)} for a,z in EXTRA],
      'scope':{'manager_common_proxy_constructors_native_binding_and_factory_reset_completed':True,
        'slot_ID_map_node_queues_not_host_filled':True,'provider_body_or_success_return_not_executed':True,
        'real_singleton_task_global_boot_and_hardware_not_proven':True,
        'UU_Windows_camera_interface_auth_mode_driver_files_module_WBI_flash':False,
        'goal_complete':False,'persistent_write_release':False}}
    im.write_json(out/'manager-factory-results.json',proof)
    (out/'executed-source.py').write_bytes(Path(__file__).read_bytes())
    im.write_json(out/'source-receipt.json',{'script_sha256':im.sha(Path(__file__).read_bytes()),
      'avcam_sha256':im.sha(blob),'LIRO_sha256':im.sha(module),'kernel_sha256':im.sha(kernel),
      'wrapper_object_sha256':im.sha(obj.read_bytes()),'writer_object_mapped_not_executed_sha256':im.sha(wobj.read_bytes()),
      'previous_manifest_sha256':PRIOR_SHA,'volume_uuid':im.VOLUME})
    print(json.dumps({'status':proof['status'],'bounded_fragments':proof['bounded_fragments'],
      'rows':[c['expected_native_row'] for c in cases],'goal_complete':False}))


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--output',required=True)
    args=ap.parse_args();im.volume();out=Path(args.output).resolve()
    assert STAGE in out.parents and not out.exists();out.mkdir()
    try:run(out)
    except Exception:
        (out/'attempt-source.py').write_bytes(Path(__file__).read_bytes())
        if 'LAST_PHASE' in globals():im.write_json(out/'last-phase-at-failure.json',LAST_PHASE)
        im.write_json(out/'attempt-failure.json',{'traceback':traceback.format_exc(),'passing_result':False})
        raise


if __name__=='__main__':main()
