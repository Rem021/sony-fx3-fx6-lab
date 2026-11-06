#!/usr/bin/env python3
"""Produce bounded WBI2 structure and RAW/ISP candidate evidence."""
import collections,hashlib,json,mmap,pathlib,struct
from elftools.elf.elffile import ELFFile
ROOT=pathlib.Path(__file__).resolve().parent

def get(path,manifest):
 return next(x for x in json.loads((ROOT/manifest).read_text())['entries'] if x.get('path')==path)

def main():
 p=ROOT/'tree/0700_part_image/dev/nflasha5'
 with p.open('rb') as f,mmap.mmap(f.fileno(),0,access=mmap.ACCESS_READ) as b:
  n=struct.unpack_from('<Q',b,8)[0];size=struct.unpack_from('<Q',b,0x30)[0];table=0x200+size
  assert b[:4]==b'WBI2' and table+n*64<=len(b)
  sections=[struct.unpack_from('<8Q',b,table+i*64) for i in range(n)]
  assert sum(s[1] for s in sections)==size
  assert all(s[0]%4096==s[4]%4096==0 for s in sections)
  assert all((s[3]==0 and s[1]==s[4]) or (s[3]==1 and s[1]==0) for s in sections)
  w={'path':'0700_part_image/dev/nflasha5','sha256':get('0700_part_image/dev/nflasha5','manifest.json')['sha256'],
     'bytes':len(b),'magic':'WBI2','section_count':n,'stored_data_bytes':size,
     'table_offset':table,'table_end':table+n*64,'flags':dict(collections.Counter(str(s[3]) for s in sections)),
     'scope':'static section-table validation; no WBI2 payload reconstruction or runtime proof'}
 (ROOT/'wbi2-receipt.json').write_text(json.dumps(w,indent=2)+'\n')
 ap=get('/lib/appFw.so','nflasha15-manifest.json')
 mpr=get('/lib/libmpr.so','nflasha15-manifest.json')
 av=get('/av-cam.bin','fat-manifest.json')
 cp=get('/cpapp-b.bin','fat-manifest.json')
 def symbols(name,needles):
  with (ROOT/'nflasha15-files/lib'/name).open('rb') as f:
   elf=ELFFile(f);dyn=elf.get_section_by_name('.dynsym')
   names=[s.name for s in dyn.iter_symbols()]
   return {'dynsym_count':len(names),'examples':[x for x in names if any(y in x for y in needles)][:12]}
 result={'evidence_level':'static extracted binaries only; candidate identification is not algorithm recovery',
  'candidates':[
   {'path':'nflasha15-files/lib/appFw.so','sha256':ap['sha256'],'elf':ap['elf'],
    'reason':'AP application ELF with Colorimetry state entry and UI symbols; control/menu candidate, not pixel processor',
    'symbols':symbols('appFw.so',['Colorimetry','DataflowInfra'])},
   {'path':'nflasha15-files/lib/libmpr.so','sha256':mpr['sha256'],'elf':mpr['elf'],
    'reason':'media pipeline ELF exposes VideoParamComb ColorFormat and still RawInfo/RawSet symbol families; recording/control candidate, demosaic unproven',
    'symbols':symbols('libmpr.so',['GetVideoParamComb','RawInfo','RawSet'])},
   {'path':'fat-files/nflasha8/cpapp-b.bin','sha256':cp['sha256'],'elf':None,
    'reason':'CP-named image from nflasha8; code format, processor, ISP function and boundaries unproven'},
   {'path':'fat-files/nflasha3/av-cam.bin','sha256':av['sha256'],'elf':None,
    'reason':'AV/camera-named image from nflasha3; code format, processor and sensor pipeline function unproven'},
   {'path':'tree/0700_part_image/dev/nflasha5','sha256':w['sha256'],'elf':None,
    'reason':'WBI2 static memory image, 1197 section records; not reconstructed or attributed to ISP'}],
  'next_precise_action':'Map CP/AV image headers and AP exported/imported IPC edges, then verify candidate functions against fixed RAW input/output; no module recovery claimed'}
 (ROOT/'candidates.json').write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps({'wbi_sections':n,'candidates':len(result['candidates'])}))
if __name__=='__main__':main()
