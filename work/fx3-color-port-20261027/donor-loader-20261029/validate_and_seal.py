#!/usr/bin/env python3
"""Read back pinned evidence, preserve prior stage, append index, seal this checkpoint."""
import datetime,fcntl,hashlib,json,os,plistlib,re,struct,subprocess,xml.etree.ElementTree as ET
from pathlib import Path
HERE=Path(__file__).resolve().parent;TASK=HERE.parent;PROJECT=HERE.parents[2]
UUID='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
def sha(b):return hashlib.sha256(b).hexdigest()
def read(name):return json.loads((HERE/name).read_text())
def main():
    final=HERE/'final-receipt.json';assert not final.exists()
    v=plistlib.loads(subprocess.check_output(['/usr/sbin/diskutil','info','-plist','/Volumes/KAFU2T']))
    assert v['VolumeUUID']==UUID
    previous=TASK/'donor-venice1-20261029/final-receipt.json'
    assert sha(previous.read_bytes())=='12a3e54c8fa67d54dc3b179a594e0051e27e721a6c9a1e7ce55902a62ea649de'
    old=json.loads(previous.read_text())['files']
    for r in old:
        b=(previous.parent/r['path']).read_bytes();assert len(b)==r['bytes'] and sha(b)==r['sha256']
    archive=read('archive-sources.json')
    assert len(archive['captures'])==2
    for r in archive['captures']:
        b=(HERE/(r['name']+'-archived.html')).read_bytes()
        assert r['status']==200 and len(b)==r['bytes'] and sha(b)==r['sha256']
    download=read('early-download.json');page=(HERE/download['source_page']).read_bytes()
    assert sha(page)==download['source_page_sha256']
    assert download['url'] in page.decode('utf-8').replace('\\/','/')
    assert download['complete'] and download['status']==200
    src=HERE/'originals/MPC-3610_V201.zip';b=src.read_bytes()
    assert len(b)==download['bytes']==170041914 and sha(b)==download['sha256']=='c6f5a3ad1a71234af265430b50ef87b29c8c7bba16d5c2e8edd4fb58d47f00d7'
    unpack=read('early-unpack.json')
    assert unpack['ZIP_CRC_all_pass'] and unpack['MD5_same_package_matches'] and len(unpack['zip_members'])==5
    for r in unpack['zip_members']:
        if 'extracted_as' in r:
            b=(HERE/r['extracted_as']).read_bytes();assert len(b)==r['bytes'] and sha(b)==r['sha256']
    fw=(HERE/'originals/MPC-3610_V201_firmware_SSB.bin').read_bytes()
    assert len(fw)==unpack['firmware_bytes']==169625600 and sha(fw)==unpack['firmware_sha256']=='67e63286fa84f9e2b13412237492d222ac027f51b68c102b1c9c4103dcf0c0c5'
    assert hashlib.md5(fw).hexdigest() in unpack['md5_file_text']
    assert len(unpack['tar_members'])==4
    for r in unpack['tar_members']:
        if r['type']!='0':continue
        b=(HERE/'outer-members'/r['path']).read_bytes()
        assert len(b)==r['bytes'] and sha(b)==r['sha256'] and b==fw[r['data_offset']:r['data_offset']+r['bytes']]
    root=ET.fromstring((HERE/'outer-members/VENICE/property.xml').read_bytes());ver=root.find('ProductCodeVersion')
    assert root.findtext('ProductID')=='VENICE' and ver is not None and ver.attrib=={'href':'VER201','enctype':'type3'} and ver.text=='201'
    probe=read('early-payload-structure.json')
    assert probe['original_payload_bytes']==169621368 and probe['original_payload_sha256']=='498d047ca2f6f11d54c502a399e2c5a9f4740e6fae4913eba1aaaf486349c785'
    assert len(probe['compressed_candidates'])==17 and probe['valid_complete_compressed_streams']==0
    assert not any(r['complete_stream'] for r in probe['compressed_candidates'])
    assert all(not x for x in probe['magic_candidates'].values()) and all(not x for x in probe['clear_markers'].values())
    assert len(probe['footer_comparison'])==5
    for r in probe['footer_comparison']:
        p=Path(r['path']);n=p.stat().st_size;assert n==r['bytes']
        with p.open('rb') as f:f.seek(-16,2);tail=f.read(16)
        length=struct.unpack_from('<Q',tail)[0];assert length==r['footer_little_endian_u64'] and tail[8:]==b' '*8
        assert r['rounded_residuals']=={str(q):n-((length+q-1)//q*q) for q in [8,16,32]}
    assert probe['footer_comparison'][0]['rounded_residuals']['8']==304
    assert probe['footer_comparison'][-1]['rounded_residuals']['16']==288
    assert not probe['correction']['universal_round8_rule_supported'] and not probe['correction']['universal_round16_rule_supported']
    scan=read('fx3-whole-filesystem-markers.json')
    assert len(scan['images'])==4 and len(scan['tokens'])==5 and len(scan['encodings'])==3
    assert sum(r['regular_files'] for r in scan['images'])==866 and sum(r['scanned_bytes'] for r in scan['images'])==484121214
    for r in scan['images']:
        assert not r['hits'] and len(r['files'])==r['regular_files']
        assert sum(x['bytes'] for x in r['files'])==r['scanned_bytes']
        assert sha(Path(r['image']).read_bytes())==r['sha256']
    gaps=read('access-gaps.json');issues=read('maintainer-issue-review.json')
    assert not gaps['browser']['page_loaded'] and 'unavailable' in gaps['browser']['result']
    assert 'error' in issues and 'issue_or_PR_records' not in issues
    validation=dict(status='PASS_EARLY_OFFICIAL_DONOR_OUTER_UNPACK_AND_COUNTEREXAMPLE',previous_sealed_files_verified=len(old),
        official_ZIP_bytes=170041914,ZIP_CRC_checked_entries=5,firmware_same_package_MD5_matches=True,outer_tar_members=4,
        inner_XML_type='type3',private_inner_bytes=169621368,private_inner_unpacked=False,bounded_compressed_candidates=17,
        validated_complete_compressed_streams=0,original_footer_payloads_compared=5,old_universal_alignment_hypothesis_disproved=True,
        FX3_regular_files_scanned=866,FX3_scanned_bytes=484121214,exact_markers=5,encodings=3,marker_hits=0,
        native_Sony_programs_executed=0,device_actions=0,modified_firmware_produced=False,flashable_package_produced=False,goal_complete=False)
    (HERE/'validation-results.json').write_text(json.dumps(validation,indent=2)+'\n')
    (HERE/'continuation-audit.json').write_text(json.dumps(dict(previous_turn='Progress: official VENICE V6.30 full donor obtained and outer-unpacked; inner type3 opaque.',
        current_turn='Progress: recovered archived official V2.01 download URL, downloaded from current official server, unpacked originals, found counterexample to proposed universal wrapper relation, expanded fixed FX3 file coverage.',
        same_impasse_repeated_consecutive_goal_turns=0,persistent_goal_status='active',goal_complete=False,
        next_step='Locate an actual type3 reader or plaintext system source; preserve type/version boundaries and full ISP/admission/boot/recovery gates.'),indent=2)+'\n')
    delta='\n- [2026-10-29 VENICE V2.01 旧供体与封装反例](<work/fx3-color-port-20261027/donor-loader-20261029/README.md>)：档案页恢复官方地址，新取170041914B原ZIP并解外层；type3仍未解，V2.01反驳8字节关系通用化。FX3四文件系统866普通文件补查，未产出完整ISP／可刷包，无设备动作。\n'.encode()
    index=PROJECT/'README.md'
    with index.open('a+b') as f:
        fcntl.flock(f.fileno(),fcntl.LOCK_EX);f.seek(0);before=f.read();assert delta not in before
        f.seek(0,os.SEEK_END);f.write(delta);f.flush();os.fsync(f.fileno());f.seek(0);after=f.read()
        assert after==before+delta;fcntl.flock(f.fileno(),fcntl.LOCK_UN)
    (HERE/'index-update-receipt.json').write_text(json.dumps(dict(before_bytes=len(before),before_sha256=sha(before),prefix_unchanged=True,
        append_bytes=len(delta),append_sha256=sha(delta),after_sha256=sha(after)),indent=2)+'\n')
    files=[]
    for p in sorted(HERE.rglob('*')):
        if not p.is_file() or '__pycache__' in p.parts or p==final:continue
        b=p.read_bytes();files.append(dict(path=str(p.relative_to(HERE)),bytes=len(b),sha256=sha(b)))
    final.write_text(json.dumps(dict(created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),stage=HERE.name,
        volume_uuid=UUID,files=files,validation=validation,other_owner_files_written=False,device_actions=0,
        full_modified_firmware_emitted=False,flashable_package_produced=False,persistent_goal_status='active',goal_complete=False),indent=2)+'\n')
    print(json.dumps(dict(sealed_files=len(files),receipt_sha256=sha(final.read_bytes()),validation=validation)))
if __name__=='__main__':main()
