#!/usr/bin/env python3
"""Cross-rebuild the bridge into a bounded temporary directory and compare bytes."""
import hashlib
import json
import subprocess
import tempfile
from pathlib import Path

HERE=Path(__file__).resolve().parent
CLANG=Path('/usr/bin/clang')
LLD=Path('/Volumes/KAFU2T/AI/Projects/HUSK/work/tools/rustup/toolchains/stable-aarch64-apple-darwin/lib/rustlib/aarch64-apple-darwin/bin/gcc-ld/ld.lld')
PIN='b5d546eb2843c819ebdcab1cda2ce7530beb30afece48d378b470c1555b2428b'

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def call(args):
    r=subprocess.run([str(x) for x in args],capture_output=True,text=True)
    if r.returncode:raise RuntimeError('command failed: '+repr(args)+'\n'+r.stderr)
    return r.stdout

def main():
    resource=call([CLANG,'-print-resource-dir']).strip()
    if not LLD.is_file():raise RuntimeError('pinned LLD absent')
    with tempfile.TemporaryDirectory(prefix='cross-check-',dir=HERE) as d:
        tmp=Path(d);objects=[]
        for stem in ('bridge_core','bridge_runtime','sha256','bridge_stops'):
            source=HERE/(stem+('.S' if stem=='bridge_stops' else '.c'))
            out=tmp/(stem+'.o');objects.append(out)
            args=[CLANG,'-target','aarch64-linux-gnu','-c',source,'-o',out]
            if source.suffix=='.c':
                args[3:3]=['-nostdinc','-isystem',resource+'/include','-std=c11','-O2',
                           '-ffreestanding','-fPIC','-fno-builtin','-fno-stack-protector']
            call(args)
        elf=tmp/'libfx6diag.so'
        call([LLD,'-m','aarch64elf','-shared','-Bsymbolic','-soname','libfx6diag.so',
              '--hash-style=gnu','-z','relro','-z','now','-z','noexecstack','-o',elf,
              *objects,HERE/'link-inputs/libdl-2.25.so',HERE/'link-inputs/libc-2.25.so'])
        if sha(elf)!=PIN or sha(HERE/'libfx6diag.so')!=PIN:
            raise RuntimeError('cross rebuild differs from pinned bridge: rebuilt '+sha(elf)+
                               ' '+str(elf.stat().st_size)+'B vs pinned '+sha(HERE/'libfx6diag.so')+
                               ' '+str((HERE/'libfx6diag.so').stat().st_size)+'B')
        objdump=call(['/usr/bin/xcrun','llvm-objdump','-p',elf])
        imports=call(['/usr/bin/xcrun','llvm-objdump','-T',elf])
        if objdump.count('NEEDED')!=2 or 'libdl.so.2' not in objdump or 'libc.so.6' not in objdump:
            raise RuntimeError('bridge DT_NEEDED drift')
        for name in ('dladdr','dlopen','dlsym','open','read','close'):
            if name not in imports:raise RuntimeError('bridge undefined import '+name)
        result={'status':'CROSS_REBUILT_IDENTICAL_NOT_RUN','bridge_sha256':PIN,
                'clang_path':str(CLANG),'lld_path':str(LLD),
                'lld_version':call([LLD,'--version']).strip(),
                'source_sha256':{p.name:sha(p) for p in (HERE/'sha256.c',HERE/'bridge_core.c',
                    HERE/'bridge_runtime.c',HERE/'bridge_stops.S',HERE/'callback_offsets.h',
                    HERE/'bridge_pins.h')},
                'link_input_sha256':{p.name:sha(p) for p in (HERE/'link-inputs/libdl-2.25.so',
                    HERE/'link-inputs/libc-2.25.so')},
                'needed':['libdl.so.2','libc.so.6'],'unknown_runtime_resolution':True}
        (HERE/'cross-build.json').write_text(json.dumps(result,indent=2)+'\n')
        print(json.dumps(result,indent=2))

if __name__=='__main__':main()
