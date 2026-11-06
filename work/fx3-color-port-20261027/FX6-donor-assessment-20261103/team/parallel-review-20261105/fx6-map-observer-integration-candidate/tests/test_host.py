#!/usr/bin/env python3
import json,sys,tempfile,threading,time
from pathlib import Path
HERE=Path(__file__).resolve().parent.parent;sys.path.insert(0,str(HERE))
import framed_provider as F,run_map_observer as R,live_runner as L
checks=[]
def check(n,f):print('RUN',n,flush=True);f();checks.append(n)
SAMP=HERE/'receipts/framed-fixture.serial'
def provider_accept():m=F.FramedProvider().select(SAMP.read_text());assert m['framed'] and m['pid']==239 and m['ap']['bias']==0x7efab5b000
check('framed_provider_accepts_fixture_without_legacy_maps',provider_accept)
def provider_reject():
 raw='\n'.join(l for l in SAMP.read_text().splitlines() if not l.startswith('FX3MS1 END'))
 try:F.FramedProvider().select(raw)
 except Exception as e:assert 'missing END' in str(e);return
 raise AssertionError('corrupt accepted')
check('framed_provider_rejects_corrupt_no_fallback',provider_reject)
GOOD={'two_keys_observed':True,'host_cleanup_complete':True,'input_unchanged_after':True,'postflight_error':None,'verification_failed':False,'guest_restore_status':'unknown_not_attempted','boot_menu_passed':False,'receipt_path':'/tmp/r.json'}
def gate():
 calls=[];rf=lambda root:(calls.append(root) or type('R',(),{'run':lambda self:GOOD})());
 assert R.main([])==2 and not calls
 assert R.main(['--approved-token','WRONG','--new-run-approval','--run-root','/tmp/x'],rf)==2 and not calls
 assert R.main(['--approved-token',R.TOKEN,'--run-root','/tmp/x'],rf)==2 and not calls
 assert R.main(['--approved-token',R.TOKEN,'--new-run-approval','--run-root','/tmp/x'],rf)==0 and len(calls)==1
check('entry_default_disabled_and_fake_success',gate)
def failure():
 bad=dict(GOOD);bad['two_keys_observed']=False;bad['verification_failed']=True;bad['postflight_error']='x'
 calls=[];rf=lambda root:(calls.append(root) or type('R',(),{'run':lambda self:bad})())
 assert R.main(['--approved-token',R.TOKEN,'--new-run-approval','--run-root','/tmp/x'],rf)==1 and len(calls)==1
check('entry_returns_nonzero_on_failed_receipt',failure)
def wait_ok():
 with tempfile.TemporaryDirectory() as td:
  p=Path(td)/'s';p.write_bytes(b'')
  def w():
   time.sleep(.08);p.write_bytes(SAMP.read_bytes())
  threading.Thread(target=w).start();m=L._wait_mapping(F.FramedProvider(),p,None);assert m['framed']
check('mapping_waits_for_late_complete_frame',wait_ok)
def wait_timeout():
 with tempfile.TemporaryDirectory() as td:
  p=Path(td)/'s';p.write_bytes(b'')
  try:L._wait_mapping(F.FramedProvider(),p,type('D',(),{'remaining_observation':lambda self:0,'remaining_total':lambda self:0})())
  except TimeoutError:return
  raise AssertionError('no timeout')
check('mapping_timeout_no_frame',wait_timeout)
def _deadline(sec):
 class D:
  def __init__(self):self.end=time.monotonic()+sec
  def remaining_observation(self):return max(0.0,self.end-time.monotonic())
  def remaining_total(self):return max(0.0,self.end-time.monotonic())
 return D()
def split_wait():
 raw=(HERE/'receipts/native-target-frame.serial').read_bytes()
 with tempfile.TemporaryDirectory() as td:
  p=Path(td)/'s';p.write_bytes(b'')
  def w():
   for i in range(0,len(raw),37):
    with p.open('ab') as f:f.write(raw[i:i+37]);f.flush()
    time.sleep(.01)
  threading.Thread(target=w).start();m=L._wait_mapping(F.FramedProvider(),p,_deadline(10));assert m['framed']
check('stream_arbitrary_byte_chunks_only_final_frame',split_wait)
def invalid_utf8_noise():
 raw=b'\xff\xfe\x80 console noise\n'+ (HERE/'receipts/native-target-frame.serial').read_bytes()
 with tempfile.TemporaryDirectory() as td:
  p=Path(td)/'s';p.write_bytes(raw);m=L._wait_mapping(F.FramedProvider(),p,_deadline(1));assert m['framed']
check('invalid_utf8_noise_does_not_crash',invalid_utf8_noise)
def partial_no_accept():
 raw=(HERE/'receipts/native-target-frame.serial').read_bytes()
 with tempfile.TemporaryDirectory() as td:
  p=Path(td)/'s';p.write_bytes(raw[:40])
  try:L._wait_mapping(F.FramedProvider(),p,_deadline(.2))
  except TimeoutError:return
  raise AssertionError('partial accepted')
check('partial_tail_not_early_rejected_or_accepted',partial_no_accept)
def complete_corrupt():
 with tempfile.TemporaryDirectory() as td:
  p=Path(td)/'s';p.write_bytes(b'FX3MS1 BAD complete line\n')
  try:L._wait_mapping(F.FramedProvider(),p,_deadline(1))
  except Exception as e:assert 'unknown frame' in str(e) or 'field' in str(e);return
  raise AssertionError('complete corrupt accepted')
check('complete_malformed_line_rejected_immediately',complete_corrupt)

out={'schema':'fx6-map-observer-integration-tests-v3','status':'PASS_OFFLINE_FAKE','tests':len(checks),'cases':checks}
(HERE/'tests/test-host.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
