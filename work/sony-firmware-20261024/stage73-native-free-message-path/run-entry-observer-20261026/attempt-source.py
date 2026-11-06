#!/usr/bin/env python3
"""Original free-message construction to the real unexecuted kernel boundary.

Cache/handle inputs are declared fixture data, not successful allocations.
The separate decoder probes are independent entries with supplied inline
records, never transport replies injected into the pending original request.
"""
from pathlib import Path
import argparse
import datetime
import json
import struct
import sys
import traceback

STAGE=Path(__file__).resolve().parent
sys.path.insert(0,str(STAGE.parent/'stage72-native-manager-teardown'))
import manager_teardown as previous
q=previous.q
c,r,im,V,n,f=q.c,q.r,q.im,q.V,q.n,q.f
BASE,ROOT=q.BASE,q.ROOT
M=q.MANAGER
G,GSIZE,FLAG=c.d.f.G,c.d.f.GSIZE,c.d.f.FLAG
UNIT=V+0x27c1a8
DECODE_STOP=V+0x27bf68
FRAME=r.SP-0x800
OBJECT=FRAME+8
OUTPUT=r.ARENA+0x3e1000
SOURCE=r.ARENA+0x3e2000


class FreeGuest(q.QueueGuest):
    def __init__(self,*args):
        super().__init__(*args)
        self.free_unit_entries=[];self.wrapper_entries=[];self.decoder_entries=[]

    def code(self,u,pc,size,user):
        rr=lambda i:u.reg_read(getattr(r.reg,'UC_ARM64_REG_X'+str(i)))
        if pc==UNIT:
            self.free_unit_entries.append({'pc':hex(pc),'LR':hex(rr(30)),
                'x0_x3':[hex(rr(i)) for i in range(4)],
                'body_allowed_this_observation':pc not in self.boundaries,
                'input_descriptor152_hex':self.read(rr(0),0x98).hex()})
        if pc==V+0x27bec8:
            self.wrapper_entries.append({'pc':hex(pc),'LR':hex(rr(30)),
                'command':hex(rr(0)),'source':hex(rr(3)),
                'input216_hex':self.read(rr(1),216).hex(),
                'output_pointer':hex(rr(2))})
        if pc==V+0x27bf28:
            self.decoder_entries.append({'pc':hex(pc),'SP':hex(u.reg_read(r.reg.UC_ARM64_REG_SP)),
                'supplied_output':hex(rr(19)),
                'independent_input_not_a_real_transport_completion':True})
        return super().code(u,pc,size,user)

    def store(self,u,access,address,size,value,user):
        if G<=address and address+size<=G+GSIZE:
            pc=u.reg_read(r.reg.UC_ARM64_REG_PC)
            # This free path's original initialization flag setter differs
            # from stage63's allocation-path setter. No write is synthesized.
            assert V+0x27bca0<=pc<V+0x27bd8c or (pc==V+0x27c1ec and address==FLAG and size==8)
            self.global_stores.append({'pc':hex(pc),'address':hex(address),
                'size':size,'value':hex(value&((1<<64)-1))})
            return
        return super().store(u,access,address,size,value,user)


def linked(assets,modules,providers,adapter):
    m=FreeGuest(assets,modules,providers,adapter);events=[n.link(m)]
    for row in m.import_bindings:
        assert m.read(int(row['actual_avcam_slot'],16),8)==r.p64(int(row['original_module_target'],16))
    assert sum(int.from_bytes(m.read(V+0x1ec+i*8,8),'little')!=0 for i in range(211))==5
    m.uc.mem_protect(V,4096,r.unicorn.UC_PROT_READ|r.unicorn.UC_PROT_EXEC)
    m.expected_data={f.f59.GUARD:1,f.f59.MUTE:0,f.f59.CAT1:1,f.f59.CAT2:1}
    for at,value in m.expected_data.items():
        assert m.blob[at-V]==0;m.uc.mem_write(at,bytes([value]))
    m.uc.mem_protect(f.f59.MUTE&-4096,4096,r.unicorn.UC_PROT_READ|r.unicorn.UC_PROT_WRITE)
    e=c.phase(m,'original mute setter for free message/independent decoder',V+0x27d898,x0=f.f59.LOG,x1=1)
    assert e['reason']=='returned';events.append(e);m.expected_data[f.f59.MUTE]=1
    m.uc.mem_protect(G&-4096,((G+GSIZE+4095)&-4096)-(G&-4096),
                     r.unicorn.UC_PROT_READ|r.unicorn.UC_PROT_WRITE)
    m.ranges.extend((V+a,V+z) for a,z in [
        (0x22db34,0x22dd38),(0x22e090,0x22e198),(0x27c1a8,0x27c2b4),
        (0x95fd0,0x96024),(0x95e58,0x95ea4),
        (0x96024,0x9604c),(0x962bc,0x96384),(0x963d8,0x9642c)])
    return m,events


