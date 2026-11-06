#!/usr/bin/env python3
from pathlib import Path
import ast,datetime,hashlib,json,plistlib
import subprocess
from capstone import Cs,CS_ARCH_ARM64,CS_MODE_LITTLE_ENDIAN

HERE=Path(__file__).resolve().parent
PROJECT=HERE.parents[2]

def digest(path):
    with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def main():
    assert not (HERE/'final-receipt.json').exists()
    volume=plistlib.loads(subprocess.check_output(['diskutil','info','-plist','/Volumes/KAFU2T']))
    assert volume['VolumeUUID']=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
    donor=HERE.parent/'donor-20261028';previous=json.loads((donor/'final-receipt.json').read_text())
    for row in previous['files']:
        p=donor/row['path'];assert p.stat().st_size==row['bytes'] and digest(p)==row['sha256']
    static=json.loads((HERE/'input-path-static-results.json').read_text());graph=json.loads((HERE/'input-dependency-and-vtable-results.json').read_text())
    assert len(static['files'])==4 and len(graph['files'])==70
    review=[]
    for source in static['files']:
        path=Path(source['path']);assert path.stat().st_size==source['bytes'] and digest(path)==source['sha256']
        assert source['identical_to_204']
        raw=path.read_bytes()
        for f in source['functions']:
            code=raw[f['file_offset']:f['file_offset']+f['bytes']];assert hashlib.sha256(code).hexdigest()==f['sha256']
            if 'SignatureVerification::VerifySignature(' not in f['label']:continue
            calls=[c['label'].split('(')[0] for c in f['calls']]
            assert 'SHA256' in calls and 'RSA_verify' in calls and calls.index('SHA256')<calls.index('RSA_verify')
            va=int(f['va'],0);ins={i.address-va:(i.mnemonic,i.op_str) for i in Cs(CS_ARCH_ARM64,CS_MODE_LITTLE_ENDIAN).disasm(code,va)}
            assert ins[0x118]==('mov','w2, #0x20') and ins[0x11c]==('mov','w0, #0x2a0')
            review.append(dict(library=path.name,verifier=f['va'],digest='SHA256',rsa_digest_id='0x2a0',digest_bytes=32,code_sha256=f['sha256']))
    assert len(review)==2 and all(s['constructor_vptr_proven'] for s in graph['preverification_slots'])
    for p in HERE.glob('*.py'):ast.parse(p.read_text(),filename=str(p))
    now=datetime.datetime.now(datetime.timezone.utc).isoformat()
    (HERE/'verification-contract-review.json').write_text(json.dumps(dict(created_utc=now,verifiers=review,preverification_vtables=graph['preverification_slots'],
        historical_source=True,current_702_device_readback=False,sony_code_executed=False,scope='Source hashes, original function slices, static SHA/RSA ordering and argument constants checked; no updater execution or admission trial.'),indent=2)+'\n')
    index=PROJECT/'README.md';before=index.read_bytes()
    assert 'transport-20261029/README.md' not in before.decode()
    entry='\n### FX3 历史 USB／文件输入验签（2026-10-29）\n\n- [原 UFP／UUD 调用与依赖图](work/fx3-color-port-20261027/transport-20261029/README.md)：核对两版一致的四份原库，USB／UUD 写入处理也调用 SHA-256／RSA 尾签名验证，构造与等待虚槽已定位；CRC 文件 API 未证明可从所查入口到达。历史程序不是当前 7.02 机身读回，无设备动作或可刷入包，目标 active。\n'
    with index.open('ab') as stream:stream.write(entry.encode())
    assert index.read_bytes().startswith(before)
    rows=[]
    for p in sorted(HERE.rglob('*')):
        if not p.is_file() or '__pycache__' in p.parts or p.name=='final-receipt.json':continue
        rows.append(dict(path=str(p.relative_to(HERE)),bytes=p.stat().st_size,sha256=digest(p)))
    receipt=dict(created_utc=now,volume_uuid=volume['VolumeUUID'],previous_donor_sealed_files_verified=len(previous['files']),previous_donor_receipt_sha256=digest(donor/'final-receipt.json'),
        previous_2213_older_files='Verified during preceding donor seal; not rerun here; no writes to those checkpoints.',
        source_libraries=4,unique_static_function_slices=sum(len({f['va'] for f in r['functions']}) for r in static['files']),dynamic_symbol_function_records=sum(len(r['functions']) for r in static['files']),engine_elf_dependency_inventory=70,
        verifier_contracts_checked=review,project_index_before_bytes=len(before),project_index_before_sha256=hashlib.sha256(before).hexdigest(),project_index_prefix_unchanged=True,
        camera_usb_phone_actions=0,sony_programs_executed=False,new_guest_execution=False,full_modified_firmware_emitted=False,flashable_package_produced=False,persistent_goal_status='active',goal_completion_claimed=False,files=rows)
    (HERE/'final-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps({'sealed':len(rows),'donor_files_unchanged':len(previous['files']),'unique_functions':receipt['unique_static_function_slices'],'verifiers':len(review),'goal':'active','camera_actions':0}))

if __name__=='__main__':main()
