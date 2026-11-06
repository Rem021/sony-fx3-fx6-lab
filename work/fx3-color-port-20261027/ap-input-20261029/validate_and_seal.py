#!/usr/bin/env python3
"""Check source pins and recorded scopes, append project index, seal this stage."""
from pathlib import Path
import ast,datetime,hashlib,json,plistlib,shutil,subprocess

HERE=Path(__file__).resolve().parent
PROJECT=HERE.parents[2]

def digest(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def main():
    assert not (HERE/'final-receipt.json').exists()
    volume=plistlib.loads(subprocess.check_output(['diskutil','info','-plist','/Volumes/KAFU2T']))
    assert volume['VolumeUUID']=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
    previous=HERE.parent/'transport-20261029';receipt=json.loads((previous/'final-receipt.json').read_text())
    for row in receipt['files']:
        p=previous/row['path'];assert p.stat().st_size==row['bytes'] and digest(p)==row['sha256']
    package=HERE.parent/'package-20261028';old=json.loads((package/'final-receipt.json').read_text())
    helper_pins=[]
    for name in ['cbc_vectors.py','original_block_checker_guest.py']:
        row=next(r for r in old['files'] if r['path']==name);assert digest(package/name)==row['sha256'];helper_pins.append(dict(path=name,sha256=row['sha256']))
    static=json.loads((HERE/'current-static-results.json').read_text());sources=[]
    for source in static['sources']:
        p=Path(source['path']);assert digest(p)==source['sha256'];sources.append(dict(path=str(p),sha256=source['sha256']))
    for source in json.loads((HERE/'additional-source-members.json').read_text()):
        p=HERE/source['output'];assert p.stat().st_size==source['bytes'] and digest(p)==source['sha256']
    consumer=json.loads((HERE/'current-consumer-results.json').read_text())
    assert consumer['regular_files_read']==797 and consumer['elf_count']==532
    assert any(r['path']=='/bin/crypter.elf' for r in consumer['hits'])
    assert any(r['path']=='/lib/libIMDB.so' for r in consumer['hits'])
    legacy=json.loads((HERE/'legacy-format-compatibility-results.json').read_text())
    assert legacy['first512_match'] and not legacy['last512_match']
    assert legacy['legacy_decrypted_original_block_result']['exception']['code']=='0x30002'
    assert legacy['in_memory_legacy_reencoding']['restored_original_plain_block'] and not legacy['in_memory_legacy_reencoding']['output_written']
    header=json.loads((HERE/'header-guest-results.json').read_text());assert len(header['cases'])==8
    assert all(r['accepted']==(r['fixture'] in ['original','changed_region_recomputed_crc']) for r in header['cases'])
    snapshot=json.loads((HERE/'registry-and-snapshot-results.json').read_text())
    assert snapshot['status']=='PARTIAL_REGISTRY_ONLY_WBI_CODE_UNREADABLE'
    assert len(snapshot['registry_pointers'])==3 and len(snapshot['checks'])==5
    assert all(not c['match'] and 'error' in c for c in snapshot['checks'])
    contracts=json.loads((HERE/'current-loader-contract-results.json').read_text());assert len(contracts['virtual_contracts'])==7
    assert any(r['text']=='/tmp_updater/updater/bodyfs/bodylib/libupdaterbody.so' for r in contracts['body_loader_literals'])
    selected=json.loads((HERE/'body-loader-selected-results.json').read_text());assert len(selected['functions'])==7 and digest(Path(selected['path']))==selected['sha256']
    for p in HERE.glob('*.py'):ast.parse(p.read_text(),filename=str(p))
    now=datetime.datetime.now(datetime.timezone.utc).isoformat()
    validation=dict(created_utc=now,previous_transport_files_unchanged=len(receipt['files']),imported_helpers_unchanged=helper_pins,
        source_pins=sources,consumer_scan=dict(regular_files=797,elf_files=532,bytes=consumer['bytes_read']),
        source_function_slices=sum(len(s['functions']) for s in static['sources']),body_function_slices=7,
        original_header_guest_cases=8,old_format_block_result='Official CBC block rejected by old ECB rule; in-memory legacy 1 KiB reencoding roundtrip passes original checksum.',
        snapshot_status=snapshot['status'],snapshot_code_identity_confirmed=False,registry_pointers=3,
        no_native_vendor_programs=True,camera_usb_phone_actions=0,full_modified_firmware_emitted=False,flashable_package_produced=False,
        goal_turn_classification='progress',persistent_goal_status='active',pending_user_questions=[],live_task_jobs_at_seal=[])
    (HERE/'validation-results.json').write_text(json.dumps(validation,indent=2)+'\n')
    index=PROJECT/'README.md';before=index.read_bytes();assert 'ap-input-20261029/README.md' not in before.decode()
    entry='\n### FX3 当前 AP 旧文件更新链（2026-10-29）\n\n- [原 crypter 调用者、格式和动态库加载条件](work/fx3-color-port-20261027/ap-input-20261029/README.md)：7.02 AP 全部 797 普通文件／532 ELF 定位 crypter 与模块登记；孤立旧格式重编码及八组原头部检查通过。候选链仍缺正常入口准入与实际加载证据，WBI 对应代码页不可读；无完整修改包或设备动作，目标 active。\n'
    with index.open('ab') as stream:stream.write(entry.encode())
    assert index.read_bytes().startswith(before)
    files=[]
    for p in sorted(HERE.rglob('*')):
        if not p.is_file() or '__pycache__' in p.parts or p.name=='final-receipt.json':continue
        files.append(dict(path=str(p.relative_to(HERE)),bytes=p.stat().st_size,sha256=digest(p)))
    result=dict(created_utc=now,volume_uuid=volume['VolumeUUID'],free_bytes=shutil.disk_usage('/Volumes/KAFU2T').free,
        previous_transport_receipt_sha256=digest(previous/'final-receipt.json'),validation=validation,
        project_index_before_bytes=len(before),project_index_before_sha256=hashlib.sha256(before).hexdigest(),project_index_prefix_unchanged=True,
        goal_completion_claimed=False,persistent_goal_status='active',files=files)
    (HERE/'final-receipt.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'sealed':len(files),'previous_transport_preserved':len(receipt['files']),'header_cases':8,'snapshot':'partial unreadable','flashable_package':False,'goal':'active'}))

if __name__=='__main__':main()
