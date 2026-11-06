#!/usr/bin/env python3
"""Bind completed acquisition/model evidence to immutable current file hashes."""
import ast
import datetime
import hashlib
import json
from pathlib import Path
import plistlib
import subprocess

HERE = Path(__file__).resolve().parent
TASK = HERE.parent


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    assert not (HERE / 'verification-receipt.json').exists()
    volume = plistlib.loads(subprocess.check_output(['diskutil','info','-plist','/Volumes/KAFU2T']))
    assert volume['VolumeUUID'] == 'F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
    previous = TASK / 'SD-frame-admission-20261030'
    receipt = previous / 'final-receipt.json'
    assert digest(receipt) == '9154e28a1a53179d13c64118316e723cb2a461555571dd815f454a430508fc6e'
    sealed = json.loads(receipt.read_text())['files']
    for row in sealed:
        path = previous / row['path']
        assert path.stat().st_size == row['bytes'] and digest(path) == row['sha256']
    old_failure = json.loads((HERE / 'acquisition-receipt.json').read_text())
    old = json.loads((HERE / 'acquisition-current-etag-receipt.json').read_text())
    assert old_failure['http_status'] == 412 and old['http_status'] == 206
    assert old['If_Match'] == old_failure['headers']['ETag']
    assert old['result'] == 'COMPLETE_AXS_MEMBER_CRC_AND_ADJACENT_MD5_VERIFIED'
    assert old['range_bytes'] == old['requested_bytes'] == 29330785
    assert digest(HERE / old['range_path']) == old['range_sha256']
    assert not old['whole_archive_downloaded'] and not old['whole_archive_identity_proven']
    for row in old['extracted']:
        path = HERE / row['path']
        assert row['CRC32_verified'] and row['local_header_and_prior_directory_fields_match']
        assert path.stat().st_size == row['bytes'] and digest(path) == row['sha256']
    catalogue = json.loads((HERE / 'AXS601-China-catalog.json').read_text())
    assert digest(HERE / catalogue['path']) == catalogue['sha256']
    assert catalogue['http_status'] == 200 and catalogue['result'] and catalogue['code'] == '00'
    item = next(x for x in catalogue['response']['returnData']['Data'] if x['id'] == '00003229')
    new_download = json.loads((HERE / 'AXS601-acquisition.json').read_text())
    new = json.loads((HERE / 'AXS601-local-verification.json').read_text())
    assert new_download['http_status'] == 200 and new_download['url'] in item['downloadPath']
    assert digest(HERE / new_download['path']) == new_download['sha256'] == new['ZIP_sha256']
    assert new['result'] == 'COMPLETE_OFFICIAL_ZIP_CRC_AND_FIRMWARE_MD5_VERIFIED' and new['network_requests'] == 0
    ordinary = [x for x in new['members'] if not x['name'].endswith('/')]
    assert len(new['members']) == 7 and len(ordinary) == 6 and all(x['CRC32_verified'] for x in ordinary)
    for row in new['members']:
        if row.get('saved_path'):
            assert digest(HERE / row['saved_path']) == row['sha256']
    assert digest(HERE / new['firmware_path']) == new['firmware_sha256']
    analysis = json.loads((HERE / 'structure-analysis.json').read_text())
    assert len(analysis['firmware_samples']) == 2
    holdout = 0
    for row in analysis['firmware_samples']:
        assert digest(HERE / row['source']) == row['sha256']
        candidate = HERE / row['candidate_path']
        assert candidate.stat().st_size == 1024 and digest(candidate) == row['candidate_sha256']
        assert row['candidate_nonzero_byte_count'] == 16 == sum(bool(b) for b in candidate.read_bytes())
        assert row['body_candidate_offset'] == 1100 and row['total_length_relation_matches']
        assert len(row['independent_run_fits']) == 6
        for fit in row['independent_run_fits']:
            assert fit['fit_degree'] == 16 and fit['taps'] == [11,13,14,16] and fit['held_out_mismatches'] == 0
            holdout += fit['held_out_bits']
        assert not row['body_or_private_loader_readable']
        assert all(not x['complete_valid_stream'] for x in row['bounded_gzip_checks'])
    assert holdout == 694
    assert not analysis['VENICE_or_FX5_private_ISP_recovered'] and not analysis['body_cipher_guesses_or_trials']
    assert not analysis['VENICE_direct_comparison']['AXS_mask_or_cipher_attempted']
    scripts = sorted(HERE.glob('*.py'))
    for script in scripts:
        ast.parse(script.read_text(),filename=str(script))
    requirements = json.loads((previous / 'verification-receipt.json').read_text())['requirements_preserved']
    result = {'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'status':'PASS_TWO_ORIGINAL_AXS_SAMPLES_AND_BOUNDED_HEADER_MODEL_NOT_TARGET_FLASH_READINESS',
              'previous_goal_turn_classification':'progress: original historical admission data-path contract completed and sealed',
              'previous_sealed_files_verified':len(sealed), 'previous_seal_sha256':digest(receipt),
              'current_progress':'Two complete official AXS firmware members acquired/verified and a cross-version bounded header model inferred; no loader or VENICE body decode.',
              'AXS600_complete_member_CRC_and_MD5':True, 'AXS601_complete_ZIP_regular_member_CRC_count':len(ordinary),
              'AXS601_firmware_MD5_verified':True, 'ZIP_files_or_members_pinned':True,
              'header_samples':2, 'fitted_runs':12, 'held_out_bits_verified':holdout,
              'body_readability_established':False, 'VENICE_reader_equivalence_established':False,
              'own_scripts_syntax_checked':len(scripts), 'initial_validation_failures_preserved_and_resolved':True,
              'repeated_firmware_download_for_selector_fix':False,
              'requirements_preserved':requirements, 'whole_goal_complete':False,
              'device_actions':0, 'vendor_program_execution':False,'modified_firmware_created':False,
              'private_signing_operations':False, 'other_owner_files_changed':False,
              'confirmation_pending_for_this_task':False}
    (HERE / 'verification-receipt.json').write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n')
    print(json.dumps({'status':result['status'],'previous_files':len(sealed),'AXS_samples':2,'held_out_bits':holdout,'whole_goal_complete':False}))


if __name__ == '__main__':
    main()
