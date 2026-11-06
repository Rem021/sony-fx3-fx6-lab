"""Read-only locator over saved official images; no Sony execution or mounts."""
from pathlib import Path
from hashlib import sha256
from io import BytesIO
import json,importlib.util,re
from elftools.elf.elffile import ELFFile
from capstone import Cs,CS_ARCH_ARM64,CS_MODE_ARM
H=Path(__file__).resolve().parent;B=H.parent
p=B/'stage2/extraction/read_filesystems.py'
assert sha256(p.read_bytes()).hexdigest()=='eecbe9b099f9fbc8f8e06759c5e8a2ce9910e0f365ae9891fe0887353edc31ad'
s=importlib.util.spec_from_file_location('readonly_saved_ext2_216',p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
images=[('root','nflasha7.img','ceca23d253350e65df9c7c976f06e545ad41a2d8f272d28fc1e73fcc576ddba7'),('app','nflasha15.img','df0a2cf2ebb0d884605d041a6dcb701092bd36848956855b8d3d7a7164a3a1c5')]
rows=[];selected=[];counts={}
for label,name,digest in images:
 f=m.Ext2(B/'stage2/extraction'/name);assert sha256(f.b).hexdigest()==digest
 seen=set();n=0
 for ent in f.walk():
  if ent['type']!=0o100000 or ent['inode'] in seen:continue
  seen.add(ent['inode']);n+=1;raw=f.data(ent['inode'])
  if b'/setting/mode/dmode' in raw:
   loc=[x.start() for x in re.finditer(re.escape(b'/setting/mode/dmode'),raw)]
   row=dict(image=name,image_sha256=digest,path=ent['path'],inode=ent['inode'],bytes=len(raw),sha256=sha256(raw).hexdigest(),string_file_offsets=loc,locator_only=True)
   if raw.startswith(b'\x7fELF'):
    e=ELFFile(BytesIO(raw));st=e.get_section_by_name('.dynsym')
    row['machine']=e.header['e_machine'];row['parsing_symbols']=[x.name for x in st.iter_symbols() if re.search(r'getline|fgets|fread|fopen|open|sscanf|atoi|strtol|mode',x.name,re.I)] if st else []
   rows.append(row)
  if label=='root' and ent['path'] in ['/sbin/init2','/sbin/initrc/fstab.ext','/sbin/initrc/fstab.root'] or label=='app' and ent['path']=='/bin/bootin.elf':
   out=H/'originals'/label/ent['path'].lstrip('/');out.parent.mkdir(parents=True,exist_ok=True);out.open('xb').write(raw)
   selected.append(dict(image=name,image_sha256=digest,path=ent['path'],inode=ent['inode'],bytes=len(raw),sha256=sha256(raw).hexdigest(),output=str(out.relative_to(H))))
 counts[name]=n;f.b.close();f.f.close()
(H/'FX3-boot-mode-locators.json').open('x').write(json.dumps(dict(source_images=images,regular_unique_inodes_scanned=counts,records=rows,selected_originals=selected,scope='saved-image string locators only; no newline requirement, runtime behavior, command execution or recovery proved',Sony_or_guest_execution=False),ensure_ascii=False,indent=2)+'\n')
print(json.dumps(dict(counts=counts,locators=rows,selected=selected)))
