#!/usr/bin/env python3
"""Original buffer-record FIFO, not allocation/deallocation or ownership proof."""
from pathlib import Path
import argparse
import datetime
import json
import struct
import sys
import traceback

STAGE=Path(__file__).resolve().parent
sys.path.insert(0,str(STAGE.parent/'stage70-native-open-rejection'))
import open_rejection as prior
c=prior.c
r,im,V,n,f=c.r,c.im,c.V,c.n,c.f
BASE,ROOT=c.BASE,c.ROOT
MANAGER=f.last.MANAGER
Q=MANAGER+0x15518
Q_USED=0x90
OUTPUT=r.ARENA+0x3e0000
PUSH=V+0x22da80
POP=V+0x22d9b0


class QueueGuest(c.Guest):
    def code(self,u,pc,size,user):
        if pc==V+0x27d568:
            self.observed_pc=pc
            sp=u.reg_read(r.reg.UC_ARM64_REG_SP);raw=self.read(sp,80)
            fmt=struct.unpack_from('<Q',raw)[0]
            self.all_logs.append({'pc':hex(pc),'SP':hex(sp),'LR':hex(u.reg_read(r.reg.UC_ARM64_REG_LR)),
                'format':f.f59.bounded_cstring(self,fmt),
                'arguments_x0_x7':[hex(u.reg_read(getattr(r.reg,'UC_ARM64_REG_X'+str(i)))) for i in range(8)],
                'spill80_hex':raw.hex(),'generic_raw_observation_not_matcher_signature':True})
            # Skip only the stage59 matcher-specific argument decoder. The
            # original logger body still executes through the ordinary guest.
            return f.f58.Guest.code(self,u,pc,size,user)
        return super().code(u,pc,size,user)


def linked(assets,modules,providers,adapter):
    m=QueueGuest(assets,modules,providers,adapter);events=[n.link(m)]
    for row in m.import_bindings:
        assert m.read(int(row['actual_avcam_slot'],16),8)==r.p64(int(row['original_module_target'],16))
    assert sum(int.from_bytes(m.read(V+0x1ec+i*8,8),'little')!=0 for i in range(211))==5
    # Both original Sony callsites remain pristine; mapped adapters are inert.
    m.uc.mem_protect(V,4096,r.unicorn.UC_PROT_READ|r.unicorn.UC_PROT_EXEC)
    m.expected_data={f.f59.GUARD:1,f.f59.MUTE:0,f.f59.CAT1:1,f.f59.CAT2:1}
    for a,value in m.expected_data.items():assert m.blob[a-V]==0;m.uc.mem_write(a,bytes([value]))
    m.uc.mem_protect(f.f59.MUTE&-4096,4096,r.unicorn.UC_PROT_READ|r.unicorn.UC_PROT_WRITE)
    e=c.phase(m,'original mute setter on declared initialized logger',V+0x27d898,x0=f.f59.LOG,x1=1)
    assert e['reason']=='returned';events.append(e);m.expected_data[f.f59.MUTE]=1
    return m,events


def state(m):
    raw=m.read(Q,Q_USED);count,tail,head=struct.unpack_from('<III',raw)
    assert 0<=count<=8 and tail<8 and head<8
    return {'count':count,'tail':tail,'head':head,'raw144_hex':raw.hex(),
            'slots':[[hex(x) for x in struct.unpack_from('<2Q',raw,16+i*16)] for i in range(8)]}


def operation(m,label,which,record=None,expected=0):
    before=m.read(Q,Q_USED);output=m.read(OUTPUT,16);m.record_stores=[]
    if which=='push':
        args={'x0':MANAGER,'x1':record[0],'x2':record[1]};pc=PUSH
    else:assert which=='pop';args={'x0':MANAGER,'x1':OUTPUT};pc=POP
    e=c.phase(m,label,pc,**args)
    assert e['reason']=='returned' and m.uc.reg_read(r.reg.UC_ARM64_REG_X0)==expected
    after=m.read(Q,Q_USED)
    if expected:
        assert after==before and m.read(OUTPUT,16)==output
    if which=='push':assert m.read(OUTPUT,16)==output
    e.update(operation=which,expected_result=expected,queue_before=before.hex(),queue_after=state(m),
             input_record=[hex(x) for x in record] if record else None,output16_hex=m.read(OUTPUT,16).hex(),
             memory_stores=list(m.record_stores))
    return e


