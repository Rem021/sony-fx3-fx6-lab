from pathlib import Path
import re,json,sys,collections,statistics
s=Path(sys.argv[1]).read_text(errors='replace')
queues=collections.defaultdict(collections.deque); pairs=[];unmatched=[]
for line in s.splitlines():
 if 'FX3_GPE104_DYNAMIC_RETURN' in line and 'flags=0x2a' in line and 'result=0 ' in line:
  q=re.search(r'QID=(0x[0-9a-f]+)',line);t=re.search(r'ns=(\d+)',line)
  if q and t:queues[q[1]].append(int(t[1]))
 if 'FX3_GPE104_COMPLETE_RETURN' in line and 'real_function_returned=1' in line:
  q=re.search(r'completion_source=(0x[0-9a-f]+)',line);t=re.search(r'ns=(\d+)',line);seq=re.search(r'seq=(\d+)',line)
  if q and t:
   if queues[q[1]]:
    a=queues[q[1]].popleft();pairs.append({'qid':q[1],'seq':int(seq[1]) if seq else None,'receive_return_ns':a,'completion_return_ns':int(t[1]),'upper_bound_ms':(int(t[1])-a)/1e6})
   else:unmatched.append(line[:300])
vals=[x['upper_bound_ms'] for x in pairs]
result={'scope':'Same guest user monotonic ns: successful dynamic QID return to explicit SendDrawComp return, conservative bound, not direct ReceiveDrawComp entry','pairs':len(pairs),'max_ms':max(vals) if vals else None,'p95_ms':sorted(vals)[int(.95*(len(vals)-1))] if vals else None,'over_5000_ms':[x for x in pairs if x['upper_bound_ms']>=5000],'top10':sorted(pairs,key=lambda x:x['upper_bound_ms'],reverse=True)[:10],'unmatched_completion_count':len(unmatched),'pending_receives':sum(map(len,queues.values())),'unfetched_count':s.count('unfetched'),'gpe_cmd_count':s.count('FX3_GPE_CMD ')}
print(json.dumps(result,indent=2))
