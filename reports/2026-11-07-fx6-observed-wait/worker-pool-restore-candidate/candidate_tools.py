"""Read-only archive and ELF helpers, snapshotted from the verified snapshot builder."""
import hashlib,io,re
from pathlib import Path
from elftools.elf.elffile import ELFFile

def sha(b):return hashlib.sha256(b).hexdigest()

def fp(p):
 p=Path(p);h=hashlib.sha256()
 with p.open('rb') as f:
  for c in iter(lambda:f.read(1024*1024),b''):h.update(c)
 return {'path':str(p),'bytes':p.stat().st_size,'sha256':h.hexdigest()}

def scan(b):
 rows=[];pos=0;nonzero=re.compile(b'[^\x00]')
 while pos+110<=len(b):
  if b[pos]==0:
   m=nonzero.search(b,pos)
   if not m:break
   pos=m.start()
  assert b[pos:pos+6]==b'070701',pos
  v=[int(b[pos+6+i*8:pos+14+i*8],16) for i in range(13)]
  n=b[pos+110:pos+110+v[11]];assert len(n)==v[11] and n[-1:]==b'\0'
  start=(pos+110+v[11]+3)&~3;end=(start+v[6]+3)&~3;assert end<=len(b)
  rows.append({'name':n[:-1].decode(),'header':pos,'offset':start,'bytes':v[6],'end':end,'fields':v,'sha256':sha(b[start:start+v[6]]),'raw_sha256':sha(b[pos:end])});pos=end
 assert not any(b[pos:]);return rows

def elf_info(data):
 e=ELFFile(io.BytesIO(data));dyn=e.get_section_by_name('.dynsym');vs=e.get_section_by_name('.gnu.version');required={};defined={}
 vn=e.get_section_by_name('.gnu.version_r')
 if vn:
  for version,aux in vn.iter_versions():
   for item in aux:required[item['vna_other']]=(version.name,item.name)
 vd=e.get_section_by_name('.gnu.version_d')
 if vd:
  for version,aux in vd.iter_versions():defined[version['vd_ndx']]=next(aux).name
 imports=[];exports=set()
 for i,s in enumerate(dyn.iter_symbols()):
  if not s.name:continue
  v=vs.get_symbol(i)['ndx'] if vs else 'VER_NDX_GLOBAL'
  if isinstance(v,int):v &= 0x7fff
  if s['st_shndx']=='SHN_UNDEF':
   library,version=required.get(v,(None,None));imports.append({'name':s.name,'version':version,'provider':library,'weak':s['st_info']['bind']=='STB_WEAK'})
  else:exports.add((s.name,defined.get(v)))
 needed=[t.needed for t in e.get_section_by_name('.dynamic').iter_tags() if t.entry.d_tag=='DT_NEEDED']
 interp=next((s.get_interp_name() for s in e.iter_segments() if s['p_type']=='PT_INTERP'),None)
 return {'machine':e['e_machine'],'type':e['e_type'],'needed':needed,'interpreter':interp,'imports':imports},exports
