#!/usr/bin/env python3
"""Seal this checkpoint once, appending the shared index without replacing it."""
import datetime,fcntl,hashlib,json,os,plistlib,subprocess
from pathlib import Path
HERE=Path(__file__).resolve().parent
PROJECT=HERE.parents[2]
EXPECTED_VOLUME='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'

def sha(b):return hashlib.sha256(b).hexdigest()
def main():
    target=HERE/'final-receipt.json';assert not target.exists()
    info=plistlib.loads(subprocess.check_output(['/usr/sbin/diskutil','info','-plist','/Volumes/KAFU2T']))
    assert info['VolumeUUID']==EXPECTED_VOLUME
    assert PROJECT==Path('/Volumes/KAFU2T/AI/Projects/Mac')
    validation=json.loads((HERE/'validation-results.json').read_text())
    assert validation['full_goal_gates_passed']==0 and validation['device_actions']==0
    audit=dict(created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        previous_goal_turn_classification='progress: original DMM message allocation and request fields',
        current_goal_turn_classification='progress: original queue registration and callback binding; static handler and configuration source; fresh official-page/full-goal audit',
        repeated_impasse=False,full_goal_complete=False,persistent_goal_status='active',
        evidence_boundary='No normal-send completion, provider response, real pixels, full donor ISP or modified package admission.',
        next_step='Trace parameter0xfa0182 normal producer and unit-list configuration stream; preserve full donor/signature/boot gates.')
    (HERE/'continuation-audit.json').write_text(json.dumps(audit,indent=2)+'\n')
    line='\n- [2026-10-29 FX3 DMM 接收端与完整目标复核](<work/fx3-color-port-20261027/dmm-service-20261029/README.md>)：原队列注册／独立回调前缀和0x20静态分派已证，4组有界案例；正常提交停在线程身份查询前。官方FX5两入口无更新信息，完整供体／MAIN／整包准入仍缺，无设备动作。\n'
    index=PROJECT/'README.md'
    with index.open('a+b') as file:
        fcntl.flock(file.fileno(),fcntl.LOCK_EX)
        file.seek(0);before=file.read();addition=line.encode();assert addition not in before
        file.seek(0,os.SEEK_END);file.write(addition);file.flush();os.fsync(file.fileno())
        file.seek(0);after=file.read();assert after==before+addition
        index_receipt=dict(index=str(index),before_bytes=len(before),before_sha256=sha(before),
            prefix_unchanged=True,appended_bytes=len(addition),append_sha256=sha(addition),after_sha256=sha(after),
            scope='Immediate readback while holding append lock; no whole-file replacement or concurrent entry deletion.')
        fcntl.flock(file.fileno(),fcntl.LOCK_UN)
    (HERE/'index-update-receipt.json').write_text(json.dumps(index_receipt,indent=2)+'\n')
    files=[]
    for path in sorted(HERE.rglob('*')):
        if not path.is_file() or '__pycache__' in path.parts or path==target:continue
        b=path.read_bytes();files.append(dict(path=str(path.relative_to(HERE)),bytes=len(b),sha256=sha(b)))
    out=dict(created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),volume_uuid=EXPECTED_VOLUME,
        stage=HERE.name,files=files,validation=validation,original_guest_cases=4,
        old_guest_mains_rerun=False,full_modified_firmware_emitted=False,flashable_package_produced=False,
        private_signing_material_read_or_derived=False,device_actions=0,native_Sony_programs_executed=0,
        persistent_goal_status='active',goal_complete=False)
    target.write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps(dict(sealed_files=len(files),receipt_sha256=sha(target.read_bytes()),goal_complete=False)))

if __name__=='__main__':main()
