#!/usr/bin/env python3
"""One task freeze, no runtime operation or historical broad manifest scan."""
from pathlib import Path
import datetime,hashlib,json,plistlib,subprocess
P=Path(__file__).resolve().parent;R=P.parent/'r42-command-timing-runner'
def sha(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def js(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def main():
 assert plistlib.loads(subprocess.check_output(['diskutil','info','-plist','/Volumes/KAFU2T']))['VolumeUUID']=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
 observed=sorted(P.glob('INPUTS-*.json'))+sorted(R.glob('INPUTS-*.json'))
 observed=[p for p in observed if p.name!='INPUTS-AFTER.json']
 rows={}
 for p in observed:
  value=json.loads(p.read_text())
  for n,x in value['files'].items():
   if n in rows:assert rows[n]['sha256']==x['sha256'],('conflicting task observations',n)
   rows.setdefault(n,{**x,'observation_receipts':[]})['observation_receipts'].append(str(p))
 for n,x in rows.items():assert sha(Path(n))==x['sha256'] and Path(n).stat().st_size==x['bytes'],('technical input drift',n)
 external=sum(not any(Path(n).is_relative_to(root) for root in (P,R)) for n in rows)
 after=dict(schema='r42-used-inputs-recheck-v1',time=datetime.datetime.now(datetime.timezone.utc).isoformat(),passed=True,unique_pin_count=len(rows),external_original_pin_count=external,internal_current_artifact_pin_count=len(rows)-external,basis='only actually used inputs; task-initial, later first-observed and post-import pins remain distinguished by observation receipt; no inherited mass input snapshot',files=rows)
 js(P/'INPUTS-AFTER.json',after);js(R/'INPUTS-AFTER.json',after)
 for root in (P,R):
  with (root/'REPORT.md').open('a') as f:f.write('\n最终必要技术 pin 去重 **'+str(len(rows))+'项**，其中外部原技术输入 **'+str(external)+'项**、本轮产物依赖 **'+str(len(rows)-external)+'项**；结束复核全部一致。时点口径见各观察清单及 `INPUTS-AFTER.json`。\n')
  analysis=sorted(root.glob('*.py')) if root==P else [R/'derive_runner.py',R/'verify_r42.py']
  js(root/'ANALYSIS-SOURCE-FREEZE.json',{str(p.relative_to(root)):sha(p) for p in analysis})
  assert not any(p.is_symlink() for p in root.rglob('*'))
  assert not any(p.name in ('__pycache__','node_modules','.venv') for p in root.rglob('*'))
  js(root/'FINAL-VERIFY.json',dict(status='offline_package_and_host_binding_passed',time=after['time'],external_inputs_unchanged=external,current_artifact_pins_unchanged=len(rows)-external,VM=False,browser=False,service=False,QMP=False,guest_execution=False,compilation=False,deployment=False,root_cause_fixed=False,menu_passed=False,FX6_boot_passed=False,owned_host_processes='all controlled host subprocess.run children synchronously returned; no persistent process launched',historical_matrix='not rerun; prior accepted evidence only'))
  files=sorted(p for p in root.rglob('*') if p.is_file() and p.name!='SHA256SUMS')
  (root/'SHA256SUMS').write_text(''.join(sha(p)+'  '+str(p.relative_to(root))+'\n' for p in files))
  print(json.dumps(dict(root=str(root),files=len(files),bytes=sum(p.stat().st_size for p in files),manifest_sha256=sha(root/'SHA256SUMS'))))
if __name__=='__main__':main()
