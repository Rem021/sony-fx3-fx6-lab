#!/usr/bin/env python3
"""Compile/run the tiny C reader on fixtures; validate protocol rejection paths."""
import base64,hashlib,json,os,subprocess,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent.parent;sys.path.insert(0,str(HERE));import decode_snapshot as D
FIX=HERE/'tests/fixtures/maps-8955-9222.txt';STAT=HERE/'tests/fixtures/stat-before.txt';STAT2=HERE/'tests/fixtures/stat-after.txt';SRC=HERE/'fx3_map_snapshot.c';PROD=HERE/'fx3_map_snapshot';TEST=HERE/'fx3_map_snapshot_test';TRACE=HERE/'tests/fixtures/io-trace.txt';checks=[]
def check(n,f):f();checks.append(n)
def compile_readers():
 for out,extra in ((PROD,[]),(TEST,['-DFX3_MAP_SNAPSHOT_TEST'])):
  r=subprocess.run(['cc','-std=c11','-O2','-Wall','-Wextra',*extra,'-o',str(out),str(SRC)],capture_output=True,text=True);assert r.returncode==0,r.stderr
check('c_production_and_compile_time_test_build',compile_readers)
def run(pid=239,seq=1,maps=FIX,before=STAT,after=STAT2,cap=None,extra=False,eintr=False,eof_fail=False,trace=False):
 env=dict(os.environ);env.update({'FX3_TEST_MAPS':str(maps),'FX3_TEST_STAT_BEFORE':str(before),'FX3_TEST_STAT_AFTER':str(after)})
 if cap:env['FX3_TEST_CAP']=str(cap)
 if extra:env['FX3_TEST_EXTRA']='1'
 if eintr:env['FX3_TEST_EINTR']='1'
 if eof_fail:env['FX3_TEST_EOF_FAIL']='1'
 if trace:env['FX3_TEST_TRACE']=str(TRACE)
 return subprocess.run([str(TEST),str(pid),str(seq)],capture_output=True,env=env)
def dec(text):
 try:return D.decode(text),None
 except D.ProtocolError as e:return None,str(e)
def frame(payload,pid=239,st=777,seq=1,cap=262144,line_term=1,complete=1,atomic=0,data_reads=1,eof_probe=1,eof_obs=1,bytes_override=None,lines_override=None,digest_override=None,no_data=False,data_pid=None,data_start=None,data_seq=None):
 raw=payload;lines=raw.count(b'\n');digest='fnv1a64:%016x'%D.fnv1a(raw)
 out=[f'FX3MS1 BEGIN pid={pid} starttime={st} seq={seq} cap={cap} data_reads={data_reads} eof_probe={eof_probe} data_attempts=1 eof_attempts=1 capture=bounded_single_read']
 if not no_data:
  out.append(f'FX3MS1 DATA 0 {data_pid if data_pid is not None else pid} {data_start if data_start is not None else st} {data_seq if data_seq is not None else seq} {base64.b64encode(raw).decode()}')
 out.append(f'FX3MS1 END pid={pid} starttime={st} seq={seq} bytes={len(raw) if bytes_override is None else bytes_override} lines={lines if lines_override is None else lines_override} digest={digest if digest_override is None else digest_override} line_terminated={line_term} complete={complete} snapshot_atomic={atomic} data_reads={data_reads} eof_probe={eof_probe} eof_observed={eof_obs} data_attempts=1 eof_attempts=1')
 return '\n'.join(out)+'\n'
def accepted():
 r=run();assert r.returncode==0,r.stderr;d,e=dec(r.stdout.decode());assert e is None and d['bytes']==10563 and d['lines']==105 and d['selected_seq']==1;assert d['data_reads']==1 and d['eof_probe']==1 and d['eof_observed']==1;assert d['snapshot_atomic'] is False;assert 'appFw.so' in d['maps_text']
