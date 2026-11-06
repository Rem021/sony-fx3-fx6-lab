#!/usr/bin/env python3
"""Audit pinned public-doc scope and actual local file properties, no devices.

Reference interval arithmetic is not a camera read or backup validation. This
script never imports USB libraries, launches payloads or generates flash plans.
"""
from pathlib import Path
import datetime
import hashlib
import json
import sys

STAGE=Path(__file__).resolve().parent
sys.path.insert(0,str(STAGE.parent/'stage65-windows-cache-and-runtime-readiness'))
import prepare_handoff as h


def main():
    h.im.volume();s=STAGE;im=h.im;out=s/'completed-evidence-review.json';assert not out.exists()
    prior=s.parent/'stage76-native-reselection-and-packet-lifetime/final-receipt.json'
    assert im.sha(prior.read_bytes())=='9832673d38a3888c91d7d593719978823701cb5ce5c38e184528f5b8f1997014'
    j=json.loads(prior.read_text());assert len(j['files'])==15
    for row in j['files']:assert im.sha((h.ROOT/row['path']).read_bytes())==row['sha256']
    assert (s/'goal-status-before.json').read_bytes()==(h.BASE/'GOAL_STATUS.json').read_bytes()==(prior.parent/'goal-status-after.json').read_bytes()
    source=json.loads((s/'source-manifest.json').read_text())
    assert len(source['sources'])==3 and not source['code_or_payloads_downloaded_or_executed']
    texts={}
    pins={'README.md':'dac6d70739bfcfa51710b4f8613f4d16166ab7bde04709a7da1a974a9fc020aa',
          '操作手册.md':'0a5266d4209113e8fccc6c886cc1eb591eee05557b04e637cd52c18a9ba031b2',
          '硬件说明.md':'4ff60e3df394d78d196781d350ace7f13b02e5e82c50bb4634bfd991a1b66737'}
    for row in source['sources']:
        assert row['commit']=='d5bb9485dfe7cc4bf13a4ead3a7437c2f40240a9'
        p=h.ROOT/row['saved_path'];raw=p.read_bytes()
        assert im.sha(raw)==row['sha256']==pins[row['upstream_path']]
        texts[row['upstream_path']]=raw.decode()
    manual=texts['操作手册.md'];readme=texts['README.md']
    for value in ('0x379000','1,864,368,128','0x8000','0x378000','0x1000','512','A6700-AP-read-candidate'):
        assert value in manual
    assert '完整备份恢复尚未提供' in readme and '未确认整个物理 eMMC 容量' in manual
    # These constants are copied from the pinned reference documentation,
    # never obtained from the user's FX3. Keep planned ranges and data apart.
    count=0x379000;sector_bytes=512;maximum=0x8000
    assert count*sector_bytes==1864368128
    ranges=[]
    for start in range(0,count,maximum):
        ranges.append({'start_sector':start,'sector_count':min(maximum,count-start)})
    assert len(ranges)==112 and len([x for x in ranges if x['sector_count']==maximum])==111
    assert ranges[-1]=={'start_sector':0x378000,'sector_count':0x1000}
    assert all(a['start_sector']+a['sector_count']==b['start_sector'] for a,b in zip(ranges,ranges[1:]))
    assert sum(x['sector_count'] for x in ranges)==count
    user_bytes=count*sector_bytes;boot_bytes=0x2000*sector_bytes
    known_bytes=user_bytes+2*boot_bytes
    assert boot_bytes==4194304 and known_bytes==1872756736
    coverage={'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'source_model':'ILCE-6700','source_firmware':'2.00','scope':'PUBLIC_DOCUMENT_REFERENCE_ARITHMETIC_ONLY',
        'user_partition_table_range_sectors':count,'sector_bytes':sector_bytes,
        'user_documented_range_bytes':user_bytes,'maximum_chunk_sectors':maximum,
        'full16MiB_chunks':111,'last_chunk_sectors':0x1000,'last_chunk_bytes':0x1000*512,
        'user_chunks_total':112,'reference_intervals_not_device_reads':ranges,
        'boot0_documented_prefix_bytes':boot_bytes,'boot1_documented_prefix_bytes':boot_bytes,
        'sum_of_documented_ranges_bytes':known_bytes,
        'minimum_data_bytes_if_each_documented_range_read_twice':known_bytes*2,
        'actual_raw_images_or_double_read_hashes_verified_here':False,
        'whole_physical_user_area_or_boot_partitions_capacity_known':False,
        'full_capacity_coverage_percentage':None,'full_restore_demonstrated':False,
        'FX3_geometry_or_payload_compatibility_proven':False,
        'important':'Consistent range reads and SHA checks cannot establish omitted capacity, whole-body authenticity, plaintext/raw format compatibility or a working restore path.'}
    im.write_json(s/'reference-backup-coverage.json',coverage)
    rea_receipt=json.loads((s/'REA-source-receipt.json').read_text())
    rea=(s/'public-source-snapshots/REA-firmware-analysis.md').read_bytes()
    assert rea_receipt['commit']=='f89b03e738fe94f2bea6927c84e05871293707ea'
    assert im.sha(rea)==rea_receipt['sha256']
    rt=rea.decode()
    assert 'at most **128 MiB**' in rt and 'verified on Linux x64' in rt
    assert 'complete firmware reconstruction' in rt and 'other hosts and architectures remain unverified' in rt
    receipt_path=h.BASE/'fx3-7.02-download-receipt.json';download=json.loads(receipt_path.read_text())
    package=h.BASE/'fx3-7.02-BODYDATA.DAT'
    assert package.resolve()==Path(download['file']).resolve() and package.stat().st_size==download['size_bytes']==811876768
    with package.open('rb') as stream:digest=hashlib.file_digest(stream,'sha256').hexdigest()
    assert digest==download['sha256']=='f040affe234a8b6ec996ba616108c0014573f3cf28deb8b442fd0be091cac854'
    av=h.BASE/'stage2/extraction/files/nflasha3/av-cam.bin';raw=av.read_bytes()
    assert im.sha(raw)==im.PINS['stage2/extraction/files/nflasha3/av-cam.bin']
    assert raw[:4]!=b'\x7fELF' and raw[8:12]==b'ORIL'
    limit=128*1024*1024
    tool={'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'source_commit':rea_receipt['commit'],'source_sha256':im.sha(rea),
        'documented_firmware_input_limit_bytes':limit,
        'local_official_FX3_package_bytes':package.stat().st_size,'local_package_sha256_reverified':digest,
        'package_within_documented_firmware_input_limit':package.stat().st_size<=limit,
        'local_avcam_bytes':len(raw),'local_avcam_sha256':im.sha(raw),
        'avcam_within_size_allowance':len(raw)<=limit,'avcam_ELF_magic':False,
        'firmware_workflow_validation':'Linuxx64 with generated gzip/USTAR/ext4 and Linuxx64ELF child; proprietary formats/other hosts/architectures unverified in this document.',
        'native_raw_image_support_or_Mac_firmware_tool_availability_proven':False,
        'REA_session_or_firmware_engine_launched_here':False,
        'scope':'Limit applies to documented firmware entry, not every REA native tool. Splitting must preserve real source/offset/provenance; size alone does not establish native support. Analysis complete is not reconstruction or safe reflash.'}
    assert not tool['package_within_documented_firmware_input_limit'] and tool['avcam_within_size_allowance']
    im.write_json(s/'REA-input-and-native-admission-scope.json',tool)
    observations=json.loads((s/'upstream-observation-receipt.json').read_text())
    refs={(x['repo'],x['ref']):x['sha'] for x in observations['read_only_git_refs']}
    assert refs[('QAQLeonard/a7c2-fl23-research','HEAD')]=='ef7db116e13e37be91e9af20360dc9bba8d64a9b'
    matrix={'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'target_model':'ILME-FX3','target_firmware':'7.02',
        'candidates':[
            {'method':'A7CII Tools3.0.3/app factory restore','supported_source_model':'ILCE-7CM2/2.01',
             'kind':'application/session-dependent scoped restoration','FX3_supported':False,
             'independent_of_installed_application_and_service_mode_proven':False},
            {'method':'A7CII movie/P workaround','supported_source_model':'A7CII self-reported cases',
             'kind':'surviving shooting-mode boot path','FX3_supported':False,
             'evidence_quality':'community reports, one additional confirmation observed2026-10-26; not independent replication'},
            {'method':'A6700 Pico/RAM read Fastboot','supported_source_model':'ILCE-6700/2.00',
             'kind':'hardware cold-start RAM code plus partial-scope backup',
             'FX3_supported':False,'full_restore_proven_by_source':False,
             'current_cached_PnP_authorization_includes_RAM_injection':False},
            {'method':'A7IV bootrom/RAM Fastboot','supported_source_model':'ILCE-7M4',
             'kind':'other-model author research; boot0 crypto handling explicitly excluded',
             'FX3_supported':False,'FX3_ROM_entry_RAM_storage_map_crypto_and_same_body_restore_proven':False}],
        'required_before_any_FX3_independent_recovery_claim':['FX3-specific boot entry and identity; payload and memory/storage map verification',
            'Same-body healthy originals and mapped backup ranges with authenticated format/geometry',
            'Bounded FX3 restore writer, verification and documented failure coverage',
            'Healthy-body nondestructive independent-entry validation and authorized hardware workflow'],
        'existing_Mac_and_Windows_alone_prove_rescue':False,'source_reference_numbers_not_FX3_constants':True,
        'unknown_actual_USB_HID_identity_not_a_recovery_protocol_proof':True,
        'goal_complete':False,'persistent_write_release':False}
    im.write_json(s/'FX3-independent-recovery-transfer-matrix.json',matrix)
    review={'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'status':'PASS_PINNED_SOURCE_SCOPE_AND_REFERENCE_ARITHMETIC_NOT_DEVICE_RECOVERY',
        'prior_sealed_files_verified':15,'public_A6700_documents_pinned_and_verified':3,
        'reference_user_chunks':112,'documented_range_sum_bytes':known_bytes,
        'official_FX3_package_hash_reverified':True,'REA_original_package_oversize_for_documented_entry':True,
        'raw_avcam_not_ELF_in_documented_firmware_child_workflow':True,
        'A7CII_source_HEAD_unchanged_from_stage46':True,
        'new_case_confirmation_observed_not_FX3_validation':True,
        'actual_camera_backup_full_restore_or_independent_FX3_rescue_proven':False,
        'reference_payload_or_vendor_tool_executed':False,
        'Windows_UU_camera_operations':False,'goal_complete':False,'persistent_write_release':False}
    im.write_json(out,review)
    print(json.dumps({'status':review['status'],'reference_chunks':112,
                      'documented_range_bytes':known_bytes,'real_FX3_rescue_proven':False}))


if __name__=='__main__':main()
