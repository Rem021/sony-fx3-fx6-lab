from pathlib import Path
import ast,importlib.util,json,hashlib
R=Path(__file__).resolve().parents[1];BASE=R.parent/'first-key-freshness-r19/trial_web_v22_navigation_review.py'
def load(p,name):
 sp=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m);return m
old=load(BASE,'old_r19');new=load(R/'trial_web_v22_navigation_review.py','new_r20')
def prep(m):
 t=m.TrialState('offline',3600,4096);t.phase='ready';t.ready=True
 import hashlib
 raw=b'fixture';h=hashlib.sha256(raw).hexdigest();t.publish(raw,{'sequence':1,'PNG_sha256':h,'all_zero_pixels':False});return t
results={}
for label,body in [('badkey',{'key':9,'observed_sequence':1}),('missingseq',{'key':427,'observed_sequence':4}),('accepted',{'key':427,'observed_sequence':1})]:
 a,b=prep(old),prep(new);x=a.submit(body);y=b.submit(body);assert x==y,(label,x,y);assert len(a.pending)==len(b.pending);results[label]={'legacy_response_equal':True,'pending':len(b.pending)}
uid='aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa';t=prep(new);code,body=t.submit({'key':427,'observed_sequence':9,'request_id':uid});assert code==409 and body['request_id']==uid and body['enqueued'] is False and not t.pending
row=t.key_rejection_snapshot()['records'][0];assert row['request_id']==uid;results['structured_reject']={'code':code,'response':body,'row_request_id':row['request_id'],'pending':len(t.pending)}
t=prep(new);code,body=t.submit({'key':427,'observed_sequence':1,'request_id':uid});assert code==202 and body['request_id']==uid and len(t.pending)==1;results['structured_accepted']={'code':code,'response':body,'pending':len(t.pending),'guest_input_written':'not_observed'}
(R/'evidence/server-audit.json').write_text(json.dumps(results,ensure_ascii=False,indent=2)+'\n');print('PASS',len(results))
