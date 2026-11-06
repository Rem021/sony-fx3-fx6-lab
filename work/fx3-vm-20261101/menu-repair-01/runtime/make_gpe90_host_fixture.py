from pathlib import Path
import json,struct,hashlib
R=Path(__file__).resolve().parent;H=R/'helpers';v=json.loads((R/'ap90-rebuilt-proof.json').read_text());out=['/* Original AP89 params, synthetic resource bytes only. */','static const unsigned char params90[73][144]={']
for q in v['commands']:out.append('{'+','.join('0x'+q['raw_hex'][i:i+2] for i in range(0,288,2))+'},')
out.append('};\nstatic const unsigned vectors90[16][8]={')
for q in v['proposed_mask_formula']['synthetic_vectors']:
 d=q['dst8'];px=sum((x//17)<<(12-i*4) for i,x in enumerate(d));out.append('{'+','.join(map(str,[q['mask'],*q['color'],px,q['K'],int(q['fmt0_value'],16)]))+'},')
out.append('};');(H/'gpe90-fixture.h').write_text('\n'.join(out)+'\n')
expected=[]
for q in v['commands']:
 dst=bytearray(b'\x0f\0'*(0x140000//2));dx,dy=q['dst_xy'];dw,dh=q['dst_wh'];cx,cy=q['clip_xy'];cw,ch=q['clip_wh'];sx,sy=q['src_xy'];sw,sh=q['src_wh'];stride=q['src_stride_pixels'];fmt=q['src_fmt'];color=q['color_6c_6f'];k=q['alpha_72'];rnd=lambda n:(n+127)//255
 for y in range(max(dy,cy),min(dy+dh,cy+ch)):
  yy=sy+(y-dy)*sh//dh
  for x in range(max(dx,cx),min(dx+dw,cx+cw)):
   xx=sx+(x-dx)*sw//dw;i=yy*stride+xx
   if fmt==2:
    m=(i*17+(i//stride)*3)&255;a=rnd(m*k);cs=color[:3]
   else:
    pixel=(((i//8)%16)<<12)|(((i//stride)%16)<<8)|((i%16)<<4)|(i%16)
    a=rnd((pixel&15)*17*k);cs=[((pixel>>(12-c*4))&15)*17 for c in range(3)]
   rgba=[rnd(c*a) for c in cs]+[255];outp=sum(min(15,(c+8)//17)<<(12-z*4) for z,c in enumerate(rgba));struct.pack_into('<H',dst,0x100+(y*640+x)*2,outp)
 fnv=14695981039346656037
 for b in dst:fnv=((fnv^b)*1099511628211)&((1<<64)-1)
 expected.append({'sequence':q['sequence'],'fnv64':hex(fnv),'sha256':hashlib.sha256(dst).hexdigest()})
(R/'ap90-synthetic-73-reference.json').write_text(json.dumps({'scope':'Independent Python nearest/straight-over candidate; artificial resource patterns, not Sony pixel oracle','commands':expected},indent=2)+'\n')
print('fixture73/vector16/reference73 complete')
