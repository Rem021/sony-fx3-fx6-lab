typedef unsigned long U;typedef unsigned int W;typedef unsigned long size_t;
extern void *dlsym(void *,const char *);extern int dlinfo(void *,int,void *);extern int dprintf(int,const char *,...);extern int *__errno_location(void);extern int open(const char *,int,...);extern long read(int,void *,size_t);extern int close(int);extern long syscall(long,...);extern void *mmap(void *,size_t,int,int,int,long);extern int munmap(void *,size_t);extern int mprotect(void *,size_t,int);extern void *memcpy(void *,const void *,size_t);extern void *memset(void *,int,size_t);extern char *strstr(const char *,const char *);
struct ts{long s,n;};extern int clock_gettime(int,struct ts *);
struct lm{U base;char *name;void *dynamic;struct lm *next,*prev;};
struct ctx{U pc,continuation,id,objreg;};
extern long pread(int,void *,size_t,long);extern char *getenv(const char *);extern int strcmp(const char *,const char *);
extern void fx3_media_probe_core(void);extern int fx3_media_test(void),fx3_media_branch_test(int),fx3_media_bl_test(int);extern char fx3_media_test_point[],fx3_media_test_cb[],fx3_media_test_bl[];
__attribute__((visibility("hidden"))) int fx3_media_test_compare(U *p){for(int i=0;i<31;i++)if(p[i]!=(U)(0x100+i))return i+1;unsigned char *q=(void *)(p+32);for(int i=0;i<32;i++)for(int j=0;j<16;j++)if(q[i*16+j]!=i+1)return 100+i;if(p[96]!=0xa0000000)return 200;if(p[97]||p[98])return 202;if(p[124]!=(U)p)return 201;return 0;}

