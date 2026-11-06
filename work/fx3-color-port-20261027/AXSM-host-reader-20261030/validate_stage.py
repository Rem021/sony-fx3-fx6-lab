#!/usr/bin/env python3
"""Verify current artifacts cover their declared scope, never target admission."""
import ast
import datetime
import hashlib
import json
from pathlib import Path
import plistlib
import subprocess

HERE=Path(__file__).resolve().parent
TASK=HERE.parent


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()


def main():
    assert not (HERE/'verification-receipt.json').exists()
    volume=plistlib.loads(subprocess.check_output(['diskutil','info','-plist','/Volumes/KAFU2T']))
    assert volume['VolumeUUID']=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
    previous=TASK/'AXS-R7-donor-loader-20261030'
    seal=previous/'final-receipt.json'
    assert digest(seal)=='73f1c33d5bdde8abdfddb9c8489dfe37c42495b326ca9623fde5e9b19b977afb'
    old=json.loads(seal.read_text())['files']
    for row in old:
        path=previous/row['path']
        assert path.stat().st_size==row['bytes'] and digest(path)==row['sha256']
    catalogue=json.loads((HERE/'official-catalog.json').read_text())
    assert catalogue['http_status']==200 and catalogue['response']['result'] and catalogue['response']['code']=='00'
    assert digest(HERE/catalogue['path'])==catalogue['sha256']
    discovery=json.loads((HERE/'source-discovery.json').read_text())
    for row in discovery['requests']:
        assert row.get('http_status') in [200,206] and digest(HERE/row['path'])==row['sha256']
    download=json.loads((HERE/'package-acquisition.json').read_text())
    assert download['result']=='OFFICIAL_ZIP_CRC_VERIFIED_NOT_INSTALLED'
    assert digest(HERE/download['path'])==download['sha256']
    regular=[row for row in download['members'] if row['bytes']]
    assert len(regular)==3 and all(row['CRC32_verified'] for row in regular)
    for row in download['members']:
        if row.get('saved_path'):
            assert digest(HERE/row['saved_path'])==row['sha256']
    pkg=json.loads((HERE/'PKG-extraction.json').read_text())
    assert digest(HERE/'AXSMDriveSoftware.pkg')==pkg['pkg_sha256']
    assert pkg['7z_exit_code']==pkg['listing_exit_code']==0 and not pkg['installer_executed'] and not pkg['mounted']
    xar=json.loads((HERE/'XAR-structure.json').read_text())
    assert xar['source_sha256']==pkg['pkg_sha256'] and xar['toc_compressed_SHA1_verified'] and xar['file_entries']==75
    for row in xar['entries']:
        if row.get('saved_path'):
            assert row['archived_and_extracted_SHA1_verified'] and digest(HERE/row['saved_path'])==row['sha256']
    payload=json.loads((HERE/'payload-inventory.json').read_text())
    assert len(payload['packages'])==6 and payload['total_regular_files']==439
    count=0
    for component in payload['packages']:
        assert component['gzip_CRC_verified'] and digest(HERE/component['source'])==component['source_sha256']
        for row in component['entries']:
            if row['type']=='file':
                path=HERE/row['saved_path']
                assert path.stat().st_size==row['bytes'] and digest(path)==row['sha256'] and not path.stat().st_mode&0o111
                count+=1
    assert count==439
    reader=json.loads((HERE/'reader-contract.json').read_text())
    assert digest(HERE/reader['selected_source'])==reader['source_sha256']
    assert len(reader['functions'])==5 and sum(row['bytes'] for row in reader['functions'])==5928
    for row in reader['functions']:
        assert (HERE/row['raw']).stat().st_size==row['bytes'] and digest(HERE/row['raw'])==row['sha256']
    assert reader['same_named_library_whole_files_equal'] is False
    gate=json.loads((HERE/'original-header-gate-results.json').read_text())
    assert gate['source_library_sha256']==reader['source_sha256']
    assert gate['original_gate_bytes']==28 and gate['original_instructions_executed']==70 and len(gate['cases'])==10
    assert digest(HERE/'UPDATE-header-gate-original.bin')==gate['original_gate_sha256']
    for case in gate['cases']:
        assert digest(HERE/case['prefix'])==case['prefix_sha256'] and case['input_and_code_unchanged'] and case['instructions_executed']==7
    assert sum(row['matched_UPDATE_header_predicate'] for row in gate['cases'])==7
    assert all(not row['matched_UPDATE_header_predicate'] for row in gate['cases'] if row['kind']!='Embedded drive/card firmware from the same official utility')
    assert not gate['full_ReadDriveFirmwareFile_executed'] and not gate['other_parser_paths_excluded'] and not gate['VENICE_decoder_recovered']
    scripts=sorted(HERE.glob('*.py'))
    for path in scripts:
        ast.parse(path.read_text(),filename=str(path))
    requirements=json.loads((previous/'verification-receipt.json').read_text())['requirements_preserved']
    result={'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'status':'PASS_ORIGINAL_AXSM_READER_SCOPE_NOT_VENICE_DECODE_OR_FX3_FLASH_READINESS',
            'previous_goal_turn_classification':'progress: two complete original AXS samples and bounded cross-version prefix model',
            'previous_sealed_files_verified':len(old),'previous_seal_sha256':digest(seal),
            'new_progress':'Actual official host package and five original reader functions acquired; original header gate distinguishes embedded drive/card data from two AXS-R7 and one VENICE inner.',
            'ZIP_regular_member_CRC_count':3,'XAR_entries_verified':75,'component_payloads':6,'regular_payload_files_verified':count,
            'original_complete_reader_functions':5,'original_function_bytes':5928,'header_gate_original_cases':10,'header_gate_original_instructions':70,
            'entire_reader_or_vendor_app_executed':False,'device_actions':0,'modified_firmware_created':False,
            'body_cipher_or_private_signing_trials':False,'all_other_parser_paths_excluded':False,'VENICE_decoder_recovered':False,
            'own_scripts_syntax_checked':len(scripts),'requirements_preserved':requirements,'whole_goal_complete':False,
            'confirmation_pending_for_this_task':False,'other_owner_files_changed':False}
    (HERE/'verification-receipt.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'status':result['status'],'payload_files':count,'reader_functions':5,'header_gate_cases':10,'whole_goal_complete':False}))


if __name__=='__main__':
    main()
