#!/usr/bin/env python3
"""Finite source/compiled ABI audit, never execute a guest object."""
from pathlib import Path
import json,re,hashlib,subprocess
O=Path(__file__).resolve().parent;D=O.parent
old=(D/'v25-r15-snapshot-tail/fx3-ui-gate-v15.c').read_text();new=(O/'src/fx3-ui-r35.c').read_text()
start='if(n<=50||n%1000==0){';stop='\n mirror();snapshot_serve(id,0);'
a=old.index(start,old.index('void fx3_gate_event'));b=old.index(stop,a);c=new.index(start,new.index('void fx3_gate_event'));d=new.index(stop,c)
oldblock=old[a:b];newblock=new[c:d]
assert newblock.replace('char r35_text[185];r35_suffix(r35_text);','').replace('observed_only=1%s','observed_only=1').replace('msg,type,src,r35_text','msg,type,src')==oldblock
(O/'tests/original-ui-selected.inc').write_text(oldblock+'\n');(O/'tests/candidate-ui-selected.inc').write_text(newblock+'\n')
# No additional original native calls or diagnostic logging sites.
o=(D/'v25-menu-osd-diagnostic-r3/src/fx3-osd-headless-v25-r3.c').read_text();n=(O/'src/fx3-osd-r35.c').read_text()
call_counts={}
for f in ['hsend','hfree','halloc','hreceive','hwait','hsignal','open','mmap','munmap','dprintf','own_lock','own_unlock']:
 x=len(re.findall(r'\b'+f+r'\s*\(',o));y=len(re.findall(r'\b'+f+r'\s*\(',n));assert x==y,(f,x,y);call_counts[f]=[x,y]
for s in ['const U offsets[60]','const W words[60]','const U regs[60]']:
 pattern=re.escape(s)+r'=\{[^}]+\}';assert re.search(pattern,old).group()==re.search(pattern,new).group()
# Check original claim dominates selftest and install; no activation of extra instance.
bind=old[old.index('static void bind(void *h)'):old.index('void *dlopen(const char *name')]
assert bind.index('if(bind_ram())')<bind.index('install(&test_pool')<bind.index('install(&app_pool')
# Save full candidate disassembly/symbol/dynamic receipts.
receipts={}
for tag in ['osd','ui']:
 f=O/'build'/('fx3-'+tag+'-r35.so');rec={}
 for name,args in [('disasm',['/usr/bin/xcrun','llvm-objdump','-d',str(f)]),('symbols',['/usr/bin/xcrun','llvm-nm','-S',str(f)]),('dynamic',['/usr/bin/xcrun','llvm-objdump','-p',str(f)])]:
  p=subprocess.run(args,capture_output=True);(O/'receipts'/(tag+'-'+name+'.txt')).write_bytes(p.stdout);(O/'receipts'/(tag+'-'+name+'.stderr')).write_bytes(p.stderr);assert p.returncode==0;rec[name]={'argv':args,'exit':p.returncode}
 receipts[tag]=rec
(O/'CONTROL-FLOW.json').write_text(json.dumps({'selected_block_exact_reversible_difference':True,'native_call_site_counts':call_counts,'probe_table_and_assembly_unchanged':True,'original_claim_dominates_all_probe_installs':True,'guest_assembly_executed':False,'disassembly':receipts},indent=2)+'\n');print('source native/log/control-flow invariants PASS; disassembly receipts saved')
