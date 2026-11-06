#!/usr/bin/env python3
"""Explicit failure-only ONE read-only snapshot/screenshot, then original End immediately."""
from pathlib import Path
import datetime,json,subprocess,time
R=Path(__file__).resolve().parent;c=json.loads((R/'OPERATOR-CONFIG.json').read_text())
def utc():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def br(args,source=None):
 p=subprocess.run(['agent-browser','--session',c['session'],*args],input=source,capture_output=True,text=True,timeout=5)
 if p.returncode:raise RuntimeError(p.stdout+p.stderr)
 return p.stdout
record={'UTC_enter':utc(),'host_monotonic_enter':time.monotonic(),'operation':'single passive rejection snapshot then End; no wait refresh or retry'}
with (R/'R18-409-End.json').open('x') as f:json.dump(record,f,indent=2)
identity=False
try:
 script='''(()=>{if(location.href!==URL||lastStatus.launch_request_id!==LAUNCH)throw Error('owned page identity mismatch');return {UTC:new Date().toISOString(),performance_ms:performance.now(),shownSHA,displayedGeneration,displayed,lastStatus,explicitRejection,deliveryUnknown,awaitingStep,busy,ending,finished,renderFault,keys:keys.map(b=>({key:b.dataset.key,disabled:b.disabled})),failureSummary:failureSummary.textContent,error:err.textContent,review:reviewEl.textContent,alarm:window.__fx3InteractionDeadlineV1.status()};})()'''.replace('URL',json.dumps(c['url'])).replace('LAUNCH',json.dumps(c['launch_id']))
 snap=json.loads(br(['eval','--stdin'],script));identity=True
 (R/'R18-409-snapshot.json').write_text(json.dumps(snap,ensure_ascii=False,indent=2)+'\n')
 record.update(snapshot_UTC=utc(),snapshot_host_monotonic=time.monotonic())
 br(['screenshot',str(R/'R18-409-page.png')]);record.update(screenshot_return_UTC=utc(),screenshot_return_host_monotonic=time.monotonic())
except Exception as e:record['diagnostic_error']=repr(e)
finally:
 if identity:
  record.update(End_click_enter_UTC=utc(),End_click_enter_host_monotonic=time.monotonic())
  try:record['End_click_result']=br(['click','#end'])
  except Exception as e:record['End_error']=repr(e)
  record.update(End_click_return_UTC=utc(),End_click_return_host_monotonic=time.monotonic())
 record.update(UTC_return=utc(),host_monotonic_return=time.monotonic())
 (R/'R18-409-End.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(record,ensure_ascii=False))
