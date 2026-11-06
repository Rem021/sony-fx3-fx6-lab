from pathlib import Path
import json,subprocess,hashlib
R=Path(__file__).resolve().parent;H=R/'helpers';s=(H/'fx3-osd-headless-v3.c').read_text();code=s[s.index('static int mapped_cpu('):s.index('static int capture(')];pre=r'''
#include <assert.h>
#include <string.h>
#include <stdio.h>
#include <stdlib.h>
typedef unsigned long U;
#include "fx3-osd-core-v3.h"
static char fixture[262144];static unsigned position,closed;
static int test_open(const char *p,int flags){assert(!strcmp(p,"/proc/self/maps")&&flags==0);position=0;return 9;}
static long test_read(int fd,void *out,unsigned long n){assert(fd==9);unsigned left=strlen(fixture)-position;if(n>left)n=left;memcpy(out,fixture+position,n);position+=n;return n;}
static int test_close(int fd){assert(fd==9);closed++;return 0;}
#define open test_open
#define read test_read
#define close test_close
''';post=r'''
int main(void){struct ho_frame f={.span=0x96000,.physical=0x43feb5100UL};const void *bits=(void *)0x7efe036100UL;unsigned n=0;for(unsigned j=0;j<2100;j++)n+=sprintf(fixture+n,"00400000-00409000 r-xp 00000000 00:02 261 /usr/bin/im.elf\n");memset(fixture+n,'a',2000);n+=2000;fixture[n++]='\n';strcpy(fixture+n,"7efe036000-7efe0cd000 rw-s 43feb5000 00:06 3073 /dev/mem\n");assert(mapped_cpu(bits,&f)&&f.bits==(U)bits&&f.map_begin==0x7efe036000UL&&f.map_offset==0x43feb5000UL&&closed==1);unsigned hits=0;const char *negative[]={"7efe036000-7efe0cd000 rw-p 43feb5000 00:06 3073 /dev/mem\n","7efe036000-7efe0cd000 -w-s 43feb5000 00:06 3073 /dev/mem\n","7efe036000-7efe0cd000 rw-s 43feb5001 00:06 3073 /dev/mem\n","7efe036000-7efe037000 rw-s 43feb5000 00:06 3073 /dev/mem\n","7efe036000-7efe0cd000 rw-s 43feb5000 00:06 3073 /tmp/file\n"};for(unsigned j=0;j<5;j++){strcpy(fixture,negative[j]);assert(!mapped_cpu(bits,&f));hits++;}printf("CPU_MAPPING_PASS real_parser/large_maps_stream/chunk_and_overlong_lines/exact_shared_devmem_VA_physical_span/negative%u\n",hits);}
''';p=H/'check-osd-cpu-mapping-v3.c';p.write_text(pre+code+post);a=['clang','-O1','-g','-fsanitize=address,undefined','-fno-sanitize-recover=all',str(p),'-o',str(p.with_suffix(''))];q=subprocess.run(a,text=True,capture_output=True);assert not q.returncode,q.stderr;q=subprocess.run([str(p.with_suffix(''))],text=True,capture_output=True);(H/'osd-cpu-mapping-host-check.json').write_text(json.dumps({'args':a,'exit':q.returncode,'stdout':q.stdout,'stderr':q.stderr,'tested_helper_sha256':hashlib.sha256(s.encode()).hexdigest()},indent=2)+'\n');assert not q.returncode,q.stderr;print(q.stdout)
