from pathlib import Path
import json,re,subprocess,hashlib
R=Path(__file__).resolve().parent;H=R/'helpers';run=R/'runs/ap94child-ad25d7a1';lines=(run/'serial.log').read_bytes().decode(errors='replace').split('\n');raw=next(re.search(r'raw_hex=([0-9a-f]{288})',l)[1] for l in lines if 'FX3_GPE_RAW_PARAMS op=BitBlit seq=86 ' in l);results=[]
for suffix,adapter,backend in [('v18','fx3-gpe-observe-v18-frame-target.c','fx3-gpe-backend-v3.c'),('v19','fx3-gpe-observe-v19-child-stretch.c','fx3-gpe-backend-v4.c')]:
 s=(H/'check-gpe93-frame-target.c').read_text().replace('fx3-gpe-observe-v18-frame-target.c',adapter).replace('flag==1&&lifecycle_lock','flag==1&&!lifecycle_lock' if suffix=='v19' else 'flag==1&&lifecycle_lock').replace('int main(void){assert(!legacy_native_target93_main());','int retained_unused_stage94_main(void){assert(!legacy_native_target93_main());')
 s=s.replace('static unsigned char memory[EXT_BYTES]', 'static unsigned char source94[0x340000];\nstatic unsigned char memory[EXT_BYTES]')
 s=s.replace('if(off==EXT_BASE)return memory;', 'if(off==0x43ae96000UL)return private_memory;if(off>=0x410924000UL&&off<0x410c64000UL)return source94+(off-0x410924000UL);if(off==EXT_BASE)return memory;')
 s=s.replace('(p==memory||p==private_memory)', '(p==memory||p==private_memory||((U)p>=(U)source94&&(U)p<(U)source94+sizeof source94))')
 s+='\nint main(void){unsigned char p[144]={'+','.join('0x'+raw[i:i+2] for i in range(0,len(raw),2))+'};\n'
 s+=r'''physical=80;process_mem=80;draw_complete=complete;reset();private_register(0x403,1);p64(object90+0x60,0x43ae96000UL);life_enter();resource_add(object90,"native_open_return_v1");unsigned char source_obj[0x120];memcpy(source_obj,object90,sizeof source_obj);p64(source_obj+0x10,0x888);p64(source_obj+0x38,0);p64(source_obj+0x58,0x22220000);p64(source_obj+0x60,0x410924000UL);p64(source_obj+0x68,sizeof source94);p32(source_obj+0x40,0x30303030);resource_add(source_obj,"malloc_parent_v1");life_leave();
'''
 if suffix=='v19':s+='memset(children,0,sizeof children);\n'
 s+=r'''assert(!blit(0,0,86,0,p));puts("SEQ86_EXACT_RAW_PASS source_parent_no_child native403_target original_old_parent_rule");return 0;}
'''
 name='check-gpe94-seq86-'+suffix;p=H/(name+'.c');assert not p.exists();p.write_text(s);args=['clang','-O1','-g','-fsanitize=address,undefined','-fno-sanitize-recover=all','-pthread','-I',str(H),str(p),str(H/backend),'-o',str(H/name)];v=subprocess.run(args,capture_output=True,text=True);assert not v.returncode,v.stderr;v=subprocess.run([str(H/name)],capture_output=True,text=True);(H/(name+'.log')).write_text(v.stdout+v.stderr);print(name,v.returncode,v.stdout[-180:],v.stderr);assert not v.returncode;results.append({'adapter':adapter,'exit':v.returncode,'source_without_child':True,'exact_original_raw144_hex':raw,'log':str(H/(name+'.log'))})
(R/'ap94-seq86-host-comparison.json').write_text(json.dumps({'run':run.name,'results':results,'conclusion':'both v18 native403 extension of v16r2 parent-source policy and v19 accept identical captured seq86 with no source child record; guest transient guard source not determined','not_runtime_root_cause_proof':True},indent=2)+'\n')
