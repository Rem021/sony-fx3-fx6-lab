from pathlib import Path
import json,re,subprocess,sys
R=Path(__file__).resolve().parent;stage=sys.argv[1];subprocess.run(['python3',str(R/'review_ap71_73.py'),stage],check=True)
p=R/(stage.lower()+'-review.json');v=json.loads(p.read_text());l=(Path(v['run'])/'serial.log').read_text(errors='replace').split('\n');keys=['FX3_TIMER_SNAPSHOT','FX3_TIMER_BOUND','FX3_TIMER_ENTRY','FX3_TIMER_ID ','FX3_TIMER_INFO ','FX3_TIMER_TABLE','FX3_TIMER_RETURN','FX3_UI_CONFIG_ENTER','FX3_UI_CONFIG_RETURN','FX3_UI_CONFIG_DONE','FX3_UI_FILL_EXEC','FX3_UI_FILL_RETURN','FX3_UI_WIRE','FX3_GPE_CMD']
v['timer_events']={k:[{'line':i+1,'text':x.rstrip('\r')} for i,x in enumerate(l) if k in x] for k in keys};v['end_stats']={}
for i,x in enumerate(l):
 for kind in ['FX3_UIPC_OBSERVER_END','FX3_TIMER_OBSERVER_END']:
  if kind in x:
   fields=dict(re.findall(r'(\w+)=(\d+)',x[x.index(kind):]));pid=fields.get('pid','unknown');v['end_stats'][kind+'/'+pid]={'line':i+1,**{k:int(z) for k,z in fields.items()}}
v['fatal']=[{'line':i+1,'text':x} for i,x in enumerate(l) if 'Entering exception monitor.' in x or 'symbol lookup error' in x or 'FX3_TIMER_BIND_FAILED' in x];v['same_candidate_repeat_group']='AP75-final-r3' if 'r3' in json.loads((Path(v['run'])/'receipt.json').read_text())['candidate'] else 'AP75-instrument-calibration';p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n');print('EVENT_COUNTS',{k:len(x) for k,x in v['timer_events'].items()});print('STATS',json.dumps(v['end_stats'],indent=2));print('FATAL',v['fatal'])
