typedef unsigned long U;typedef unsigned int W;typedef unsigned long size_t;
extern void *dlsym(void *,const char *);extern int dlinfo(void *,int,void *);extern int dprintf(int,const char *,...);extern int *__errno_location(void);extern int open(const char *,int,...);extern long read(int,void *,size_t);extern int close(int);extern long syscall(long,...);extern void *mmap(void *,size_t,int,int,int,long);extern int munmap(void *,size_t);extern int mprotect(void *,size_t,int);extern void *memcpy(void *,const void *,size_t);extern void *memset(void *,int,size_t);extern char *strstr(const char *,const char *);
struct ts{long s,n;};extern int clock_gettime(int,struct ts *);
struct lm{U base;char *name;void *dynamic;struct lm *next,*prev;};
struct ctx{U pc,continuation,id,objreg;};
struct statistics{U count[48],peak_all,peak_gate,field_samples,hist[6],gate_hist[6],system_false,backlog_skip,time_skip,time_pass,dequeue_total,timer_dequeue,a12_nonzero,a13_nonzero,last_object,last_a18,last_a12,last_a13,first_ns,last_ns,mirror_skip,selftest,bound;};
static struct statistics st;static volatile U *ram;static unsigned char mirror_lock;static U mirror_serial,app_base,root_object;static W (*message_source)(void *);static __thread W decision_a18;
extern void fx3_gate_probe_core(void);extern int fx3_gate_test(void);extern int fx3_gate_branch_test(int);extern int fx3_gate_bl_test(int);extern char fx3_gate_test_point[],fx3_gate_test_cb[],fx3_gate_test_bl[];
static U add(U *p,U n){return __atomic_add_fetch(p,n,__ATOMIC_RELAXED);}static U load(U *p){return __atomic_load_n(p,__ATOMIC_RELAXED);}static void save(U *p,U n){__atomic_store_n(p,n,__ATOMIC_RELAXED);}
static void peak(U *p,U n){U old=load(p);while(old<n&&!__atomic_compare_exchange_n(p,&old,n,0,__ATOMIC_RELAXED,__ATOMIC_RELAXED)){} }
static U now(void){struct ts t={0};return clock_gettime(7,&t)?0:(U)t.s*1000000000UL+t.n;}
static void mirror(void){if(!ram)return;if(__atomic_test_and_set(&mirror_lock,__ATOMIC_ACQUIRE)){add(&st.mirror_skip,1);return;}U bank=ram[2]^1;volatile U *out=ram+0x100/8+bank*(0x1000/8);U *in=(U *)&st;for(U i=0;i<sizeof st/8;i++)out[i]=load(in+i);__asm__ volatile("dmb sy":::"memory");ram[2]=bank;ram[3]=++mirror_serial;__asm__ volatile("dmb sy":::"memory");__atomic_clear(&mirror_lock,__ATOMIC_RELEASE);}
static unsigned int bucket(U n){return n<=2?(unsigned int)n:n<=10?3:n<=100?4:5;}

