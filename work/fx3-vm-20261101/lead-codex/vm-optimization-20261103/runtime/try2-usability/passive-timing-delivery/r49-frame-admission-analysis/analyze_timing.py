#!/usr/bin/env python3
"""r49 v2: native phases.first_kinds + r41 command-entry parser + approximate HAR mapping.

No runtime/browser/VM contact. Boundaries are explicit; later 6082916 is not used
for phase/cutoff. Boot guest-entry is not the same as guest-command entry.
"""
import datetime,json,statistics
from pathlib import Path
DEL=Path('/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/lead-codex/vm-optimization-20261103/runtime/try2-usability/passive-timing-delivery')
RUN=DEL/'r47-runtime-integration-candidate/run-inputs/f9c618eedbad'; OUT=DEL/'r49-frame-admission-analysis/receipts'
N=Path(json.loads((RUN/'runtime.json').read_text())['run'])
HAR=json.loads((RUN/'cleanup-calls/dc3a1077-4b0d-4bff-8351-ff77d26c582b/traffic.har').read_text())
POSTS={e['request']['url'].split('/api/')[-1]:e['startedDateTime'] for e in HAR['log']['entries'] if e['request']['method']=='POST' and '/api/' in e['request']['url']}
A=json.loads((OUT/'startup-observation-audit.json').read_text()); PI=json.loads((OUT/'parser-invocation.json').read_text())
PSTART=json.loads((OUT/'command-entry-parse-startup-3490401.json').read_text()); PALL=json.loads((OUT/'command-entry-parse-6077228.json').read_text())
H=json.loads((OUT/'har-transitions.json').read_text())
ff_clock=json.loads((RUN/'FIRST-FRAME-CLOCK.json').read_text()); ff_pass=json.loads((RUN/'FIRST-FRAME-PASS.json').read_text())
standby=json.loads((RUN/'initial-standby/capture-result.json').read_text()); pre=json.loads((RUN/'PRESTART-READY.json').read_text())
rec=json.loads((N/'receipt.json').read_text()); arg=json.loads((RUN/'ACTUAL-RUNNING-ARGV.json').read_text()); cmd=json.loads((N/'command.json').read_text()); qmp=json.loads((N/'startup-qmp-timing.json').read_text())
def dt(s):return datetime.datetime.fromisoformat(s.replace('Z','+00:00'))
def diff(a,b):return (dt(b)-dt(a)).total_seconds()
def stats(records):
 dur=[r['duration_ns'] for r in records if r.get('duration_status')=='known']
 return {'known_count':len(dur),'min_ns':min(dur) if dur else None,'median_ns':statistics.median(dur) if dur else None,'max_ns':max(dur) if dur else None}
def attempts():
 out=[]
 for a in H['attempts']:
  out.append({'case':a['case'],'identities':a['identity'],'clicked_frame':a['clicked_frame'],'preflight_status_frame':a['preflight_status']['frame'],
   'last_tick_utc':a['last_status_before']['utc'],'click_snapshot_utc_approx':a['click_snapshot_utc_approx'],'fresh_preflight_utc':a['preflight_utc'],
   'last_tick_to_click_ms_approx':a['last_tick_to_click_ms_approx'],'click_to_preflight_ms_approx':a['click_to_preflight_ms_approx'],
   'last_tick_to_preflight_ms_approx':a['last_tick_to_preflight_ms_approx'],'timing_status':a['timing_status'],
   'frame_change_window':a['frame_change_window'],'sequence_note':a['sequence_note'],'sequence_is_direct_gate_term':False,
   'failing_frame_terms':a['failing_frame_terms'],'outcome':a['outcome']})
 return out
