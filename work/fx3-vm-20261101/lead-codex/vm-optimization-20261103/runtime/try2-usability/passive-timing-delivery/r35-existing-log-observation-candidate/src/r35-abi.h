#ifndef R35_ABI_H
#define R35_ABI_H
/* Own helper ABI; all words unsigned 32-bit. No guest address in identity. */
#define R35_ABI 0x35010058U
#define R35_SOURCE 0x52333501U
#define R35_SUFFIX_BYTES 184U
struct r35_packet { unsigned w[22]; };
typedef int (*r35_snapshot_fn)(unsigned,struct r35_packet *);
#endif
