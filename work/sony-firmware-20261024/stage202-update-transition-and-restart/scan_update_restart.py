"""Locate update/restart references in saved current AP image; no Sony execution."""
from pathlib import Path
from io import BytesIO
from hashlib import sha256
import json,importlib.util,re
from elftools.elf.elffile import ELFFile
H=Path(__file__).resolve().parent;B=H.parent
p=B/'stage2/extraction/read_filesystems.py';sp=importlib.util.spec_from_file_location('saved_ext2',p);m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m)
f=m.Ext2(B/'stage2/extraction/nflasha15.img');assert sha256(f.b).hexdigest()=='df0a2cf2ebb0d884605d041a6dcb701092bd36848956855b8d3d7a7164a3a1c5'
rows=[];seen=set();total=0
for ent in f.walk():
    if ent['type']!=0o100000 or ent['inode'] in seen:continue
    seen.add(ent['inode']);total+=1;raw=f.data(ent['inode']);strings=[];symbols=[]
    if raw.startswith(b'\x7fELF'):
        e=ELFFile(BytesIO(raw))
        for key in ['.dynsym','.symtab']:
            st=e.get_section_by_name(key)
            if not st:continue
            for s in st.iter_symbols():
                if re.search(r'(kernel|machine|emergency)_(restart|halt|power_off)|reboot|udtr.*(start|init|exit)|switch.*updat|updat.*(switch|reboot|reset)',s.name,re.I):
                    symbols.append(dict(name=s.name,value=hex(s['st_value']),bytes=s['st_size'],section=s['st_shndx']))
    for x in re.finditer(rb'[\x20-\x7e]{5,}',raw):
        text=x.group()
        if re.search(rb'(^|[/ ])up\.sh|/sbin/reboot|^reboot$|^reboot |^/[^ ]*reboot|updater.*reboot|reboot.*updater|updater.*restart|restart.*updater',text,re.I):
            strings.append(dict(file_offset=hex(x.start()),text=text.decode()))
    if strings or symbols:rows.append(dict(path=ent['path'],inode=ent['inode'],bytes=len(raw),sha256=sha256(raw).hexdigest(),strings=strings,symbols=symbols))
f.b.close();f.f.close()
with (H/'restart-locators.json').open('x') as out:json.dump(dict(source_image_sha256='df0a2cf2ebb0d884605d041a6dcb701092bd36848956855b8d3d7a7164a3a1c5',regular_inodes_scanned=total,records=rows,scope='locators only; references do not prove actual calls or cold recovery',original_or_guest_execution=False,root_or_device_operations=0),out,indent=2);out.write('\n')
print(json.dumps(dict(scanned=total,records=[dict(path=r['path'],strings=r['strings'],symbols=r['symbols'][:30]) for r in rows]),ensure_ascii=False))
