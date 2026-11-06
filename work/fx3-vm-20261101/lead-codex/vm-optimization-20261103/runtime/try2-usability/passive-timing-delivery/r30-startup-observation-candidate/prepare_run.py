#!/usr/bin/env python3
"""Create task-specific run inputs only; this command NEVER starts a browser/runner/guest."""
import argparse,hashlib,json,os,plistlib,re,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parent
DEL=ROOT.parent
FROZEN=DEL/'v25-r21-recovery-integration'
def main():
 p=argparse.ArgumentParser(description=__doc__)
 for k in ('run-dir','task-id','dispatch-id','session'):p.add_argument('--'+k,required=True)
 a=p.parse_args()
 assert plistlib.loads(subprocess.check_output(['diskutil','info','-plist','/Volumes/KAFU2T']))['VolumeUUID']=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
 out=Path(a.run_dir).resolve();assert out.is_relative_to(DEL) and out!=ROOT and re.fullmatch(r'fx3-deadline-[A-Za-z0-9_-]+',a.session)
 assert a.task_id.startswith('task_') and a.dispatch_id.startswith('ctx_') and a.task_id.removeprefix('task_') in out.name
 out.mkdir() # exclusive; never overwrite a prior run
 plan=json.loads((ROOT/'NAVIGATION-PLAN.json').read_text())
 cfg={'session':a.session,'frozen_root':str(FROZEN),'task_id':a.task_id,'dispatch_id':a.dispatch_id,
      'scripted_navigation':True,'visual_review_at_click':False,'scope':'one future explicitly authorized VM; 8 steps/10 attempts/2 unqueued recoveries',
      'plan_sha':hashlib.sha256((ROOT/'NAVIGATION-PLAN.json').read_bytes()).hexdigest(),'steps':plan['steps']}
 def put(n,v):(out/n).write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
 put('config.json',cfg)
 files=[ROOT/'startup_observation.py',ROOT/'trial_ring_cached.py',ROOT/'trial_log_v4_mss.py',ROOT/'NAVIGATION-PLAN.json',ROOT/'prepare_run.py',ROOT/'PAGE-IDENTITY.json',ROOT/'trial_web_r24_review_snapshot.py',ROOT/'run_trial_r24_review_snapshot.py',ROOT/'review_page_r24.js',ROOT/'confirm_page_r24.js',*sorted((ROOT/'operator-helpers').glob('*.*')),*sorted((ROOT/'runtime-wrapper').glob('*.*')),*sorted((ROOT/'return-tools').glob('*.*')),ROOT/'CORE-SOURCE-FREEZE.json']
 put('LOCAL-SOURCE-FREEZE.json',{str(f):hashlib.sha256(f.read_bytes()).hexdigest() for f in files if f.is_file()})
 put('ledger.json',{'attempts':[],'recoveries':[]})
 wrapper=ROOT/'runtime-wrapper'
 commands={name:['python3','-B',str(wrapper/name)] for name in ('preflight.py','launch_prepare.py','start_and_wait.py','cleanup.py','audit_after.py')}
 commands['standby_review']=['python3','-B',str(wrapper/'operate.py'),'standby_review','实际看图后填入待机语义判断']
 commands['steps']=[{'planned_click':['python3','-B',str(wrapper/'operate.py'),'click',str(s['step']),s['target']],
                     'pin_after_actual_observation_review':['python3','-B',str(wrapper/'operate.py'),'pin','实际看上一张观察图已完整后的明确选择：'+s['target']],
                     'confirm_after_actual_fixed_image_review':['python3','-B',str(wrapper/'operate.py'),'confirm','实际看本步新图后填入语义判断：'+s['target']]} for s in plan['steps']]
 commands['reject']=['python3','-B',str(wrapper/'operate.py'),'reject','实际观察/固定图语义不符或不确定，立即原End']
 commands['observe']=['python3','-B',str(wrapper/'operate.py'),'observe','实际看上一观察仍为正常过渡，明确再次观察；最多3次含首图，原20s不重置']
 commands['recovery_cancel']=['python3','-B',str(wrapper/'operate.py'),'recovery_cancel','实际看归因未入队新图后的判断']
 commands['recovery_review']=['python3','-B',str(wrapper/'operate.py'),'recovery_review','实际看cancel后新图后的判断']
 put('CLI-TEMPLATES.json',{'env':{'FX3_NAV_RUN_DIR':str(out)},'commands':commands,'warning':'templates only; no command executed by prepare_run'})
 print(json.dumps({'status':'prepared_only_no_process_started','run_dir':str(out),'config':cfg},ensure_ascii=False))
if __name__=='__main__':main()
