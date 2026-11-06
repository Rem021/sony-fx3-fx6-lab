#!/usr/bin/env python3
"""Verify new official donor evidence and seal without rerunning old stages."""
import datetime,fcntl,hashlib,json,os,plistlib,struct,xml.etree.ElementTree as ET
from pathlib import Path
HERE=Path(__file__).resolve().parent;TASK=HERE.parent;PROJECT=HERE.parents[2]
VOLUME='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
def sha(b):return hashlib.sha256(b).hexdigest()
def main():
    import subprocess
    final=HERE/'final-receipt.json';assert not final.exists()
    v=plistlib.loads(subprocess.check_output(['/usr/sbin/diskutil','info','-plist','/Volumes/KAFU2T']))
    assert v['VolumeUUID']==VOLUME
    old=TASK/'dmm-backup-20261029/final-receipt.json'
    assert sha(old.read_bytes())=='a192a5baf3b1442a7aaee7d46d769a8c44a0eac526b6e06c8f965ec4346c66a0'
    previous=json.loads(old.read_text())['files']
    for r in previous:
        b=(old.parent/r['path']).read_bytes();assert len(b)==r['bytes'] and sha(b)==r['sha256']
    page=json.loads((HERE/'official-source-page.json').read_text())
    assert sha((HERE/'official-source-page.html').read_bytes())==page['sha256']
    download=json.loads((HERE/'download-receipt.json').read_text())
    assert download['url'] in page['embedded_download_URLs']
    b=(HERE/download['output']).read_bytes();assert len(b)==download['bytes'] and sha(b)==download['sha256']
    package=json.loads((HERE/'package-unpack.json').read_text())
    assert len(package['zip_entries'])==5 and all(r['CRC_checked'] for r in package['zip_entries'])
    for r in package['selected_originals'].values():
        b=(HERE/r['path']).read_bytes();assert len(b)==r['bytes'] and sha(b)==r['sha256']
    firmware=(HERE/package['selected_originals']['.bin']['path']).read_bytes()
    assert hashlib.md5(firmware).hexdigest()==package['firmware_md5_expected']
    for r in package['outer_members']:
        if r['type']!='regular':continue
        b=(HERE/r['output']).read_bytes();assert len(b)==r['bytes'] and sha(b)==r['sha256']
        assert b==firmware[r['data_offset']:r['data_offset']+r['bytes']]
    root=ET.fromstring((HERE/'outer-members/VENICE/property.xml').read_bytes());version=root.find('ProductCodeVersion')
    assert root.findtext('ProductID')=='VENICE' and version is not None
    assert version.attrib=={'href':'VER630','enctype':'type3'} and version.text=='630'
    payload=(HERE/'outer-members/VENICE/DATA23213').read_bytes();probe=json.loads((HERE/'payload-structure-results.json').read_text())
    assert sha(payload)==probe['type3_payload_sha256'] and len(payload)==187973304
    assert len(probe['gzip_candidates'])==11 and len(probe['bzip2_candidates'])==19
    assert not any(r['valid_complete_stream'] for r in probe['gzip_candidates']+probe['bzip2_candidates'])
    assert all(not v for k,v in probe['signatures'].items() if k!='zstd')
    zstd=json.loads((HERE/'zstd-candidate-results.json').read_text());assert len(zstd['candidates'])==1
    candidate=zstd['candidates'][0];assert candidate['offset']==probe['signatures']['zstd'][0]
    assert candidate['frame_content_size']==57726 and candidate['first_block_regenerated_bytes']==322747
    assert candidate['first_block_regenerated_bytes']>candidate['block_maximum_size'] and not candidate['valid_frame']
    assert len(payload)-((struct.unpack_from('<Q',payload,len(payload)-16)[0]+7)//8*8)==296
    assert len(probe['cross_generation_footer_relations'])==4 and all(r['residual_after_rounding_to8']==296 for r in probe['cross_generation_footer_relations'])
    oss=json.loads((HERE/'OSS-kernel-review.json').read_text())
    assert sha((HERE/'OSS-source-page.html').read_bytes())==oss['source_page_sha256'] and len(oss['reviews'])==2
    for r in oss['reviews']:
        b=(HERE/r['file']).read_bytes();assert len(b)==r['bytes'] and sha(b)==r['sha256'] and not r['marker_hits']
    platform=json.loads((HERE/'platform-source-review.json').read_text());assert len(platform['sources'])==4
    for r in platform['sources']:
        b=(HERE/r['output']).read_bytes();assert len(b)==r['bytes'] and sha(b)==r['sha256'] and r['relevant_lines']
    validation=dict(status='PASS_NEW_OFFICIAL_VENICE_V630_OUTER_PACKAGE_AND_SCOPED_SOURCE_REVIEW',previous_files_verified=len(previous),
        official_zip_bytes=download['bytes'],ZIP_entries_CRC_checked=5,firmware_same_package_MD5_matches=True,
        outer_tar_members=4,private_inner_XML_type='type3',private_inner_bytes=len(payload),private_inner_unpacked=False,
        invalid_gzip_bzip2_candidates=30,zstd_candidates_structurally_rejected=1,footer_relation_versions=4,official_kernel_archives=2,
        kernel_text_files_scanned=sum(r['text_files_scanned'] for r in oss['reviews']),selected_kernel_sources=4,
        native_Sony_programs_or_vendor_source_builds=0,device_actions=0,full_modified_firmware_emitted=False,
        flashable_package_produced=False,goal_complete=False)
    (HERE/'validation-results.json').write_text(json.dumps(validation,indent=2)+'\n')
    (HERE/'continuation-audit.json').write_text(json.dumps(dict(previous_turn='progress: original BK4/default DMM source candidate',
        current_turn='progress: newly acquired first-generation VENICE official full package, actual outer unpack, type3 distinction, cross-generation framing and kernel-interface limits',
        repeated_impasse=False,persistent_goal_status='active',goal_complete=False,
        next_step='Find a real type3 parser/loader or earlier official donor evidence; maintain full ISP and FX3 admission requirements.'),indent=2)+'\n')
    addition='\n- [2026-10-29 第一代 VENICE V6.30 供体解包](<work/fx3-color-port-20261027/donor-venice1-20261029/README.md>)：新取官方188874442B包并验ZIP／MD5，tar外层完整提取；内层type3仍未解开。两份GPL内核和四个接口仅源码证据，未恢复完整ISP或可刷包，无设备动作。\n'.encode()
    index=PROJECT/'README.md'
    with index.open('a+b') as f:
        fcntl.flock(f.fileno(),fcntl.LOCK_EX);f.seek(0);before=f.read();assert addition not in before
        f.seek(0,os.SEEK_END);f.write(addition);f.flush();os.fsync(f.fileno());f.seek(0);after=f.read()
        assert after==before+addition;fcntl.flock(f.fileno(),fcntl.LOCK_UN)
    (HERE/'index-update-receipt.json').write_text(json.dumps(dict(before_bytes=len(before),before_sha256=sha(before),prefix_unchanged=True,
        appended_bytes=len(addition),append_sha256=sha(addition),after_sha256=sha(after)),indent=2)+'\n')
    files=[]
    for p in sorted(HERE.rglob('*')):
        if not p.is_file() or '__pycache__' in p.parts or p==final:continue
        b=p.read_bytes();files.append(dict(path=str(p.relative_to(HERE)),bytes=len(b),sha256=sha(b)))
    final.write_text(json.dumps(dict(created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),stage=HERE.name,
        volume_uuid=VOLUME,files=files,validation=validation,source_worktree_written=False,device_actions=0,
        full_modified_firmware_emitted=False,flashable_package_produced=False,persistent_goal_status='active',goal_complete=False),indent=2)+'\n')
    print(json.dumps(dict(sealed_files=len(files),receipt_sha256=sha(final.read_bytes()),validation=validation)))
if __name__=='__main__':main()