def one_case(assets,modules,providers,adapter,label,seed):
    m,events=linked(assets,modules,providers,adapter)
    global CURRENT_GUEST
    CURRENT_GUEST=m
    m.ranges.append((POP,V+0x22db34))
    m.uc.mem_write(MANAGER,bytes([seed])*f.last.MANAGER_SIZE)
    before=m.read(r.ARENA,r.ARENA_SIZE)
    e=c.phase(m,'original manager constructor only '+label,V+0x22cc8c,x0=MANAGER)
    assert e['reason']=='returned';events.append(e)
    after=m.read(r.ARENA,r.ARENA_SIZE);lo=MANAGER-r.ARENA;hi=lo+f.last.MANAGER_SIZE
    assert before[:lo]==after[:lo] and before[hi:]==after[hi:]
    initial=state(m);assert initial['count']==initial['head']==initial['tail']==0
    m.uc.mem_write(OUTPUT,b'\x5a'*16);m.record_stores=[]
    def write(u,access,a,size,value,user):
        assert any(start<=a and a+size<=end for start,end in
                   [(Q,Q+Q_USED),(OUTPUT,OUTPUT+16),(r.STACK,r.STACK+r.STACK_SIZE)]),(hex(a),size)
        m.record_stores.append({'pc':hex(u.reg_read(r.reg.UC_ARM64_REG_PC)),'address':hex(a),'bytes':size})
    hook=m.uc.hook_add(r.unicorn.UC_HOOK_MEM_WRITE,write)
    prefix=seed*0x0101010101010101
    records=[((prefix+i)&((1<<64)-1),0x1000+i*0x111) for i in range(11)]
    assert all(not r.ARENA<=a<r.ARENA+r.ARENA_SIZE and not r.STACK<=a<r.STACK+r.STACK_SIZE for a,length in records)
    events.append(operation(m,'original dequeue on constructor-empty queue '+label,'pop',expected=1))
    for i in range(8):
        events.append(operation(m,'original enqueue record '+str(i)+' '+label,'push',records[i]))
        assert state(m)['count']==i+1
    full=state(m);assert full['head']==full['tail']==0 and full['count']==8
    events.append(operation(m,'original ninth enqueue rejected with queue unchanged '+label,'push',records[8],1))
    popped=[]
    for i in range(3):
        events.append(operation(m,'original dequeue first records '+str(i)+' '+label,'pop'))
        value=struct.unpack('<2Q',m.read(OUTPUT,16));assert value==records[i];popped.append(value)
    for i in range(8,11):
        events.append(operation(m,'original enqueue after wrap '+str(i)+' '+label,'push',records[i]))
    wrapped=state(m);assert wrapped['count']==8 and wrapped['head']==wrapped['tail']==3
    for i in range(3,11):
        events.append(operation(m,'original dequeue through wrap '+str(i)+' '+label,'pop'))
        value=struct.unpack('<2Q',m.read(OUTPUT,16));assert value==records[i];popped.append(value)
    empty=state(m);assert empty['count']==0 and empty['head']==empty['tail']==3
    assert any(x!=0 for x in m.read(Q+16,128))
    events.append(operation(m,'original empty dequeue preserves previous output '+label,'pop',expected=1))
    assert state(m)==empty and popped==records
    m.uc.hook_del(hook)
    prior.assert_images(m)
    assert not m.kernel_service_entries and not m.message_entries and not m.module_alloc_entries
    return {'label':label,'prior_storage_seed':seed,'initial':initial,'full':full,'wrapped':wrapped,'empty':empty,
            'declared_records':[[hex(x) for x in row] for row in records],
            'dequeued_in_original_FIFO_order':[[hex(x) for x in row] for row in popped],
            'data_words_are_unmapped_numeric_fixtures_not_verified_buffers':True,
            'logical_empty_retains_old_slot_bytes':True,'events':events,
            'original_logger_raw_calls':m.all_logs,'formatter_entries':m.format_args,
            'real_allocation_deallocation_pointer_validation_ownership_or_transport_executed':False}


def static_provenance(blob):
    targets={0x22da80:[],0x22d9b0:[]}
    for at in range(0,0x300000,4):
        word=struct.unpack_from('<I',blob,at)[0]
        if word&0xfc000000!=0x94000000:continue
        disp=word&0x3ffffff
        if disp&0x2000000:disp-=0x4000000
        if at+disp*4 in targets:targets[at+disp*4].append(at)
    assert targets=={0x22da80:[0x21f72c],0x22d9b0:[0x21eca0,0x21ef78]}
    rows=[]
    for index in (386,431):
        at=0x395108+index*0x90;raw=blob[at:at+0x90]
        assert raw[0x8a]==0
        rows.append({'index':index,'row_offset':hex(at),'row_sha256':im.sha(raw),
                     'preset_ID':hex(struct.unpack_from('<I',raw,0x28)[0]),'row_plus8a':raw[0x8a]})
    return {'direct_BL_candidates_in_first_0x300000_only':{hex(k):[hex(x) for x in v] for k,v in targets.items()},
            'not_indirect_or_whole_program_coverage':True,'rows':rows,
            'regions':[{'start':hex(a),'end':hex(z),'instructions':im.dump(blob,a,z,V)} for a,z in
                       [(0x22ccd4,0x22cd04),(0x22d9b0,0x22db34),(0x21f71c,0x21f738),
                        (0x21edf4,0x21ee30),(0x21ef28,0x21efbc)]],
            'scope':['Original push stores two words in a local bounded queue, not a physical free or pointer attestation.',
                     'Original pop copies/removes the record into the supplied output; it does not allocate or validate the referenced storage.',
                     'Normal selected-row code copies COMMON1040/1048 to output then clears COMMON fields; separate row flag gates the pop.',
                     'Rows386/431 have raw flag0; the later branch is static, not a completed target hardware request or an exemption from ownership checks.']}


