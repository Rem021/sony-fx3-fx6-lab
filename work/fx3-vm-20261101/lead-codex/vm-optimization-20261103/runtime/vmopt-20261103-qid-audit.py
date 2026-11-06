from pathlib import Path
import re,sys,json,collections
p=Path(sys.argv[1]);s=p.read_text(errors='replace');events=[]
for l in s.splitlines():
 if 'FX3_GPE104_DYNAMIC_RETURN' not in l and 'FX3_GPE104_COMPLETE_RETURN' not in l:continue
 def v(k):
  m=re.search(r'(?<![a-zA-Z])'+re.escape(k)+r'=([^ ]+)',l);return m[1] if m else None
 kind='dynamic' if 'FX3_GPE104_DYNAMIC_RETURN' in l else 'complete'
 events.append({'kind':kind,'event':v('event'),'tid':v('tid'),'ns':int(v('ns')) if v('ns') else None,'flags':v('flags'),'module':v('module'),'qid':v('QID') if kind=='dynamic' else v('completion_source'),'caller':v('caller'),'seq':v('seq'),'result':v('result'),'line':l[:350]})
unique={};duplicates=[]
for e in events:
 k=(e['kind'],e['event'],e['tid'])
 if k in unique:duplicates.append({'key':k,'same':e==unique[k]})
 else:unique[k]=e
alloc=[e for e in unique.values() if e['kind']=='dynamic' and e['flags']=='0x2a' and e['result']=='0']
release=[e for e in unique.values() if e['kind']=='dynamic' and e['flags']=='0x4a' and e['result']=='0']
complete=[e for e in unique.values() if e['kind']=='complete' and e['result']=='1']
by_module=collections.Counter((e['module'],e['caller']) for e in alloc)
qalloc=collections.defaultdict(list);qrel=collections.defaultdict(list);qcomp=collections.defaultdict(list)
for e in alloc:qalloc[e['qid']].append(e)
for e in release:qrel[e['qid']].append(e)
for e in complete:qcomp[e['qid']].append(e)
rows=[]
for q,aa in qalloc.items():
 rr=qrel[q];cc=qcomp[q];rows.append({'qid':q,'alloc':len(aa),'release':len(rr),'complete':len(cc),'modules':dict(collections.Counter(e['module'] for e in aa)),'first_ns':aa[0]['ns'],'last_ns':aa[-1]['ns']})
gpe=[e for e in alloc if e['module']=='0x82'];other=[e for e in alloc if e['module']!='0x82'];gpecomp=[e for e in complete if e['qid'] in {x['qid'] for x in gpe}]
res={'source':str(p),'raw_event_lines':len(events),'unique_events':len(unique),'duplicate_event_lines':duplicates[:5],'duplicate_count':len(duplicates),'alloc_total':len(alloc),'alloc_gpe_module_0x82':len(gpe),'alloc_other_module':len(other),'alloc_other_by_module_caller':[{'module':m,'caller':c,'count':n} for (m,c),n in by_module.items() if m!='0x82'],'release_total':len(release),'complete_total':len(complete),'gpe_source_completes':len(gpecomp),'qid_rows':rows,'gpe_qids':sorted(set(e['qid'] for e in gpe)),'non_gpe_qids':sorted(set(e['qid'] for e in other)),'saw_unfetched':s.count('unfetched')}
print(json.dumps(res,indent=2))
