#!/usr/bin/env python3
"""Host-only AP serial classifier. It never launches or controls a guest."""
import argparse
import ast
import hashlib
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
MAC = HERE.parents[5]
PARENT = MAC/'work/fx3-vm-20261101/lead-codex/vm-optimization-20261103/runtime/try2-usability/runs/try2mssallinternal-c017e6ed/observer-source/trial_log_v4_mss.py'
PARENT_SHA = '4d57629fc8bf1c8d158bfcf101915b9edd626f7bfb11c55fc78fe634ef7d6645'
CANDIDATE_SHA = 'bb618bd24f0b504edb14820da4d8204c4b1517cc225e4633eb43f5884f3fff02'
EXACT_DIAGNOSTICS = {
    'FX3_PRESET_CONTEXT_BIND_REJECT point=0 reason=original_word': 'fx3_preset_48_word_guard',
    'FX3_UI_GATE_BIND_FAIL id=0 reason=original_instruction': 'fx3_ui_60_word_guard',
    'FX3_TIMER_BIND_FAILED k=0 reason=prefix original_unchanged=1': 'fx3_timer_ap_prefix_guard',
    'FX3_MEDIA_BIND_REJECT module=A reason=parameter_getter_code id=0x6db': 'fx3_media_ap_getter_guard',
}
LOADERS = {
    'verify': re.compile(r'FX3_TRACE_ABI_VERIFY_RC=(-?\d+)'),
    'list': re.compile(r'FX3_TRACE_ABI_LIST_RC=(-?\d+)'),
    'true': re.compile(r'FX3_TRACE_ABI_TRUE_RC=(-?\d+)'),
}
FATAL = re.compile(r'assert at|Assertion|\bASSERT(?:!|:|\s+fail)|exception monitor|Kernel panic|Unhandled fault:|symbol lookup error:|\bOops:|\bBUG:|FX3_TRACE_FATAL|FX3_SIGNAL_OBSERVE[^\n]*signal=6(?:\s|$)', re.I)
PROTECT = re.compile(r'FX3_(?:SYNC100_REJECT|SYNC100_DISABLED|TOUCH100_REJECT|DATE99_REJECT|OSD_HEADLESS_REJECT|BACKUP_CP_OWNER_FAILED|BACKUP_CP_REJECT|BACKUP_CP_RETRY|GPE_EARLY_BIND_REJECT|GPE_RESOURCE_BIND_REJECT|RM_[A-Z_]*REJECT|RM_UNKNOWN|MEDIA_BIND_REJECT|MEDIA_OWNED_RAW_REJECT|UI_GATE_BIND_FAIL|PRESET_CONTEXT_BIND_REJECT|TIMER_BIND_FAILED|DISPLAY_BIND_FAIL|FILE103_READY_FAILED)|unknown\s+key|invalid\s+from_type', re.I)
AP_DIAGNOSTIC = re.compile(r'FX3_(?:PRESET_CONTEXT_BIND_REJECT|UI_GATE_BIND_FAIL|MEDIA_BIND_REJECT module=A|TIMER_BIND_FAILED|APP_INIT_BIND|MEDIA_BOUND module=A)[^\r\n]*')

def sha(path):
    with Path(path).open('rb') as f: return hashlib.file_digest(f,'sha256').hexdigest()

def parent_failures():
    assert sha(PARENT)==PARENT_SHA,'parent health monitor drift'
    tree=ast.parse(PARENT.read_text())
    assignment=next(x for x in tree.body if isinstance(x,ast.Assign)
                    and any(isinstance(t,ast.Name) and t.id=='FAILURES' for t in x.targets))
    return [re.compile(p,re.I) for p,_ in ast.literal_eval(assignment.value)]

PARENT_FAILURES=parent_failures()

def classify(raw, candidate_sha=CANDIDATE_SHA):
    assert candidate_sha == CANDIDATE_SHA, 'diagnostic exceptions require exact candidate'
    lines = raw.decode(errors='replace').splitlines()
    events=[]; loader={k:None for k in LOADERS};observations={k:[] for k in LOADERS};first_fault=None
    for n,line in enumerate(lines,1):
        clean=line.strip()
        for name,pattern in LOADERS.items():
            for m in pattern.finditer(line):
                value=int(m.group(1));observations[name].append({'line':n,'column':m.start(),'value':value})
                if loader[name] is None:loader[name]=value
                if value!=0 and first_fault is None:
                    first_fault={'line':n,'column':m.start(),'kind':'loader_nonzero','text':clean[:300]}
        if clean in EXACT_DIAGNOSTICS:
            events.append({'line':n,'kind':'expected_fx3_diagnostic_only','which':EXACT_DIAGNOSTICS[clean], 'text':clean})
            continue
        m=AP_DIAGNOSTIC.search(line)
        if m: events.append({'line':n,'kind':'ap_related_unclassified','text':m.group()[:300]})
        if first_fault is None and (FATAL.search(line) or PROTECT.search(line)
                                    or any(p.search(line) for p in PARENT_FAILURES)):
            first_fault={'line':n,'kind':'real_fault_or_unproven_guard','text':clean[:300]}
    return {'candidate_sha256':candidate_sha,'loader_first_rc':loader,
            'loader_all_observations':observations,'events':events,
            'first_fault':first_fault,'serial_sha256':hashlib.sha256(raw).hexdigest(),
            'classification':'HOST_LOG_ONLY_NO_AP_ENTRY_PROOF'}

