from pathlib import Path
import json,hashlib
from elftools.elf.elffile import ELFFile
R=Path(__file__).resolve().parent;M=R.parents[3];L=R.parents[1]/'lead-claude';P=R.parent/'original-uipc/ap-projection/regular-files/usr/lib';sha=lambda b:hashlib.sha256(b).hexdigest();out={'sources':[],'blocks':[],'audits':[]}
for rel,key in [('boot-screen-controller/boot-screen-proof.json','code')]:
 p=L/'audits'/rel;a=json.loads(p.read_text());out['audits'].append({'path':str(p),'sha256':sha(p.read_bytes())})
 for rel,v in a['sources'].items():
  p=M/rel;b=p.read_bytes();match=sha(b[:v['bytes']])==v['sha256'];strict='original-' in rel or 'extraction/' in rel or '/runs/' in rel or rel.endswith(('.so','.c','.sh'));assert match or not strict,(rel,'SHA mismatch');out['sources'].append({'path':str(p),'match_audited_prefix':match,'strict':strict})
 blocks=a[key];rows=blocks if isinstance(blocks,list) else [{'image':im.lower(),'va':v,**q} for im,windows in blocks.items() for v,q in ([(q['va'],q) for q in windows] if isinstance(windows,list) else windows.items())]
 for q in rows:
  image=q['image'];v=int(q['va'],16);raw=bytes.fromhex(q['raw'])
  if image=='cp':p=M/'work/sony-firmware-20261024/stage2/extraction/files/nflasha8/cpapp-b.bin';b=p.read_bytes()[v-0x108000:v-0x108000+len(raw)]
  else:
   p=(R.parent/'original-uipc/original-modules/backup.ko' if image=='backup.ko' else P/('appFw.so' if image=='ap' else 'libObj.so' if image=='obj' else image)) if image!='input' else next(M/x for x in a['sources'] if x.endswith('d9fcf59b62f9960878f5ea433d350112f4a03fb9c6cd9d30154fb3e3ff54a057'))
   with p.open('rb') as f:
    ef=ELFFile(f)
    if image in ('input','backup.ko'):b=ef.get_section_by_name(q.get('section','.text')).data()[v:v+len(raw)]
    else:
     off=next(s['p_offset']+v-s['p_vaddr'] for s in ef.iter_segments() if s['p_type']=='PT_LOAD' and s['p_vaddr']<=v and v+len(raw)<=s['p_vaddr']+s['p_filesz']);f.seek(off);b=f.read(len(raw))
  assert raw==b,(image,hex(v));out['blocks'].append({'image':image,'va':hex(v),'bytes':len(raw),'match':True})
(R/'ap88-audit-input-check.json').write_text(json.dumps(out,indent=2)+'\n');print('AP88_AUDIT_PASS',len(out['sources']),len(out['blocks']))
