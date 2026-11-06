"""Adapt pinned OWN240/234 sources; never import or run downloaded firmware."""
from pathlib import Path
from hashlib import sha256
import json
H=Path(__file__).resolve().parent
bridge=(H/'seed-bridge.c').read_text()
bridge=bridge.replace('0x00b70002u','0x00b70003u').replace('base[56]!=5','base[56]!=6')
bridge=bridge.replace('bj_g64(p+16)!=0x400000ULL+(u64)i*PAGE','bj_g64(p+16)!=(u64)i*PAGE')
bridge=bridge.replace('bj_g64(p+32)!=(i==3?0u:PAGE)','bj_g64(p+32)!=PAGE')
bridge=bridge.replace('const u8 *p=base+64+56*4;return bj_g32(p)==0x6474e551u&&bj_g32(p+4)==6;',
'''const u8 *p=base+64+56*4;
 if(bj_g32(p)!=2||bj_g32(p+4)!=6||bj_g64(p+8)!=3*PAGE||bj_g64(p+16)!=3*PAGE||bj_g64(p+32)!=112||bj_g64(p+40)!=112)return 0;
 p=base+64+56*5;return bj_g32(p)==0x6474e551u&&bj_g32(p+4)==6;''')
bridge=bridge.replace('static int validate(struct bridge_job *j',
'''__attribute__((visibility("hidden"))) int fx3_bridge_image_id(u8 out[32]){return image_hash(__capsule_base,out);}
static int validate(struct bridge_job *j''')
(H/'bridge.c').open('x').write(bridge)

p=(H/'seed-prepare.c').read_text()
p=p.replace('extern const u8 __fx3_elf_base[]','extern const u8 __capsule_base[]').replace('__fx3_elf_base','__capsule_base')
p=p.replace('static const char worker_sha[]="c711f6ab13666c45249cc255d2ab09ec283496214d8941d11b9f1569124c47ec";',
'''static const char worker_sha[]="0bf01a5c42ea6a7591d30954fea8448d65c45dae28ec2c20b6769e12f188b1b4";
extern int fx3_bridge_start(const u8 *,unsigned long) __attribute__((visibility("hidden")));
extern int fx3_bridge_image_id(u8 *) __attribute__((visibility("hidden")));''')
p=p.replace('FX3PREPCONFIGv1','FX3ENTRYCFGv2').replace('get32(p+16)!=1','get32(p+16)!=2',1)
p=p.replace('get64(p+152)!=131864','get64(p+152)!=262144')
p=p.replace('return nonzero(__capsule_base+4352,32);','return 1;')
start=p.index('static int image_profile(');end=p.index('static int store(',start)
p=p[:start]+'''/* Full file SHA and zero-normalized immutable image ID are DISTINCT.
 * File consistency/parent profile do not authenticate the controller. */
static int image_profile(u8 full_sha[32],u8 image_id[32]){
 const u8 *base=__capsule_base;long fd=sc(56,AT_FDCWD,(long)"/tmp/jiritsu/libJit.so",RD,0);if(fd<0)return 0;
 struct kstat a,z;struct sha full,norm;u8 buf[4096],actual[32],extra=0;int ok=0;
 if(!stat_(fd,&a)||(a.mode&0170000)!=0100000||a.uid||a.nlink!=1||a.size!=262144||!fx3_bridge_image_id(actual))goto end;
 sha_init(&full);sha_init(&norm);
 for(u32 at=0;at<262144;at+=4096){
  if(sc(63,fd,(long)buf,4096,0)!=4096)goto end;sha_update(&full,buf,4096);
  if(at<196608){if(!equal(buf,base+at,4096))goto end;}else zero(buf,4096);
  sha_update(&norm,buf,4096);
 }
 sha_final(&full,full_sha);sha_final(&norm,image_id);
 if(!equal(image_id,actual,32)||sc(63,fd,(long)&extra,1,0)||!stat_(fd,&z)||!stable(&a,&z))goto end;ok=1;
end:if(sc(57,fd,0,0,0))ok=0;return ok;
}
''' + p[end:]
p=p.replace('__attribute__((constructor)) static void fx3_module_init(void){','static int prepare_fixed(u8 accepted[256]){')
p=p.replace('u8 own_sha[32],plan[256],report[256]','u8 own_sha[32],image_id[32],plan[256],report[256]')
p=p.replace('if(!parent_identity()||!config_valid()||!image_profile(own_sha))return;',
            'if(!parent_identity()||!config_valid()||!image_profile(own_sha,image_id))return 0;')
