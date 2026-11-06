#!/usr/bin/env python3
"""Offline FX6 serial fault detector (standard library only).

CLI: python3 detect_serial_faults.py --serial PATH --output JSON
Exit: 0 complete/no fault marker; 1 assert or fatal marker; 2 unknown/incomplete.
No-fault is not boot/menu success.
"""
import argparse,hashlib,json,re,sys
from pathlib import Path

ASSERT=re.compile(r'^\s*assert at (?P<source>[^:\s]+):(?P<source_line>\d+)\s*$')
FATAL_PATTERNS=[
 ('internal_error_oops',re.compile(r'^\s*(?:\[\s*\d+(?:\.\d+)?\]\s*)?Internal error:\s*Oops:\s*\S*')),
 ('oops',re.compile(r'^\s*(?:\[\s*\d+(?:\.\d+)?\]\s*)?Oops:\s*\S*')),
 ('kernel_panic',re.compile(r'^\s*(?:\[\s*\d+(?:\.\d+)?\]\s*)?Kernel panic(?:\s*-\s*not syncing)?\b')),
 ('unable_to_handle_kernel',re.compile(r'^\s*(?:\[\s*\d+(?:\.\d+)?\]\s*)?Unable to handle kernel\b')),
 ('seerror_interrupt',re.compile(r'^\s*(?:\[\s*\d+(?:\.\d+)?\]\s*)?SError Interrupt\b')),
 ('bug_unable',re.compile(r'^\s*BUG:\s*(?:unable to handle|kernel NULL pointer)\b')),
]
SCREEN_MARKERS=('FX3_AP89_SCREEN_CREATE','FX3_AP89_UUD_DECISION','FX3_MENU')

def sha_bytes(b):return hashlib.sha256(b).hexdigest()
def detect(data,path_note='<memory>'):
    if data is None:return {'serial':path_note,'status':'unknown_missing','line_terminated':False,'capture_complete':None,'complete':None,'line_basis':'splitlines','lines':0,'markers':[],'asserts':[],'kernel_faults':[],'fault_markers':[],'kernel_fault_markers':[],'screen_markers':{},'screen_marker_count':0,'screen_evidence':'unknown','visible_pixels_zero_claimed':False,'boot_menu_passed':False,'functional_success':False,'no_fault_is_boot_success':False,'sha256':None,'bytes':0,'error':'serial path missing','exit_code':2}
    sha=sha_bytes(data);raw_lines=data.splitlines(keepends=True);lines=[]
    for i,raw in enumerate(raw_lines,1):
        text=raw.decode('utf-8','replace')
        if text.endswith('\n'):text=text[:-1]
        if text.endswith('\r'):text=text[:-1]
        lines.append((i,text,raw.endswith(b'\n')))
    line_terminated=bool(data) and data.endswith(b'\n')
    # A final newline only means the last line is terminated.  Without an
    # independent capture/run terminal record, capture completeness is unknown.
    capture_complete=False if (data and not line_terminated) else None
    markers=[];asserts=[];kernel=[];screen={k:0 for k in SCREEN_MARKERS}
    for idx,text,terminated in lines:
        for k in screen:
            if k in text:screen[k]+=1
        m=ASSERT.match(text)
        if m:
            fn=None
            if idx < len(lines) and lines[idx][1].startswith('function:'):fn=lines[idx][1][len('function:'):].strip() or None
            row={'line':idx,'raw_line':text,'type':'assert','classification':'assert_reported','fatal':None,'returnable':None,'termination_proven':False,'source':m.group('source'),'source_line':int(m.group('source_line')),'function':fn,'note':'format reports an assert; this detector does not prove nonfatal or returnable'}
            asserts.append(row);markers.append(row);continue
        for name,pat in FATAL_PATTERNS:
            if pat.match(text):
                row={'line':idx,'raw_line':text,'type':'kernel_fault_marker','classification':name,'fatal':None,'termination_proven':False,'source':None,'source_line':None,'function':None,'note':'kernel fault marker; termination is not proven by this line'}
                kernel.append(row);markers.append(row);break
    if not data:status='unknown_empty'
    elif not line_terminated:status='incomplete_truncated'
    elif kernel:status='kernel_fault_markers_detected'
    elif asserts:status='asserts_detected'
    else:status='scan_no_marker_capture_unknown'
    return {'schema':'fx6-serial-fault-detection-v2','serial':path_note,'status':status,'line_terminated':line_terminated,'capture_complete':capture_complete,'complete':capture_complete,'line_basis':'bytes.splitlines(keepends=True); logical line index','lines':len(lines),'sha256':sha,'bytes':len(data),'markers':markers,'asserts':asserts,'kernel_faults':kernel,'fault_markers':[x['raw_line'] for x in markers],'kernel_fault_markers':[x['raw_line'] for x in kernel],'assert_count':len(asserts),'kernel_fault_count':len(kernel),'fatal_fault_count':0,'panic_count':sum(1 for x in kernel if x['classification']=='kernel_panic'),'termination_proven':False,'screen_markers':screen,'screen_marker_count':sum(screen.values()),'screen_evidence':'markers_present' if sum(screen.values()) else 'absent','visible_pixels_zero_claimed':False,'boot_menu_passed':False,'functional_success':False,'no_fault_is_boot_success':False,'exit_code':2 if (not data or not line_terminated or status.startswith('unknown')) else (1 if markers else 0),'note':'CLI exit 0 means scan completed with no marker, not a complete run; assert/fault markers do not prove nonfatal/termination'}

def read_detect(path):
    p=Path(path)
    try:b=p.read_bytes()
    except FileNotFoundError:return detect(None,str(path))
    except (IsADirectoryError,PermissionError,OSError) as e:
        out=detect(None,str(path));out['status']='unknown_unreadable';out['error']=repr(e);out['exit_code']=2;return out
    return detect(b,str(path))
def main(argv=None):
 ap=argparse.ArgumentParser();ap.add_argument('--serial',required=True);ap.add_argument('--output',required=True);a=ap.parse_args(argv)
 out=read_detect(a.serial);out['exit_code']=out.get('exit_code',2)
 Path(a.output).write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({'status':out['status'],'asserts':out.get('assert_count',0),'fatal':out.get('fatal_fault_count',0),'exit_code':out['exit_code'],'output':str(a.output)}))
 return out['exit_code']
if __name__=='__main__':sys.exit(main())
