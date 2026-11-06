"""Read-only AP terminal symbols and literal message references; no emulation."""
from pathlib import Path
from hashlib import sha256
import importlib.util,io,json,re
from elftools.elf.elffile import ELFFile
HERE=Path(__file__).resolve().parent;BASE=HERE.parent
reader=BASE/'stage2/extraction/read_filesystems.py'
assert sha256(reader.read_bytes()).hexdigest()=='eecbe9b099f9fbc8f8e06759c5e8a2ce9910e0f365ae9891fe0887353edc31ad'
spec=importlib.util.spec_from_file_location('original_read_only_fs',reader);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
image=BASE/'stage2/extraction/nflasha15.img';fs=m.Ext2(image)
assert sha256(fs.b).hexdigest()=='df0a2cf2ebb0d884605d041a6dcb701092bd36848956855b8d3d7a7164a3a1c5'
old=json.loads((BASE/'stage148-initial-MSC-handler-inventory/AP-handler-inventory.json').read_text())
pattern=re.compile(rb'term(?:inal|mode|ctl|control|io|_mode|_ctrl|_ctl|_io|_change)|/dev/(?:ptmx|pts/|ttyGS|ttyUSB)',re.I)
records=[]
for rec in old['ELF_records']:
 raw=fs.data(rec['inode']);assert sha256(raw).hexdigest()==rec['sha256']
 literal=[x.start() for x in re.finditer(re.escape(b'\x5f\x02\x3d\x00'),raw)]
 terms=[{'offset':x.start(),'text':x.group().decode('ascii')} for x in pattern.finditer(raw)]
 if not literal and not terms:continue
 e=ELFFile(io.BytesIO(raw));symbols=[]
 for table in e.iter_sections():
  if table['sh_type'] not in ('SHT_DYNSYM','SHT_SYMTAB'):continue
  for sym in table.iter_symbols():
   if pattern.search(sym.name.encode()):symbols.append({'name':sym.name,'va':sym['st_value'],'bytes':sym['st_size'],'section':sym['st_shndx'],'kind':sym['st_info']['type']})
 records.append({'paths':rec['image_paths'],'inode':rec['inode'],'sha256':rec['sha256'],'literal_mid_offsets':literal,'term_count':len(terms),'term_matches':terms[:100],'symbols':symbols})
report={'status':'STATIC_AP_TERMINAL_CANDIDATE_INVENTORY','image_sha256':old['source_image_sha256'],'ELFs_reverified':len(old['ELF_records']),
 'message_literal':'0x003d025f','pattern':pattern.pattern.decode(),'records':records,
 'scope':'symbols/literals only; absence is not proof against inline, external partitions, RTOS or dynamic dispatch','camera_operations':0}
with (HERE/'AP-terminal-inventory.json').open('x') as f:json.dump(report,f,indent=2);f.write('\n')
print(json.dumps({'ELFs':len(old['ELF_records']),'candidates':len(records),'literal_files':[r['paths'] for r in records if r['literal_mid_offsets']],
 'defined_terminal_symbols':[{ 'paths':r['paths'],'names':[s['name'] for s in r['symbols'] if s['section']!='SHN_UNDEF']} for r in records if any(s['section']!='SHN_UNDEF' for s in r['symbols'])]}))
