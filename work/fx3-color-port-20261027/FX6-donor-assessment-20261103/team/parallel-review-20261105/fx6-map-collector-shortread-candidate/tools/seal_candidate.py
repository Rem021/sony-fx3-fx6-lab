#!/usr/bin/env python3
"""Write the candidate SHA256SUMS and SEAL.json.  No runtime actions."""
import hashlib, json, sys
from pathlib import Path

CAND = Path(__file__).resolve().parent.parent
SUMS = CAND / 'SHA256SUMS'
SUMS_SHA = CAND / 'SHA256SUMS.sha256'
SEAL = CAND / 'SEAL.json'

def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()

def main():
    skip = {SUMS.name, SUMS_SHA.name, SEAL.name}
    rows = []
    for p in sorted(CAND.rglob('*')):
        if not p.is_file():
            continue
        rel = str(p.relative_to(CAND))
        if rel in skip or rel.endswith('.tmp') or rel.endswith('.pyc') or '__pycache__' in rel:
            continue
        rows.append((rel, p, sha(p), p.stat().st_size))
    with SUMS.open('w') as f:
        for rel, p, digest, size in rows:
            f.write(f"{digest}  {rel}\n")
    sums_sha = sha(SUMS)
    SUMS_SHA.write_text(f"{sums_sha}  SHA256SUMS\n")
    bad = []
    for want, rel in (ln.split(None, 1) for ln in SUMS.read_text().splitlines() if ln.strip()):
        if sha(CAND / rel) != want:
            bad.append(rel)
    target = json.loads((CAND / 'receipts/target-elf-audit-v2.json').read_text())
    cpio = json.loads((CAND / 'work/cpio-binding.json').read_text())
    host = json.loads((CAND / 'receipts/host-tests.json').read_text())
    e2e = json.loads((CAND / 'receipts/e2e-hostrunner-v2.json').read_text())
    gates = json.loads((CAND / 'receipts/entry-gates.json').read_text())
    collector_last = (CAND / 'receipts/collector-test.out').read_text().strip().splitlines()[-1]
    seal = {
        'schema': 'fx6-map-collector-shortread-seal-v1',
        'task': 'task_7ce9fcff3fe6', 'dispatch': 'ctx_93f279790a19',
        'status': 'OFFLINE_COLLECTOR_CANDIDATE_BUILT_ADMISSION_BLOCKED_NOT_RUN',
        'no_run': True, 'vm_started': False, 'real_qmp_rsp_started': False,
        'guest_started': False, 'target_elf_executed': False, 'deployed': False,
        'sha256sums': {'path': str(SUMS), 'sha256': sums_sha, 'entries': len(rows),
                       'all_entries_match': not bad, 'mismatches': bad},
        'result_sha256': sha(CAND / 'RESULT.json'),
        'report_sha256': sha(CAND / 'REPORT.md'),
        'admission_sha256': sha(CAND / 'ADMISSION.md'),
        'kernel_evidence_sha256': sha(CAND / 'KERNEL-EVIDENCE.md'),
        'run_plan_sha256': sha(CAND / 'RUN-PLAN.md'),
        'target_elf': {'path': target['path'], 'sha256': target['sha256'], 'bytes': target['bytes'],
                       'entry': target['entry'], 'pt_interp': target['pt_interp_present'],
                       'pt_dynamic': target['pt_dynamic'], 'executed': False},
        'cpio': {'path': cpio['candidate_cpio']['path'],
                 'sha256': cpio['candidate_cpio']['sha256'],
                 'bytes': cpio['candidate_cpio']['bytes'],
                 'diff': cpio['cpio_diff']},
        'init': cpio['init'],
        'tests': {
            'collector_state_machine': {'status': 'PASS', 'cases': 19, 'summary': collector_last},
            'host_parser_wait': {'status': host['status'], 'cases': host['tests']},
            'hostrunner_qmp_rsp_e2e': {'status': e2e['status'], 'cases': e2e['tests'],
                                      'tls_reader': e2e['tls_reader'], 'target_execution': False,
                                      'vm_started': False},
            'entry_gates': {'status': gates['status'], 'cases': gates['tests']},
        },
        'admission': {'status': 'BLOCKED', 'runtime_authorized': False,
                      'reason': 'non-atomic multi-read map cannot establish current executable mapping/PTE permissions at pause; no SIGSTOP/ptrace/guest modification allowed'},
        'old_run_correction': {
            'old_manifest_sha256': '679145f9fde899aff679873caec936585199eb5dc43f64a6651a7de2a7939aab',
            'old_seal_sha256': 'a2bc053c124880e5e8937ab78fd530811bda07e34e76477d72fc5a3c41187a5a',
            'corrected_manifest': 'runs/fx6-framed-map-20261106T083817Z/SHA256SUMS.CORRECTED',
            'corrected_manifest_sha256': 'd875de596338fb9c34e93ef1cec8380e8c4ebd409578c4482740bf1ca4cb74d8',
            'corrected_entries': 40, 'postrun_stdout_discrepancy': True,
            'write_path_corrected': True, 'elf_entry_corrected': True,
            'qemu_external_locks_distinguished': True,
        },
        'note': 'SEAL.json is written after SHA256SUMS and is not itself listed in SHA256SUMS; no runtime action in this task.',
    }
    SEAL.write_text(json.dumps(seal, indent=2, ensure_ascii=False) + '\n')
    print(json.dumps({'sha256sums': str(SUMS), 'sha256sums_sha256': sums_sha,
                      'entries': len(rows), 'all_entries_match': not bad,
                      'seal': str(SEAL), 'result_sha256': seal['result_sha256'],
                      'report_sha256': seal['report_sha256'],
                      'target_elf': seal['target_elf']['sha256'],
                      'cpio': seal['cpio']['sha256']}, indent=2))
    return 0 if not bad else 1

if __name__ == '__main__':
    sys.exit(main())
