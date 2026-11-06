#!/usr/bin/env python3
"""Validate this phase and preserve all seven prior immutable research checkpoints."""
from pathlib import Path
from hashlib import sha256,md5,file_digest
from datetime import datetime,timezone
import ast,io,json,plistlib,subprocess,sys,zlib
from read_squashfs4_gzip import SquashFS
from verify_original_fdat_rsa import public_pem

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
PREV=HERE.parent/'tail-20261028'
sys.path.insert(0,str(PREV))
from wbi_page_table_candidates import Snapshot


def main():
    assert not (HERE/'final-receipt.json').exists(),'Already sealed; do not rerun writes'
    volume=plistlib.loads(subprocess.check_output(['diskutil','info','-plist','/Volumes/KAFU2T']))
    assert volume['VolumeUUID']=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
    def load(name):return json.loads((HERE/name).read_bytes())
    def digest(path):
        with path.open('rb') as f:return file_digest(f,'sha256').hexdigest()
    old=[]
    for directory in [HERE.parent]+[HERE.parent/name for name in ('route-20261028','consumer-20261028','resource-20261028','binding-20261028','package-20261028','tail-20261028')]:
        receipt=directory/'final-receipt.json';raw=receipt.read_bytes();meta=json.loads(raw)
        for row in meta['files']:
            path=directory/row['path'];assert path.stat().st_size==row['bytes'] and digest(path)==row['sha256'],str(path)
        old.append(dict(receipt=str(receipt.relative_to(ROOT)),sha256=sha256(raw).hexdigest(),files_verified=len(meta['files'])))
    assert sum(row['files_verified'] for row in old)==1704
    print('PREVIOUS_CHECKPOINTS_PASS',1704,flush=True)
    # Original source pins, separate from the newly extracted outputs.
    fw=ROOT/'work/sony-firmware-20261024'
    pins={
        fw/'fx3-7.02-BODYDATA.DAT':json.loads((fw/'fx3-7.02-download-receipt.json').read_bytes())['sha256'],
        fw/'fx3-7.02-decrypted.fdat':json.loads((fw/'fx3-7.02-offline-manifest.json').read_bytes())['decrypted_fdat_sha256'],
        fw/'stage2/extraction/nflasha5.img':json.loads((PREV/'wbi2-map-results.json').read_bytes())['source_sha256'],
        fw/'stage2/extraction/files/nflasha8/cpapp-b.bin':'c90d00d807874a5309dc1b65b203287e83608ceee513cc57b53409333fb6bcba',
        fw/'stage2/extraction/files/nflasha3/av-cam.bin':'0cb7e03a59b4ec3d7633664ab0f7a9477892d1aaf442b9db83a7e9a62a49bdaf',
        fw/'stage2/extraction/files/nflasha15/lib/appFw.so':'545c5053a74e04ffbf2bbaaf80f558092dd545ed2298b2395ca547dbba58290f'
    }
    original=[]
    for path,pin in pins.items():
        assert digest(path)==pin,str(path)
        original.append(dict(path=str(path.relative_to(ROOT)),bytes=path.stat().st_size,sha256=pin,unchanged=True))
    updates=load('original-update-engine-results.json');assert len(updates['packages'])==2
    for package in updates['packages']:
        assert package['updater_crc32_matches']
        for row in package['members']:
            data=(HERE/row['output']).read_bytes();assert len(data)==row['bytes'] and sha256(data).hexdigest()==row['sha256'] and f'{zlib.crc32(data):08x}'==row['crc32']
    fat=load('updater-fat-extraction-results.json')
    for package in fat['packages']:
        assert package['metadata']['kind']=='FAT12' and len(package['files'])==6
        for row in package['files']:
            data=(HERE/row['output']).read_bytes();assert len(data)==row['size'] and sha256(data).hexdigest()==row['sha256']
        paths={row['path']:row for row in package['files']}
        for line in (HERE/paths['/p1chksum']['output']).read_text().splitlines():
            pin,name=line.split();data=(HERE/paths['/'+name.removeprefix('./')]['output']).read_bytes()
            assert md5(data,usedforsecurity=False).hexdigest()==pin
    # Recheck independent prior parser oracle without writing prior directories.
    oracle=json.loads((HERE.parent/'package-20261028/updater-inventory.json').read_bytes())
    with (fw/'fx3-7.02-decrypted.fdat').open('rb') as f:f.seek(oracle['filesystem_offset']);image_bytes=f.read(oracle['filesystem_bytes'])
    image=SquashFS(image_bytes);expected={row['path']:row for row in oracle['entries']};actual={row['path']:row for row in image.walk()}
    assert set(expected)==set(actual) and len(actual)==65
    for path,row in actual.items():
        prior=expected[path];assert row['type']==prior['type'] and row['mode']==prior['mode']
        if row['type']=='file':assert sha256(image.contents(row)).hexdigest()==prior['sha256']
        if row['type']=='symlink':assert row['target']==prior['target']
    # Every saved initrd ordinary file is tied back to its compressed source.
    initrd=load('original-initrd-inventory.json');assert initrd['parser_sha256']==digest(HERE/'read_squashfs4_gzip.py')
    for package in initrd['packages']:
        raw=(HERE/package['source']).read_bytes();assert sha256(raw).hexdigest()==package['source_sha256']
        image=SquashFS(raw);entries={row['path']:row for row in image.walk()};assert len(entries)==342
        assert len({row['inode'] for row in entries.values()})==image.header['inodes']==342
        assert package['ordinary_files']==216 and package['total_regular_bytes']==35523243
        assert set(entries)=={row['path'] for row in package['entries']}
        for row in package['entries']:
            assert entries[row['path']]['type']==row['type']
            if row['type']=='file':
                data=image.contents(entries[row['path']]);saved=HERE/row['output']
                assert not saved.is_symlink() and saved.read_bytes()==data and sha256(data).hexdigest()==row['sha256']
    rsa=load('official-key-rsa-verification-results.json');pem=(HERE/rsa['key_path']).read_bytes();n,e,der=public_pem(pem)
    assert sha256(pem).hexdigest()==rsa['pem_sha256'] and der==rsa['public_key_der_sha256'] and n.bit_length()==2048 and e==65537
    assert len(rsa['packages'])==3
    for row in rsa['packages']:
        assert row['coverage_matches']==['ciphertext_body_then_iv'] and row['pkcs1_v1_5_padding_valid'] and row['sha256_digest_info_valid']
        signature=(HERE/row['original_signature_output']).read_bytes();assert len(signature)==256 and sha256(signature).hexdigest()==row['signature_sha256']
        encoded=pow(int.from_bytes(signature,'big'),e,n).to_bytes(256,'big');end=encoded.find(b'\0',2)
        assert encoded[:2]==b'\0\1' and encoded[2:end]==b'\xff'*(end-2) and encoded[-32:].hex()==row['digest_info_sha256']
        assert len(row['in_memory_single_byte_mutations'])==4 and all(not change['retained_signature_accepts'] for change in row['in_memory_single_byte_mutations'])
    native=load('native-openssl-verification-results.json')
    assert [(c['includes_iv'],c['exit_code']) for c in native['cases']]==[(True,0),(False,1)]
    assert native['cases'][0]['stdout'].strip()=='Verified OK'
    assert not load('rsa-key-family-comparison.json')['matching_modes']
    core=load('cryptcore-snapshot-results.json');snapshot=Snapshot();root=int(core['root_physical_address'],16);base=int(core['module']['base'],16)
    assert len(core['identity'])==5 and all(row['match'] for row in core['identity'])
    for row in core['identity']:
        assert sha256(snapshot.virtual(root,base+int(row['va'],16),row['bytes'])).hexdigest()==row['sha256']
    for row in core['functions']:
        data=snapshot.virtual(root,base+int(row['va'],16),row['bytes']);assert data==(HERE/row['output']).read_bytes() and sha256(data).hexdigest()==row['sha256']
    for name,label,va_field in [('skd-key-trust-callback-results.json','SKD-service-callback','callback_va'),('skd-key-lookup-results.json','SKD-key-lookup','va')]:
        row=load(name);data=snapshot.virtual(int(row['root'],16),int(row['base'],16)+int(row[va_field],16),row['bytes'])
        assert data==(HERE/'snapshot-fragments'/(label+'.bin')).read_bytes() and sha256(data).hexdigest()==row['sha256']
    snapshot.close()
    # Original text spans use a different PT_LOAD mapping from the data/vtable region.
    from elftools.elf.elffile import ELFFile
    source=HERE/'engine-rootfs/2.05/usr/lib/libsdfileinputupdaterapi.so';raw=source.read_bytes();elf=ELFFile(io.BytesIO(raw))
    def elf_read(va,length):
        for segment in elf.iter_segments():
            start=segment['p_vaddr']
            if segment['p_type']=='PT_LOAD' and start<=va and va+length<=start+segment['p_filesz']:
                off=segment['p_offset']+va-start;return raw[off:off+length]
        raise ValueError((va,length))
    for row in load('sd-input-static-results.json')['functions']:
        assert sha256(elf_read(int(row['va'],16),row['bytes'])).hexdigest()==row['sha256']
    tables=load('sd-input-vtable-results.json')['vtables'];sd=next(row for row in tables if row['name']=='vtable for Updater::SDDecryptorModule')
    assert sd['primary_vptr']=='0x1d950'
    wait=next(row for row in sd['entries'] if row['vptr_offset']=='0xa0');assert wait['target_va']=='0x8b0c'
    for section in elf.iter_sections():
        if section['sh_type']=='SHT_RELA':
            for relocation in section.iter_relocations():
                if relocation['r_offset']==0x1df90:
                    target=elf.get_section(section['sh_link']).get_symbol(relocation['r_info_sym'])
                    assert target.name=='_ZTVN7Updater17SDDecryptorModuleE'
    for path in HERE.rglob('*.py'):ast.parse(path.read_bytes(),filename=str(path))
    assert not list((HERE/'work').glob('*.whl'))
    assert load('goal-status.json')['goal']['status']=='active'
    validation=dict(status='PASS_ORIGINAL_SD_INPUT_AND_SIGNATURE_EVIDENCE_VALIDATION',prior_files_verified=1704,
        independent_squashfs_oracle_entries=65,independent_oracle_regular_file_hashes=58,
        initrd_entries_each=342,initrd_regular_files_each=216,original_boot_md5_records=4,
        original_signed_packages_verified=3,in_memory_mutation_cases_rejected=12,native_openssl_cases=2,
        cryptcore_exports_recovered=2,skd_static_callback_fragments=2,original_sd_vptr_and_dispatch_checked=True,
        old_stages_rerun=False,no_network_needed_for_validation=True,sony_programs_executed=0,device_actions=0,
        scope='Original artifacts and static code, independent decompression oracle, public RSA signatures and independent native crypto. No full modified package, signing, updater execution, device admission, boot or recovery acceptance.')
    (HERE/'validation-results.json').write_text(json.dumps(validation,indent=2)+'\n')
    index=ROOT/'README.md';before=index.read_bytes();assert b'input-20261028/README.md' not in before
    entry='\n\n### FX3 SD 更新入口与官方尾签名（2026-10-28）\n\n- [原更新引擎拆读及 RSA-2048／SHA-256 验证](work/fx3-color-port-20261027/input-20261028/README.md)：两份 19 MB 原更新分区通过 CRC32，初始化文件系统各 342 项／216 普通文件；取得真实 sdfileinput、接口库和官方公钥。三份原包验签确认覆盖完整密文＋IV，12 个改动样本不再匹配；宿主 OpenSSL 独立复核边界。完整移植及有效修改包仍未完成，目标 active，无设备操作。\n'
    with index.open('ab') as output:output.write(entry.encode())
    after=index.read_bytes();assert after==before+entry.encode(),'Concurrent index change; preserve and inspect'
    files=[]
    for path in sorted(HERE.rglob('*')):
        if path.is_file() and '__pycache__' not in path.parts and path.name!='final-receipt.json':
            files.append(dict(path=str(path.relative_to(HERE)),bytes=path.stat().st_size,sha256=digest(path)))
    for row in old:assert digest(ROOT/row['receipt'])==row['sha256']
    final=dict(created_utc=datetime.now(timezone.utc).isoformat(),volume_uuid=volume['VolumeUUID'],validation=validation,
        previous_sealed_material=old,original_binaries=original,project_index_prefix_unchanged=True,
        project_index_before_bytes=len(before),project_index_before_sha256=sha256(before).hexdigest(),project_index_after_sha256=sha256(after).hexdigest(),
        third_party_parser_downloaded=False,global_network_settings_modified=False,private_rsa_parameters_read_or_derived=False,
        new_signatures_generated=False,sony_programs_executed=0,camera_usb_phone_actions=0,full_modified_firmware_emitted=False,
        flashable_package_produced=False,persistent_goal_status='active',goal_completion_claimed=False,files=files)
    dest=HERE/'final-receipt.json';dest.write_text(json.dumps(final,indent=2)+'\n');assert json.loads(dest.read_bytes())==final
    print('SEALED',len(files),'new files; prior verified',1704,'goal active; flashable package',False,flush=True)


if __name__=='__main__':main()
