#!/usr/bin/env python3
"""Read back pending native free paths and independent local reply gates."""
from pathlib import Path
import datetime
import json
import struct
import free_message_path as t


def phases(case):
    assert len(case['events'])==5
    for i,e in enumerate(case['events']):
        assert int(e['SP_after'],16)%16==0
        if i==0:assert e['native_output_or_return_adapter'] is False
        else:
            assert e['native_output_or_PC_return_adapter'] is False
            chunks=e['same_instance_observation_slices']
            assert sum(x['executed'] for x in chunks)==len(e['pcs'])<=2000000
            assert all(a['end_pc']==b['start_pc'] for a,b in zip(chunks,chunks[1:]))
            assert chunks[-1]['reason']==e['reason']


def main():
    t.im.volume();s=t.STAGE;out=s/'completed-evidence-review.json';assert not out.exists()
    sealed={
        'stage64-osal-offline-link':'0bf042fe283fe4a56c9146bbe9eb5cd8cc750847877922cecf45d69355220b6a',
        'stage69-native-16M-callpath':'417033856d0b31e1019bd64b932199d826ebdefcc9321a96dae1334fae8c1d8e',
        'stage72-native-manager-teardown':'1bad5c4cfba82600385e96df861374652103168d6cef7091d0d6beca3aa8a8aa'}
    counts={}
    for name,digest in sealed.items():
        p=t.BASE/name/'final-receipt.json';j=json.loads(p.read_text())
        assert t.im.sha(p.read_bytes())==digest
        for row in j['files']:
            assert t.im.sha((t.ROOT/row['path']).read_bytes())==row['sha256'],row['path']
        counts[name]=len(j['files'])
    assert counts=={'stage64-osal-offline-link':23,'stage69-native-16M-callpath':50,'stage72-native-manager-teardown':14}
    assert (s/'goal-status-before.json').read_bytes()==(t.BASE/'GOAL_STATUS.json').read_bytes()==(t.previous.STAGE/'goal-status-after.json').read_bytes()
    p=s/'run-original-sparse-lookup-20261026/free-message-results.json'
    result=json.loads(p.read_text());raw=(s/'free_message_path.py').read_bytes()
    assert result['source_receipt']['script_sha256']==t.im.sha(raw)
    assert (p.parent/'executed-source.py').read_bytes()==raw
    assert result['source_receipt']['queue_guest_helper_sha256']==t.im.sha((t.q.STAGE/'buffer_record_fifo.py').read_bytes())
    assert result['source_receipt']['runner_sha256']==t.im.sha((t.c.STAGE/'channel_callpath.py').read_bytes())
    assert len(result['requests'])==4 and len(result['independent_decoder_cases'])==7 and result['bounded_fragments']==55
    lock_objects={}
    for case in result['requests']:
        phases(case);seed=case['seed'];handle=int(case['declared_handle'],16);bit=(handle>>15)&1
        assert seed in (0xa5,0xc3) and case['handle_bit15']==bit
        assert case['cache_descriptor_are_declared_not_real_successful_allocation']
        a,z=case['events'][-2:]
        assert a['stop_pc']==z['start_pc']==hex(t.UNIT)
        assert z['independent_entry_fixture'] is False and a['SP_after']==z['SP_before']
        assert z['reason']=='boundary: before_original_unexecuted_kernel_service'
        entries=case['original_free_entry_boundary_then_same_instance_execution']
        assert len(entries)==2 and [x['body_allowed_this_observation'] for x in entries]==[False,True]
        assert entries[0]['x0_x3']==entries[1]['x0_x3'] and entries[0]['LR']==entries[1]['LR']
        assert entries[0]['input_descriptor152_hex']==entries[1]['input_descriptor152_hex']
        d=bytes.fromhex(entries[1]['input_descriptor152_hex'])
        assert struct.unpack_from('<I',d)[0]==handle and d[8:]==bytes(0x90)
        msg=case['native_inline_message'];payload=bytes.fromhex(msg['inline_payload216_hex'])
        expected=bytearray(216);struct.pack_into('<H',expected,0,0x23)
        struct.pack_into('<I',expected,8,handle);struct.pack_into('<HH',expected,0x14,0x1111,2)
        assert payload==bytes(expected)
        assert msg['command']==hex(0x8061003c|(bit<<28))
        assert msg['size_u16']==216 and msg['state_u32']==2 and msg['source_u32']=='0x806800f3'
        alloc=case['original_OSAL_allocation_entry'];client=case['empty_ELF_client_cache']
        if bit:
            assert alloc['x0_x3'][0]=='0x8f013a' and alloc['x0_x3'][2:]==['0x34','0x0']
            assert client['client_id']==0x13a and client['returned_null_in_ELF_zero_BSS']
            assert [x['x0'] for x in client['observations']]==['0x13a','0x0']
        else:
            assert alloc['x0_x3'][0]=='0x8061003c' and alloc['x0_x3'][2:]==['0xd8','0x1']
            assert client['client_id']==0x3c and client['loaded_X21']=='0x0'
        assert case['first_allocation_is_diagnostic_before_main_send']==bool(bit)
        kernel=case['unexecuted_kernel_service']
        assert kernel['names']==['_raw_spin_lock_irqsave'] and not kernel['kernel_body_executed']
        assert not kernel['kernel_return_IRQ_lock_thread_or_allocation_adapter']
        lock_objects[(seed,bit)]=int(case['original_lock_entry']['object'],16)
        assert case['original_lock_entry']['initial_object16_hex']==bytes(16).hex()
        assert not case['reply_decoder_entered'] and not case['original_release_return_received']
        assert not case['physical_release_or_main_recording_complete']
        # Reconstruct only the original recorded metadata stores. These are
        # metadata entries with false per-entry flags, not active allocations.
        metadata=bytearray(t.GSIZE)
        for write in case['global_metadata_and_stores']:
            at=int(write['address'],16)-t.G;length=write['size'];pc=int(write['pc'],16)
            assert 0<=at and at+length<=len(metadata) and 0<length<=8
            assert t.V+0x27bca0<=pc<t.V+0x27bd8c or (pc==t.V+0x27c1ec and at==t.FLAG-t.G and length==8)
            metadata[at:at+length]=int(write['value'],16).to_bytes(length,'little')
        assert struct.unpack_from('<I',metadata,0x2000)[0]==202
        assert struct.unpack_from('<Q',metadata,t.FLAG-t.G)[0]==1
        assert struct.unpack_from('<I',metadata,4)[0]==0x123abcde
        assert all(metadata[i*32+0x18]==0 for i in range(202))
    assert all(lock_objects[(seed,1)]-lock_objects[(seed,0)]==0x210 for seed in (0xa5,0xc3))
    expected_decoder={
        'full zero status':0,'full positive status':2,'full negative status':1,
        'bad magic':1,'eight bytes unrelated kind':0,'six bytes':1,'empty inline state2':1}
    for case in result['independent_decoder_cases']:
        phases(case)
        assert case['result_W19']==expected_decoder[case['label']]
        assert case['events'][-1]['stop_pc']==hex(t.DECODE_STOP)
        assert case['events'][-1]['reason']=='boundary: after_independent_original_decoder_before_wrapper_cleanup'
        assert case['events'][-1]['SP_before']==case['events'][-1]['SP_after']==hex(t.FRAME)
        assert case['standalone_entry_not_transport_reply_or_full_wrapper_return']
        assert case['native_message_consumed_state_size_source_cleared']
        assert not case['real_send_correlation_reply_completion_physical_free_or_recovery']
        if case['label']=='eight bytes unrelated kind':
            assert case['supplied_length']==8 and case['supplied_kind']=='0xbeef'
            raw=bytes.fromhex(case['copied_output216_hex']);assert raw[8:]==bytes(208)
    blob=(t.BASE/'stage2/extraction/files/nflasha3/av-cam.bin').read_bytes()
    assert t.im.sha(blob)==result['source_receipt']['avcam_sha256']==t.im.PINS['stage2/extraction/files/nflasha3/av-cam.bin']
    for region in result['original_regions']:
        assert region['instructions']==t.im.dump(blob,int(region['start'],16),int(region['end'],16),t.V)
    # Save the newly permitted original read-only sparse lookup and its real
    # callers/lock branch from the pinned, relocated module bytes.
    mods,providers,kernel=t.c.d.link.build();text=mods['osal_uipc.ko'].section('.text')
    from capstone import Cs,CS_ARCH_ARM64,CS_MODE_ARM
    md=Cs(CS_ARCH_ARM64,CS_MODE_ARM);regions=[]
    for start,end in [(0x2938,0x2978),(0x3248,0x3294),(0x33b8,0x33dc),(0x2f48,0x2f64)]:
        data=bytes(text['data'])[start:end]
        ins=[{'offset':hex(i.address-text['base']),'bytes':i.bytes.hex(),
              'asm':i.mnemonic+' '+i.op_str} for i in md.disasm(data,text['base']+start)]
        assert len(ins)*4==end-start
        if start==0x2938:assert not any(i['asm'].startswith(('str','stp','stur','bl ','blr ')) for i in ins)
        regions.append({'text_relative_start':hex(start),'text_relative_end':hex(end),
                        'sha256':t.im.sha(data),'instructions':ins})
    audit={'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'module':'osal_uipc.ko','relocated_text_base':hex(text['base']),
        'module_text_bytes_sha256':t.im.sha(bytes(text['data'])),'regions':regions,
        'lock_object_delta_between_low_and_high_client':0x210,
        'actual_module_initialization_or_driver_state_proven':False,
        'ack_scope':'Local decoder success does not prove physical completion. An8-byte ACK may be legitimate; no protocol minimum/full-length rule, correlation failure or vulnerability is inferred.'}
    t.im.write_json(s/'sparse-client-and-ack-audit.json',audit)
    failures=[]
    for name,expected in [('run-20261026','boundary: before_original_unexecuted_kernel_service'),
                          ('run-entry-observer-20261026','unapproved execution '+hex(text['base']+0x2938))]:
        d=s/name;failed=json.loads((d/'failure-state.json').read_text())
        assert failed['reason']==expected
        assert not json.loads((d/'attempt-failure.json').read_text())['passing_result']
        assert not (d/'free-message-results.json').exists()
        failures.append({'path':name,'retained_source_sha256':t.im.sha((d/'attempt-source.py').read_bytes()),
                         'last_reason':failed['reason'],'camera_or_firmware_failure':False})
    g=json.loads((s/'goal-status-before.json').read_text())
    assert g['current_user_operational_constraint']['current_scope']=='Mac offline research and reversible local preparation only'
    review={'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'status':'PASS_ORIGINAL_PENDING_FREE_AND_INDEPENDENT_ACK_SCOPE',
        'verified_prior_sealed_file_counts':counts,'request_cases':4,'independent_decoder_cases':7,
        'total_bounded_fragments':55,'same_pending_free_request_continued_without_return_adapter':True,
        'handle_bit15_command_bit28_and_first_diagnostic_allocation_proven_in_fixture':True,
        'original_sparse_client_lookup_executed_no_fabricated_client':True,
        'all_requests_stop_before_original_kernel_lock':True,
        'independent_supplied_ack_not_injected_into_pending_transport':True,
        'eight_byte_local_success_not_protocol_vulnerability_or_physical_completion':True,
        'retained_failed_attempts':failures,'source_image_and_modules_unchanged_except_declared_original_data':True,
        'Windows_UU_camera_operations':False,'physical_release_main_recording_or_recovery_proven':False,
        'goal_complete':False,'persistent_write_release':False}
    t.im.write_json(out,review)
    print(json.dumps({'status':review['status'],'bounded_fragments':55,'requests':4,'independent_decoder_cases':7}))


if __name__=='__main__':main()
