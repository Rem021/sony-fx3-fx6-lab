from pathlib import Path
import json,re,subprocess,sys
R=Path(__file__).resolve().parent
subprocess.run(['python3',str(R/'review_ap71_73.py'),'AP74']+sys.argv[1:],check=True)
p=R/'ap74-review.json';v=json.loads(p.read_text());l=(Path(v['run'])/'serial.log').read_text(errors='replace').split('\n')
commits=[]
for i,x in enumerate(l):
 m=re.search(r'FX3_ADF_BEEP_COMMIT command=(0x\w+) tid=(\d+) kind=(\d+) registered=(\d+) volume=(\d+) phys=(0x\w+|0) offset=(0x\w+|0) size=(\d+) lease=(\d+)',x)
 if m:
  c,tid,kind,reg,vol,phys,off,size,lease=m.groups();free=[{'line':j+1,'text':y} for j,y in enumerate(l) if f'command={c} lease={lease} result=0' in y and 'FX3_CAPID_NATIVE_FREE' in y];commits.append(dict(line=i+1,command=c,tid=int(tid),kind=int(kind),registered=int(reg),volume=int(vol),physical=phys,offset=off,size=int(size),lease=int(lease),free_result0=free))
v.update(beep_commits=commits,beep_all_observed_consumed_free0=all(x['free_result0'] for x in commits),beep_rejects=[{'line':i+1,'text':x} for i,x in enumerate(l) if 'FX3_ADF_BEEP_REJECT' in x],queue_sends=[{'line':i+1,'text':x} for i,x in enumerate(l) if 'FX3_BOOT_QUEUE_SEND' in x],get_func_325_requests=[{'line':i+1,'text':x} for i,x in enumerate(l) if 'raw=0d20250308000180' in x or 'tag1=0x325200d' in x],fatal=[{'line':i+1,'text':x} for i,x in enumerate(l) if any(z in x for z in ['FX3_ASSERT_OBSERVE','Entering exception monitor.','Abort (PC=','status=-3 handle='])],barrier_passed=False,healthy_im=False)
# Normalize independently captured exception FP chain, preserving raw stack evidence.
start=next((i for i,x in enumerate(l) if '[stack dump]' in x),len(l));v['exception_stack_raw']=[{'line':i+1,'text':x} for i,x in enumerate(l) if start<i<start+100];v['new_dmm_request']=[{'line':i+1,'text':x} for i,x in enumerate(l) if 'raw=2000000017080700' in x];p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
print('BEEP',len(commits),'FREE0',sum(bool(x['free_result0']) for x in commits),'325',len(v['get_func_325_requests']),'FATAL',v['fatal'])
