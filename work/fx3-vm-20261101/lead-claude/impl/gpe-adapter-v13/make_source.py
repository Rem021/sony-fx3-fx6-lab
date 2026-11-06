from pathlib import Path
D=Path(__file__).resolve().parent
R=D.parents[2]/'menu-repair-01/runtime'
# Frozen local copies; originals remain read-only.
for name in ['fx3-gpe-backend.c','fx3-gpe-backend.h']:
 (D/name).write_bytes((D.parent/'gpe-backend'/name).read_bytes())
s=(R/'helpers/fx3-gpe-observe-v12.c').read_text()
s=s.replace('/* FX3 original FIFO retained; symbol-derived binding and bounded request capture.\n * No raster/ACK is fabricated: workers reject pending ownership/layout validation.\n */','/* v13: original v12 binding/FIFO retained; bounded backend adapter. */\n#include "fx3-gpe-backend.h"\n#include <string.h>')
a=s.index('static int capture(');b=s.index('extern long read(',a);s=s[:a]+s[b:]
s=s.replace('#include "fx3-gpe-uniform-v2.c"','')
a=s.index('static int fill(');b=s.index('static const char *names[]',a)
s=s[:a]+(D/'adapter.inc').read_text()+s[b:]
s=s.replace('n<sizeof(data)-1','n<(long)sizeof(data)-1').replace('n>=sizeof(data)-1','n>=(long)sizeof(data)-1')
s=s.replace('completion_added=0','completion_added=1 adapter=v13')
# Host harness compiles real workers and binding code; stub only instruction cache and exported interposers.
a=s.index(' U ctr;__asm__',s.index('static void sync_instructions'));b=s.index('\n}',a)
s=s[:a]+'\n#ifndef FX3_GPE_HOST_TEST\n'+s[a:b]+'\n#else\n (void)p;(void)n;\n#endif'+s[b:]
a=s.index(' U ctr;__asm__',s.index('static int install_setup'));b=s.index(' if(mprotect',a)
s=s[:a]+' sync_instructions(p,16);\n'+s[b:]
s=s.replace('void *dlopen(const char *name,int flags)', '#ifdef FX3_GPE_HOST_TEST\n#define dlopen host_interposer_dlopen\n#endif\nvoid *dlopen(const char *name,int flags)')
s=s.replace(' __asm__("_ZN8BTUtils_6BTBlog10errorPlaceEtj")','\n#ifndef FX3_GPE_HOST_TEST\n __asm__("_ZN8BTUtils_6BTBlog10errorPlaceEtj")\n#endif\n')
(D/'fx3-gpe-observe-v13.c').write_text(s)
