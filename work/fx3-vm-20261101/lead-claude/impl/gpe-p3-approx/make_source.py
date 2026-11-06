"""Rebuild v14 from frozen v13 plus the local adapter; --check is read-only."""
from pathlib import Path
import sys
D=Path(__file__).resolve().parent
s=(D/'reference-v13/fx3-gpe-observe-v13.c').read_text()
s=s.replace('/* v13:','/* v14:').replace('"fx3-gpe-backend.h"','"fx3-gpe-backend-v2.h"')
s=s.replace('adapter=v13','adapter=v14 approx_model=straight_over_v1')
a=s.index('#define EXT_BASE');b=s.index('static const char *names[]',a)
s=s[:a]+(D/'adapter.inc').read_text()+s[b:]
p=D/'fx3-gpe-observe-v14.c'
if '--check' in sys.argv:
    assert p.read_text()==s,'v14 source differs from frozen-v13 + adapter.inc'
    print('PASS v14 source reconstruction: v13 binding/FIFO/interposers unchanged')
else:
    import plistlib,subprocess
    v=plistlib.loads(subprocess.check_output(['diskutil','info','-plist','/Volumes/KAFU2T']))
    assert v['VolumeUUID']=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
    p.write_text(s)