struct di {const char *file;void *base;const char *symbol;void *symaddr;};extern int dladdr(void *,struct di *);
extern int pthread_create(U *,const void *,void *(*)(void *),void *);extern int pthread_detach(U);extern int usleep(unsigned);
#include "fx3-media-params-v1.inc"
#include "fx3-media-points-v1.inc"
static int pmem=-1,active,binding,selftest_done;static U app_base,dbase,mbase,sequence;static int bound_D,bound_M,param_started;
static int peek(U p,void *out,U n){return pmem>=0&&p>=4096&&p<0x8000000000UL&&n<=0x8000000000UL-p&&pread(pmem,out,n,p)==(long)n;}
static W word(U p){W v=0xffffffffU;peek(p,&v,4);return v;}static U pointer(U p){U v=0;peek(p,&v,8);return v;}
static U stamp(void){struct ts t={0};clock_gettime(1,&t);return (U)t.s*1000000000UL+t.n;}
static __thread U eid;static __thread int inside;
static void raw(const char *tag,U p,U n){int saved=*__errno_location();char hex[8193];unsigned char b[4096];if(n>4096||!peek(p,b,n)){dprintf(2,"FX3_MEDIA_RAW eid=%lu tid=%ld tag=%s pointer=%#lx bytes=%lu readable=0 limit=4096 passive=1\n",eid,syscall(178),tag,p,n);*__errno_location()=saved;return;}const char *h="0123456789abcdef";for(U i=0;i<n;i++){hex[2*i]=h[b[i]>>4];hex[2*i+1]=h[b[i]&15];}hex[2*n]=0;dprintf(2,"FX3_MEDIA_RAW eid=%lu tid=%ld tag=%s pointer=%#lx bytes=%lu readable=1 raw=%s passive=1\n",eid,syscall(178),tag,p,n,hex);*__errno_location()=saved;}
static void frame(U pc,unsigned depth){struct di d={0};dladdr((void*)pc,&d);dprintf(2,"FX3_MEDIA_STACK eid=%lu tid=%ld depth=%u pc=%#lx module=%s relative=%#lx passive=1\n",eid,syscall(178),depth,pc,d.file?d.file:"unknown",d.base?pc-(U)d.base:0);}
static void stack(U pc,U fp){frame(pc,0);for(unsigned j=1;j<=12;j++){U v[2];if((fp&15)||!peek(fp,v,16))break;if(!v[1])break;frame(v[1],j);if(v[0]<=fp||v[0]-fp>0x100000||(v[0]&15))break;fp=v[0];}}
static void ports(const char *tag,U self){raw(tag,self+0x268,72);}
static void record(const char *tag,U p){raw(tag,p,0x3c);dprintf(2,"FX3_MEDIA_RECORD eid=%lu tid=%ld tag=%s record=%#lx mediaID=%#x state=%u mask=%#x notify_destination=%#x passive=1\n",eid,syscall(178),tag,p,word(p+0xc),word(p+0x38),word(p+0x14),word(p+0x1c));}
static W last_cur[10],last_shadow[10];static unsigned last_valid[10];static int param_lock;
static void sample(const char *why){if(!app_base||__atomic_test_and_set(&param_lock,__ATOMIC_ACQUIRE))return;for(unsigned i=0;i<10;i++){W a=0,b=0;unsigned ok=peek(app_base+params[i].offset,&a,params[i].size)&&peek(app_base+params[i].shadow_offset,&b,params[i].size);if(!last_valid[i]||ok!=last_valid[i]||a!=last_cur[i]||b!=last_shadow[i]){dprintf(2,"FX3_MEDIA_PARAM eid=%lu tid=%ld ns=%lu reason=%s id=%#lx current=%#x shadow=%#x bytes=%u readable=%u offset=%#lx read_only=1\n",eid,syscall(178),stamp(),why,params[i].id,a,b,params[i].size,ok,params[i].offset);last_cur[i]=a;last_shadow[i]=b;last_valid[i]=ok;}}__atomic_clear(&param_lock,__ATOMIC_RELEASE);}
static void *sampler(void *unused){(void)unused;for(;;){sample("period100ms_target");usleep(100000);}return 0;}
struct call {U self,payload,sp,caller,token;};static __thread struct call rm,status_call,mount_call;
__attribute__((visibility("hidden"))) void fx3_media_event(struct ctx *c,U *r){int saved=*__errno_location();U id=c->id;
 if(id==63){
  __asm__ volatile("mov x18,xzr; msr nzcv,xzr; movi v0.16b,#0; movi v1.16b,#0; movi v2.16b,#0; movi v3.16b,#0; movi v4.16b,#0; movi v5.16b,#0; movi v6.16b,#0; movi v7.16b,#0; movi v8.16b,#0; movi v9.16b,#0; movi v10.16b,#0; movi v11.16b,#0; movi v12.16b,#0; movi v13.16b,#0; movi v14.16b,#0; movi v15.16b,#0; movi v16.16b,#0; movi v17.16b,#0; movi v18.16b,#0; movi v19.16b,#0; movi v20.16b,#0; movi v21.16b,#0; movi v22.16b,#0; movi v23.16b,#0; movi v24.16b,#0; movi v25.16b,#0; movi v26.16b,#0; movi v27.16b,#0; movi v28.16b,#0; movi v29.16b,#0; movi v30.16b,#0; movi v31.16b,#0":::"x18","v0","v1","v2","v3","v4","v5","v6","v7","v8","v9","v10","v11","v12","v13","v14","v15","v16","v17","v18","v19","v20","v21","v22","v23","v24","v25","v26","v27","v28","v29","v30","v31","cc","memory");*__errno_location()=saved;return;
 }
 if(inside){*__errno_location()=saved;return;}inside=1;eid=__atomic_add_fetch(&sequence,1,__ATOMIC_RELAXED);
 dprintf(2,"FX3_MEDIA_POINT eid=%lu tid=%ld ns=%lu module=%c point=%#lx x0=%#lx x1=%#lx x2=%#lx x3=%#lx x4=%#lx x5=%#lx x6=%#lx sp=%#lx lr=%#lx passive=1\n",eid,syscall(178),stamp(),id==0x22eacd48?'A':id&0x100000?'M':'D',id==0x22eacd48?0x2eacd48:id&0xfffff,r[0],r[1],r[2],r[3],r[4],r[5],r[6],r[35],r[30]);
 switch(id){
 case 0x22eacd48:{W tag=word(r[1]);if((W)r[0]==0x5503e0&&(tag==0x10002||tag==0x10003)){dprintf(2,"FX3_MEDIA_INSERT_SEND eid=%lu tid=%ld ns=%lu destination=%#x tag=%#x bytes=28 original_native_callsite=2eacd48 original_send_follows=1 synthetic=0 source_in_existing_BOOT_QUEUE_SEND=1\n",eid,syscall(178),stamp(),(W)r[0],tag);raw("NATIVE_INSERT_FULL28",r[1],28);stack(c->pc+4,r[29]);}break;}
 case 0xe6dc: stack(r[30],r[29]);break;
 case 0xe750: dprintf(2,"FX3_MEDIA_FRONT eid=%lu tid=%ld source=%#x bytes=%u self=%#lx original_metadata_calls_complete=1 original_free_follows=1\n",eid,syscall(178),(W)r[24],(W)r[23],r[19]);raw("FRONT_FULL_BODY",r[21],(W)r[23]);break;
 case 0xf1e4:rm=(struct call){r[0],r[1],r[35],r[30],eid};raw("RM_ENTRY_HEADER24",r[0],24);stack(r[30],r[29]);break;
 case 0xf274: {unsigned short n=0;peek(r[1]+6,&n,2);raw("RM_SEND_FULL24_PLUS_PAYLOAD",r[1],24+n);break;}
 case 0xf2b8:raw("RM_NATIVE_REPLY_BEFORE_FREE",pointer(r[29]+0x38),(W)r[0]);break;
 case 0xf31c:dprintf(2,"FX3_MEDIA_RM_RETURN eid=%lu tid=%ld token=%lu native_rc=%#x entry_SP_matches=%u caller=%#lx\n",eid,syscall(178),rm.token,(W)r[0],r[35]==rm.sp,rm.caller);if(r[35]==rm.sp){raw("RM_RETURN_HEADER24",rm.self,24);unsigned short n=0;peek(rm.self+6,&n,2);if(n)raw("RM_RETURN_PAYLOAD",rm.payload,n);}break;
 case 0xf380:status_call=(struct call){r[0],r[2],r[35],r[30],eid};dprintf(2,"FX3_MEDIA_STATUS_ENTER eid=%lu mediaID=%#x output=%#lx\n",eid,(W)r[1],r[2]);break;
 case 0xf39c:dprintf(2,"FX3_MEDIA_STATUS_MISSING_RECORD eid=%lu original_error_tail_follows=1\n",eid);break;
 case 0xf468:dprintf(2,"FX3_MEDIA_STATUS_RETURN eid=%lu token=%lu native_rc=%#x entry_SP_matches=%u\n",eid,status_call.token,(W)r[0],r[35]==status_call.sp);if(r[35]==status_call.sp)raw("GET_INOUT_STATUS6",status_call.payload,6);break;
 case 0xf8d8:record("NOTIFY_ADAPTER_RECORD",r[1]);ports("NOTIFY_ADAPTER_PORTS",r[0]);stack(r[30],r[29]);break;
 case 0xd40c:dprintf(2,"FX3_MEDIA_NOTIFY eid=%lu tid=%ld mediaID=%#x destination=%#x status=%d hold=%d RemoveCnt=%u extra16=%u native=1 synthetic=0\n",eid,syscall(178),(W)r[1],(W)r[2],(signed char)r[3],(signed char)r[4],(unsigned char)r[5],(unsigned short)r[6]);stack(r[30],r[29]);break;
 case 0xd534:raw("NOTIFY_HEADER24",r[3],(W)r[4]);raw("NOTIFY_PAYLOAD16",r[1],(W)r[2]);break;
 case 0xf92c:raw("START_REQUEST6",r[2],6);ports("START_ENTRY_PORTS",r[0]);stack(r[30],r[29]);break;
 case 0xf978:record("START_FOUND_RECORD_BEFORE_ACTIVE_CHECK",r[0]);break;
 case 0xf9a0:record("START_INITIAL_RECORD",r[19]);ports("START_INITIAL_PORTS",r[21]);raw("START_INITIAL_REQUEST6",r[20],6);break;
 case 0xfa00:record("START_BRANCH_RECORD",r[19]);dprintf(2,"FX3_MEDIA_START_BRANCH eid=%lu state=%u if_state2_native_status0_else_request_and_count=1\n",eid,(W)r[0]);break;
 case 0xfa24:case 0xfa3c:dprintf(2,"FX3_MEDIA_START_NOTIFY eid=%lu branch=%#lx status=%d native_branch=1\n",eid,id,(signed char)r[2]);record("START_NOTIFY_RECORD",r[1]);break;
 case 0xe8f4:ports("THREAD_INIT_ENTRY_PORTS",r[0]);stack(r[30],r[29]);break;
 case 0xe9d4:dprintf(2,"FX3_MEDIA_INIT_WAIT_RETURN eid=%lu native_rc=%u\n",eid,(W)r[0]);ports("THREAD_INIT_WAIT_PORTS",r[20]);break;
 case 0xe9e0:dprintf(2,"FX3_MEDIA_INIT_TIMEOUT eid=%lu native_timeout110_taken=1 default_object_initialization_follows=1\n",eid);break;
 case 0xec34:raw("THREAD_INIT_DEFAULT_OBJECTS",pointer(r[20]+0x2a8),48);ports("THREAD_INIT_AFTER_DEFAULT_OBJECTS_PORTS",r[20]);break;
 case 0x1091c:dprintf(2,"FX3_MEDIA_INTERNAL_ENTER eid=%lu type=%#x self=%#lx object=%#lx\n",eid,(W)r[1],r[0],r[2]);stack(r[30],r[29]);break;
 case 0x109e0:raw("FRONT_DECODE_BODY7",r[0],7);ports("FRONT_DECODE_BEFORE_PORTS",r[19]);break;
 case 0x10d38:ports("FRONT_DECODE_AFTER_PORTS",r[19]);break;
 case 0x109c98:mount_call=(struct call){r[0],r[1],r[35],r[30],eid};dprintf(2,"FX3_MEDIA_MOUNT_ENTER eid=%lu tid=%ld mediaID=%#x self=%#lx out=%#lx native=1\n",eid,syscall(178),word(r[0]+8),r[0],r[1]);stack(r[30],r[29]);break;
 case 0x109d6c:dprintf(2,"FX3_MEDIA_MOUNT_RETURN eid=%lu tid=%ld token=%lu mediaID=%#x native_rc=%#x entry_SP_matches=%u\n",eid,syscall(178),mount_call.token,word(mount_call.self+8),(W)r[0],r[35]==mount_call.sp);if(r[35]==mount_call.sp){raw("MOUNT_OUTPUT8",mount_call.payload,8);raw("MOUNT_SELF_STATE",mount_call.self,0xc0);}break;
 case 0x109dc4:raw("MEDIA_COMMON_QUERY_REQUEST_E4",r[1],(W)r[2]);break;
 case 0x109dc8:dprintf(2,"FX3_MEDIA_COMMON_QUERY_RETURN eid=%lu wrapper_rc=%#x mediaID=%#x valid=%u\n",eid,(W)r[0],word(r[19]+8),({unsigned char b=255;peek(r[22]+0x1c,&b,1);b;}));raw("MEDIA_COMMON_QUERY_REPLY_E4",r[22],0xe4);break;
 case 0x109e40:raw("MOUNT_QUERY_SUCCESS_REPLY_E4",r[22],0xe4);break;
 case 0x109e14:raw("MCMN_DRV_OPEN_PATH21",r[0],21);dprintf(2,"FX3_MEDIA_DRV_OPEN_ENTER eid=%lu tid=%ld mediaID=%#x path=%#lx flags=%#x handle_output=%#lx\n",eid,syscall(178),word(r[19]+8),r[0],(W)r[1],r[2]);break;
 case 0x109e18:dprintf(2,"FX3_MEDIA_DRV_OPEN_RETURN eid=%lu tid=%ld mediaID=%#x native_rc=%#x handle=%#lx\n",eid,syscall(178),word(r[19]+8),(W)r[0],pointer(r[19]+0xb0));break;
 case 0x109eac:dprintf(2,"FX3_MEDIA_DRV_GETINFO_RETURN eid=%lu native_rc=%#x\n",eid,(W)r[0]);break;
 case 0x109ef8:dprintf(2,"FX3_MEDIA_MOUNT_CONVERTED_RETURN eid=%lu tid=%ld mediaID=%#x infra_rc=%#x\n",eid,syscall(178),word(r[19]+8),(W)r[20]);break;
 }
 sample("native_media_point");inside=0;*__errno_location()=saved;
}
static void sync_code(unsigned char *p,U n){U ctr;__asm__ volatile("mrs %0,ctr_el0":"=r"(ctr));U dc=4UL<<((ctr>>16)&15),ic=4UL<<(ctr&15);for(U a=(U)p&~(dc-1);a<(U)p+n;a+=dc)__asm__ volatile("dc cvau,%0"::"r"(a):"memory");__asm__ volatile("dsb ish":::"memory");for(U a=(U)p&~(ic-1);a<(U)p+n;a+=ic)__asm__ volatile("ic ivau,%0"::"r"(a):"memory");__asm__ volatile("dsb ish;isb":::"memory");}
struct pool{unsigned char*p;U used;};static struct pool test_pool,pool_D,pool_M,pool_A;
static W branch(U at,U to){return 0x14000000U|((W)((long)(to-at)/4)&0x3ffffff);}
static W literal(unsigned int reg,unsigned int from,unsigned int to){return 0x58000000U|(((to-from)/4)<<5)|reg;}
static int allocate_pool(struct pool *pool,U pc){if(pool->p)return 0;for(U i=1;i<1792;i++)for(int sign=-1;sign<=1;sign+=2){U hint=(pc&~4095UL)+sign*(i*0x10000);void *p=mmap((void *)hint,8192,3,0x22,-1,0);if(p==(void *)-1)continue;long d=(long)((U)p-pc);if(d>-(120L<<20)+8192&&d<(120L<<20)-8192){pool->p=p;return 0;}munmap(p,8192);}return -1;}
static int install(struct pool *pool,U pc,W expected,U id,U objreg){
 W original=*(W *)pc;if(original!=expected)return -2;if(allocate_pool(pool,pc)||pool->used+128>8192)return -3;unsigned char *p=pool->p+pool->used;long delta=(long)((U)p-pc);if(delta<=-(1L<<27)||delta>=(1L<<27))return -8;pool->used+=128;if(mprotect(pool->p,8192,7))return -4;memset(p,0,128);W *code=(void *)p;code[0]=0xa9bf47f0;code[1]=literal(16,4,32);code[2]=literal(17,8,40);code[3]=0xd61f0220;code[4]=0xa8c147f0;
 code[5]=original;code[6]=branch((U)p+24,pc+4);code[7]=0xd503201f;U context=(U)p+48,core=(U)fx3_media_probe_core;memcpy(p+32,&context,8);memcpy(p+40,&core,8);struct ctx c={pc,(U)p+16,id,objreg};memcpy(p+48,&c,sizeof c);
 if((original&0x7e000000U)==0x34000000U){long imm=(original>>5)&0x7ffff;if(imm&(1<<18))imm-=1<<19;U target=pc+imm*4;code[5]=(original&0xff00001fU)|(2<<5);code[6]=branch((U)p+24,pc+4);code[7]=branch((U)p+28,target);}
 else if((original&0xfc000000U)==0x94000000U){long imm=original&0x3ffffff;if(imm&(1<<25))imm-=1<<26;U target=pc+imm*4,link=pc+4;code[5]=literal(30,20,80);code[6]=branch((U)p+24,target);memcpy(p+80,&link,8);}
 sync_code(p,128);if(mprotect(pool->p,8192,5))return -5;if(mprotect((void *)(pc&~4095UL),4096,7))return -6;*(W *)pc=branch(pc,(U)p);sync_code((void *)pc,4);if(mprotect((void *)(pc&~4095UL),4096,5))return -7;return 0;
}

