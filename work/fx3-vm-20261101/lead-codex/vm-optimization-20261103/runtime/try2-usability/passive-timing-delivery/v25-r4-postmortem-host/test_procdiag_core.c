#define main procdiag_guest_main
#include "fx3-procdiag-v1.c"
#undef main
#include <assert.h>
#include <signal.h>
#include <sys/stat.h>

static void write_file(const char *path,const char *value){
    int f=open(path,O_WRONLY|O_CREAT|O_TRUNC,0600);assert(f>=0);
    size_t n=strlen(value);assert(write(f,value,n)==(ssize_t)n);close(f);
}
int main(void){
    char dir[]="/tmp/fx3-procdiag-test-XXXXXX";assert(mkdtemp(dir));
    char path[256];snprintf(path,sizeof path,"%s/identity",dir);
    long tid=0;
    write_file(path,"F100FILE_READY_V2 148\n");
    assert(parse_identity(path,"file100",mono_ns()+1000000000ULL,0)==148);
    write_file(path,"F100FILE_READY_V2 148 trailing\n");
    assert(parse_identity(path,"file100",mono_ns()+1000000000ULL,0)==-1);
    write_file(path,"343 344\n");
    assert(parse_identity(path,"key96",mono_ns()+1000000000ULL,&tid)==343&&tid==344);
    write_file(path,"343\n");
    assert(parse_identity(path,"key96",mono_ns()+1000000000ULL,&tid)==-1);
    write_file(path,"abc");
    char out[256];
    assert(bounded_read(path,out,sizeof out,mono_ns()+1000000000ULL,"test","regular")==3);
    snprintf(path,sizeof path,"%s/fifo",dir);assert(mkfifo(path,0600)==0);
    uint64_t begin=mono_ns();
    assert(bounded_read(path,out,sizeof out,mono_ns()+1000000000ULL,"test","fifo")==-1);
    assert(mono_ns()-begin<300000000ULL);
    assert(pending_count>=1);
    for(unsigned i=0;i<pending_count;i++)kill(pending[i].pid,SIGKILL);
    for(unsigned i=0;i<pending_count;i++)waitpid(pending[i].pid,0,0);
    snprintf(path,sizeof path,"%s/identity",dir);unlink(path);
    snprintf(path,sizeof path,"%s/fifo",dir);unlink(path);rmdir(dir);
    puts("procdiag identity, bounded regular/FIFO timeout PASS");
    return 0;
}