def images(m,initialized):
    raw=bytearray(m.read(V,len(m.blob)))
    assert raw[0x1ec:0x884]==m.read(n.MDATA,0x698)
    raw[0x1ec:0x884]=m.blob[0x1ec:0x884]
    for at,value in m.expected_data.items():
        assert raw[at-V]==value;raw[at-V]=m.blob[at-V]
    if initialized:
        assert m.read(FLAG,8)==r.p64(1)
        assert struct.unpack('<I',m.read(G+0x2000,4))[0]==202
        assert m.global_stores
        raw[G-V:G-V+GSIZE]=m.blob[G-V:G-V+GSIZE]
    else:
        assert m.read(G,GSIZE)==bytes(GSIZE) and not m.global_stores
    assert raw==m.blob
    assert not m.module_writes and not m.writer_entries and not m.adapter_entries and not m.bridge_entries
    assert not m.rate_entries and not m.admitted_channel_entries
    for module in m.modules.values():
        for section in module.sections.values():assert m.read(section['base'],section['size'])==bytes(section['data'])
    for at,data in [(f.f58.BRIDGE,m.code_bytes),(f.f58.CONST,m.ro_bytes),
                    (c.old.CODE,m.writer_code),(c.old.RODATA,m.writer_ro),
                    (c.BRIDGE,m.adapter_code),(c.CONST,m.adapter_ro)]:
        assert m.read(at,len(data))==data


