#!/usr/bin/env python3
"""Read frozen FX3 sources and completed logs; write only HERE. No runtime action."""
from pathlib import Path
import collections, datetime, hashlib, json, plistlib, re, struct, subprocess

HERE = Path(__file__).resolve().parent
ROOT = next(x for x in HERE.parents if x.name == 'Mac')
DEL = HERE.parent
TRY = HERE.parents[1]
H = ROOT/'work/fx3-vm-20261101/menu-repair-01/runtime/helpers'
LIB = H.parents[1]/'original-uipc/ap-projection/regular-files/usr/lib'
INPUTS = {}


def sha(p):
    with p.open('rb') as f: return hashlib.file_digest(f,'sha256').hexdigest()


def read(p):
    p = p.resolve(); b = p.read_bytes()
    INPUTS[str(p.relative_to(ROOT))] = {'bytes':len(b), 'sha256':hashlib.sha256(b).hexdigest()}
    return b


def js(p): return json.loads(read(p))


def fields(b):
    return dict(re.findall(r'\b([A-Za-z_][A-Za-z_0-9]*)=([^\s]+)',b.decode(errors='replace')))


def rec(l, i, off, tok):
    at = l.index(tok)
    return {'LF':i, 'byte_offset':off+at, 'fields':fields(l[at:]),
            'text':l[at:].decode(errors='replace').rstrip('\r')}


def bank(b):
    h = struct.unpack_from('<8Q',b)
    assert h[0] == 0x3145544147335846 and h[1] == 2 and h[2] in [0,1]
    out=[]
    names=['peak_all','peak_gate','field_samples']+[f'hist{i}' for i in range(6)]+[f'gate_hist{i}' for i in range(6)]
    names+=['system_false','backlog_skip','time_skip','time_pass','dequeue_total','timer_dequeue',
            'a12_nonzero','a13_nonzero','last_object','last_a18','last_a12','last_a13',
            'first_ns','last_ns','mirror_skip','selftest','bound']
    for i in [0,1]:
        v=struct.unpack_from('<96Q',b,0x100+i*0x1000); d=dict(zip(names,v[64:]))
        d.update(counts=list(v[:64]), gate_hist=list(v[73:79]));out.append(d)
    d=out[h[2]];c=d['counts']
    consumer_ids=[4,5,6,7,8,10,11,40]
    consumer=sum(c[i] for i in consumer_ids)
    return {'header8Q':list(h), 'active_bank_offset':hex(0x100+h[2]*0x1000), 'banks':out,
            'active':d, 'nontransactional':True,
            'derived':{'all_probe_count_sum':sum(c),'production_id9':c[9],
                       'consumer_probe_ids':consumer_ids,'consumer_probe_count':consumer,
                       'consumer_probes_per_id10':consumer/c[10],
                       'publication':h[3], 'published_copy_bytes':h[3]*96*8,
                       'published_dmb_instructions':h[3]*2,
                       'sampled_clock7_first_last_delta_ns':d['last_ns']-d['first_ns']}}


