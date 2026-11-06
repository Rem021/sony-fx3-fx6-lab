#!/usr/bin/env python3
"""Verify preserved checkpoints and seal this new donor stage, no device work."""
from pathlib import Path
import ast,datetime,hashlib,json,plistlib,shutil,subprocess,sys

HERE=Path(__file__).resolve().parent
PROJECT=HERE.parents[2]

def digest(p):
    with p.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()

def main():
    assert not (HERE/'final-receipt.json').exists(),'stage already sealed'
    volume=plistlib.loads(subprocess.check_output(['diskutil','info','-plist','/Volumes/KAFU2T']))
    assert volume['VolumeUUID']=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
    preserved=[]
    for name in ['', 'route-20261028','consumer-20261028','resource-20261028','binding-20261028','package-20261028','tail-20261028','input-20261028']:
        p=HERE.parent/name;receipt=p/'final-receipt.json';r=json.loads(receipt.read_text())
        for f in r['files']:
            q=p/f['path'];assert q.stat().st_size==f['bytes'] and digest(q)==f['sha256'],str(q)
        preserved.append(dict(checkpoint=name or 'base',files=len(r['files']),receipt_sha256=digest(receipt)))
    assert sum(r['files'] for r in preserved)==2213
    executions=[]
    for name in ['art_matrix_guest.py','art_dispatch_guest.py','compare_matrix_serialization.py']:
        r=subprocess.run([sys.executable,str(HERE/name)],cwd=PROJECT,capture_output=True,text=True)
        row=dict(script=name,script_sha256=digest(HERE/name),exit=r.returncode,stdout=r.stdout,stderr=r.stderr)
        executions.append(row);assert r.returncode==0,row
    for p in HERE.glob('*.py'):ast.parse(p.read_text(),filename=str(p))
    matrix=json.loads((HERE/'art-matrix-guest-results.json').read_text());assert len(matrix['matrix_cases'])==138 and len(matrix['register_cases'])==10
    dispatch=json.loads((HERE/'art-dispatch-guest-results.json').read_text());assert len(dispatch['cases'])==72
    serial=json.loads((HERE/'matrix-serialization-comparison.json').read_text());assert serial['all_nine_existing_coefficient_words_match'] and len(serial['cases'])==3
    footer=json.loads((HERE/'donor-footer-results.json').read_text());assert len(footer['files'])==3 and all(f['formula_matches'] for f in footer['files'])
    scan=json.loads((HERE/'loader-marker-scan-results.json').read_text());assert scan['files']==83 and scan['hits']==[]
    donor=Path('/Volumes/KAFU2T/AI/Codex/Worktrees/phayen-venice-firmware')
    donor_state=dict(head=subprocess.check_output(['git','-C',str(donor),'rev-parse','HEAD'],text=True).strip(),
                     branch=subprocess.check_output(['git','-C',str(donor),'branch','--show-current'],text=True).strip(),
                     status=subprocess.check_output(['git','-C',str(donor),'status','--porcelain'],text=True).splitlines())
    assert donor_state['head']=='28f74ffe76ee845ec7b51cf4ae5229a56688a4bd'
    assert donor_state['branch']=='codex/venice-color-fidelity'
    assert donor_state['status']==['?? work/venice-component-contract-2026-10-27/']
    validation=dict(common_guest_change_reverification=executions,
                    existing_result_checks=dict(static_functions=len(json.loads((HERE/'venice-register-static-results.json').read_text())['functions']),quantizer_cases=138,register_label_cases=10,dispatch_cases=72,serialization_cases=3,matching_fx3_words=9,footer_versions=3,loader_scan_files=83),
                    source_worktree_after=donor_state)
    (HERE/'validation-results.json').write_text(json.dumps(validation,indent=2)+'\n')
    now=datetime.datetime.now(datetime.timezone.utc).isoformat()
    (HERE/'restart-audit-20261029.json').write_text(json.dumps(dict(created_utc=now,previous_stage_sealed_files=509,previous_total_files=2213,donor_stage_was_unsealed=True,
            pending_user_questions=[],relevant_old_jobs_at_start=[],previous_terminal_handle='91103 unavailable after restart; completed string values re-read with fixed parser',classification='progress',
            new_progress=['Original VENICE matrix quantizer and descriptor dispatch recovered','Nine coefficient words match original FX3 AV table','Three type4 inner footer length relations recovered'],
            goal_status='active',goal_complete=False),indent=2)+'\n')
    index=PROJECT/'README.md';before=index.read_bytes()
    entry='\n### VENICE 原 ART 参数与 FX3 系数兼容性（2026-10-29）\n\n- [原矩阵量化、分派与 type4 尾部研究](work/fx3-color-port-20261027/donor-20261028/README.md)：138 组矩阵、72 组分派和三组字节序检查通过，既有 FX3 VENICE 矩阵的九个系数字节匹配；三版内层新增统一尾长关系，尚未解密或完成完整色彩链／可刷入包。旧 2213 项封存核验不变，无设备操作，目标 active。\n'
    assert 'donor-20261028/README.md' not in before.decode()
    with index.open('ab') as stream:stream.write(entry.encode())
    after=index.read_bytes();assert after.startswith(before)
    files=[]
    for p in sorted(HERE.rglob('*')):
        if not p.is_file() or '__pycache__' in p.parts or p.name=='final-receipt.json':continue
        files.append(dict(path=str(p.relative_to(HERE)),bytes=p.stat().st_size,sha256=digest(p)))
    receipt=dict(created_utc=now,volume_uuid=volume['VolumeUUID'],volume_free_bytes=shutil.disk_usage('/Volumes/KAFU2T').free,
        previous_sealed_material=preserved,validation=validation,project_index_before_bytes=len(before),project_index_before_sha256=hashlib.sha256(before).hexdigest(),project_index_prefix_unchanged=True,
        native_vendor_library_loads=0,sony_updater_programs_executed=0,guest_execution='Bounded original ARM64 functions in synthetic Unicorn RAM with listed shims',
        camera_usb_phone_actions=0,full_modified_firmware_emitted=False,flashable_package_produced=False,persistent_goal_status='active',goal_completion_claimed=False,files=files)
    (HERE/'final-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(dict(sealed=len(files),previous_files_unchanged=2213,new_guest_checks='PASS',goal='active',camera_actions=0)))

if __name__=='__main__':main()
