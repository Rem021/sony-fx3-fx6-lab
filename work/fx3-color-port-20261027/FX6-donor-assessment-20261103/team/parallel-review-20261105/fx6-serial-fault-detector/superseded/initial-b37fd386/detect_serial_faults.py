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
    if data is None:return {'serial':path_note,'status':'unknown_missing','complete':False,'line_basis':'splitlines','lines':0,'markers':[],'asserts':[],'fatal_faults':[],'fault_markers':[],'screen_markers':{},'screen_marker_count':0,'screen_evidence':'unknown','visible_pixels_zero_claimed':False,'boot_menu_passed':False,'no_fault_is_boot_success':False,'sha256':None,'bytes':0,'error':'serial path missing'}
    sha=sha_bytes(data);raw_lines=data.splitlines(keepends=True);lines=[]
    for i,raw in enumerate(raw_lines,1):
        text=raw.decode('utf-8','replace')
        if text.endswith('\n'):text=text[:-1]
        if text.endswith('\r'):text=text[:-1]
        lines.append((i,text,raw.endswith(b'\n')))
    complete=bool(data) and data.endswith(b'\n')
    markers=[];asserts=[];fatals=[];screen={k:0 for k in SCREEN_MARKERS}
    for idx,text,terminated in lines:
        for k in screen:
            if k in text:screen[k]+=1
        m=ASSERT.match(text)
        if m:
            fn=None
            if idx < len(lines) and lines[idx][1].startswith('function:'):fn=lines[idx][1][len('function:'):].strip() or None
            row={'line':idx,'raw_line':text,'type':'assert','classification':'assert_reported_nonfatal','fatal':False,'source':m.group('source'),'source_line':int(m.group('source_line')),'function':fn,'returnable':'not_proven_by_detector; appears in the known nonfatal assert logger format'}
            asserts.append(row);markers.append(row);continue
        for name,pat in FATAL_PATTERNS:
            if pat.match(text):
                row={'line':idx,'raw_line':text,'type':'fatal_fault','classification':name,'fatal':True,'source':None,'source_line':None,'function':None}
                fatals.append(row);markers.append(row);break
    if not data:status='unknown_empty'
    elif not complete:status='incomplete_truncated'
    elif fatals:status='faults_detected'
    elif asserts:status='asserts_detected'
    else:status='complete_no_fault_marker'
    return {'schema':'fx6-serial-fault-detection-v1','serial':path_note,'status':status,'complete':complete,'line_basis':'bytes.splitlines(keepends=True); logical line index','lines':len(lines),'sha256':sha,'bytes':len(data),'markers':markers,'asserts':asserts,'fatal_faults':fatals,'fault_markers':[x['raw_line'] for x in markers],'fatal_fault_markers':[x['raw_line'] for x in fatals],'assert_count':len(asserts),'fatal_fault_count':len(fatals),'screen_markers':screen,'screen_marker_count':sum(screen.values()),'screen_evidence':'markers_present' if sum(screen.values()) else 'absent','visible_pixels_zero_claimed':False,'boot_menu_passed':False,'functional_success':False,'no_fault_is_boot_success':False,'exit_code':2 if (not data or not complete or status.startswith('unknown')) else (1 if (asserts or fatals) else 0)}
def read_detect(path):
    p=Path(path)
    try:b=p.read_bytes()
    except FileNotFoundError:return detect(None,str(path))
    except (IsADirectoryError,PermissionError,OSError) as e:return {'serial':str(path),'status':'unknown_unreadable','complete':False,'line_basis':'splitlines','lines':0,'markers':[],'asserts':[],'fatal_faults':[],'fault_markers':[],'screen_markers':{k:0 for k in SCREEN_MARKERS},'screen_marker_count':0,'screen_evidence':'unknown','visible_pixels_zero_claimed':False,'boot_menu_passed':False,'no_fault_is_boot_success':False,'sha256':None,'bytes':0,'error':repr(e),'exit_code':2}
    return detect(b,str(path))
def main(argv=None):
 ap=argparse.ArgumentParser();ap.add_argument('--serial',required=True);ap.add_argument('--output',required=True);a=ap.parse_args(argv)
 out=read_detect(a.serial);out['exit_code']=out.get('exit_code',2)
 Path(a.output).write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({'status':out['status'],'asserts':out.get('assert_count',0),'fatal':out.get('fatal_fault_count',0),'exit_code':out['exit_code'],'output':str(a.output)}))
 return out['exit_code']
if __name__=='__main__':sys.exit(main())