def request_case(assets,modules,providers,adapter,seed,handle):
    m,events=linked(assets,modules,providers,adapter)
    global CURRENT_GUEST
    CURRENT_GUEST=m
    m.uc.mem_write(M,bytes([seed])*f.last.MANAGER_SIZE)
    e=c.phase(m,'original manager constructor for declared last-reference request',V+0x22cc8c,x0=M)
    assert e['reason']=='returned';events.append(e)
    ptr=seed*0x0101010101010101
    descriptor=struct.pack('<QII',ptr,0x12345678,handle)
    m.uc.mem_write(M+0x209b8,descriptor)
    m.uc.mem_write(M+0x20a00,struct.pack('<QIII',ptr,0x12345678,handle,1))
    m.boundaries[UNIT]='before_original_free_body_for_same_instance_continuation'
    e=c.phase(m,'original last-reference cache clear to pending free-body entry',V+0x22db34,x0=M)
    events.append(e);assert e['reason']=='boundary: before_original_free_body_for_same_instance_continuation'
    assert m.read(M+0x20a00,20)==struct.pack('<QIII',0,0,0xffffffff,0)
    assert m.read(M+0x209b8,16)==descriptor
    before_arena=m.read(r.ARENA,r.ARENA_SIZE)
    m.boundaries.pop(UNIT)
    e=c.phase(m,'same pending original free request through actual LIRO-bound OSAL',UNIT,independent=False)
    events.append(e)
    assert e['reason']=='boundary: before_original_unexecuted_kernel_service',e['reason']
    assert len(m.resource_constructor_entries)==len(m.message_entries)==len(m.wrapper_entries)==1
    assert len(m.free_unit_entries)==2
    assert [x['body_allowed_this_observation'] for x in m.free_unit_entries]==[False,True]
    assert m.free_unit_entries[0]['input_descriptor152_hex']==m.free_unit_entries[1]['input_descriptor152_hex']
    assert len(m.kernel_service_entries)==len(m.module_alloc_entries)==len(m.empty_client_reads)==len(m.lock_entries)==1
    assert m.resource_constructor_entries[0]['initial_global_object_zero']
    assert m.read(r.ARENA,r.ARENA_SIZE)==before_arena
    request=m.wrapper_entries[0];msg=m.message_entries[0]
    expected=bytearray(216)
    struct.pack_into('<H',expected,0,0x23)
    struct.pack_into('<I',expected,8,handle)
    struct.pack_into('<HH',expected,0x14,0x1111,2)
    assert request['input216_hex']==msg['inline_payload216_hex']==bytes(expected).hex()
    command=0x8061003c|(((handle>>15)&1)<<28)
    assert request['command']==msg['command']==hex(command)
    assert msg['state_u32']==2 and msg['size_u16']==216 and msg['source_u32']=='0x806800f3'
    alloc=m.module_alloc_entries[0];client=m.empty_client_reads[0]
    bit=(handle>>15)&1
    # Bit15 selects the original wrapper's flagged command. The flag enters
    # an earlier diagnostic allocation, before the main free-message send.
    expected_command=0x8f013a if bit else command
    expected_size=0x34 if bit else 216
    expected_wait=0 if bit else 1
    assert alloc['x0_x3'][0]==hex(expected_command)
    assert alloc['x0_x3'][2:]==[hex(expected_size),hex(expected_wait)]
    assert client['client_id']==(expected_command&0x7fff) and client['loaded_X21']=='0x0'
    kernel=m.kernel_service_entries[0]
    assert kernel['names']==['_raw_spin_lock_irqsave'] and kernel['LR']==hex(m.utext+0x1cc)
    assert not kernel['kernel_body_executed'] and not kernel['kernel_return_IRQ_lock_thread_or_allocation_adapter']
    assert not m.decoder_entries
    assert m.read(M+0x209b8,16)==descriptor and q.state(m)['count']==0
    images(m,True)
    return {'seed':seed,'declared_handle':hex(handle),'handle_bit15':bit,
        'cache_descriptor_are_declared_not_real_successful_allocation':True,
        'master_descriptor_still_live_hex':descriptor.hex(),
        'original_free_entry_boundary_then_same_instance_execution':m.free_unit_entries,
        'original_wrapper_input':request,'native_inline_message':msg,
        'resource_metadata_constructor':m.resource_constructor_entries[0],
        'global_metadata_records':202,'global_metadata_and_stores':m.global_stores,
        'original_OSAL_allocation_entry':alloc,'empty_ELF_client_cache':client,
        'first_allocation_is_diagnostic_before_main_send':bool(bit),
        'original_lock_entry':m.lock_entries[0],'unexecuted_kernel_service':kernel,
        'events':events,'reply_decoder_entered':False,'original_release_return_received':False,
        'physical_release_or_main_recording_complete':False}


