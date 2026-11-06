#!/usr/bin/env python3
"""Prepare isolated helper sources, never import a runner or repack a CPIO."""
from pathlib import Path
import difflib,json,hashlib,subprocess,plistlib
O=Path(__file__).resolve().parent; D=O.parent
assert plistlib.loads(subprocess.check_output(['diskutil','info','-plist','/Volumes/KAFU2T']))['VolumeUUID']=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
def replace(s,a,b):
 assert s.count(a)==1,(a,s.count(a));return s.replace(a,b)
osd=D/'v25-menu-osd-diagnostic-r3/src/fx3-osd-headless-v25-r3.c'; orig=osd.read_text();s=orig
s=replace(s,'static int observer_bind(void){','/* Independent ordinary-BSS diagnostics; no physical storage. */\n#include "r35-collector.inc"\nstatic int observer_bind(void){')
s=replace(s,'if(observer_ready)return 0;owner=syscall(172);','if(observer_ready)return 0;unsigned r35_bt=r35_bind_begin();owner=syscall(172);')
s=replace(s,'if(f<0)return -1;dprintf(f,"pid=%ld epoch=1','if(f<0){r35_bind_end(r35_bt,-1,0,0);return -1;}dprintf(f,"pid=%ld epoch=1')
s=replace(s,'if(n<=0||!strstr(cmd,"memrsv=0x01000000@0x41e000000:uc"))return -2;','if(n<=0||!strstr(cmd,"memrsv=0x01000000@0x41e000000:uc")){r35_bind_end(r35_bt,-2,0,0);return -2;}')
s=replace(s,'if(pmem<0)return -3;','if(pmem<0){r35_bind_end(r35_bt,-3,0,0);return -3;}')
s=replace(s,'if(p==(void *)-1)return -4;ring=p;','if(p==(void *)-1){r35_bind_end(r35_bt,-4,f<0?1:2,0);return -4;}ring=p;')
s=replace(s,'diag[5]=0;observer_ready=1;','diag[5]=0;r35_bind_end(r35_bt,0,3,(volatile U *)w);observer_ready=1;')
s=replace(s,'*__errno_location()=saved;int rc=hsend(dst,p);int after=*__errno_location();if(diag_enter)', 'unsigned r35_pt=watch&&dst==HO_CONTROL&&qo_publication(dst,src,copy,n)==0x1002?r35_pub_begin(ho_u32(copy+8)):0;*__errno_location()=saved;int rc=hsend(dst,p);int after=*__errno_location();r35_pub_end(r35_pt,rc);if(diag_enter)')
(O/'src/fx3-osd-r35.c').write_text(s);(O/'osd-source.diff').write_text(''.join(difflib.unified_diff(orig.splitlines(True),s.splitlines(True),fromfile=str(osd),tofile='src/fx3-osd-r35.c')))
ui=D/'v25-r15-snapshot-tail/fx3-ui-gate-v15.c';orig=ui.read_text();s=orig
s=replace(s,'static int publication_due(U visit)', '#include "r35-log.inc"\nstatic int publication_due(U visit)')
s=replace(s,'if(n<=50||n%1000==0){save(&st.last_ns,now());dprintf(2,"FX3_UI_GATE_SAMPLE','if(n<=50||n%1000==0){save(&st.last_ns,now());char r35_text[185];r35_suffix(r35_text);dprintf(2,"FX3_UI_GATE_SAMPLE')
s=replace(s,'source=%#lx observed_only=1\\n",id,n,syscall(178)', 'source=%#lx observed_only=1%s\\n",id,n,syscall(178)')
s=replace(s,'msg,type,src);}', 'msg,type,src,r35_text);}')
(O/'src/fx3-ui-r35.c').write_text(s);(O/'ui-source.diff').write_text(''.join(difflib.unified_diff(orig.splitlines(True),s.splitlines(True),fromfile=str(ui),tofile='src/fx3-ui-r35.c')))
print('2 isolated helper sources prepared; original probe assembly referenced unchanged')
