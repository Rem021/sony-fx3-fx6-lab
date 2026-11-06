#!/usr/bin/env python3
"""Original ImageSizeInfo construction/serialization and complete frame fill.

Runtime object storage, input values, backing buffer and ownership are explicit
RAM fixtures. Original typed setters, container constructor, publisher, tag
lookup and whole0x1479d8 body produce all observed output. No camera or adapter.
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
sys.path.insert(0,str(BASE/'stage52-frame-lifetime-and-fill'))
import frame_lifetime as l
im,r,V,n,c=l.im,l.r,l.V,l.n,l.c
POOL,NODES,OUT,STRIDE=l.POOL,l.NODES,l.OUT,l.STRIDE
EVENT=r.ARENA+0x2f0000
BUFFER=r.ARENA+0x2f1000
COMPONENT=r.ARENA+0x310000
IMAGE=r.ARENA+0x320000
PAYLOAD=r.ARENA+0x321000
OBJECTS=r.ARENA+0x330000
BUFFER_SIZE=0x2000
PRIOR_SHA='7effd8b0d61f02bc41110d473031f8dcabdd8171102adbd9c957362cd4e17dfc'
EXTRA=[(0x1479d8,0x147ad8),(0x148454,0x1484a8),(0x12bd78,0x12bfbc),
  (0xa3fb0,0xa4268),(0xa43c4,0xa4438),(0xa46f0,0xa4764),
  (0xa4884,0xa4894),(0xa4894,0xa48ec),
  (0x8f210,0x8f2bc),(0x8fae8,0x8fb94),(0x8fef0,0x8ff9c),
  (0x9186c,0x91914),(0x91b78,0x91c24),(0x91dd4,0x92138),
  (0x92a60,0x92b04),(0x940e4,0x94190),(0x94478,0x945b8),
  (0x94b54,0x94d14),(0x94d84,0x94e04),(0x95178,0x951a0),
  (0x951a4,0x95228),(0x952d4,0x9547c),(0x9561c,0x95644),
  (0x9572c,0x957bc),(0x9589c,0x959c0),(0x959c0,0x95a08),
  (0x95b9c,0x95be0),(0x95c30,0x95ce8),(0x27da84,0x27da9c),
  (0x24cfb8,0x24d110),(0x24d160,0x24d1c4),
  (0x27b9a8,0x27b9c8),(0x27b7ac,0x27b81c)]
# type key, original ctor, actual typed publisher thunk, record validity field.
TAGS=[(1,0x94478,0x95c44,0x50),(5,0x8f210,0x95c5c,0x9c),
  (2,0x91b78,0x95c34,0x59),(10,0x940e4,0x95c84,0x438),
  (4,0x8fef0,0x95c54,0x4bc),(3,0x8fae8,0x95c4c,0x5f0),
  (22,0x92a60,0x95cdc,0x62c),(24,0x9186c,0x95ce4,None)]
SETTERS=[(0x92070,'format'),(0x920e8,'packing'),
  (0x91f6c,'w'),(0x91f80,'h'),(0x91f94,'zero'),(0x91fa8,'zero'),
  (0x91fbc,'w'),(0x91fd0,'h'),(0x91fe4,'zero'),(0x91ff8,'zero'),
  (0x9200c,'w'),(0x92020,'h')]


class Guest(l.Guest):
    def __init__(self,blob,module,kernel):
        super().__init__(blob,module,kernel)
        self.ranges.extend((V+a,V+z) for a,z in EXTRA)
        self.boundaries.pop(V+0x147a44)
        self.boundaries[V+0x24d1c0]='before_real_locked_Start_wrapper'


def phase(m,label,start,**regs):
    result=l.phase(m,label,start,**regs)
    global LAST_PHASE
    LAST_PHASE=result
    return result


def call(m,events,label,start,**regs):
    e=phase(m,label,start,**regs);events.append(e)
    assert e['reason']=='returned',e['reason']
    assert e['SP_after']==hex(r.SP)
    return e


def fresh(blob,module,kernel,events):
    m=Guest(blob,module,kernel);events.append(n.link(m))
    m.uc.mem_protect(V,4096,r.unicorn.UC_PROT_READ|r.unicorn.UC_PROT_EXEC)
    m.uc.mem_write(POOL,bytes(0x95000));tree=POOL+0x8af60
    m.uc.mem_write(tree+0x670,struct.pack('<3I',40,0,0))
    for i in range(40):m.uc.mem_write(tree+0x680+i*8,r.p64(NODES+i*0x28))
    call(m,events,'original40slot pool initializer',0x15ed14,x0=POOL)
    m.uc.mem_write(EVENT,bytes(0x100));m.uc.mem_write(BUFFER,bytes(BUFFER_SIZE))
    e=call(m,events,'complete native SSYC container constructor on supplied backing storage',0x95b9c,
      x0=EVENT+8,x1=BUFFER,x2=BUFFER_SIZE,x3=0)
    assert m.read(BUFFER,4)==b'SSYC' and l.u32(m,BUFFER+0xc)==0
    m.uc.mem_write(COMPONENT,bytes(0x1000))
    m.uc.mem_write(EVENT+0x58,r.p64(r.ARENA+0x3c0000))
    m.uc.mem_write(EVENT+0x60,r.p64(r.ARENA+0x3c1000))
    return m


def typed_name(blob,vt):
    ti=struct.unpack_from('<Q',blob,vt+8)[0]-V
    nm=struct.unpack_from('<Q',blob,ti+8)[0]-V
    return im.cstring(blob,nm)


def image(m,events,width,height,fmt,label):
    call(m,events,'original ImageSizeInfo ctor '+label,0x91dd4,x0=IMAGE)
    assert l.u32(m,IMAGE+8)==0 and l.u32(m,IMAGE+0x18)==0x48
    values={'w':width,'h':height,'format':fmt,'packing':1,'zero':0}
    for entry,meaning in SETTERS:
        call(m,events,'original ImageSizeInfo setter '+meaning+' '+hex(entry)+' '+label,
          entry,x0=IMAGE,x1=values[meaning])
    call(m,events,'original ImageSizeInfo payload export '+label,0x91e68,x0=IMAGE,x1=PAYLOAD)
    payload=m.read(PAYLOAD,0x48)
    assert payload==m.read(IMAGE+0x20,0x48)
    assert payload[0x20:0x22]==bytes([fmt,1])
    assert struct.unpack_from('<10H',payload,0x2e)==(width,height,0,0,width,height,0,0,width,height)
    e=call(m,events,'complete native ImageSizeInfo event publisher '+label,0xa4894,x0=EVENT,x1=PAYLOAD)
    assert e['x0_after']=='0x1'
    return payload


def add_tags(m,events,omit):
    records=[]
    for i,(key,ctor,pub,valid) in enumerate(TAGS):
        if key in omit:continue
        obj=OBJECTS+i*0x1000
        call(m,events,'native tag constructor key'+str(key),ctor,x0=obj)
        assert l.u32(m,obj+8)==key
        size=l.u32(m,obj+0x18);ptr=int.from_bytes(m.read(obj+0x10,8),'little')
        assert obj<=ptr and ptr+size<=obj+0x1000
        initial=m.read(ptr,size)
        e=call(m,events,'native typed tag publisher key'+str(key),pub,x0=EVENT+8,x1=obj)
        assert e['x0_after']=='0x0'
        records.append({'native_type_key':key,'original_ctor':hex(ctor),'original_publisher':hex(pub),
          'native_payload_bytes':size,'native_payload_sha256':im.sha(initial),
          'record_validity_offset':None if valid is None else hex(valid)})
    return records


def fill(m,events,index,label,expected_image,expected_flags):
    e=call(m,events,'native borrow frame slot'+str(index)+' '+label,0x15f8c0,x0=POOL,x1=OUT)
    assert int(e['x0_after'],16)==index
    record=POOL+index*STRIDE
    assert int.from_bytes(m.read(OUT,8),'little')==record and m.read(record,STRIDE)==bytes(STRIDE)
    before=l.snapshot(m,'before full frame fill',index)
    e=call(m,events,'complete original frame fill0x1479d8 '+label,0x1479d8,x0=COMPONENT,x1=EVENT,x2=record)
    data=m.read(record,STRIDE)
    flags={hex(k):data[k] for k in (0,0x50,0x59,0x9c,0x438,0x4bc,0x5f0,0x62c)}
    assert flags=={hex(k):v for k,v in expected_flags.items()}
    if expected_image is not None:
        assert data[0x28:0x4a]==expected_image[0x20:0x42]
    else:assert data[8:0x10]==bytes(8) and data[0x18:0x50]==bytes(0x38)
    assert data[0x10:0x18]==m.read(EVENT+0x58,8)
    assert data[0x640:0x648]==m.read(EVENT+0x60,8)
    after=l.snapshot(m,'after full frame fill',index)
    assert after['queued_indices']==before['queued_indices']==index+1
    assert after['flags']==before['flags']
    assert e['x0_after']=='0x1' # tail tag24 present; this is not aggregate validity.
    # Independent encoder packing fragment, with the actual just-filled record
    # left in the same guest. Whole action/default query/logs/locks unexecuted.
    # Only the external matching descriptor's height and entry registers are
    # declared. No record/geometry/format output patch is made after native fill.
    target_height=struct.unpack_from('<H',expected_image,0x38)[0] if expected_image is not None else 1080
    m.uc.mem_write(r.SP+0xb8,bytes([0xc3])*0x170)
    m.uc.mem_write(r.SP+0xca,struct.pack('<H',target_height))
    e2=phase(m,'independent original encoder packing of native-filled slot '+label,0x24cfb8,
      x19=COMPONENT,x24=r.SP+0xc0,x26=record+0x48,x27=record+0x36,x22=0,x23=0)
    events.append(e2)
    assert e2['reason']==('boundary: before_real_locked_Start_wrapper' if expected_image is not None
      else 'boundary: before_unexecuted_diagnostic')
    packed=m.read(r.SP+0xb8,0x170)
    native_fmt=struct.unpack_from('<I',packed,0xf8)[0]
    assert native_fmt==(data[0x28] if data[0x28] in range(1,8) else 8)
    assert struct.unpack_from('<2H',packed,0xe8)==struct.unpack_from('<2H',data,0x3e)
    assert m.read(record,STRIDE)==data
    return {'label':label,'slot_index':index,'record_hex':data.hex(),'validity_bytes':flags,
      'format_byte28':data[0x28],'packing_byte29':data[0x29],
      'geometry_10u16_at36':list(struct.unpack_from('<10H',data,0x36)),
      'native_function_return':1,'tail_return_is_not_aggregate_frame_validity':True,
      'queue_before':before['queued_indices'],'queue_after':after['queued_indices'],
      'source_payload_hex':None if expected_image is None else expected_image.hex(),
      'native_fragment':e,'encoder_pack_fragment':e2,
      'independent_encoder_pack_input_hex':packed.hex(),
      'encoder_input_e8_ea_geometry':list(struct.unpack_from('<2H',packed,0xe8)),
      'encoder_input_f8_format':native_fmt,'external_descriptor_height_fixture':target_height,
      'whole_encoder_action_default_query_logs_locks_or_Start_unexecuted':True}


def run(out):
    prior=l.STAGE/'final-receipt.json';assert im.sha(prior.read_bytes())==PRIOR_SHA
    for e in json.loads(prior.read_text())['files']:
        assert im.sha((ROOT/e['path']).read_bytes())==e['sha256']
    blob=(BASE/'stage2/extraction/files/nflasha3/av-cam.bin').read_bytes()
    assert im.sha(blob)==im.PINS['stage2/extraction/files/nflasha3/av-cam.bin']
    module=(n.STAGE/'official-files/nflasha15/kmod/liro.ko').read_bytes()
    kernel=(n.STAGE/'official-files/nflasha3/vmlinux.bin').read_bytes()
    events=[];cases=[];all_flags={k:1 for k in (0,0x50,0x59,0x9c,0x438,0x4bc,0x5f0,0x62c)}
    m=fresh(blob,module,kernel,events)
    tags=add_tags(m,events,set())
    raw=image(m,events,1920,1080,5,'HD format5')
    assert l.u32(m,BUFFER+0xc)==9
    cases.append(fill(m,events,0,'all9tags HD format5',raw,all_flags))
    directory_before=m.read(BUFFER,BUFFER_SIZE)
    raw2=image(m,events,1280,720,6,'replace existing image tag with720 format6')
    assert l.u32(m,BUFFER+0xc)==9
    cases.append(fill(m,events,1,'same native event after ImageSizeInfo replacement',raw2,all_flags))
    assert m.read(POOL+0x28,0x22)==bytes.fromhex(cases[0]['record_hex'])[0x28:0x4a]
    replaced=m.read(BUFFER,BUFFER_SIZE)
    changed=[i for i,(a,b) in enumerate(zip(directory_before,replaced)) if a!=b]
    assert changed
    c.assert_image(m,blob)
    for name,omit,has_image in (('missing ImageSizeInfo',set(),False),('missing CameraInfo',{5},True)):
        m=fresh(blob,module,kernel,events);add_tags(m,events,omit)
        payload=image(m,events,1920,1080,5,name) if has_image else None
        flags=dict(all_flags);flags[0 if not has_image else 0x9c]=0
        cases.append(fill(m,events,0,name,payload,flags))
        c.assert_image(m,blob)
    regions=[('complete frame fill',0x1479d8,0x147ad8),
      ('camera translation helper',0x148454,0x1484a8),
      ('native ImageSizeInfo publisher',0xa4894,0xa48ec),
      ('ImageSizeInfo ctor/import/export',0x91dd4,0x91e7c),
      ('ImageSizeInfo geometry setters',0x91f44,0x92138),
      ('native event container constructor',0x95b9c,0x95be0),
      ('native tag serialization',0x952d4,0x9547c),
      ('actual encoder input format load',0x24d024,0x24d038)]
    proof={'status':'PASS_NATIVE_TYPED_TAG_SERIALIZATION_AND_COMPLETE_FRAME_FILL',
      'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
      'original_fragments':len(events),'original_events':events,'cases':cases,
      'original_tag_constructor_publishers':tags,
      'ImageSizeInfo_RTTI':typed_name(blob,0x33e8a0),
      'CameraInfo_RTTI':typed_name(blob,0x33e2f0),
      'same_event_replacement_did_not_append_duplicate_key':True,
      'same_event_replacement_changed_buffer_offsets':changed,
      'source_format_at_record28_not_record36':True,
      'source_geometry_10u16_starts_record36':True,
      'native_function_return1_is_tail_tag24_result_not_aggregate_validity':True,
      'native_filled_records_consumed_unchanged_by_independent_encoder_pack_fragment':True,
      'original_regions':[{'name':name,'instructions':im.dump(blob,a,z,V)} for name,a,z in regions],
      'declared_RAM_input_values_storage_object_links_and_ownership_not_real_MAIN_or_sensor':True,
      'native_output_PC_return_log_lock_notification_or_HAL_adapter':False,
      'original_guest_code_unchanged':True,'camera_UU_Windows_module_WBI_flash':False,
      'live_source_graph_scheduling_transport_fullStart_Hal_hardware_or_recovery_verified':False,
      'goal_complete':False,'persistent_write_release':False}
    im.write_json(out/'native-frame-fill-results.json',proof)
    (out/'executed-source.py').write_bytes(Path(__file__).read_bytes())
    im.write_json(out/'source-receipt.json',{'script_sha256':im.sha(Path(__file__).read_bytes()),
      'avcam_sha256':im.sha(blob),'LIRO_sha256':im.sha(module),'kernel_sha256':im.sha(kernel),
      'previous_manifest_sha256':im.sha(prior.read_bytes()),'volume_uuid':im.VOLUME})
    print(json.dumps({k:proof[k] for k in ('status','original_fragments','ImageSizeInfo_RTTI','goal_complete')}))


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
