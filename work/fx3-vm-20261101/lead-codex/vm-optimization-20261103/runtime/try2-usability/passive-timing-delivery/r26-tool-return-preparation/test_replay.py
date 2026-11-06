#!/usr/bin/env python3
"""Small historical replay suite and single-case display harness; NEVER calls operate.py."""
import contextlib,hashlib,io,json,os,subprocess,sys
from pathlib import Path
import return_adapter as adapter
ROOT=Path(__file__).resolve().parent

def run(case,name):
 root=ROOT/'evidence'/name;root.mkdir();image=root/'old.png';image.write_bytes((ROOT/'samples/observation.png').read_bytes());os.utime(image,ns=(1,1))
 old={'status':'qualified_unpinned_postkey_observation','screenshot_path':str(image),'screenshot_sha256':adapter.sha(image)}
 (root/'current-return.json').write_text(json.dumps(old));old_hash=adapter.sha(root/'current-return.json');out=root/'call'
 action='pin' if case=='fixed' else ('confirm' if case=='confirmation' else 'observe')
 argv=[sys.executable,'-B',str(ROOT/'fake_child.py'),case,str(root)]
 with contextlib.redirect_stdout(io.StringIO()):code=adapter._execute_once(argv,action,root,out,{**os.environ,'FX3_RETURN_FIXTURE_ONLY':'1','PYTHONDONTWRITEBYTECODE':'1'})
 value=json.loads((out/'summary.json').read_text());assert len((out/'summary.json').read_bytes())<4096 and adapter.sha(root/'current-return.json')==old_hash
 expected=case in ('observation','fixed','confirmation');assert value['ok']==expected and (code==0)==expected
 if expected and case!='confirmation':assert value['image'] and adapter.sha(value['image']['path'])==value['image']['sha256']
 else:assert value['image'] is None and not (out/'returned.png').exists()
 return {'case':case,'code':code,'root':str(root),'out':str(out),'action':action,'stdout_bytes':(out/'child.stdout.json').stat().st_size,'summary_bytes':(out/'summary.json').stat().st_size,'current_return_untouched':True,'summary':value}

if __name__=='__main__':
 if len(sys.argv)==3:
  value=run(sys.argv[1],sys.argv[2]);(ROOT/'evidence'/(sys.argv[2]+'.json')).write_text(json.dumps(value,indent=2)+'\n');print(json.dumps(value['summary'],ensure_ascii=False));raise SystemExit(value['code'])
 cases=['observation','fixed','confirmation','nonzero','invalid','truncated','current_only','stale_png'];values=[run(c,'attempt02-case-'+c) for c in cases]
 # Production dispatch spy: validate exact frozen argv, one call and shell text remains one argument.
 spy_root=ROOT/'evidence/attempt02-dispatch-spy';spy_root.mkdir();(spy_root/'config.json').write_text('{}');(spy_root/'runtime.json').write_text('{}');calls=[]
 original=adapter._execute_once
 def spy(argv,action,run_dir,out,env):calls.append((argv,action));return 0
 adapter._execute_once=spy;saved=sys.argv
 try:
  sys.argv=['return_adapter.py','--run-dir',str(spy_root),'--output-dir',str(spy_root/'new-call'),'--','pin','literal $(false); do not execute']
  assert adapter.main()==0 and len(calls)==1 and calls[0][0]==['python3','-B',str(adapter.OPERATE),'pin','literal $(false); do not execute']
 finally:adapter._execute_once=original;sys.argv=saved
 result={'passed':True,'scope':__doc__,'cases':values,'production_dispatch_spy':{'calls':len(calls),'frozen_argv':calls[0][0],'real_original_actions':0},'VM_starts':0}
 (ROOT/'evidence/TEST-RESULT.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'passed':True,'cases':len(values),'real_original_actions':0,'VM_starts':0}))
