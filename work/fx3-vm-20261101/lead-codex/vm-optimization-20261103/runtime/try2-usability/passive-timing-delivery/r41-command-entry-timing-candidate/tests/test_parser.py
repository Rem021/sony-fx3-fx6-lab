"""Positive/negative independent byte fixtures, chunk equivalence and legacy replay."""
from pathlib import Path
import collections,hashlib,json,subprocess,sys
O=Path(__file__).resolve().parents[1];sys.path.insert(0,str(O));from parse_command_timing import Parser,read
rows=[]
def line(seq=1,tid=7,tp=0x123,entry=100,end=160,op=0):
 suffix='' if entry is None else ' entry_ns='+str(entry)
 return ('FX3_GPE104_CMD_RETURN tid=%d tpidr=%#x ns=%d seq=%d op=%d completion_source=0x123 result=0 errno=17 call_path=adapter_return_to_original_Main unchanged=1%s\n'%(tid,tp,end,seq,op,suffix)).encode()
def parse(data,step=7):
 p=Parser('fixture-only')
 for i in range(0,len(data),step):p.feed(data[i:i+step])
 return p.finish()
valid=line()+b'FX3_OTHER complete separate line\n'+line(2,entry=190,end=230,op=1)
v=parse(valid);assert [r['duration_ns'] for r in v['records']]==[60,40] and v['records'][1]['previous_return_to_entry_ns']==30
for chunk in (1,2,31,4096):assert parse(valid,chunk)==v
rows.append({'case':'ordered_same_thread_and_chunking','passed':True,'duration_ns':[60,40],'gap_ns':30})
for name,data,reason in [('missing',line(entry=None),'missing_entry'),('zero',line(entry=0),'zero_entry_unknown'),('negative_duration',line(entry=170),'end_before_entry'),('duplicate',line()+line(),'duplicate_or_conflicting_seq_tid_op'),('conflicting_op',line()+line(op=1),'duplicate_or_conflicting_seq_tid_op'),('truncated',line()[:-4],'incomplete_at_cutoff_or_EOF'),('interleaved',line()[:-1]+b' FX3_OTHER x=1\n','malformed_or_interleaved_record'),('bad_prefix',b'\x00'+line(),'malformed_or_interleaved_record'),('range',line(entry=2**64),'entry_range'),('zero_end',line(entry=0,end=0),'end_unknown_or_range'),('overlong',line()[:-1]+b'x'*5000+b'\n','overlong_or_truncated_record')]:
 v=parse(data);assert not v['known_durations'] and reason in v['unknown_reason_counts'],(name,v);rows.append({'case':name,'passed':True,'unknown_reason':reason})
# A malformed record blocks only the inter-command gap, not valid local samples.
v=parse(line()+b'FX3_GPE104_CMD_RETURN mixed\n'+line(2,entry=200,end=220));assert v['known_durations']==2 and v['known_same_thread_gaps']==0
rows.append({'case':'damaged_boundary_no_gap','passed':True})
v=parse(line()+line(2,tid=8,entry=200,end=220));assert v['known_durations']==2 and v['known_same_thread_gaps']==0
rows.append({'case':'different_threads_never_subtracted','passed':True})
v=parse(line()+line(3,entry=200,end=220));assert v['known_same_thread_gaps']==0
v=parse(line()+line(2,entry=150,end=180));assert v['known_same_thread_gaps']==0
rows.append({'case':'seq_gap_and_overlap_unknown','passed':True})
# Scope boundary never joins a partial line from one run to another.
a=Parser('A');a.feed(line()[:45]);b=Parser('B');b.feed(line()[45:]);assert a.finish()['known_durations']==b.finish()['known_durations']==0
rows.append({'case':'run_cutoff_boundary_not_joined','passed':True})
# Replay actual host-produced candidate logs: one exact sample per case, both paths.
for case in range(5):
 data=(O/'receipts'/('case-%d-candidate.stdout'%case)).read_bytes();logs=b''.join(x[4:]+b'\n' for x in data.splitlines() if x.startswith(b'LOG '));v=parse(logs)
 assert v['record_count']==1 and v['known_durations']==(0 if case in (3,4) else 1),(case,v)
rows.append({'case':'actual_candidate_host_lines','passed':True})
D=O.parent;meta=json.loads((D/'r40-deepseek-menu-timing/review-revision-1/results.json').read_text());native=meta['native_run'];native=native['path'] if isinstance(native,dict) else native;serial=(Path(native) if Path(native).is_absolute() else D.parent/'runs'/native)/'serial.log'
assert serial.is_file(),native
# This is a compatibility replay of the ENTIRE historical file, including
# cleanup. It is NOT an End cutoff or a startup/menu success assertion.
v=read(serial,'r38-historical-compatibility-entire-file',serial.stat().st_size);assert v['known_durations']==0 and v['known_same_thread_gaps']==0 and v['unknown_reason_counts'].get('missing_entry',0)>0
(O/'R38-COMPATIBILITY.json').write_text(json.dumps({'scope':'entire original historical serial including cleanup; compatibility only, not End/startup attribution','serial':str(serial),'serial_sha256':hashlib.sha256(serial.read_bytes()).hexdigest(),'cutoff_byte':serial.stat().st_size,'summary':{k:v[k] for k in ('record_count','known_durations','known_same_thread_gaps','unknown_reason_counts')},'rows':v['records']},indent=2)+'\n')
# Pin only this additional actual-used file, rather than old timing input matrices.
(O/'ADDITIONAL-INPUTS-BEFORE.json').write_text(json.dumps({str(serial):{'sha256':hashlib.sha256(serial.read_bytes()).hexdigest(),'bytes':serial.stat().st_size}},indent=2)+'\n')
rows.append({'case':'actual_r38_legacy_no_entry_unknown','passed':True,'record_count':v['record_count'],'reasons':v['unknown_reason_counts']})
(O/'PARSER-TESTS.json').write_text(json.dumps({'passed':True,'cases':rows},indent=2)+'\n');print('parser PASS',len(rows),'bounded groups; historical replay unknown')
