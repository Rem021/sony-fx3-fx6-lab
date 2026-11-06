from pathlib import Path
R=Path(__file__).resolve().parent;H=R/'helpers';s=(H/'check-gpe-early88.c').read_text().replace('"fx3-gpe-observe-v15-earlybind.c"','"fx3-gpe-observe-v16-resources.c"')
s=s.replace('if(!strcmp(p,"/proc/self/maps"))return 82;','if(!strcmp(p,"/proc/self/maps"))return 82;if(!strcmp(p,"/proc/udm/dmm_units"))return 83;')
s=s.replace('"0 0 1 %x 0 0 3 0 43feb5000 (43feb5000+0) 140000\\n",live?0x545:0x546','"0081 0003 00000001 %08x 00000000 00000000 00000003 0000008c 43feb5000 (430400000+fab5000) 00140000\\n",live?0x545:0x546')
s=s.replace('else snprintf(buf,sizeof(buf),"%lx-%lx r-xp','else if(fd==83)snprintf(buf,sizeof(buf),"0402 00000403 0002 01 01 00 01 00000003 43feb5000 00140000 0081 < 0003\\n");else snprintf(buf,sizeof(buf),"%lx-%lx r-xp')
s=s.replace('int main(void){assert(!retained_raster_main());','int early90_main(void){assert(!retained_raster_main());')
s+='''
static unsigned char object90[0x120];static unsigned nr_open,nr_close,nr_malloc,nr_free;static int native90_result;
static int stub_resource_open(void*o,const void*c){assert(o==object90&&c==(void*)19);assert(*stub_errno()==77);nr_open++;*stub_errno()=13;return native90_result;}
static int stub_resource_close(void*o){assert(o==object90&&!lifecycle_lock);assert(*stub_errno()==77);nr_close++;*stub_errno()=14;return native90_result;}
static int stub_resource_malloc(void*o,U bytes,U align,void**out){assert(o==object90&&bytes==32&&align==16);assert(*stub_errno()==77);nr_malloc++;*out=(void*)0x12340100;*stub_errno()=15;return native90_result;}
static int stub_resource_free(void*o,void*p,unsigned flag){assert(o==object90&&p==(void*)0x12340100&&flag==1&&lifecycle_lock);assert(*stub_errno()==77);nr_free++;*stub_errno()=16;return native90_result;}
static void*free90_thread(void*unused){(void)unused;*stub_errno()=77;assert(observe_resource_free(object90,(void*)0x12340100,1)==native90_result);assert(*stub_errno()==16);return 0;}
static void check_resources90(void){
 native_resource_open=stub_resource_open;native_resource_close=stub_resource_close;native_resource_malloc=stub_resource_malloc;native_resource_free=stub_resource_free;
 memset(resources,0,sizeof(resources));resource_epoch=0;memset(object90,0,sizeof(object90));p64(object90+0x10,0x123);p32(object90+0x20,0x10);p64(object90+0x38,0x55);p32(object90+0x40,0x77);p64(object90+0x58,0x12340000);p64(object90+0x60,0x512340000);p64(object90+0x68,4096);
 native90_result=0;*stub_errno()=77;assert(!observe_resource_open(object90,(void*)19)&&*stub_errno()==13&&nr_open==1&&resources[0].active);
 struct resource_record r={0};life_enter();assert(resource_lookup(0x512340100,16,8,2,&r));assert(r.uhdl==0x77&&r.epoch==1);assert(!resource_lookup(0x512340fff,16,2,1,&r));assert(!resource_lookup(0x410524000,16,8,1,&r));life_leave();
 void*out=0;*stub_errno()=77;assert(!observe_resource_malloc(object90,32,16,&out)&&*stub_errno()==15&&nr_malloc==1);
 life_enter();U events=allocation_events;unsigned prior=nr_free;pthread_t t;assert(!pthread_create(&t,0,free90_thread,0));while(__atomic_load_n(&allocation_events,__ATOMIC_RELAXED)==events)sched_yield();assert(nr_free==prior);life_leave();assert(!pthread_join(t,0));assert(nr_free==prior+1);
 *stub_errno()=77;assert(!observe_resource_close(object90)&&*stub_errno()==14&&nr_close==1&&!resources[0].active);
 *stub_errno()=77;assert(!observe_resource_open(object90,(void*)19)&&resources[0].epoch==2);life_enter();assert(resource_lookup(0x512340100,16,8,1,&r)&&r.epoch==2);p32(object90+0x40,0x78);assert(!resource_lookup(0x512340100,16,8,1,&r)&&!resources[0].active);life_leave();
 native90_result=-9;*stub_errno()=77;assert(observe_resource_open(object90,(void*)19)==-9&&*stub_errno()==13&&!resources[0].active);puts("GPE90_RESOURCE_PASS original_once/errno/result/shared_free_lock/retire_before_close/unknown_extent_reject/reuse_epoch/native_identity_change; compaction/queuedABA untested and uncovered");
}
int main(void){assert(!early90_main());check_resources90();return 0;}
'''
(H/'check-gpe90-adapter.c').write_text(s)
