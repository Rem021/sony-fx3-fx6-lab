"""QMP physical READ ONLY of self-owned guest ring; no per-frame ACK/host write."""
from pathlib import Path
import struct,json,hashlib,time,zlib,binascii
BASE=0x41e000000;TOTAL=0xc10000;HEADER=0x10000;STRIDE=0x180000;MAGIC=0x32474e495244534f
LUT=[bytes(((v>>12)*17,((v>>8)&15)*17,((v>>4)&15)*17,255)) for v in range(65536)]
def sha(b):return hashlib.sha256(b).hexdigest()
def nonuniform_rgba(pixels):
 complete=len(pixels)//4
 return (len(pixels)>4 and len(pixels)%4!=0) or (complete>1 and pixels[:complete*4]!=pixels[:4]*complete)
def fnv(b):
 h=14695981039346656037
 for c in b:h=((h^c)*1099511628211)&0xffffffffffffffff
 return h
def png(w,h,b):
 def c(k,v):return struct.pack('>I',len(v))+k+v+struct.pack('>I',binascii.crc32(k+v)&0xffffffff)
 return b'\x89PNG\r\n\x1a\n'+c(b'IHDR',struct.pack('>IIBBBBB',w,h,8,6,0,0,0))+c(b'IDAT',zlib.compress(b''.join(b'\0'+b[y*w*4:(y+1)*w*4] for y in range(h)),3))+c(b'IEND',b'')
def rgba(raw,w,h,stride,fmt):
 bpp=2 if fmt==0 else 4;assert ((h-1)*stride+w)*bpp<=len(raw);rows=[]
 for y in range(h):
  b=raw[y*stride*bpp:(y*stride+w)*bpp]
  if not fmt:row=b''.join(LUT[v[0]] for v in struct.iter_unpack('<H',b))
  else:
   row=bytearray(w*4);row[0::4]=b[3::4];row[1::4]=b[2::4];row[2::4]=b[1::4];row[3::4]=b'\xff'*w;row=bytes(row)
  rows.append(row)
 return b''.join(rows)
