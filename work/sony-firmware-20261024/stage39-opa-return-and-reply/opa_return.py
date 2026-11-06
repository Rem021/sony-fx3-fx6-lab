#!/usr/bin/env python3
"""Original OPA return/index removal and type3-message cleanup, guest only.

Message origin, current generation and actual HAL completion are fixtures, not
proved. Returns distinguish cleanup result from copied, unnamed message bytes. No camera access,
whole HAL request, runtime/output adapter or physical recovery is implemented.
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
sys.path.insert(0,str(BASE/'stage38-imola-parameter-copy'))
import parameter_copy as t
p,w,r,V=t.p,t.w,t.r,t.V
MAPS=[w.A+n for n in (0x1160,0x11e8,0x1270,0x12f8)]
BUFFERS=[t.BUFFER+n*0x1000 for n in range(4)]
NODES=[t.NODE+n*0x100 for n in range(4)]
THIRD=r.ARENA+0x340000
FOURTH=r.ARENA+0x341000
MESSAGE=r.ARENA+0x390000
OUTPUT=r.ARENA+0x391000
OWNER_NODE=r.ARENA+0x3b0000
RETURN_POOL=r.ARENA+0x3c0000
IFACE=r.ARENA+0x200000
EXTRA=[(0x21c114,0x21c218),(0x22c6f8,0x22c7d4),(0x21d704,0x21d83c),
       (0x225934,0x225b74),(0x227870,0x227918),(0x228bbc,0x228bd4)]


class Guest(t.Guest):
    def __init__(self,blob,code,ro):
        super().__init__(blob,code,ro)
        self.ranges.extend((V+a,V+z) for a,z in EXTRA)


def setup(blob,code,ro,descriptor):
    # Reuse the original source/preparation functions with our extended guest.
    original_class=t.Guest
    try:
        t.Guest=Guest
        m,events,prototypes,_=t.setup(blob,code,ro,descriptor,True)
    finally:t.Guest=original_class
    assembled=t.assemble(m,events);assert assembled['target']==16000000
    m.uc.mem_write(THIRD,bytes((i*7+3)&255 for i in range(0x80)))
    m.uc.mem_write(FOURTH,bytes((i*11+5)&255 for i in range(0x300)))
    m.uc.mem_write(w.A+0x1038,r.p64(t.POOL))
    m.uc.mem_write(t.POOL,bytes(0x2ab0))
    w.put32(m,t.POOL,4);w.put32(m,t.POOL+4,4)
    sources=[(t.COMMON,0x40),(t.CODEC,0x1c0),(THIRD,0x80),(FOURTH,0x300)]
    copied=[]
    for i,((source,length),dest,node,mapping) in enumerate(zip(sources,BUFFERS,NODES,MAPS)):
        m.uc.mem_write(t.POOL+0x10+i*16,struct.pack('<QQ',dest,0x400))
        m.uc.mem_write(dest,bytes([0xd7])*0x400)
        m.uc.mem_write(mapping,bytes(0x88));w.put32(m,mapping+0x68,1)
        m.uc.mem_write(mapping+0x78,r.p64(node));m.uc.mem_write(node,bytes([0xc9])*0x40)
        m.uc.mem_write(t.PAIR,bytes(16))
        event=t.original(m,'native copy/index block'+str(i),0x21a3b8,
            x0=w.A,x1=t.PAIR,x2=source,x3=length,x4=mapping,x5=0)
        assert event['reason']=='returned' and event['x0_to_x5'][0]=='0x0'
        assert m.read(dest,length)==m.read(source,length)
        assert int.from_bytes(m.read(mapping,8),'little')==node
        events.append(event);copied.append(m.read(dest,0x400))
    assert int.from_bytes(m.read(t.POOL,4),'little')==0
    # Actual transport/producer is unbound. These messages and pending slots
    # only establish behavior of the original local cleanup implementation.
    m.uc.mem_write(w.A+0x10,r.p64(RETURN_POOL))
    m.uc.mem_write(RETURN_POOL,bytes(0x1020))
    m.uc.mem_write(w.A+0x18,struct.pack('<I',1));w.put32(m,w.A+0x20,0)
    m.uc.mem_write(w.A+0x30,r.p64(MESSAGE))
    raw=bytearray(0x80);raw[2]=3;raw[3]=0;struct.pack_into('<H',raw,4,0x1234)
    raw[0xa]=0;raw[0xb]=0x56
    m.uc.mem_write(MESSAGE,bytes(raw));m.uc.mem_write(OUTPUT,bytes([0xa5])*8)
    # Original interface thunk resolves a synthetic keyed owner entry, then
    # delegates to the same cleanup function. No actual registry observed.
    m.uc.mem_write(OWNER_NODE,bytes(0x28));m.uc.mem_write(OWNER_NODE+0x20,r.p64(w.A-8))
    m.uc.mem_write(IFACE+0x55f10,r.p64(OWNER_NODE))
    return m,events,prototypes,assembled,copied


def state(m):
    return {'pool_count':int.from_bytes(m.read(t.POOL,4),'little'),
      'pool_write_index':int.from_bytes(m.read(t.POOL+4,4),'little'),
      'pool_read_index':int.from_bytes(m.read(t.POOL+8,4),'little'),
      'index_roots':[hex(int.from_bytes(m.read(x,8),'little')) for x in MAPS],
      'index_node_available':[int.from_bytes(m.read(x+0x68,4),'little') for x in MAPS],
      'pending_count':int.from_bytes(m.read(w.A+0x18,4),'little'),
      'pending_read_index':int.from_bytes(m.read(w.A+0x20,4),'little'),
      'message_return_count':int.from_bytes(m.read(RETURN_POOL,4),'little'),
      'output_hex':m.read(OUTPUT,8).hex(),
      'returned_entries':[{'pointer':hex(int.from_bytes(m.read(t.POOL+0x10+i*16,8),'little')),
                           'capacity':int.from_bytes(m.read(t.POOL+0x18+i*16,8),'little')}
                          for i in range(4,8)]}


def cleanup(m,events,label,thunk=False):
    event=t.original(m,label,0x228bbc if thunk else 0x225934,
      **({'x0':IFACE,'x1':0,'x2':OUTPUT} if thunk else {'x0':w.A,'x1':OUTPUT}))
    event['scope']='Original local type3-message cleanup, pool return and map removal on explicit fixtures; no real message provenance/epoch/HAL completion.'
    event['state_after']=state(m);events.append(event);return event


def success(blob,code,ro,descriptor,byte3=0,leases=False,thunk=False):
    m,events,prototypes,assembled,copied=setup(blob,code,ro,descriptor)
    m.uc.mem_write(MESSAGE+3,bytes([byte3]));original_message=m.read(MESSAGE,0x80)
    source_id=copy_id=None
    if leases:
        for label,address in (('fixture source declaration',t.CODEC),('fixture copied-buffer declaration',BUFFERS[1])):
            event=m.invoke(label,1,ticket=1,address=address);assert event['status']==0
            prototypes.append(event)
            if source_id is None:source_id=event['control_after']['out_id']
            else:copy_id=event['control_after']['out_id']
        for label,op,kw,expected in (
          ('close native guest entry',4,{},0),('finish producer declaration',2,{'ticket':1},0),
          ('simulated source-only completion',3,{'ticket':source_id,'address':t.CODEC},0),
          ('retained native copy blocks data restore',5,{},10)):
            event=m.invoke(label,op,**kw);assert event['status']==expected;prototypes.append(event)
    before=state(m);event=cleanup(m,events,'original type3 cleanup with byte3='+str(byte3),thunk)
    assert event['reason']=='returned' and event['x0_to_x5'][0]=='0x0'
    after=state(m)
    assert after['pool_count']==4 and after['pool_write_index']==8 and after['pool_read_index']==4
    assert after['index_roots']==['0x0']*4 and after['index_node_available']==[1]*4
    assert after['pending_count']==0 and after['pending_read_index']==1 and after['message_return_count']==1
    assert after['returned_entries']==[{'pointer':hex(b),'capacity':0x400} for b in BUFFERS]
    assert m.read(MESSAGE,0x80)==original_message
    assert int.from_bytes(m.read(RETURN_POOL+0x10,8),'little')==MESSAGE
    assert int.from_bytes(m.read(RETURN_POOL+0x18,4),'little')==0x80
    assert m.read(OUTPUT,1)==bytes([byte3]) and m.read(OUTPUT+2,4)==b'\x34\x12\x00\x56'
    assert [m.read(at,0x400) for at in BUFFERS]==copied
    if leases:
        event=m.invoke('native local cleanup alone does not release prototype lease',5)
        assert event['status']==10;prototypes.append(event)
        # Explicit HOST notification follows validated local map/pool state.
        # Its production origin and true HAL completion remain unimplemented.
        event=m.invoke('host declares copied buffer completion after local cleanup',3,ticket=copy_id,address=BUFFERS[1])
        assert event['status']==0;prototypes.append(event)
        event=m.invoke('guest data-only restore after declared cleanup',5)
        assert event['status']==0;prototypes.append(event)
        assert int.from_bytes(m.read(w.A+0xe000,8),'little')==w.PRESET
        assert [m.read(at,0x400) for at in BUFFERS]==copied
    return {'message_byte3_fixture':byte3,'interface_thunk':thunk,'original_fragments':events,
      'prototype_events':prototypes,'before_cleanup':before,'after_cleanup':after,
      'copied_codec_payload_hex':copied[1][:0x1c0].hex(),
      'buffers_and_message_not_wiped':True,'local_cleanup_return_zero_not_encoder_success':True,
      'actual_names_of_message_bytes3_4_a_b_unbound':True,
      'host_completion_notification_not_real_hook':leases,
      'actual_Hal_completion_and_recovery_verified':False}


def negatives(blob,code,ro,descriptor):
    cases=[]
    for kind in ('wrong_type','wrong_key','second_map_key_mismatch','pool_full','missing_owner'):
        m,events,prototypes,_,copied=setup(blob,code,ro,descriptor)
        if kind=='wrong_type':m.uc.mem_write(MESSAGE+2,b'\x02')
        elif kind=='wrong_key':m.uc.mem_write(MESSAGE+0xa,b'\x01')
        elif kind=='second_map_key_mismatch':w.put32(m,NODES[1]+0x18,1)
        elif kind=='pool_full':w.put32(m,t.POOL,0x2a8)
        elif kind=='missing_owner':m.uc.mem_write(IFACE+0x55f10,bytes(8))
        event=cleanup(m,events,kind,kind=='missing_owner');after=state(m)
        if kind=='wrong_type':
            assert event['reason']=='returned' and event['x0_to_x5'][0]=='0x0'
            assert after['pending_count']==1 and after['pool_count']==0
            assert after['index_roots']==[hex(z) for z in NODES]
            assert after['message_return_count']==0 and m.read(OUTPUT,8)==bytes([0xa5])*8
        else:
            assert event['reason']=='boundary: before_unexecuted_diagnostic_acquire'
            if kind=='second_map_key_mismatch':
                assert after['pool_count']==1 and after['index_roots'][0]=='0x0'
                assert after['index_roots'][1:]==[hex(z) for z in NODES[1:]]
            elif kind=='pool_full':
                assert after['pool_count']==0x2a8 and after['index_roots']==[hex(z) for z in NODES]
            else:
                assert after['pool_count']==0 and after['index_roots']==[hex(z) for z in NODES]
            assert after['message_return_count']==0
        assert [m.read(at,0x400) for at in BUFFERS]==copied
        cases.append({'control':kind,'original_fragments':events,'prototype_events':prototypes,
          'state_after':after,'full_error_return_or_cleanup_not_executed':kind!='wrong_type',
          'scope':'Synthetic message/owner/key/pool boundary; never a physical response or actual error recovery.'})
    return cases


def wrap_case(blob,code,ro,descriptor):
    m=Guest(blob,code,ro);m.uc.mem_write(w.A+0x1038,r.p64(t.POOL))
    m.uc.mem_write(t.POOL,bytes(0x2ab0));w.put32(m,t.POOL+4,0x2a7);w.put32(m,t.POOL+8,0x2a7)
    m.uc.mem_write(t.PAIR,struct.pack('<QQ',BUFFERS[0],0x400))
    payload=bytes((i*13+9)&255 for i in range(0x1c0));m.uc.mem_write(t.CODEC,payload)
    events=[]
    pushed=t.original(m,'original OPA return wraps last slot',0x22c6f8,x0=w.A,x1=t.PAIR);events.append(pushed)
    assert pushed['reason']=='returned' and pushed['x0_to_x5'][0]=='0x0'
    assert int.from_bytes(m.read(t.POOL,4),'little')==1 and int.from_bytes(m.read(t.POOL+4,4),'little')==0
    popped=t.original(m,'original OPA copy reuses returned last-slot buffer',0x22c7d4,
        x0=w.A,x1=t.PAIR,x2=t.CODEC,x3=0x1c0);events.append(popped)
    assert popped['reason']=='returned' and popped['x0_to_x5'][0]=='0x0'
    assert int.from_bytes(m.read(t.POOL,4),'little')==0 and int.from_bytes(m.read(t.POOL+8,4),'little')==0
    assert m.read(BUFFERS[0],0x1c0)==payload
    return {'original_fragments':events,'prototype_events':[],
      'scope':'Valid artificial empty ring at last index: original return then new copy/pop; no live hardware owner.'}


def run(out):
    prior=t.STAGE/'final-receipt.json'
    assert r.im.sha(prior.read_bytes())=='25fd4512c4ef374cb35ab79c63d6fe00bc205dddf27d85e2cbde10a321b32f7f'
    manifest=json.loads(prior.read_text())
    for e in manifest['files']:assert r.im.sha((ROOT/e['path']).read_bytes())==e['sha256']
    image=BASE/'stage2/extraction/files/nflasha3/av-cam.bin';blob=image.read_bytes()
    assert r.im.sha(blob)==r.im.PINS['stage2/extraction/files/nflasha3/av-cam.bin']
    code,ro,_=p.object_image((p.STAGE/'scoped_writer.a64.o').read_bytes())
    descriptor=bytes.fromhex(json.loads((w.v.u.q.STAGE/'run-20261025/imola-matcher-results.json').read_text())['artificial_quality24_descriptor']['descriptor_hex'])
    ok=success(blob,code,ro,descriptor,0,True)
    nonzero_byte3=success(blob,code,ro,descriptor,7)
    thunk=success(blob,code,ro,descriptor,0,False,True)
    controls=negatives(blob,code,ro,descriptor);wrap=wrap_case(blob,code,ro,descriptor)
    cases=[ok,nonzero_byte3,thunk,*controls,wrap]
    original_count=sum(len(c['original_fragments']) for c in cases);prototype_count=sum(len(c['prototype_events']) for c in cases)
    regions=[('original OPA return',0x22c6f8,0x22c7d4),('original keyed buffer release',0x21c114,0x21c218),
      ('original index removal/node return',0x21d704,0x21d83c),('original type3 cleanup',0x225934,0x225b74),
      ('interface owner lookup',0x227870,0x227918),('interface cleanup tail thunk',0x228bbc,0x228bd4),
      ('unexecuted start sender dependencies',0x26c91c,0x26ca58)]
    proof={'status':'PASS_ORIGINAL_LOCAL_POOL_RETURN_INDEX_REMOVAL_AND_TYPE3_CLEANUP_SCOPE',
      'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
      'matching_reply':ok,'nonzero_byte3_message':nonzero_byte3,'interface_thunk':thunk,
      'negative_cases':controls,'ring_wrap':wrap,'original_fragments':original_count,'prototype_calls':prototype_count,
      'source_regions':[{'name':name,'instructions':r.im.dump(blob,a,z,V)} for name,a,z in regions],
      'actual_message_producer_current_epoch_Hal_completion_or_complete_error_handling_bound':False,
      'runtime_or_diagnostic_output_adapters':False,'camera_or_remote_access_attempted':False,
      'physical_hardware_recording_backup_restore_or_code_reclamation_verified':False,
      'goal_complete':False,'persistent_write_release':False}
    summary={k:proof[k] for k in ('status','original_fragments','prototype_calls',
      'actual_message_producer_current_epoch_Hal_completion_or_complete_error_handling_bound',
      'physical_hardware_recording_backup_restore_or_code_reclamation_verified','goal_complete','persistent_write_release')}
    summary.update(negative_controls=len(controls),four_parameter_buffers_returned_and_index_nodes_removed_on_fixture=True,
      local_cleanup_returns_zero_even_message_byte3_7_or_wrong_type=True,buffers_retain_old_bytes_after_return=True,
      partial_second_map_failure_keeps_remaining_buffers_indexed=True,original_ring_last_slot_push_pop_verified=True)
    assert r.im.sha(blob)==r.im.sha(image.read_bytes())
    r.im.write_json(out/'opa-return-results.json',proof);r.im.write_json(out/'summary.json',summary)
    (out/'executed-source.py').write_bytes(Path(__file__).read_bytes())
    r.im.write_json(out/'source-receipt.json',{'script_sha256':r.im.sha(Path(__file__).read_bytes()),
      'stage38_helper_sha256':r.im.sha(Path(t.__file__).read_bytes()),'stage37_helper_sha256':r.im.sha(Path(p.__file__).read_bytes()),
      'raw_harness_sha256':r.im.sha(Path(r.__file__).read_bytes()),'image_sha256':r.im.sha(blob),
      'prototype_object_sha256':r.im.sha((p.STAGE/'scoped_writer.a64.o').read_bytes()),
      'previous_manifest_sha256':r.im.sha(prior.read_bytes()),'proof_sha256':r.im.sha((out/'opa-return-results.json').read_bytes()),
      'summary_sha256':r.im.sha((out/'summary.json').read_bytes()),'volume_uuid':r.im.VOLUME})
    print(json.dumps(summary,ensure_ascii=False))


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',required=True)
    args=parser.parse_args();r.im.volume();out=Path(args.output).resolve()
    assert STAGE in out.parents and not out.exists();out.mkdir()
    try:run(out)
    except Exception:
        (out/'attempt-source.py').write_bytes(Path(__file__).read_bytes())
        r.im.write_json(out/'attempt-failure.json',{'traceback':traceback.format_exc(),'passing_result':False});raise


if __name__=='__main__':main()
