#!/usr/bin/env python3
"""Seal this research checkpoint without rerunning downloads, failed extraction or old stages."""
from pathlib import Path
from hashlib import sha256,file_digest
from datetime import datetime,timezone
import ast,json,plistlib,subprocess,struct
from wbi_page_table_candidates import Snapshot,HERE,ROOT


def main():
    assert not (HERE/'final-receipt.json').exists(),'Already sealed; do not mutate or repeat this checkpoint'
    volume=plistlib.loads(subprocess.check_output(['diskutil','info','-plist','/Volumes/KAFU2T']))
    assert volume['VolumeUUID']=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
    def digest(path):
        with path.open('rb') as f:return file_digest(f,'sha256').hexdigest()
    def load(name):return json.loads((HERE/name).read_bytes())
    directories=[HERE.parent]+[HERE.parent/n for n in ('route-20261028','consumer-20261028','resource-20261028','binding-20261028','package-20261028')]
    old=[]
    for directory in directories:
        receipt=directory/'final-receipt.json';raw=receipt.read_bytes();meta=json.loads(raw)
        for row in meta['files']:
            file=directory/row['path'];assert file.stat().st_size==row['bytes'] and digest(file)==row['sha256'],str(file)
        old.append(dict(receipt=str(receipt.relative_to(ROOT)),sha256=sha256(raw).hexdigest(),files_verified=len(meta['files'])))
    assert sum(r['files_verified'] for r in old)==1599
    print('PREVIOUS_SEALED_FILES_PASS',1599,flush=True)
    fw=ROOT/'work/sony-firmware-20261024'
    pins={
        fw/'fx3-7.02-BODYDATA.DAT':json.loads((fw/'fx3-7.02-download-receipt.json').read_bytes())['sha256'],
        fw/'fx3-7.02-decrypted.fdat':json.loads((fw/'fx3-7.02-offline-manifest.json').read_bytes())['decrypted_fdat_sha256'],
        fw/'stage2/extraction/nflasha5.img':load('wbi2-map-results.json')['source_sha256'],
        fw/'stage2/extraction/nflasha15.img':load('ap-consumer-candidates.json')['partition_sha256'],
        fw/'stage2/extraction/files/nflasha8/cpapp-b.bin':'c90d00d807874a5309dc1b65b203287e83608ceee513cc57b53409333fb6bcba',
        fw/'stage2/extraction/files/nflasha3/av-cam.bin':'0cb7e03a59b4ec3d7633664ab0f7a9477892d1aaf442b9db83a7e9a62a49bdaf',
        fw/'stage2/extraction/files/nflasha15/lib/appFw.so':'545c5053a74e04ffbf2bbaaf80f558092dd545ed2298b2395ca547dbba58290f'
    }
    originals=[]
    for path,pin in pins.items():
        assert digest(path)==pin,str(path)
        originals.append(dict(path=str(path.relative_to(ROOT)),bytes=path.stat().st_size,sha256=pin,unchanged=True))
    cab=load('cab-index-results.json');members=load('cab-mspack-extraction-results.json')
    exe=HERE/'official-interim/01_Update_ILMEFX3V20x.exe'
    assert digest(exe)==cab['source_sha256']==load('official-interim/member-receipt.json')['exe_sha256']
    assert len(cab['files'])==46 and len(cab['folders'])==11
    for row in members['members']:
        path=HERE/'interim-members/mspack'/row['name']
        assert row['exit_code']==0 and path.stat().st_size==row['expected_bytes']==row['bytes'] and digest(path)==row['sha256']
    prefix=load('decoder-prefix-comparison.json');partial=HERE/'interim-members/FirmwareA1Data_ILMEFX3V204.dat.part'
    assert prefix['prefix_match'] and partial.stat().st_size==prefix['bytes'] and digest(partial)==prefix['sha256']
    assert digest(HERE/'tools/extract-cab-mspack')==load('tools/build-receipt.json')['binary_sha256']
    assert not (HERE/'work-third-party/libmspack').exists() and load('third-party-source-cleanup.json')['source_directory_removed']
    interim=load('interim-fdat-inventory.json');assert len(interim['packages'])==2
    assert [(p['header']['firmware_version'],len(p['tar_members'])) for p in interim['packages']]==[('2.04',135),('2.05',134)]
    assert all(p['outer_crc32_matches'] and p['header']['header_crc32_matches'] and not p['all_plaintext_blocks_checked'] for p in interim['packages'])
    assert len(load('random-reader-validation.json')['offsets'])==13
    wbi=load('wbi2-map-results.json');assert wbi['section_count']==1399 and wbi['stored_section_count']==1317 and wbi['omitted_section_count']==82 and not wbi['physical_overlaps']
    identity=load('skd-snapshot-code-results.json');assert len(identity['metadata'])==5 and all(m['match'] for m in identity['metadata'])
    assert len(identity['functions'])==6 and all(f['read_success'] and f['symbol_record_and_name_match'] and f['data_bytes']==0 for f in identity['functions'])
    snapshot=Snapshot();root=int(identity['root_physical_address'],16);base=int(identity['library_base_candidate'],16)
    for row in identity['metadata']:
        raw=snapshot.virtual(root,base+int(row['relative_va'],16),row['bytes']);assert sha256(raw).hexdigest()==row['sha256']
    for row in identity['functions']:
        va=int(row['symbol']['va'],16);raw=snapshot.virtual(root,base+va,row['symbol']['bytes'])
        assert raw==(HERE/row['output']).read_bytes() and sha256(raw).hexdigest()==row['sha256']
    for row in load('skd-helper-static-results.json')['fragments']:
        raw=snapshot.virtual(root,base+int(row['va'],16),row['bytes'])
        assert raw==(HERE/'snapshot-fragments'/(row['label']+'.bin')).read_bytes() and sha256(raw).hexdigest()==row['sha256']
    modules=load('snapshot-link-map-inventory.json')['modules'];assert len(modules)==129 and sum(m['name'] is None for m in modules)==1
    for i,module in enumerate(modules):
        address,nameptr,dynamic,nextmap,prevmap=struct.unpack('<5Q',snapshot.virtual(root,int(module['link_map_va'],16),40))
        assert address==int(module['base'],16) and dynamic==int(module['dynamic_va'],16) and nameptr==int(module['name_pointer'],16)
        assert prevmap==(int(modules[i-1]['link_map_va'],16) if i else 0)
        assert nextmap==(int(modules[i+1]['link_map_va'],16) if i+1<len(modules) else 0)
    snapshot.close()
    rsa=load('fdat-public-rsa-probe-results.json');assert len(rsa['public_keys'])==5 and len(rsa['packages'])==3
    assert sum(len(p['public_key_trials']) for p in rsa['packages'])==15
    assert all(not t['pkcs1_v1_5_padding_valid'] for p in rsa['packages'] for t in p['public_key_trials'])
    for path in HERE.rglob('*.py'):ast.parse(path.read_bytes(),filename=str(path))
    validation=dict(status='PASS_CHECKPOINT_SOURCE_AND_PROVENANCE_VALIDATION',previous_files_verified=1599,
        source_pin_checks=len(pins),original_cab_members=len(members['members']),snapshot_identity_regions=5,
        snapshot_functions=6,snapshot_helper_fragments=4,reciprocal_module_records=129,unreadable_module_names=1,
        rsa_candidate_trials=15,rsa_valid_padding_trials=0,all_interim_plaintext_blocks_checked=False,
        old_stages_rerun=False,network_required_for_this_validation=False,camera_usb_phone_actions=0,
        scope='Original byte identities, static snapshot provenance, strict metadata identity, and reciprocal module links. No Sony code, installer, updater, live memory, camera, signing or flash execution.')
    (HERE/'validation-results.json').write_text(json.dumps(validation,indent=2)+'\n')
    index=ROOT/'README.md';before=index.read_bytes();marker=b'tail-20261028/README.md';assert marker not in before
    entry='\n\n### FX3 原始过渡固件与 WBI 保护函数恢复（2026-10-28）\n\n- [2.04／2.05 原件提取、页表与 SKD 静态恢复](work/fx3-color-port-20261027/tail-20261028/README.md)：独立 LZX 提取三份原成员，旧固件稀疏枚举及 13 处明文对照通过；从原 WBI 页表核对恢复六个 SKD 函数，验证 129 个加载器模块记录。15 组具体 RSA 尾部探测未匹配；实际输入校验、完整色彩链和可刷入包仍未完成，目标 active，无设备操作。\n'
    with index.open('ab') as out:out.write(entry.encode())
    after=index.read_bytes();assert after==before+entry.encode(),'Project index changed concurrently; preserve and inspect'
    files=[]
    for path in sorted(HERE.rglob('*')):
        if path.is_file() and '__pycache__' not in path.parts and path.name!='final-receipt.json':
            files.append(dict(path=str(path.relative_to(HERE)),bytes=path.stat().st_size,sha256=digest(path)))
    # Older receipts and index prefix remain pinned; no old research script was invoked.
    for row in old:assert digest(ROOT/row['receipt'])==row['sha256']
    receipt=dict(created_utc=datetime.now(timezone.utc).isoformat(),volume_uuid=volume['VolumeUUID'],validation=validation,
        original_binaries=originals,previous_sealed_material=old,project_index_prefix_unchanged=True,
        project_index_before_bytes=len(before),project_index_before_sha256=sha256(before).hexdigest(),project_index_after_sha256=sha256(after).hexdigest(),
        camera_usb_phone_actions=0,private_rsa_parameters_read_or_derived=False,new_signature_generated=False,
        full_modified_firmware_emitted=False,flashable_package_produced=False,persistent_goal_status='active',goal_completion_claimed=False,files=files)
    final=HERE/'final-receipt.json';final.write_text(json.dumps(receipt,indent=2)+'\n');assert json.loads(final.read_bytes())==receipt
    print('SEALED',len(files),'new files; previous verified',1599,'goal active; flashable package',False,flush=True)


if __name__=='__main__':main()