def parse_run(suffix):
    p=TRY/'runs'/('v25diag-web-r6-'+suffix)
    raw=read(p/'serial.log'); lines=raw.split(b'\n')
    gates=collections.defaultdict(list); sends=[]; polls=[]; sync=[]; stats=[]; marks=collections.defaultdict(list)
    cleanup=None;off=0;round_no=None;uptime=None
    for i,l in enumerate(lines,1):
        if b'FX3_PROC97_ALL_THREAD_STAT_BEGIN' in l:
            round_no=fields(l).get('round')
        if re.fullmatch(rb'[0-9]+\.[0-9]+ [0-9]+\.[0-9]+\r?',l):uptime={'LF':i,'raw':l.decode().strip()}
        if b'FX3_UI_GATE_SAMPLE ' in l:
            r=rec(l,i,off,b'FX3_UI_GATE_SAMPLE ');gates[r['fields']['id']].append(r)
        if b'FX3_BOOT_QUEUE_SEND ' in l:sends.append(rec(l,i,off,b'FX3_BOOT_QUEUE_SEND '))
        if b'FX3_KEY96_POLL ' in l:polls.append(rec(l,i,off,b'FX3_KEY96_POLL '))
        if b'FX3_SYNC100_NATIVE_POINT ' in l:sync.append(rec(l,i,off,b'FX3_SYNC100_NATIVE_POINT '))
        for tok in [b'FX3_TIMER_SNAPSHOT ',b'FX3_TIMER_BOUND ',b'FX3_UI_GATE_BOUND ',
                    b'FX3_UI_FILL_EXEC ',b'FX3_TIMER_ENTRY ',b'FX3_AP89_SCREEN_CREATE ',
                    b'FX3_AP100_CONTROLLED_CLEANUP_BEGIN ',b'FX3_BOOT_GATE_SAMPLE id=40 ']:
            if tok in l:marks[tok.decode().strip()].append(rec(l,i,off,tok))
        if b'FX3_AP100_CONTROLLED_CLEANUP_BEGIN' in l and cleanup is None:cleanup=i
        # Preserve partial/interleaved lines; only decode complete stat records.
        m=re.search(rb'(\d+) \(([^)]+)\) ([A-Za-z]) ((?:-?[0-9]+\s+){38,}-?[0-9]+)',l)
        if m:
            a=m[4].split(); tid=int(m[1]);name=m[2].decode(errors='replace')
            if name.startswith('uipc_proxy_') or (name=='AppFw' and tid>300):
                stats.append({'LF':i,'byte_offset':off+m.start(),'tid':tid,'name':name,'round_last_marker':round_no,
                              'state':m[3].decode(),'utime_ticks':int(a[10]),'stime_ticks':int(a[11]),
                              'priority':int(a[14]),'nice':int(a[15]),'processor':int(a[35]),
                              'rt_priority':int(a[36]),'policy':int(a[37]),'last_uptime_record':uptime,
                              'raw_stat':m[0].decode()})
        off+=len(l)+1
    def count_send_until(end):
        a=[x for x in sends if x['LF']<end]
        return {'all_queue5503e0_attempt_log_count':len(a),
                'by_caller_return_pc':dict(collections.Counter(x['fields'].get('caller_relative') for x in a)),
                'producer_by_tid':dict(collections.Counter(x['fields'].get('tid') for x in a
                         if x['fields'].get('caller_relative')=='0x16f1bb4'))}
    startup={}
    for name, rs in [('first_id9',gates['9'][:1]),('first_id10',gates['10'][:1]),
                      ('first_id5',gates['5'][:1]),('first_id7',gates['7'][:1]),
                      ('id10_n50',[x for x in gates['10'] if x['fields'].get('n')=='50']),
                      ('id10_n1000',[x for x in gates['10'] if x['fields'].get('n')=='1000'])]:
        if rs:
            r=rs[0]; prior=[x for x in polls if x['LF']<r['LF']];after=[x for x in polls if x['LF']>r['LF']]
            startup[name]={'probe':r, 'send_counts_before_LF':count_send_until(r['LF']),
                           'nearest_poll_before_by_serial_order':prior[-1:] or None,
                           'nearest_poll_after_by_serial_order':after[:1] or None}
        else:startup[name]=None
    # Same-clock poll deltas are exact; event rates by serial-order window are approximate.
    intervals=[]
    for a,b in zip(polls,polls[1:]):
        try: start=int(a['fields']['ns']);end=int(b['fields']['ns'])
        except (KeyError,ValueError):continue
        if end<=start or (cleanup and b['LF']>=cleanup):continue
        ss=[x for x in sends if a['LF']<x['LF']<b['LF'] and x['fields'].get('caller_relative')=='0x16f1bb4']
        cc=[x for x in sync if a['LF']<x['LF']<b['LF'] and x['fields'].get('id')=='109']
        intervals.append({'LFs':[a['LF'],b['LF']],'clock1_poll_ns':[start,end],'delta_poll_ns':end-start,
                          'producer_attempt_logs_between':len(ss),'consumer_sync109_logs_between':len(cc)})
    receipt=js(p/'receipt.json');bs=bank(read(p/'ui-gate-counters.bin'))
    out={'run':str(p.relative_to(ROOT)),'serial_bytes':len(raw),'serial_sha256':hashlib.sha256(raw).hexdigest(),
         'minus1018_literal':raw.count(b'-1018'),'cleanup_begin_LF':cleanup,
         'receipt':{k:receipt.get(k) for k in ['duration_seconds','key_steps','health_pass','protocol_pass','render_pass',
                         'lifecycle_pass','diagnostic_readback_pass','inputs_unchanged','candidate_sha256','cleanup']},
         'gate':bs,'gate_samples':dict(gates),'startup':startup,'poll_flow_intervals':intervals,
         'send_attempts_before_cleanup':count_send_until(cleanup or len(lines)),
         'sync109_count_before_cleanup':sum(x['fields'].get('id')=='109' and x['LF']<(cleanup or len(lines)) for x in sync),
         'thread_stat_records':stats,
         'marker_summaries':{k:{'count':len(a),'first':a[:1],'last':a[-1:]} for k,a in marks.items()},
         'recorded_input_checks':receipt['input_checks'], 'observer_sources':receipt['observer_source_snapshot']}
    if suffix=='2b63f512':
        out['command']=js(p/'command.json');out['qmp']=js(p/'qmp.json')
        ring=read(p/'osd-ring-final.bin');out['ring']={'bytes':len(ring),'all_zero':not any(ring),
                    'header6Q_at_0x2000':list(struct.unpack_from('<6Q',ring,0x2000)), 'valid_diag_events':False}
        assert out['serial_sha256']=='ba4ece40d053a92bba9fdfa2d42ccd9525e08f18c3e371b9093167f4717025f8'
        assert hashlib.sha256((p/'ui-gate-counters.bin').read_bytes()).hexdigest()=='e2b9ebb587c442904a2abb8c39f3ca27ceadcaea4d5d17ff112d68ee6bce1ce1'
        assert bs['active']['counts'][4:12]==[5768,5767,5767,0,0,8831,5741,5768]
        for f in receipt['observer_source_snapshot']:
            data=read(p/'observer-source'/f['name']);assert hashlib.sha256(data).hexdigest()==f['sha256']
    return out