check('single_read_plus_eof_probe_fixture_accepted',accepted)
def fnv_vectors():
 assert D.fnv1a(b'')==0xcbf29ce484222325 and D.fnv1a(b'a')==0xaf63dc4c8601ec8c and D.fnv1a(b'foobar')==0x85944171f73967e8
 r=run();raw=r.stdout.decode();dig=next(l.split('digest=')[1].split()[0] for l in raw.splitlines() if l.startswith('FX3MS1 END'));assert dig=='fnv1a64:%016x'%D.fnv1a(FIX.read_bytes())
check('standard_fnv1a64_python_and_c_fixture',fnv_vectors)
def empty_payload():
 d,e=dec(frame(b'',no_data=True,bytes_override=0,lines_override=0,digest_override='fnv1a64:%016x'%D.fnv1a(b'')));assert e and 'empty payload' in e
check('empty_frame_rejected_despite_flags',empty_payload)
def nonnewline():
 d,e=dec(frame(b'not-newline',line_term=1));assert e and ('unterminated' in e or 'final byte not newline' in e)
check('nonnewline_payload_rejected_despite_flag',nonnewline)
def numeric_and_field():
 raw=frame(b'x\n');raw=raw.replace('bytes=2','bytes=abc',1);d,e=dec(raw);assert e and 'bad numeric' in e
 raw=frame(b'x\n');raw=raw.replace('FX3MS1 BEGIN ','FX3MS1 BEGIN extra=1 ',1);d,e=dec(raw);assert e
check('bad_numeric_and_extra_field_protocol_errors',numeric_and_field)
def cap_equal_or_over():
 d,e=dec(frame(b'a'*10,cap=10,bytes_override=10,lines_override=1));assert e and ('cap' in e)
check('data_at_cap_rejected',cap_equal_or_over)
def console_noise():
 raw=(b'console noise\nnot a map at all\n'+run().stdout+b'after noise\n').decode();d,e=dec(raw);assert e is None and d['console_noise_lines']==3 and 'not a map' not in d['maps_text']
check('console_noise_ignored_not_stitched',console_noise)
def data_identity():
 d,e=dec(frame(b'x\n',data_pid=240));assert e and 'DATA identity' in e
check('data_packet_identity_mismatch_rejected',data_identity)
def stream_select():
 a=run(seq=1).stdout;b=run(seq=2).stdout;d,e=dec((a+b).decode());assert e is None and d['frame_count']==2 and d['selected_seq']==2
check('stream_selects_latest_same_identity_seq',stream_select)
def stream_no_fallback():
 a=run(seq=1).stdout;b=run(seq=2).stdout;bad='\n'.join(l for l in b.decode().splitlines() if not l.startswith('FX3MS1 END'))+'\n';d,e=dec(a.decode()+bad);assert e and 'missing END' in e
check('later_incomplete_frame_no_fallback',stream_no_fallback)
def mixed_frames():
 a=frame(b'x\n',pid=239);b=frame(b'x\n',pid=240);d,e=dec(a+b);assert e and 'mixed PID' in e
check('cross_pid_stream_rejected',mixed_frames)
def missing_end():
 raw='\n'.join(l for l in run().stdout.decode().splitlines() if not l.startswith('FX3MS1 END'));d,e=dec(raw);assert e and 'missing END' in e
check('missing_end_rejected',missing_end)
def out_of_order():
 raw=run().stdout.decode().splitlines();datas=[i for i,l in enumerate(raw) if l.startswith('FX3MS1 DATA')];assert len(datas)>=2;raw[datas[0]],raw[datas[1]]=raw[datas[1]],raw[datas[0]];d,e=dec('\n'.join(raw));assert e and ('out of order' in e or 'duplicate' in e)
check('data_out_of_order_rejected',out_of_order)
def digest_length():
 raw=run().stdout.decode().replace('digest=fnv1a64:','digest=fnv1a64:0',1);d,e=dec(raw);assert e and 'digest mismatch' in e
 raw=run().stdout.decode().replace('bytes=10563','bytes=10562',1);d,e=dec(raw);assert e and 'length mismatch' in e
check('digest_and_length_mismatch_rejected',digest_length)
def cap_overflow():
 r=run(cap=4096);assert r.returncode==4 and b'FX3MS1 ERROR' in r.stdout;d,e=dec(r.stdout.decode());assert e and 'collector ERROR' in e
