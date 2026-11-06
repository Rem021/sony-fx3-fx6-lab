/* Host-arm64 execution of the actual r15 C translation unit; guest ASM stubbed. */
#define syscall guest_test_syscall
#define clock_gettime guest_test_clock
#include "fx3-ui-gate-v15.c"
static U tid_calls;
long guest_test_syscall(long n,...){if(n==178)tid_calls++;return n==172?321:42;}
int guest_test_clock(int id,struct ts *t){t->s=100;t->n=id==1?7:9;return 0;}
static __thread int fake_errno;
int *__errno_location(void){return &fake_errno;}
static unsigned char area[0x10000];static U object[0xa20/8+1],object_next[0xa20/8+1];
extern int pthread_create(U *,const void *,void *(*)(void *),void *);extern int pthread_join(U,void **);
#define CHECK(x) do{if(!(x)){dprintf(2,"FAIL line %d\n",__LINE__);__builtin_trap();}}while(0)
static void event(U id){struct ctx c={0,0,id,31};U regs[32]={0};regs[3]=7;fake_errno=123;fx3_gate_event(&c,regs);CHECK(fake_errno==123);}
static void root_event(void){struct ctx c={0,0,0,0};U regs[32]={0};regs[0]=(U)object_next;fake_errno=123;fx3_gate_event(&c,regs);CHECK(fake_errno==123);}
static void *producer(void *v){(void)v;for(int i=0;i<1000;i++)event(9);return 0;}
static void put64(volatile W *p,U i,U v){p[i]=(W)v;p[i+1]=(W)(v>>32);}
int main(int argc,char **argv){(void)argv;ram=(volatile U *)area;ram[0]=0x3145544147335846UL;ram[1]=2;ram[4]=(U)syscall(172);save(&st.bound,1);save(&root_object,(U)object);save(&st.object_mismatch,7);save(&st.root_change,9);snapshot_ready();
 volatile W *q=(volatile W *)(area+SNAP_REQ_OFFSET),*a=(volatile W *)(area+SNAP_ACK_OFFSET),*out=(volatile W *)(area+SNAP_PAYLOAD_OFFSET);
 CHECK(a[0]==SNAP_READY_MAGIC&&a[1]==SNAP_VERSION&&a[6]==SNAP_PAYLOAD_BYTES&&a[19]==0);
 save(&st.count[9],50);U before_tid=tid_calls;event(9);CHECK(tid_calls==before_tid); /* no-request hot path */
 q[0]=SNAP_REQ_MAGIC;q[1]=SNAP_VERSION;q[2]=SNAP_PAYLOAD_BYTES;q[3]=(W)syscall(172);put64(q,4,0xabc123UL);put64(q,6,0xdecafbadUL);put64(q,8,(U)object);q[10]=SNAP_PAYLOAD_OFFSET;q[11]=SNAP_PAYLOAD_BYTES;q[12]=q[13]=q[14]=0;
 /* Missing commit, wrong version/pid/root/length/nonce each leave the slot absent. */
 event(9);CHECK(a[19]==0&&out[0]==0);
 q[15]=SNAP_REQ_COMMIT;q[1]=4;event(9);CHECK(a[19]==0);q[1]=SNAP_VERSION;
 q[3]++;event(9);CHECK(a[19]==0);q[3]--;
 put64(q,8,(U)object+8);event(9);CHECK(a[19]==0);put64(q,8,(U)object);
 q[11]=0x300;event(9);CHECK(a[19]==0);q[11]=SNAP_PAYLOAD_BYTES;
 put64(q,6,0);event(9);CHECK(a[19]==0);put64(q,6,0xdecafbadUL);
 int multi=argc>1&&argv[1][0]=='m';
 if(multi){U first[4];for(U i=0;i<4;i++)CHECK(!pthread_create(&first[i],0,producer,0));for(U i=0;i<4;i++)CHECK(!pthread_join(first[i],0));}
 else if(argc>1)event(40);else event(9);
 CHECK(a[0]==SNAP_ACK_MAGIC&&a[19]==SNAP_ACK_COMMIT&&load(&snapshot_done)==1);
 CHECK(a[10]==(argc>1&&!multi?40:9)&&a[16]==SNAP_PAYLOAD_BYTES&&a[18]==1);
 CHECK(out[0x300/4]==7&&out[0x304/4]==0&&out[0x308/4]==9&&out[0x30c/4]==0);
 CHECK(((U)a[6]|((U)a[7]<<32))==0xdecafbadUL);
 W hash=2166136261U;for(U i=0;i<SNAP_PAYLOAD_BYTES;i++){unsigned char b=((volatile unsigned char *)out)[i];hash=(hash^b)*16777619U;}CHECK(a[17]==hash);
 unsigned char frozen[SNAP_PAYLOAD_BYTES];for(U i=0;i<SNAP_PAYLOAD_BYTES;i++)frozen[i]=((volatile unsigned char *)out)[i];
 U threads[4];for(U i=0;i<4;i++)CHECK(!pthread_create(&threads[i],0,producer,0));for(U i=0;i<4;i++)CHECK(!pthread_join(threads[i],0));
 root_event();CHECK(load(&root_object)==(U)object_next&&load(&st.root_change)==10);
 for(U i=0;i<SNAP_PAYLOAD_BYTES;i++)CHECK(frozen[i]==((volatile unsigned char *)out)[i]);CHECK(a[19]==SNAP_ACK_COMMIT);
 dprintf(1,"mode=%d probe=%u payload=%u count9=%lu frozen=1 checksum=%u errno=123\n",FX3_GATE_PUBLISH_INTERVAL,a[10],SNAP_PAYLOAD_BYTES,load(&st.count[9]),hash);return 0;}
/* Guest assembly and loader are checked byte-for-byte separately, not run here. */
void fx3_gate_probe_core(void){}int fx3_gate_test(void){return 0;}int fx3_gate_branch_test(int x){return x?22:11;}int fx3_gate_bl_test(int x){return x+7;}char fx3_gate_test_point[4],fx3_gate_test_cb[4],fx3_gate_test_bl[4];int dlinfo(void *h,int r,void *o){(void)h;(void)r;(void)o;return -1;}
