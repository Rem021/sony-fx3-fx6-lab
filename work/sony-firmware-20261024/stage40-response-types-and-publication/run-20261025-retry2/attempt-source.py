#!/usr/bin/env python3
"""Bind original IMOLA response type names and queue/callback ordering, offline.

Raw inbound transport, owner registration and current generation are fixtures.
Unconditional diagnostics are stopped, not adapted: post-diagnostic execution
is a separate fragment with captured explicit inputs. Actual C++ dynamic_cast
executes against original RTTI/vtable data; callback target is never fabricated.
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
sys.path.insert(0,str(BASE/'stage39-opa-return-and-reply'))
import opa_return as x
t,p,w,r,V=x.t,x.p,x.w,x.r,x.V
RAW=r.ARENA+0x3e0000
CALLBACK=r.ARENA+0x3d0000
LOG_TABLE=0x37be00
API_ENC_VTABLE=V+0x37bda8
API_ENC_TI=V+0x32e1d0
BASE_TI=V+0x37beb0
EXTRA=[(0x2280c0,0x22856c),(0x22856c,0x22873c),(0x22873c,0x228abc),
       (0x22c558,0x22c604),(0x226aa4,0x226ab4),(0x226ac4,0x226ae0),
       (0x1a58,0x1b74),(0x2fd8,0x3124)]


class Guest(x.Guest):
    def __init__(self,blob,code,ro):
        super().__init__(blob,code,ro)
        self.ranges.extend((V+a,V+z) for a,z in EXTRA)
        self.boundaries.update({V+0x228148:'before_unexecuted_response_diagnostic',
          V+0x226634:'before_unbound_STOP_callback_invocation',
          V+0x226604:'before_unbound_START_callback_invocation'})


def setup(blob,code,ro,descriptor,kind,callback=False,pending=0,capacity=0x80,channel=0):
    old=x.Guest
    try:
        x.Guest=Guest;m,events,prototypes,assembled,copied=x.setup(blob,code,ro,descriptor)
    finally:x.Guest=old
    m.uc.mem_write(w.A,r.p64(API_ENC_VTABLE))
    # The original lookup scans a synthetic owner registry, matching owner+8.
    m.uc.mem_write(w.A+0x1138,b'\0')
    w.put32(m,w.A+0x18,pending);w.put32(m,w.A+0x1c,0);w.put32(m,w.A+0x20,0)
    m.uc.mem_write(x.RETURN_POOL,bytes(0x1020))
    w.put32(m,x.RETURN_POOL,1);w.put32(m,x.RETURN_POOL+4,1)
    m.uc.mem_write(x.RETURN_POOL+0x10,struct.pack('<QQ',x.MESSAGE,capacity))
    m.uc.mem_write(x.MESSAGE,bytes([0xd7])*0x80)
    inbound=bytearray(0x90);inbound[0x11]=channel;inbound[0x12]=kind
    inbound[0x13]=7;struct.pack_into('<H',inbound,0x14,0x1234)
    inbound[0x1a]=0;inbound[0x1b]=0x56
    m.uc.mem_write(RAW,bytes(inbound))
    if callback:
        assert kind in (0,3)
        m.uc.mem_write(w.A+(0x1158 if kind==3 else 0x1148),r.p64(CALLBACK))
    return m,events,prototypes,assembled,copied,bytes(inbound)


def classify(blob,code,ro):
    result=[]
    for kind in range(15):
        target=struct.unpack_from('<Q',blob,LOG_TABLE+kind*8)[0]-V
        assert target==0x228764+kind*0x38
        # BL is PC-relative: equal destinations have different encoded words.
        first=r.im.dump(blob,target,target+4,V)[0]
        assert first['asm']=='bl #'+hex(V+0x27d528)
        # The string is materialized after the logger acquire. Recover this
        # original ADRP/ADD pair statically, without executing the diagnostic.
        region=r.im.dump(blob,target,target+0x38,V)
        pair=[i for i in region if int(i['offset'],16) in (target+0x2c,target+0x30)]
        assert len(pair)==2 and pair[0]['asm'].startswith('adrp x8, ')
        assert pair[1]['asm'].startswith('add x8, x8, #')
        page=int(pair[0]['asm'].split('#')[1],16);offset=int(pair[1]['asm'].split('#')[1],16)
        string_at=page+offset-V;name=r.im.cstring(blob,string_at)
        assert name.startswith('[IMLCMNWRAP]') and 'IMOLA_' in name
        m=Guest(blob,code,ro);m.uc.mem_write(RAW+2,bytes([kind]))
        phase=t.original(m,'original response type'+str(kind)+' dispatch',0x22873c,x1=RAW)
        assert phase['reason']=='boundary: before_unexecuted_diagnostic_acquire'
        assert phase['pcs'][-2]==hex(V+target)
        result.append({'type':kind,'table_target':hex(target),'name':name,'name_offset':hex(string_at),
          'string_reference_instructions':pair,'original_fragment':phase})
    assert 'IMOLA_ENC_START_DONE' in result[0]['name']
    assert 'IMOLA_ENC_STOP_DONE' in result[3]['name']
    return result


def case(blob,code,ro,descriptor,label,kind,callback=False,pending=0,capacity=0x80,channel=0):
    m,events,prototypes,assembled,copied,inbound=setup(blob,code,ro,descriptor,kind,callback,pending,capacity,channel)
    prefix=t.original(m,label+' original lookup/borrow prefix',0x2280c0,x0=x.IFACE,x1=RAW)
    events.append(prefix)
    if channel:
        assert prefix['reason']=='boundary: before_unexecuted_diagnostic_acquire'
        assert int.from_bytes(m.read(x.RETURN_POOL,4),'little')==1
        return {'label':label,'type':kind,'original_fragments':events,'prototype_events':prototypes,
          'scope':'No matching owner: before diagnostic; raw transport and registration remain fixtures.'}
    assert prefix['reason']=='boundary: before_unexecuted_response_diagnostic'
    assert int.from_bytes(m.read(x.RETURN_POOL,4),'little')==0
    assert int.from_bytes(m.read(w.A+0x18,4),'little')==pending
    regs={f'x{i}':m.uc.reg_read(getattr(r.reg,'UC_ARM64_REG_X'+str(i))) for i in range(19,29)}
    regs['sp']=m.uc.reg_read(r.reg.UC_ARM64_REG_SP)
    assert regs['x19']==w.A and regs['x20']==x.MESSAGE
    assert regs['x21']==RAW and regs['x22']==x.RETURN_POOL and regs['x25']==capacity
    prefix['captured_post_diagnostic_fixture_registers']={k:hex(v) for k,v in regs.items()}
    continuation=t.original(m,label+' independent post-diagnostic publication',0x22814c,**regs)
    events.append(continuation)
    roots=[hex(int.from_bytes(m.read(z,8),'little')) for z in x.MAPS]
    pending_after=int.from_bytes(m.read(w.A+0x18,4),'little')
    if callback:
        assert continuation['reason']=='boundary: before_unbound_'+('STOP' if kind==3 else 'START')+'_callback_invocation'
        assert pending_after==pending
    elif pending==0x100 or capacity<0x80:
        assert continuation['reason']=='boundary: before_unexecuted_diagnostic_acquire'
        assert pending_after==pending
    else:
        assert continuation['reason']=='returned',continuation['reason']
        assert pending_after==pending+1
        assert m.read(x.MESSAGE,0x80)==inbound[0x10:0x90]
        assert int.from_bytes(m.read(w.A+0x30,8),'little')==x.MESSAGE
        assert int.from_bytes(m.read(w.A+0x28,8),'little')==kind
        assert hex(V+0x1a58) in continuation['pcs'] and hex(V+0x2fd8) in continuation['pcs']
    assert roots==[hex(n) for n in x.NODES]
    assert int.from_bytes(m.read(t.POOL,4),'little')==0
    assert [m.read(at,0x400) for at in x.BUFFERS]==copied
    cleanup=None
    if not callback and pending==0 and capacity>=0x80:
        cleanup=x.cleanup(m,events,label+' original STOP consumer')
        assert cleanup['reason']=='returned' and cleanup['x0_to_x5'][0]=='0x0'
        if kind==3:
            assert cleanup['state_after']['pool_count']==4 and cleanup['state_after']['index_roots']==['0x0']*4
        else:
            assert cleanup['state_after']['pool_count']==0
            assert cleanup['state_after']['pending_count']==1
            assert cleanup['state_after']['index_roots']==[hex(n) for n in x.NODES]
    return {'label':label,'type':kind,'callback_pointer_fixture':callback,'original_fragments':events,
      'prototype_events':prototypes,'pending_after_dispatch':pending_after,'roots_after_dispatch_before_consumer':roots,
      'codec_copy_target':assembled['target'],'cleanup_state':cleanup['state_after'] if cleanup else None,
      'scope':'Original lookup/borrow prefix stops before mandatory diagnostic. Independent captured-input continuation executes original dynamic_cast, native callback predicate/queue publication. Callback itself remains unexecuted, no completion/output adapter.',
      'actual_transport_callback_target_current_epoch_Hal_or_physical_recovery_verified':False}


def run(out):
    prior=x.STAGE/'final-receipt.json'
    assert r.im.sha(prior.read_bytes())=='cef5b9178b7f795bb601613c200d12f5458d80548883fcfbf7f220c23366d0ba'
    manifest=json.loads(prior.read_text())
    for e in manifest['files']:assert r.im.sha((ROOT/e['path']).read_bytes())==e['sha256']
    image=BASE/'stage2/extraction/files/nflasha3/av-cam.bin';blob=image.read_bytes()
    assert r.im.sha(blob)==r.im.PINS['stage2/extraction/files/nflasha3/av-cam.bin']
    code,ro,_=p.object_image((p.STAGE/'scoped_writer.a64.o').read_bytes())
    descriptor=bytes.fromhex(json.loads((w.v.u.q.STAGE/'run-20261025/imola-matcher-results.json').read_text())['artificial_quality24_descriptor']['descriptor_hex'])
    types=classify(blob,code,ro)
    cases=[case(blob,code,ro,descriptor,'START_DONE no callback',0),
      case(blob,code,ro,descriptor,'STOP_DONE no callback',3),
      case(blob,code,ro,descriptor,'START_DONE registered callback',0,True),
      case(blob,code,ro,descriptor,'STOP_DONE registered callback',3,True),
      case(blob,code,ro,descriptor,'pending queue full',3,pending=0x100),
      case(blob,code,ro,descriptor,'undersized message buffer',3,capacity=0x7f),
      case(blob,code,ro,descriptor,'unmatched owner channel',3,channel=1)]
    original_count=len(types)+sum(len(z['original_fragments']) for z in cases)
    prototype_count=sum(len(z['prototype_events']) for z in cases)
    regions=[('native inbound wrapper',0x2280c0,0x22856c),('native owner scan',0x22856c,0x22873c),
      ('native response type names',0x22873c,0x228abc),('queue publication and owner predicates',0x22c558,0x22c604),
      ('START STOP callback predicates',0x226aa4,0x226ad4),('START callback virtual dispatch',0x226604,0x226614),
      ('STOP callback virtual dispatch',0x226634,0x226644),('original dynamic_cast',0x1a58,0x1b74),
      ('original single-inheritance RTTI traversal',0x2fd8,0x3124)]
    proof={'status':'PASS_ORIGINAL_START_STOP_TYPE_BINDING_AND_POST_LOG_PUBLICATION_SCOPE',
      'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'types':types,'cases':cases,
      'original_fragments':original_count,'compiled_prototype_calls':prototype_count,
      'stage39_type3_refined_to':'IMOLA_ENC_STOP_DONE, not IMOLA_ENC_START_DONE',
      'type0':'IMOLA_ENC_START_DONE','actual_virtual_metadata':{
       'object_vptr_fixture':hex(API_ENC_VTABLE),'derived_typeinfo':hex(API_ENC_TI),'base_typeinfo':hex(BASE_TI),
       'derived_name':r.im.cstring(blob,0x32e1a0),'base_name':r.im.cstring(blob,0x32e6d0),
       'metadata_scope':'Original RTTI used by original runtime helper; live object construction, registry and compiler ABI are not observed.'},
      'source_regions':[{'name':n,'instructions':r.im.dump(blob,a,z,V)} for n,a,z in regions],
      'callback_before_pending_publication':True,'START_message_does_not_release_STOP_retained_buffers':True,
      'actual_raw_transport_callback_target_current_request_epoch_Hal_or_recovery_bound':False,
      'runtime_or_diagnostic_output_adapters':False,'camera_or_remote_access_attempted':False,
      'goal_complete':False,'persistent_write_release':False}
    summary={k:proof[k] for k in ('status','original_fragments','compiled_prototype_calls','stage39_type3_refined_to',
      'callback_before_pending_publication','START_message_does_not_release_STOP_retained_buffers',
      'actual_raw_transport_callback_target_current_request_epoch_Hal_or_recovery_bound','goal_complete','persistent_write_release')}
    summary.update(original_named_response_types=len(types),publication_controls=len(cases))
    assert r.im.sha(blob)==r.im.sha(image.read_bytes())
    r.im.write_json(out/'response-publication-results.json',proof);r.im.write_json(out/'summary.json',summary)
    (out/'executed-source.py').write_bytes(Path(__file__).read_bytes())
    r.im.write_json(out/'source-receipt.json',{'script_sha256':r.im.sha(Path(__file__).read_bytes()),
      'stage39_helper_sha256':r.im.sha(Path(x.__file__).read_bytes()),'stage38_helper_sha256':r.im.sha(Path(t.__file__).read_bytes()),
      'stage37_helper_sha256':r.im.sha(Path(p.__file__).read_bytes()),'raw_harness_sha256':r.im.sha(Path(r.__file__).read_bytes()),
      'image_sha256':r.im.sha(blob),'prototype_object_sha256':r.im.sha((p.STAGE/'scoped_writer.a64.o').read_bytes()),
      'previous_manifest_sha256':r.im.sha(prior.read_bytes()),'proof_sha256':r.im.sha((out/'response-publication-results.json').read_bytes()),
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