def decoder_case(assets,modules,providers,adapter,label,size,status,magic,kind):
    m,events=linked(assets,modules,providers,adapter)
    global CURRENT_GUEST
    CURRENT_GUEST=m
    # Frame and message are declared standalone inputs, not an interrupted
    # transport frame. No pending request is resumed with these records.
    m.uc.mem_write(FRAME,b'\x5a'*0x200)
    m.uc.mem_write(OUTPUT,bytes(216))
    payload=bytearray(max(8,size))
    struct.pack_into('<HHHH',payload,0,kind,status,0,magic)
    m.uc.mem_write(SOURCE,bytes(payload))
    e=c.phase(m,'independent original inline-message constructor '+label,V+0x960a4,x0=OBJECT)
    assert e['reason']=='returned';events.append(e)
    e=c.phase(m,'independent original inline payload setter '+label,V+0x96240,
              x0=OBJECT,x1=SOURCE,x2=size)
    assert e['reason']=='returned' and m.uc.reg_read(r.reg.UC_ARM64_REG_X0)==0;events.append(e)
    assert struct.unpack('<I',m.read(OBJECT+8,4))[0]==2
    assert struct.unpack('<H',m.read(OBJECT+12,2))[0]==size
    before_object=m.read(OBJECT,0x198)
    before_arena=m.read(r.ARENA,r.ARENA_SIZE)
    m.boundaries.pop(V+0x96024)
    m.boundaries[DECODE_STOP]='after_independent_original_decoder_before_wrapper_cleanup'
    e=c.phase(m,'independent post-transport decoder with supplied local inline bytes '+label,
              V+0x27bf28,sp=FRAME,x19=OUTPUT)
    events.append(e);assert e['reason']=='boundary: after_independent_original_decoder_before_wrapper_cleanup'
    result=m.uc.reg_read(r.reg.UC_ARM64_REG_X19)&0xffffffff
    copied=min(size,216)
    expected_output=bytes(payload[:copied])+bytes(216-copied)
    assert m.read(OUTPUT,216)==expected_output
    observed_magic=struct.unpack_from('<H',expected_output,6)[0]
    observed_status=struct.unpack_from('<h',expected_output,2)[0]
    expected_result=1 if observed_magic!=0x1111 or observed_status<0 else (0 if observed_status==0 else 2)
    assert result==expected_result
    expected_arena=bytearray(before_arena);at=OUTPUT-r.ARENA
    expected_arena[at:at+216]=expected_output
    assert m.read(r.ARENA,r.ARENA_SIZE)==bytes(expected_arena)
    assert m.read(OBJECT+8,4)==bytes(4) and m.read(OBJECT+12,2)==bytes(2)
    assert m.read(OBJECT+16,4)==bytes(4) and m.read(OBJECT+24,size)==bytes(size)
    assert not m.kernel_service_entries and not m.module_alloc_entries and not m.message_entries
    assert not m.free_unit_entries and not m.wrapper_entries and len(m.decoder_entries)==1
    assert not m.resource_constructor_entries
    images(m,False)
    return {'label':label,'supplied_length':size,'supplied_status':status,
        'supplied_magic':hex(magic),'supplied_kind':hex(kind),'result_W19':result,
        'before_message_hex':before_object.hex(),'copied_output216_hex':expected_output.hex(),
        'native_message_consumed_state_size_source_cleared':True,'events':events,
        'standalone_entry_not_transport_reply_or_full_wrapper_return':True,
        'real_send_correlation_reply_completion_physical_free_or_recovery':False}


