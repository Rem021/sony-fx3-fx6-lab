"""Actual candidate compilation and bounded host-only cases. No guest execution."""
from pathlib import Path
import hashlib,json,os,subprocess,sys,time
O=Path(__file__).resolve().parent;G=Path('/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/lead-claude/impl/gpe-perf');H=G.parents[3]/'menu-repair-01/runtime/helpers'
# Resolve H from the accepted actual recipe, never from a runner import.
binding=json.loads((O/'BINDING.json').read_text());recipe=binding['original_recipe'];H=Path(recipe[recipe.index('-I',recipe.index('-I')+1)+1]);rows=[]
def run(name,argv,env=None):
 p=subprocess.run(argv,capture_output=True,env=env or {**os.environ,'PYTHONDONTWRITEBYTECODE':'1'});(O/'receipts'/(name+'.stdout')).write_bytes(p.stdout);(O/'receipts'/(name+'.stderr')).write_bytes(p.stderr);rows.append({'name':name,'argv':argv,'exit':p.returncode});(O/'BUILD-COMMANDS.json').write_text(json.dumps(rows,indent=2)+'\n');assert not p.returncode,(name,p.stderr.decode()[-2500:]);return p.stdout.decode()
# Both host programs compile the full owning source plus the same real backend;
# the seam mocks IO/native/clock, with only the original HOST_TEST ISA switches.
for candidate in (False,True):
 source=O/'src/fx3-gpe-observe-v26-perf.c' if candidate else G/'fx3-gpe-observe-v26-perf.c';name='host-candidate' if candidate else 'host-original'
 args=['/usr/bin/clang','-std=gnu11','-O2','-I',str(G),'-I',str(H),'-DTEST_CANDIDATE='+str(int(candidate)),'-DADAPTER_SOURCE="'+str(source)+'"',str(O/'tests/host_seam.c'),str(G/'fx3-gpe-backend-v9.c'),'-o',str(O/'build'/name)]
 run('compile-'+name,args)
checks=[]
for case in range(5):
 outputs=[]
 for cand in (False,True):
  label='candidate' if cand else 'original';text=run('case-'+str(case)+'-'+label,[str(O/'build'/('host-'+label)),str(case)]);summary=json.loads(next(line[8:] for line in text.splitlines() if line.startswith('SUMMARY ')));logs=[line[4:] for line in text.splitlines() if line.startswith('LOG ')];outputs.append((summary,logs))
 a,alogs=outputs[0];b,blogs=outputs[1]
 assert b['clock_calls']==a['clock_calls']+1
 for k in ('result','errno','first_read_errno','log_calls','callback_calls','SendDrawComp_calls','pixels','callback_order'):assert a[k]==b[k],(case,k,a,b)
 assert b['effects'][0]=='C' and b['effects'][1:]==a['effects'],(case,a['effects'],b['effects'])
 ar=next(x for x in alogs if x.startswith('FX3_GPE104_CMD_RETURN '));br=next(x for x in blogs if x.startswith('FX3_GPE104_CMD_RETURN '));prefix,entry=br.rsplit(' entry_ns=',1);assert prefix==ar,(case,ar,br)
 assert int(entry)==(0 if case in (3,4) else 1000000000)
 assert len([x for x in blogs if x.startswith('FX3_GPE104_CMD_RETURN ')])==1
 checks.append({'case':case,'case_name':['success_callback_and_SendDrawComp','entry_rejection','gpe102_take_failure_early_return','entry_clock_failure','entry_clock_zero'][case],'original':a,'candidate':b,'original_CMD_RETURN_prefix_exact':True,'extra_clock_calls':1,'extra_log_calls':0,'entry_ns':int(entry)})
(O/'HOST-TESTS.json').write_text(json.dumps({'fixture_only':True,'actual_candidate_source':str(O/'src/fx3-gpe-observe-v26-perf.c'),'cases':checks,'passed':True,'limits':'host IO/native/clock mocked; real full adapter/backend code; no guest or QEMU performance claim'},indent=2)+'\n')
# Same cross recipe; primary source/header override and output/cache paths only.
env={**os.environ,'ZIG_LOCAL_CACHE_DIR':str(O/'build/zig-local'),'ZIG_GLOBAL_CACHE_DIR':str(O/'build/zig-global')}
for candidate in (False,True):
 name='candidate' if candidate else 'baseline';args=list(recipe);args[args.index('-o')+1]=str(O/'build'/('gpe-r41-'+name+'.so'))
 if candidate:
  args[args.index(str(G/'fx3-gpe-observe-v26-perf.c'))]=str(O/'src/fx3-gpe-observe-v26-perf.c');args[2:2]=['-I',str(O/'src')]
 run('cross-'+name,args,env)
print('PASS actual host seam 5 paired cases and AArch64 recipe compilation')
