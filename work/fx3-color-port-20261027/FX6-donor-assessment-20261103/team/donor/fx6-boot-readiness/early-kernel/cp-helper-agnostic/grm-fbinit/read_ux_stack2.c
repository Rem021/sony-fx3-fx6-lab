#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <fcntl.h>
#include <dirent.h>
#include <errno.h>
#include <sys/stat.h>
#include <sys/types.h>

static int read_file(const char *p, char *buf, size_t n) {
    int fd = open(p, O_RDONLY);
    if (fd < 0) return -1;
    ssize_t r = read(fd, buf, n - 1);
    close(fd);
    if (r < 0) return -1;
    buf[r] = 0;
    return (int)r;
}

static int parse_syscall(const char *s, unsigned long long *sp, unsigned long long *pc) {
    char *tmp = strdup(s), *tok, *save = NULL;
    unsigned long long vals[16]; int n = 0;
    for (tok = strtok_r(tmp, " \n", &save); tok && n < 16; tok = strtok_r(NULL, " \n", &save))
        vals[n++] = strtoull(tok, NULL, 0);
    free(tmp);
    if (n < 2) return -1;
    *sp = vals[n-2]; *pc = vals[n-1];
    return 0;
}

static int dump_one(const char *pid, const char *tid, const char *name) {
    char path[256], buf[4096], comm[128];
    snprintf(path, sizeof path, "/proc/%s/task/%s/comm", pid, tid);
    if (read_file(path, comm, sizeof comm) < 0) return -1;
    comm[strcspn(comm, "\n")] = 0;
    if (strcmp(comm, "AppFw") && strcmp(comm, "uxengine_res1") && strcmp(comm, "uxengine_res2")) return 0;
    snprintf(path, sizeof path, "/proc/%s/task/%s/syscall", pid, tid);
    if (read_file(path, buf, sizeof buf) < 0) { printf("UXSTACK_SYSCALL_FAIL tid=%s name=%s errno=%d\n", tid, comm, errno); return -1; }
    unsigned long long sp = 0, pc = 0;
    if (parse_syscall(buf, &sp, &pc) < 0) { printf("UXSTACK_PARSE_FAIL tid=%s name=%s line=%s\n", tid, comm, buf); return -1; }
    printf("UXSTACK_BEGIN tid=%s name=%s sp=%016llx pc=%016llx\n", tid, comm, sp, pc);
    unsigned long long start = (sp > 0x100) ? sp - 0x100 : sp;
    unsigned char mem[0x300];
    snprintf(path, sizeof path, "/proc/%s/task/%s/mem", pid, tid);
    int fd = open(path, O_RDONLY);
    if (fd < 0) { printf("UXSTACK_MEM_OPEN_FAIL tid=%s errno=%d\n", tid, errno); return -1; }
    ssize_t r = pread(fd, mem, sizeof mem, (off_t)start); int e = errno; close(fd);
    if (r <= 0) { printf("UXSTACK_MEM_READ_FAIL tid=%s start=%016llx errno=%d\n", tid, start, e); return -1; }
    for (ssize_t i = 0; i < r; i += 16) {
        printf("UXSTACK %016llx:", start + (unsigned long long)i);
        for (ssize_t j = 0; j < 16 && i + j < r; j++) printf(" %02x", mem[i+j]);
        printf("\n");
    }
    printf("UXSTACK_END tid=%s bytes=%zd\n", tid, r);
    return 1;
}

int main(void) {
    if (access("/tmp/uxstack.done", F_OK) == 0) return 0;
    int any = 0;
    DIR *proc = opendir("/proc");
    if (!proc) { printf("UXSTACK_PROCDIR_FAIL errno=%d\n", errno); return 0; }
    struct dirent *pe;
    while ((pe = readdir(proc))) {
        if (pe->d_name[0] < '0' || pe->d_name[0] > '9') continue;
        char tdir[128]; snprintf(tdir, sizeof tdir, "/proc/%s/task", pe->d_name);
        DIR *d = opendir(tdir);
        if (!d) continue;
        struct dirent *de;
        while ((de = readdir(d))) {
            if (de->d_name[0] == '.') continue;
            int r = dump_one(pe->d_name, de->d_name, de->d_name);
            if (r > 0) any = 1;
        }
        closedir(d);
    }
    closedir(proc);
    if (any) { int fd = open("/tmp/uxstack.done", O_WRONLY|O_CREAT|O_TRUNC, 0600); if (fd >= 0) close(fd); }
    return 0;
}
