#ifndef FX3_FRAME_IO_H
#define FX3_FRAME_IO_H
#include "entry_shared.h"
#include <sys/stat.h>
typedef struct {int fd;struct stat identity;_Atomic uint32_t failed;} fx3_frame_io;
int fx3_frame_write(fx3_frame_io *,const fx3_entry_frame *);
void fx3_frame_progress(fx3_frame_io *,const fx3_entry_frame *);
void fx3_frame_control(fx3_frame_io *,fx3_entry_frame *);
#endif
