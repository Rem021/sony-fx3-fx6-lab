#!/usr/bin/env python3
"""Run only this round's experiments, verify previous receipts, append project index."""
from pathlib import Path
from hashlib import sha256
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timezone
import json,subprocess,sys,plistlib

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
VOLUME_UUID='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
SCRIPTS=['resource_binding_guest.py','caller_binding_guest.py','context_binding_guest.py',
         'owner_boundaries_guest.py','static_inventory.py']


def digest(b):return sha256(b).hexdigest()


def main():
    assert not (HERE/'final-receipt.json').exists(),'Already sealed; do not silently overwrite a final receipt.'
    volume=plistlib.loads(subprocess.check_output(['diskutil','info','-plist','/Volumes/KAFU2T']))
    assert volume['VolumeUUID']==VOLUME_UUID
    old=[]
    for directory in [HERE.parent,HERE.parent/'route-20261028',HERE.parent/'consumer-20261028',HERE.parent/'resource-20261028']:
        p=directory/'final-receipt.json';raw=p.read_bytes();receipt=json.loads(raw)
        for row in receipt['files']:
            data=(directory/row['path']).read_bytes()
            assert len(data)==row['bytes'] and digest(data)==row['sha256'],str(directory/row['path'])
        old.append(dict(receipt=str(p.relative_to(ROOT)),files_verified=len(receipt['files']),
                        unchanged=True,receipt_sha256=digest(raw)))
    logdir=HERE/'validation-logs';logdir.mkdir(exist_ok=True)
    def run(script):
        p=subprocess.run([sys.executable,str(HERE/script)],cwd=ROOT,capture_output=True)
        (logdir/(script+'.stdout.txt')).write_bytes(p.stdout)
        (logdir/(script+'.stderr.txt')).write_bytes(p.stderr)
        return dict(script=script,exit_code=p.returncode,stdout=p.stdout.decode(),stderr=p.stderr.decode(),
                    stdout_sha256=digest(p.stdout),stderr_sha256=digest(p.stderr))
    with ThreadPoolExecutor(max_workers=5) as pool:validation=list(pool.map(run,SCRIPTS))
    (HERE/'validation-results.json').write_text(json.dumps(validation,indent=2)+'\n')
    for v in validation:
        print(v['stdout'].strip())
        assert v['exit_code']==0 and not v['stderr'],v
    from importlib.metadata import version
    environment=dict(python=sys.version,python_executable=sys.executable,unicorn=version('unicorn'),capstone=version('capstone'))
    (HERE/'environment.json').write_text(json.dumps(environment,indent=2)+'\n')
    # Re-verify original binaries. This round only uses CP, never writes any of these files.
    originals=[]
    for relative,pin in [
        ('work/sony-firmware-20261024/stage2/extraction/files/nflasha8/cpapp-b.bin','c90d00d807874a5309dc1b65b203287e83608ceee513cc57b53409333fb6bcba'),
        ('work/sony-firmware-20261024/stage2/extraction/files/nflasha3/av-cam.bin','0cb7e03a59b4ec3d7633664ab0f7a9477892d1aaf442b9db83a7e9a62a49bdaf'),
        ('work/sony-firmware-20261024/stage2/extraction/files/nflasha15/lib/appFw.so','545c5053a74e04ffbf2bbaaf80f558092dd545ed2298b2395ca547dbba58290f')]:
        data=(ROOT/relative).read_bytes();assert digest(data)==pin,relative
        originals.append(dict(path=relative,bytes=len(data),sha256=pin,unchanged=True))
    # Check older sealed files again after imports/execution, before appending the entry.
    for p in old:
        receipt_path=ROOT/p['receipt'];receipt=json.loads(receipt_path.read_bytes())
        assert digest(receipt_path.read_bytes())==p['receipt_sha256']
        for row in receipt['files']:
            data=(receipt_path.parent/row['path']).read_bytes()
            assert len(data)==row['bytes'] and digest(data)==row['sha256']
    index=ROOT/'README.md';before=index.read_bytes()
    entry='\n\n### FX3 原配置生产与 VFX 所有权绑定（2026-10-28）\n\n- [原同步参数、资源申请与同对象色彩提交](work/fx3-color-port-20261027/binding-20261028/README.md)：恢复 acquire ID 的原生产者、默认资源节点与 ImageParam 配置号生成；原分配器替代预填 ID，30 组配置生产接入原色彩命令构造，另验证占用与句柄代次。正常主录／监看参数含义和像素归属仍未确认；没有可刷入包或设备操作。\n'
    assert b'binding-20261028/README.md' not in before
    with index.open('ab') as f:f.write(entry.encode())
    after=index.read_bytes();assert after==before+entry.encode()
    files=[]
    for p in sorted(HERE.rglob('*')):
        if p.is_file() and '__pycache__' not in p.parts and p.name!='final-receipt.json':
            data=p.read_bytes();files.append(dict(path=str(p.relative_to(HERE)),bytes=len(data),sha256=digest(data)))
    result=dict(created_utc=datetime.now(timezone.utc).isoformat(),volume_uuid=VOLUME_UUID,
                validation=[{k:v[k] for k in ['script','exit_code','stdout_sha256','stderr_sha256']} for v in validation],
                original_binaries=originals,previous_sealed_material=old,
                project_index_prefix_unchanged=True,project_index_before_bytes=len(before),
                project_index_before_sha256=digest(before),project_index_after_sha256=digest(after),
                camera_usb_phone_actions=0,full_firmware_modified=False,flashable_package_produced=False,files=files)
    (HERE/'final-receipt.json').write_text(json.dumps(result,indent=2)+'\n')
    # Read back receipt and every sealed output before reporting completion.
    receipt=json.loads((HERE/'final-receipt.json').read_bytes())
    for row in receipt['files']:
        data=(HERE/row['path']).read_bytes();assert len(data)==row['bytes'] and digest(data)==row['sha256']
    print('SEALED',len(files),'new files; verified',sum(r['files_verified'] for r in old),'prior sealed files; original CP/AV/AP unchanged')


if __name__=='__main__':main()
