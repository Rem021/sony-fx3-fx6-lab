"""Read-only post-run GPE dynamic-QID/explicit-completion pairing.
No inference about original ReceiveDrawComp duration or kernel clock correlation.
"""
from pathlib import Path
import collections, hashlib, json, re, sys

def fields(text):
    return dict(re.findall(r'([A-Za-z_]+)=([^\s]+)',text))

def analyze(path):
    raw=path.read_bytes();text=raw.decode('utf-8','replace')
    pending=collections.defaultdict(collections.deque)
    by_event={}
    pairs=[];release_only=[];unmatched_completion=[];ambiguous=[]
    pattern=re.compile(r'FX3_GPE104_(DYNAMIC_RETURN|COMPLETE_ENTER|COMPLETE_RETURN)[^\r\n]*')
    for m in pattern.finditer(text):
        typ=m.group(1); f=fields(m.group(0)); q=f.get('QID') if typ=='DYNAMIC_RETURN' else f.get('completion_source')
        try: ns=int(f['ns'])
        except (ValueError,KeyError): ambiguous.append(m.start());continue
        if typ=='DYNAMIC_RETURN':
            try:result=int(f['result'])
            except (ValueError,KeyError):ambiguous.append(m.start());continue
            if f.get('flags')=='0x2a' and f.get('module')=='0x82' and result==0 and q:
                pending[q].append({'qid':q,'alloc_event':int(f['event']),'alloc_return_ns':ns,'alloc_offset':m.start(),'complete':None,'complete_enter':None,'release':None})
            elif f.get('flags')=='0x4a' and q:
                if not pending[q]:release_only.append({'qid':q,'ns':ns,'offset':m.start()});continue
                item=pending[q].popleft();item['release']={'ns':ns,'result':result,'errno':f.get('errno'),'event':f.get('event')};pairs.append(item)
        elif typ=='COMPLETE_ENTER':
            if not q or q=='0':continue
            item=next((x for x in pending[q] if x['complete_enter'] is None),None)
            if item is None:unmatched_completion.append({'kind':'enter','qid':q,'ns':ns,'seq':f.get('seq')});continue
            event=int(f['event']);item['complete_enter']={'ns':ns,'seq':int(f['seq']),'event':event};by_event[event]=item
        else:
            if not q or q=='0':continue
            try:event=int(f['event']);result=int(f['result'])
            except (ValueError,KeyError):ambiguous.append(m.start());continue
            item=by_event.pop(event,None)
            if item is None:unmatched_completion.append({'kind':'return','qid':q,'ns':ns,'seq':f.get('seq'),'result':result});continue
            item['complete']={'ns':ns,'seq':int(f['seq']),'event':event,'result':result,'errno':f.get('errno')}
            item['bound_ms']=(ns-item['alloc_return_ns'])/1e6
    for q,queue in pending.items():pairs.extend(queue)
    complete=[x for x in pairs if x['complete'] is not None]
    successful=[x for x in complete if x['complete']['result']==1]
    over5=[x for x in successful if x['bound_ms']>=5000]
    late_release=[x for x in complete if x['release'] and x['complete']['ns']>x['release']['ns']]
    return {'serial_path':str(path),'serial_sha256':hashlib.sha256(raw).hexdigest(),'serial_bytes':len(raw),'clock':'guest user CLOCK_MONOTONIC ns only','allocations':len(pairs),'completion_count':len(complete),'successful_completion_count':len(successful),'release_count':sum(bool(x['release']) for x in pairs),'unmatched_completion':unmatched_completion[:30],'release_only':release_only[:30],'ambiguous_records':ambiguous[:30],'pending_unreleased':[{k:v for k,v in x.items() if k!='alloc_offset'} for x in pairs if not x['release']][:30],'completed_after_release':late_release[:30],'over_5000ms_bounds':over5,'max_bound_ms':max((x['bound_ms'] for x in successful),default=None),'bound_definition':'dynamic allocation return to explicit SendDrawComp return, not original ReceiveDrawComp timing','kernel_free_error_count':text.count('free_dynamic_msgq_id:'),'unfetched_count':text.count('unfetched'),'osd_alloc_marker_count':text.count('FX3_OSD_ALLOC_DEADLINE_EVIDENCE_END')}

if __name__=='__main__':
    for arg in sys.argv[1:]:
        p=Path(arg);out=p.parent/'performance-analysis.json'
        if out.exists():raise SystemExit('Refuse overwrite '+str(out))
        x=analyze(p);out.write_text(json.dumps(x,indent=2)+'\n')
        print(out,x['allocations'],x['successful_completion_count'],x['release_count'],x['max_bound_ms'],len(x['over_5000ms_bounds']))
