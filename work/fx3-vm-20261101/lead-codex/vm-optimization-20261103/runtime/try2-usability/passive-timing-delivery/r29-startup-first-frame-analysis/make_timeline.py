#!/usr/bin/env python3
"""Derive compact timeline from the pinned r29 evidence; no runtime access."""
import json
from pathlib import Path
P=Path(__file__).resolve().parent
out={'clock_rules':{
 'host_relative':'original FIRST-FRAME-CLOCK.start_monotonic; first-pixel stamp is host conversion/publication observation, not guest emission/compositor',
 'qmp_relative':'journal elapsed_seconds since Popen; separate origin from FIRST-FRAME-CLOCK',
 'guest_ns':'explicit clock_id=1 in serial; never substitute preceding printk bracket or host file mtime',
 'timer':'original TIMER_ENTRY input_time in ms; retain as its own application domain; matching ~clock1 values does not establish a universal conversion',
 'browser':'last saved poll only; first onload instant not logged'},'runs':{}}
for n in ['r26','r26b','r28']:
 e=json.loads((P/(n+'-EVIDENCE.json')).read_text());s=e['summary'];m=e['serial_markers'];q=e['qmp_control_milestones']
 src=s['run']+'/serial.log'
 def row(rec):
  return {'source':src,**{k:rec[k] for k in ['byte_offset','LF_line','fields','before_original_cleanup_serial_boundary']}}
 out['runs'][n]={
  'Start_POST':e['http']['Start'],
  'QMP_handshake_s':s['startup_qmp']['total_elapsed_seconds'],
  'first_cont_Popen_relative_s':next(x['Popen_relative_request_seconds'] for x in q if x['command']=='cont'),
  'pre_AP_Backup_read_Popen_relative_s':next(x['Popen_relative_request_seconds'] for x in q if 'backup-native-load-before-AP.bin' in x['command_line']),
  'screen_transitions': [row(x) for x in e['screens_first4']],
  'first_timer':row(m['FX3_TIMER_ENTRY ']['first'][0]),
  'first_low16_1004':row(m['UI_WIRE_low16_1004']['first'][0]),
  'first_Fill':row(m['FX3_UI_FILL_EXEC ']['first'][0]),
  'first_guest_commit':row(m['FX3_OSD102_COMMIT ']['first'][0]),
  'first_host_pixels_relative_s':s['first_host_pixels_since_clock_seconds'],
  'frame_used_for_ready_capture_relative_s':s['frame_used_for_ready_capture_since_clock_seconds'],
  'first_HTTP_frame':e['http']['first_status_frame'],
  'first_HTTP_ready':e['http']['first_status_ready'],
  'first_frame_GET':e['http']['first_frame_GET'],
  'saved_browser_poll':s['operator_check'],
  'pass_or_failure_relative_s':s['operator_pass_or_timeout_since_clock_seconds'],
  'Stop_POST':e['http']['Stop'],
  'render_at_end':{k:s['receipt'][k] for k in ['standby_ready','render_pass','render_valid_at_end','render_observation_ok']}}
r=e # loop final r28
j=json.loads((P/'r28-EVIDENCE.json').read_text())
z=j['ring']['last_zero_header']['host_monotonic'];a=j['ring']['first_positive_header']['host_monotonic']
# End tool host timestamp is the raw process receipt, not HAR realtime.
f=Path(j['summary']['operator'])/'End-original-button-process.json'
end=json.loads(f.read_text())
out['r28_end_boundary']={'last_observed_zero_header_host_monotonic':z,
 'first_observed_positive_header_host_monotonic':a,
 'End_tool_start_host_monotonic':end['start']['host_ns']/1e9,
 'first_pixel_publication_host_monotonic':j['ring']['first_nonuniform']['host_monotonic'],
 'claim':'The header observations straddle End; exact guest commit relative to End is unknown; no assertion that End caused rendering',
 'additional_input':str(f)}
(P/'TIMELINE.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(out['r28_end_boundary'],indent=2))
