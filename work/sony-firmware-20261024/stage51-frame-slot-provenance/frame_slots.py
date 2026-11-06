#!/usr/bin/env python3
"""Original frame-slot pool, metadata/picture framing and flag preparation.

Map-node storage and object links are declared fixtures. The original initializer
registers40indices; the original allocator chooses them, clears each record, and
returns-1/null at capacity. This is not a full controller/lock/hardware boot.
Metadata production stops before remaining fields; packets are bytes/receiver
fragments, never live transport. No native output, PC or return adapter.
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
sys.path.insert(0,str(BASE/'stage50-native-start-geometry'))
import start_geometry as s
c,n,im,r,V=s.c,s.c.n,s.im,s.r,s.V
POOL=r.ARENA+0x1c0000
NODES=r.ARENA+0x280000
SOURCE=r.ARENA+0x2a0000
PARENT=r.ARENA+0x2a1000
LEAF=r.ARENA+0x2a2000
OUT=r.ARENA+0x2a3000
VIDEO=r.ARENA+0x2a4000
META=r.ARENA+0x2a5000
IDENTITY=r.ARENA+0x2a6000
PACKET=r.ARENA+0x2b0000
DEFAULTS=r.ARENA+0x2b1000
AUX=r.ARENA+0x2b2000
MATRIX=r.ARENA+0x2b3000
INPUT=r.ARENA+0x2c0000
UID=0x2a
STRIDE=0xd18
PRIOR_SHA='d69cc8a9d4e8b21759716588af80880f6ac0cc22152b0997ac265aea3a6ceedc'
RANGES=[(0x15ed14,0x15eedc+4),(0x15f8c0,0x15fa10),
  (0x15f4ec,0x15f524),(0x14fdb0,0x14fdc0),(0x136378,0x13641c),
  (0x136df0,0x136e28),(0x1382f4,0x138354),(0x1383d0,0x138408),
  (0x249ad0,0x249bbc),(0x249c00,0x249c20),(0x24a034,0x24a044),(0x24a098,0x24a0b0),
  (0x246274,0x24641c),(0x248d4c,0x248de8),(0x24952c,0x249548),
  (0x22c35c,0x22c3ac),(0x27cf44,0x27cf58),
  (0x25465c,0x254674),(0x25492c,0x254944),
  (0x27da9c,0x27dab4),(0xd80,0xeec)]


class Guest(n.Guest):
    def __init__(self,blob,module,kernel):
        super().__init__(blob,module,kernel)
        self.ranges.extend((V+a,V+z) for a,z in RANGES)
        self.boundaries.update({V+0x136418:'before_remaining_metadata_production',
          V+0x0960a4:'before_message_object_constructor_and_transport',
          V+0x27d528:'before_unexecuted_diagnostic',
          V+0x251460:'before_typed_Start_state_event_wrapper',
          V+0x2518dc:'before_typed_encode_picture_state_event_wrapper'})
        self.store_count=0;self.store_digest=hashlib.sha256()

    def store(self,u,access,address,size,value,user):
        if V+0x1ec<=address and address+size<=V+0x884:
            return super().store(u,access,address,size,value,user)
        if not any(a<=address and address+size<=a+b for a,b in ((r.ARENA,r.ARENA_SIZE),(r.STACK,r.STACK_SIZE))):
            return super().store(u,access,address,size,value,user)
        # Observe all stores and enforce the inherited arena/stack boundary.
        # Summarize repetitive native clear stores rather than huge JSON lists.
        pc=u.reg_read(r.reg.UC_ARM64_REG_PC)
        self.store_count+=1;self.store_digest.update(struct.pack('<QQI',pc,address,size))


def phase(m,label,start,**regs):
    m.store_count=0;m.store_digest=hashlib.sha256()
    event=c.phase(m,label,V+start,**regs)
    event['approved_arena_stack_store_count']=m.store_count
    event['approved_store_PC_address_size_sha256']=m.store_digest.hexdigest()
    event['store_trace_scope']='All stores range-checked; repetitive approved stores represented by count/digest. No write-output replacement.'
    event['x1_after']=hex(m.uc.reg_read(r.reg.UC_ARM64_REG_X1))
    global LAST_PHASE
    LAST_PHASE=event
    return event


def new_guest(blob,module,kernel):
    m=Guest(blob,module,kernel);event=n.link(m)
    m.uc.mem_protect(V,4096,r.unicorn.UC_PROT_READ|r.unicorn.UC_PROT_EXEC)
    return m,event


def run(out):
    prior=s.STAGE/'final-receipt.json';assert im.sha(prior.read_bytes())==PRIOR_SHA
    for e in json.loads(prior.read_text())['files']:assert im.sha((ROOT/e['path']).read_bytes())==e['sha256']
    blob=(BASE/'stage2/extraction/files/nflasha3/av-cam.bin').read_bytes()
    assert im.sha(blob)==im.PINS['stage2/extraction/files/nflasha3/av-cam.bin']
    module=(n.STAGE/'official-files/nflasha15/kmod/liro.ko').read_bytes()
    kernel=(n.STAGE/'official-files/nflasha3/vmlinux.bin').read_bytes()
    m,load=new_guest(blob,module,kernel);events=[load]
    # Explicit initial map-node pool, not a claimed native whole-controller ctor.
    m.uc.mem_write(POOL,bytes(0x95000));tree=POOL+0x8af60
    m.uc.mem_write(tree+0x670,struct.pack('<3I',40,0,0))
    for i in range(40):m.uc.mem_write(tree+0x680+i*8,r.p64(NODES+i*0x28))
    init=phase(m,'original frame-record pool initializer and40native map insertions',0x15ed14,x0=POOL)
    assert init['reason']=='returned';events.append(init)
    assert m.read(POOL+0x8af38,8)==r.p64(POOL)
    assert int.from_bytes(m.read(POOL+0x8af40,4),'little')==40*STRIDE==0x20bc0
    assert m.read(POOL,40*STRIDE)==bytes(40*STRIDE)
    assert int.from_bytes(m.read(tree+0x670,4),'little')==0
    for i in range(40):
        assert int.from_bytes(m.read(NODES+i*0x28+0x18,4),'little')==i
        assert m.read(NODES+i*0x28+0x20,8)==r.p64(POOL+0x8ade0+3*i)
    init2=phase(m,'complete original companion-storage initializer',0x15ee7c,x0=POOL)
    assert init2['reason']=='returned';events.append(init2)
    assert m.read(POOL+0x8af50,8)==r.p64(POOL+0x20bc0)
    assert int.from_bytes(m.read(POOL+0x8af58,4),'little')==0x63420
    allocations=[]
    # Prior-content controls are explicit host inputs. Native allocator clears
    # only each chosen record before returning its native-generated index.
    m.uc.mem_write(POOL,bytes([0xa5])*(40*STRIDE))
    for i in range(41):
        m.uc.mem_write(OUT,r.p64(0x99999999))
        event=phase(m,'complete original frame allocator call'+str(i),0x15f8c0,x0=POOL,x1=OUT)
        assert event['reason']=='returned';events.append(event)
        index=int(event['x0_after'],16)&0xffffffff;pointer=int.from_bytes(m.read(OUT,8),'little')
        assert index==(i if i<40 else 0xffffffff)
        assert pointer==(POOL+i*STRIDE if i<40 else 0)
        if i<40:
            assert m.read(pointer,STRIDE)==bytes(STRIDE)
            assert m.read(POOL+0x8ade0+3*i,3)==b'\1\0\0'
            if i<39:assert m.read(POOL+(i+1)*STRIDE,STRIDE)==bytes([0xa5])*STRIDE
        allocations.append({'call':i,'native_index':index,'native_record_pointer':hex(pointer),
          'record_cleared_by_original_allocator':i<40,'original_fragment':event})
    assert int.from_bytes(m.read(POOL+0x947a8,4),'little')==40
    # Native source getters are reached via their original frontend forwarders.
    m.uc.mem_write(SOURCE,r.p64(PARENT));m.uc.mem_write(PARENT,r.p64(LEAF))
    m.uc.mem_write(LEAF+8,bytes([UID]));m.uc.mem_write(SOURCE+8,r.p64(POOL-0xa0))
    m.uc.mem_write(VIDEO,bytes(0x100))
    m.uc.mem_write(r.SP-0x100,bytes([0xc3])*0x200)
    meta=phase(m,'original Start metadata prefix through native pool getters',0x136378,
      x0=SOURCE,x1=VIDEO,x2=0,x3=0,x4=0,x5=0)
    assert meta['reason']=='boundary: before_remaining_metadata_production';events.append(meta)
    base_sp=int(meta['SP_after'],16);metadata=m.read(base_sp+0x18,0x88)
    assert int.from_bytes(metadata[:4],'little')==UID
    assert struct.unpack_from('<Q',metadata,8)[0]==POOL+0x20bc0
    assert struct.unpack_from('<I',metadata,0x10)[0]==0x120c
    assert struct.unpack_from('<Q',metadata,0x18)[0]==POOL
    assert struct.unpack_from('<I',metadata,0x20)[0]==40
    # Rest is an unfinished native prefix/explicit seed, not valid Start data.
    m.uc.mem_write(META,metadata)
    send=phase(m,'original Start packet copy before message construction',0x136df0,x0=SOURCE,x1=META)
    assert send['reason']=='boundary: before_message_object_constructor_and_transport';events.append(send)
    start_packet=m.read(int(send['SP_after'],16)+0x1b0,0x90)
    assert struct.unpack_from('<3H',start_packet,0)==(0x2103,0x102,0x90)
    assert start_packet[8:]==metadata
    m.uc.mem_write(s.STATE,bytes(0x32000));m.uc.mem_write(s.STATE,r.p64(IDENTITY))
    m.uc.mem_write(IDENTITY,struct.pack('<I',UID))
    m.uc.mem_write(s.STATE+8,r.p64(r.ARENA+0x170000))
    m.uc.mem_write(PACKET,start_packet)
    recv=phase(m,'original matching-UID Start receiver to mandatory diagnostic',0x249ad0,x0=s.STATE,x1=PACKET)
    assert recv['reason']=='boundary: before_unexecuted_diagnostic'
    assert hex(V+0x249bb4) in recv['pcs'];events.append(recv)
    picture_cases=[]
    for index,final in ((allocations[0]['native_index'],0),(allocations[39]['native_index'],0),
      (allocations[1]['native_index'],1)):
        event=phase(m,'original picture API and packet prefix index'+str(index)+' final'+str(final),0x1382f4,
          x0=SOURCE,x1=index,x2=0,x3=final,x4=0,x5=0,x6=0,x7=0)
        assert event['reason']=='boundary: before_message_object_constructor_and_transport';events.append(event)
        packet=m.read(int(event['SP_after'],16)+0x1b0,0x30)
        assert struct.unpack_from('<3H',packet,0)==(0x2103,0x103,0x30)
        assert struct.unpack_from('<I',packet,8+0x14)[0]==index and packet[8+0x10]==final
        m.uc.mem_write(PACKET,packet)
        receiver=phase(m,'original picture receiver index'+str(index)+' final'+str(final),0x249ad0,x0=s.STATE,x1=PACKET)
        assert receiver['reason']==('boundary: before_unexecuted_diagnostic' if final else 'boundary: before_typed_encode_picture_state_event_wrapper')
        if not final:assert receiver['x1_after']==hex(PACKET+8)
        events.append(receiver);picture_cases.append({'native_allocator_index':index,'final':final,
          'packet_hex':packet.hex(),'original_fragments':[event,receiver]})
    wrong=bytearray(start_packet);struct.pack_into('<I',wrong,8,UID+1);m.uc.mem_write(PACKET,bytes(wrong))
    rejected=phase(m,'original different-UID receiver returns without dispatch',0x249ad0,x0=s.STATE,x1=PACKET)
    assert rejected['reason']=='returned' and hex(V+0x249bb4) not in rejected['pcs'];events.append(rejected)
    # Full original start-input flag helper on declared flags/defaults. The
    # native lock/default-query wrapper remains unexecuted, as in stage50.
    old=json.loads((s.STAGE/'run-corrected-20261025/start-geometry-results.json').read_text())
    input_bytes=bytes.fromhex(old['cases'][0]['start_input_hex'])
    flags=[]
    for mode in ('inactive_override','cache_byte36_set','descriptor_guard','active_override_needs_diagnostic'):
        component=s.STATE+0x20;qos=component+0x2aa20
        m.uc.mem_write(component,bytes(0x2ac00));m.uc.mem_write(component+0x738,struct.pack('<I',14))
        m.uc.mem_write(component+0x8e8,b'\x07');m.uc.mem_write(INPUT,input_bytes)
        m.uc.mem_write(DEFAULTS,bytes(0x38));m.uc.mem_write(AUX,bytes(0x80));m.uc.mem_write(MATRIX,bytes(0x300))
        if mode=='cache_byte36_set':m.uc.mem_write(qos+0x36,b'\1\x09')
        if mode=='descriptor_guard':m.uc.mem_write(component+0x750,struct.pack('<I',1))
        if mode=='active_override_needs_diagnostic':
            m.uc.mem_write(qos+0xc,b'\1');m.uc.mem_write(qos+0xfc,struct.pack('<I',1))
        event=phase(m,'complete original flag helper '+mode,0x246274,
          x0=component,x1=INPUT,x2=AUX,x3=MATRIX,x4=DEFAULTS)
        if mode in ('inactive_override','cache_byte36_set'):
            assert event['reason']=='returned' and event['x0_after']=='0x1'
            assert m.read(INPUT,5)==bytes([7,1,0,2,0])
            if mode=='cache_byte36_set':assert m.read(INPUT+0x118,4)==struct.pack('<I',9)
        else:assert event['reason']=='boundary: before_unexecuted_diagnostic'
        events.append(event);flags.append({'mode':mode,'input_after_hex':m.read(INPUT,0x170).hex(),'original_fragment':event})
    selectors=[]
    for entry,expected in ((0x25465c,1),(0x25466c,5),(0x25492c,1),(0x25493c,7)):
        event=phase(m,'original guard or next selector '+hex(entry),entry)
        assert event['reason']=='returned' and int(event['x0_after'],16)==expected
        events.append(event);selectors.append(event)
    typed=[]
    for event,state,table,guard,action,nextfn,body in (
      (4,4,0x37f718,0x25465c,0x254664,0x25466c,0x24bec0),
      (6,6,0x37f9b8,0x25492c,0x254934,0x25493c,0x24cda8)):
        assert struct.unpack_from('<3Q',blob,table+state*24)==(V+guard,V+action,V+nextfn)
        name=im.cstring(blob,struct.unpack_from('<Q',blob,0xbdde38+event*8)[0]-V)
        typed.append({'event':event,'name':name,'source_state':state,'table':hex(table),
          'guard':hex(guard),'action':hex(action),'next_selector':hex(nextfn),'body':hex(body),
          'next_selector_is_not_completed_transition':True})
    regions=[('frame record pool initializer',0x15ed14,0x15edc4),
      ('native map insertion',0x15edc4,0x15ee7c),('companion storage initializer',0x15ee7c,0x15eee0),
      ('frame allocator and chosen-record clear',0x15f8c0,0x15fa10),
      ('native storage getters',0x15f4ec,0x15f524),('frontend getter forwarders',0x14fdb0,0x14fdc0),
      ('metadata production prefix',0x136378,0x136418),('Start packet prefix',0x136df0,0x136e24),
      ('picture API and sender prefix',0x1382f4,0x138354),('picture packet prefix',0x1383d0,0x138408),
      ('typed receiver and Start branch',0x249ad0,0x249c00),('picture/final branch',0x249c00,0x249c68),
      ('normal picture typed forwarding',0x24a034,0x24a044)]
    c.assert_image(m,blob)
    proof={'status':'PASS_ORIGINAL_FRAME_SLOT_POOL_PROVENANCE_PACKETS_AND_BOUNDED_FLAG_PREPARATION',
      'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'original_fragments':len(events),
      'original_events':events,'allocations':allocations,'metadata_prefix_hex':metadata.hex(),
      'Start_packet_hex':start_packet.hex(),'picture_cases':picture_cases,'different_UID_receiver':rejected,
      'flag_cases':flags,'typed_bindings':typed,'selector_fragments':selectors,
      'original_regions':[{'name':name,'instructions':im.dump(blob,a,z,V)} for name,a,z in regions],
      'frame_slot_count':40,'frame_slot_stride':STRIDE,'frame_array_bytes':40*STRIDE,
      'index_namespace':'Frame-slot index generated by native allocator and copied by native picture API; not a fixed encoding-channel ID or observed live MAIN index.',
      'identity_namespace':'Packet payload UID derives from an8-bit parent field and receiver comparesu32; fixture0x2a is not sourceID0x805700f9 or current camera identity.',
      'metadata_prefix_is_not_complete_Start_param':True,
      'partial_metadata_remaining_helpers_transport_constructor_dispatch_logs_locks_live_controller_init_unexecuted':True,
      'map_free_node_pool_object_links_and_optional_flags_are_declared_fixtures':True,
      'actual_live_frame_fill_owner_epoch_synchronization_HW_and_recovery_verified':False,
      'original_guest_code_unchanged_no_native_output_or_return_adapter':True,
      'camera_UU_Windows_module_WBI_flash':False,'goal_complete':False,'persistent_write_release':False}
    im.write_json(out/'frame-slot-results.json',proof)
    (out/'executed-source.py').write_bytes(Path(__file__).read_bytes())
    im.write_json(out/'source-receipt.json',{'script_sha256':im.sha(Path(__file__).read_bytes()),
      'avcam_sha256':im.sha(blob),'LIRO_sha256':im.sha(module),'kernel_sha256':im.sha(kernel),
      'previous_manifest_sha256':im.sha(prior.read_bytes()),'volume_uuid':im.VOLUME})
    print(json.dumps({k:proof[k] for k in ('status','original_fragments','frame_slot_count','frame_slot_stride','metadata_prefix_is_not_complete_Start_param','goal_complete')}))


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',required=True)
    args=parser.parse_args();im.volume();out=Path(args.output).resolve()
    assert STAGE in out.parents and not out.exists();out.mkdir()
    try:run(out)
    except Exception:
        (out/'attempt-source.py').write_bytes(Path(__file__).read_bytes())
        if 'LAST_PHASE' in globals():im.write_json(out/'last-phase-at-failure.json',LAST_PHASE)
        im.write_json(out/'attempt-failure.json',{'traceback':traceback.format_exc(),'passing_result':False});raise


if __name__=='__main__':main()
