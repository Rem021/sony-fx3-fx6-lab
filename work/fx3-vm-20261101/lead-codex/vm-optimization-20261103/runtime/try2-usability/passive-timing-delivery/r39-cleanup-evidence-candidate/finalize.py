"""Seal only this r39 delivery; no source changes, external writes or runtime execution."""
from pathlib import Path
import fcntl,hashlib,json,os,platform,subprocess,sys,time
O=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for name in ('SOURCE-FREEZE.json','CORE-SOURCE-FREEZE.json'):
 for n,h in json.loads((O/name).read_text()).items():assert sha(O/n)==h,(name,n)
v=json.loads((O/'OFFLINE-CHECKS.json').read_text());assert v['passed'] and len(v['checks'])==10
for row in v['checks']:assert row['exit']==0 and sha(Path(row['argv'][-1]))==row['script_sha256']
assert len(json.loads((O/'CLEANUP-TESTS.json').read_text())['cases'])==40
inputs=json.loads((O/'INPUTS-AFTER.json').read_text());assert inputs['counts']=={'checked':1398,'matched':1398} and not inputs['mismatches']
# All controlled host children were synchronously waited by the test scripts.
# Report only matching executable/script rows, not other agents' commands/data.
matches=[]
for line in subprocess.check_output(['ps','-axo','pid=,args='],text=True).splitlines():
 words=line.strip().split(None,2)
 if len(words)<3:continue
 pid=int(words[0]);exe=Path(words[1]).name
 if exe.lower().startswith(('python','node')):
  args=words[2].split();scripts=[a for a in args if a.startswith(str(O)+'/') and Path(a).suffix in ('.py','.mjs')]
  if scripts and pid!=os.getpid():matches.append({'pid':pid,'scripts':scripts})
assert not matches,matches
scope={'scope':'host offline only','python':sys.version,'owned_script_processes_remaining':matches,'all_test_children_waited':True,'real_APFS_files_and_cleanup_flock':True,'browser_native_PID_port_QMP_responses':'mock; no QMP invocation','actual_external_reads':['diskutil volume info','ps own script check','frozen input hashes'],'VM_Start_browser_service_QMP_guest_device_deploy_executed':False,'new_source_only_under':str(O),'shared_ledger_README_changed':False,'original_CPIO_DTB_copied_or_changed':False,'cleanup_status_not_menu_success':True,'scope_wall_ns':time.time_ns()}
(O/'EXECUTION-SCOPE.json').write_text(json.dumps(scope,indent=2)+'\n')
syms=[{'path':str(p.relative_to(O)),'target':os.readlink(p)} for p in sorted(O.rglob('*')) if p.is_symlink()]
(O/'SYMLINKS.json').write_text(json.dumps({'scope':'negative-test fixture symlinks only; not runtime sources','links':syms},indent=2)+'\n')
analysis={str(p.relative_to(O)):sha(p) for p in [O/'freeze.py',O/'implement.py',O/'run_offline_checks.py',O/'verify_inputs.py',O/'finalize.py',*sorted((O/'tests').glob('*'))] if p.is_file()}
(O/'ANALYSIS-SOURCE-FREEZE.json').write_text(json.dumps(analysis,indent=2)+'\n')
(O/'VERDICT.json').write_text(json.dumps({'offline_host_candidate':'passed','cleanup_cases':40,'actual_boundary_rejections':6,'node_failure_cases':5,'source_items':43,'core_items':38,'observed_input_pins':192,'inherited_r37_historical_pins':1206,'current_input_recheck_matched':1398,'r38_outcome':'failed: 1 accepted/0 pin/0 confirm','VM':False,'deployment':False,'menu_latency_fixed':False,'zero_frame_cause_fixed':False,'FX6_boot_improved':False},indent=2)+'\n')
files=[p for p in sorted(O.rglob('*')) if p.is_file() and not p.is_symlink() and p!=O/'SHA256SUMS']
(O/'SHA256SUMS').write_text(''.join(sha(p)+'  '+str(p.relative_to(O))+'\n' for p in files))
print(json.dumps({'files':len(files),'bytes':sum(p.stat().st_size for p in files),'SOURCE_SHA256':sha(O/'SOURCE-FREEZE.json'),'CORE_SHA256':sha(O/'CORE-SOURCE-FREEZE.json'),'REPORT_SHA256':sha(O/'REPORT.md'),'SHA256SUMS_SHA256':sha(O/'SHA256SUMS'),'symlinks_separately_listed':len(syms)}))
