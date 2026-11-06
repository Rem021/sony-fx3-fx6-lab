#!/usr/bin/env python3
"""Read only owning AST constants; do not import/execute any runner."""
from pathlib import Path
import ast,json,re,hashlib,subprocess,sys
O=Path(__file__).resolve().parent;D=O.parent
new=(O/'receipts/ui-candidate.stdout').read_bytes();old=(O/'receipts/ui-baseline.stdout').read_bytes();lines=new.splitlines(True)
def node(path,name):
 for x in ast.parse(path.read_text()).body:
  if isinstance(x,ast.Assign) and any(isinstance(t,ast.Name) and t.id==name for t in x.targets):return x.value
 raise KeyError(name)
# r32 is actually a prefix regex: it still accepts old fields on the appended line.
p=D/'r32-zero-ring-causal-review/analyze_zero_ring.py';gate=re.compile(ast.literal_eval(node(p,'GATE').args[0]));assert [m.groups() for m in gate.finditer(old)]==[m.groups() for m in gate.finditer(new)]
# Opportunities analyzer uses exact ordered field list; it rejects an appended field.
keys='id n tid pc object a18 a12 a13 r0 decision_a18 elapsed old_time new_time message type source observed_only'.split()
def strict(line):
 a=line.rstrip(b'\r\n').split(b' ',1)[1].split();pairs=[v.split(b'=',1) for v in a];return len(pairs)==len(keys) and all(len(v)==2 and v[0].decode()==k for v,k in zip(pairs,keys))
assert all(strict(x) for x in old.splitlines(True));assert sum(not strict(x) for x in lines)==1
# Runtime monitor and startup predicates do not parse this UI_SAMPLE record.
p=D/'r30-startup-observation-candidate/trial_log_v4_mss.py';keep=re.compile(ast.literal_eval(node(p,'KEEP').args[0]));failures=ast.literal_eval(node(p,'FAILURES'))
for b,c in zip(old.splitlines(True),new.splitlines(True)):
 b=b.decode();c=c.decode();assert bool(keep.search(b))==bool(keep.search(c));assert [bool(re.search(pat,b,re.I)) for pat,_ in failures]==[bool(re.search(pat,c,re.I)) for pat,_ in failures]
p=D/'r30-startup-observation-candidate/startup_observation.py';markers=ast.literal_eval(node(p,'MARKERS'));assert all(old.count(m)==new.count(m) for m in markers)
# Actual CLI never joins a partial line across End. Long-line failures are structured.
cli=[]
for name,b in [('long-no-LF',b'x'*22000),('long-complete-and-fragment',b'x'*22000+b'\n'+lines[0][:-10]),('candidate-complete',new)]:
 f=O/'tests'/('parser-'+name+'.bin');f.write_bytes(b);args=[sys.executable,'-B',str(O/'parse_r35.py'),str(f),'--run-id','offline-fixture-r35-'+name,'--end-byte',str(len(b))];r=subprocess.run(args,capture_output=True);(O/'receipts'/('parser-CLI-'+name+'.stdout')).write_bytes(r.stdout);(O/'receipts'/('parser-CLI-'+name+'.stderr')).write_bytes(r.stderr);assert not r.returncode;rj=json.loads(r.stdout)
 if name!='candidate-complete':assert not rj['records'] and rj['unknown']
 else:assert len(rj['records'])==1
 cli.append({'argv':args,'exit':r.returncode,'valid_records':len(rj['records']),'unknown':rj['unknown']})
result={'r32_prefix_regex_same_original_captures':True,'opportunities_strict_exact_fields_rejects_suffix_records':1,'runtime_KEEP_FAILURES_MARKERS_same_results_on_actual_selected_fixture':True,'scope':'No runtime/ready consumer changed. Added bytes affect offsets/serial volume and can perturb timing; this is not runtime admission equivalence.','CLI':cli}
(O/'PARSER-COMPATIBILITY.json').write_text(json.dumps(result,indent=2)+'\n');print('actual prior parser/constants and actual CLI long-line/End checks PASS')