check('C_cap_overflow_rejected',cap_overflow)
def short_read_more():
 r=run(extra=True);assert r.returncode==4 and b'short_read_more_data' in r.stdout;d,e=dec(r.stdout.decode());assert e and 'collector ERROR' in e
check('short_read_followed_by_extra_byte_rejected',short_read_more)
def identity_change():
 r=run(after=HERE/'tests/fixtures/stat-after-change.txt');assert r.returncode==4 and b'identity_changed' in r.stdout;d,e=dec(r.stdout.decode());assert e
check('identity_before_after_change_rejected',identity_change)
def eintr():
 r=run(eintr=True);assert r.returncode==4 and b'data_read_error' in r.stdout;d,e=dec(r.stdout.decode());assert e
check('eintr_read_error_rejected',eintr)
def unterminated():
 f=HERE/'tests/fixtures/maps-unterminated.txt';f.write_bytes(FIX.read_bytes().rstrip(b'\n'));r=run(maps=f);assert r.returncode==4;d,e=dec(r.stdout.decode());assert e and ('unterminated' in e or 'final byte not newline' in e)
check('unterminated_maps_rejected',unterminated)
def duplicate_conflict():
 raw=run().stdout.decode();d,e=dec(raw+'\n'+raw);assert e and ('sequence' in e or 'mixed' in e)
check('duplicate_frame_rejected_no_selection',duplicate_conflict)
def old_real_rejected():
 p=HERE.parent/'fx6-backup-map-parser-candidate/receipts/replay-current-official.json';d=json.loads(p.read_text());assert any(c['status']=='blocked' and c['reason']=='im_endmaps_source_is_imelf_only' for c in d['cuts'])
check('old_real_log_rejected_not_protocol_success',old_real_rejected)
def trace_order():
 TRACE.unlink(missing_ok=True);r=run(trace=True);assert r.returncode==0,r.stderr;t=TRACE.read_text().split();assert t[:4]==['open','stat_before','maps_open','data'],t;assert 'probe' in t and 'stat_after' in t and t.index('probe')<t.index('stat_after')
check('C_io_order_before-stat_data_probe_after-stat',trace_order)
def eof_fail():
 r=run(eof_fail=True);assert r.returncode==4 and b'eof_probe_error' in r.stdout;d,e=dec(r.stdout.decode());assert e
check('C_eof_probe_error_rejected',eof_fail)
def after_disappears():
 r=run(after=HERE/'tests/fixtures/no-such-stat.txt');assert r.returncode==4 and b'stat_after_error' in r.stdout;d,e=dec(r.stdout.decode());assert e
check('C_after_stat_disappear_rejected',after_disappears)
def cap_incremental():
 # cap1 + 2048-byte first chunk, no END: must reject at DATA before missing END
 b=base64.b64encode(b'x'*2048).decode();raw=f'FX3MS1 BEGIN pid=239 starttime=777 seq=1 cap=1 data_reads=1 eof_probe=1 data_attempts=1 eof_attempts=1 capture=bounded_single_read\nFX3MS1 DATA 0 239 777 1 {b}\n';d,e=dec(raw);assert e and 'cap' in e and 'missing END' not in e
check('cap1_oversize_data_rejected_at_packet',cap_incremental)
def long_index():
 raw=frame(b'x\n');raw=raw.replace('FX3MS1 DATA 0 ', 'FX3MS1 DATA '+'9'*5000+' ',1);d,e=dec(raw);assert e and 'too long' in e
check('5000_digit_DATA_index_ProtocolError',long_index)
if __name__=='__main__':
 out={'schema':'fx6-map-snapshot-protocol-tests-v1','status':'PASS_OFFLINE_C_PROTOCOL','tests':len(checks),'cases':checks,'c_source_sha256':hashlib.sha256(SRC.read_bytes()).hexdigest(),'fixture_sha256':hashlib.sha256(FIX.read_bytes()).hexdigest()}
 (HERE/'tests/test-protocol.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
