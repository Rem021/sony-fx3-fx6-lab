#!/usr/bin/env python3
"""Original extended IMOLA parameter fragments and pool/index copy, offline only.

Runtime memset and the unconditional diagnostic are NOT executed or adapted.
The pre-log prefix and post-log continuation are independent bounded fragments
with explicit initialized-buffer/register/stack fixtures. No whole builder,
valid full HAL request, actual consumer completion or camera restore is claimed.
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
sys.path.insert(0,str(BASE/'stage37-compiled-scoped-writer'))
import compiled_writer as p
w,r,V=p.w,p.r,p.V
INPUT=r.ARENA+0x310000
COMMON=w.A+0xe198
CODEC=w.A+0xe1d8
POOL=r.ARENA+0x350000
BUFFER=r.ARENA+0x360000
NODE=r.ARENA+0x370000
PAIR=r.ARENA+0x380000
MAP=w.A+0x11e8
LENGTH=0x1c0
EXTRA=[(0x221b8c,0x221eec),(0x221f50,0x2227b4),
       (0x27b9c8,0x27bbd0),(0x27cf58,0x27cf68),
       (0x24870c,0x24879c),(0x21a3b8,0x21a494),
       (0x22c7d4,0x22c938),(0x21d4f8,0x21d5f8)]


class Guest(p.Guest):
    def __init__(self,blob,code,ro):
        super().__init__(blob,code,ro)
        self.ranges.extend((V+a,V+z) for a,z in EXTRA)
        self.boundaries.pop(V+0x22211c)
        self.boundaries.update({V+0x221eec:'before_unexecuted_unconditional_VUI_diagnostic',
          V+0x2227b0:'builder_body_success_marker_before_epilogue',
          V+0x27d528:'before_unexecuted_diagnostic_acquire'})


def original(m,label,start,**registers):
    w.f.reset_trace(m);m.regs(**registers);out=m.run(start);out['label']=label
    return out


def setup(blob,code,ro,descriptor,candidate=True,seed=0xa5):
    m=Guest(blob,code,ro);m.uc.mem_write(w.DESC,descriptor)
    events=[w.prepare(m,w.A,'original descriptor prefix'),w.selection(m,w.A,'original FF selection')]
    values=[p.MAGIC,p.SESSION,p.EPOCH,p.EPOCH,w.A,1,0,0,1,0,0,0,0]
    m.uc.mem_write(p.CONTROL,struct.pack('<13Q',*values)+bytes(192))
    prototypes=[]
    if candidate:
        enter=m.invoke('native guest ENTER before parameter fragments',0)
        assert enter['status']==0;prototypes.append(enter)
    # These are declared inputs, not authenticated live constructor values.
    raw=bytearray(0x170)
    struct.pack_into('<I',raw,0x20,14)
    struct.pack_into('<HH',raw,0xe0,1920,1080)
    struct.pack_into('<I',raw,0xfc,1)
    m.uc.mem_write(INPUT,bytes(raw))
    # Original memset would clear COMMON; its runtime function is unbound.
    # Codec reserved/default initialization is not established. Preserve seed.
    m.uc.mem_write(COMMON,bytes(0x40))
    m.uc.mem_write(CODEC,bytes([seed])*LENGTH)
    return m,events,prototypes,bytes(raw)


def assemble(m,events):
    prefix=original(m,'independent post-clear prefix through native VUI helper',0x221b8c,
       x19=COMMON,x20=INPUT,x21=w.A,x22=CODEC)
    assert prefix['reason']=='boundary: before_unexecuted_unconditional_VUI_diagnostic'
    registers={f'x{i}':m.uc.reg_read(getattr(r.reg,'UC_ARM64_REG_X'+str(i))) for i in range(19,30)}
    vui=m.read(r.SP+0xd8,6)
    assert registers['x26']==1 and registers['x27']==0 and registers['x29']==0
    prefix.update(scope='Independent prefix after unexecuted runtime memset; original format guards and VUI helper only, ending before mandatory diagnostic.',
                  native_VUI_bytes=vui.hex(),post_prefix_callee_registers={k:hex(v) for k,v in registers.items()})
    events.append(prefix)
    continuation=original(m,'independent post-diagnostic HEVC continuation',0x221f50,**registers)
    assert continuation['reason']=='boundary: builder_body_success_marker_before_epilogue'
    assert int(continuation['x0_to_x5'][0],16)==1
    continuation.update(scope='Independent post-log registers/stack/output fixtures from stopped prefix. Diagnostic not skipped by adapter and whole function not executed. HEVC fields, defaults and copy helper execute to body success marker.',
      unexecuted_runtime_clear_and_unconditional_log=True,
      whole_builder_or_full_valid_Hal_request_verified=False)
    events.append(continuation)
    payload=m.read(CODEC,LENGTH);words=struct.unpack_from('<3I',payload,0x2c)
    values=(((words[0]>>8)+1)<<(6+(words[0]&255)),
            ((words[1]>>8)+1)<<(6+(words[1]&255)),
            ((words[2]>>8)+1)<<(4+(words[2]&255)))
    written=set()
    for phase in (prefix,continuation):
        for z in phase['writes']:
            for at in range(int(z['address'],16),int(z['address'],16)+z['size']):
                if CODEC<=at<CODEC+LENGTH:written.add(at-CODEC)
    untouched=sorted(set(range(LENGTH))-written)
    return {'payload_hex':payload.hex(),'common_hex':m.read(COMMON,0x40).hex(),
      'target':values[0],'trace':values[1],'cpb':values[2],
      'written_byte_offsets':[hex(i) for i in sorted(written)],
      'unwritten_byte_offsets':[hex(i) for i in untouched],
      'entire_tail_0x1a0_to_0x1bf_unwritten':all(i in untouched for i in range(0x1a0,LENGTH)),
      'logical_copy_length':LENGTH,'valid_complete_request_not_proven':True}


def pool_setup(m,capacity=0x200,count=1,nodes=1):
    m.uc.mem_write(w.A+0x1038,r.p64(POOL));m.uc.mem_write(POOL,bytes(0x40))
    m.uc.mem_write(POOL,struct.pack('<I',count));m.uc.mem_write(POOL+0x10,r.p64(BUFFER))
    w.put32(m,POOL+0x18,capacity);m.uc.mem_write(BUFFER,bytes([0xd7])*0x200)
    m.uc.mem_write(PAIR,bytes(16));m.uc.mem_write(MAP,bytes(0x88))
    w.put32(m,MAP+0x68,nodes);m.uc.mem_write(MAP+0x78,r.p64(NODE))
    m.uc.mem_write(NODE,bytes([0xc9])*0x40)


def copy_register(m,events,label):
    result=original(m,label,0x21a3b8,x0=w.A,x1=PAIR,x2=CODEC,x3=LENGTH,x4=MAP,x5=0)
    events.append(result)
    result.update(pool_count_after=int.from_bytes(m.read(POOL,4),'little'),
      pair_pointer=hex(int.from_bytes(m.read(PAIR,8),'little')),
      pair_capacity=int.from_bytes(m.read(PAIR+8,4),'little'),
      index_root=hex(int.from_bytes(m.read(MAP,8),'little')),
      index_node_pool_count=int.from_bytes(m.read(MAP+0x68,4),'little'),
      node_hex=m.read(NODE,0x30).hex(),copied_buffer_hex=m.read(BUFFER,0x200).hex(),
      scope='Original prepared-pool-buffer memcpy and ordered-index registration on explicit populated pool/map fixtures. No HAL publication/consumption or cancellation/return path.')
    return result


def success_case(blob,code,ro,descriptor,candidate,seed,leases=False,capacity=0x200):
    m,events,prototypes,input_bytes=setup(blob,code,ro,descriptor,candidate,seed)
    assembled=assemble(m,events);assert assembled['target']==(16000000 if candidate else 24498176)
    assert (assembled['trace'],assembled['cpb'])==(25999360,26000000)
    assert assembled['entire_tail_0x1a0_to_0x1bf_unwritten']
    pool_setup(m,capacity=capacity)
    copied=copy_register(m,events,'original 448-byte pool copy and index insertion')
    assert copied['reason']=='returned' and copied['x0_to_x5'][0]=='0x0'
    assert copied['pool_count_after']==0 and copied['index_node_pool_count']==0
    assert copied['pair_pointer']==hex(BUFFER) and copied['pair_capacity']==capacity
    assert copied['index_root']==hex(NODE)
    assert m.read(NODE+0x20,16)==m.read(PAIR,16)
    assert m.read(BUFFER,LENGTH)==bytes.fromhex(assembled['payload_hex'])
    assert m.read(BUFFER+LENGTH,0x200-LENGTH)==bytes([0xd7])*(0x200-LENGTH)
    if leases:
        def proto(label,op,expected,**kw):
            event=m.invoke(label,op,**kw);assert event['status']==expected
            prototypes.append(event);return event
        source=proto('fixture registers prepared source dependency',1,0,ticket=1,address=CODEC)['control_after']['out_id']
        copied_id=proto('fixture registers native copied-buffer dependency',1,0,ticket=1,address=BUFFER)['control_after']['out_id']
        proto('close new admission',4,0)
        proto('finish producing inputs',2,0,ticket=1)
        proto('simulated source completion only',3,0,ticket=source,address=CODEC)
        proto('copied buffer still blocks data restoration',5,10)
        # Reselection is original code, not native prototype restoration. This
        # is an explicit fixture order, not a demonstrated physical race.
        events.append(w.selection(m,w.A,'original selector changes only current preset'))
        assert int.from_bytes(m.read(w.A+0xe000,8),'little')==w.PRESET
        assert m.read(BUFFER,LENGTH)==bytes.fromhex(assembled['payload_hex'])
        assert int.from_bytes(m.read(MAP,8),'little')==NODE
        proto('copied buffer remains held after original pointer reselection',5,10)
        assert p.control(m)['live']==1 and p.control(m)['slots'][2]['id']==copied_id
    return {'candidate':candidate,'initial_codec_fill':hex(seed),'input_fixture_hex':input_bytes.hex(),
      'assembled':assembled,'original_fragments':events,'prototype_events':prototypes,
      'copied_buffer_still_registered':True,
      'native_copied_buffer_lease_release_or_actual_consumer_completion':False,
      'final_control':p.control(m) if candidate else None}


def negative_cases(blob,code,ro,descriptor):
    cases=[]
    for kind in ('empty_pool','too_small','no_index_node','invalid_RC','misaligned_width'):
        m,events,prototypes,_=setup(blob,code,ro,descriptor,True)
        if kind=='misaligned_width':
            m.uc.mem_write(INPUT+0xe0,struct.pack('<H',1921))
            event=original(m,'misaligned input width reaches error diagnostic',0x221b8c,
                x19=COMMON,x20=INPUT,x21=w.A,x22=CODEC);events.append(event)
            assert event['reason']=='boundary: before_unexecuted_diagnostic_acquire'
            assert hex(V+0x221d70) in event['pcs']
        elif kind=='invalid_RC':
            # Prefix stops at its mandatory diagnostic; make the subsequent
            # independent continuation input invalid without running that log.
            w.put32(m,INPUT+0xd0,2)
            event=original(m,'invalid RcMethod continuation reaches diagnostic',0x221fd0,
                x19=COMMON,x20=INPUT,x21=w.A,x22=CODEC,x25=w.A+0xe128,
                x24=INPUT+0x20,x23=INPUT+0x100,x26=1,x27=0,x29=0)
            events.append(event);assert event['reason']=='boundary: before_unexecuted_diagnostic_acquire'
            assert hex(V+0x222638) in event['pcs']
        else:
            assembled=assemble(m,events)
            pool_setup(m,capacity=0x1bf if kind=='too_small' else 0x200,
                       count=0 if kind=='empty_pool' else 1,nodes=0 if kind=='no_index_node' else 1)
            event=copy_register(m,events,kind)
            assert event['reason']=='boundary: before_unexecuted_diagnostic_acquire'
            if kind=='no_index_node':
                assert event['pool_count_after']==0 and event['index_root']=='0x0'
                assert m.read(BUFFER,LENGTH)==bytes.fromhex(assembled['payload_hex'])
                assert hex(V+0x21a464) in event['pcs']
            else:
                assert m.read(BUFFER,0x200)==bytes([0xd7])*0x200
                assert event['pool_count_after']==(0 if kind=='empty_pool' else 1)
        cases.append({'control':kind,'original_fragments':events,'prototype_events':prototypes,
          'complete_error_return_cleanup_not_executed':True,
          'scope':'Explicit fixture rejects/stops before original diagnostic; do not infer error cleanup, success return or physical failure behavior.'})
    return cases


def run(out):
    prior=p.STAGE/'final-receipt.json'
    assert r.im.sha(prior.read_bytes())=='e36641ede43d83275f58efba31d8d3c577b9ab219a8de07861489f93d6ab52ff'
    manifest=json.loads(prior.read_text())
    for e in manifest['files']:assert r.im.sha((ROOT/e['path']).read_bytes())==e['sha256']
    image=BASE/'stage2/extraction/files/nflasha3/av-cam.bin';blob=image.read_bytes()
    assert r.im.sha(blob)==r.im.PINS['stage2/extraction/files/nflasha3/av-cam.bin']
    code,ro,_=p.object_image((p.STAGE/'scoped_writer.a64.o').read_bytes())
    descriptor=bytes.fromhex(json.loads((w.v.u.q.STAGE/'run-20261025/imola-matcher-results.json').read_text())['artificial_quality24_descriptor']['descriptor_hex'])
    baseline=success_case(blob,code,ro,descriptor,False,0xa5)
    candidate=success_case(blob,code,ro,descriptor,True,0xa5,True)
    alternate=success_case(blob,code,ro,descriptor,True,0xc3,capacity=0x1c0)
    negatives=negative_cases(blob,code,ro,descriptor)
    a=bytes.fromhex(baseline['assembled']['payload_hex']);b=bytes.fromhex(candidate['assembled']['payload_hex'])
    c=bytes.fromhex(alternate['assembled']['payload_hex'])
    rate_diff=[i for i,(x,y) in enumerate(zip(a,b)) if x!=y]
    assert rate_diff==[0x2d,0x2e,0x2f]
    seed_diff=[i for i,(x,y) in enumerate(zip(b,c)) if x!=y]
    unwritten={int(i,16) for i in candidate['assembled']['unwritten_byte_offsets']}
    assert set(range(0x1a0,0x1c0))<=set(seed_diff)
    assert set(seed_diff)==unwritten
    all_cases=[baseline,candidate,alternate,*negatives]
    original_count=sum(len(k['original_fragments']) for k in all_cases)
    proto_count=sum(len(k['prototype_events']) for k in all_cases)
    regions=[('original start-param builder',0x221b50,0x222828),
      ('original source block copy and map caller',0x21f7f4,0x21f9f0),
      ('original pool-copy and map wrapper',0x21a3b8,0x21a494),
      ('original pool-copy allocation',0x22c7d4,0x22c938),
      ('original map-node allocation and insert',0x21d4f8,0x21d5f8),
      ('original VUI prefix helper',0x27b9c8,0x27bbd0),
      ('original format predicate',0x27cf58,0x27cf68),
      ('original color helper pair',0x24870c,0x24879c)]
    proof={'status':'PASS_EXTENDED_ORIGINAL_PARAMETER_AND_POOL_INDEX_SCOPE',
      'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
      'baseline':baseline,'candidate':candidate,'alternate_initialization':alternate,'negative_cases':negatives,
      'rate_only_changed_bytes':[hex(i) for i in rate_diff],
      'seed_dependent_unwritten_bytes':[hex(i) for i in seed_diff],
      'original_fragments':original_count,'compiled_prototype_calls':proto_count,
      'source_regions':[{'name':name,'instructions':r.im.dump(blob,a,z,V)} for name,a,z in regions],
      'declared_gaps':['Original runtime memset and mandatory VUI diagnostic unexecuted; prefix/continuation are separate fixture fragments.',
       'Actual start input/default/reserved initialization, full builder caller and actual object/epoch/synchronization unbound.',
       '448-byte copy is not a proved whole valid request. Capacity in pair/index is not inferred actual HAL payload length.',
       'Native copy/index registration creates additional retained data. No actual completion, map removal, buffer return, full error cleanup or HAL run.',
       'Prototype source/copy lease notifications are host-declared fixtures; real hook registration/transfer remains unimplemented.'],
      'native_output_or_diagnostic_adapters':False,'camera_or_remote_access_attempted':False,
      'whole_valid_Hal_request_hardware_recording_restore_or_code_reclamation_verified':False,
      'goal_complete':False,'persistent_write_release':False}
    summary={k:proof[k] for k in ('status','original_fragments','compiled_prototype_calls','rate_only_changed_bytes',
      'whole_valid_Hal_request_hardware_recording_restore_or_code_reclamation_verified','goal_complete','persistent_write_release')}
    summary.update(logical_codec_copy_bytes=LENGTH,seed_dependent_unwritten_byte_count=len(seed_diff),
      negative_controls=len(negatives),copied_buffer_remains_indexed_after_preset_reselection=True,
      native_copied_buffer_retained_by_fixture_lease_blocks_data_restore=True)
    assert r.im.sha(blob)==r.im.sha(image.read_bytes())
    r.im.write_json(out/'parameter-copy-results.json',proof);r.im.write_json(out/'summary.json',summary)
    (out/'executed-source.py').write_bytes(Path(__file__).read_bytes())
    r.im.write_json(out/'source-receipt.json',{'script_sha256':r.im.sha(Path(__file__).read_bytes()),
      'stage37_helper_sha256':r.im.sha(Path(p.__file__).read_bytes()),'stage36_helper_sha256':r.im.sha(Path(w.__file__).read_bytes()),
      'raw_harness_sha256':r.im.sha(Path(r.__file__).read_bytes()),'compiled_object_sha256':r.im.sha((p.STAGE/'scoped_writer.a64.o').read_bytes()),
      'image_sha256':r.im.sha(blob),'previous_manifest_sha256':r.im.sha(prior.read_bytes()),
      'proof_sha256':r.im.sha((out/'parameter-copy-results.json').read_bytes()),'summary_sha256':r.im.sha((out/'summary.json').read_bytes()),'volume_uuid':r.im.VOLUME})
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
