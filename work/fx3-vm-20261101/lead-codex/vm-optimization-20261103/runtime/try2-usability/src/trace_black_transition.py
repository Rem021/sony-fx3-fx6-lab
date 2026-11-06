#!/usr/bin/env python3
"""Read-only same-clock ring and serial transition comparison."""
import json,re
from pathlib import Path

root=Path(__file__).resolve().parents[1]
runs={
 'user_try2_70588c4c': (root.parent/'try2-delivery/runs/try2-70588c4c',1198,1199),
 'internal_47e2924a': (root/'runs/try2gapinternal-47e2924a',717,718),
}
out={}
for label,(run,fill_seq,flush_seq) in runs.items():
 frames=json.loads((run/'osd-ring-readback.json').read_text())['frames']
 zero=lambda f: f.get('all_zero_pixels',not f['nonuniform_pixels'] and f['fnv64']=='0x4f2d9f141eeda325')
 first=next(i for i,f in enumerate(frames) if i and zero(f) and any(not zero(x) for x in frames[:i]))
 before=next(f for f in frames[:first][::-1] if not zero(f))
 after=frames[first]
 pick=lambda f:{k:f.get(k) for k in ('sequence','update_id','pixel_source_sequence','token','physical','fnv64','sha256','PNG_sha256','host_monotonic','nonuniform_pixels','all_zero_pixels')}|{'config_hash':f['native_identity']['config_hash']}
 b=(run/'serial.log').read_bytes()
 events=[]
 for pattern,name in [(rb'FX3_GPE_CMD op=FillRect seq='+str(fill_seq).encode()+rb'[^\r\n]*','fill'),
                      (rb'FX3_GPE_CMD op=Flush seq='+str(flush_seq).encode()+rb'[^\r\n]*','flush'),
                      (rb'FX3_OSD102_COMMIT frame='+str(after['pixel_source_sequence']).encode()+rb'[^\r\n]*','source_commit')]:
  match=re.search(pattern,b)
  if match: events.append({'kind':name,'serial_byte_range':[match.start(),match.end()],'line':match[0].decode(errors='replace')})
 fill_at=next((e['serial_byte_range'][0] for e in events if e['kind']=='fill'),len(b))
 gui=[]
 for match in re.finditer(rb'FX3_OSD_OWNER_GUI queue=[^\r\n]* op=100[014] [^\r\n]*',b):
  gui.append({'serial_byte_range':[match.start(),match.end()],'line':match[0].decode(errors='replace')})
 owner_gui={}
 for op in ('1000','1001','1004'):
  pre=[e for e in gui if e['serial_byte_range'][0]<fill_at and 'op='+op+' ' in e['line']]
  post=[e for e in gui if e['serial_byte_range'][0]>fill_at and 'op='+op+' ' in e['line']]
  owner_gui[op]={'last_before_fill':pre[-1] if pre else None,'first_after_fill':post[0] if post else None}
 out[label]={'run':str(run),'last_sampled_nonblack':pick(before),'first_sampled_black':pick(after),
             'host_monotonic_observation_gap_seconds':round(after['host_monotonic']-before['host_monotonic'],3),
             'serial_events':events,'owner_gui_receipts':owner_gui,
             'config_payload_bytes':'unknown: owner log records op/size/count, not raw config; ring exposes hash only',
             'gpe_to_host_time':'unknown: serial command has no host monotonic stamp'}
(root/'black-transition-compare.json').write_text(json.dumps(out,indent=2,ensure_ascii=False)+'\n')
print(root/'black-transition-compare.json')
