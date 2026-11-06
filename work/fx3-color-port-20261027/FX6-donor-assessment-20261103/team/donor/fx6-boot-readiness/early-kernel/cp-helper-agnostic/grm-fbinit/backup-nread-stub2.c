/* Key-specific synthetic Backup_nread only. */
extern int dprintf(int, const char *, ...);
static void zero(void *p, int n) { char *q=(char*)p; for (int i=0;i<n;i++) q[i]=0; }
int Backup_nread(unsigned key, void *buf, int size) {
    dprintf(2,"FX6_BACKUP_NREAD_STUB2 key=%#x size=%d\n", key, size);
    if (buf && size > 0) zero(buf, size);
    if (buf && size >= 4) {
        unsigned *p=(unsigned*)buf;
        if (key == 0x2cf1841U) p[0]=0;
        else if (key == 0x2cf1842U) p[0]=1;
    }
    return size;
}
