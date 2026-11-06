#!/usr/bin/env python3
"""Check only relevant immutable evidence, record honest no-progress audit, seal."""
import ast,datetime,fcntl,hashlib,json,os,plistlib,subprocess
from pathlib import Path

HERE=Path(__file__).resolve().parent;TASK=HERE.parent;PROJECT=HERE.parents[2]
UUID='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
def sha(b):return hashlib.sha256(b).hexdigest()
def pin(p):
    b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=sha(b))
def main():
    final=HERE/'final-receipt.json';assert not final.exists()
    v=plistlib.loads(subprocess.check_output(['/usr/sbin/diskutil','info','-plist','/Volumes/KAFU2T']))
    assert v['VolumeUUID']==UUID and v['MountPoint']=='/Volumes/KAFU2T'
    prior=TASK/'dgu-mis-consumer-20261029/final-receipt.json'
    assert sha(prior.read_bytes())=='4b00fdb477853d0025a5271f6f205c28d636325bd51cece1f4c69522c855548c'
    previous=json.loads(prior.read_text());assert len(previous['files'])==23
    for r in previous['files']:
        b=(prior.parent/r['path']).read_bytes();assert len(b)==r['bytes'] and sha(b)==r['sha256'],r['path']
    selected=[]
    choices={
        'input-20261028':['native-openssl-verification-results.json','official-key-rsa-verification-results.json','validation-results.json'],
        'donor-venice1-20261029':['validation-results.json'],
        'donor-loader-20261029':['validation-results.json'],
        'loader-host-20261029':['validation-results.json'],
        'body-state-20261029':['README.md'],
        'frame-route-20261029':['README.md'],
    }
    for stage,names in choices.items():
        manifest=TASK/stage/'final-receipt.json';j=json.loads(manifest.read_text())
        for name in names:
            row=next(r for r in j['files'] if r['path']==name)
            file=manifest.parent/name;b=file.read_bytes();assert len(b)==row['bytes'] and sha(b)==row['sha256']
            selected.append(dict(**pin(file),manifest=str(manifest),manifest_sha256=sha(manifest.read_bytes()),verification_scope='Selected member only, not every file of this historical stage.'))
    rsa_path=TASK/'input-20261028/official-key-rsa-verification-results.json';rsa=json.loads(rsa_path.read_text())
    actual_packages=[]
    for r in rsa['packages']:
        p=Path(r['source']);h=hashlib.sha256()
        with p.open('rb') as f:
            while b:=f.read(8*1024*1024):h.update(b)
        assert h.hexdigest()==r['source_sha256']
        assert r['sha256_digest_info_valid'] and r['coverage_matches']==['ciphertext_body_then_iv']
        assert len(r['in_memory_single_byte_mutations'])==4 and not any(x['retained_signature_accepts'] for x in r['in_memory_single_byte_mutations'])
        actual_packages.append(dict(path=str(p),bytes=p.stat().st_size,sha256=h.hexdigest(),preserved_prior_original_signature_result=True))
    public_key=TASK/'input-20261028'/rsa['key_path'];assert sha(public_key.read_bytes())==rsa['pem_sha256']
    status=json.loads((HERE/'public-maintainer-status.json').read_text());assert len(status['sources'])==3
    for r in status['sources']:
        assert 'incomplete_retrieval' not in r
        for item in [r['commit_metadata'],r['readme']]+([r['tree']] if 'tree' in r else [])+r.get('format_entry_sources',[]):
            b=(HERE/item['path']).read_bytes();assert len(b)==item['bytes'] and sha(b)==item['sha256']
    fw=next(r for r in status['sources'] if r['label']=='fwtool')
    entry=next(x for x in fw['format_entry_sources'] if x['repository_path']=='fwtool.py')
    text=(HERE/entry['path']).read_text();module=ast.parse(text)
    fn=next(n for n in module.body if isinstance(n,ast.FunctionDef) and n.name=='unpackCommand')
    selector=ast.get_source_segment(text,fn)
    format_tests=sorted({ast.unparse(n.test) for n in ast.walk(fn) if isinstance(n,ast.If) and isinstance(n.test,ast.Call) and isinstance(n.test.func,ast.Attribute) and n.test.func.attr.startswith('is')})
    assert len(format_tests)==9 and not any(s in selector for s in ['DATA23213','type3','type4','ProductCodeVersion'])
    for rel in ['body-state-20261029/final-receipt.json','frame-route-20261029/final-receipt.json']:
        j=json.loads((TASK/rel).read_text());assert not j['goal_complete'] and not j['firmware_output']
    other=PROJECT/'work/sony-firmware-20261024/stage199-Darwin-vector-map-and-update-entry/README.md'
    assert other.is_file();other_pin=pin(other)
    requirements=[
        dict(id='FX5_full_private_donor',status='missing',proof_required='Complete readable private system/menu payload and dependencies'),
        dict(id='VENICE_complete_ISP_color_chain',status='incomplete',proof_required='Readable private inner plus full realtime ISP/sensor calibration/data-domain mapping'),
        dict(id='RAM_chip_and_DMM_runtime',status='incomplete',proof_required='Normal hardware initialization and actual buffers/capacity/payload linked to allocation'),
        dict(id='CMOS_RAW_and_calibration',status='unproven',proof_required='Reachable original acquisition and actual RAW samples/domain validation'),
        dict(id='professional_menu_and_MAIN_recording',status='incomplete',proof_required='Whole professional UI/control route and target recording output'),
        dict(id='exact_modified_target_firmware',status='missing',proof_required='Concrete classic FX3 target package carrying the requested full change'),
        dict(id='classic_FX3_7_02_modified_package_admission',status='unproven',proof_required='Reproducible acceptance evidence for modified whole package, not original signature/repacking'),
        dict(id='normal_boot_support_and_independent_recovery',status='unproven',proof_required='Target compatibility and independent recovery evidence sufficient for readiness'),
        dict(id='stop_before_actual_flash',status='preserved',proof_required='No target flashing; not a substitute for earlier requirements'),
    ]
    audit=dict(created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),full_objective_preserved=True,
        requirements=requirements,selected_prior_evidence=selected,original_packages_rehashed=actual_packages,
        official_public_verification_key=pin(public_key),public_repo_snapshot='public-maintainer-status.json',
        current_fwtool_selector=dict(commit=fw['commit'],source_sha256=entry['sha256'],function='unpackCommand',format_tests=format_tests,
            dedicated_named_VENICE_branch_obtained=False,full_repository_or_global_absence_proved=False,source_executed=False),
        other_owner_latest_reviewed_report=other_pin,other_owner_files_written=False,
        previous_goal_turn_classification='progress: new MIS framing/dispatch and hardware boundary,23 files reverified',
        current_goal_turn_classification='no_progress_toward_full_requested_goal',
        same_impasse_repeated_consecutive_goal_turns=1,verified_wait=False,public_fetch_job_confirmed_terminal=True,
        shared_blocker='No accessible readable complete private donor ISP and no validated classic FX3 7.02 modified-package admission path in current reviewed materials. Device/capture/recovery execution remains outside this task ownership.',
        external_changes_that_can_unblock=['Readable complete private donor or verified decoder','Applicable target admission/loading evidence','Current same-model boot/recovery evidence from its authorized owner'],
        private_signing_key_requested=False,goal_complete=False,persistent_goal_status='active',
        device_actions=0,native_Sony_programs_executed=0,modified_firmware_produced=False,flashable_package_produced=False)
    (HERE/'readiness-audit.json').write_text(json.dumps(audit,indent=2)+'\n')
    delta='\n- [2026-10-29 FX3完整移植目标准入审计](<work/fx3-color-port-20261027/full-goal-readiness-20261029/README.md>)：三主仓库固定提交／各地区供体复查，三原包SHA与签名证据一致；未新增完整私有ISP或7.02修改整包准入方法。按首次无目标关键进展记录，目标active，未刷写。\n'.encode()
    with (PROJECT/'README.md').open('a+b') as f:
        fcntl.flock(f.fileno(),fcntl.LOCK_EX);f.seek(0);before=f.read();assert delta not in before
        f.seek(0,os.SEEK_END);f.write(delta);f.flush();os.fsync(f.fileno());f.seek(0);after=f.read();assert after==before+delta
        fcntl.flock(f.fileno(),fcntl.LOCK_UN)
    (HERE/'index-update-receipt.json').write_text(json.dumps(dict(prefix_unchanged=True,before_bytes=len(before),before_sha256=sha(before),append_sha256=sha(delta),after_sha256=sha(after)),indent=2)+'\n')
    files=[]
    for p in sorted(HERE.rglob('*')):
        if not p.is_file() or p==final or '__pycache__' in p.parts:continue
        b=p.read_bytes();files.append(dict(path=str(p.relative_to(HERE)),bytes=len(b),sha256=sha(b)))
    final.write_text(json.dumps(dict(created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),stage=HERE.name,
        volume_uuid=UUID,files=files,prior_sealed_files_verified=23,goal_complete=False,persistent_goal_status='active',
        current_turn_classification='no_progress',same_impasse_repeated_consecutive_goal_turns=1,
        device_actions=0,flashable_package_produced=False),indent=2)+'\n')
    print(json.dumps(dict(sealed_files=len(files),receipt_sha256=sha(final.read_bytes()),requirements=len(requirements),
        current_turn_classification='no_progress',same_impasse_repeated_consecutive_goal_turns=1,flashable_package_produced=False)))
if __name__=='__main__':main()
