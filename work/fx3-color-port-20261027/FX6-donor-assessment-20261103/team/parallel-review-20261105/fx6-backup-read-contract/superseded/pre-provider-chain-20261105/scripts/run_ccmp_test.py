#!/usr/bin/env python3
"""Compile/run finite integer cmp/ccmp/b.eq test on Apple arm64; no firmware/VM."""
import hashlib,json,platform,subprocess
from pathlib import Path
C=Path(__file__).resolve().parent.parent; T=C/'tests'; OUT=C/'receipts'; OUT.mkdir(exist_ok=True)
def h(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
 exe=T/'ccmp_test'
 cmd=['clang','-arch','arm64','-O0','-o',str(exe),str(T/'ccmp_test.s'),str(T/'ccmp_driver.c')]
 comp=subprocess.run(cmd,capture_output=True,text=True)
 assert comp.returncode==0,comp.stderr
 run=subprocess.run([str(exe)],capture_output=True,text=True); assert run.returncode==0,run.stderr
 (T/'ccmp-test-output.txt').write_text(run.stdout)
 rows=[]
 for line in run.stdout.splitlines():
  p=dict(x.split('=') for x in line.split())
  rows.append({'actual':int(p['actual']),'capacity':int(p['cap']),'flag':int(p['flag']),'beq':int(p['b.eq'])})
 expected=[]; got=[]
 for actual in (0,1,4,5):
  for flag in (0,1):
   expected.append({'actual':actual,'capacity':4,'flag':flag,'beq':1 if actual>4 and flag==1 else 0})
 got=[{'actual':r['actual'],'capacity':r['capacity'],'flag':r['flag'],'beq':r['beq']} for r in rows]
 assert got==expected,(got,expected)
 value={'schema':'fx6-ccmp-host-test-v1','host':platform.platform(),'machine':platform.machine(),'compiler':'Apple clang','compile_cmd':cmd,'compile_stdout':comp.stdout,'compile_stderr':comp.stderr,'run_stdout':run.stdout,'cases':got,'expected':'b.eq only when actual>capacity && flag==1; actual==capacity gives CCMP NZCV=0, Z=0','all_match':True,
  'source_hashes':{'ccmp_test.s':h(T/'ccmp_test.s'),'ccmp_driver.c':h(T/'ccmp_driver.c')},'binary_sha256':h(exe),'semantics':'finite host integer test; no firmware/system registers/VM'}
 (OUT/'ccmp-host-test.json').write_text(json.dumps(value,indent=2)+'\n'); print(json.dumps({'all_match':True,'cases':got,'binary_sha256':value['binary_sha256'],'receipt':str(OUT/'ccmp-host-test.json')},indent=2))
if __name__=='__main__':main()
