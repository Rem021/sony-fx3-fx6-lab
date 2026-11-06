#!/usr/bin/env python3
"""Offline tests for the independent serial fault detector."""
import hashlib,json,subprocess,sys,tempfile
from pathlib import Path
HERE=Path(__file__).resolve().parent.parent;DET=HERE/'detect_serial_faults.py';CP=Path('/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/fx6-boot-readiness/early-kernel/cp-helper-agnostic');R66=CP/'runs/cp-bind-66ed0f78/serial.log';R84=CP/'runs/cp-bind-84db17c2/serial.log'
checks=[]
def check(n,f):f();checks.append(n)
def run(serial):
 with tempfile.TemporaryDirectory() as td:
  out=Path(td)/'detected.json';p=subprocess.run([sys.executable,str(DET),'--serial',str(serial),'--output',str(out)],capture_output=True,text=True);return p.returncode,json.loads(out.read_text())
def test66():
 rc,d=run(R66);assert rc==2 and d['status']=='incomplete_truncated';assert d['assert_count']==4 and d['fatal_fault_count']==0
 assert [(x['line'],x['source'],x['source_line']) for x in d['asserts']]==[(11688,'model_api.cpp',3147),(11738,'model_api.cpp',3176),(14502,'infra_wrapper_bb_procam_chaplin_base.cpp',1075),(14734,'infra_wrapper_bb_procam_chaplin_base.cpp',1075)]
 assert len(d['fault_markers'])==4 and d['fatal_fault_markers']==[] and all(x['fatal'] is False for x in d['asserts']);assert d['screen_evidence']=='absent' and d['visible_pixels_zero_claimed'] is False and d['boot_menu_passed'] is False
check('66ed_four_asserts_real_lines_nonfatal',test66)
def test84():
 rc,d=run(R84);assert rc==2 and d['status']=='incomplete_truncated';assert d['assert_count']==2 and d['fatal_fault_count']==1
 assert [(x['line'],x['source_line']) for x in d['asserts']]==[(11597,3147),(11644,3176)]
 assert len(d['fault_markers'])==3 and len(d['fatal_fault_markers'])==1
 f=d['fatal_faults'][0];assert f['line']==16408 and f['classification']=='internal_error_oops' and f['fatal'] is True and 'Internal error: Oops:' in f['raw_line']
 assert f['raw_line']==d['markers'][-1]['raw_line']
check('84db_assert_oops_regression_fatal_vs_assert',test84)
def old_miss():
 p=json.loads((HERE/'receipts/old-detector-reproducer.json').read_text());assert p['66ed']['old_fault_markers']==[] and p['66ed']['assert_lines']==4 and p['84db']['old_fault_markers']==['Oops:','Internal error:']
check('old_detector_miss_reproducer',old_miss)
def malformed():
 for data,status in ((b'','unknown_empty'),(b'assert at x:1\n','asserts_detected'),(b'assert at x:1','incomplete_truncated')):
  with tempfile.TemporaryDirectory() as td:
   f=Path(td)/'s.log';f.write_bytes(data);rc,d=run(f);assert d['status']==status;assert rc==(1 if status=='asserts_detected' else 2)
 with tempfile.TemporaryDirectory() as td:
  rc,d=run(Path(td)/'missing.log');assert rc==2 and d['status']=='unknown_missing'
  rc,d=run(Path(td));assert rc==2 and d['status']=='unknown_unreadable'
check('empty_missing_directory_and_truncated_unknown',malformed)
def counterexamples():
 with tempfile.TemporaryDirectory() as td:
  f=Path(td)/'ordinary.log';f.write_text('This note discusses panic and assert at model_api.cpp:3147 but is not a marker.\nKernel command line: console=ttyAMA0 panic=-1\nassertion at model_api.cpp:999\n')
  rc,d=run(f);assert d['assert_count']==0 and d['fatal_fault_count']==0 and d['status']=='complete_no_fault_marker' and rc==0
  f.write_text('assert at model_api.cpp:3147\n');rc,d=run(f);assert d['assert_count']==1 and rc==1
check('ordinary_text_not_panic_or_assert_but_exact_assert_is',counterexamples)
def screen_marker():
 with tempfile.TemporaryDirectory() as td:
  f=Path(td)/'screen.log';f.write_text('FX3_AP89_SCREEN_CREATE value=1\n');rc,d=run(f);assert d['screen_marker_count']==1 and d['screen_evidence']=='markers_present' and d['visible_pixels_zero_claimed'] is False
check('screen_marker_presence_not_pixel_claim',screen_marker)
out={'status':'PASS_OFFLINE_SERIAL_DETECTOR','cases':checks,'count':len(checks),'detector_sha256':hashlib.sha256(DET.read_bytes()).hexdigest()}
(HERE/'tests/host-tests.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
