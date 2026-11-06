from pathlib import Path
import subprocess,json,hashlib,re,sys
H=Path(__file__).resolve().parent;B=H.parent
ns={'__file__':str(B/'analyze.py')};exec((B/'analyze.py').read_text().split('E={k:ELF')[0],ns)
P=ns['P'];E={k:ns['ELF'](p) for k,p in P.items()};sha=lambda b:hashlib.sha256(b).hexdigest()
old=json.loads((B/'receipt.json').read_text());assert all(sha(e.b)==old['hashes'][k] for k,e in E.items())
def dis(k,a,z):
 t=subprocess.check_output(['xcrun','llvm-objdump','-d',f'--start-address={a}',f'--stop-address={z}',str(P[k])],text=True);(H/f'{k}-{a:x}.txt').write_text(t);return t
if __name__=='__main__':
 if len(sys.argv)>1:print(dis(sys.argv[1],int(sys.argv[2],0),int(sys.argv[3],0)))
 else:
  for k,a,z in [('fx3_ap',0x2e57a90,0x2e57b50),('fx3_ap',0x2e6c7a0,0x2e6c8a0),('fx6_ap',0x212d524,0x212d5e0),('fx6_ap',0x213b870,0x213b970),('fx3_ap',0x2e58088,0x2e58200),('fx6_ap',0x212e994,0x212eb10),('fx3_ap',0x2bcce64,0x2bccf60),('fx6_ap',0x1d6d134,0x1d6d230),('fx3_ap',0x2bcd130,0x2bcd220),('fx6_ap',0x1ca0738,0x1ca0820)]:print(dis(k,a,z))
