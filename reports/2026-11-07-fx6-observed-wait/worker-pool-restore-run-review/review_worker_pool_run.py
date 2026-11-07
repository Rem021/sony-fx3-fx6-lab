#!/usr/bin/env python3
"""Review completed worker-restore hashes/proofs, native threads and snapshots; no VM I/O."""
import argparse
from collections import Counter, defaultdict
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys

sys.dont_write_bytecode = True


def fp(p):
    h = hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda: f.read(4*1024*1024),b''):
            h.update(b)
    return {'path':str(p),'bytes':p.stat().st_size,'sha256':h.hexdigest()}


def fields(s):
    return dict(re.findall(r'(\w+)=([^\s]+)',s))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--run',type=Path,required=True)
    ap.add_argument('--runner',type=Path,required=True)
    args = ap.parse_args()
    run = args.run.resolve()
    rp = run/'run-receipt.json'
    receipt = json.loads(rp.read_text())
    if receipt['process_reaped'] is not True or receipt['locks_released'] is not True:
        raise ValueError('completed receipt required')
    if receipt.get('schema')!='fx6-worker-pool-restore-owned-run-v1' or receipt.get('mode')!='worker-pool-restore':
        raise ValueError('worker-pool-restore receipt required')
    manifest_path = Path(receipt['manifest'])
    before_paths = [rp,manifest_path,args.runner]+[run/n for n in receipt['files']]
    before = [(p.stat().st_size,p.stat().st_mtime_ns) for p in before_paths]
    checks = {'runner_matches_receipt':fp(args.runner)['sha256']==receipt['runner_sha256'],
              'manifest_matches_receipt':fp(manifest_path)['sha256']==receipt['manifest_sha256']}
    if not all(checks.values()):
        raise ValueError('run source binding mismatch')
    spec = importlib.util.spec_from_file_location('v3_verified_runner',args.runner)
    runner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runner)
    # Only check(): hashes/proof chain/argv. Never execute(), acquire() or QEMU.
    manifest,base = runner.check(manifest_path,receipt['manifest_sha256'])
    checks['full_295_observer_snapshot_restore_chain_passed'] = True
    fixed = runner.CP.parent/'fixed_runner.py'
    checks['fixed_runner_matches_receipt'] = fp(fixed)['sha256']==receipt['fixed_runner_sha256']
    for key in ('snapshot_helper','abi_verification'):
        runner.verify_artifact(manifest[key],key)
    checks['helper_and_abi_artifact_hashes_match'] = True
    files = {}
    for n,expected in receipt['files'].items():
        p = run/n
        files[n] = fp(p)
        files[n]['matches_receipt'] = all(files[n][k]==expected[k] for k in ('bytes','sha256'))
        if n.endswith('.bin'):
            files[n]['nonzero_bytes'] = sum(v!=0 for v in p.read_bytes())
    checks['all_recorded_files_match'] = all(v['matches_receipt'] for v in files.values())
    command = json.loads((run/'command.json').read_text())
    checks['command_argv_exact'] = command['argv']==runner.runtime_argv(manifest,run)
    checks['command_manifest_hash_matches'] = command['manifest_sha256']==receipt['manifest_sha256']
    checks['command_model_matches'] = command['model_env']==manifest['model_env']
    checks['command_has_no_duplicate_s'] = '-s' not in command['argv']
    checks['worker_authorization_label'] = command['authorization']=='user requested continuing repair; worker-pool-restore diagnostic derived295'
    checks['command_mode_matches'] = command['mode']==manifest['mode']==receipt['mode']=='worker-pool-restore'
    lines = (run/'serial.log').read_text(errors='replace').splitlines()
    samples = []
    for i,line in enumerate(lines):
        m = re.fullmatch(r'FX6_NATIVE_THREAD_BEGIN_(\d+)',line)
        if not m:
            continue
        j = lines.index('FX6_NATIVE_THREAD_END_'+m[1],i+1)
        b = lines[i:j+1]
        def value(marker):
            return b[b.index(marker)+1]
        status = dict(re.findall(r'^(Name|State|Tgid|Pid|PPid|Threads):\s+(.*)$','\n'.join(b),re.M))
        samples.append({'line':i+1,'end_line':j+1,'tid':int(m[1]),'uptime':float(b[2].split()[0]),
            'comm':value('FX6_QUEUE_OBS_COMM'),'status':status,'wchan':value('FX6_QUEUE_OBS_WCHAN')})
    threads = {}
    for tid in sorted({s['tid'] for s in samples}):
        a = [s for s in samples if s['tid']==tid]
        threads[str(tid)] = {'sample_count':len(a),'first':a[0],'last':a[-1],
            'states':dict(Counter(s['status']['State'] for s in a)),
            'wchan':dict(Counter(s['wchan'] for s in a)),
            'thread_counts':dict(Counter(s['status']['Threads'] for s in a))}
    diag = [{'line':i+1,'text':s,'fields':fields(s)} for i,s in enumerate(lines) if s.startswith('FX6_WAIT_SNAPSHOT_')]
    regs = [v for v in diag if v['text'].startswith('FX6_WAIT_SNAPSHOT_REG ')]
    detaches = [v for v in diag if v['text'].startswith('FX6_WAIT_SNAPSHOT_DETACH ')]
    end = [v for v in diag if v['text'].startswith('FX6_WAIT_SNAPSHOT_END ')]
    init_end = [v for v in diag if v['text'].startswith('FX6_WAIT_SNAPSHOT_INIT_END ')]
    register_tids = {v['fields']['tid'] for v in regs}
    checks['129_unique_register_snapshots'] = len(regs)==len(register_tids)==129
    for event in ('SEIZE','INTERRUPT'):
        events = [v for v in diag if v['text'].startswith('FX6_WAIT_SNAPSHOT_'+event+' ')]
        checks['129_'+event.lower()+'_rc0'] = len(events)==129 and all(v['fields']['rc']=='0' for v in events) and {v['fields']['tid'] for v in events}==register_tids
    checks['129_matching_detaches_rc0'] = len(detaches)==129 and all(v['fields']['rc']=='0' for v in detaches) and {v['fields']['tid'] for v in detaches}==register_tids
    checks['one_successful_snapshot_end'] = len(end)==1 and all(end[0]['fields'].get(k)==str(v) for k,v in {'processed':129,'enumerated':129,'failures':0,'cancelled':0,'overflow':0,'detach_failed':0}.items())
    checks['helper_rc0'] = len(init_end)==1 and init_end[0]['fields'].get('rc')=='0'
    frames = [v for v in diag if v['text'].startswith('FX6_WAIT_SNAPSHOT_FRAME ')]
    key1 = json.loads((run/'keyinject-step1.json').read_text())
    gate = json.loads((run/'ap96-host-input-gate.json').read_text())
    checks['key1_gate_only_readback'] = key1['written_hex']==key1['readback_hex'] and key1['software_gate_only'] is True and gate==[key1]
    checks['key1_unverified_native_screen'] = key1['observed_page']=='native-screen-unverified' and key1['reason']=='bounded diagnostic key sequence; no verified native menu'
    checks['key_scope_and_no_retries'] = [v['step'] for v in receipt['key_attempts']]==[1,2] and [v['step'] for v in receipt['key_operations']]==[1] and receipt['key_attempts'][1]['retry_suppressed'] is True and receipt['key_attempts'][1]['subsequent_steps_suppressed'] is True
    evidence = [{'line':i+1,'text':s} for i,s in enumerate(lines) if re.match(r'FX6_(APP_CONFIG|PATCH_|QUEUE_OBS_(LIBRARY|GOT|ENTER|EXIT)|OSD_FLUSH|UX_)',s)]
    enters = [{'line':i+1,'text':s,'fields':fields(s)} for i,s in enumerate(lines) if s.startswith('FX6_QUEUE_OBS_ENTER ')]
    exits = [{'line':i+1,'text':s,'fields':fields(s)} for i,s in enumerate(lines) if s.startswith('FX6_QUEUE_OBS_EXIT ')]
    exit_by_seq = {x['fields']['seq']:x for x in exits}
    unmatched = [x for x in enters if x['fields']['seq'] not in exit_by_seq]
    checks['nine_enters_eight_exits_unique'] = len(enters)==len({x['fields']['seq'] for x in enters})==9 and len(exits)==len(exit_by_seq)==8
    checks['receive_pairs_tid_match'] = all(x['fields']['tid']==exit_by_seq[x['fields']['seq']]['fields']['tid'] for x in enters if x['fields']['seq'] in exit_by_seq)
    checks['only_unmatched_seq9_bb_request_reply'] = len(unmatched)==1 and all(unmatched[0]['fields'].get(k)==v for k,v in {'seq':'9','tid':'231','caller':'/usr/lib/appFw.so+0x20ef7cc','site':'bb_request_reply','qid':'0x81cf610f','timeout':'-1'}.items())
    faults = {n:sum(n in s for s in lines) for n in ['APPFW_SEGV','assert at','Assertion ','Kernel panic','Oops:','Internal error:','FX6_QUEUE_OBS_ENTER','FX6_QUEUE_OBS_EXIT']}
    checks['read_inputs_unchanged'] = before==[(p.stat().st_size,p.stat().st_mtime_ns) for p in before_paths]
    if not all(checks.values()):
        raise ValueError('review check failed: '+repr(checks))
    print(json.dumps({'schema':'fx6-completed-worker-pool-restore-review-v1','receipt':fp(rp),
        'manifest':fp(manifest_path),'runner':fp(args.runner),'fixed_runner':fp(fixed),
        'reason':receipt['reason'],'elapsed_seconds':receipt['elapsed_seconds'],'qemu_exit':receipt['qemu_exit'],
        'process_reaped':receipt['process_reaped'],'locks_released':receipt['locks_released'],
        'binding_checks':checks,'files':files,'threads':threads,'samples':samples,
        'distinct_sampled_tids':len(threads),'status_thread_counts':dict(Counter(s['status']['Threads'] for s in samples)),
        'comm_groups_by_last_sample':dict(Counter(v['last']['comm'] for v in threads.values())),
        'diagnostic_records':diag,'register_snapshot_count':len(regs),'fp_frame_count':len(frames),
        'raw_pc_lr_saved_lr_address_count':2*len(regs)+len(frames),
        'snapshot_elapsed_ms':int(end[0]['fields']['elapsed_ms']),'key_operations':receipt['key_operations'],
        'receive_entries':enters,'receive_exits':exits,'unmatched_receive_entries':unmatched,
        'key_attempts':receipt['key_attempts'],'key1':key1,'key_error':(run/'keyinject-error.txt').read_text(),
        'fault_counts':faults,'evidence_lines':evidence,
        'limits':['No disassembly/address ownership inference repeated in this review.',
                  'Ptrace sequentially interrupts guest threads; successful detach does not remove scheduling interference.',
                  'Wchan and END markers are samples, not user LR or thread exit events.',
                  'Software key write/readback does not prove guest consumption or native UI response.',
                  'Eight observed returns do not prove an acknowledgement for the ninth receive; message contents were not read.'],
        'scope':'Completed files only; no VM/socket/process/camera operations'},ensure_ascii=False,indent=2))


if __name__=='__main__':
    main()
