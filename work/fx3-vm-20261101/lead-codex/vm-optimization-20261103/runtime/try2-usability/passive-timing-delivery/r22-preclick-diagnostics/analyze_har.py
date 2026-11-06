"""Read existing r21c HAR only. Polls bound observations, never eval-time DOM evidence."""
import datetime as dt, decimal, hashlib, json, statistics
from pathlib import Path
ROOT=Path(__file__).resolve().parent
SRC=ROOT.parent/'r21c-cli-menu8-024b06c9361a'

def timestamp(s):
 # Preserve HAR's nanosecond precision instead of float datetime truncation.
 whole,frac=s.removesuffix('Z').split('.')
 return int(dt.datetime.fromisoformat(whole).replace(tzinfo=dt.timezone.utc).timestamp())*10**9+int(frac.ljust(9,'0'))
rows=[]
for i,e in enumerate(json.loads((SRC/'traffic.har').read_text())['log']['entries']):
 if e['request']['method']!='GET' or not e['request']['url'].endswith('/api/status'):continue
 body=json.loads(e['response']['content']['text']);f=body.get('frame')
 if not f or body['phase']!='ready':continue
 rows.append({'entry_index':i,'start_UTC':e['startedDateTime'],'start_ns':timestamp(e['startedDateTime']),
              'duration_ms':e.get('time'),'phase':body['phase'],'ready':body['ready'],'steps':body['steps'],
              'busy':body['busy'],'review_required':body['review_required'],
              'generation':f['content_generation'],'sequence':f['sequence'],'sha256':f['PNG_sha256'],
              'frame_host_monotonic':f.get('host_monotonic')})
changes=[];runs=[]
for row in rows:
 if not runs or row['generation']!=runs[-1]['generation']:
  if runs:
   prev=rows[rows.index(row)-1]
   changes.append({'from_generation':prev['generation'],'to_generation':row['generation'],
                   'last_old_status_start_UTC':prev['start_UTC'],'first_new_status_start_UTC':row['start_UTC'],
                   'poll_bracket_ms':(row['start_ns']-prev['start_ns'])/1e6})
  runs.append({'generation':row['generation'],'sha256':row['sha256'],'first':row,'last':row,'samples':1})
 else:runs[-1]['last']=row;runs[-1]['samples']+=1
intervals=[(b['first']['start_ns']-a['first']['start_ns'])/1e6 for a,b in zip(runs,runs[1:])]
# For internal generation lifetimes, interval bounds come from the two polling brackets.
bounds=[]
for i in range(1,len(runs)-1):
 a,b,c=runs[i-1:i+2]
 lower=(b['last']['start_ns']-b['first']['start_ns'])/1e6
 upper=(c['first']['start_ns']-a['last']['start_ns'])/1e6
 bounds.append({'generation':b['generation'],'observed_same_generation_span_ms':lower,
                'poll_bracket_lifetime_upper_ms_approx':upper})
cap=json.loads((SRC/'initial-standby/capture-result.json').read_text())
ledger=json.loads((SRC/'ledger.json').read_text())
delay=(ledger['attempts'][0]['host_ns']-cap['host_ns'])/1e9
r={'source_HAR_sha256':hashlib.sha256((SRC/'traffic.har').read_bytes()).hexdigest(),
   'scope':'server status GET observations only; request-start polling brackets approximate response/server timing, not exact publish or eval-time DOM',
   'ready_status_samples':len(rows),'generation_runs':len(runs),'observed_generation_changes':len(changes),
   'generations':[x['generation'] for x in runs], 'distinct_SHA':sorted({x['sha256'] for x in rows}),
   'first_observed_new_generation_intervals_ms':intervals,
   'interval_summary_ms':{'min':min(intervals),'median':statistics.median(intervals),'max':max(intervals)},
   'observed_generation_lifetime_bounds':bounds,
   'review_to_reservation_seconds':delay,'reviewed_identity':cap['firmware'],
   'rows':rows,'changes':changes,
   'cannot_determine':['exact generation publish times','unobserved intermediate generations','eval-time DOM fields','original failing predicate','model receive/review completion time']}
(ROOT/'evidence/HAR-ANALYSIS.json').write_text(json.dumps(r,indent=2)+'\n')
print(json.dumps({k:r[k] for k in ['ready_status_samples','generation_runs','observed_generation_changes','generations','interval_summary_ms','review_to_reservation_seconds']},indent=2))
