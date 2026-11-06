#!/usr/bin/env python3
"""Readback validation; do not repeat the completed decoder/controller guests."""
import ast,hashlib,json,re
from pathlib import Path
from decrypt_stream_guest import HERE,View,whole_fixture

def digest(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()

def main():
    previous=HERE.parent/'controller-20261029';receipt=previous/'final-receipt.json';pin='70af33a3def91000d3db5bbe225a6e1c8095001fa21e51ecba6234db060f5db9'
    assert digest(receipt)==pin
    rows=json.loads(receipt.read_text())['files'];assert len(rows)==36
    for row in rows:
        p=previous/row['path'];assert p.stat().st_size==row['bytes'] and digest(p)==row['sha256']
    syntax=[]
    for p in sorted(HERE.glob('*.py')):ast.parse(p.read_text(),filename=str(p));syntax.append(p.name)
    json_files=[]
    for p in sorted(HERE.rglob('*.json')):
        if p.name in ['validation-results.json','final-receipt.json']:continue
        json.loads(p.read_text());json_files.append(str(p.relative_to(HERE)))
    stream=json.loads((HERE/'decrypt-stream-results.json').read_text());lens=json.loads((HERE/'lens-header-gate-results.json').read_text());contract=json.loads((HERE/'stream-contract-results.json').read_text())
    views={r['path']:View(r['path'],r['sha256']) for r in stream['sources']+lens['sources']}
    checks=[]
    for key,count in [('decoder_unique_function_bodies',19),('selected_fragments',30)]:
        assert len(contract[key])==count
        for row in contract[key]:
            v=views[row['source']];assert hashlib.sha256(v.raw).hexdigest()==row['source_sha256']
            raw=v.read(int(row['va'],16),row['bytes']);assert hashlib.sha256(raw).hexdigest()==row['sha256']
            if 'disassembly' in row:assert (HERE/row['disassembly']).is_file()
            checks.append(dict(kind=key,source_sha256=row['source_sha256'],va=row['va'],bytes=len(raw)))
    decoded=stream['cases'];assert len(decoded)==7
    assert [r['returned'] for r in decoded]==[True,True,True,False,False,False,False]
    whole=decoded[0];plain,fixture=whole_fixture()
    assert stream['fixture']==fixture
    assert len(plain)==whole['decoded_bytes']==1259008 and hashlib.sha256(plain).hexdigest()==whole['decoded_sha256']
    assert whole['cipher_bytes']==1264640 and whole['cipher_bytes']//1024==1235 and whole['host_aes_block_calls']==79040
    assert whole['trailing_cipher_bytes']==0 and whole['output_end_flag_count']==1 and whole['last_output_end_flag']==1
    assert whole['original_function_entries']['Updater::RingBuffer::IsEnd()']>0
    assert decoded[1]['decoded_bytes']==1057 and decoded[1]['trailing_cipher_bytes']==0
    assert decoded[2]['decoded_bytes']==1020 and decoded[2]['trailing_cipher_bytes']==1024
    assert decoded[3]['decoded_bytes']==1020 and decoded[4]['host_aes_block_calls']==0
    for row in decoded[3:]:assert row['exception']['code']=='0x30002' and row['exception']['native_unwind'] is False
    for row in decoded:assert 0<row['total_instructions']<=12000000
    down=stream['downstream'];assert down['decoded_bytes_handed_off_unchanged'] and down['assembly_image_bytes']==1253376
    assert down['assembly_image_sha256']=='62e86fad175e0326969d5f1cea29d780feb496ce8034acd2c9c3954320d8ccaa' and down['plaintext_cursor_after_assembly']==1253888
    assert down['controller']['boundary']['operation']=='system_request_boundary'
    assert down['controller']['system_requests'][0]['fixture_wait_status']==0
    assert all(r['native_execution'] is False for r in down['controller']['system_requests'])
    assert len(lens['cases'])==2
    camera,accessory=lens['cases']
    assert camera['returned'] and camera['return_value']==2 and camera['copied_model_word']=='0x91030080' and camera['boundary'] is None
    assert not accessory['returned'] and accessory['boundary']['service']=='0x912503d0' and accessory['boundary']['original_request_command']==3 and accessory['boundary']['requested_message_bytes']==8
    assert accessory['boundary']['native_allocation'] is False
    assert all(r['file_cursor']==532 for r in lens['cases'])
    attempts=sorted((HERE/'attempts').glob('*.json'));assert len(attempts)==1
    assert 'ModuleNotFoundError' in json.loads(attempts[0].read_text())['error']
    links=[]
    for target in re.findall(r'\]\(([^)]+)\)',(HERE/'README.md').read_text()):
        if target.startswith('https://'):continue
        if target not in ['validation-results.json','final-receipt.json']:assert (HERE/target).exists(),target
        links.append(target)
    result=dict(status='PASS_RAM_LEGACY_STREAM_AND_ORIGINAL_LENS_CLASS_GATE',previous_controller_receipt_sha256=pin,previous_sealed_files_verified=36,syntax_files=syntax,json_files=json_files,
                source_span_checks=checks,case_counts=dict(decoder_streams=7,lens_preparation_headers=2),guest_cases_total=9,whole_plain_hash_recomputed_without_guest_rerun=True,
                consumer_handoff_is_between_separate_guests=True,startup_system_status_is_fabricated=True,actual_manager_and_input_service_proven=False,lens_service_reply_proven=False,
                native_system_calls=0,native_ipc_calls=0,native_target_loading=0,firmware_file_output=0,camera_actions=0,
                complete_venice_color_port_proven=False,goal_completion_claimed=False,termination_condition_met=False,local_readme_links=links)
    (HERE/'validation-results.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(status=result['status'],previous_files=36,decoder_function_bodies=19,fragments=30,cases=9,camera_actions=0)))

if __name__=='__main__':main()
