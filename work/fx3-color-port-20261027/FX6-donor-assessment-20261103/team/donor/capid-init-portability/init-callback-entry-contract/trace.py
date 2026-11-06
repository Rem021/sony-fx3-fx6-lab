import sys
sys.dont_write_bytecode=True
from pathlib import Path
import subprocess,struct,json,re,hashlib
H=Path(__file__).resolve().parent;B=H.parent
ns={'__file__':str(B/'analyze.py')};exec((B/'analyze.py').read_text().split('E={k:ELF')[0],ns)
P=ns['P'];E={k:ns['ELF'](p) for k,p in P.items()};sha=lambda b:hashlib.sha256(b).hexdigest()
old=json.loads((B/'receipt.json').read_text());assert all(sha(e.b)==old['hashes'][k] for k,e in E.items())
def dis(k,a,z):
 t=subprocess.check_output(['xcrun','llvm-objdump','-d',f'--start-address={a}',f'--stop-address={z}',str(P[k])],text=True);(H/f'{k}-{a:x}-{z:x}.txt').write_text(t);return t
if __name__=='__main__':
 if len(sys.argv)!=4:raise SystemExit('usage: trace.py INPUT_KEY START_VA END_VA (targeted range only)')
 print(dis(sys.argv[1],int(sys.argv[2],0),int(sys.argv[3],0)))
