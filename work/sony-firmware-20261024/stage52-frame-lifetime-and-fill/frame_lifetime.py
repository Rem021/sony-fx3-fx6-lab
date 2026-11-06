#!/usr/bin/env python3
"""Bounded original frame return/dequeue/reuse and event-tag geometry copy.

All controller/map/owner/event links are explicit RAM fixtures. No camera,
native output adapter, simulated HAL success, log/lock return or PC repair.
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
sys.path.insert(0,str(BASE/'stage51-frame-slot-provenance'))
import frame_slots as f
c,n,im,r,V=f.c,f.n,f.im,f.r,f.V
POOL,NODES,OUT,STRIDE=f.POOL,f.NODES,f.OUT,f.STRIDE
INDEX=r.ARENA+0x2d0000
OWNER=r.ARENA+0x2e0000
PARENT=r.ARENA+0x2e1000
EVENT=r.ARENA+0x2f0000
ROOT_TAG=r.ARENA+0x2f1000
MAGIC=r.ARENA+0x2f2000
PRIOR_SHA='c1fe9d89c021510bd231a77be57dfbfed9deba55e6c699ceb42063a9e1bde3d3'
EXTRA=[(0x15fa10,0x15fc78),(0x161590,0x1616a8),(0x162c88,0x162f78),
  (0xa3f3c,0xa3f9c),(0x91dd4,0x91e34),(0x91e68,0x91e7c),
  (0x8f1ac,0x8f210),(0x95c38,0x95c3c),(0x94d14,0x94d84),
  (0x957bc,0x9589c),(0x10dc,0x1294),(0x147a2c,0x147a44)]


class Guest(f.Guest):
    def __init__(self,blob,module,kernel):
        super().__init__(blob,module,kernel)
        self.ranges.extend((V+a,V+z) for a,z in EXTRA)
        self.boundaries.update({V+0x27c1a8:'before_unbound_runtime_notification',
          V+0x147a44:'after_original_tag_getter_and_record_validity_store'})


def phase(m,label,start,**regs):
    result=f.phase(m,label,start,**regs)
    global LAST_PHASE
    LAST_PHASE=result
    return result


def fresh(blob,module,kernel,events):
    m=Guest(blob,module,kernel)
    events.append(n.link(m))
    m.uc.mem_protect(V,4096,r.unicorn.UC_PROT_READ|r.unicorn.UC_PROT_EXEC)
    m.uc.mem_write(POOL,bytes(0x95000))
    tree=POOL+0x8af60
    m.uc.mem_write(tree+0x670,struct.pack('<3I',40,0,0))
    for i in range(40):m.uc.mem_write(tree+0x680+i*8,r.p64(NODES+i*0x28))
    e=phase(m,'original40slot initialization on declared map-node pool',0x15ed14,x0=POOL)
    assert e['reason']=='returned';events.append(e)
    return m


def u32(m,address):return int.from_bytes(m.read(address,4),'little')


def snapshot(m,label,index=0):
    flags=[list(m.read(POOL+0x8ade0+3*i,3)) for i in range(40)]
    record=m.read(POOL+index*STRIDE,STRIDE)
    return {'label':label,'queued_indices':u32(m,POOL+0x947a8),
      'write_cursor':u32(m,POOL+0x947ac),'read_cursor':u32(m,POOL+0x947b0),
      'active_slots':sum(v[0]!=0 for v in flags),'flags':flags,
      'queued_storage_u32':list(struct.unpack('<40I',m.read(POOL+0x947b4,160))),
      'selected_slot_index':index,'selected_record_sha256':im.sha(record),
      'selected_geometry_u16':list(struct.unpack_from('<2H',record,0x3e)),
      'selected_record_630':record[0x630],'selected_record_63c':struct.unpack_from('<I',record,0x63c)[0]}


def borrow(m,events,label,expected):
    m.uc.mem_write(OUT,r.p64(0x99999999))
    e=phase(m,label,0x15f8c0,x0=POOL,x1=OUT);events.append(e)
    assert e['reason']=='returned'
    index=int(e['x0_after'],16)&0xffffffff
    pointer=int.from_bytes(m.read(OUT,8),'little')
    assert index==expected
    assert pointer==(0 if expected==0xffffffff else POOL+expected*STRIDE)
    return e


def dequeue(m,events,label,expected):
    e=phase(m,label,0x161590,x0=POOL);events.append(e)
    assert e['reason']=='returned' and int(e['x0_after'],16)==POOL+expected*STRIDE
    return e


def mark(m,events,label,entry,index):
    e=phase(m,label,entry,x0=POOL,x1=index);events.append(e)
    assert e['reason']=='returned'
    return e


def composite(m,events,index,label):
    m.uc.mem_write(INDEX,struct.pack('<I',index))
    e=phase(m,label,0x15fa10,x0=POOL,x1=INDEX);events.append(e)
    return e


def tag_fixture(m,blob,payload,key=0,root_present=True):
    # Generic native tag getter compares the root's first4bytes with a pointer
    # stored in the event container. These deliberately chosen bytes are NOT a
    # recovered live packet. Entry magic alone is pinned to original constant.
    m.uc.mem_write(EVENT,bytes(0x100));m.uc.mem_write(ROOT_TAG,bytes(0x200))
    m.uc.mem_write(MAGIC,b'TEST')
    m.uc.mem_write(EVENT+0x20,r.p64(MAGIC))
    m.uc.mem_write(EVENT+0x30,r.p64(ROOT_TAG if root_present else 0))
    m.uc.mem_write(ROOT_TAG,b'TEST')
    m.uc.mem_write(ROOT_TAG+0xc,struct.pack('<2I',1,0x40))
    m.uc.mem_write(ROOT_TAG+0x40,blob[0x3f530b:0x3f530f])
    m.uc.mem_write(ROOT_TAG+0x44,struct.pack('<I',key))
    m.uc.mem_write(ROOT_TAG+0x4c,struct.pack('<I',0x80))
    m.uc.mem_write(ROOT_TAG+0x80,payload)


def run(out):
    prior=f.STAGE/'final-receipt.json'
    assert im.sha(prior.read_bytes())==PRIOR_SHA
    for e in json.loads(prior.read_text())['files']:
        assert im.sha((ROOT/e['path']).read_bytes())==e['sha256']
    blob=(BASE/'stage2/extraction/files/nflasha3/av-cam.bin').read_bytes()
    assert im.sha(blob)==im.PINS['stage2/extraction/files/nflasha3/av-cam.bin']
    module=(n.STAGE/'official-files/nflasha15/kmod/liro.ko').read_bytes()
    kernel=(n.STAGE/'official-files/nflasha3/vmlinux.bin').read_bytes()
    events=[];cases=[]

    m=fresh(blob,module,kernel,events)
    for i in range(40):borrow(m,events,'native initial borrow'+str(i),i)
    states=[snapshot(m,'all40borrowed')]
    for i in range(40):
        dequeue(m,events,'native dequeue without optional notification'+str(i),i)
        assert m.read(POOL+0x8ade0+3*i,3)==bytes([1,1,0])
    states.append(snapshot(m,'queue_empty_all_slots_still_active'))
    assert states[-1]['queued_indices']==0 and states[-1]['active_slots']==40
    borrow(m,events,'empty queue does not make active slots borrowable',0xffffffff)
    empty=phase(m,'empty dequeue stops at original diagnostic',0x161590,x0=POOL)
    assert empty['reason']=='boundary: before_unexecuted_diagnostic';events.append(empty)
    # This old geometry is a controlled prior-content input, not a live frame.
    m.uc.mem_write(POOL+0x3e,struct.pack('<2H',1920,1080))
    old_hash=im.sha(m.read(POOL,STRIDE))
    mark(m,events,'marker2 clears selected flags after native dequeue marker1',0x15fb64,0)
    states.append(snapshot(m,'slot0_flags_clear_record_content_retained'))
    assert states[-1]['queued_indices']==0 and states[-1]['flags'][0]==[0,0,0]
    assert states[-1]['selected_record_sha256']==old_hash
    borrow(m,events,'native reborrow0 clears old geometry',0)
    states.append(snapshot(m,'slot0_reborrowed_and_native_record_cleared'))
    assert m.read(POOL,STRIDE)==bytes(STRIDE)
    assert states[-1]['queued_indices']==1 and states[-1]['flags'][0]==[1,0,0]
    # Controlled helper order only: does not establish a reachable late callback
    # in Sony's real serialized/locked/generation-bound producer and consumer.
    mark(m,events,'old index0 marker2 deliberately reapplied after reborrow',0x15fb64,0)
    states.append(snapshot(m,'index_only_marker2_now_refers_to_reused_slot'))
    assert states[-1]['flags'][0]==[1,0,1]
    dequeue(m,events,'native dequeue of reused slot with marker2 already set',0)
    states.append(snapshot(m,'both_markers_clear_reused_slot_on_controlled_order'))
    assert states[-1]['flags'][0]==[0,0,0] and states[-1]['queued_indices']==0
    c.assert_image(m,blob)
    cases.append({'name':'queue_zero_not_slot_release_and_index_reuse_boundary','states':states,
      'late_callback_reachability_or_real_camera_ABA_bug_proven':False})

    m=fresh(blob,module,kernel,events)
    for i in range(40):borrow(m,events,'composite case native borrow'+str(i),i)
    for i in range(40):
        e=composite(m,events,i,'native composite marker pair index'+str(i))
        assert e['reason']=='returned' and e['x0_after']=='0x1'
    states=[snapshot(m,'all_flags_clear_queue_still_full')]
    assert states[-1]['queued_indices']==40 and states[-1]['active_slots']==0
    borrow(m,events,'cleared flags do not bypass queued capacity40',0xffffffff)
    before=m.read(POOL,0x95000)
    sentinel=composite(m,events,0xffffffff,'native sentinel composite returns1 without pool mutation')
    assert sentinel['reason']=='returned' and sentinel['x0_after']=='0x1'
    assert m.read(POOL,0x95000)==before
    missing=composite(m,events,40,'unregistered index40 stops at original diagnostic')
    assert missing['reason']=='boundary: before_unexecuted_diagnostic'
    c.assert_image(m,blob)
    cases.append({'name':'flags_zero_not_queue_drain','states':states,
      'sentinel_noop_return1':True,'unknown_index_full_failure_return_unexecuted':True})

    notifications=[]
    for enabled in (1,0):
        m=fresh(blob,module,kernel,events)
        borrow(m,events,'optional notification case borrow0 enabled'+str(enabled),0)
        m.uc.mem_write(POOL+0x8ae58,r.p64(OWNER));m.uc.mem_write(OWNER,r.p64(PARENT))
        m.uc.mem_write(PARENT+0xc,struct.pack('<I',0x17))
        m.uc.mem_write(POOL+0x630,bytes([enabled]));m.uc.mem_write(POOL+0x63c,struct.pack('<I',7))
        e=phase(m,'native dequeue optional notification enabled'+str(enabled),0x161590,x0=POOL)
        events.append(e);state=snapshot(m,'notification boundary' if enabled else 'optional notification skipped')
        if enabled:
            assert e['reason']=='boundary: before_unbound_runtime_notification'
            assert state['queued_indices']==1 and state['flags'][0]==[1,0,0]
            assert hex(V+0x162e64) in e['pcs'] and state['selected_record_63c']==7
            arg=int(e['x0_after'],16)
            assert u32(m,arg)==7 and e['x1_after']=='0x2'
            assert m.uc.reg_read(r.reg.UC_ARM64_REG_X2)==0x17
        else:
            assert e['reason']=='returned' and e['x0_after']==hex(POOL)
            assert state['queued_indices']==0 and state['flags'][0]==[1,1,0]
        notifications.append({'enabled_byte630':enabled,'state':state,'original_fragment':e})
        c.assert_image(m,blob)

    # Locate and exercise a real source-side getter: original tag constructor,
    # original serialized lookup and memcpy, actual caller's validity store.
    # Full0x1479d8 event filling, upstream tag producer and actual MAIN unbound.
    geometry=[]
    for name,key,present in (('declared_geometry_tag',0,True),('different_tag_key',1,True),('no_tag_root',0,False)):
        m=fresh(blob,module,kernel,events)
        borrow(m,events,'tag case native borrow0 '+name,0)
        payload=bytearray(0x48)
        payload[0x2e]=5
        struct.pack_into('<2H',payload,0x36,1920,1080)
        tag_fixture(m,blob,bytes(payload),key,present)
        e=phase(m,'original source getter and caller validity '+name,0x147a2c,x19=POOL,x20=EVENT)
        events.append(e)
        assert e['reason']=='boundary: after_original_tag_getter_and_record_validity_store'
        rec=m.read(POOL,STRIDE)
        if name=='declared_geometry_tag':
            assert rec[0]==1 and rec[8:0x50]==payload
            assert struct.unpack_from('<2H',rec,0x3e)==(1920,1080) and rec[0x36]==5
        else:assert rec[:0x50]==bytes(0x50)
        geometry.append({'name':name,'fixture_key':key,'root_present':present,
          'fixture_tag_payload_hex':bytes(payload).hex(),'record_prefix_hex':rec[:0x50].hex(),
          'record_valid_byte':rec[0],'record_geometry_u16':list(struct.unpack_from('<2H',rec,0x3e)),
          'record_format_byte36':rec[0x36],'original_fragment':e})
        c.assert_image(m,blob)

    regions=[('allocator queue gate and enqueue',0x15f8c0,0x15fa10),
      ('composite and two independent markers',0x15fa10,0x15fc78),
      ('dequeue with pre-removal helper',0x161590,0x1616a8),
      ('flag clearance and optional notification',0x162c88,0x162f78),
      ('input action native borrow and fill call',0x147538,0x147628),
      ('source fill helper',0x1479d8,0x147ad8),('source geometry getter',0xa3f3c,0xa3f9c),
      ('source tag constructor and48byte export',0x91dd4,0x91e7c),
      ('serialized lookup',0x957bc,0x9589c),('actual callback marker-pair forwarding',0x138c18,0x138c3c)]
    proof={'status':'PASS_BOUNDED_ORIGINAL_FRAME_LIFETIME_AND_TAG_GEOMETRY_SOURCE',
      'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
      'original_fragments':len(events),'original_events':events,'lifetime_cases':cases,
      'notification_cases':notifications,'geometry_tag_cases':geometry,
      'original_regions':[{'name':name,'instructions':im.dump(blob,a,z,V)} for name,a,z in regions],
      'pool_947a8_is_queued_index_count_not_active_slot_count':True,
      'marker1_marker2_names_are_structural_not_hardware_completion_certificates':True,
      'geometry_getter_original_copies48bytes_to_record8':True,
      'event_tag_container_owner_links_and_order_are_explicit_fixtures':True,
      'source_fill_helper_whole_body_upstream_tag_production_transport_locks_generations_unexecuted':True,
      'native_output_PC_return_log_lock_notification_or_HAL_adapter':False,
      'original_guest_code_unchanged':True,'camera_UU_Windows_module_WBI_flash':False,
      'real_MAIN_frame_source_hardware_recording_backup_restore_or_independent_recovery':False,
      'goal_complete':False,'persistent_write_release':False}
    im.write_json(out/'frame-lifetime-results.json',proof)
    (out/'executed-source.py').write_bytes(Path(__file__).read_bytes())
    im.write_json(out/'source-receipt.json',{'script_sha256':im.sha(Path(__file__).read_bytes()),
      'avcam_sha256':im.sha(blob),'LIRO_sha256':im.sha(module),'kernel_sha256':im.sha(kernel),
      'previous_manifest_sha256':im.sha(prior.read_bytes()),'volume_uuid':im.VOLUME})
    print(json.dumps({k:proof[k] for k in ('status','original_fragments','goal_complete')}))


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
