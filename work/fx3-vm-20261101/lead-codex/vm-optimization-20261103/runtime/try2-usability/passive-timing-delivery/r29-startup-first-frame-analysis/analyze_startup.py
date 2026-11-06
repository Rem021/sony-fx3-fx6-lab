#!/usr/bin/env python3
"""Read-only r29 analysis. No runtime imports, subprocess, network or service.
Only output files beside this script; every consumed byte source is hashed.
"""
import bisect, collections, datetime as dt, hashlib, json, re, statistics, struct
from pathlib import Path

OUT = Path(__file__).resolve().parent
DEL = OUT.parent
TRY = DEL.parent
PROJECT = Path('/Volumes/KAFU2T/AI/Projects/Mac')
RUNS = {'r28': ('f7903939','r28-vm-cb12b6256797'),
        'r26': ('740bafa8','r26-vm-49f0c1c3663b'),
        'r26b': ('45304842','r26b-vm-93b3e243da6f')}
INPUTS = {}

def read(p):
    p=Path(p).resolve(); b=p.read_bytes()
    row={'path':str(p),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
    if str(p) in INPUTS: assert INPUTS[str(p)]==row, f'input changed during analysis: {p}'
    INPUTS[str(p)]=row
    return b

def jread(p): return json.loads(read(p))
def save(name,x): (OUT/name).write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def fields(s): return dict(re.findall(r'\b([A-Za-z_][A-Za-z_0-9]*)=([^\s]+)',s))
def utc(s): return dt.datetime.fromisoformat(s.replace('Z','+00:00')).timestamp()
def delta_har(s,start): return utc(s)-start

def parse_run(label,rid,opname):
    run=TRY/'runs'/('v25gate-n64-r17-'+rid); op=DEL/opname
    c=jread(run/'command.json'); receipt=jread(run/'receipt.json'); q=jread(run/'qmp.json')
    clock=jread(op/'FIRST-FRAME-CLOCK.json'); base=clock['start_monotonic']
    raw=read(run/'serial.log'); lf=[m.start() for m in re.finditer(b'\n',raw)]
    clean=jread(run/'trial-cleanup-phase.json'); boundary=clean['serial_bytes_before_cleanup']
    def records(token):
        rs=[]
        for m in re.finditer(re.escape(token.encode()),raw):
            end=raw.find(b'\n',m.start()); end=len(raw) if end<0 else end
            s=raw[m.start():end].decode(errors='replace').rstrip('\r')
            rs.append({'byte_offset':m.start(),'LF_line':bisect.bisect_left(lf,m.start())+1,
                       'before_original_cleanup_serial_boundary':m.start()<boundary,
                       'fields':fields(s),'text':s})
        return rs
    tokens=['FX3_GPE104_DYNAMIC_ENTER ','FX3_AP89_SCREEN_OPEN_ENTER ','FX3_AP89_SCREEN_CREATE ',
            'FX3_UI_GATE_BOUND ','FX3_TIMER_BOUND ','FX3_UI_CONFIG_DONE ','FX3_TIMER_ENTRY ',
            'FX3_TIMER_ID ','FX3_TIMER_INFO ','FX3_UI_FILL_EXEC ','FX3_UI_FILL_RETURN ',
            'FX3_GPE_CMD op=','FX3_OSD_OWNER_GUI ','FX3_OSD_OWNER_CURRENT ',
            'FX3_OSD_HEADLESS_VALIDATE ','FX3_OSD_HEADLESS_COPY ','FX3_OSD102_COMMIT ',
            'FX3_AP101_NATIVE_LOAD_READBACK_WINDOW_BEGIN','FX3_AP_NATURAL_BOOTIN_BEGIN']
    markers={t:{'count':len(rs),'first':rs[:1],'last':rs[-1:]} for t in tokens if (rs:=records(t))}
    screens=records('FX3_AP89_SCREEN_OPEN_ENTER ')
    wire=records('FX3_UI_WIRE ')
    timerwire=[r for r in wire if r['fields'].get('tag1') and int(r['fields']['tag1'],0)&65535==0x1004]
    markers['UI_WIRE_low16_1004']={'count':len(timerwire),'first':timerwire[:1],
                                'semantics':'low16 opcode only; no assertion about high halfword schema'}
    gates={}
    for i in range(12):
        rs=records(f'FX3_UI_GATE_SAMPLE id={i} ')
        vals=[int(r['fields']['decision_a18']) for r in rs if r['fields'].get('decision_a18','').isdecimal()]
        signed=[v-(1<<32) if v&(1<<31) else v for v in vals]
        gates[str(i)]={'logged_records':len(rs),'first':rs[:1],'last':rs[-1:],
                      'sampled_signed_decision_min':min(signed) if signed else None,
                      'sampled_signed_decision_max':max(signed) if signed else None}
    cb=read(run/'ui-gate-counters.bin'); h=struct.unpack_from('<8Q',cb)
    assert h[0]==0x3145544147335846 and h[1]==2 and h[2] in (0,1)
    v=struct.unpack_from('<98Q',cb,0x100+h[2]*0x1000)
    counters={'header':h,'count0_to11':v[:12],'peak_gate':v[65],'gate_hist_0_1_2_3to10_11to100_gt100':v[73:79],
        'system_false':v[79],'backlog_skip':v[80],'time_skip':v[81],'time_pass':v[82],
        'dequeue_total':v[83],'timer_dequeue':v[84],'a12_nonzero':v[85],'a13_nonzero':v[86],
        'object_mismatch':v[96],'root_change':v[97],
        'scope':'original End paused snapshot, N64 published bank may lag and has no exact final-freshness guarantee; fields copied individually, not atomic execution snapshot; controls include later one key; not startup-only'}
    ring=jread(run/'osd-ring-readback.json'); frames=ring['frames']; polls=ring['polls']
    diag=jread(run/'osd-ring-final-diag.json'); native=jread(run/'ap101-native-load-readback.json')
    hh=jread(op/'traffic.har')['log']['entries']; statuses=[]
    for ix,e in enumerate(hh):
        if e['request']['url'].split('?')[0].endswith('/status'):
            try: st=json.loads(e['response']['content']['text'])
            except (ValueError,KeyError): continue
            statuses.append((ix,e,st))
    def erow(ix,e,st=None):
        z={'HAR_entry_index':ix,'request_start_UTC':e['startedDateTime'],'duration_ms':e['time'],
           'path':e['request']['url'].split('/')[-1], 'HTTP_status':e['response']['status']}
        if st is not None:
            z.update({k:st.get(k) for k in ['phase','ready','render_valid','busy','steps','review_required','launch_status']})
            z['frame']=None if not st.get('frame') else {k:st['frame'].get(k) for k in ['sequence','PNG_sha256','host_monotonic','content_generation']}
        return z
    start_e=next((i,e) for i,e in enumerate(hh) if e['request']['method']=='POST' and e['request']['url'].endswith('/start'))
    startUTC=utc(start_e[1]['startedDateTime'])
    firstframe=next((x for x in statuses if x[2].get('frame')),None)
    firstready=next((x for x in statuses if x[2].get('ready')),None)
    stop=next(((i,e) for i,e in enumerate(hh) if e['request']['method']=='POST' and e['request']['url'].endswith('/stop')),None)
    last_no_frame=next((x for x in reversed(statuses) if not x[2].get('frame') and (firstframe is None or x[0]<firstframe[0])),None)
    frame_gets=[(i,e) for i,e in enumerate(hh) if e['request']['url'].split('?')[0].endswith('/frame.png')]
    http={'Start':erow(*start_e),'Stop':erow(*stop) if stop else None,
          'first_status_frame':erow(*firstframe) if firstframe else None,
          'last_status_no_frame':erow(*last_no_frame) if last_no_frame else None,
          'first_status_ready':erow(*firstready) if firstready else None,
          'first_frame_GET':erow(*frame_gets[0]) if frame_gets else None,
          'status_count':len(statuses),'ready_true_count':sum(bool(x[2].get('ready')) for x in statuses),
          'POST_counts':dict(collections.Counter(e['request']['url'].split('/')[-1] for e in hh if e['request']['method']=='POST')),
                    'clock_semantics':'HAR timestamps are request start, responses/delivery/compositor distinct; no screenshot/model receive inference'}
    reqs=[(i,x) for i,x in enumerate(q) if 'request' in x]
    interesting=[]
    for i,x in reqs:
        req=x['request']; line=req.get('arguments',{}).get('command-line','')
        if req['execute'] in ['stop','cont'] or 'backup-native-load-before-AP.bin' in line or 'osd-ring-final.bin' in line:
            interesting.append({'qmp_entry_index':i,'request_id':req['id'],'command':req['execute'],
                'command_line':line,'Popen_relative_request_seconds':x['elapsed_seconds']})
    headerreq=[{'qmp_entry_index':i,'request_id':x['request']['id'],
                'Popen_relative_request_seconds':x['elapsed_seconds']} for i,x in reqs
               if 'osd-ring-header-live.bin' in x['request'].get('arguments',{}).get('command-line','')]
    matched=0
    for hreq in headerreq:
        rs=[x['response'] for x in q if x.get('response',{}).get('id')==hreq['request_id']]
        assert len(rs)==1 and rs[0].get('return')==''
        matched+=1
    pause=None; pauses=[]
    for row in q:
        e=row.get('response',{});ts=e.get('timestamp')
        if not ts or e.get('event') not in ['STOP','RESUME']:continue
        stamp=ts['seconds']*1000000+ts['microseconds']
        if e['event']=='STOP':assert pause is None;pause=stamp
        elif pause is not None:
            pauses.append({'stop_unix_us':pause,'resume_unix_us':stamp,'duration_us':stamp-pause});pause=None
    stop_us=round(utc(stop[1]['startedDateTime'])*1000000) if stop else None
    pause_accounting={'completed_pairs':pauses,'total_us':sum(x['duration_us'] for x in pauses),
        'completed_before_End_POST_us':sum(x['duration_us'] for x in pauses if stop_us and x['resume_unix_us']<stop_us),
        'terminal_unpaired_STOP_us':pause,'scope':'QMP event realtime microseconds, excluding initial -S, scheduling stalls and possible realtime jumps'}
    ring_summary={'first_nonuniform':frames[0] if frames else None,'valid_header_polls':len(polls),
       'first_valid_header':polls[0] if polls else None,'first_positive_header':next((x for x in polls if x['global_words'][4]),None),
       'last_zero_header':next((x for x in reversed(polls) if x['global_words'][4]==0),None),
       'rejected_torn_count':len(ring['rejected_torn_samples']), 'header_request_count':len(headerreq),
       'header_matched_empty_success_responses':matched,
       'header_request_median_gap_seconds':statistics.median(b['Popen_relative_request_seconds']-a['Popen_relative_request_seconds'] for a,b in zip(headerreq,headerreq[1:])),
       'header_request_first':headerreq[:1],'header_request_last':headerreq[-2:],
       'header_requests_max_gap_seconds':max((b['Popen_relative_request_seconds']-a['Popen_relative_request_seconds'] for a,b in zip(headerreq,headerreq[1:])),default=0),
       'diag':{k:diag[k] for k in ['total_accepted_events','dropped_busy_writer_events','tail_first_serial','invalid_or_torn_slots','readback_quiesced']},
       'diag_first_commit':next((x for x in diag['rows'] if x['event']=='commit'),None),
       'diag_tail_scope':'successful sample tails overwrite early events; first guest commit there is not the first-ever commit'}
    poll=jread(op/'first-frame-poll-process.json')
    passpath=op/'FIRST-FRAME-PASS.json'; failpath=op/'STARTUP-FAILURE.json'
    result=jread(passpath if passpath.exists() else failpath)
    before=jread(op/'INPUTS-BEFORE.json'); after=jread(op/'INPUTS-AFTER.json')
    args=c['args']; normalized=[a.replace(str(run),'<RUN>') for a in args]
    platform=[]
    relevant=[args[0],args[args.index('-kernel')+1],c['candidate']]
    relevant += [a.split('file=',1)[1].split(',addr=',1)[0] for a in args if a.startswith('loader,file=')]
    for path in relevant:
        bmatch=[x for xs in before['groups'].values() for x in xs if x.get('path')==path]
        amatch=[x for xs in after['groups'].values() for x in xs if x.get('path')==path]
        assert bmatch and amatch and all(x.get('match') for x in bmatch+amatch)
        hashes={x['actual'] for x in bmatch+amatch};assert len(hashes)==1
        platform.append({'path':path,'sha256':hashes.pop(),'recorded_before_after_pins_match':True})
    cmdproof={'normalized_launch_args':normalized,'model_env':c['model_env'],'smp':c['smp'],'tcg_thread':c['tcg_thread'],
              'icount_profile':c['icount_profile'],'fixed_inputs_from_actual_run_pins':platform,
              'actual_Popen_binding':'runner writes command.json then subprocess.Popen(args,cwd=run,env=env); QMP actual CPU types checked separately; r28 lacks live ps argv capture'}
    if (op/'ACTUAL-RUNNING-ARGV.json').exists(): cmdproof['running_argv_capture']=jread(op/'ACTUAL-RUNNING-ARGV.json')
    cpu=next(x['response']['return'] for x in q if isinstance(x.get('response',{}).get('return'),list) and x['response']['return'] and 'cpu-index' in x['response']['return'][0])
    cmdproof['actual_QMP_cpu_types']=[x['qom-type'] for x in cpu]
    assert len(cpu)==4 and all(x['qom-type']=='cortex-a35-arm-cpu' for x in cpu)
    startq=jread(run/'startup-qmp-timing.json')
    summary={'label':label,'run':str(run),'operator':str(op),'first_frame_clock':clock,
        'operator_result':result,'operator_check':poll,
        'first_host_pixels_since_clock_seconds':frames[0]['host_monotonic']-base,
        'operator_pass_or_timeout_since_clock_seconds':result['host_ns']/1e9-base,
        'frame_used_for_ready_capture_since_clock_seconds':jread(run/'trial-standby-ready.json')['host_monotonic']-base if (run/'trial-standby-ready.json').exists() else None,
        'first_HTTP_frame_since_Start_POST_seconds':delta_har(firstframe[1]['startedDateTime'],startUTC) if firstframe else None,
        'first_HTTP_ready_since_Start_POST_seconds':delta_har(firstready[1]['startedDateTime'],startUTC) if firstready else None,
        'receipt':{k:receipt[k] for k in ['created_utc','duration_seconds','standby_ready','render_pass','render_valid_at_end','health_pass','render_observation_ok','key_steps','stop_cause','host_observer_error','qemu_exit','process_reaped','inputs_unchanged']},
        'serial_cleanup_boundary':boundary,'startup_qmp':startq,
        'original_backup_readback':{k:native[k] for k in ['before_AP_bootin_marker','native_file_seen_and_module_load0','file_sha256','sha256']},
        'original_observer_sources':receipt['observer_source_snapshot']}
    save(label+'-EVIDENCE.json',{'summary':summary,'platform':cmdproof,'http':http,'ring':ring_summary,
       'qmp_pause_accounting':pause_accounting,'qmp_control_milestones':interesting,'serial_markers':markers,'screens_first4':screens[:4],
       'UI_gates':gates,'UI_original_paused_published_counters':counters})
    return summary,cmdproof,markers,counters

def main():
    results={n:parse_run(n,*ids) for n,ids in RUNS.items()}
    ref=results['r26']; proof={}
    for n,(s,p,m,c) in results.items():
        proof[n]={'normalized_args_equal_r26':p['normalized_launch_args']==ref[1]['normalized_launch_args'],
                  'model_env_equal_r26':p['model_env']==ref[1]['model_env'],
                  'fixed_pins_equal_r26':p['fixed_inputs_from_actual_run_pins']==ref[1]['fixed_inputs_from_actual_run_pins'],
                  'observer_sources_equal_r26':s['original_observer_sources']==ref[0]['original_observer_sources']}
        assert all(proof[n].values())
    # Read exact relevant code; keep small excerpts and pin all consumed sources.
    requests={
      DEL/'r28-first-observation-candidate/run_trial_r24_review_snapshot.py':[(386,393),(439,448),(476,484),(521,524),(548,591),(762,774),(779,821),(935,982)],
      DEL/'v25-r21-recovery-integration/trial_ring_cached.py':[(48,69),(128,141)],
      DEL/'r28-first-observation-candidate/trial_web_r24_review_snapshot.py':[(1,30)],
      DEL/'v25-r21-recovery-integration/trial_web_v22_navigation_review.py':[(65,99),(341,345),(387,405)],
      DEL/'v25-r21-recovery-integration/trial_log_v4_mss.py':[(35,47)],
      DEL/'v25-r21-recovery-integration/trial_health_v2.py':[(1,12)],
      DEL/'v25-r15-snapshot-tail/fx3-ui-gate-v15.c':[(6,6),(33,35),(134,146)],
      DEL/'r9-ui-startup-offline/app-main-gate.txt':[(1,200)],
      DEL/'r9-ui-startup-offline/app-update-and-draw.txt':[(1,170)],
    }
    excerpts=[]
    for path,ranges in requests.items():
        lines=read(path).decode(errors='replace').splitlines()
        for a,b in ranges:
            excerpts.append({'path':str(path),'first_line':a,'last_line':min(b,len(lines)),
                             'lines':[f'{i}: {lines[i-1]}' for i in range(a,min(b,len(lines))+1)]})
    # Additional contextual inputs actually consulted, kept as hashes only.
    for path in [DEL/'r29-startup-first-frame-task.txt', DEL/'r9-ui-startup-offline/REPORT.md',
                 DEL/'r9-ui-startup-offline/analyze_startup.py',
                 PROJECT/'work/fx3-vm-20261101/menu-repair-01/runtime/helpers/fx3-ui-gate-v11.c',
                 DEL/'v25-r15-snapshot-tail/BUILD.json',DEL/'r16-fixed-slot-guests/guest-N64/candidate.json']:
        read(path)
    # Pin current platform bytes independently, using only the five actually launched paths.
    current=[]
    for x in ref[1]['fixed_inputs_from_actual_run_pins']:
        b=read(x['path']); actual=hashlib.sha256(b).hexdigest(); assert actual==x['sha256']
        current.append(dict(x,current_analysis_sha256=actual))
    candidate=jread(DEL/'r16-fixed-slot-guests/guest-N64/candidate.json')
    member=candidate['fixed_layout_diagnostic_contract']['member']
    slot=candidate['fixed_layout_diagnostic_contract']['padded_slot_sha256']
    helper_binding={}
    for n,(rid,opname) in RUNS.items():
        run=TRY/'runs'/('v25gate-n64-r17-'+rid)
        audit=jread(run/'cpio-audit.json'); row=next(x for x in audit['members'] if x['path']==member)
        assert row['sha256']==slot
        app=next(x for x in audit['members'] if x['path']=='usr/lib/appFw.so')
        assert app['sha256']=='545c5053a74e04ffbf2bbaaf80f558092dd545ed2298b2395ca547dbba58290f'
        helper_binding[n]={'ui_helper':row,'original_appFw':app}
        for f in ['trial-session.json','trial-frame.json']:read(run/f)
        for f in ['End-original-button-process.json','Start-original-button-process.json']:read(DEL/opname/f)
    for p in [DEL/'r29-coordinator-qmp-pause-accounting.json',DEL/'r29-coordinator-header-poll-cadence.json',DEL/'r16-r15-guest-SOURCE-SHA256SUMS']:
        read(p)
    source_manifest=read(DEL/'r16-r15-guest-SOURCE-SHA256SUMS').decode()
    sm={line.split('  ',1)[1]:line.split('  ',1)[0] for line in source_manifest.splitlines()}
    source_path=DEL/'v25-r15-snapshot-tail/fx3-ui-gate-v15.c'
    source_hash=hashlib.sha256(read(source_path)).hexdigest()
    assert source_hash==sm['v25-r15-snapshot-tail/fx3-ui-gate-v15.c']
    build=jread(DEL/'v25-r15-snapshot-tail/BUILD.json')
    assert build['variants']['N64']['sha256']==candidate['fixed_layout_diagnostic_contract']['helper_raw_sha256']
    save('PLATFORM-AND-HELPER-BINDING.json',{'current_platform_check_UTC':dt.datetime.now(dt.timezone.utc).isoformat(),
        'current_bytes_match_historical_pins':current,'guest_member':helper_binding,'actual_ui_source_sha256':source_hash,'source_manifest_matches':True,'raw_build_matches_candidate':True,
        'provenance':candidate['fixed_layout_diagnostic_contract'],
        'scope':'Historical input before/after pin receipts plus current read hashes, not a new VM or re-execution; padded member identity per actual-run CPIO audits'})
    save('CODE-EVIDENCE.json',excerpts)
    save('COMPARISON.json',{'runs':{n:r[0] for n,r in results.items()},'unchanged_platform_and_startup_code':proof,
        'boundaries':['host monotonic vs guest clock_id1 vs printk vs timer input_time are distinct domains',
                      'N64 counters are original paused published-bank evidence, not full causal transaction history',
                      'late pixels published during stopping never retroactively satisfy standby_ready',
                      'no service/browser/VM/runtime import or candidate implemented in this analysis']})
    stable=[]
    for row in INPUTS.values():
        b=Path(row['path']).read_bytes(); same=len(b)==row['bytes'] and hashlib.sha256(b).hexdigest()==row['sha256']
        stable.append(dict(row,unchanged_after_analysis=same)); assert same,row['path']
    save('INPUTS.json',{'captured_UTC':dt.datetime.now(dt.timezone.utc).isoformat(),'count':len(stable),
          'current_r28_seal_scope':'operator may still be sealing; only named raw files consumed and rechecked, no blanket final manifest assertion', 'files':stable})
    print(json.dumps({'input_count':len(stable),'platform_equal':True,'input_stable':True,
      'summary':{n:{k:v for k,v in r[0].items() if k in ['first_host_pixels_since_clock_seconds','operator_pass_or_timeout_since_clock_seconds','frame_used_for_ready_capture_since_clock_seconds']} for n,r in results.items()}},indent=2))

if __name__=='__main__':main()
