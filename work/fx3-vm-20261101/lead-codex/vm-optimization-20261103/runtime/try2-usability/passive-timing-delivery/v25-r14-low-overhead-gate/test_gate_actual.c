/* Native-arm64 offline test of the actual candidate translation unit. */
#include "fx3-ui-gate-v14.c"
static __thread int test_errno;
int *__errno_location(void){return &test_errno;}
static unsigned char fake_observer[0x10000];
static U object_a[0xA20/8+1],object_b[0xA20/8+1];
extern int pthread_create(U *,const void *,void *(*)(void *),void *);
extern int pthread_join(U,void **);
#define check(ok) do{if(!(ok)){dprintf(2,"offline check failed at line %d\n",__LINE__);__builtin_trap();}}while(0)
static void event(U id,U x0,U x1,U x3){struct ctx c={0,0,id,31};U r[32]={0};r[0]=x0;r[1]=x1;r[3]=x3;test_errno=123;fx3_gate_event(&c,r);check(test_errno==123);}
static void event_object(U id,U *object){struct ctx c={0,0,id,0};U r[32]={0};r[0]=(U)object;test_errno=123;fx3_gate_event(&c,r);check(test_errno==123);}
static void *producer(void *arg){U base=(U)arg;for(U i=0;i<1000;i++)event(9,0,0,(base+i)%37);return 0;}
int main(void){ram=(volatile U *)fake_observer;ram[0]=0x3145544147335846UL;save(&mirror_visit,FX3_GATE_PUBLISH_INTERVAL-1);mirror();check(mirror_serial==1);
 /* The first genuine event is intentionally not mirrored by N64. */
 event(5,0,0,0);check(load(&st.count[5])==1&&load(&st.gate_hist[0])==1&&decision_a18==0);
 event(5,2,0,0);event(5,3,0,0);event(5,(U)(W)-1,0,0);
 check(load(&st.count[5])==4&&load(&st.gate_hist[0])==1&&load(&st.gate_hist[2])==1&&load(&st.gate_hist[3])==1&&load(&st.gate_hist[5])==1);
 event(6,0,0,0);event(7,4,3,0);event(7,2,3,0);event(9,0,0,9);event(10,5,0,0);
 check(load(&st.backlog_skip)==1&&load(&st.time_pass)==1&&load(&st.time_skip)==1);
 check(load(&st.count[9])==1&&load(&st.count[10])==1&&load(&st.peak_all)==0xffffffffUL);
 if(FX3_GATE_PUBLISH_INTERVAL==64){check(mirror_serial==1);check(ram[0x100/8+5]==0);}
 else check(mirror_serial==10);
 /* Interleaved producers exercise the same actual add/peak code. */
 for(int i=0;i<1000;i++){event(9,0,0,(U)(i%37));event(10,(U)(i%29),0,0);}
 check(load(&st.count[9])==1001&&load(&st.count[10])==1001&&load(&st.field_samples)==2006);
 check(load(&st.object_mismatch)==0);
 check(mirror_serial>1);U threads[4];for(U i=0;i<4;i++)check(!pthread_create(&threads[i],0,producer,(void *)(i*1000)));for(U i=0;i<4;i++)check(!pthread_join(threads[i],0));check(load(&st.count[9])==5001);
 event_object(0,object_a);event_object(4,object_b);event_object(2,object_b);event_object(4,object_a);
 check(load(&st.object_mismatch)==2&&load(&st.root_change)==1&&load(&root_object)==(U)object_b);
 U published_before=mirror_serial;mirror_lock=1;save(&mirror_visit,load(&mirror_published)+FX3_GATE_PUBLISH_INTERVAL-1);event(9,0,0,99);check(mirror_serial==published_before&&load(&st.count[9])==5002&&load(&st.mirror_skip)>0);mirror_lock=0;
 dprintf(1,"count5=%lu count6=%lu count7=%lu count9=%lu count10=%lu hist0=%lu hist2=%lu hist3=%lu hist5=%lu peak=%lu field=%lu backlog=%lu timepass=%lu timeskip=%lu mismatch=%lu rootchange=%lu publications=%lu skips=%lu\n",load(&st.count[5]),load(&st.count[6]),load(&st.count[7]),load(&st.count[9]),load(&st.count[10]),load(&st.gate_hist[0]),load(&st.gate_hist[2]),load(&st.gate_hist[3]),load(&st.gate_hist[5]),load(&st.peak_all),load(&st.field_samples),load(&st.backlog_skip),load(&st.time_pass),load(&st.time_skip),load(&st.object_mismatch),load(&st.root_change),mirror_serial,load(&st.mirror_skip));return 0;}
/* Symbols normally supplied by the unchanged guest assembly or guest loader. */
void fx3_gate_probe_core(void){}
int fx3_gate_test(void){return 0;}
int fx3_gate_branch_test(int x){return x?22:11;}
int fx3_gate_bl_test(int x){return x+7;}
char fx3_gate_test_point[4],fx3_gate_test_cb[4],fx3_gate_test_bl[4];
int dlinfo(void *h,int request,void *out){(void)h;(void)request;(void)out;return -1;}
