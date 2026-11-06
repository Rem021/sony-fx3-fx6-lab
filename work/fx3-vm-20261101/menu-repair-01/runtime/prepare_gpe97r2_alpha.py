from pathlib import Path
import json,re,struct,hashlib,subprocess
from fractions import Fraction
R=Path(__file__).resolve().parent;H=R/'helpers';authority='msg_155b0cf9b5b7';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def new(p,s):
 with p.open('x') as f:f.write(s)
s=(H/'fx3-gpe-backend-v5.h').read_text().replace('BACKEND_V5','BACKEND_V6');new(H/'fx3-gpe-backend-v6.h',s)
s=(H/'fx3-gpe-backend-v5.c').read_text().replace('fx3-gpe-backend-v5.h','fx3-gpe-backend-v6.h').replace('||(!q[36]&&q[37]!=255)','').replace('p->approx_blend=q[36]!=0;','p->approx_blend=q[36]!=0||q[37]!=255;').replace('||q[114]!=255||q[115]!=1','||q[115]!=1');s=s.replace('/* selector0/K255 is exact replacement. Only selectors1/2 gain the\n  * explicitly authorized approximate model; selector0/K<255 stays closed. */','/* AP97r2: selector0/K255 keeps exact replacement; selector0/K<255\n  * uses the approved straight_over_v1 approximation, as selectors1/2. */');new(H/'fx3-gpe-backend-v6.c',s)
s=(H/'fx3-gpe-observe-v19r4-parent-source.c').read_text().replace('fx3-gpe-backend-v5.h','fx3-gpe-backend-v6.h');s=s.replace('(p[36]==1||p[36]==2)','(p[36]==1||p[36]==2||p[37]!=255)').replace('selector=%u K=%u rotation=%u','selector=%u K=%u const_alpha=%u rotation=%u').replace('readable&&op!=4?p[op?114:37]:0,readable&&op==1?load32','readable&&op!=4?p[op?114:37]:0,readable&&op!=4?p[op?114:37]:0,readable&&op==1?load32');new(H/'fx3-gpe-observe-v20-const-alpha97.c',s)
serial=(R/'runs/ap97v1panelrepeat-8003227c/serial.log').read_text(errors='replace');records=[]
for seq,op,n in [(998,'BitBlit',144),(999,'BitBlit',144),(1050,'Flush',24)]:
 hits=[]
 for i,l in enumerate(serial.split('\n')):
  m=re.search(rf'FX3_GPE_RAW_PARAMS op={op} seq={seq} read=1 len={n} raw_hex=([0-9a-f]+)',l)
  if m and len(m[1])==n*2:hits.append({'LF_line':i+1,'sequence':seq,'operation':op,'raw':m[1]})
 assert len(hits)==1,(seq,len(hits));records+=hits
assert bytes.fromhex(records[2]['raw'])[1:8]==b'\0'*7
(R/'ap97r2-alpha-original-requests.json').write_text(json.dumps({'records':records,'Flush1050_reason':'adapter raster_failed sticky set by first prior nonFlush failure; successful fills already observed and raw reserved1..7 zero; no Flush gate change','authority':authority},indent=2)+'\n')
def rnd(f):return (f.numerator*2+f.denominator)//(2*f.denominator)
def r255(v):return rnd(Fraction(v,255))
def ref(src,dst,k,bpp=2):
 bits,ex,mask=(4,17,15) if bpp==2 else (8,1,255);sc=[(src>>(bits*i)&mask)*ex for i in range(4)];dc=[(dst>>(bits*i)&mask)*ex for i in range(4)];a=r255(sc[0]*k);inv=255-a;val=[a+r255(dc[0]*inv)]+[r255(sc[i]*a+dc[i]*inv) for i in range(1,4)];return sum((rnd(Fraction(v,ex)) if bpp==2 else v)<<(bits*i) for i,v in enumerate(val))
def refa(m,c,dst,k):
 a=r255(r255(m*c[3])*k);iv=255-a;d=[((dst>>(12-4*i))&15)*17 for i in range(3)];rgb=[rnd(Fraction(r255(c[i]*a+d[i]*iv),17)) for i in range(3)];oa=rnd(Fraction(a+r255((dst&15)*17*iv),17));return sum(rgb[i]<<(12-4*i) for i in range(3))|oa
Ks=[0,65,128,254,255];vectors=[];a8=[]
for k in Ks:
 for alpha in [0,1,7,15]:
  src=0xa53f&~15|alpha;dst=0x24c8;vectors.append([src,dst,k,2,ref(src,dst,k)])
 for alpha in [0,1,127,255]:
  src=0xa25b7c00|alpha;dst=0x2468ac51;vectors.append([src,dst,k,4,ref(src,dst,k,4)])
 for m in [0,1,17,127,128,254,255]:a8.append([m,231,42,186,255,0x24c8,k,refa(m,[231,42,186,255],0x24c8,k)])
