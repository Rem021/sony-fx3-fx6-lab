#!/usr/bin/env python3
"""Hash already-selected review sources and quote existing policy lines; no model/VM code."""
import hashlib
import json
from pathlib import Path

PROJECT = Path('/Volumes/KAFU2T/AI/Projects/Mac/outputs/sony-fx3-fx6-lab')
CP = Path('/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/fx6-boot-readiness/early-kernel/cp-helper-agnostic')


def fp(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(4*1024*1024),b''):
            h.update(b)
    return {'path':str(path),'bytes':path.stat().st_size,'sha256':h.hexdigest()}


def main():
    paths = [PROJECT/'reports/2026-11-07-fx6-observed-wait/bb-request-contract/bb-request-contract.md',
        PROJECT/'reports/2026-11-07-fx6-observed-wait/bb-request-contract/bb-request-contract.json',
        PROJECT/'work/fx6-worker-pool-restore-20261107/candidate-manifest.json',
        PROJECT/'work/fx6-worker-pool-restore-20261107/guest-worker-pool-restore295.cpio',
        PROJECT/'work/fx6-worker-pool-restore-20261107/runs/worker-pool-restore-a3af746e3d/run-receipt.json',
        PROJECT/'work/fx6-worker-pool-restore-20261107/runs/worker-pool-restore-a3af746e3d/serial.log',
        CP/'BUILD.json',CP/'fx6-cp-backup-sync100-agnostic-g0.ko',
        CP/'fx6-cp-backup-sync100-agnostic.c',CP/'fx6-cp-backup-sync100-agnostic-module-unit.c',
        CP/'fx3-backup-sync101-v1.h',CP/'fx3-date99-consumer-v1.h']
    rows = [fp(p) for p in paths]
    build = json.loads((CP/'BUILD.json').read_text())
    bypath = {r['path']:r for r in rows}
    checks = {
        'module_matches_recorded_build':bypath[str(CP/'fx6-cp-backup-sync100-agnostic-g0.ko')]['sha256']==build['module']['sha256']=='7e8d859ecb0fc66c5e05909ae5688b966838a6aa7bb0a478b6b4139177004aaa',
        'main_source_matches_recorded_build':bypath[str(CP/'fx6-cp-backup-sync100-agnostic.c')]['sha256']==build['source']['fx6_cp_backup_sync100_agnostic.c'],
        'sync_header_matches_recorded_build':bypath[str(CP/'fx3-backup-sync101-v1.h')]['sha256']==build['source']['fx3-backup-sync101-v1.h'],
        'module_unit_matches_recorded_build':bypath[str(CP/'fx6-cp-backup-sync100-agnostic-module-unit.c')]['sha256']==build['source']['fx6-cp-backup-sync100-agnostic-module-unit.c']}
    excerpts = []
    for p,needles in [(CP/'fx6-cp-backup-sync100-agnostic.c',['static int cp_reset_send_backup100_prior','rc=osal_valloc_msg_wait','osal_set_msg_src(reply','rc=osal_snd_msg','Reply is native queue owned','int freed=osal_free_msg','fail_reply:','static int cp_reset_send99','static const struct']),
                      (CP/'fx3-backup-sync101-v1.h',['static int sync100_route','return cp_reset_send_backup100_prior'])]:
        for i,line in enumerate(p.read_text().splitlines()):
            if any(n in line for n in needles):
                excerpts.append({'path':str(p),'line':i+1,'text':line})
    print(json.dumps({'schema':'adf-negative-model-selected-source-hashes-v1','sources':rows,
        'build_binding_checks':checks,'selected_source_lines':excerpts,
        'actual_cpio_member_observed_in_this_review':{'member':'simulation/fx3-cp-backup-reset-v1.ko','bytes':66552,'sha256':'7e8d859ecb0fc66c5e05909ae5688b966838a6aa7bb0a478b6b4139177004aaa','init_insmod_lines':[128,129,130,131]},
        'limits':['The recorded source/unit/header hashes match BUILD.json; no independent rebuild or full transitive dependency reproduction was performed.',
                  'No runtime 0x9058003f queue/provider absence or child-send failure is proven by these files.',
                  'This collector only reads already-selected files and prints metadata; no reply/model/VM behavior is implemented.']},ensure_ascii=False,indent=2))


if __name__=='__main__':main()
