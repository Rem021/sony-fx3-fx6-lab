#!/usr/bin/env python3
"""Pin original shutdown-screen entry against nearby native receipts, read only."""
import json,re
from pathlib import Path
root=Path(__file__).resolve().parents[1]
runs={'user_try2_70588c4c':root.parent/'try2-delivery/runs/try2-70588c4c',
      'internal_47e2924a':root/'runs/try2gapinternal-47e2924a'}
patterns={
 'screen_open':rb'open screen: [^\r\n]* -> scr0039_shutdown',
 'model_power_off':rb'FX3_BOOT_QUEUE_SEND[^\r\n]*source=0x830128 raw=2c000300[^\r\n]*',
 'ap89_id2':rb'FX3_AP89_SCREEN_OPEN_ENTER[^\r\n]*id2=0x2af[^\r\n]*',
 'controller_return':rb'FX3_AP89_SCREEN_CREATE phase=controller_init_return screen_id=0x2af[^\r\n]*',
 'presenter_return':rb'FX3_AP89_SCREEN_CREATE phase=presenter_factory_return screen_id=0x2af[^\r\n]*',
 'power_seed':rb'POWER_ON_RECORD_OK[^\r\n]*',
 'upm_init':rb'FX3_UPM_RC=[^\r\n]*',
 'media_notify':rb'FX3_MEDIA_NOTIFY[^\r\n]*',
 'key_down':rb'FX3_KEY_INPUT_RECV step=\d+[^\r\n]*status=1[^\r\n]*',
 'key_up':rb'FX3_KEY_INPUT_RECV step=\d+[^\r\n]*status=0[^\r\n]*',
 'timer_snapshot':rb'FX3_TIMER_SNAPSHOT[^\r\n]*',
 'ui_gate_timer':rb'FX3_UI_GATE_SAMPLE id=11[^\r\n]*type=0x150000 source=0x830128[^\r\n]*',
 'deadline_or_reject':rb'FX3_OSD_(?:ALLOC|PAIR)_DEADLINE[^\r\n]*|FX3_MEDIA_BIND_REJECT[^\r\n]*|FX3_DATE99_REJECT[^\r\n]*',
}
out={}
for name,run in runs.items():
 data=(run/'serial.log').read_bytes(); first=re.search(patterns['screen_open'],data)
 if not first: raise RuntimeError('original shutdown screen absent: '+name)
 at=first.start(); rows={}
 for kind,pat in patterns.items():
  matches=list(re.finditer(pat,data))
  before=[m for m in matches if m.start()<at]
  after=[m for m in matches if m.start()>=at]
  def record(m):return None if m is None else {'serial_byte_range':[m.start(),m.end()],'raw':m[0].decode(errors='replace')}
  rows[kind]={'count_total':len(matches),'last_before_shutdown':record(before[-1] if before else None),
              'first_after_shutdown':record(after[0] if after else None)}
 out[name]={'run':str(run),'first_original_shutdown_serial_byte':at,'first_original_shutdown':first[0].decode(),
            'screen_name_source':'reports/2026-11-01-fx3-vm-resumed-repair/ap87-uud-queue-first-screen.md:44',
            'serial_order_not_host_or_guest_elapsed_time':True,'evidence':rows}
(root/'shutdown-trace.json').write_text(json.dumps(out,indent=2,ensure_ascii=False)+'\n')
print(root/'shutdown-trace.json')
