#!/usr/bin/env python3
"""Reproduce bounded offline checks. Never execute AArch64 ELF or a runner."""
from pathlib import Path
import json,subprocess,sys,hashlib,plistlib
O=Path(__file__).resolve().parent;ROOT=next(p for p in O.parents if p.name=='Mac');py=ROOT/'work/sony-firmware-20261024/stage4-windows-collab/mac-verification/.venv/bin/python'
assert plistlib.loads(subprocess.check_output(['diskutil','info','-plist','/Volumes/KAFU2T']))['VolumeUUID']=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
steps=[('prepare',sys.executable,'prepare_sources.py'),('actual-binding',sys.executable,'bind_inputs.py'),('baseline-recompile',sys.executable,'rebuild_baselines.py'),('cross-compile',sys.executable,'build_candidate.py'),('source-control-flow',sys.executable,'check_control_flow.py'),('assembly-audit',str(py),'audit_assembly.py'),('host-wrapper',sys.executable,'run_host.py'),('host-collector',sys.executable,'run_collector_host.py'),('parser-tests',sys.executable,'tests/test_parser.py'),('host-UI-cost',sys.executable,'run_ui_host.py'),('parser-compatibility-CLI',sys.executable,'check_parser_compatibility.py'),('host-wrapper-cost',sys.executable,'run_cost_host.py'),('instance-contract',sys.executable,'test_instance_contract.py')]
results=[]
for tag,exe,script in steps:
 args=[exe,'-B',str(O/script)];p=subprocess.run(args,capture_output=True,cwd=ROOT)
 out='receipts/offline-'+tag+'.stdout';err='receipts/offline-'+tag+'.stderr';(O/out).write_bytes(p.stdout);(O/err).write_bytes(p.stderr);results.append({'step':tag,'argv':args,'source_sha256':hashlib.sha256((O/script).read_bytes()).hexdigest(),'exit':p.returncode,'stdout':out,'stderr':err})
 (O/'OFFLINE-RECEIPT.json').write_text(json.dumps({'scope':'Offline host fixtures/static cross compilation; no VM/runner/browser/service/QMP','steps':results},indent=2)+'\n')
 if p.returncode:print('FAILED',tag,'read',err,flush=True);sys.exit(p.returncode)
 print('PASS',tag,flush=True)
print('offline candidate checks complete; runtime not executed',flush=True)