def selected_cpio(p,wanted):
    result={};st=p.stat()
    with p.open('rb') as f:
        while True:
            start=f.tell();h=f.read(110);assert h[:6]==b'070701'
            v=[int(h[6+i*8:14+i*8],16) for i in range(13)]
            name=f.read(v[11])[:-1].decode().removeprefix('./');body=(start+110+v[11]+3)&~3
            if name in wanted:
                f.seek(body);b=f.read(v[6]);assert len(b)==v[6]
                result[name]={'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest(),'archive_data_offset':body}
                if name=='init':result[name]['preload_lines']=[s for s in b.decode().split('\n') if 'LD_PRELOAD' in s and 'ui-gate' in s]
            if name=='TRAILER!!!':break
            f.seek((body+v[6]+3)&~3)
    assert set(result)==set(wanted)
    assert p.stat().st_mtime_ns==st.st_mtime_ns and p.stat().st_size==st.st_size
    return {'path':str(p.relative_to(ROOT)),'only_selected_payloads_read':True,'members':result}


def main():
    v=plistlib.loads(subprocess.check_output(['diskutil','info','-plist','/Volumes/KAFU2T']))
    assert v['VolumeUUID']=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
    for p in [DEL/'r12-frame-stall-offline/REPORT.md',DEL/'r9-ui-startup-offline/REPORT.md',
              DEL/'r9-ui-startup-offline/EVIDENCE.json',DEL/'r9-ui-startup-offline/app-main-gate.txt',
              DEL/'r9-ui-startup-offline/app-backlog-producer.txt',DEL/'r9-ui-startup-offline/app-backlog-consumer.txt']:
        read(p)
    sources=[H/'fx3-ui-gate-v11.c',H/'fx3-ui-gate-v11-build.json',H/'fx3-ui-gate-v11.so',
             H/'fx3-timer-observe-v3.c',H/'fx3-timer-observe-v3-build.json',H/'fx3-timer-observe-v3.so',
             H/'fx3-capid-v49-touch100.c',H/'fx3-capid-v49-touch100-build.json',H/'fx3-capid-v49-touch100.so']
    timing=TRY/'mss-all-key-contrast/passive-timing-next'
    sources += [timing/'src/fx3-preset-context-v6-save102-timing.c',timing/'build/ap-timing.so',timing/'build-receipt.json']
    for p in sources:read(p)
    source_build_binding={}
    for name in ['fx3-ui-gate-v11','fx3-timer-observe-v3','fx3-capid-v49-touch100']:
        b=json.loads((H/(name+'-build.json')).read_text())
        assert sha(H/(name+'.c'))==b['source_sha256']
        assert sha(H/(name+'.so'))==b['output_sha256']
        source_build_binding[name]={'source_sha256':b['source_sha256'],
                                    'output_sha256':b['output_sha256'],'matched':True}
    runs={x:parse_run(x) for x in ['2b63f512','5010d535','8456422c','49f9bf9d','814c425f']}
    r13=runs['2b63f512']
    cpio=Path(next(x['path'] for x in r13['recorded_input_checks'] if x['path'].endswith('/guest.cpio')))
    wanted=['init','simulation/fx3-ui-gate-v1.so','simulation/fx3-timer-observe-v1.so',
            'simulation/fx3-preset-context-v2-screen.so','simulation/fx3-capid-v1.so']
    members=selected_cpio(cpio,wanted)
    binding={}
    for member,binary in zip(wanted[1:],[H/'fx3-ui-gate-v11.so',H/'fx3-timer-observe-v3.so',
                                       timing/'build/ap-timing.so',H/'fx3-capid-v49-touch100.so']):
        binding[member]={'binary':str(binary.relative_to(ROOT)),'matches':sha(binary)==members['members'][member]['sha256']}
        assert binding[member]['matches']
    exports=[]
    read(LIB/'appFw.so')
    for name,start,end in [('timer-start',0x16f16bc,0x16f1818),('timer-request',0x16f1118,0x16f1188),
                           ('timer-dispatch',0x16f1358,0x16f1448),('timer-callback',0x16f1c18,0x16f1cdc)]:
        argv=['xcrun','llvm-objdump','--disassemble',f'--start-address={hex(start)}',f'--stop-address={hex(end)}',str(LIB/'appFw.so')]
        result=subprocess.run(argv,capture_output=True,check=True).stdout
        (HERE/(name+'.txt')).write_bytes(result);exports.append({'file':name+'.txt','argv':argv})
    out={'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'scope':'offline only',
         'volume_uuid':v['VolumeUUID'],'runs':runs,'selected_cpio_members':members,'binding':binding,
         'source_build_binding':source_build_binding,
         'disassembly':exports,'inputs':INPUTS,
         'clock_warning':'gate first/last are sampled clock7; key polls clock1; no mixed-clock subtraction',
         'flow_warning':'event counts between serial-order poll boundaries are approximate rates, not per-event timestamps'}
    for rel, pin in INPUTS.items():assert sha(ROOT/rel)==pin['sha256'],rel
    (HERE/'EVIDENCE.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
    (HERE/'INPUT-SHA256SUMS').write_text(''.join(f"{x['sha256']}  {ROOT/rel}\n" for rel,x in sorted(INPUTS.items())))
    print(json.dumps({'inputs_unchanged':len(INPUTS),'binding':binding,'r13_gate_derived':r13['gate']['derived']}))


if __name__=='__main__':main()
