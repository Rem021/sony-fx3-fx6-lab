#!/usr/bin/env python3
"""Read-only single-run input/frame/power audit; no QMP or guest access."""
from pathlib import Path
import hashlib,json,re,sys
run=Path(sys.argv[1]).resolve()
out=Path(sys.argv[2]).resolve()
b=(run/'serial.log').read_bytes()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
events=[json.loads(line) for line in (run/'trial-input-events.jsonl').read_text().splitlines() if line]
readbacks=json.loads((run/'trial-step-readbacks.json').read_text())
assert len(events)==len(readbacks)==27
steps=[]
for index,(event,frame) in enumerate(zip(events,readbacks),1):
 key=event['key'];h=hex(key).encode()
 native={};synthetic={}
 for status in (1,0):
  matches=list(re.finditer(rb'FX3_KEY_INPUT_RECV step='+str(index).encode()+rb' key='+h+rb' status='+str(status).encode()+rb' [^\r\n]*native_result=0',b))
  assert len(matches)==1,(index,status,'native',len(matches))
  native[str(status)]={'count':1,'serial_byte':matches[0].start()}
  matches=list(re.finditer(rb'FX3_SYNTH_KEY step='+str(index).encode()+rb' key='+h+rb' status='+str(status).encode()+rb' [^\r\n]*monotonic_ns=(\d+)',b))
  assert len(matches)==1,(index,status,'synth',len(matches))
  synthetic[str(status)]={'count':1,'serial_byte':matches[0].start(),'guest_monotonic_ns':int(matches[0].group(1))}
 done=list(re.finditer(rb'FX3_KEY95_STEP_DONE step='+str(index).encode()+rb' key='+h+rb' [^\r\n]*one_down_one_up=1',b))
 assert len(done)==1,(index,'done',len(done))
 assert event['step']==frame['step']==index
 png=run/f'trial-step-{index:02d}-key-{key:03x}.png'
 assert png.is_file() and sha(png)==frame['PNG_sha256']
 decision=run/f'internal-observe-{index:02d}-decision.md'
 observed=run/f'internal-observe-{index:02d}.png'
 assert decision.is_file() and observed.is_file()
 steps.append({'step':index,'key':hex(key),'host_sent_monotonic':event['sent_monotonic'],
  'host_capture_monotonic':frame['host_monotonic'],
  'host_sent_to_capture_seconds':frame['host_monotonic']-event['sent_monotonic'],
  'guest_send':synthetic,'guest_native_recv':native,'guest_done_serial_byte':done[0].start(),
  'observed_png':str(observed),'observed_png_sha256':sha(observed),
  'decision_file':str(decision),'after_png':str(png),'after_png_sha256':sha(png),
  'render_nonuniform':frame['nonuniform_pixels'],'render_all_zero':frame['all_zero_pixels']})
notify=list(re.finditer(rb'FX3_POWER_NATIVE_NOTIFY seq=(\d+) ns=(\d+) tid=(\d+) point=(0x[0-9a-f]+) [^\r\n]*raw12=([0-9a-f]+)',b))
assert len(notify)==2
power=[{'seq':int(x[1]),'guest_monotonic_ns':int(x[2]),'tid':int(x[3]),'point':x[4].decode(),'raw12_hex':x[5].decode(),'serial_byte':x.start()} for x in notify]
assert power[0]['raw12_hex']==power[1]['raw12_hex']=='520000001100000002000000'
assert steps[-1]['guest_send']['0']['guest_monotonic_ns']<power[0]['guest_monotonic_ns']
receipt=json.loads((run/'receipt.json').read_text())
result={'schema':'fx3-27key-natural-apo1-continuous-navigation-v1','run':str(run),'candidate_sha256':receipt['candidate_sha256'],
 'runner_source_sha256':sha(run.parent.parent/'run_trial_v10_stale_review.py'),
 'serial_bytes':len(b),'serial_sha256':sha(run/'serial.log'),'key_steps':len(steps),'steps':steps,
 'power_native_records':power,
 'guest_last_key_up_to_power_ns':power[0]['guest_monotonic_ns']-steps[-1]['guest_send']['0']['guest_monotonic_ns'],
 'guest_first_key_up_to_power_ns':power[0]['guest_monotonic_ns']-steps[0]['guest_send']['0']['guest_monotonic_ns'],
 'host_first_key_sent_to_last_key_sent_seconds':steps[-1]['host_sent_monotonic']-steps[0]['host_sent_monotonic'],
 'read_only_power_setting_ui':{'page':'Setup > Power Setting Option','value':'Power Save Start Time 5 Min','other_row':'Auto Power OFF Temp. Standard','screenshot':str(run/'internal-preview-11.png'),'screenshot_sha256':sha(run/'internal-preview-11.png'),'semantic_scope':'visible UI only; UPM Backup ID mapping remains unknown; no value edited'},
 'unconsumed_step28_request':(run/'INTERNAL_STEP.json').is_file(),
 'receipt':{'stop_cause':receipt['stop_cause'],'early_stop_reason':receipt['early_stop_reason'],'qemu_pid':receipt['qemu_pid'],'qemu_exit':receipt['qemu_exit'],'process_reaped':receipt['process_reaped'],'pid_absent':receipt['PID_absent'],'API16_restored':receipt['cleanup']['API16_restored'],'restore_reason':receipt['cleanup']['restore103']['reason'],'inputs_unchanged':receipt['inputs_unchanged'],'locks':receipt['locks']},
 'interpretation':'Native OFF_BY_APO1 appeared about 11.87 guest seconds after step27 up while 27 meaningful menu keys were received and rendered. This rules out five minutes of no host input immediately before shutdown, but does not by itself identify which original activity-reset path is missing or prove the exact timer origin. Guest and host monotonic intervals are kept separate.'}
out.write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n')
print('PASS',len(steps),'guest last up to APO seconds',result['guest_last_key_up_to_power_ns']/1e9,'serial SHA',result['serial_sha256'])
