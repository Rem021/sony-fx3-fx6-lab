/* Read-only native guest /setting/Backup.bin -> new observer-only reservation. */
typedef unsigned long U;typedef unsigned int W;typedef unsigned char B;
extern int open(const char*,int,...),close(int),munmap(void*,U),usleep(W),dprintf(int,const char*,...),system(const char*);
extern long read(int,void*,U),lseek(int,long,int);extern void* mmap(void*,U,int,int,int,long),*malloc(U),*memcpy(void*,const void*,U);extern int memcmp(const void*,const void*,U);extern void free(void*);
#define PHYS 0x41d400000UL
#define SPAN 0x300000UL
#define CAP 0x230000UL
static U hash(const B*p,U n){U h=14695981039346656037UL;for(U i=0;i<n;i++){h^=p[i];h*=1099511628211UL;}return h;}
static long load(B*p){int f=open("/setting/Backup.bin",0);if(f<0)return -1;long n=lseek(f,0,2);if(n<=0||n>CAP||lseek(f,0,0)){close(f);return -2;}U at=0;while(at<(U)n){long r=read(f,p+at,n-at);if(r<=0){close(f);return -3;}at+=r;}B extra;long more=read(f,&extra,1);close(f);return more==0?n:-4;}
int main(void){int f=open("/dev/mem",2);if(f<0)return 1;B*out=mmap(0,SPAN,3,1,f,PHYS);close(f);if(out==(void*)-1)return 2;B*a=malloc(CAP),*b=malloc(CAP);if(!a||!b)return 3;U*h=(U*)out;for(U i=0;i<4096;i++)out[i]=0;memcpy(out,"F100FILE",8);U gen=0,last=0;int stopped=0;
 dprintf(1,"FX3_FILE100_OBSERVER_READY physical=%#lx span=%#lx native_path=/setting/Backup.bin O_RDONLY=1 no_native_data_writes=1\n",PHYS,SPAN);
 for(;;){
  if(h[6]==0x100c1ea9UL&&!stopped){stopped=1;int rc=system("/bin/sh /simulation/fx3-sync100-shutdown.sh");h[7]=(U)(long)rc;h[8]=1;dprintf(1,"FX3_FILE100_MODULE_RESTORE_REQUEST result=%d QEMU_shutdown_pending=1 observer_only_control=1\n",rc);}
  long n=load(a),n2=n>0?load(b):-1;
  if(n>0&&n==n2&&!memcmp(a,b,n)){U v=hash(a,n);if(!gen||v!=last){h[1]=2*gen+1;__atomic_thread_fence(__ATOMIC_SEQ_CST);memcpy(out+4096,a,n);h[3]=n;h[4]=v;h[5]=0;gen++;h[2]=gen;__atomic_thread_fence(__ATOMIC_SEQ_CST);h[1]=2*gen;last=v;dprintf(1,"FX3_FILE100_NATIVE_FILE_READ generation=%lu bytes=%ld fnv64=%#lx two_full_reads_equal=1 source_O_RDONLY=1 payload_physical=%#lx unchanged_file_bytes=1\n",gen,n,v,PHYS+4096);}}
  else h[5]=(U)(long)(n<0?n:-5);
  for(unsigned i=0;i<8;i++){usleep(250000);if(h[6]==0x100c1ea9UL&&!stopped)break;}
 }
}
