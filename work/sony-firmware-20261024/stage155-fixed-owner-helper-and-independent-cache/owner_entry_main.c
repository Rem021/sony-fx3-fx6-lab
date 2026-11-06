/* Fixed-purpose executable. No Python, user script, DSO, shell, Sony protocol,
 * camera file, arbitrary target, reset, retry or firmware-write entry exists. */
#include "entry_shared.h"
#include <CommonCrypto/CommonDigest.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <unistd.h>
#ifndef FX3_APPROVED_JOB_ROOT
#error FX3_APPROVED_JOB_ROOT must be fixed at build time
#endif
#ifdef FX3_ENTRY_FIXTURE
void fx3_owner_fixture_reset(uint32_t,uint32_t,uint32_t);
void fx3_owner_fixture_block(uint32_t,fx3_fixture_gate *);
void fx3_owner_fixture_body_tag(const uint8_t *);
uint32_t fx3_owner_fixture_calls(uint32_t);
#endif

static int hex_nonce(const char *text,uint8_t out[16]) {
    if (strlen(text)!=32) return -1;
    for (unsigned i=0;i<16;++i) {
        char pair[3]={text[i*2],text[i*2+1],0};
        for (unsigned j=0;j<2;++j) if (!((pair[j]>='0' && pair[j]<='9') || (pair[j]>='a' && pair[j]<='f'))) return -1;
        out[i]=(uint8_t)strtoul(pair,NULL,16);
    }
    return 0;
}
static int nonzero(const uint8_t *p,size_t n) { uint8_t sum=0;for(size_t i=0;i<n;++i)sum|=p[i];return sum!=0; }
static int denied(const char *reason,int code) { fprintf(stderr,"FX3_OWNER_ENTRY_DENIED:%s\n",reason);return code; }

int main(int argc,char **argv) {
    if (argc!=3) return denied("fixed_job_and_nonce_required",64);
    uint8_t nonce[16];if (hex_nonce(argv[2],nonce)) return denied("nonce_shape",64);
    struct stat original_path;
    if (lstat(argv[1],&original_path) || S_ISLNK(original_path.st_mode)) return denied("job_missing_or_symlink",65);
    char path[4096];if (!realpath(argv[1],path)) return denied("job_missing",65);
    const char prefix[]=FX3_APPROVED_JOB_ROOT;
    if (strncmp(path,prefix,sizeof(prefix)-1)) return denied("job_outside_reviewed_root",65);
#ifndef FX3_ENTRY_FIXTURE
    if (geteuid()!=0) return denied("administrator_required",77);
#endif
    int fd=open(path,O_RDWR|O_NOFOLLOW);
    if (fd<0) return denied("job_open",65);
    struct stat st;
    if (fstat(fd,&st) || !S_ISREG(st.st_mode) || (st.st_mode&0777)!=0600 || st.st_nlink!=1 || st.st_size!=FX3_ENTRY_BLOCK_BYTES) {
        close(fd);return denied("job_file_identity",65);
    }
    void *memory=mmap(NULL,FX3_ENTRY_BLOCK_BYTES,PROT_READ|PROT_WRITE,MAP_SHARED,fd,0);close(fd);
    if (memory==MAP_FAILED) return denied("mapping",65);
    fx3_entry_frame *f=memory;fx3_entry_grant *g=&f->grant;
#ifdef FX3_ENTRY_FIXTURE
    if (g->mode!=1 || g->owner_uid!=getuid()) return denied("fixture_identity",65);
#else
    struct stat console;
    if (stat("/dev/console",&console) || !console.st_uid || g->mode!=0 || g->owner_uid!=console.st_uid ||
        g->fixture_fail || g->fixture_option || g->fixture_block || nonzero(g->fixture_observed_tag,32)) return denied("live_identity",65);
#endif
    if (st.st_uid!=g->owner_uid || f->control.abi!=FX3_OWNER_ABI ||
        !nonzero(g->privacy_key,32) || !nonzero(g->expected_body_tag,32)) return denied("grant_identity_or_tag",65);
    if (fx3_entry_claim(f,nonce)) return denied("consumed_or_wrong_grant",66);
    /* Persist consumption before any device provider can run; never reset it. */
    if (msync(memory,FX3_ENTRY_BLOCK_BYTES,MS_SYNC)) return denied("claim_sync",65);
    if (fx3_ipc_install_handlers(memory)) return denied("signal_setup",65);
    uint32_t uid=0;uint64_t sec=0,usec=0;
    if (fx3_entry_pid_info((uint32_t)getpid(),&uid,&sec,&usec)) return denied("self_process_identity",65);
    g->native_pid=(uint32_t)getpid();g->birth_sec=sec;g->birth_usec=usec;
    g->started_ns=fx3_entry_clock_ns();
#ifdef FX3_ENTRY_FIXTURE
    g->work_deadline_ns=g->started_ns+500000000ull;g->final_deadline_ns=g->started_ns+1500000000ull;
    fx3_owner_fixture_reset(g->fixture_fail,g->fixture_option|512u,0);
    fx3_owner_fixture_body_tag(g->fixture_observed_tag);
    if (g->fixture_block) fx3_owner_fixture_block(g->fixture_block,&f->gate);
#else
    g->work_deadline_ns=g->started_ns+20000000000ull;g->final_deadline_ns=g->started_ns+30000000000ull;
#endif
    fx3_owner_config config={.abi=FX3_OWNER_ABI,.arm=FX3_OWNER_ARM,.location=0x02100000,.capture_permitted=1,.vid=0x054c,.pid=0x0da1,
        .work_deadline_ns=g->work_deadline_ns,.final_deadline_ns=g->final_deadline_ns};
    memcpy(config.privacy_key,g->privacy_key,32);memcpy(config.expected_body_tag,g->expected_body_tag,32);
    atomic_store_explicit(&g->native_started,1,memory_order_release);
    g->native_return=fx3_owner_run(&config,&f->result,&f->control);
    CC_SHA256(&f->result,sizeof(f->result),g->result_sha256);
    atomic_store_explicit(&g->native_completed,1,memory_order_release);
    if (msync(memory,FX3_ENTRY_BLOCK_BYTES,MS_SYNC)) return denied("result_sync",65);
    printf("{\"schema\":1,\"mode\":\"%s\",\"nonce\":\"%s\",\"pid\":%u,\"native_return\":%d,\"result_sha256\":\"",
#ifdef FX3_ENTRY_FIXTURE
        "fixture",
#else
        "live",
#endif
        argv[2],g->native_pid,g->native_return);
    for (unsigned i=0;i<32;++i) printf("%02x",g->result_sha256[i]);
    printf("\",\"physical_camera_acceptance\":false");
#ifdef FX3_ENTRY_FIXTURE
    printf(",\"fixture_calls\":[");for(unsigned i=1;i<=12;++i)printf("%s%u",i==1?"":",",fx3_owner_fixture_calls(i));printf("]");
#endif
    printf("}\n");fflush(stdout);
    /* Mapping and signal destination remain valid until the process exits. */
    _exit(0);
}