p=p.replace('copy(plan+32,cfg+32,112);','copy(plan+32,cfg+32,112);copy(plan+112,image_id,32);')
p=p.replace('copy(report+112,cfg+112,32);','copy(report+112,image_id,32);')
p=p.replace('else state=1;','else{copy(accepted,plan,256);state=1;}')
p=p[:p.index('__attribute__((visibility("default"))) int fx3_prepare_state')]
last=p.rfind('\n}')
p=p[:last]+'\n return state==1;'+p[last:]
p+='''
/* Zero explicit arguments: named directly by DT_INIT. Never exits caller.
 * The enclosing dlopen/dlclose and controller return remain unverified. */
__attribute__((visibility("hidden"))) void fx3_entry_init(void){
 u8 private_plan[256];if(!prepare_fixed(private_plan))return;
 state=2;int r=fx3_bridge_start(private_plan,256);
 if(r==11){state=11;reason=0;}else{state=2;reason=100+r;}
}
__attribute__((visibility("hidden"))) int fx3_entry_state(void){return state;}
__attribute__((visibility("hidden"))) int fx3_entry_reason(void){return reason;}
'''
(H/'front.c').open('x').write(p)

s=(H/'seed-bridge_build.py').read_text().replace('BASE=0x400000','BASE=0')
s=s.replace("'fx3_isolated_collector_core'}","'fx3_isolated_collector_core','fx3_bridge_image_id','fx3_entry_init','fx3_entry_state','fx3_entry_reason'}")
s=s.replace('len(raw_objects)==4','len(raw_objects)==5')
s=s.replace('content=bytearray();mem=0;members=[]','content=bytearray(4096) if flags==6 else bytearray();mem=len(content);members=[]')
s=s.replace("PAGE if g['flags']!=6 else 0","PAGE")
s=s.replace("ph.append((0x6474e551,6,0,0,0,0,0,16))",'''init_oi,init_symbol=globals_['fx3_entry_init']
    initializer=placements[(init_oi,init_symbol['section'])]['va']+init_symbol['value']
    dynamic=[(4,8192),(5,8232),(6,8208),(10,1),(11,24),(12,initializer),(0,0)]
    for i,item in enumerate(dynamic):struct.pack_into('<qQ',output,3*PAGE+i*16,*item)
    output[8192:8208]=struct.pack('<4I',1,1,0,0)
    output[8208:8232]=bytes(24);output[8232]=0
    cfg=bytearray(256);cfg[:16]=b'FX3ENTRYCFGv2'.ljust(16,b'\\0')
    struct.pack_into('<IIII',cfg,16,2,1,1,1);cfg[32:48]=b'\\xbb'*16;cfg[48:80]=b'\\xcc'*32;cfg[80:112]=b'\\xdd'*32
    cfg[112:144]=bytes.fromhex('0bf01a5c42ea6a7591d30954fea8448d65c45dae28ec2c20b6769e12f188b1b4')
    struct.pack_into('<QQI',cfg,144,60000000000,262144,1)
    import zlib
    struct.pack_into('<I',cfg,252,zlib.crc32(cfg[:252]));output[4096:4352]=cfg
    ph.append((2,6,3*PAGE,3*PAGE,3*PAGE,112,112,8))
    ph.append((0x6474e551,6,0,0,0,0,0,16))''')
s=s.replace('HEADER.pack(ident,2,183','HEADER.pack(ident,3,183')
s=s.replace("h[1:4]==(2,183,1)","h[1:4]==(3,183,1)")
s=s.replace("h[8:11]==(64,56,5)","h[8:11]==(64,56,6)")
s=s.replace("if kind==0x6474e551:","if kind==2:\n            require((flags,offset,va,pa,filesz,memsz,alignment)==(6,3*PAGE,3*PAGE,3*PAGE,112,112,8),'dynamic layout differs');continue\n        if kind==0x6474e551:")
s=s.replace("names=['parent.c','collector.c','bridge.c']","names=['parent.c','collector.c','bridge.c','front.c']")
s=s.replace("names+['bridge_job.h','sha_impl.inc']","names+['bridge_job.h','sha_impl.inc','core_support.inc','parent_ipc.inc']")
s=s.replace("b'    mov x0, #0x72000000\\n    mov x1, #256\\n    bl fx3_bridge_start\\n'", "b'    bl fx3_entry_init\\n    bl fx3_entry_state\\n'")
s=s.replace("out.put('bridge.elf',raw)","out.put('entry.so',raw)")
s=s.replace("r.update(source_pins=pins,", "r.update(ET_DYN_DT_INIT_zero_argument_entry_present=True,full_file_sha256=sha256(raw).hexdigest(),immutable_image_id=sha256(raw[:3*PAGE]+bytes(PAGE)).hexdigest(),dynamic_tags=[4,5,6,10,11,12,0],source_pins=pins,")
s=s.replace('real_Sony_loader_constructor_or_camera_context_implemented=False','real_Sony_loader_execution_or_camera_context_verified=False')
(H/'entry_build.py').open('x').write(s)
record=dict(own_sources_only=True,generated={n:sha256((H/n).read_bytes()).hexdigest() for n in ['front.c','bridge.c','entry_build.py']},
 plan_image_field_now_zero_normalized_immutable_image_ID_not_full_file_SHA=True,
 original_code_executed=False,device_operations=0)
(H/'source-assembly.json').open('x').write(json.dumps(record,indent=2)+'\n')
print(json.dumps(record))
