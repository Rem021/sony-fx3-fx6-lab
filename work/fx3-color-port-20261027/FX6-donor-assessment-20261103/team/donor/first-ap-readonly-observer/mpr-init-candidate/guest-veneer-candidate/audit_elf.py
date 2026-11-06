#!/usr/bin/env python3
"""Inspect only pinned ELF dynamic contracts; static scope, no guest execution."""
import hashlib
import json
import re
import subprocess
from pathlib import Path

HERE=Path(__file__).resolve().parent
BRIDGE=HERE/'libfx6diag.so';AP=HERE/'appFw-bridge.so'

def run(*args):return subprocess.check_output(['/usr/bin/xcrun','llvm-objdump',*args],text=True)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    dynamic=run('-p',str(BRIDGE));symbols=run('-T',str(BRIDGE));relocs=run('-R',str(BRIDGE))
    aprelocs=run('-R',str(AP));apdynamic=run('-p',str(AP))
    needed=re.findall(r'^\s*NEEDED\s+(\S+)',dynamic,re.M)
    undef=re.findall(r'^\S+\s+DF \*UND\*\s+\S+ \(([^)]+)\) (\S+)$',symbols,re.M)
    exp=re.findall(r'^\S+\s+g\s+DF \S+\s+\S+\s+(\S+)$',symbols,re.M)
    slots={x for x in exp if re.fullmatch(r'fx6diag_slot_\d\d',x)}
    rel=re.findall(r'^([0-9a-f]{16})\s+(R_AARCH64_\S+)\s+(\S+)',relocs,re.M)
    types={x[1] for x in rel}
    jumps={x[2] for x in rel if x[1]=='R_AARCH64_JUMP_SLOT'}
    funcs={'dladdr','dlopen','dlsym','open','read','close'}
    if needed!=['libdl.so.2','libc.so.6'] or set(undef)!={( 'GLIBC_2.17',x) for x in funcs}:
        raise ValueError('DT_NEEDED/undefined version drift')
    if len(undef)!=6 or types!={'R_AARCH64_RELATIVE','R_AARCH64_JUMP_SLOT'} or jumps!=funcs:
        raise ValueError('bridge relocation drift')
    if slots!={f'fx6diag_slot_{i:02d}' for i in range(57)}:raise ValueError('slot exports')
    for x in ('fx6diag_mpr_init','fx6diag_mpr_enterrec','fx6diag_failstop','fx6diag_call_original'):
        if x not in exp:raise ValueError('bridge export '+x)
    apj={int(addr,16):name for addr,typ,name in re.findall(
        r'^([0-9a-f]{16})\s+(R_AARCH64_JUMP_SLOT)\s+(\S+)',aprelocs,re.M)}
    if apj.get(0x2ef1368)!='fx6diag_mpr_init' or apj.get(0x2ef2670)!='fx6diag_mpr_enterrec':
        raise ValueError('AP relocation names/addresses')
    if re.findall(r'^\s*NEEDED\s+(\S+)',apdynamic,re.M)[-1]!='libfx6diag.so':
        raise ValueError('AP bridge dependency')
    result={'status':'ELF_STATIC_AUDITED_NOT_LOADED','patched_ap_sha256':sha(AP),
        'bridge_sha256':sha(BRIDGE),'bridge_undefined_versioned':
        [{'name':n,'version':v} for v,n in undef],
        'bridge_needed':needed,'bridge_jump_slots':sorted(jumps),
        'bridge_relocation_types':{t:sum(1 for x in rel if x[1]==t) for t in sorted(types)},
        'unique_guest_slot_exports':len(slots),
        'ap_two_changed_jump_slots':{'0x2ef1368':apj[0x2ef1368],
                                     '0x2ef2670':apj[0x2ef2670]},
        'ap_new_needed':'libfx6diag.so','runtime_resolution_proven':False}
    (HERE/'elf-audit.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