def run(out):
    manifest=previous.STAGE/'final-receipt.json'
    assert im.sha(manifest.read_bytes())=='1bad5c4cfba82600385e96df861374652103168d6cef7091d0d6beca3aa8a8aa'
    for row in json.loads(manifest.read_text())['files']:
        assert im.sha((ROOT/row['path']).read_bytes())==row['sha256']
    assert (BASE/'GOAL_STATUS.json').read_bytes()==(STAGE/'goal-status-before.json').read_bytes()
    modules,providers,kernel=c.d.link.build()
    code,ro,_=f.f58.object_image((f.f58.STAGE/'run-post-loader-patch-20261026/match_adapter.a64.o').read_bytes())
    wcode,wro,functions,_=c.old.object_image((c.old.STAGE/'run-bounded-stores-20261026/resource_alias.a64.o').read_bytes())
    blob=(BASE/'stage2/extraction/files/nflasha3/av-cam.bin').read_bytes()
    assert im.sha(blob)==im.PINS['stage2/extraction/files/nflasha3/av-cam.bin']
    liro=(n.STAGE/'official-files/nflasha15/kmod/liro.ko').read_bytes()
    adapter=c.object_image((c.STAGE/'run-same-instance-slices-20261026/channel_adapter.a64.o').read_bytes())
    assets=blob,liro,kernel,code,ro,wcode,wro,functions
    requests=[request_case(assets,modules,providers,adapter,seed,handle)
              for seed in (0xa5,0xc3) for handle in (0x123a3cde,0x123abcde)]
    specs=[('full zero status',216,0,0x1111,0x23),('full positive status',216,1,0x1111,0x23),
           ('full negative status',216,0xffff,0x1111,0x23),('bad magic',216,0,0x2222,0x23),
           ('eight bytes unrelated kind',8,0,0x1111,0xbeef),('six bytes',6,0,0x1111,0x23),
           ('empty inline state2',0,0,0x1111,0x23)]
    decoders=[decoder_case(assets,modules,providers,adapter,*args) for args in specs]
    proof={'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'status':'PASS_ORIGINAL_FREE_REQUEST_TO_KERNEL_AND_INDEPENDENT_REPLY_GATE_SCOPE',
        'requests':requests,'independent_decoder_cases':decoders,
        'bounded_fragments':sum(len(x['events']) for x in requests+decoders),
        'original_regions':[{'start':hex(a),'end':hex(z),'instructions':im.dump(blob,a,z,V)} for a,z in
             [(0x27c1a8,0x27c2b4),(0x27bec8,0x27bf90),(0x99004,0x99120),
              (0x95fd0,0x96024),(0x95e58,0x95ea4),(0x962bc,0x96384),(0x963d8,0x9642c),
              (0x96024,0x9604c),(0x992b4,0x992cc)]],
        'source_receipt':{'script_sha256':im.sha(Path(__file__).read_bytes()),
            'queue_guest_helper_sha256':im.sha((q.STAGE/'buffer_record_fifo.py').read_bytes()),
            'runner_sha256':im.sha((c.STAGE/'channel_callpath.py').read_bytes()),
            'avcam_sha256':im.sha(blob),'LIRO_sha256':im.sha(liro),'kernel_sha256':im.sha(kernel),
            'previous_manifest_sha256':im.sha(manifest.read_bytes())},
        'scope':['Nonzero handle/cache fixtures are not evidence of successful physical allocation.',
            'Original last-reference path builds the216-byte free request and native message, then enters LIRO-bound OSAL and stops before the kernel IRQ lock.',
            'Handle bit15 sets command bit28. In this declared module state the flagged path first allocates an original diagnostic message, before sending the main free request.',
            'Independent decoder tests supply local inline records after transport; they do not inject replies into either pending request or emulate successful transport.',
            'The local generic decoder accepts an8-byte supplied record with magic1111/status0 even with unrelated first kind; this is not proof that end-to-end correlation is absent or a firmware vulnerability.',
            'No physical allocation/free, successful sync reply, hardware consumer exit, main recording, cold boot or recovery is proven.'],
        'Windows_UU_camera_operations':False,'real_free_or_main_recording_or_recovery':False,
        'goal_complete':False,'persistent_write_release':False}
    im.write_json(out/'free-message-results.json',proof)
    (out/'executed-source.py').write_bytes(Path(__file__).read_bytes())
    print(json.dumps({'status':proof['status'],'requests':len(requests),'decoder_cases':len(decoders),
                      'bounded_fragments':proof['bounded_fragments'],'real_free_proven':False}))


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--output',required=True);args=ap.parse_args()
    im.volume();out=Path(args.output).resolve();assert STAGE in out.parents and not out.exists();out.mkdir()
    try:run(out)
    except Exception:
        (out/'attempt-source.py').write_bytes(Path(__file__).read_bytes())
        im.write_json(out/'attempt-failure.json',{'traceback':traceback.format_exc(),'passing_result':False})
        if 'CURRENT_GUEST' in globals():
            m=CURRENT_GUEST
            im.write_json(out/'failure-state.json',{'pc':hex(m.uc.reg_read(r.reg.UC_ARM64_REG_PC)),
                'reason':m.reason,'last_pcs':[hex(x) for x in m.pcs[-12:]],
                'wrapper_entries':m.wrapper_entries,'module_alloc_entries':m.module_alloc_entries,
                'message_entries':m.message_entries,'kernel_entries':m.kernel_service_entries})
        raise


if __name__=='__main__':main()
