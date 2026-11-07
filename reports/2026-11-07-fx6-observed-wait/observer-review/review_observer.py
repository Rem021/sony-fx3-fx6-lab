#!/usr/bin/env python3
"""Read a completed observer receipt/logs and summarize task snapshots. No VM I/O."""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import re


def sha(p):
    h = hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda: f.read(4*1024*1024), b''):
            h.update(b)
    return h.hexdigest()


def fingerprint(p):
    return {'path': str(p), 'bytes': p.stat().st_size, 'sha256': sha(p)}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--run', type=Path, required=True)
    ap.add_argument('--runner', type=Path, required=True)
    ap.add_argument('--fixed-runner', type=Path, required=True)
    ap.add_argument('--gate', type=Path, required=True)
    args = ap.parse_args()
    run = args.run.resolve()
    receipt_path = run/'run-receipt.json'
    receipt = json.loads(receipt_path.read_text())
    if not receipt['process_reaped'] or not receipt['locks_released']:
        raise ValueError('run is not completed/released')
    manifest_path = Path(receipt['manifest'])
    manifest = json.loads(manifest_path.read_text())
    watched = [receipt_path, manifest_path, args.runner, args.fixed_runner, args.gate]
    watched += [run/n for n in receipt['files']]
    before = [(p.stat().st_size, p.stat().st_mtime_ns) for p in watched]
    checks = {'manifest_hash_matches': sha(manifest_path) == receipt['manifest_sha256'],
              'runner_hash_matches': sha(args.runner) == receipt['runner_sha256'],
              'fixed_runner_hash_matches': sha(args.fixed_runner) == receipt['fixed_runner_sha256']}
    files = {}
    for n, expected in receipt['files'].items():
        p = run/n
        files[n] = fingerprint(p)
        files[n]['receipt_matches'] = all(files[n][k] == expected[k] for k in ['bytes', 'sha256'])
        if p.suffix == '.bin':
            raw = p.read_bytes()
            files[n]['nonzero_bytes'] = sum(v != 0 for v in raw)
    checks['all_recorded_files_match'] = all(x['receipt_matches'] for x in files.values())
    cpio = Path(manifest['initrd']['path'])
    cpio_fp = fingerprint(cpio)
    checks['cpio_hash_matches'] = cpio_fp['sha256'] == manifest['initrd']['sha256']
    checks['cpio_size_matches'] = cpio_fp['bytes'] == manifest['initrd']['bytes']
    command = json.loads((run/'command.json').read_text())
    checks['command_manifest_hash_matches'] = command['manifest_sha256'] == receipt['manifest_sha256']
    checks['loader_path_matches'] = any('loader,file='+str(cpio)+',' in s for s in command['argv'])

    lines = (run/'serial.log').read_text(errors='replace').splitlines()
    snapshots = []
    for i, line in enumerate(lines):
        m = re.fullmatch(r'FX6_NATIVE_THREAD_BEGIN_(\d+)', line)
        if not m:
            continue
        end_marker = 'FX6_NATIVE_THREAD_END_'+m[1]
        try:
            j = lines.index(end_marker, i+1)
        except ValueError:
            raise ValueError('incomplete task block at '+str(i+1))
        block = lines[i:j+1]
        def value(marker):
            return block[block.index(marker)+1]
        status = {}
        for s in block:
            sm = re.fullmatch(r'(Name|State|Tgid|Pid|PPid|Threads):\s+(.*)', s)
            if sm:
                status[sm[1]] = sm[2]
        tm = re.fullmatch(r'FX6_QUEUE_OBS_TASK pid=(\d+) tid=(\d+)', block[1])
        if not tm or tm[2] != m[1] or status['Pid'] != m[1] or status['Tgid'] != tm[1]:
            raise ValueError('task identity mismatch')
        snapshots.append({'line': i+1, 'end_line': j+1, 'pid': int(tm[1]), 'tid': int(tm[2]),
            'uptime': float(block[2].split()[0]), 'idle_sum': float(block[2].split()[1]),
            'comm': value('FX6_QUEUE_OBS_COMM'), 'status': status, 'wchan': value('FX6_QUEUE_OBS_WCHAN')})
    threads = {}
    for tid in sorted({s['tid'] for s in snapshots}):
        samples = [s for s in snapshots if s['tid'] == tid]
        threads[str(tid)] = {'sample_count': len(samples), 'first': samples[0], 'last': samples[-1],
            'comm_counts': dict(Counter(s['comm'] for s in samples)),
            'state_counts': dict(Counter(s['status']['State'] for s in samples)),
            'wchan_counts': dict(Counter(s['wchan'] for s in samples)),
            'thread_count_counts': dict(Counter(s['status']['Threads'] for s in samples))}
    evidence = [{'line': i+1, 'text': s} for i, s in enumerate(lines)
                if re.match(r'FX6_(APP_CONFIG|PATCH_|QUEUE_OBS_(LIBRARY|GOT|ENTER|EXIT|RESOLVE_FAILED|BIND_FAILED)|'
                            r'GRM_|OSD|BMP_READY|UX_)|appfw-launch: (stub_entry|sleeping)|fix_got_table: base=', s)]
    fault_counts = {needle: sum(needle in s for s in lines) for needle in
                    ['APPFW_SEGV', 'assert at', 'Assertion ', 'Kernel panic', 'Oops:', 'Internal error:',
                     'FX6_QUEUE_OBS_ENTER', 'FX6_QUEUE_OBS_EXIT', 'FX6_QUEUE_OBS_RESOLVE_FAILED', 'FX6_QUEUE_OBS_BIND_FAILED']}
    argv = command['argv']
    gdb_flags = [{'index': i, 'option': v, 'value': argv[i+1] if v == '-gdb' else None}
                 for i, v in enumerate(argv) if v in ('-gdb', '-s')]
    key_files = [p.name for p in run.glob('*key*')]
    last_ux = max((x['line'] for x in evidence if x['text'].startswith('FX6_UX_')), default=None)
    task_lines = set()
    for s in snapshots:
        task_lines.update(range(s['line'], s['end_line']+1))
    after_ux_other = [{'line': i+1, 'text': s} for i, s in enumerate(lines)
                      if last_ux and i+1 > last_ux and i+1 not in task_lines]
    checks['read_inputs_unchanged'] = before == [(p.stat().st_size, p.stat().st_mtime_ns) for p in watched]
    if not all(checks.values()):
        raise ValueError('binding check failed: '+repr(checks))
    print(json.dumps({'schema': 'fx6-completed-observer-review-v1',
        'receipt': fingerprint(receipt_path), 'manifest': fingerprint(manifest_path), 'cpio': cpio_fp,
        'reason': receipt['reason'], 'elapsed_seconds': receipt['elapsed_seconds'],
        'process_reaped': receipt['process_reaped'], 'locks_released': receipt['locks_released'],
        'binding_checks': checks, 'files': files, 'threads': threads, 'snapshots': snapshots,
        'evidence_lines': evidence, 'after_last_ux_non_task_lines': after_ux_other,
        'fault_counts': fault_counts, 'gdb_flags': gdb_flags,
        'key_operations': receipt['key_operations'], 'key_files': key_files,
        'key_error': (run/'keyinject-error.txt').read_text(),
        'supporting_sources': [fingerprint(p) for p in [args.runner, args.fixed_runner, args.gate]],
        'limits': ['Task blocks are samples, not create/exit events.',
                   'Kernel wchan is not a user LR or proof of a specific futex owner.',
                   'GOT install/readback is recorded before app init, not continuously afterward.',
                   'Zero hook entries does not prove the program never receives via other entries/direct calls.',
                   'Key FileNotFoundError lacks a traceback; exact raise site is inferred from matching runner/gate code.'],
        'scope': 'Completed local files only; no socket, VM, process, camera or Git operation'}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
