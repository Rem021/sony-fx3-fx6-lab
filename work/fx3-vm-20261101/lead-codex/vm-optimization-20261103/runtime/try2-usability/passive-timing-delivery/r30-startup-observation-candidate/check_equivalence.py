#!/usr/bin/env python3
"""Structural audit plus small observation-cost measurements; offline only."""
import ast,copy,hashlib,importlib.util,json,statistics,sys,time
from pathlib import Path
R=Path(__file__).resolve().parent;B=R.parent/'r28-first-observation-candidate';F=R.parent/'v25-r21-recovery-integration'
sys.dont_write_bytecode=True;sys.path[:0]=[str(R),str(F)]
from startup_observation import StartupObservation, PREDICATES
from test_offline import header, VirtualPath, load

def diag(n):
 return isinstance(n,ast.Attribute) and isinstance(n.value,ast.Name) and n.value.id in ['startup_observation','ACTIVE_STARTUP_OBSERVATION']
class Strip(ast.NodeTransformer):
 def visit_Call(self,n):
  self.generic_visit(n)
  if diag(n.func) and n.func.attr=='predicate':return n.args[1]
  if isinstance(n.func,ast.Name) and n.func.id in ['TrialRingReader','FullLogMonitor']:
   n.keywords=[x for x in n.keywords if x.arg not in ('startup_observation','request_sequence')]
  return n
 def visit_Expr(self,n):
  if isinstance(n.value,ast.Call) and diag(n.value.func):return None
  return self.generic_visit(n)
 def visit_Assign(self,n):
  if any(isinstance(t,ast.Name) and t.id in ('startup_observation','ACTIVE_STARTUP_OBSERVATION') for t in n.targets):return None
  return self.generic_visit(n)
 def visit_If(self,n):
  if any(isinstance(x,ast.Name) and x.id=='ACTIVE_STARTUP_OBSERVATION' for x in ast.walk(n.test)):return None
  return self.generic_visit(n)
 def visit_Dict(self,n):
  pairs=[(k,v) for k,v in zip(n.keys,n.values) if not(isinstance(k,ast.Constant) and k.value=='startup_observation')]
  n.keys=[x[0] for x in pairs];n.values=[x[1] for x in pairs];return self.generic_visit(n)
 def visit_List(self,n):
  n.elts=[x for x in n.elts if not(isinstance(x,ast.Constant) and x.value=='startup_observation.py')];return self.generic_visit(n)
 def visit_Global(self,n):
  n.names=[x for x in n.names if x!='ACTIVE_STARTUP_OBSERVATION'];return n if n.names else None
 def visit_ImportFrom(self,n):
  return None if n.module=='startup_observation' else n
old=ast.parse((B/'run_trial_r24_review_snapshot.py').read_text());new=ast.parse((R/'run_trial_r24_review_snapshot.py').read_text())
assert ast.dump(old,include_attributes=False)==ast.dump(Strip().visit(new),include_attributes=False),'runner changed outside observational additions'
# Monitor: remove only constructor parameter/assignment and raw chunk hook.
a=ast.parse((F/'trial_log_v4_mss.py').read_text());b=ast.parse((R/'trial_log_v4_mss.py').read_text())
class MonitorStrip(ast.NodeTransformer):
 def visit_FunctionDef(self,n):
  if n.name=='__init__':n.args.kwonlyargs=[];n.args.kw_defaults=[]
  return self.generic_visit(n)
 def visit_Assign(self,n):
  if any(isinstance(x,ast.Attribute) and x.attr=='startup_observation' for x in n.targets):return None
  if any(isinstance(x,ast.Name) and x.id=='chunk_start' for x in n.targets):return None
  return self.generic_visit(n)
 def visit_If(self,n):
  if any(isinstance(x,ast.Attribute) and x.attr=='startup_observation' for x in ast.walk(n.test)):return None
  return self.generic_visit(n)
assert ast.dump(a,include_attributes=False)==ast.dump(MonitorStrip().visit(b),include_attributes=False),'serial functional code drift'
# Original cached poll/slot guards/evidence untouched. Header override is exercised dynamically.
a=ast.parse((F/'trial_ring_cached.py').read_text());b=ast.parse((R/'trial_ring_cached.py').read_text())
for name in ('validate_slot','poll','evidence'):
 def get(tree):return next(x for x in ast.walk(tree) if isinstance(x,ast.FunctionDef) and x.name==name)
 assert ast.dump(get(a),include_attributes=False)==ast.dump(get(b),include_attributes=False),name
# Cost: median three runs of new callbacks; not QMP/VM end-to-end performance.
bench={};h=header();words=h[:128]
for kind in ['header','ready','ready_all_13']:
 rows=[]
 for rep in range(3):
  ob=StartupObservation(R/'evidence');begin=time.perf_counter_ns()
  for i in range(10000):
   if kind=='header':ob.header_read(before_ns=1,after_ns=2,request_id_before=i,request_id_after=i+1,returned=h,file_length=256,prefix=words,source='benchmark',outcome='returned')
   else:
    ob.begin_ready()
    if kind=='ready_all_13':
     for k in PREDICATES:ob.predicate(k,True)
    else:ob.predicate('phaseA_unobserved',True);ob.predicate('replay_input_verified',False)
    ob.end_ready(qualified=False,last_screen_observed_at=1,frame=None)
  elapsed=time.perf_counter_ns()-begin;rows.append(elapsed)
 bench[kind]={'iterations':10000,'elapsed_ns_samples':rows,'median_ns_per_observation':statistics.median(rows)/10000}
raw=(R.parent.parent/'runs/v25gate-n64-r17-f7903939/serial.log').read_bytes();bench['serial_marker_only']={}
for rep in range(3):
 ob=StartupObservation(R/'evidence');begin=time.perf_counter_ns()
 for start in range(0,len(raw),65536):ob.serial_chunk(start,raw[start:start+65536],min(start+65536,len(raw)))
 elapsed=time.perf_counter_ns()-begin
 bench['serial_marker_only'][str(rep)]={'bytes':len(raw),'elapsed_ns':elapsed,'ns_per_byte':elapsed/len(raw)}
out={'runner_AST_after_removing_only_observation_additions_matches_r28':True,'monitor_original_functional_AST_matches_r21':True,
 'ring_original_validate_poll_evidence_AST_unchanged':True,'benchmark':bench,
 'benchmark_scope':'new callbacks only; no fsync or writes in measured loops; no fake result claimed as VM/QMP latency; host scheduling and serial read timing can still be perturbed'}
(R/'evidence/STRUCTURAL-AND-COST.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