def u(q,i):return struct.unpack_from('<I',q,i)[0]
def si(q,i):return struct.unpack_from('<i',q,i)[0]
def pattern(i):return(i*37+11)&255
def fnv(data):
 h=14695981039346656037
 for v in data:h=((h^v)*1099511628211)&((1<<64)-1)
 return h
def oracle(q,total):
 out=bytearray(b'\x5f\x13'*(total//2));dw,dh,sw,sh=[u(q,i) for i in [16,20,72,76]];dx=si(q,8)+si(q,40)-si(q,80);dy=si(q,12)+si(q,44)-si(q,84);sx,sy=si(q,64),si(q,68);cx,cy=si(q,24),si(q,28);cw,ch=u(q,32),u(q,36);sf=u(q,92);k=q[114];ss=u(q,88);ds=u(q,48)
 for y in range(max(dy,cy),min(dy+dh,cy+ch)):
  for x in range(max(dx,cx),min(dx+dw,cx+cw)):
   xsrc=sx+(x-dx)*sw//dw;ysrc=sy+(y-dy)*sh//dh;idx=(ysrc*ss+xsrc)*(1 if sf==2 else 2);dpos=(y*ds+x)*2;assert 0<=dpos<len(out)-1
   val=refa(pattern(idx),list(q[108:112]),0x135f,k) if sf==2 else ref(pattern(idx)|(pattern(idx+1)<<8),0x135f,k);out[dpos:dpos+2]=struct.pack('<H',val)
 return fnv(out)
params=[bytes.fromhex(x['raw']) for x in records[:2]];refs=[oracle(q,614400) for q in params]
near=bytearray(144)
for i,v in [(0,0x1000),(56,0x100000)]:struct.pack_into('<Q',near,i,v)
for i,v in [(16,3),(20,2),(32,3),(36,2),(48,3),(72,2),(76,1),(88,2)]:struct.pack_into('<I',near,i,v)
near[112]=1;near[114]=255;near[115]=1;near[121]=1;nrefs=[]
for k in Ks:q=near.copy();q[114]=k;nrefs.append(oracle(q,12))
lines=['/* Independent Fraction oracle, fixed raw AP97 requests and approved formula only. */','static const unsigned pv97[][5]={'+','.join('{'+','.join(hex(v)+'U' for v in row)+'}' for row in vectors)+'};','static const unsigned av97[][8]={'+','.join('{'+','.join(hex(v)+'U' for v in row)+'}' for row in a8)+'};']
for i,q in enumerate(params):lines.append(f'static const unsigned char native97_{i}[144]={{'+','.join(hex(v) for v in q)+'};')
lines+=['static const unsigned long long native97_fnv[2]={'+','.join(hex(v)+'ULL' for v in refs)+'};','static const unsigned char near97[144]={'+','.join(hex(v) for v in near)+'};','static const unsigned near97_K[5]={0,65,128,254,255};','static const unsigned long long near97_fnv[5]={'+','.join(hex(v)+'ULL' for v in nrefs)+'};','static const unsigned fill97_ref[5]={'+','.join(hex(ref(0xa5e8,0x24c8,k) if k<255 else 0xa5e8)+'U' for k in Ks)+'};'];new(H/'gpe97-alpha-fixture.h','\n'.join(lines)+'\n')
s=(H/'check-gpe94-r3-regression.c').read_text().replace('fx3-gpe-backend-v5.c','fx3-gpe-backend-v6.c');new(H/'check-gpe97r2-regression.c',s)
args=['clang','-O1','-g','-fsanitize=address,undefined','-fno-sanitize-recover=all',str(H/'check-gpe97r2-regression.c'),'-o',str(H/'check-gpe97r2-regression')];subprocess.run(args,check=True);c=subprocess.run([str(H/'check-gpe97r2-regression')],capture_output=True,text=True);new(H/'check-gpe97r2-regression.log',c.stdout+c.stderr);assert not c.returncode,c.stdout+c.stderr;got=re.findall(r'REF90 index=\d+ fnv=(0x[0-9a-f]+)',c.stdout);want=[x['fnv64'] for x in json.loads((R/'ap90-synthetic-73-reference.json').read_text())['commands']];assert got==want
(R/'ap97r2-alpha-reference.json').write_text(json.dumps({'K_values':Ks,'math_vectors':len(vectors),'A8_vectors':len(a8),'native_raw_sequences':[998,999],'native_synthetic_pixel_FNV':[hex(x) for x in refs],'nearest_synthetic_FNV':[hex(x) for x in nrefs],'unchanged_prior_73_FNV':True,'reference':'Python Fraction independent rounding at each approved stage; host synthetic source pixels, no Sony hardware oracle','authority':authority},indent=2)+'\n');print('GPE97R2 prepared: Fraction oracles, original raw998/999, retained73FNV pass')
