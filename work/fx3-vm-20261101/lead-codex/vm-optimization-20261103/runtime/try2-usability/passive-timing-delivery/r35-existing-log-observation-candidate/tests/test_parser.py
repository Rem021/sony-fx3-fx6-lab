from pathlib import Path
import importlib.util,json,sys
O=Path(__file__).resolve().parents[1];spec=importlib.util.spec_from_file_location('parse_r35',O/'parse_r35.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
b=(O/'receipts/collector-log.stdout').read_bytes();lines=b.splitlines(True);main=lines[:7]
def parse(b,chunk=1):
 q=m.Parser()
 for i in range(0,len(b),chunk):q.feed(b[i:i+chunk])
 return q.end()
def modify(line,index,value):
 stem,h=line.split(b' r35v1=');w=[int(h[i:i+8],16) for i in range(0,176,8)];w[index]=value;w[21]=m.fnv(w);return stem+b' r35v1='+''.join(f'{x:08x}' for x in w).encode()+b';\n'
r=parse(b''.join(main));assert len(r['records'])==7 and not r['unknown'];assert r['records'][-1]['budget_terminal'];assert r['records'][0]['publication']=='collector_unready';assert r['records'][2]['publication']=='captured_attempt_return_unknown';assert r['records'][-2]['bind']=='original_bind_succeeded_magic_observed'
checks={'actual_candidate_7_suffixes':True}
for size in (1,2,7,183,184,185,4096):
 assert parse(b''.join(main),size)==r
assert len(parse(b''.join(main).replace(b'\n',b'\r\n'))['records'])==7
checks['cross_chunk_all_fields_and_original_CRLF']=True
for cut in range(len(main[5])-1):
 x=parse(main[5][:cut]);assert not x['records']
checks['all_line_truncation_and_End_boundaries']=True
q=m.Parser();q.feed(main[0][:-1]);assert not q.end()['records']
try:q.feed(b'\n');raise AssertionError()
except ValueError:pass
checks['no_join_across_End']=True
for i,v in [(0,1),(1,0),(2,123),(3,0),(6,4),(7,0x2000),(9,3),(10,5),(11,0),(12,0),(14,2),(18,8),(19,999),(20,0)]:
 bad=modify(main[5],i,v);x=parse(bad);assert not x['records'],(i,x)
checks['negative_ABI_source_identity_phases_rc_magic_budget']=True
bad=bytearray(main[5]);at=bad.index(b'r35v1=')+8;bad[at]=ord('f') if bad[at]!=ord('f') else ord('0');assert not parse(bytes(bad))['records']
for bad in [main[5].replace(b'observed_only=1',b'observed_only=0'),main[5].replace(b'id=9',b'id=99'),main[5].replace(b'n=1 ',b'n=51 '),b'junk\x00'+main[5],main[5].replace(b' r35v1=',b' other=1 r35v1='),main[5].replace(b';\n',b';more\n')]:assert not parse(bad)['records']
checks['tamper_and_interleaving_rejected']=True
x=parse(main[0]+main[2]);assert any(a['reason']=='export_record_gap' for a in x['unknown'])
x=parse(main[2]+main[1]);assert any(a['reason']=='duplicate_or_out_of_order' for a in x['unknown'])
x=parse(main[1]+modify(main[2],4,12345));assert any(a['reason']=='collector_instance_changed' for a in x['unknown'])
x=parse(main[2]+modify(main[3],6,0));assert len(x['records'])==1
x=parse(main[2]+main[2]);assert len(x['records'])==1
checks['loss_order_reload_duplicate_first_record_immutable']=True
assert parse(b'old log with no exporter\n')['overall']=='no_complete_export_unknown';assert parse(b'')['overall']=='no_complete_export_unknown'
for chunk in (1,4096,50000):
 x=parse(b'x'*22000+b'\n'+main[0],chunk);assert len(x['records'])==1 and x['unknown']
 x=parse(b'x'*22000+main[0],chunk);assert not x['records'] and x['unknown']
 x=parse(b'x'*22000,chunk);assert not x['records'] and x['unknown']
checks['overlong_partial_complete_line_chunked_unknown_not_exception']=True
# Original send failure vs bind failure are distinct states, not inferred by absence.
x=parse(modify(main[3],8,0xfffffff1));assert x['records'][0]['publication']=='original_send_failed'
y=main[5]
for i,v in [(10,0xfffffffc),(11,2),(12,0),(13,0)]:y=modify(y,i,v)
assert parse(y)['records'][0]['bind']=='original_bind_failed';checks['separate_send_and_bind_results']=True
(O/'PARSER-TEST.json').write_text(json.dumps({'checks':checks,'count':len(checks),'fixture_only':True},indent=2)+'\n');(O/'PARSED-FIXTURE.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(checks))
