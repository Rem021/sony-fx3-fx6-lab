#!/usr/bin/env python3
"""Recompute both declaration receipts; read-only except optional stdout."""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

HERE=Path(__file__).resolve().parent


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    checks={}
    for script,artifact in [('preflight.py','preflight-receipt.json'),('build_manifest.py','candidate-manifest.json')]:
        generated=json.loads(subprocess.check_output([sys.executable,str(HERE/script)],cwd=HERE))
        saved=json.loads((HERE/artifact).read_text())
        if generated!=saved:
            raise ValueError(f'{artifact} differs from regenerated source evidence')
        checks[artifact]={'regeneration_equal':True,'sha256':digest(HERE/artifact)}
    p=json.loads((HERE/'preflight-receipt.json').read_text())
    m=json.loads((HERE/'candidate-manifest.json').read_text())
    assert p['status']=='PASS_OFFLINE_PRECHECK_ONLY'
    assert m['kind']=='OFFLINE_MANIFEST_ONLY_NOT_A_BOOTABLE_CANDIDATE'
    assert m['preflight_receipt_sha256']==checks['preflight-receipt.json']['sha256']
    assert p['vm']['member_checks']['usr/kmod/liro.ko']['present']
    assert not p['vm']['member_checks']['system/av-cam.bin']['present']
    assert not p['vm']['member_checks']['usr/kmod/pciedma.ko']['present']
    assert p['runtime_ORIL_AV_loaded_proven'] is False
    assert p['runtime_FX6_kernel_tested'] is False
    assert p['new_VM_or_device_operations']==0
    return {'status':'PASS_REGENERATED_OFFLINE_ONLY','checks':checks,'source_scripts':{x:digest(HERE/x) for x in ('elf64.py','fdt.py','preflight.py','build_manifest.py','verify.py')},'not_a_runtime_test':True}


if __name__=='__main__':
    print(json.dumps(main(),indent=2,ensure_ascii=False))
