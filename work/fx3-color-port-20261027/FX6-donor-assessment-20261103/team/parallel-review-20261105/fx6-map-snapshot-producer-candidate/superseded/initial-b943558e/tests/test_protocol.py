#!/usr/bin/env python3
"""Compile/run the tiny C reader on fixtures; validate protocol rejection paths."""
import base64,hashlib,json,subprocess,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent.parent;sys.path.insert(0,str(HERE));import decode_snapshot as D
FIX=HERE/'tests/fixtures/maps-8955-9222.txt';C=HERE/'fx3_map_snapshot';SRC=HERE/'fx3_map_snapshot.c';checks=[]
def check(n,f):f();checks.append(n)
def run(fixture=FIX,cap=None,start=1234,pid=239,seq=1):
 args=[str(C),str(pid),str(seq),'--fixture',str(fixture),'--starttime',str(start)]
 if cap:args+=['--cap',str(cap)]
 return subprocess.run(args,capture_output=True)
def dec(text):
 try:return D.decode(text),None
 except D.ProtocolError as e:return None,str(e)
def compile_reader():
 r=subprocess.run(['cc','-std=c11','-O2','-Wall','-Wextra','-o',str(C),str(SRC)],capture_output=True,text=True);assert r.returncode==0,r.stderr
check('c_reader_compiles_stdlib_only',compile_reader)
def accepted():
 r=run();assert r.returncode==0,r.stderr;d,e=dec(r.stdout.decode());assert e is None and d['status'].startswith('ACCEPTED');assert d['pid']==239 and d['bytes']==FIX.stat().st_size;assert d['bytes']==10563;assert d['snapshot_atomic'] is False;assert 'appFw.so' in d['maps_text'] and d['maps_text'].count('/usr/bin/im.elf')>=3
check('c_single_read_fixture_decodes_with_digest_and_lines',accepted)
def noise():
 r=run();raw=b'console noise before\nthis is not a map\n'+r.stdout+b'console noise after\n';d,e=dec(raw.decode());assert e is None and d['console_noise_lines']==3 and 'not a map' not in d['maps_text']
check('console_noise_ignored_not_stitched',noise)
def mixed():
 a=run(pid=239).stdout;b=run(pid=240).stdout;d,e=dec((a+b).decode());assert e and 'exactly one' in e
check('mixed_pid_frames_rejected',mixed)
def missing_end():
 raw=run().stdout.decode();raw='\n'.join(l for l in raw.splitlines() if not l.startswith('FX3MS1 END'));d,e=dec(raw);assert e and 'missing END' in e
check('missing_end_rejected',missing_end)
def reordered():
 raw=run().stdout.decode().splitlines();datas=[i for i,l in enumerate(raw) if l.startswith('FX3MS1 DATA')];assert len(datas)>=2;raw[datas[0]],raw[datas[1]]=raw[datas[1]],raw[datas[0]];d,e=dec('\n'.join(raw));assert e and ('out of order' in e or 'duplicate' in e)
check('data_out_of_order_rejected',reordered)
def bad_digest():
 raw=run().stdout.decode();raw=raw.replace('digest=fnv1a64:', 'digest=fnv1a64:0',1);d,e=dec(raw);assert e and 'digest mismatch' in e
check('digest_mismatch_rejected',bad_digest)
def bad_length():
 raw=run().stdout.decode();raw=raw.replace('bytes=10563','bytes=10562',1);d,e=dec(raw);assert e and 'length mismatch' in e
check('length_mismatch_rejected',bad_length)
def overflow():
 r=run(cap=4096);assert r.returncode==4 and b'FX3MS1 ERROR' in r.stdout;d,e=dec(r.stdout.decode());assert e and 'collector ERROR' in e
check('cap_overflow_rejected',overflow)
def unterminated():
 f=HERE/'tests/fixtures/maps-unterminated.txt';f.write_bytes(FIX.read_bytes().rstrip(b'\n'));r=run(fixture=f);assert r.returncode==4;d,e=dec(r.stdout.decode());assert e and 'unterminated' in e
check('unterminated_maps_rejected',unterminated)
def old_real_rejected():
 p=HERE.parent/'fx6-backup-map-parser-candidate/receipts/replay-current-official.json';assert p.exists();d=json.loads(p.read_text());assert any(c['status']=='blocked' and c['reason']=='im_endmaps_source_is_imelf_only' for c in d['cuts'])
check('old_real_log_source_rejected_not_protocol_success',old_real_rejected)
def identity_change():
 raw=run().stdout.decode().replace('starttime=1234','starttime=9999',1);d,e=dec(raw);assert e and 'identity change' in e
check('identity_change_rejected',identity_change)
def duplicate_conflict():
 raw=run().stdout.decode();raw=raw+'\n'+raw;d,e=dec(raw);assert e
check('duplicate_conflict_rejected',duplicate_conflict)
if __name__=='__main__':
 out={'schema':'fx6-map-snapshot-protocol-tests-v1','status':'PASS_OFFLINE_C_PROTOCOL','tests':len(checks),'cases':checks,'c_source_sha256':hashlib.sha256(SRC.read_bytes()).hexdigest(),'fixture_sha256':hashlib.sha256(FIX.read_bytes()).hexdigest()}
 (HERE/'tests/test-protocol.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
