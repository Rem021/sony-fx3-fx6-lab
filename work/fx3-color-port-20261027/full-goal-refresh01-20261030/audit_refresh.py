#!/usr/bin/env python3
"""Scope current public leads against the unchanged full requested outcome."""
import datetime,hashlib,json,re
from pathlib import Path
HERE=Path(__file__).resolve().parent;TASK=HERE.parent;FW=HERE.parents[2]/'work/sony-firmware-20261024'
def sha(b):return hashlib.sha256(b).hexdigest()


def main():
    assert not (HERE/'readiness-refresh.json').exists()
    captures=[]
    for name in ['public-source-capture.json','pinned-readme-capture.json','reloaded-selected-source-capture.json','reloaded-extra-source-capture.json']:
        j=json.loads((HERE/name).read_text())
        for x in j.get('sources',j.get('files',[])):
            if 'path' in x:
                b=(HERE/x['path']).read_bytes();assert len(b)==x['bytes'] and sha(b)==x['sha256'];captures.append(x)
    archive=json.loads((HERE/'reloaded-archive-capture.json').read_text());b=(HERE/archive['path']).read_bytes()
    assert len(b)==archive['bytes'] and sha(b)==archive['sha256']
    heads=json.loads((HERE/'git-head-fallback.json').read_text())['sources']
    prior=json.loads((TASK/'full-goal-blocked-audit-20261029/public-head-check.json').read_text())['sources']
    old={x['repository'].removeprefix('https://github.com/'):x['current_commit'] for x in prior}
    old['masterflai/pmca-re-reloaded']=json.loads((FW/'stage7-entry/compatibility/sources.json').read_text())['refs']['masterflai/pmca-re-reloaded main']
    repo_review=[]
    for x in heads:
        assert x['exit_code']==0
        pin=x['stdout'].split()[0];assert re.fullmatch('[0-9a-f]{40}',pin)
        repo_review.append(dict(repository=x['repository'],prior_commit=old[x['repository']],current_commit=pin,
                                changed=pin!=old[x['repository']],transport='git ls-remote HEAD only'))
    core=(HERE/'references/reloaded-crates_pmca-core_src_firmware.rs.source.txt').read_text()
    app=(HERE/'references/reloaded-crates_pmca-app_src_firmware.rs.source.txt').read_text()
    generator=(HERE/'references/reloaded-crates_pmca-app_src_fdat.rs.source.txt').read_text()
    readme=(HERE/'references/reloaded-README-pinned.source.txt').read_text()
    assert 'data[..8] != DAT_MAGIC' in core and 'UFU dat header' in core and 'if ty == b"FDAT"' in core
    assert 'updater.check_guard(payload)?;' in app and 'updater.write_firmware(payload, None)?;' in app
    arms=re.findall(r'^\s*"(CXD[^"\n]+)"\s*=>',generator,re.M)
    assert arms==['CXD4105','CXD4115','CXD4115_ilc','CXD4120','CXD4132','CXD90014']
    rows=[]
    for line in (HERE/'references/reloaded-models.tsv.source.txt').read_text().splitlines():
        f=line.split('\t')
        if len(f)!=4:continue
        try:int(f[2],16);int(f[3],16)
        except ValueError:continue
        rows.append(f)
    assert len(rows)==121 and not any(x[0] in ['ILME-FX3','ILME-FX3A','ILME-FX5'] for x in rows)
    selected_source_review=dict(commit=archive['commit'],archive_sha256=archive['sha256'],
        README_modern_camera_updater_marked_unsupported='| **Newer Sony cameras** (roughly 2018 onwards) | ✔ | ✖ | ✖ | many models |' in readme,
        README_official_flashing_experimental='Flashing official firmware is ported but has not yet been tried on a camera' in readme,
        core_firmware_entry='read_dat checks UFU magic and locates FDAT; selected entry is not a VENICE type3/type4 decoder',
        app_firmware_entry='Passes original FDAT slice to camera check_guard then write_firmware; no target acceptance receipt produced',
        updater_shell_generator_chip_arms=arms,shipped_model_table_rows=121,exact_FX3_FX3A_FX5_rows=[],
        selected_source_executed=False,signing_key_access_or_derivation=False,
        scope='Selected parser/sender/generator/model-table inspection. Not a claim that all settings/service-mode operations reject modern Sony or that the entire repository cannot change later.')
    (HERE/'reloaded-applicability-review.json').write_text(json.dumps(selected_source_review,indent=2)+'\n')
    old_audit=json.loads((TASK/'full-goal-readiness-20261029/readiness-audit.json').read_text())
    history=[]
    for x in old_audit['selected_prior_evidence']:
        b=Path(x['path']).read_bytes();assert len(b)==x['bytes'] and sha(b)==x['sha256']
        assert sha(Path(x['manifest']).read_bytes())==x['manifest_sha256']
        history.append(dict(path=x['path'],bytes=len(b),sha256=sha(b),scope='Selected member and historical seal digest only, not all old stage files.'))
    packages=[]
    for x in old_audit['original_packages_rehashed']:
        p=Path(x['path']);b=p.read_bytes();assert len(b)==x['bytes'] and sha(b)==x['sha256'];packages.append(x)
    key=old_audit['official_public_verification_key'];b=Path(key['path']).read_bytes();assert len(b)==key['bytes'] and sha(b)==key['sha256']
    latest=FW/'stage225-im-reaper-and-loader-ABI-audit/README.md';report=latest.read_bytes()
    requirements=[]
    for row in old_audit['requirements']:
        requirements.append(dict(row,completion_proved=row['id']=='stop_before_actual_flash',
            refreshed_status_note='Constraint preserved only; not evidence for the functional requirements.' if row['id']=='stop_before_actual_flash' else 'No new completing evidence in this refreshed source scope. Prior partial results retained.'))
    blockers=['No accessible readable complete private FX5/VENICE donor or verified inner decoder in reviewed inputs',
              'No validated classic FX3 7.02 modified-package admission path or concrete requested modified package',
              'Current same-model AP/Backup, full hardware buffers/RAW delivery and independent recovery not supplied by scoped reference/model results']
    result=dict(created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),full_objective_preserved=True,
        requirements=requirements,public_repositories=repo_review,changed_repository_review='reloaded-applicability-review.json',
        selected_history_reverified=history,three_original_packages_rehashed=packages,official_public_key=key,
        native_RSA_tests_rerun=False,prior_signature_results_preserved='Original3 valid; retained-signature12 byte mutations rejected; original7.02 body+IV native verification previously passes. Unchanged input SHA rechecked here.',
        latest_other_owner_report=dict(path=str(latest),bytes=len(report),sha256=sha(report),
            scope='Static im child-reaper/loader ABI plus own ARM64 models; no actual target AP/capture/recovery supplied.'),
        previous_goal_turn_classification='progress: WBI zero-fill dispatch and current default staging exclusion',
        current_goal_turn_classification='no_progress_toward_full_requested_goal',
        same_impasse_consecutive_goal_turns=1,earlier_Oct29_blocked_counter_not_reused=True,
        shared_blocker=blockers,verified_wait=False,all_current_fetch_sessions_confirmed_terminal=True,
        persistent_goal_status='active',goal_complete=False,other_owner_files_written=False,device_actions=0,
        downloaded_source_built_or_executed=False,modified_firmware_produced=False,flashable_package_produced=False)
    (HERE/'readiness-refresh.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(dict(changed_repositories=[x['repository'] for x in repo_review if x['changed']],
        selected_source_files_hash_checked=len(captures),prior_members_checked=len(history),original_packages_checked=len(packages),
        requirements_proved_complete=[x['id'] for x in requirements if x['completion_proved']],
        same_impasse_consecutive_goal_turns=1,goal_status='active',goal_complete=False)))


if __name__=='__main__':main()