value={'schema':'fx3-r49-command-entry-timing-v2','source_run':str(RUN),'native_run':str(N),
 'startup_observation_audit':A,
 'stage_boundaries':{'phases_first_kinds':A['phases_first_kinds'],'startup_phase':'[0,6077228)','startup_first_qualified_evaluation_complete':'3490401','first_cleanup':'6077228','after_cleanup':'6260972',
  'cleanup_phase':'[6077228,6260972]','later_cleanup_serial_bytes_before_cleanup':A['later_cleanup_receipt_serial_bytes_before_cleanup'],'later_6082916_used':False,
  'boot_guest_entry':'unknown: phases.startup.serial_offset=0 is host observation start, not an exact guest-entry timestamp'},
 'command_entry':{'parser_invocation':str(OUT/'parser-invocation.json'),'parser_sha256':PI['parser_sha256'],'serial_sha256':PI['serial_sha256'],
  'clock_domain':PALL['clock_domain'],
  'cutoffs':PI['cutoffs'],'startup_parse':PSTART,'precleanup_parse':PALL,
  'startup_stats':stats(PSTART['records']),'precleanup_stats':stats(PALL['records']),
  'examples':[{k:r.get(k) for k in ('seq','op','entry_ns','end_ns','duration_ns','duration_status','gap_status','reasons')} for r in PALL['records'][:4]],
  'unknown_counts':PALL['unknown_reason_counts'],'known_same_thread_gaps':PALL['known_same_thread_gaps'],
  'ignored_complete_other_lines':PALL['ignored_complete_other_lines'],
  'scope':'guest CLOCK_MONOTONIC command entry->return marks only; same-thread adjacent gaps may include unobserved activity; no CPU/FIFO/HTTP speed inference',
  'distinction':'guest-command entry = FX3_GPE104_CMD_RETURN entry_ns; this is NOT boot guest-entry; boot guest-entry exact timestamp remains unknown'},
 'observed_first_frame':{'api_start_post_utc':POSTS.get('start'),'api_stop_post_utc':POSTS.get('stop'),'api_final_ack_post_utc':POSTS.get('final-ack'),
  'prestart_ready_utc':pre.get('UTC'),'first_frame_clock':ff_clock,'first_frame_pass':ff_pass,
  'start_monotonic_to_pass_s':ff_pass['host_ns']/1e9-ff_clock['start_monotonic'],
  'first_frame_clock_to_pass_s':diff(ff_clock['UTC'],ff_pass['UTC']),
  'api_start_post_to_first_frame_clock_s':diff(POSTS['start'],ff_clock['UTC']),
  'api_start_post_to_first_frame_s':diff(POSTS['start'],ff_pass['UTC']),
  'limit_seconds':180,'under_limit':(ff_pass['host_ns']/1e9-ff_clock['start_monotonic'])<180,
  'initial_standby':{'utc':standby.get('UTC'),'host_ns':standby.get('host_ns'),'before_performance_ms':standby['before']['performance_ms'],'after_performance_ms':standby['after']['performance_ms'],'firmware':standby.get('firmware'),'screenshot_sha256':standby.get('screenshot_sha256')}},
 'api_start_to_stop_s':diff(POSTS['start'],POSTS['stop']),'api_stop_to_final_ack_s':diff(POSTS['stop'],POSTS['final-ack']),
 'attempts':attempts(),
 'native_receipt':{'stop_cause':rec.get('stop_cause'),'duration_seconds':rec.get('duration_seconds'),'maximum_seconds':rec.get('maximum_seconds'),'key_steps':rec.get('key_steps'),'menu_verified':rec.get('menu_verified'),'qemu_exit':rec.get('qemu_exit'),'process_reaped':rec.get('process_reaped'),'PID_absent':rec.get('PID_absent'),'API16_restored':rec.get('cleanup',{}).get('API16_restored'),'quit_sent':rec.get('cleanup',{}).get('quit_sent'),'serial_bytes_before_cleanup':rec.get('cleanup',{}).get('serial_bytes_before_cleanup')},
 'actual_running_argv':{'pid':arg.get('pid'),'qemu_sha256':arg.get('qemu_sha256'),'ps_command':arg.get('ps_command'),'utc':arg.get('UTC'),'host_ns':arg.get('host_ns')},
 'command_json':{'cwd':cmd.get('cwd'),'candidate':cmd.get('candidate'),'candidate_sha256':cmd.get('candidate_sha256'),'args':cmd.get('args'),'seconds':cmd.get('seconds'),'smp':cmd.get('smp'),'tcg_thread':cmd.get('tcg_thread'),'icount_profile':cmd.get('icount_profile')},
 'startup_qmp_timing':qmp,
 'har_clock_mapping':H['clock_mapping'],
 'boundaries':{'exact_api_start_post':'known','exact_first_frame_pass':'known','exact_guest_command_entry':'parsed guest CLOCK_MONOTONIC entry_ns, not a boot/guest-entry timestamp','exact_boot_guest_entry':'unknown','phases_first_kinds':'known (native startup-observation.json)','first_startup_qualified_offset':'3490401','first_cleanup_offset':'6077228','after_cleanup_offset':'6260972','later_6082916':'present in cleanup receipt but NOT used for phase/cutoff','interaction_cutoff':'phase first cleanup 6077228; early/late boundary beyond retained phases unknown','har_time_mapping':'approximate wall-clock epoch mapping; not same monotonic; 1ms values not exact','frame_change_window':'between last old frame observation and fresh preflight read; cannot be bounded to after click'},
 'limitations':['single failed run; step1 only','guest boot-entry exact timestamp unknown','phases.first_kinds are known at 0/6077228/6260972; no further phase stream beyond retained first_kinds/recent; no later cleanup serial substitution','no CPU/FIFO/HTTP latency inference','no second VM/start']}
(OUT/'command-entry-timing.json').write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'first_startup_qualified':3490401,'first_cleanup':6077228,'after_cleanup':6260972,'later_6082916_used':False,
 'startup_command_entry':PSTART['known_durations'],'precleanup_command_entry':PALL['known_durations'],'unknown':PALL['unknown_reason_counts'],
 'first_frame_wait_s':value['observed_first_frame']['start_monotonic_to_pass_s'],'attempts':[{'case':a['case'],'last_tick_to_click_ms_approx':a['last_tick_to_click_ms_approx'],'click_to_preflight_ms_approx':a['click_to_preflight_ms_approx'],'sequence_direct_gate':a['sequence_is_direct_gate_term']} for a in value['attempts']],'receipt':str(OUT/'command-entry-timing.json')},ensure_ascii=False,indent=2))
