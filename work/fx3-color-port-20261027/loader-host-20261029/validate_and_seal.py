#!/usr/bin/env python3
"""Read back this new host-reader checkpoint, preserve previous seal, append index."""
import datetime,fcntl,hashlib,json,os,plistlib,struct,subprocess
from pathlib import Path
HERE=Path(__file__).resolve().parent;TASK=HERE.parent;PROJECT=HERE.parents[2]
UUID='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
def sha(b):return hashlib.sha256(b).hexdigest()
def read(name):return json.loads((HERE/name).read_text())
def check(path,n,pin):
    b=path.read_bytes();assert len(b)==n and sha(b)==pin;return b
def main():
    final=HERE/'final-receipt.json';assert not final.exists()
    v=plistlib.loads(subprocess.check_output(['/usr/sbin/diskutil','info','-plist','/Volumes/KAFU2T']));assert v['VolumeUUID']==UUID
    previous=TASK/'donor-loader-20261029/final-receipt.json'
    assert sha(previous.read_bytes())=='fa0d3604ebe2075dcbc57ba3b1766ec8e20de9f79310f6fa4bfb0a50da5e2b90'
    old=json.loads(previous.read_text())['files']
    for r in old:check(previous.parent/r['path'],r['bytes'],r['sha256'])
    pages=read('host-source-pages.json')['pages'];index=next(r for r in pages if r['name']=='snc-index')
    page=check(HERE/'snc-index.html',index['bytes'],index['sha256']);assert index['status']==200
    archived=next(r for r in read('host-archive-pages.json')['pages'] if r['name']=='snc-japan')
    raw=check(HERE/'snc-japan-archived.html',archived['bytes'],archived['sha256']);assert archived['capture_status']==200
    download=read('host-tool-download.json');assert download['complete'] and download['status']==200
    assert download['requested_url'] in raw.decode('cp932') and download['source_page_sha256']==sha(raw)
    check(HERE/download['path'],download['bytes'],download['sha256']);assert download['bytes']==119665922
    zipinv=read('host-tool-ZIP-inventory.json');assert zipinv['CRC_all_pass'] and len(zipinv['entries'])==4
    exe=read('host-installer-structure.json');check(HERE/'originals/SncToolbox_Setup.exe',exe['bytes'],exe['sha256'])
    setup=read('setup-stream-unpack.json');assert setup['source_sha256']==exe['sha256'] and setup['stream_type']==3 and setup['files']==3
    assert setup['parsed_end']==setup['source_bytes']==exe['bytes']
    for r in setup['members']:
        assert r['zlib_complete'] and r['zlib_adler_checked'];check(HERE/r['output'],r['bytes'],r['sha256'])
    msi=read('msi-streams.json');assert len(msi['streams'])==76 and not msi['parse_issues'] and len(msi['cabinets'])==1
    cab=msi['cabinets'][0];b=check(HERE/cab['output'],cab['bytes'],cab['sha256']);assert b[:4]==b'MSCF'
    assert struct.unpack_from('<I',b,8)[0]==len(b) and struct.unpack_from('<H',b,28)[0]==len(cab['members'])
    components=read('host-component-review.json');assert components['selected_files']==26 and components['scanned_bytes']==173615339
    assert len(components['markers'])==7 and len(components['encodings'])==3
    assert sum(r['matched_preserved_bsdtar_output'] for r in components['files'])==2
    for r in components['files']:
        assert not r['wrapper_marker_hits'];check(HERE/r['output'],r['bytes'],r['sha256'])
    interfaces=read('host-PE-interfaces.json');assert len(interfaces['files'])==5
    svu=next(r for r in interfaces['files'] if r['name']=='sncverup_tool.dll');assert len(svu['exports'])==23 and svu['machine']=='0x14c'
    guest=read('svu-header-guest-results.json');dll=check(HERE/'host-components/sncverup_tool.dll',svu['bytes'],guest['source_DLL_sha256'])
    start=guest['fragment_file_offset'];fragment=bytes.fromhex(guest['fragment_bytes'])
    assert len(fragment)==25 and dll[start:start+25]==fragment and sha(fragment)==guest['fragment_SHA256']
    assert len(guest['disassembly'])==6 and len(guest['cases'])==9
    assert all(r['observed']==r['expected'] and r['original_code_and_input_unchanged'] for r in guest['cases'])
    assert sum(r['observed']=='invalid_signature_branch' and r['name'].startswith('VENICE') for r in guest['cases'])==5
    pins=read('svu-header-source-pins.json');assert len(pins['sources'])==6
    for r in pins['sources']:
        p=Path(r['path']);assert p.stat().st_size==r['bytes']
        with p.open('rb') as f:header=f.read(16)
        assert header.hex()==r['first16_hex'] and header.hex()==next(c['input_first16_hex'] for c in guest['cases'] if c['name']==r['case'])
    rpms=read('public-source-rpms.json');assert len(rpms['packages'])==2
    for r in rpms['packages']:assert r['status']==200 and r['list_exit']==0;check(HERE/r['path'],r['bytes'],r['sha256'])
    review=read('source-patch-review.json');assert len(review['files'])==23
    for r in review['files']:assert not r['private_marker_hits'];check(HERE/r['output'],r['bytes'],r['sha256'])
    spec=(HERE/'source-excerpts/sony-target-dev-rpm.spec').read_text()
    assert 'This package include only popt package.' in spec and 'cd popt\nmake\ncd ..' in spec and 'cd %{sony_objdir}/popt && make' in spec
    tool=read('archive-tool-receipt.json');assert tool['curl_exit']==0
    for r in tool['files']:check(HERE/r['output'],r['bytes'],r['sha256'])
    for parent,name in [(HERE/'reference','source-receipt.json'),(HERE/'reference/olefile','dependency-receipt.json')]:
        dep=json.loads((parent/name).read_text())
        for r in dep['files']:check(parent/r['path'],r['bytes'],r['sha256'])
    assert guest['native_Sony_programs_executed']==guest['device_actions']==0
    validation=dict(status='PASS_HOST_READER_FORMAT_BOUNDARY_CHECKPOINT',previous_files_verified=len(old),official_host_ZIP_bytes=119665922,
        ZIP_CRC_entries=4,InstallShield_members_zlib_checked=3,MSI_streams=76,CAB_members=len(cab['members']),host_components=26,
        host_component_bytes=173615339,private_wrapper_marker_hits=0,PE_interfaces_reviewed=5,upgrade_DLL_named_exports=23,
        original_x86_fragment_bytes=25,original_x86_fragment_instructions=6,guest_cases=9,VENICE_prefixes_rejected_at_SVU_branch=5,
        GPL_source_RPMs=2,source_specs_configs_patches=23,complete_VENICE_reader_recovered=False,whole_ISP_recovered=False,
        native_Sony_programs_executed=0,device_actions=0,modified_firmware_produced=False,flashable_package_produced=False,goal_complete=False)
    (HERE/'validation-results.json').write_text(json.dumps(validation,indent=2)+'\n')
    (HERE/'continuation-audit.json').write_text(json.dumps(dict(previous_turn='Progress: official V2.01 donor and wrapper counterexample.',
        current_turn='Progress: obtained original host upgrade component, fully static installer/CFB/CAB extraction, identified real reader exports and original SVU signature gate; five VENICE prefixes fail this specific branch. Excludes treating this SVU route as a direct type3 reader.',
        same_impasse_repeated_consecutive_goal_turns=0,goal_status='active',goal_complete=False,
        next_step='Seek an actual BinaryPackProperty/type3/type4 reader or plaintext donor system source; do not infer VENICE support from an SNC decryptor or try its unrelated algorithm blindly.'),indent=2)+'\n')
    delta='\n- [2026-10-29 专业更新组件与 VENICE 格式边界](<work/fx3-color-port-20261027/loader-host-20261029/README.md>)：实际解开官方SNC安装包，取得26组件及升级DLL；25字节原x86头检查9例通过预期，五份VENICE负载在该SVU分支拒绝。未恢复type3／完整ISP或可刷包，无设备动作。\n'.encode()
    with (PROJECT/'README.md').open('a+b') as f:
        fcntl.flock(f.fileno(),fcntl.LOCK_EX);f.seek(0);before=f.read();assert delta not in before
        f.seek(0,os.SEEK_END);f.write(delta);f.flush();os.fsync(f.fileno());f.seek(0);after=f.read();assert after==before+delta
        fcntl.flock(f.fileno(),fcntl.LOCK_UN)
    (HERE/'index-update-receipt.json').write_text(json.dumps(dict(before_bytes=len(before),before_sha256=sha(before),prefix_preserved=True,
        append_bytes=len(delta),append_sha256=sha(delta),after_sha256=sha(after)),indent=2)+'\n')
    files=[]
    for p in sorted(HERE.rglob('*')):
        if not p.is_file() or '__pycache__' in p.parts or p==final:continue
        b=p.read_bytes();files.append(dict(path=str(p.relative_to(HERE)),bytes=len(b),sha256=sha(b)))
    final.write_text(json.dumps(dict(created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),stage=HERE.name,volume_uuid=UUID,
        files=files,validation=validation,other_owner_files_written=False,device_actions=0,full_modified_firmware_emitted=False,
        flashable_package_produced=False,persistent_goal_status='active',goal_complete=False),indent=2)+'\n')
    print(json.dumps(dict(sealed_files=len(files),receipt_sha256=sha(final.read_bytes()),validation=validation)))
if __name__=='__main__':main()
