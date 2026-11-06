"""Pinned static FX3 main format/menu inspection. No native or guest execution."""
from pathlib import Path
import sys, json, re, struct, hashlib, subprocess, plistlib
from collections import defaultdict
ROOT=Path(__file__).resolve().parents[4]
sys.path.insert(0,str(ROOT/'work/sony-firmware-20261024/stage10-mainpath/main'))
from audit_main_path import Image, INPUT, EXPECTED
OUT=Path(__file__).resolve().parent

def main():
 assert plistlib.loads(subprocess.check_output(['diskutil','info','-plist','/Volumes/KAFU2T']))['VolumeUUID']=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
 im=Image();elf=im.elf
 rel={}
 for s in elf.iter_sections():
  if s['sh_type']=='SHT_RELA':
   for r in s.iter_relocations():
    if r['r_info_type']==1027:rel[r['r_offset']]=r['r_addend']
 rev=defaultdict(list)
 for a,b in rel.items():rev[b].append(a)
 def ptr(a):return rel.get(a,struct.unpack('<Q',im.read(a,8))[0])
 def z(a):return im.read(a,2000).split(b'\0')[0].decode('ascii',errors='replace')
 sec=elf.get_section_by_name('.rodata');strs=[]
 patterns=['PRM_setting_file_format','VAL_setting_file_format_', 'PRM_setting_movie_rec_frame_rate_xavc_hs_4k','VAL_setting_movie_rec_frame_rate_xavc_hs_4k_', 'PRM_setting_movie_record_setting_xavc_hs_4k','VAL_setting_movie_record_setting_xavc_hs_4k_', 'FEATURE_MANAGER_movie', 'xavc_hs_hd', 'xavc_hs_4k_30', 'menu_item::movie', 'movie_file_format', 'extern_menu_mov_file_format', 'EXTERN_VAL_MENU_MOV_FILE_FORMAT', 'to_remote_event_file_format_movie', 'set_file_format']
 for m in re.finditer(rb'[ -~]{6,}',sec.data()):
  t=m.group().decode()
  if any(x in t for x in patterns):
   a=sec['sh_addr']+m.start();strs.append({'va':hex(a),'text':t,'reloc_refs':[hex(x) for x in rev[a]]})
 targets={int(x['va'],16) for x in strs};targets.update(a for t in list(targets) for a in rev[t])
 targets.update([0x41a6a48,0x41a6a50,0x41a6b28,0x41a6b30,0x4117f48,0x4117f88])
 refs=defaultdict(list);text=elf.get_section_by_name('.text');d=text.data();va=text['sh_addr']
 # Resolve ADRP to short ADD/LDR window; destination register must match ADRP base.
 for o in range(0,len(d)-36,4):
  w=struct.unpack_from('<I',d,o)[0]
  if w&0x9f000000!=0x90000000:continue
  reg=w&31;imm=((w>>29)&3)|(((w>>5)&0x7ffff)<<2)
  if imm&(1<<20):imm-=1<<21
  page=((va+o)&~4095)+(imm<<12)
  for k in range(4,36,4):
   q=struct.unpack_from('<I',d,o+k)[0];a=None
   # Stop at a call or replacement ADRP: no stale-register cross-call refs.
   if q>>26 in (0b100101,0b000101) or (q&0x9f000000==0x90000000 and q&31==reg):break
   if ((q>>5)&31)!=reg:continue
   if q&0xff800000==0x91000000:a=page+((q>>10)&4095)*(4096 if q&(1<<22) else 1)
   elif q&0xffc00000==0xf9400000:a=page+8*((q>>10)&4095)
   elif q&0xffc00000==0xb9400000:a=page+4*((q>>10)&4095)
   if a in targets:refs[a].append({'adrp':hex(va+o),'use':hex(va+o+k),'context':im.dump(va+o-16,va+o+k+20)})
   if q&0xff800000==0x91000000 and q&31==reg:break
 for s in strs:
  s['code_refs']=refs[int(s['va'],16)]
  s['record_code_refs']={a:refs[int(a,16)] for a in s['reloc_refs']}
 tables={}
 for n,a,l in [('format',0x411f108,14),('hs4k_frame',0x411f390,10)]:
  tables[n]=[{'index':i,'slot':hex(a+i*8),'string_va':hex(ptr(a+i*8)),'text':z(ptr(a+i*8))} for i in range(l)]
 for name in ['60p_50p','24p','120p_100p']:
  prefix='VAL_setting_movie_record_setting_xavc_hs_4k_'+name+'_'
  first=next(s for s in strs if s['text']==prefix+'RECORD_SETTING_600M_422_10BIT')
  a=int(first['reloc_refs'][0],16);rows=[]
  for i in range(64):
   text=z(ptr(a+8*i))
   if not text.startswith(prefix):break
   rows.append({'index':i,'slot':hex(a+i*8),'string_va':hex(ptr(a+i*8)),'text':text})
  tables['hs4k_quality_'+name]=rows
 tables['external_movie_format']=[{'value':struct.unpack('<I',im.read(0x41a6a48+16*i,4))[0],'record':hex(0x41a6a48+16*i),'name':z(ptr(0x41a6a50+16*i))} for i in range(21)]
 regions=[('frame_change_dispatch',0x27c79c4,0x27c7c2c),('hs4k_frame_setter',0x1e49cf8,0x1e49d74),('movie_format_derived_classification',0x2a50354,0x2a505a0),('external_enum_registration',0x16cee28,0x16cee5c),('remote_event_file_format',0x2e9b898,0x2e9b97c)]
 snippets=[{'name':n,'entry':hex(a),'end_exclusive':hex(b),'bytes':im.read(a,b-a).hex(),'instructions':im.dump(a,b)} for n,a,b in regions]
 format_routes=[]
 for i in range(7):
  delta=struct.unpack('<h',im.read(0x37fa3b8+2*i,2))[0]
  dest=0x2a50390+4*delta;w=struct.unpack('<I',im.read(dest,4))[0]
  assert w&0xffe0001f==0x52800000
  format_routes.append({'setting_format':i+5,'jump_slot':hex(0x37fa3b8+2*i),'target':hex(dest),'movie_format_result':(w>>5)&0xffff})
 event_map=[{'external_value':im.read(0x3997e68+8*i,1)[0],'remote_event_value':struct.unpack('<I',im.read(0x3997e6c+8*i,4))[0]} for i in range(9)]
 out={'input':str(INPUT),'sha256':EXPECTED,'static_only':True,'tables':tables,'strings':strs,'snippets':snippets,'main_to_derived_movie_format':format_routes,'remote_event_file_format_map':event_map,'external_HD_to_main_setting_mapping':'not established; external metadata and remote event mapping do not establish selectable main mode'}
 (OUT/'capability-string-index.json').write_text(json.dumps(out,indent=2,ensure_ascii=False)+'\n')
 print(json.dumps({'output':str(OUT/'capability-string-index.json'),'strings':len(strs),'code_ref_counts':[(s['text'][:130],len(s['code_refs']),sum(len(x) for x in s['record_code_refs'].values())) for s in strs]},indent=2))
if __name__=='__main__':main()
