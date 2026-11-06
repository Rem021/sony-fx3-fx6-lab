from pathlib import Path
import re,sys,json,collections
s=Path(sys.argv[1]).read_text(errors='replace');ev=[]
for l in s.splitlines():
 if not any(x in l for x in ('FX3_GPE104_DYNAMIC_RETURN','FX3_GPE104_COMPLETE_RETURN')):continue
 def v(k):
  m=re.search(r'(?<![A-Za-z])'+k+r'=([^ ]+)',l);return m[1] if m else None
 if 'FX3_GPE104_DYNAMIC_RETURN' in l and v('result')=='0':
  if v('flags')=='0x2a' and v('module')=='0x82':ev.append(('alloc',v('QID'),int(v('ns')),v('event'),None))
  if v('flags')=='0x4a':ev.append(('release',v('QID'),int(v('ns')),v('event'),None))
 if 'FX3_GPE104_COMPLETE_RETURN' in l:ev.append(('complete',v('completion_source'),int(v('ns')),v('event'),v('result')))
q=collections.defaultdict(collections.deque);gen=collections.Counter();rows=[];orphan=[];maxpending=0
for kind,key,ns,e,result in ev:
 if kind=='alloc':
  gen[key]+=1;row={'qid':key,'generation':gen[key],'allocate_ns':ns,'alloc_event':e,'complete_ns':None,'complete_result':None,'release_ns':None};q[key].append(row);rows.append(row)
 elif kind=='complete':
  matches=[x for x in q[key] if x['complete_ns'] is None]
  if matches:matches[0].update(complete_ns=ns,complete_result=result,complete_event=e)
  else:orphan.append((kind,key,e))
 elif kind=='release':
  matches=[x for x in q[key] if x['release_ns'] is None]
  if matches:matches[0].update(release_ns=ns,release_event=e)
  # Other modules use separate QIDs, so ignore releases without GPE allocation.
 maxpending=max(maxpending,sum(x['complete_ns'] is None for x in rows))
paired=[x for x in rows if x['complete_ns'] is not None];success=[x for x in paired if x['complete_result']=='1'];fail=[x for x in paired if x['complete_result']!='1']
res={'source':sys.argv[1],'gpe_alloc':len(rows),'gpe_complete':len(paired),'gpe_success':len(success),'gpe_failed':fail,'gpe_incomplete':[x for x in rows if x['complete_ns'] is None],'gpe_released':sum(x['release_ns'] is not None for x in rows),'gpe_missing_release':[x for x in rows if x['release_ns'] is None],'orphan_completion':orphan,'max_outstanding_completion':maxpending,'success_max_upper_bound_ms':max(((x['complete_ns']-x['allocate_ns'])/1e6 for x in success),default=None),'success_over_5000':sum((x['complete_ns']-x['allocate_ns'])>=5_000_000_000 for x in success),'failed_bounds_ms':[(x['complete_ns']-x['allocate_ns'])/1e6 for x in fail],'order_violations':[x for x in paired if x['complete_ns']<x['allocate_ns'] or (x['release_ns'] is not None and x['release_ns']<x['allocate_ns'])]}
print(json.dumps(res,indent=2))