class RingReader:
 def __init__(self,run,qmp):self.run=run;self.qmp=qmp;self.seen=set();self.last=0;self.records=[];self.rejects=[];self.polls=[];self.first_nonuniform=False
 def read(self,address,n,name):
  p=self.run/name;r=self.qmp('human-monitor-command',{'command-line':f'pmemsave {hex(address)} {hex(n)} "{p}"'});return p.read_bytes() if 'error' not in r and p.exists() and p.stat().st_size==n else b''
 def poll(self,final=False):
  head=self.read(BASE,0x100,'osd-ring-header-live.bin')
  if len(head)!=256:return
  g=struct.unpack_from('<16Q',head)
  if g[0]!=MAGIC or g[1]!=2:return
  self.polls.append({'host_monotonic':time.monotonic(),'global_words':list(g),'final':final})
  if g[4]<=self.last and not final:return
  raw=self.read(BASE,TOTAL,'osd-ring-live.bin')
  if len(raw)!=TOTAL:return
  frames=[]
  for i in range(8):
   s=raw[HEADER+i*STRIDE:HEADER+(i+1)*STRIDE];v=struct.unpack_from('<36Q',s)
   if not v[0] or v[0] in self.seen:continue
   if v[0]!=v[2] or v[1]!=g[3] or v[11]>0x12c000 or v[11]==0 or v[7]>1 or not 0<v[8]<=640 or not 0<v[9]<=480 or v[10]<v[8]:self.rejects.append({'slot':i,'reason':'uncommitted/invalid header','words':list(v)});continue
   if v[26]!=1 or v[27] not in [1,2] or not v[29] or not v[32] or v[31]+v[32]>0xffffffffffffffff or v[33]!=v[5] or v[35]!=v[6] or not(v[31]<=v[6]<v[31]+v[32]) or v[11]>v[31]+v[32]-v[6] or v[27]==2 and not(v[28] and v[30] and v[34]):self.rejects.append({'slot':i,'seq':v[0],'reason':'invalid registered frame target tuple','words':list(v)});continue
   if not(v[23]<=v[22]<v[24]) or v[11]>v[24]-v[22] or v[25]+v[22]-v[23]!=v[6]:self.rejects.append({'slot':i,'seq':v[0],'reason':'native CPU mapping/physical mismatch'});continue
   b=s[0x200:0x200+v[11]]
   if fnv(b)!=v[12]:self.rejects.append({'slot':i,'seq':v[0],'reason':'concurrent overwrite checksum mismatch; no ACK dependency'});continue
   frames.append((v,b,s[:512]))
  for v,b,sh in sorted(frames,key=lambda q:q[0][0]):
   seq=v[0];self.seen.add(seq);fmt,w,h,stride=v[7:11];pixels=rgba(b,w,h,stride,fmt);nu=nonuniform_rgba(pixels);keep=seq<=30 or seq%30==0 or(nu and not self.first_nonuniform);record={'sequence':seq,'epoch':v[1],'update_id':hex(v[3]),'pixel_source_sequence':v[4],'token':hex(v[5]),'physical':hex(v[6]),'native_bitmap_format':v[21],'native_format':fmt,'native_format_domain':'Mapped GPE format; original bitmap enum recorded separately','width':w,'height':h,'stride_pixels':stride,'span':v[11],'fnv64':hex(v[12]),'sha256':sha(b),'native_identity':{'FB':hex(v[13]),'bitmap':hex(v[14]),'entry':hex(v[15]),'allocation':hex(v[16]),'metadata_physical':hex(v[17]),'FB_format':v[18],'publish_sem':hex(v[19]),'config_hash':hex(v[20]),'bits_cpu_VA':hex(v[22]),'map_begin':hex(v[23]),'map_end':hex(v[24]),'map_offset':hex(v[25])},'descriptor':sh[0x180:0x1a4].hex(),'registered_target':{'version':v[26],'kind':v[27],'object':hex(v[28]),'epoch':v[29],'identity':hex(v[30]),'parent_physical':hex(v[31]),'parent_bytes':v[32],'native_token':hex(v[33]),'vptr':hex(v[34]),'captured_physical':hex(v[35]),'valid_during_native_read_lease_and_raster_lifecycle_guards':True},'nonuniform_pixels':nu,'retained_on_host':keep,'QMP_read_only':True,'guest_native_lease_released_before_ring_commit':True,'CP_composition_panel_acceptance':False,'views':[]}
   if keep:
    prefix=f'osd-frame-{seq:06d}';(self.run/(prefix+'.raw')).write_bytes(b);(self.run/(prefix+'-slot-header.bin')).write_bytes(sh)
    for assumed in [0,1]:
     aw,ah,astride=w,h,stride
     if fmt==0 and assumed==1:aw=w//2;astride=stride//2
     # For native fmt1, 16-bit alternative uses actual physical row byte distance.
     if fmt==1 and assumed==0:astride=stride*2
     if aw<1 or ((ah-1)*astride+aw)*(2 if assumed==0 else 4)>len(b):continue
     pix=rgba(b,aw,ah,astride,assumed);name=prefix+f'-format{assumed}-RGBA-opaque.png';img=png(aw,ah,pix);(self.run/name).write_bytes(img);record['views'].append({'path':str(self.run/name),'sha256':sha(img),'format':assumed,'width':aw,'height':ah,'stride_pixels':astride,'native_format_matches':fmt==assumed,'component_order':'RGBA','alpha':'opaque hypothesis','colors':'Unverified nibble/byte interpretation','H_V_flip':False,'inside_owned_span':True})
    (self.run/(prefix+'.json')).write_text(json.dumps(record,indent=2)+'\n')
   self.first_nonuniform|=nu;self.records.append(record)
  self.last=max(self.last,g[4]);self.save()
 def save(self):
  observed=sorted(self.seen);gaps=[{'after':a,'before':b,'missing_count':b-a-1} for a,b in zip([0]+observed,observed) if b>a+1];(self.run/'osd-ring-readback.json').write_text(json.dumps({'scope':'Passive QMP guest software snapshot ring; host export never gates guest ACK; overwritten intermediate frames may be unavailable','frames':self.records,'polls':self.polls,'rejected_torn_samples':self.rejects,'sequence_gaps':gaps,'first_nonuniform_found':self.first_nonuniform,'retention':'first30 sequences plus every30 and first nonuniform; ring overwrite allowed','host_write_to_guest':False},indent=2)+'\n')