def run(out):
    assert (BASE/'GOAL_STATUS.json').read_bytes()==(STAGE/'goal-status-before.json').read_bytes()
    manifest=BASE/'stage70-native-open-rejection/final-receipt.json'
    assert im.sha(manifest.read_bytes())=='ec99ebf0d9cdbb5c80bba00e4c54635f30d57f14e4055ea8b51f08845a6e6b78'
    for row in json.loads(manifest.read_text())['files']:assert im.sha((ROOT/row['path']).read_bytes())==row['sha256']
    modules,providers,kernel=c.d.link.build()
    matchobj=f.f58.STAGE/'run-post-loader-patch-20261026/match_adapter.a64.o'
    code,ro,_=f.f58.object_image(matchobj.read_bytes())
    writerobj=c.old.STAGE/'run-bounded-stores-20261026/resource_alias.a64.o'
    wcode,wro,functions,_=c.old.object_image(writerobj.read_bytes())
    blob=(BASE/'stage2/extraction/files/nflasha3/av-cam.bin').read_bytes();assert im.sha(blob)==im.PINS['stage2/extraction/files/nflasha3/av-cam.bin']
    liro=(n.STAGE/'official-files/nflasha15/kmod/liro.ko').read_bytes()
    adapter=c.object_image((c.STAGE/'run-same-instance-slices-20261026/channel_adapter.a64.o').read_bytes())
    assets=blob,liro,kernel,code,ro,wcode,wro,functions
    cases=[one_case(assets,modules,providers,adapter,'A5-shaped unmapped record values',0xa5),
           one_case(assets,modules,providers,adapter,'C3-shaped unmapped record values',0xc3)]
    proof={'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
           'status':'PASS_ORIGINAL_NUMERIC_RECORD_FIFO_NOT_PHYSICAL_STORAGE_RELEASE',
           'cases':cases,'bounded_fragments':sum(len(x['events']) for x in cases),'static_provenance':static_provenance(blob),
           'source_receipt':{'script_sha256':im.sha(Path(__file__).read_bytes()),
                             'runner_sha256':im.sha((c.STAGE/'channel_callpath.py').read_bytes()),
                             'image_assertion_helper_sha256':im.sha((prior.STAGE/'open_rejection.py').read_bytes()),
                             'avcam_sha256':im.sha(blob),'LIRO_sha256':im.sha(liro),'kernel_sha256':im.sha(kernel),
                             'previous_manifest_sha256':im.sha(manifest.read_bytes())},
           'semantic_refinement':'stage70 boundary label manager_storage_release was an unexecuted stop name. This stage verifies a local record-return enqueue primitive; do not read the old name as physical deallocation evidence.',
           'real_buffer_origin_current_owner_consumers_full_Close_Hal_or_recovery':False,
           'Windows_UU_camera_operations':False,'goal_complete':False,'persistent_write_release':False}
    im.write_json(out/'buffer-record-fifo-results.json',proof)
    (out/'executed-source.py').write_bytes(Path(__file__).read_bytes())
    print(json.dumps({'status':proof['status'],'cases':2,'bounded_fragments':proof['bounded_fragments'],
                      'actual_physical_release_or_ownership_validation':False}))


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--output',required=True);args=ap.parse_args()
    im.volume();out=Path(args.output).resolve();assert STAGE in out.parents and not out.exists();out.mkdir()
    try:run(out)
    except Exception:
        (out/'attempt-source.py').write_bytes(Path(__file__).read_bytes())
        im.write_json(out/'attempt-failure.json',{'traceback':traceback.format_exc(),'passing_result':False})
        if 'CURRENT_GUEST' in globals():
            m=CURRENT_GUEST;im.write_json(out/'failure-state.json',{'pc':hex(m.uc.reg_read(r.reg.UC_ARM64_REG_PC)),
                'reason':m.reason,'last_pcs':[hex(x) for x in m.pcs[-12:]],'queue':state(m)})
        raise


if __name__=='__main__':main()
