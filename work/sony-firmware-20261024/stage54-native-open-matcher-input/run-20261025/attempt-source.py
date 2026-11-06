#!/usr/bin/env python3
"""Original queued Open -> allocation/registration -> native matcher input.

Queue/free-slot/id/map-node storage and descriptors are explicit RAM fixtures.
No camera or HAL. The original call chain stops at its first matcher diagnostic;
post-diagnostic matching is a separate copied guest, with assumptions explicit.
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
sys.path.insert(0,str(BASE/'stage53-native-frame-fill'))
import native_frame_fill as p
im,r,V,n,c=p.im,p.r,p.V,p.n,p.c
sys.path.insert(0,str(BASE/'stage33-imola-format-matcher'))
import imola_matcher as match
CTX=r.ARENA+0x200000
FACTORY=CTX+0x390
HANDLER=r.ARENA+0x100000
COMMON=HANDLER+8
MESSAGE=r.ARENA+0x280000
IDENTITY=r.ARENA+0x290000
NODE=r.ARENA+0x2a0000
UID=0x2a
PRIOR_SHA='bfdfb6f95487a103566979da8643540cf4652cb7b9da2c052c51427de7645b7b'
EXTRA=[(0x22f34c,0x22f408),(0x229808,0x229ae4),
  (0x227cdc,0x227dcc),(0x228e40,0x229014),(0x229014,0x2290cc),
  (0x227e0c,0x227ecc),(0x226644,0x226778),(0x22c500,0x22c514),
  (0x22c9a4,0x22c9c0),(0x21e26c,0x21e2f4),
  (0x21ecf4,0x21ed24),(0x225eb8,0x225ee0),(0x225fa0,0x226128),
  (0x27cf58,0x27cf68)]


class Guest(p.l.f.Guest):
    def __init__(self,blob,module,kernel):
        super().__init__(blob,module,kernel)
        self.ranges.extend((V+a,V+z) for a,z in [*c.w.RANGES,*c.t.EXTRA,*c.EXTRA,*EXTRA])
        self.boundaries[V+0x27d528]='before_unexecuted_diagnostic'
        self.common_calls=[];self.matcher_calls=[];self.tail_reads=[];self.match_param=None
        self.uc.hook_add(r.unicorn.UC_HOOK_MEM_READ,self.observe_read)

    def code(self,u,pc,size,user):
        if pc in (V+0x21e26c,V+0x225eb8):
            a=u.reg_read(r.reg.UC_ARM64_REG_X0);b=u.reg_read(r.reg.UC_ARM64_REG_X1)
            record={'pc':hex(pc),'owner':hex(a),'input_pointer':hex(b),'input98_hex':self.read(b,0x98).hex()}
            (self.common_calls if pc==V+0x21e26c else self.matcher_calls).append(record)
            if pc==V+0x225eb8:self.match_param=b
        return super().code(u,pc,size,user)

    def observe_read(self,u,access,address,size,value,user):
        at=self.match_param
        if at is not None and at+0x88<=address and address+size<=at+0x98:
            self.tail_reads.append({'pc':hex(u.reg_read(r.reg.UC_ARM64_REG_PC)),
              'offset':hex(address-at),'size':size})


def phase(m,label,start,independent=True,**regs):
    m.store_count=0;m.store_digest=hashlib.sha256()
    e=c.phase(m,label,V+start,independent=independent,**regs)
    e['approved_arena_stack_store_count']=m.store_count
    e['approved_store_PC_address_size_sha256']=m.store_digest.hexdigest()
    global LAST_PHASE
    LAST_PHASE=e
    return e


def fresh(blob,module,kernel,events):
    m=Guest(blob,module,kernel);events.append(n.link(m))
    m.uc.mem_protect(V,4096,r.unicorn.UC_PROT_READ|r.unicorn.UC_PROT_EXEC)
    m.uc.mem_write(HANDLER,bytes(0xe520))
    e=phase(m,'complete original common-handler constructor',0x21d9e0,x0=COMMON)
    assert e['reason']=='returned';events.append(e)
    # Declared free queues/node storage, not a claimed whole native factory boot.
    m.uc.mem_write(CTX,bytes(0x57000))
    m.uc.mem_write(CTX+0x108,struct.pack('<I',1));m.uc.mem_write(CTX+0x118,r.p64(MESSAGE))
    m.uc.mem_write(FACTORY+0x55ec8,struct.pack('<I',1))
    m.uc.mem_write(FACTORY+0x55ed8,r.p64(HANDLER))
    m.uc.mem_write(FACTORY+8,struct.pack('<I',1))
    m.uc.mem_write(FACTORY+0x14,struct.pack('<I',0))
    tree=FACTORY+0x55f10
    m.uc.mem_write(tree+0x120,struct.pack('<I',1))
    m.uc.mem_write(tree+0x130,r.p64(NODE))
    return m


def inputs():
    d=json.loads((BASE/'stage32-resource-open-descriptor/run-enum-bound-20261025/resource-descriptor-results.json').read_text())
    target,proxy,uhd=[bytes.fromhex(x['descriptor_hex']) for x in d['cases'][:3]]
    old=json.loads((BASE/'stage33-imola-format-matcher/run-20261025/imola-matcher-results.json').read_text())
    # Preserve stage33's artificial FF descriptor and its provenance explicitly.
    # Find the native descriptor-case output rather than synthesize its byte here.
    def descriptors(value):
        out=[]
        if isinstance(value,dict):
            if value.get('label')=='artificial MAIN API-quality24 control' and value.get('descriptor_hex'):
                out.append(bytes.fromhex(value['descriptor_hex']))
            for v in value.values():out.extend(descriptors(v))
        elif isinstance(value,list):
            for v in value:out.extend(descriptors(v))
        return out
    ff=descriptors(old);assert ff and all(x==ff[0] for x in ff)
    assert [i for i,(a,b) in enumerate(zip(target,ff[0])) if a!=b]==[0x38]
    return [('target_MAIN_FH',target,1),('artificial_MAIN_FF_quality24',ff[0],1),
      ('proxy_FH_control',proxy,2),('stock_UHD_QT150M_control',uhd,1)]


def captured_regs(m):
    regs={f'x{i}':m.uc.reg_read(getattr(r.reg,'UC_ARM64_REG_X'+str(i))) for i in range(31)}
    regs['sp']=m.uc.reg_read(r.reg.UC_ARM64_REG_SP)
    return regs


def case(blob,module,kernel,label,descriptor,expected_type):
    events=[];m=fresh(blob,module,kernel,events)
    m.uc.mem_write(MESSAGE,bytes(0xc0));m.uc.mem_write(MESSAGE+8,r.p64(IDENTITY))
    m.uc.mem_write(IDENTITY,struct.pack('<I',UID));m.uc.mem_write(MESSAGE+0x20,descriptor)
    # Preserve the untouched tail word as an explicit prior-stack-content input.
    m.uc.mem_write(r.SP-0x2000,bytes([0xc3])*0x3000)
    e=phase(m,'original queued Open through native tail allocation registration and common-to-matcher calls '+label,
      0x22f34c,x0=CTX)
    assert e['reason']=='boundary: before_unexecuted_diagnostic';events.append(e)
    assert e['pcs'][-2]==hex(V+0x225edc)
    assert len(m.common_calls)==len(m.matcher_calls)==1
    common,entered=m.common_calls[0],m.matcher_calls[0]
    assert common['owner']==entered['owner']==hex(COMMON)
    raw=bytes.fromhex(entered['input98_hex'])
    assert raw==bytes.fromhex(common['input98_hex']) and raw[:0x88]==descriptor
    tail=struct.unpack_from('<4I',raw,0x88)
    assert tail==(expected_type,10,25,0xc3c3c3c3)
    assert m.read(COMMON+0xe110,0x88)==descriptor
    assert p.l.u32(m,COMMON+0x10ac)==UID
    assert p.l.u32(m,HANDLER)==0
    assert p.l.u32(m,CTX+0x108)==0
    assert p.l.u32(m,FACTORY+0x55ec8)==0 and p.l.u32(m,FACTORY+8)==0
    tree=FACTORY+0x55f10
    assert m.read(tree,8)==r.p64(NODE)
    assert p.l.u32(m,NODE+0x18)==0 and m.read(NODE+0x20,8)==r.p64(HANDLER)
    c.assert_image(m,blob)
    # A distinct guest: no diagnostic-return adapter or modification of the
    # suspended original guest's PC. The unexecuted diagnostics' effects remain
    # unproven. Original saved frames and computed input are explicit fixtures.
    post=Guest(blob,module,kernel);load=n.link(post);events.append(load)
    post.uc.mem_protect(V,4096,r.unicorn.UC_PROT_READ|r.unicorn.UC_PROT_EXEC)
    post.uc.mem_write(r.ARENA,m.read(r.ARENA,r.ARENA_SIZE))
    post.uc.mem_write(r.STACK,m.read(r.STACK,r.STACK_SIZE))
    regs=captured_regs(m);regs['x20']=3 # original MOV W20,#3 at0x225f94
    post.regs(**regs);post.match_param=int(entered['input_pointer'],16)
    e2=phase(post,'independent post-diagnostic native matcher on actually produced tail '+label,
      0x225fa0,independent=False)
    assert e2['reason']=='boundary: before_unexecuted_diagnostic';events.append(e2)
    assert e2['pcs'][-2]==hex(V+0x21ed20)
    scalar=post.uc.reg_read(r.reg.UC_ARM64_REG_X23)&0xffffffff
    index=scalar if scalar<0x80000000 else scalar-(1<<32)
    expected={'target_MAIN_FH':-1,'artificial_MAIN_FF_quality24':386,
      'proxy_FH_control':-1,'stock_UHD_QT150M_control':431}[label]
    assert index==expected
    assert post.read(int(entered['input_pointer'],16),0x98)==raw
    reads={(x['offset'],x['size']) for x in post.tail_reads}
    assert reads=={('0x88',4),('0x8c',4)}
    c.assert_image(post,blob)
    return {'label':label,'descriptor88_hex':descriptor.hex(),
      'source_descriptor_is_artificial_quality_control':label=='artificial_MAIN_FF_quality24',
      'native_common_entry':common,'native_matcher_entry':entered,'native_tail_words88_8c_90_94':list(tail),
      'pending_Open_queue_count_after_native_dequeue':0,
      'native_new_handler_id':0,'source_UID_fixture':UID,
      'native_new_handler_registered_in_map':True,
      'free_handler_id_and_map_node_queues_are_declared_fixtures':True,
      'full_factory_construction_real_registration_or_global_idle':False,
      'native_chain_to_first_matcher_diagnostic_contiguous':True,
      'independent_native_matcher_row':index,'independent_matcher_tail_reads':post.tail_reads,
      'post_diagnostic_assumptions':'Separate guest copies computed arena/stack/registers, sets W20=3 from original225f94; no real diagnostic execution/effect equivalence proved.',
      'full_resource_Open_or_Hal_acceptance':False,'original_events':events}


def run(out):
    prior=p.STAGE/'final-receipt.json';assert im.sha(prior.read_bytes())==PRIOR_SHA
    for e in json.loads(prior.read_text())['files']:
        assert im.sha((ROOT/e['path']).read_bytes())==e['sha256']
    blob=(BASE/'stage2/extraction/files/nflasha3/av-cam.bin').read_bytes()
    assert im.sha(blob)==im.PINS['stage2/extraction/files/nflasha3/av-cam.bin']
    module=(n.STAGE/'official-files/nflasha15/kmod/liro.ko').read_bytes()
    kernel=(n.STAGE/'official-files/nflasha3/vmlinux.bin').read_bytes()
    cases=[case(blob,module,kernel,*args) for args in inputs()]
    regions=[('queued Open consumer and constant tail',0x22f34c,0x22f408),
      ('native new handler allocation',0x228e40,0x228f98),
      ('native descriptor classification',0x227cdc,0x227dcc),
      ('native Open argument augmentation',0x229808,0x229888),
      ('native prior-handler selection and tail update',0x229900,0x229a00),
      ('native common Open calls',0x229ac8,0x229ae4),
      ('common original copy clear dispatch',0x21e26c,0x21e2f4),
      ('common original matcher call and returned scalar capture',0x21ecf4,0x21ed24)]
    proof={'status':'PASS_ORIGINAL_QUEUED_OPEN_NATIVE_MATCHER_INPUT_PROVENANCE',
      'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
      'original_fragments':sum(len(x['original_events']) for x in cases),'cases':cases,
      'original_regions':[{'name':name,'instructions':im.dump(blob,a,z,V)} for name,a,z in regions],
      'native_classification_table25':list(struct.unpack_from('<25I',blob,0x32e560)),
      'old_extra2_10_is_not_observed_MAIN_tail':True,
      'native_MAIN_type1_and_8c10_keep_FF_match_conditional_row386':True,
      'native_proxy_type2_8c10_not_old_proxy2_1':True,
      'target_FH_missing_preset_remains_unresolved':True,
      'original_guest_code_unchanged':True,'native_output_PC_return_log_lock_or_HAL_adapter':False,
      'camera_UU_Windows_module_WBI_flash':False,
      'hardware_recording_same_body_backup_restore_or_independent_recovery':False,
      'goal_complete':False,'persistent_write_release':False}
    im.write_json(out/'open-matcher-input-results.json',proof)
    (out/'executed-source.py').write_bytes(Path(__file__).read_bytes())
    im.write_json(out/'source-receipt.json',{'script_sha256':im.sha(Path(__file__).read_bytes()),
      'avcam_sha256':im.sha(blob),'LIRO_sha256':im.sha(module),'kernel_sha256':im.sha(kernel),
      'previous_manifest_sha256':im.sha(prior.read_bytes()),'volume_uuid':im.VOLUME})
    print(json.dumps({'status':proof['status'],'original_fragments':proof['original_fragments'],
      'native_tails_and_match':[(x['label'],x['native_tail_words88_8c_90_94'],x['independent_native_matcher_row']) for x in cases],
      'goal_complete':False}))


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