static void bind(void*h,const char*name){if(!active||__atomic_test_and_set(&binding,__ATOMIC_ACQUIRE))return;int rc=0;struct lm*a=0;if(dlinfo(h,2,&a)||!a)goto out;int kind=strstr(name,"libInfraMediaDetect.so")?1:strstr(name,"libInfraMediaMount.so")?2:strstr(name,"appFw.so")?3:0;if(!kind)goto out;
 if(kind==3){if(app_base)goto out;for(unsigned i=0;i<10;i++){unsigned char b[20];if(!peek(a->base+params[i].getter,b,20)||__builtin_memcmp(b,params[i].code,20)||!peek(a->base+params[i].shadow_getter,b,20)||__builtin_memcmp(b,params[i].shadow_code,20)){dprintf(2,"FX3_MEDIA_BIND_REJECT module=A reason=parameter_getter_code id=%#lx\n",params[i].id);goto out;}}W native_word=0;if(!peek(a->base+0x2eacd48,&native_word,4)||native_word!=0x979b9872U){dprintf(2,"FX3_MEDIA_BIND_REJECT module=A reason=native_send_word\n");goto out;}rc=install(&pool_A,a->base+0x2eacd48,0x979b9872U,0x22eacd48,31);if(rc){dprintf(2,"FX3_MEDIA_BIND_REJECT module=A reason=native_send_install result=%d\n",rc);goto out;}app_base=a->base;sample("app_bound");U t;if(!param_started&&pthread_create(&t,0,sampler,0)==0){pthread_detach(t);param_started=1;}dprintf(2,"FX3_MEDIA_BOUND module=A base=%#lx parameters=10 original_getter_code_guard=1 original_getters_called=0 sampler_started=%d\n",app_base,param_started);goto out;}
 if((kind==1&&bound_D)||(kind==2&&bound_M))goto out;
 if(!selftest_done){rc=install(&test_pool,(U)fx3_media_test_point,*(W*)fx3_media_test_point,63,31);if(!rc)rc=install(&test_pool,(U)fx3_media_test_cb,*(W*)fx3_media_test_cb,63,31);if(!rc)rc=install(&test_pool,(U)fx3_media_test_bl,*(W*)fx3_media_test_bl,63,31);if(!rc)rc=fx3_media_test();if(!rc&&(fx3_media_branch_test(0)!=11||fx3_media_branch_test(1)!=22||fx3_media_bl_test(9)!=16))rc=250;if(rc){dprintf(2,"FX3_MEDIA_BIND_REJECT reason=selftest result=%d\n",rc);goto out;}selftest_done=1;dprintf(2,"FX3_MEDIA_SELFTEST_PASS GPR=31 SIMD=32 NZCV=preserved FPCR=preserved FPSR=preserved SP=preserved CBZ_BL_original_LR=1\n");}
 struct point *points=kind==1?points_D:points_M;U count=kind==1?sizeof(points_D)/sizeof(points_D[0]):sizeof(points_M)/sizeof(points_M[0]);struct pool*pool=kind==1?&pool_D:&pool_M;
 for(U i=0;i<count;i++){W w;if(!peek(a->base+points[i].off,&w,4)||w!=points[i].word){dprintf(2,"FX3_MEDIA_BIND_REJECT module=%c reason=original_word point=%#lx\n",kind==1?'D':'M',points[i].off);goto out;}}
 for(U i=0;i<count;i++){rc=install(pool,a->base+points[i].off,points[i].word,points[i].off+(kind==2?0x100000:0),31);if(rc){dprintf(2,"FX3_MEDIA_BIND_REJECT module=%c reason=install point=%#lx result=%d\n",kind==1?'D':'M',points[i].off,rc);goto out;}}
 if(kind==1){dbase=a->base;bound_D=1;}else{mbase=a->base;bound_M=1;}
 dprintf(2,"FX3_MEDIA_BOUND module=%c base=%#lx points=%lu full_original_register_preservation=1 native_calls_unchanged=1\n",kind==1?'D':'M',a->base,count);
 out:__atomic_clear(&binding,__ATOMIC_RELEASE);
}
void fx3_media_wire_observe(W dst,const void *p,W n,W src,void *caller,void *fp){int saved=*__errno_location();if(!active||inside||!p){*__errno_location()=saved;return;}W tag=0;peek((U)p,&tag,4);if(!((dst==0x5503e0&&n==28&&(tag==0x10002||tag==0x10003))||dst==0x80d9016e||dst==0x80cf016d)){*__errno_location()=saved;return;}inside=1;eid=__atomic_add_fetch(&sequence,1,__ATOMIC_RELAXED);dprintf(2,"FX3_MEDIA_WIRE eid=%lu tid=%ld ns=%lu destination=%#x source=%#x tag=%#x bytes=%u original_send_follows=1 synthetic=0\n",eid,syscall(178),stamp(),dst,src,tag,n);raw("ORIGINAL_OSAL_SEND_FULL",(U)p,n);stack((U)caller,(U)fp);sample("original_OSAL_send");inside=0;*__errno_location()=saved;}
void *dlopen(const char *name,int flags){int saved=*__errno_location();void *(*fn)(const char *,int)=dlsym((void *)-1,"dlopen");if(!fn)__builtin_trap();*__errno_location()=saved;void *h=fn(name,flags);saved=*__errno_location();if(h&&name)bind(h,name);*__errno_location()=saved;return h;}
__attribute__((constructor)) static void init(void){int saved=*__errno_location();const char*p=getenv("FX3_MEDIA_OBSERVE");if(p&&!strcmp(p,"passive-v1")){pmem=open("/proc/self/mem",0);active=pmem>=0;dprintf(2,"FX3_MEDIA_SCOPE profile=passive-v1 active=%d original_CP=0 state_writes=0 replies_added=0 synthetic_keys=0 original_getter_invocations=0\n",active);}*__errno_location()=saved;}
