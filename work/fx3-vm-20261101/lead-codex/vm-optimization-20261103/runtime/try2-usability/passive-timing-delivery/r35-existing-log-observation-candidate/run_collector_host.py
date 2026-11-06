#!/usr/bin/env python3
from pathlib import Path
import subprocess,json
O=Path(__file__).resolve().parent
args=['/usr/bin/clang','-O2','-pthread','-I'+str(O/'src'),str(O/'tests/collector_log_test.c'),'-o',str(O/'build/host-collector-log')];c=subprocess.run(args,capture_output=True);(O/'receipts/collector-compile.stderr').write_bytes(c.stderr);assert c.returncode==0,c.stderr.decode();r=subprocess.run([args[-1]],capture_output=True)
for k,b in [('stdout',r.stdout),('stderr',r.stderr)]:(O/'receipts'/('collector-log.'+k)).write_bytes(b)
(O/'HOST-COLLECTOR.json').write_text(json.dumps({'argv':args,'compile_exit':c.returncode,'run_exit':r.returncode,'actual_host_fork_and_threads':True,'foreign_shared_BSS_case':'host TGID injection model; not guest raw clone/vfork execution'},indent=2)+'\n');assert r.returncode==0,r.stderr.decode();print(r.stderr.decode())
