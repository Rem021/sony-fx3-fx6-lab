/* Synthetic user-space Backup_nread/Backup_write for FX6 appFw bring-up. */
extern int dprintf(int, const char *, ...);
static void zero(void *p, int n) { char *q=(char*)p; for (int i=0;i<n;i++) q[i]=0; }
int Backup_nread(unsigned key, void *buf, int size) {
    dprintf(2,"FX6_BACKUP_NREAD_STUB key=%#x size=%d\n", key, size);
    if (buf && size > 0) zero(buf, size);
    return size;
}
int Backup_write(unsigned key, const void *buf, int size) {
    dprintf(2,"FX6_BACKUP_WRITE_STUB key=%#x size=%d\n", key, size);
    (void)buf;
    return size;
}
