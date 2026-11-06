from pathlib import Path
R=Path(__file__).resolve().parent;H=R/'helpers'
s=(H/'fx3-gpe-observe-v17-native-target.c').read_text();needle='#include "fx3-gpe-resource-v3-target.inc"';assert s.count(needle)==1;exports=r'''
#include "fx3-frame-target-v1.h"
static __thread unsigned frame_target_held;
static int frame_target_tuple(U physical_address,U span,unsigned token,U*out){
 if(!span||span>0x10000000UL)return 0;
 U t[FT_WORDS]={1,0,0,0,0,0,0,token,0,physical_address};
 if(within(physical_address,span,span,1)&&token==0x402){struct screen_identity si={0};if(!screen_live(&si))return 0;t[1]=1;t[3]=si.serial;t[5]=EXT_BASE;t[6]=EXT_BYTES;}
 else {struct resource_record r={0};if(!obj_bound||!resource_lookup(physical_address,span,span,1,&r)||!r.native_open||r.type!=0x403||r.vptr!=resource_class_vptr||r.uhdl!=token)return 0;t[1]=2;t[2]=r.object;t[3]=r.epoch;t[4]=r.identity;t[5]=r.phys;t[6]=r.bytes;t[8]=r.vptr;}
 if(!frame_tuple_valid(t,physical_address,span,token))return 0;__builtin_memcpy(out,t,sizeof(t));return 1;
}
int fx3_gpe_frame_target_acquire(U physical_address,U span,unsigned token,U*out,unsigned capacity){if(!snapshot_owned||frame_target_held||!out||capacity!=FT_WORDS)return -1;life_enter();if(!frame_target_tuple(physical_address,span,token,out)){life_leave();return -2;}frame_target_held=1;return 0;}
int fx3_gpe_frame_target_recheck(const U*t,U physical_address,U span,unsigned token){if(!snapshot_owned||!frame_target_held||!frame_tuple_valid(t,physical_address,span,token))return -1;U current[FT_WORDS];if(!frame_target_tuple(physical_address,span,token,current)||__builtin_memcmp(t,current,sizeof(current)))return -2;return 0;}
int fx3_gpe_frame_target_release(void){if(!snapshot_owned||!frame_target_held)return -1;frame_target_held=0;life_leave();return 0;}
'''
# within is declared after include; use a forward declaration before exported code.
exports='\nstatic int within(U,U,U,unsigned);\n'+exports
s=s.replace(needle,needle+exports).replace('adapter=v17_native_target','adapter=v18_frame_target');(H/'fx3-gpe-observe-v18-frame-target.c').write_text(s)
s=(H/'fx3-osd-core-v3.h').read_text().replace('FX3_OSD_CORE_V3','FX3_OSD_CORE_V4_FRAME').replace('#define HO_DATA 0x100UL','#define HO_DATA 0x200UL').replace('0x31474e495244534fUL','0x32474e495244534fUL');s=s.replace('map_offset;};','map_offset;unsigned long frame_target[10];};');s=s.replace('static int ho_validate(const struct ho_model *s,','static int ho_validate_frame(const struct ho_model *s,').replace('unsigned long extent_bytes){if(s->failed','unsigned long extent_bytes,unsigned long prefix){if(s->failed').replace('extent_bytes<0x100||f->physical<extent_base+0x100','extent_bytes<prefix||extent_base>~0UL-prefix||f->physical<extent_base+prefix');needle='static int ho_commit(';idx=s.index(needle);s=s[:idx]+'static int ho_validate(const struct ho_model*s,const struct ho_frame*f,unsigned long bytes,int active,unsigned long base,unsigned long span){return ho_validate_frame(s,f,bytes,active,base,span,0x100);}\n'+s[idx:];(H/'fx3-osd-core-v4-frame.h').write_text(s)
s=(H/'fx3-osd-headless-v5.c').read_text().replace('fx3-osd-core-v3.h','fx3-osd-core-v4-frame.h');needle='static int (*raster_try)(void),(*raster_leave)(void);';s=s.replace(needle,needle+'\n#include "fx3-frame-target-v1.h"\nstatic int (*frame_acquire)(U,U,unsigned,U*,unsigned),(*frame_recheck)(const U*,U,U,unsigned),(*frame_release)(void);')
needle='if(!raster_try||!raster_leave)return -4;frame_api_ready=1;';assert s.count(needle)==1;s=s.replace(needle,'frame_acquire=dlsym(g,"fx3_gpe_frame_target_acquire");frame_recheck=dlsym(g,"fx3_gpe_frame_target_recheck");frame_release=dlsym(g,"fx3_gpe_frame_target_release");if(!raster_try||!raster_leave||!frame_acquire||!frame_recheck||!frame_release)return -4;frame_api_ready=1;')
s=s.replace('w[0]=HO_MAGIC;w[1]=1;','w[0]=HO_MAGIC;w[1]=2;')
s=s.replace('ref=0,reader=0,guard=0,ok=0','ref=0,reader=0,guard=0,target_held=0,ok=0')
needle='int size_rc=bsize((void *)f->bitmap,&bytes),active=extent(f->physical,f->span);int valid=ho_validate(job,f,bytes,active,0x43feb5000UL,0x140000UL);';assert s.count(needle)==1;s=s.replace(needle,'int size_rc=bsize((void *)f->bitmap,&bytes);int active=!frame_acquire(f->physical,f->span,(unsigned)f->token,f->frame_target,10);if(active)target_held=1;int valid=ho_validate_frame(job,f,bytes,active,f->frame_target[5],f->frame_target[6],f->frame_target[1]==1?0x100:0);');s=s.replace('active545=%d','active_registered_frame=%d')
needle='||!extent(f->physical,f->span)){rc=-9;goto cleanup;}ok=1;';assert s.count(needle)==1;s=s.replace(needle,'||frame_recheck(f->frame_target,f->physical,f->span,(unsigned)f->token)){rc=-9;goto cleanup;}dprintf(2,"FX3_OSD_FRAME_TARGET_VALID physical=%#lx token=%#lx kind=%lu object=%#lx epoch=%lu identity=%#lx parent=%#lx bytes=%#lx vptr=%#lx original_FB=%#lx bitmap=%#lx native_read_lease=1 raster_guard=1 lifecycle_guard=1 before_after_fields_same=1\\n",f->physical,f->token,f->frame_target[1],f->frame_target[2],f->frame_target[3],f->frame_target[4],f->frame_target[5],f->frame_target[6],f->frame_target[8],f->fb,f->bitmap);ok=1;')
s=s.replace('cleanup:if(guard&&raster_leave())','cleanup:if(target_held&&frame_release()){ok=0;rc=-22;}if(guard&&raster_leave())')
needle='memcpy(slot+0xc0,job->descriptor,36);';assert s.count(needle)==1;s=s.replace(needle,'memcpy(slot+0xd0,f->frame_target,80);memcpy(slot+0x180,job->descriptor,36);')
(H/'fx3-osd-headless-v6-live-frame.c').write_text(s);print('GPEv18, OSDv6/corev4/ringV2 generated')