static U known_sequence,boot_reserve;static __thread U create_sequence,create_function,completion_sequence,completion_handle;
static void boot_event(struct ctx *c,U *r,U n){
 U id=c->id,tid=syscall(178),token=0;int important=1;
 if(id==12){create_sequence=r[0];create_function=r[2];U fn=r[2]-app_base;important=fn==0x2b61efc||fn==0x2b5fae4||fn==0x2b61a90||fn==0x2b60208;if(important)save(&known_sequence,r[0]);}
 if(id==21){completion_sequence=r[0];completion_handle=(W)r[1];important=r[0]==load(&known_sequence);}
 if(id==22)important=r[0]==load(&known_sequence);if(id==30)important=completion_sequence==load(&known_sequence);
 if(id==23||id==24)token=*(W *)(r[29]+0x7c);if(id==20&&r[1])token=*(U *)r[1];
 if(important&&ram){U index=__atomic_fetch_add(&boot_reserve,1,__ATOMIC_RELAXED);if(index<64){U record[24]={id,n,tid,c->pc-app_base,r[0],r[1],r[2],r[3],r[4],r[19],r[20],r[21],r[22],r[25],r[26],r[27],r[28],r[29],token,create_sequence,create_function,completion_sequence,completion_handle,0x544f4f4245544147UL};volatile U *out=ram+0x4000/8+index*24;for(int i=0;i<23;i++)out[i]=record[i];__asm__ volatile("dmb sy":::"memory");out[23]=record[23];ram[5]=index+1;}else ram[6]=index-63;}
 if(important&&(n<=50||n%1000==0||id==12||id==21||id==30))dprintf(2,"FX3_BOOT_GATE_SAMPLE id=%lu n=%lu tid=%lu pc=%#lx x0=%#lx x1=%#lx x2=%#lx x3=%#lx x4=%#lx x19=%#lx remaining=%lu expected=%#lx/%#lx/%#lx/%#lx token_or_req=%#lx create_sequence=%#lx create_function=%#lx completion_sequence=%#lx completion_handle=%#lx\n",id,n,tid,c->pc-app_base,r[0],r[1],r[2],r[3],r[4],r[19],r[22],r[25],r[26],r[27],r[28],token,create_sequence,create_function,completion_sequence,completion_handle);
 mirror();
}
__attribute__((visibility("hidden"))) int fx3_gate_test_compare(U *p){for(int i=0;i<31;i++)if(p[i]!=(U)(0x100+i))return i+1;unsigned char *q=(void *)(p+32);for(int i=0;i<32;i++)for(int j=0;j<16;j++)if(q[i*16+j]!=i+1)return 100+i;if(p[96]!=0xa0000000)return 200;if(p[97]||p[98])return 202;if(p[124]!=(U)p)return 201;return 0;}
__attribute__((visibility("hidden"))) void fx3_gate_event(struct ctx *c,U *r){
 int saved=*__errno_location();U id=c->id;
 if(id==47){
  __asm__ volatile("mov x18,xzr; msr nzcv,xzr; movi v0.16b,#0; movi v1.16b,#0; movi v2.16b,#0; movi v3.16b,#0; movi v4.16b,#0; movi v5.16b,#0; movi v6.16b,#0; movi v7.16b,#0; movi v8.16b,#0; movi v9.16b,#0; movi v10.16b,#0; movi v11.16b,#0; movi v12.16b,#0; movi v13.16b,#0; movi v14.16b,#0; movi v15.16b,#0; movi v16.16b,#0; movi v17.16b,#0; movi v18.16b,#0; movi v19.16b,#0; movi v20.16b,#0; movi v21.16b,#0; movi v22.16b,#0; movi v23.16b,#0; movi v24.16b,#0; movi v25.16b,#0; movi v26.16b,#0; movi v27.16b,#0; movi v28.16b,#0; movi v29.16b,#0; movi v30.16b,#0; movi v31.16b,#0":::"x18","v0","v1","v2","v3","v4","v5","v6","v7","v8","v9","v10","v11","v12","v13","v14","v15","v16","v17","v18","v19","v20","v21","v22","v23","v24","v25","v26","v27","v28","v29","v30","v31","cc","memory");*__errno_location()=saved;return;
 }
 if(id>=40){*__errno_location()=saved;return;}if(id>=12){U n=add(&st.count[id],1);boot_event(c,r,n);*__errno_location()=saved;return;}U n=add(&st.count[id],1),obj=c->objreg<31?r[c->objreg]:load(&root_object),a18=0,a12=0,a13=0,elapsed=0,msg=0,type=0,src=0;
 if((id==0||id==2)&&obj)save(&root_object,obj);
 if(obj){a18=__atomic_load_n((W *)(obj+0xa18),__ATOMIC_RELAXED);a12=__atomic_load_n((unsigned char *)(obj+0xa12),__ATOMIC_RELAXED);a13=__atomic_load_n((unsigned char *)(obj+0xa13),__ATOMIC_RELAXED);save(&st.last_object,obj);save(&st.last_a18,a18);save(&st.last_a12,a12);save(&st.last_a13,a13);if(a12)add(&st.a12_nonzero,1);if(a13)add(&st.a13_nonzero,1);}
 if(id==4&&!(r[0]&255))add(&st.system_false,1);
 if(id==5){decision_a18=(W)r[0];a18=decision_a18;peak(&st.peak_gate,a18);add(&st.gate_hist[bucket(a18)],1);}
 if(id==6&&!((W)r[0]))add(&st.backlog_skip,1);
 if(id==7){elapsed=r[0];if(elapsed<=r[1])add(&st.time_skip,1);else add(&st.time_pass,1);}
 if(id==9)a18=(W)r[3];if(id==10)a18=(W)r[0];
 if(id==5||id==9||id==10){peak(&st.peak_all,a18);add(&st.field_samples,1);add(&st.hist[bucket(a18)],1);}
 if(id==11){add(&st.dequeue_total,1);msg=*(U *)r[20];if(msg){type=*(W *)msg;if(message_source)src=message_source((void *)msg);if(type==0x150000&&src==0x830128)add(&st.timer_dequeue,1);}}
 if(n<=50||n%1000==0){save(&st.last_ns,now());dprintf(2,"FX3_UI_GATE_SAMPLE id=%lu n=%lu tid=%ld pc=%#lx object=%#lx a18=%lu a12=%lu a13=%lu r0=%#lx decision_a18=%u elapsed=%lu old_time=%lu new_time=%lu message=%#lx type=%#lx source=%#lx observed_only=1\n",id,n,syscall(178),c->pc-app_base,obj,a18,a12,a13,r[0],decision_a18,elapsed,id==7?r[22]-r[0]:0,id==7?r[22]:0,msg,type,src);}
 mirror();*__errno_location()=saved;
}
static void sync_code(unsigned char *p,U n){U ctr;__asm__ volatile("mrs %0,ctr_el0":"=r"(ctr));U dc=4UL<<((ctr>>16)&15),ic=4UL<<(ctr&15);for(U a=(U)p&~(dc-1);a<(U)p+n;a+=dc)__asm__ volatile("dc cvau,%0"::"r"(a):"memory");__asm__ volatile("dsb ish":::"memory");for(U a=(U)p&~(ic-1);a<(U)p+n;a+=ic)__asm__ volatile("ic ivau,%0"::"r"(a):"memory");__asm__ volatile("dsb ish;isb":::"memory");}
struct pool{unsigned char *p;U used;};static struct pool test_pool,app_pool;
static W branch(U at,U to){return 0x14000000U|((W)((long)(to-at)/4)&0x3ffffff);}
static W literal(unsigned int reg,unsigned int from,unsigned int to){return 0x58000000U|(((to-from)/4)<<5)|reg;}
static int allocate_pool(struct pool *pool,U pc){if(pool->p)return 0;for(U i=1;i<1792;i++)for(int sign=-1;sign<=1;sign+=2){U hint=(pc&~4095UL)+sign*(i*0x10000);void *p=mmap((void *)hint,4096,3,0x22,-1,0);if(p==(void *)-1)continue;long d=(long)((U)p-pc);if(d>-(1L<<26)+4096&&d<(1L<<26)-4096){pool->p=p;return 0;}munmap(p,4096);}return -1;}
static int install(struct pool *pool,U pc,W expected,U id,U objreg){
 W original=*(W *)pc;if(original!=expected)return -2;if(allocate_pool(pool,pc)||pool->used+128>4096)return -3;unsigned char *p=pool->p+pool->used;long delta=(long)((U)p-pc);if(delta<=-(1L<<27)||delta>=(1L<<27))return -8;pool->used+=128;if(mprotect(pool->p,4096,7))return -4;memset(p,0,128);W *code=(void *)p;code[0]=0xa9bf47f0;code[1]=literal(16,4,32);code[2]=literal(17,8,40);code[3]=0xd61f0220;code[4]=0xa8c147f0;
 code[5]=original;code[6]=branch((U)p+24,pc+4);code[7]=0xd503201f;U context=(U)p+48,core=(U)fx3_gate_probe_core;memcpy(p+32,&context,8);memcpy(p+40,&core,8);struct ctx c={pc,(U)p+16,id,objreg};memcpy(p+48,&c,sizeof c);
 if((original&0x7e000000U)==0x34000000U){long imm=(original>>5)&0x7ffff;if(imm&(1<<18))imm-=1<<19;U target=pc+imm*4;code[5]=(original&0xff00001fU)|(2<<5);code[6]=branch((U)p+24,pc+4);code[7]=branch((U)p+28,target);}
 else if((original&0xfc000000U)==0x94000000U){long imm=original&0x3ffffff;if(imm&(1<<25))imm-=1<<26;U target=pc+imm*4,link=pc+4;code[5]=literal(30,20,80);code[6]=branch((U)p+24,target);memcpy(p+80,&link,8);}
 sync_code(p,128);if(mprotect(pool->p,4096,5))return -5;if(mprotect((void *)(pc&~4095UL),4096,7))return -6;*(W *)pc=branch(pc,(U)p);sync_code((void *)pc,4);if(mprotect((void *)(pc&~4095UL),4096,5))return -7;return 0;
}
static int bind_ram(void){int fd=open("/tmp/fx3-ui-gate.claim",0x200c1,0600);if(fd<0)return -1;dprintf(fd,"pid=%ld physical=41dc00000 bytes=10000 observer=1\n",syscall(172));close(fd);char cmd[4096]={0};fd=open("/proc/cmdline",0);long n=fd<0?-1:read(fd,cmd,4095);if(fd>=0)close(fd);if(n<=0||!strstr(cmd,"memrsv=0x00010000@0x41dc00000:uc"))return -2;fd=open("/dev/mem",2);void *p=fd<0?(void *)-1:mmap(0,0x10000,3,1,fd,0x41dc00000UL);if(fd>=0)close(fd);if(p==(void *)-1)return -3;memset(p,0,0x10000);ram=p;ram[0]=0x3145544147335846UL;ram[1]=2;ram[4]=syscall(172);return 0;}
static void bind(void *h){if(load(&st.bound))return;struct lm *a=0;if(dlinfo(h,2,&a)||!a)return;app_base=a->base;
 const U offsets[31]={0x16f2220,0x16f25e8,0x16f16bc,0x16f18b8,0x16f22cc,0x16f247c,0x16f2488,0x16f2600,0x16f2640,0x16f1a74,0x16f1d68,0x16f217c,0x2b63224,0x2b63900,0x2b66de4,0x2b66e04,0x2b67674,0x2b67678,0x2b60208,0x2dd0cb4,0x2dec7e4,0x2b634dc,0x2b6353c,0x2b63628,0x2b63678,0x2b63624,0x2b61efc,0x2b62438,0x2b61a90,0x2b5fae4,0x2b63538};
 const W words[31]={0xd10cc3ff,0xd65f03c0,0xa9b87bfd,0xd65f03c0,0x72001c1f,0x7100081f,0x35000b20,0xeb01001f,0x97fffcd6,0xb90a1a63,0xb90a1ac0,0xaa1703e2,0xa9bc7bfd,0x91051ab6,0xb9006fa0,0xb9006ba0,0x97ffeeec,0xb90067a0,0xd10803ff,0xaa1403e1,0x97ffea31,0xa9bc7bfd,0xa9b77bfd,0x6b19001f,0x35fff876,0xd65f03c0,0xd11a43ff,0xd65f03c0,0xd101c3ff,0xa9bc7bfd,0xd65f03c0};const U regs[31]={0,31,0,31,20,20,20,20,0,19,22,25,31,31,31,31,31,31,31,31,31,31,31,31,31,31,31,31,31,31,31};
 for(int i=0;i<31;i++)if(*(W *)(app_base+offsets[i])!=words[i]){dprintf(2,"FX3_UI_GATE_BIND_FAIL id=%d reason=original_instruction\n",i);return;}
 if(bind_ram()){dprintf(2,"FX3_UI_GATE_BIND_FAIL reason=reserved_observer_ram\n");return;}
 int rc=install(&test_pool,(U)fx3_gate_test_point,*(W *)fx3_gate_test_point,47,31);if(!rc)rc=install(&test_pool,(U)fx3_gate_test_cb,*(W *)fx3_gate_test_cb,47,31);if(!rc)rc=install(&test_pool,(U)fx3_gate_test_bl,*(W *)fx3_gate_test_bl,47,31);if(!rc)rc=fx3_gate_test();if(!rc&&(fx3_gate_branch_test(0)!=11||fx3_gate_branch_test(1)!=22||fx3_gate_bl_test(9)!=16))rc=250;
 if(rc){dprintf(2,"FX3_UI_GATE_SELFTEST_FAIL result=%d originals_not_bound=1\n",rc);return;}st.selftest=1;dprintf(2,"FX3_UI_GATE_SELFTEST_PASS GPR=31 SIMD=32 NZCV=preserved FPCR_FPSR=preserved SP=preserved NOP_CBNZ_BL=passed\n");
 for(int i=0;i<31;i++){rc=install(&app_pool,app_base+offsets[i],words[i],i,regs[i]);if(rc){dprintf(2,"FX3_UI_GATE_BIND_FAIL id=%d result=%d\n",i,rc);return;}}
 message_source=dlsym((void *)-1,"osal_get_msg_src");st.first_ns=st.last_ns=now();st.bound=1;mirror();dprintf(2,"FX3_UI_GATE_BOUND count=31 single_instruction_near_islands=1 full_register_state_preserved=1 observer_physical=41dc00000\n");
}
void *dlopen(const char *name,int flags){int saved=*__errno_location();void *(*fn)(const char *,int)=dlsym((void *)-1,"dlopen");if(!fn)__builtin_trap();*__errno_location()=saved;void *h=fn(name,flags);saved=*__errno_location();if(h&&name&&strstr(name,"appFw.so"))bind(h);*__errno_location()=saved;return h;}
