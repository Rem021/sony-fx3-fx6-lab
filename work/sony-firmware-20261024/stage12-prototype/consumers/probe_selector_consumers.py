"""Original image static-only selector/derived-consumer trace. No camera I/O."""
from pathlib import Path
import sys,json,re,struct,hashlib,subprocess,plistlib
from collections import defaultdict
ROOT=Path(__file__).resolve().parents[4]
sys.path.insert(0,str(ROOT/'work/sony-firmware-20261024/stage10-mainpath/main'))
from audit_main_path import Image,INPUT,EXPECTED
OUT=Path(__file__).resolve().parent

def main():
 assert plistlib.loads(subprocess.check_output(['diskutil','info','-plist','/Volumes/KAFU2T']))['VolumeUUID']=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
 im=Image(); rel={}
 for s in im.elf.iter_sections():
  if s['sh_type']=='SHT_RELA':
   for r in s.iter_relocations():
    if r['r_info_type']==1027:rel[r['r_offset']]=r['r_addend']
 rev=defaultdict(list)
 for a,b in rel.items():rev[b].append(a)
 def z(a):return im.read(a,1500).split(b'\0')[0].decode('ascii',errors='replace')
 ro=im.elf.get_section_by_name('.rodata'); strings=[]
 for m in re.finditer(rb'[ -~]{5,}',ro.data()):
  t=m.group().decode()
  if (('movie_format' in t or 'file_format' in t) and any(p in t for p in ['movie_format_t','VAL_movie_format','PRM_movie_format','remote','extern_menu_mov','set_file_format','convert_','file_format_movie','sequence_set_movie_format'])) or 'convert2MovieMainParams(' in t:
   a=ro['sh_addr']+m.start();strings.append({'va':hex(a),'text':t,'reloc_refs':[hex(x) for x in rev[a]]})
 targets={int(s['va'],16) for s in strings}|{int(a,16) for s in strings for a in s['reloc_refs']}|{0x3997e68}|set(range(0x3120200,0x3120380,4))
 refs=defaultdict(list); text=im.elf.get_section_by_name('.text');d=text.data();va=text['sh_addr']
 for o in range(0,len(d)-36,4):
  w=struct.unpack_from('<I',d,o)[0]
  if w&0x9f000000!=0x90000000:continue
  reg=w&31;imm=((w>>29)&3)|(((w>>5)&0x7ffff)<<2)
  if imm&(1<<20):imm-=1<<21
  page=((va+o)&~4095)+(imm<<12)
  for k in range(4,36,4):
   q=struct.unpack_from('<I',d,o+k)[0];a=None
   if q>>26 in (0b100101,0b000101) or (q&0x9f000000==0x90000000 and q&31==reg):break
   if ((q>>5)&31)!=reg:continue
   if q&0xff800000==0x91000000:a=page+((q>>10)&4095)*(4096 if q&(1<<22) else 1)
   elif q&0xffc00000==0xf9400000:a=page+8*((q>>10)&4095)
   elif q&0xffc00000==0xb9400000:a=page+4*((q>>10)&4095)
   if a in targets:refs[a].append({'adrp':hex(va+o),'use':hex(va+o+k),'context':im.dump(va+o-20,va+o+k+24)})
   if q&0xff800000==0x91000000 and q&31==reg:break
 for s in strings:
  s['direct_code_refs']=refs[int(s['va'],16)]
  s['record_code_refs']={a:refs[int(a,16)] for a in s['reloc_refs']}
 # Concrete reverse-pair candidates, not command/property identifiers.
 pairs=[]
 for s in im.elf.iter_sections():
  if s['sh_type']!='SHT_PROGBITS' or s['sh_flags']&4:continue
  raw=s.data()
  for p in [struct.pack('<II',113,14),struct.pack('<II',14,113),bytes([113,14]),bytes([14,113])]:
   for m in re.finditer(re.escape(p),raw):
    a=s['sh_addr']+m.start()
    pairs.append({'va':hex(a),'section':s.name,'pattern':p.hex(),'near_bytes':raw[max(0,m.start()-24):m.start()+48].hex()})
 calls=im.calls({0x2a50354,0x2e68048,0x2e91e94,0x2934c9c})
 out={'source':str(INPUT),'sha256':EXPECTED,'static_only':True,'strings':strings,'pair_candidates':pairs,'callers':calls,'known_output_table_xrefs':refs[0x3997e68], 'inverse_candidate_xrefs':{hex(a):r for a,r in refs.items() if 0x3120200<=a<0x3120380}}
 (OUT/'selector-index.json').write_text(json.dumps(out,indent=2,ensure_ascii=False)+'\n')
 regions=[('external_descriptor',0x2318720,0x23188b4),('external_allowlist',0x23184b8,0x2318624),('external_current_value',0x23067c0,0x2306810),('external_current_converter',0x22e8784,0x22e8854),('derived_primary_caller_packet',0x2b6dd0c,0x2b6de60),('derived_second_caller_packet',0x2d20f24,0x2d21100),('hdmi_definition_wrapper',0x2dd1354,0x2dd1394),('hdmi_resolution_wrapper',0x2dd1294,0x2dd12d4),('hdmi_definition',0x2df7948,0x2df7b14),('hdmi_resolution',0x2df6d8c,0x2df6ef0),('hdmi_resolution_converter',0x2de5594,0x2de568c)]
 qstart=0x2e68fec+4*struct.unpack('<h',im.read(0x398958c+2,2))[0]
 regions.append(('ordinary_query_format6_entry',qstart,qstart+0x300))
 proof={'sha256':EXPECTED,'static_only':True,'regions':[{'name':n,'start':hex(a),'end_exclusive':hex(b),'bytes':im.read(a,b-a).hex(),'instructions':im.dump(a,b)} for n,a,b in regions],
 'descriptor_tables':[{'start':hex(a),'rows':[{'va':hex(a+16*i),'u32_columns':list(struct.unpack('<IIII',im.read(a+16*i,16)))} for i in range(n)]} for a,n in [(0x3120278,8),(0x31202f8,9)]],
 'log_strings':[{'va':hex(a),'text':z(a)} for a in [0x39684d0,0x39684e8,0x391bb36,0x391bb91,0x391bbd8,0x3935c06]],
 'ordinary_query_format6':{'table':hex(0x398958c),'index':1,'entry':hex(qstart)},
 'ordinary_query_hs4k_frame_dispatch':[{'typed_frame':i,'table_slot':hex(0x39895ac+i),'target':hex(0x2e691b8+4*struct.unpack('<b',im.read(0x39895ac+i,1))[0])} for i in range(7)],
 'external_getter_case_results':[{'case':i,'branch':hex(0x22e8808+4*struct.unpack('<b',im.read(0x311f09c+i,1))[0])} for i in range(7)]}
 (OUT/'consumer-proof.json').write_text(json.dumps(proof,indent=2,ensure_ascii=False)+'\n')
 print('strings',len(strings),'pairs',len(pairs),'calls',len(calls))
 print('INVERSE XREFS',[(hex(a),[x['use'] for x in r]) for a,r in refs.items() if 0x3120200<=a<0x3120380])
 print('DERIVED CALLERS',[c['call_va'] for c in calls if c['target_va']=='0x2a50354'])
 print('QUERY CALLERS',[c['call_va'] for c in calls if c['target_va']=='0x2e68048'])
 print('QUERY FORMAT6',hex(qstart))
 print('\n'.join(x['va']+' '+x['asm'] for x in im.dump(qstart,qstart+0x150)))
 assert hashlib.sha256(INPUT.read_bytes()).hexdigest()==EXPECTED
if __name__=='__main__':main()
