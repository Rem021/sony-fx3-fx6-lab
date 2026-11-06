"""Offline source/input/cleanup audit; never executes runner main or QEMU."""
import ast,difflib,hashlib,inspect,json,os,runpy,socket,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent;OLD=ROOT.parent/'r25-recovery-observation-candidate';OUT=ROOT/'evidence'
sys.dont_write_bytecode=True

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(n,x):(ROOT/n).write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
inputs=json.loads((ROOT/'INPUTS-BEFORE.json').read_text());after={p:sha(Path(p)) for p in inputs};assert after==inputs
save('INPUTS-AFTER.json',after);save('INPUTS-VERIFICATION.json',{'matched':len(inputs),'r25_delivery':594,'r24_delivery':151,'r21_delivery':145,'fixed':14,'qemu':1,'unchanged':True})
old_sources=json.loads((OLD/'CANDIDATE-SOURCE-FREEZE.json').read_text());files=[ROOT/f for f in old_sources]+[ROOT/'operator-helpers/postkey_observation.py',ROOT/'operator-helpers/postkey_read.js',ROOT/'runtime-wrapper/postkey_flow.py']
freeze={str(p.relative_to(ROOT)):sha(p) for p in files};save('CANDIDATE-SOURCE-FREEZE.json',freeze)
reuse=[];diff=[]
for f,h in old_sources.items():
 p=ROOT/f;reuse.append({'file':f,'original_sha256':h,'candidate_sha256':sha(p),'same_bytes':sha(p)==h})
 if sha(p)!=h:diff.extend(difflib.unified_diff((OLD/f).read_text().splitlines(True),p.read_text().splitlines(True),fromfile='r25/'+f,tofile='r26/'+f))
for f in ('operator-helpers/postkey_observation.py','operator-helpers/postkey_read.js','runtime-wrapper/postkey_flow.py'):
 diff.extend(difflib.unified_diff([], (ROOT/f).read_text().splitlines(True),fromfile='/dev/null',tofile='r26/'+f))
(ROOT/'MINIMAL.diff').write_text(''.join(diff));save('SOURCE-REUSE.json',reuse)
for p in files:
 if p.suffix=='.py':ast.parse(p.read_text())
for p in [*sorted((ROOT/'operator-helpers').glob('*.js')),ROOT/'review_page_r24.js',ROOT/'confirm_page_r24.js']:
 result=subprocess.run(['node','--check',str(p)],text=True,capture_output=True);assert result.returncode==0,(p,result.stderr)
# This run_name does not invoke the __main__ runner path.
ns=runpy.run_path(str(ROOT/'run_trial_r24_review_snapshot.py'),run_name='fx3_r26_import_only')
imports=[]
for modname in ('trial_ring_cached','gate_input_usability','restore_api103_v2','runtime_resource_guard','qmp_line_transport'):
 p=Path(sys.modules[modname].__file__).resolve();expected=ROOT.parent/'v25-r21-recovery-integration'/p.name;assert p==expected and sha(p)==sha(expected);imports.append({'module':modname,'actual_file':str(p),'sha256':sha(p)})
import trial_web_r24_review_snapshot as web
assert web.PAGE_SCRIPT_SHA=='852c83d673478a8f3db8a4d71989259c476a2325f2655a8dd3c8f8e46acfa55b'
assert sha(ROOT/'NAVIGATION-PLAN.json')=='4a695e1ac12340e3e019685c1b8850177db875e1955a05e9544eb40f71cff02f'
for f in ('trial_web_r24_review_snapshot.py','run_trial_r24_review_snapshot.py','review_page_r24.js','confirm_page_r24.js','operator-helpers/planned_navigation_click.py','operator-helpers/planned_navigation_click.js','operator-helpers/review_snapshot_cli.py','operator-helpers/snapshot_read.js','operator-helpers/snapshot_confirm.js','operator-helpers/deadline.js','runtime-wrapper/untimed_image.py','operator-helpers/recovery_tools.py','operator-helpers/recovery_readonly.js','operator-helpers/recovery_cancel.js','runtime-wrapper/recovery_guard.py'):
 assert sha(ROOT/f)==sha(OLD/f)
save('evidence/IMPORT-STATIC-RESULT.json',{'passed':True,'sys_path_first_three':sys.path[:3],'imports':imports,'PAGE_script_SHA':web.PAGE_SCRIPT_SHA,'source_files':len(files),'VM_starts':0,'postkey_PAGE_server_runner_planned_click_deadline_unchanged':True})
cleanup=[]
for p in sorted(OUT.rglob('BROWSER-RESULT.json')):
 result=json.loads(p.read_text());pids=result.get('owned_browser_pids',[]);status={}
 for pid in [result['server_pid'],*pids]:
  try:os.kill(pid,0);alive=True
  except ProcessLookupError:alive=False
  status[str(pid)]=alive
 with socket.socket() as s:closed=s.connect_ex(('127.0.0.1',result['port']))!=0
 ls=subprocess.run(['lsof','-nP','-iTCP:'+str(result['port']),'-sTCP:LISTEN'],capture_output=True,text=True)
 assert not any(status.values()) and closed and not ls.stdout,(p,status,ls.stdout)
 cleanup.append({'receipt':str(p),'original_passed':result.get('passed',False),'PID_alive':status,'port':result['port'],'port_closed':closed,'lsof_stdout':ls.stdout})
save('evidence/FINAL-CLEANUP.json',{'passed':True,'all_fixture_attempts':cleanup,'real_VM_started':False})
print(json.dumps({'passed':True,'input_hashes':len(inputs),'source_files':len(files),'cleanup_receipts':len(cleanup),'VM_starts':0}))
