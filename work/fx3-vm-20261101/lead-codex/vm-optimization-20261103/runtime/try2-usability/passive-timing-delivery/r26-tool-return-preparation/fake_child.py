#!/usr/bin/env python3
"""HISTORICAL OFFLINE REPLAY ONLY. Not imported or reachable by the production CLI."""
import argparse,json,os,shutil,sys,time
from pathlib import Path
if os.environ.get('FX3_RETURN_FIXTURE_ONLY')!='1':raise SystemExit('test-only fake child requires explicit fixture environment')
p=argparse.ArgumentParser();p.add_argument('case');p.add_argument('root');a=p.parse_args();root=Path(a.root);samples=Path(__file__).resolve().parent/'samples'
case=a.case
if case=='confirmation':
 receipt=json.loads((samples/'confirmation.json').read_text());print(json.dumps({'status':receipt['status'],'step':receipt['step'],'elapsed_ms':receipt['browser_result']['cancelled']['events'][-1]['elapsed_ms'],'fixture_only':True}));raise SystemExit(0)
fixed=case=='fixed';v=json.loads((samples/('fixed.json' if fixed else 'observation.json')).read_text());image=root/('source-'+case+'.png');shutil.copyfile(samples/('fixed.png' if fixed else 'observation.png'),image)
v['screenshot_path']=str(image);v['fixture_only']='historical replay; not current firmware/native/semantic evidence'
if case=='stale_png':os.utime(image,ns=(time.time_ns()-30_000_000_000,time.time_ns()-30_000_000_000))
raw=json.dumps(v,ensure_ascii=False)
print('HISTORICAL FIXTURE CHILD, no original action or VM',file=sys.stderr)
if case=='current_only':print('{}')
elif case=='invalid':print('this is not JSON')
elif case=='truncated':sys.stdout.write(raw[:len(raw)//2])
else:print(raw)
raise SystemExit(7 if case=='nonzero' else 0)