def fixtures():
    cases={
      'two_exact_diagnostics':(b'FX3_TRACE_ABI_VERIFY_RC=0\nFX3_TRACE_ABI_LIST_RC=0\nFX3_TRACE_ABI_TRUE_RC=0\nFX3_PRESET_CONTEXT_BIND_REJECT point=0 reason=original_word\nFX3_UI_GATE_BIND_FAIL id=0 reason=original_instruction\n',None,2),
      'preset_other_point':(b'FX3_PRESET_CONTEXT_BIND_REJECT point=1 reason=original_word\n','real_fault_or_unproven_guard',1),
      'ui_other_reason':(b'FX3_UI_GATE_BIND_FAIL id=0 reason=install result=-6\n','real_fault_or_unproven_guard',1),
      'media_exact_diagnostic':(b'FX3_MEDIA_BIND_REJECT module=A reason=parameter_getter_code id=0x6db\n',None,1),
      'timer_exact_diagnostic':(b'FX3_TIMER_BIND_FAILED k=0 reason=prefix original_unchanged=1\n',None,1),
      'media_wrong_id':(b'FX3_MEDIA_BIND_REJECT module=A reason=parameter_getter_code id=0x6dc\n','real_fault_or_unproven_guard',1),
      'loader_error':(b'FX3_TRACE_ABI_VERIFY_RC=-7\n','loader_nonzero',0),
      'loader_later_nonzero':(b'FX3_TRACE_ABI_VERIFY_RC=0\nFX3_TRACE_ABI_VERIFY_RC=-7\n','loader_nonzero',0),
      'loader_same_line_nonzero':(b'FX3_TRACE_ABI_VERIFY_RC=0 FX3_TRACE_ABI_VERIFY_RC=-7\n','loader_nonzero',0),
      'interleaved_error':(b'FX3_PRESET_CONTEXT_BIND_REJECT point=0 reason=original_word Kernel panic\n','real_fault_or_unproven_guard',1),
      'lookup_error':(b'program: symbol lookup error: missing_symbol\n','real_fault_or_unproven_guard',0),
      'mss_overflow':(b'FX3_MSS_ORIGINAL_PATH_OVERFLOW\n','real_fault_or_unproven_guard',0),
      'sync_protection':(b'FX3_SYNC100_DISABLED binding_failure=1\n','real_fault_or_unproven_guard',0),
      'rm_unknown':(b'FX3_RM_UNKNOWN request=8\n','real_fault_or_unproven_guard',0),
      'media_timeout':(b'FX3_MEDIA_INIT_TIMEOUT\n','real_fault_or_unproven_guard',0),
      'gpe_command_failure':(b'FX3_GPE_CMD mode=x result=3 reason=2\n','real_fault_or_unproven_guard',0),
      'unfetched_frame':(b'unfetched -1018\n','real_fault_or_unproven_guard',0),
      'no_marker_not_success':(b'Linux version 4.9.337-scel+\n',None,0),
    }
    out={}
    for name,(sample,kind,count) in cases.items():
        result=classify(sample)
        assert (result['first_fault'] or {}).get('kind')==kind,name
        assert len(result['events'])==count,name
        out[name]={'first_fault_kind':kind,'event_count':count,'passed':True}
        if name.startswith('loader_later') or name.startswith('loader_same'):
            assert result['loader_first_rc']['verify']==0
            assert [x['value'] for x in result['loader_all_observations']['verify']]==[0,-7]
    try:classify(b'FX3_PRESET_CONTEXT_BIND_REJECT point=0 reason=original_word\n','0'*64)
    except AssertionError:out['wrong_candidate_denied']={'passed':True}
    else:raise AssertionError('wrong candidate accepted')
    return out

def main():
    assert sha(PARENT)==PARENT_SHA,'parent health monitor drift'
    r=fixtures();(HERE/'classification-fixtures.json').write_text(json.dumps(r,indent=2)+'\n')
    parser=argparse.ArgumentParser();parser.add_argument('--serial',type=Path);args=parser.parse_args()
    if args.serial:
        print(json.dumps(classify(args.serial.read_bytes()),indent=2))
    else:print(json.dumps({'fixtures_passed':len(r),'host_only':True,'parent_sha256':PARENT_SHA},indent=2))

if __name__=='__main__':main()
