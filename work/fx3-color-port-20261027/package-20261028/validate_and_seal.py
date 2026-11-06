#!/usr/bin/env python3
"""Validate only this round, preserve all previous receipts, and seal a research checkpoint."""
from pathlib import Path
from hashlib import sha256,file_digest
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timezone
import sys,subprocess,json,plistlib

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
FW=ROOT/'work/sony-firmware-20261024'


def main():
    assert not (HERE/'final-receipt.json').exists(),'Checkpoint already sealed'
    vol=plistlib.loads(subprocess.check_output(['diskutil','info','-plist','/Volumes/KAFU2T']))
    assert vol['VolumeUUID']=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
    old=[]
    def verify_old():
        result=[]
        for d in [HERE.parent]+[HERE.parent/n for n in ['route-20261028','consumer-20261028','resource-20261028','binding-20261028']]:
            p=d/'final-receipt.json';raw=p.read_bytes();r=json.loads(raw)
            for entry in r['files']:
                data=(d/entry['path']).read_bytes()
                assert len(data)==entry['bytes'] and sha256(data).hexdigest()==entry['sha256'],str(d/entry['path'])
            result.append(dict(receipt=str(p.relative_to(ROOT)),files_verified=len(r['files']),unchanged=True,receipt_sha256=sha256(raw).hexdigest()))
        return result
    old=verify_old();logs=HERE/'validation-logs';logs.mkdir(exist_ok=True)
    def run(script):
        p=subprocess.run([sys.executable,str(HERE/script)],cwd=ROOT,capture_output=True)
        (logs/(script+'.stdout.txt')).write_bytes(p.stdout);(logs/(script+'.stderr.txt')).write_bytes(p.stderr)
        row=dict(script=script,exit_code=p.returncode,stdout_sha256=sha256(p.stdout).hexdigest(),stderr_sha256=sha256(p.stderr).hexdigest())
        print(script,p.returncode,p.stdout.decode().splitlines()[0] if p.stdout else '',flush=True)
        assert p.returncode==0 and not p.stderr,(script,p.stderr.decode())
        return row
    with ThreadPoolExecutor(max_workers=2) as pool:
        validation=list(pool.map(run,['unpack_updater.py','extract_verifier_libraries.py']))
    with ThreadPoolExecutor(max_workers=2) as pool:
        validation+=list(pool.map(run,['cbc_vectors.py','static_sources.py']))
    validation.append(run('original_block_checker_guest.py'))
    (HERE/'validation-results.json').write_text(json.dumps(validation,indent=2)+'\n')
    assert old==verify_old()
    pins={
        'fx3-7.02-BODYDATA.DAT':json.loads((FW/'fx3-7.02-download-receipt.json').read_bytes())['sha256'],
        'stage2/extraction/files/nflasha8/cpapp-b.bin':'c90d00d807874a5309dc1b65b203287e83608ceee513cc57b53409333fb6bcba',
        'stage2/extraction/files/nflasha3/av-cam.bin':'0cb7e03a59b4ec3d7633664ab0f7a9477892d1aaf442b9db83a7e9a62a49bdaf',
        'stage2/extraction/files/nflasha15/lib/appFw.so':'545c5053a74e04ffbf2bbaaf80f558092dd545ed2298b2395ca547dbba58290f'}
    originals=[]
    for name,pin in pins.items():
        p=FW/name
        with p.open('rb') as f:actual=file_digest(f,'sha256').hexdigest()
        assert actual==pin,name
        originals.append(dict(path=str(p.relative_to(ROOT)),bytes=p.stat().st_size,sha256=pin,unchanged=True))
    parser=json.loads((HERE/'parser-source-receipt.json').read_bytes());assert not (ROOT/parser['wheel']).exists()
    index=ROOT/'README.md';before=index.read_bytes()
    assert b'package-20261028/README.md' not in before
    entry='\n\n### FX3 可刷入条件与更新封包研究（2026-10-28）\n\n- [官方更新环境、CBC 重编码及原校验器](work/fx3-color-port-20261027/package-20261028/README.md)：用户指定可刷入时停止，持续目标 active；拆读 65 项更新环境和 11 库，六个孤立块重建原密文，17 组原 AP 校验器实验通过。尾部验证、完整准入及启动仍未恢复，无完整修改包或设备操作。\n'
    with index.open('ab') as f:f.write(entry.encode())
    after=index.read_bytes();assert after==before+entry.encode()
    files=[]
    for p in sorted(HERE.rglob('*')):
        if p.is_file() and '__pycache__' not in p.parts and p.name!='final-receipt.json':
            data=p.read_bytes();files.append(dict(path=str(p.relative_to(HERE)),bytes=len(data),sha256=sha256(data).hexdigest()))
    result=dict(created_utc=datetime.now(timezone.utc).isoformat(),volume_uuid=vol['VolumeUUID'],validation=validation,
                original_binaries=originals,previous_sealed_material=old,parser_download_removed=True,
                project_index_prefix_unchanged=True,project_index_before_bytes=len(before),
                project_index_before_sha256=sha256(before).hexdigest(),project_index_after_sha256=sha256(after).hexdigest(),
                camera_usb_phone_actions=0,full_modified_firmware_emitted=False,flashable_package_produced=False,
                persistent_goal_status='active',goal_completion_claimed=False,files=files)
    (HERE/'final-receipt.json').write_text(json.dumps(result,indent=2)+'\n')
    for row in json.loads((HERE/'final-receipt.json').read_bytes())['files']:
        data=(HERE/row['path']).read_bytes();assert len(data)==row['bytes'] and sha256(data).hexdigest()==row['sha256']
    print('SEALED',len(files),'new files; prior verified',sum(x['files_verified'] for x in old),'goal remains active',flush=True)


if __name__=='__main__':main()
