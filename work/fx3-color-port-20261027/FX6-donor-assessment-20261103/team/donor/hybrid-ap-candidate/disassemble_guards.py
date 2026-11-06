#!/usr/bin/env python3
"""Reproduce bounded AArch64 helper disassembly from pinned guest-identical SOs."""
import hashlib
import json
import subprocess
from pathlib import Path

HERE=Path(__file__).resolve().parent
audit=json.loads((HERE/'preload-audit.json').read_text())
rows={r['index']:r for r in audit['preloads']}
TOOL=Path('/Applications/Xcode-beta.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain/usr/bin/llvm-objdump')
WINDOWS={4:[('dlopen',0x127dc,0x12c0c),('install',0x132cc,0x13604)],
         7:[('dlopen',0x26664,0x26ab0),('gpe_bind',0x25f28,0x26664)],
         11:[('dlopen',0x11f9c,0x123d8)],
         12:[('dlopen',0x13764,0x13b58),('install',0x13ca4,0x13fe4)],
         16:[('dlopen',0x139bc,0x13eec),('install',0x13f98,0x14490)]}

def sha(path):
    with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def main():
    assert TOOL.is_file()
    out=HERE/'asm';out.mkdir(exist_ok=True)
    evidence=[]
    for idx,windows in WINDOWS.items():
        row=rows[idx];binary=Path(row['matching_local_binary']);assert sha(binary)==row['guest_sha256']
        for label,start,end in windows:
            cmd=[str(TOOL),'-d',f'--start-address={start}',f'--stop-address={end}',str(binary)]
            p=subprocess.run(cmd,capture_output=True,text=True,check=True)
            assert p.stdout.startswith('\n') and 'Disassembly of section .text:' in p.stdout
            dest=out/f'{idx:02d}-{label}.txt';dest.write_text(p.stdout)
            evidence.append({'preload_index':idx,'label':label,'binary_sha256':row['guest_sha256'],
                             'start_RVA':hex(start),'stop_RVA_exclusive':hex(end),
                             'output':str(dest),'output_sha256':sha(dest)})
    (HERE/'asm-index.json').write_text(json.dumps({'tool':str(TOOL),'tool_sha256':sha(TOOL),
        'windows':evidence,'not_execution':True},indent=2)+'\n')
    print(json.dumps({'guard_helpers':len(WINDOWS),'ranges':len(evidence),'tool_sha256':sha(TOOL)},indent=2))

if __name__=='__main__':main()
