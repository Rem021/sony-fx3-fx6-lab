from pathlib import Path
from fractions import Fraction
import json,subprocess,hashlib
R=Path(__file__).resolve().parent;H=R/'helpers';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
p=H/'fx3-gpe-backend-v5.h';assert not p.exists();p.write_text((H/'fx3-gpe-backend-v4.h').read_text().replace('BACKEND_V4_H','BACKEND_V5_H').replace('unsigned approx_fmt2, approx_stretch;', 'unsigned approx_fmt2, approx_stretch; /* stretch:1 nearest_v1 edge;2 nearest_v2 pixel-center */'))
s=(H/'fx3-gpe-backend-v4.c').read_text().replace('fx3-gpe-backend-v4.h','fx3-gpe-backend-v5.h')
s=s.replace('if(!sw||!sh||sw>INT32_MAX/4||sh>GPE_MAX_ROWS/4||dw!=sw*4||dh!=sh*4)return GPE_UNSUPPORTED;', 'if(!sw||!sh||!dw||!dh||sw>INT32_MAX||dw>INT32_MAX||sh>GPE_MAX_ROWS||dh>GPE_MAX_ROWS)return GPE_BOUNDS;')
s=s.replace('p->approx_stretch=1;p->approx_blend=0;', 'p->approx_stretch=2;p->approx_blend=0;')
s=s.replace('uint32_t sy=se?(uint32_t)(((uint64_t)y+p->offset_y)*p->src_rows/p->target_height):0;', 'uint32_t sy=se?(uint32_t)(p->approx_stretch==2?(((uint64_t)y+p->offset_y)*2+1)*p->src_rows/((uint64_t)p->target_height*2):((uint64_t)y+p->offset_y)*p->src_rows/p->target_height):0;\n  if(se&&sy>=p->src_rows)sy=p->src_rows-1;')
s=s.replace('uint32_t sx=se?(uint32_t)((x/p->bpp+p->offset_x)*p->source_width/p->target_width):0;', 'uint32_t sx=se?(uint32_t)(p->approx_stretch==2?((x/p->bpp+p->offset_x)*2+1)*p->source_width/((uint64_t)p->target_width*2):(x/p->bpp+p->offset_x)*p->source_width/p->target_width):0;\n   if(se&&sx>=p->source_width)sx=p->source_width-1;')
(H/'fx3-gpe-backend-v5.c').write_text(s)
s=(H/'fx3-gpe-observe-v19r2-diag.c').read_text().replace('fx3-gpe-backend-v4.h','fx3-gpe-backend-v5.h').replace('plan.approx_stretch?"nearest_v1":"none"','plan.approx_stretch==2?"nearest_v2":plan.approx_stretch?"nearest_v1":"none"');(H/'fx3-gpe-observe-v19r3-nearest-v2.c').write_text(s)
# Independent exact rational center-index fixture, not Sony hardware oracle.
cases=[(49,49,103,116,64,112),(49,49,7,5,64,16),(1,7,1,13,16,16),(7,1,13,1,16,16),(1,1,5,9,16,16),(29,29,116,116,32,128)]
fixture=[];refs=[]
for sw,sh,dw,dh,ss,ds in cases:
 vals=[]
 for y in range(dh):
  yy=min(sh-1,int(Fraction(2*y+1,2)*sh/dh))
  for x in range(dw):
   xx=min(sw-1,int(Fraction(2*x+1,2)*sw/dw));vals.append(((xx*37+yy*53)^0xa530)&65535)
 if (sw,sh,dw,dh)==(29,29,116,116):assert all(vals[y*dw+x]==(((x//4*37+y//4*53)^0xa530)&65535) for y in range(dh) for x in range(dw))
 fixture.append('static const unsigned short expect94r3_'+str(len(refs))+'[]={'+','.join(str(v) for v in vals)+'};');refs.append({'source':[sw,sh],'destination':[dw,dh],'strides':[ss,ds],'expected_LE16_sha256':hashlib.sha256(b''.join(v.to_bytes(2,'little') for v in vals)).hexdigest()})
(H/'gpe94r3-center-fixture.h').write_text('\n'.join(fixture)+'\n')
s=(H/'check-gpe94-r2-diag.c').read_text().replace('fx3-gpe-observe-v19r2-diag.c','fx3-gpe-observe-v19r3-nearest-v2.c').replace('int main(void){assert(!retained_frame94_main());raster_vectors94();admission_vectors94();return 0;}','int retained_94r2_main(void){assert(!retained_frame94_main());raster_vectors94();admission_vectors94();return 0;}')
# one prior unsupported vector used zero source size; all nine rejects remain valid.
s+='\n#include "gpe94r3-center-fixture.h"\nstatic const unsigned dims94r3[][6]={'+','.join('{'+','.join(map(str,v))+'}' for v in cases)+'};\nstatic const unsigned short*expect94r3[]={'+','.join('expect94r3_'+str(i) for i in range(len(cases)))+'};\n'
s+=r'''
int main(void){assert(!retained_94r2_main());for(unsigned v=0;v<sizeof(dims94r3)/sizeof(dims94r3[0]);v++){
 const unsigned*d=dims94r3[v];unsigned sw=d[0],sh=d[1],dw=d[2],dh=d[3],ss=d[4],ds=d[5];unsigned char p[144];reset();private_register(0,0);memset(children,0,sizeof children);life_enter();child_add(&resources[0],0x12340100,PRIVATE_BASE+0x100,0x10000,0x40);child_add(&resources[0],0x12360000,PRIVATE_BASE+0x20000,0x10000,0x40);life_leave();memset(private_memory,0xa5,sizeof private_memory);memset(private_memory+0x100,0x3d,0x10000);
 for(unsigned y=0;y<sh;y++)for(unsigned x=0;x<sw;x++){unsigned short value=((x*37+y*53)^0xa530)&65535;memcpy(private_memory+0x100+(y*ss+x)*2,&value,2);}memcpy(private_before,private_memory,sizeof private_memory);
 stretch94(p);p64(p,PRIVATE_BASE+0x20000);p32(p+16,dw);p32(p+20,dh);p32(p+32,dw);p32(p+36,dh);p32(p+48,ds);p32(p+72,sw);p32(p+76,sh);p32(p+88,ss);
 struct gpe_plan plan;assert(!gpe_plan_blit(p,144,&plan)&&plan.approx_stretch==2&&!plan.approx_blend);assert(!blit(0,0,3000+v,0,p));for(unsigned y=0;y<dh;y++)for(unsigned x=0;x<dw;x++)memcpy(private_before+0x20000+(y*ds+x)*2,&expect94r3[v][y*dw+x],2);assert(!memcmp(private_before,private_memory,sizeof private_memory));printf("CENTER94R3_PASS index=%u source=%ux%u destination=%ux%u allpixels_padding_source_neighbors_exact\n",v,sw,sh,dw,dh);
 }return 0;}
'''
(H/'check-gpe94-r3-center.c').write_text(s)
# unchanged73 reference regression compiled against new backend
(H/'check-gpe94-r3-regression.c').write_text((H/'check-gpe90-backend.c').read_text().replace('fx3-gpe-backend-v3.c','fx3-gpe-backend-v5.c'))
checks=[]
for name,ss in [('check-gpe94-r3-center',['check-gpe94-r3-center.c','fx3-gpe-backend-v5.c']),('check-gpe94-r3-regression',['check-gpe94-r3-regression.c'])]:
 args=['clang','-O1','-g','-fsanitize=address,undefined','-fno-sanitize-recover=all','-pthread','-I',str(H),*[str(H/n) for n in ss],'-o',str(H/name)];p=subprocess.run(args,capture_output=True,text=True);assert not p.returncode,p.stderr;p=subprocess.run([str(H/name)],capture_output=True,text=True);log=H/(name+'.log');log.write_text(p.stdout+p.stderr);print(name,p.returncode,p.stdout[-500:],p.stderr);assert not p.returncode;checks.append({'test':name,'ASan_UBSan_exit':0,'log':str(log),'log_sha256':sha(log)})
old='fx3-gpe-observe-v19r2-diag';new='fx3-gpe-observe-v19r3-nearest-v2';args=[x.replace(old,new).replace('fx3-gpe-backend-v4.c','fx3-gpe-backend-v5.c') for x in json.loads((H/(old+'-build.json')).read_text())['args']];p=subprocess.run(args,capture_output=True,text=True);assert not p.returncode,p.stderr;(H/(new+'-build.json')).write_text(json.dumps({'args':args,'exit':0,'authority':'msg_c030a5a3da12','source_sha256':sha(H/(new+'.c')),'output_sha256':sha(H/(new+'.so'))},indent=2)+'\n')
(R/'ap94-r3-nearest-v2-host-check.json').write_text(json.dumps({'authority':'msg_c030a5a3da12','checks':checks,'exact_rational_pixel_center_references':refs,'old_4x_expected_pixels_identical':True,'hardware_sampling_precision_unproven':True,'guards_unchanged':True,'formula':'min(sw-1,floor((dx+0.5)*sw/dw)), min(sh-1,floor((dy+0.5)*sh/dh))'},indent=2)+'\n')
s=(R/'prepare_candidate94_r2.py').read_text().replace("D=R/'ap94-r2-guard-diagnostics'","D=R/'ap94-r3-nearest-v2'").replace("base=R/'ap94-child-stretch/candidate.json'","base=R/'ap94-r2-guard-diagnostics/candidate.json'").replace('fx3-gpe-observe-v19r2-diag.so','fx3-gpe-observe-v19r3-nearest-v2.so');a=s.index("v['scope']=");b=s.index('\n(D/',a);s=s[:a]+"v['scope']='AP94-r3 Lead msg_c030a5a3da12 approved nearest_v2 pixel-center sampler for existing fmt0/selector0/K255/flags0/rotation0/zero-coordinates/fullclip/reg7600 overwrite subset, any positive bounded source/destination dimensions incl anisotropic and downscale. All parent/child/screen/OSD/FIFO/completion/input/RM/compaction guards unchanged; hardware sampling precision unproven. Same manually confirmed English/setup/MENU script, 300s.'"+s[b:];s=s.replace("'authority':['msg_49124d89bac2']","'authority':['msg_c030a5a3da12']").replace("'host_checks':str(H/'check-gpe94-r2-diag.log')","'host_checks':str(R/'ap94-r3-nearest-v2-host-check.json')");(R/'prepare_candidate94_r3.py').write_text(s)
