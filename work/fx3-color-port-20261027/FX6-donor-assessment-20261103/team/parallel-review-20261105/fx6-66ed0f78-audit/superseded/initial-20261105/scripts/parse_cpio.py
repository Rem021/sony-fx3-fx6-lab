#!/usr/bin/env python3
"""Stream newc CPIO members: selected hashes and optional full map. No extraction."""
import hashlib,json,sys
from pathlib import Path
SEL={b'usr/lib/appFw.so',b'usr/kmod/upm.ko',b'usr/kmod/backup.ko',b'simulation/fx3-cp-backup-reset-v1.ko',b'/init',b'usr/lib/libgrm.so'}
def parse(path,full=False):
 h={}; count=0; names=[]
 with Path(path).open('rb') as f:
  while True:
   hdr=f.read(110)
   if len(hdr)!=110:raise ValueError('short header '+str(path))
   if hdr[:6]!=b'070701':raise ValueError('not newc '+str(path)+' '+hdr[:6].decode('ascii','replace'))
   namesize=int(hdr[94:102],16); filesize=int(hdr[54:62],16)
   name=f.read(namesize).rstrip(b'\0'); f.read((4-(110+namesize)%4)%4)
   def digest():
    H=hashlib.sha256(); left=filesize
    while left:
     b=f.read(min(1<<20,left));H.update(b);left-=len(b)
    return H.hexdigest()
   if full or name in SEL:
    h[name.decode('ascii','replace')]=digest()
   else:
    left=filesize
    while left:
     b=f.read(min(1<<20,left));left-=len(b)
   f.read((4-filesize%4)%4);count+=1;names.append(name.decode('ascii','replace'))
   if name==b'TRAILER!!!':break
 return {'path':str(path),'bytes':Path(path).stat().st_size,'members':count,'selected':h,'full':h if full else None,'names':names if full else None}
def main():
 base=Path('/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/fx6-boot-readiness/early-kernel/cp-helper-agnostic')
 donor=Path('/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor')
 files={'target_grmreal46':base/'guest-hybrid-fx6kernel-capid-grmreal46.cpio','source_grmreal41':base/'guest-hybrid-fx6kernel-capid-grmreal41.cpio','grmreal21':base/'guest-hybrid-fx6kernel-capid-grmreal21.cpio','grmreal19':base/'guest-hybrid-fx6kernel-capid-grmreal19.cpio','grmreal20':base/'guest-hybrid-fx6kernel-capid-grmreal20.cpio','hybrid_fx6kernel':base/'guest-hybrid-fx6kernel.cpio','cp_helper_agnostic':base/'guest-cp-helper-agnostic.cpio','hybrid_three_entry':donor/'hybrid-ap-candidate/guest-three-entry.cpio'}
 full={}; selected={}
 for k,p in files.items():
  if not p.is_file():print('MISSING',k,p);continue
  full[k]=parse(p,full=(k in ('target_grmreal46','source_grmreal41')))
  selected[k]=full[k]['selected']
  print(k,'members',full[k]['members'],'selected',selected[k])
 # target vs source full diff
 t=full['target_grmreal46'];s=full['source_grmreal41']; changed=sorted(n for n in set(t['full'])|set(s['full']) if t['full'].get(n)!=s['full'].get(n))
 value={'schema':'fx6-r50-cpio-member-audit-v1','selected':selected,'target_vs_source_grmreal41':{'target_members':t['members'],'source_members':s['members'],'changed':changed,'only_upm_changed':changed==['usr/kmod/upm.ko']},
  'full_maps':{k:{'path':v['path'],'bytes':v['bytes'],'members':v['members'],'full':v['full']} for k,v in full.items()},
  'note':'Independent newc stream parse; target member hashes compared to source/build chain. No CPIO copied/extracted.'}
 out=Path(__file__).resolve().parent.parent/'receipts/cpio-member-audit.json';out.write_text(json.dumps(value,indent=2)+'\n');print('OUT',out)
if __name__=='__main__':main()
