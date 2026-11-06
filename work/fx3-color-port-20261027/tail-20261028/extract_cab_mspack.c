/* Task-local CAB extraction only. Does not execute the installer or Sony code.
 * Source input is a bounded, complemented view of the pinned original EXE.
 * libmspack receives normal CAB bytes through its documented I/O interface.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdarg.h>
#include <stdint.h>
#include <unistd.h>
#include <sys/stat.h>
#include "mspack.h"

#define CAB_START ((off_t)0x6ef5a)
#define CAB_SIZE ((off_t)1539537813)
struct handle { FILE *f; int input; off_t count, last; };
static const char *input_name, *output_name;
static int io_error;

static struct mspack_file *op(struct mspack_system *s, const char *name, int mode) {
    (void)s;
    int input = mode == MSPACK_SYS_OPEN_READ && !strcmp(name, input_name);
    if (!input && !(mode == MSPACK_SYS_OPEN_WRITE && !strcmp(name, output_name))) return NULL;
    struct handle *h = calloc(1, sizeof(*h));
    if (!h) return NULL;
    h->input = input;
    h->f = fopen(name, input ? "rb" : "wbx");
    if (!h->f) { free(h); return NULL; }
    if (input) {
        if (fseeko(h->f, CAB_START, SEEK_SET)) { fclose(h->f); free(h); return NULL; }
    } else if (fchmod(fileno(h->f), 0600)) { fclose(h->f); free(h); return NULL; }
    return (struct mspack_file *)h;
}
static void cl(struct mspack_file *file) {
    struct handle *h = (struct handle *)file;
    if (!h->input && (fflush(h->f) || fsync(fileno(h->f)))) io_error = 1;
    if (fclose(h->f)) io_error = 1;
    free(h);
}
static int rd(struct mspack_file *file, void *buf, int bytes) {
    struct handle *h = (struct handle *)file;
    if (!h->input || bytes < 0) return -1;
    off_t pos = ftello(h->f) - CAB_START;
    if (pos < 0 || pos > CAB_SIZE) return -1;
    if ((off_t)bytes > CAB_SIZE - pos) bytes = (int)(CAB_SIZE - pos);
    size_t n = fread(buf, 1, (size_t)bytes, h->f);
    if (ferror(h->f)) return -1;
    unsigned char *b = buf;
    for (size_t i=0; i<n; i++) b[i] ^= 255;
    return (int)n;
}
static int wr(struct mspack_file *file, void *buf, int bytes) {
    struct handle *h = (struct handle *)file;
    if (h->input || bytes < 0) return -1;
    size_t n = fwrite(buf, 1, (size_t)bytes, h->f);
    h->count += n;
    if (h->count - h->last >= 64*1024*1024) {
        printf("OUTPUT_BYTES %lld\n", (long long)h->count); fflush(stdout); h->last = h->count;
    }
    return ferror(h->f) ? -1 : (int)n;
}
static int sk(struct mspack_file *file, off_t off, int mode) {
    struct handle *h = (struct handle *)file;
    if (!h->input) return -1;
    off_t base;
    if (mode == MSPACK_SYS_SEEK_START) base=0;
    else if (mode == MSPACK_SYS_SEEK_CUR) base=ftello(h->f)-CAB_START;
    else if (mode == MSPACK_SYS_SEEK_END) base=CAB_SIZE;
    else return -1;
    if (off < -base || off > CAB_SIZE-base) return -1;
    return fseeko(h->f, CAB_START+base+off, SEEK_SET);
}
static off_t tl(struct mspack_file *file) {
    struct handle *h = (struct handle *)file;
    return ftello(h->f) - (h->input ? CAB_START : 0);
}
static void msg(struct mspack_file *file, const char *fmt, ...) {
    (void)file; va_list ap; va_start(ap,fmt); vfprintf(stderr,fmt,ap); va_end(ap); fputc('\n',stderr);
}
static void *al(struct mspack_system *s, size_t n) { (void)s; return malloc(n); }
static void cp(void *src, void *dst, size_t n) { memcpy(dst,src,n); }
static struct mspack_system sys = {op,cl,rd,wr,sk,tl,msg,al,free,cp,NULL};

int main(int argc, char **argv) {
    if (argc != 4) { fprintf(stderr,"usage: extractor original.exe member output.part\n"); return 2; }
    int test; MSPACK_SYS_SELFTEST(test); if (test) return 3;
    input_name=argv[1]; output_name=argv[3];
    const char *allowed[] = {"FirmwareA1Data_ILMEFX3V204.dat", "FirmwareA2Data_ILMEFX3V205.dat", "FirmwareUpdaterImg.dll"};
    unsigned int lengths[] = {779108760,756424088,111392};
    unsigned int wanted=3;
    for (unsigned int i=0;i<3;i++) if (!strcmp(argv[2],allowed[i])) wanted=i;
    if (wanted==3) return 4;
    struct mscab_decompressor *d=mspack_create_cab_decompressor(&sys);
    if (!d) return 5;
    struct mscabd_cabinet *cab=d->open(d,input_name);
    if (!cab) { fprintf(stderr,"CAB_OPEN_ERROR %d\n",d->last_error(d)); return 6; }
    if (cab->length!=CAB_SIZE || cab->base_offset!=0) return 7;
    int result=8, found=0;
    for (struct mscabd_file *f=cab->files;f;f=f->next) {
        if (strcmp(f->filename,argv[2])) continue;
        if (found++ || f->length!=lengths[wanted]) return 9;
        result=d->extract(d,f,output_name);
        printf("EXTRACT_RESULT %d MEMBER %s EXPECTED_BYTES %u IO_ERROR %d\n",result,argv[2],f->length,io_error);
        fflush(stdout);
    }
    d->close(d,cab); mspack_destroy_cab_decompressor(d);
    return result || io_error || found!=1 ? 10 : 0;
}
