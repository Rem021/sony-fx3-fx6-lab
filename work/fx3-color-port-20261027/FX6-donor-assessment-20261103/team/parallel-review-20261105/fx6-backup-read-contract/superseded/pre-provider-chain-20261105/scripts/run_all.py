#!/usr/bin/env python3
import datetime,hashlib,json,os,shutil,subprocess,sys,time
from pathlib import Path
R=Path(__file__).resolve().parent; RAW=R/'receipts/raw'; RAW.mkdir(parents=True,exist_ok=True)
CASES=[('ccmp-host-test',['python3','scripts/run_ccmp_test.py']),('reader-semantics',['python3','scripts/analyze_reader.py']),('producer-chain',['python3','scripts/analyze_producer.py']),('migration-dry-run',['python3','scripts/migration_dry_run.py']),('input-seal-after',['python3','input_seal.py','after'])]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
 started=datetime.datetime.now(datetime.timezone.utc).isoformat();rows=[];failed=False
 for name,argv in CASES:
  t0=time.monotonic();p=subprocess.run(argv,cwd=R,text=True,capture_output=True,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'});elapsed=time.monotonic()-t0
  (RAW/(name+'.stdout.txt')).write_text(p.stdout);(RAW/(name+'.stderr.txt')).write_text(p.stderr)
  rows.append({'case':name,'argv':argv,'returncode':p.returncode,'elapsed_seconds':elapsed,'stdout_tail':p.stdout[-2500:],'stderr_tail':p.stderr[-2500:]});print(('PASS' if p.returncode==0 else 'FAIL'),name);failed|=p.returncode!=0
 before=json.loads((R/'receipts/before-input-seal.json').read_text());after=json.loads((R/'receipts/after-input-seal.json').read_text())
 b={x['path']:x['sha256'] for x in before['inputs']};a={x['path']:x['sha256'] for x in after['inputs']};changed=sorted(k for k in set(b)|set(a) if b.get(k)!=a.get(k));cmp={'schema':'fx6-r50-backup-read-input-compare-v1','count':len(b),'changed':changed,'unchanged':not changed and before['count']==after['count']==18}
 (R/'receipts/input-seal-compare.json').write_text(json.dumps(cmp,indent=2)+'\n')
 if not cmp['unchanged']:failed=True
 receipts={p.name:{'sha256':sha(p),'bytes':p.stat().st_size} for p in sorted((R/'receipts').glob('*.json')) if p.name!='test-run.json'}
 run={'schema':'fx6-r50-backup-read-test-run-v1','offline':True,'browser':False,'server':False,'VM':False,'QMP':False,'guest':False,'started_utc':started,'finished_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'cases':rows,'cases_failed':sum(1 for x in rows if x['returncode']),'input_seal':cmp,'receipts':receipts,'passed':not failed}
 (R/'receipts/test-run.json').write_text(json.dumps(run,indent=2)+'\n')
 for p in sorted(R.rglob('__pycache__'),reverse=True):shutil.rmtree(p,ignore_errors=True)
 print(json.dumps({'passed':not failed,'cases':len(rows),'failed':run['cases_failed'],'input_unchanged':cmp['unchanged'],'receipt':str(R/'receipts/test-run.json')}))
 return 0 if not failed else 1
if __name__=='__main__':sys.exit(main())
