"""Saved raw command corpus plus freshly decoded real LDEC texture bytes."""
from pathlib import Path
import sys, re, struct, hashlib, json, collections
ROOT=Path(__file__).resolve().parent
FX=ROOT.parents[2]
RUNTIME=FX/'menu-repair-01/runtime'
LDEC=ROOT.parent/'ldec-lz77'
def sha(data):return hashlib.sha256(data).hexdigest()
def write_json(path,obj):path.write_text(json.dumps(obj,indent=2,ensure_ascii=False)+'\n')
def prepare():
 sys.dont_write_bytecode=True
 sys.path.insert(0,str(LDEC))
 from decode_ldec import decode_ldec
 summary=json.loads((LDEC/'results/batch_summary.json').read_text())
 assets=[];combined=bytearray()
 for sample in summary['sample_images']:
  name=sample['name'];compressed=(LDEC/'samples'/f'{name}.ldec').read_bytes()
  saved=(LDEC/'samples'/f'{name}.raw').read_bytes();decoded=decode_ldec(compressed,len(saved));assert decoded==saved
  assets.append({'name':name,'width':sample['width'],'height':sample['height'],'source_sha256':sha(compressed),'raw_sha256':sha(decoded),'offset':len(combined),'bytes':len(decoded),'note':'LDEC sample identity; not bound to runtime bitmap ID'})
  combined+=decoded
 (ROOT/'build/textures.bin').write_bytes(combined)
 write_json(ROOT/'build/textures.json',assets)
 records=[];manifest=[];unique={};stats={};cmds=collections.Counter()
 raw_pattern=re.compile(rb'FX3_GPE_(?:RAW|REJECT)_PARAMS op=(FillRect|BitBlit) seq=(\d+) read=1 len=(56|144) raw_hex=([0-9a-f]+)')
 for family in ['ap89','ap90','ap97','ap101','ap104']:
  stat={'files':[],'raw_records':0,'unique_raw_records':0,'marker_classes':collections.Counter(),'bad_raw_records':0}
  for file in sorted((RUNTIME/'runs').glob(family+'*/serial.log')):
   data=file.read_bytes();stat['files'].append({'path':str(file),'sha256':sha(data),'bytes':len(data)})
   for m in re.finditer(rb'FX3_GPE_CMD op=(FillRect|BitBlit|Flush)[^\n]*',data):
    # Counts are log observations; interleaved marker fields may be partial.
    op=m.group(1).decode();stat['marker_classes'][op]+=1
   for m in raw_pattern.finditer(data):
    op,seq,n,raw=m.groups()
    if len(raw)!=int(n)*2:stat['bad_raw_records']+=1;continue
    op=0 if op==b'FillRect' else 1;raw=bytes.fromhex(raw.decode());stat['raw_records']+=1
    key=(op,raw)
    if key in unique:
     records[unique[key]]['occurrences']+=1;continue
    line=data.count(b'\n',0,m.start())+1
    unique[key]=len(records);records.append({'op':op,'raw':raw.hex(),'run':file.parent.name,'LF_line':line,'sequence':int(seq),'occurrences':1,'origin':'historical_exact'})
    stat['unique_raw_records']+=1
  stat['marker_classes']=dict(stat['marker_classes']);stats[family]=stat
 # Canonical coverage at 640x480; these mutations are labelled and never counted as historical.
 def fill(sel=0,k=255,fmt=0):
  b=bytearray(56);struct.pack_into('<Q',b,0,0x600000000)
  struct.pack_into('<6I',b,8,0,0,640,480,640,fmt);b[32:36]=bytes([80,132,231,176]);b[36]=sel;b[37]=k;b[38]=1;return b
 def blit(sw=640,sh=480,sf=0,sel=0,k=255,flags=0,tile=0,fmt=0):
  b=bytearray(144);struct.pack_into('<Q',b,0,0x600000000)
  for off,v in {16:640,20:480,32:640,36:480,48:640,52:fmt,72:sw,76:sh,88:sw,92:sf}.items():struct.pack_into('<I',b,off,v)
  struct.pack_into('<Q',b,56,0x500000000);b[112]=sel;b[114]=k;b[115]=flags;b[116]=tile;b[121]=1
  if sf==2:b[108:112]=bytes([221,134,81,255]);b[117]=14
  if tile:struct.pack_into('<2I',b,96,0x3f800000,0x3f800000)
  return b
 canonical=[('fill_replace',0,fill()),('fill_blend_K128',0,fill(1,128)),('blit_replace',1,blit()),('blit_blend_K255',1,blit(sel=1,flags=1)),('blit_blend_K65',1,blit(sel=1,k=65,flags=1)),('nearest_center',1,blit(320,240)),('nearest_edge_blend',1,blit(320,240,sel=1,flags=1)),('repeat_tile',1,blit(16,16,sel=1,flags=1,tile=1)),('fmt2_A8_K255',1,blit(sf=2,sel=1,flags=1)),('fmt2_A8_K128',1,blit(sf=2,sel=1,k=128,flags=1))]
 for name,op,raw in canonical:records.append({'op':op,'raw':raw.hex(),'run':'canonical','sequence':len(records),'LF_line':None,'origin':'synthetic_coverage','name':name,'occurrences':1})
 with (ROOT/'build/vectors.bin').open('wb') as f:
  f.write(b'GPEVEC09'+struct.pack('<I',len(records)))
  for row in records:
   raw=bytes.fromhex(row['raw']);f.write(struct.pack('<II',row['op'],len(raw))+raw)
 write_json(ROOT/'build/vectors.json',records)
 write_json(ROOT/'build/corpus-statistics.json',stats)
 return records,assets
if __name__=='__main__':prepare()
