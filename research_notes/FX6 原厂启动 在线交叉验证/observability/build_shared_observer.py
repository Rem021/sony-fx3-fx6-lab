#!/usr/bin/env python3
"""Build a review-only AArch64 ET_DYN queue observer. Never starts/contacts a VM."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import plistlib
import subprocess
from elftools.elf.elffile import ELFFile

EXPECTED_IMPORTS = {'__errno_location', '_exit', 'clock_gettime', 'dladdr',
                    'dlerror', 'dlsym', 'dprintf', 'syscall'}


def fp(path):
    path=Path(path)
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):
            h.update(chunk)
    return {'path':str(path),'bytes':path.stat().st_size,'sha256':h.hexdigest()}


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--repo',type=Path,default=Path('/Volumes/KAFU2T/AI/Projects/Mac/outputs/sony-fx3-fx6-lab'))
    ap.add_argument('--compiler',default='/usr/bin/clang')
    ap.add_argument('--zig',type=Path,default=Path('/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/menu-repair-01/runtime/toolchains/zig-aarch64-macos-0.17.0/zig'))
    ap.add_argument('--guest-lib-dir',type=Path,default=Path('/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/menu-repair-01/runtime/guest-sdk/lib'))
    ap.add_argument('--baseline-cpio',type=Path,default=Path('/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/fx6-boot-readiness/early-kernel/cp-helper-agnostic/guest-hybrid-fx6kernel-capid-grmreal293-native.cpio'))
    args=ap.parse_args()
    volume=plistlib.loads(subprocess.check_output(['diskutil','info','-plist','/Volumes/KAFU2T']))
    if volume.get('VolumeUUID')!='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B':
        raise RuntimeError('wrong external volume')
    repo=args.repo.resolve()
    build=repo/'work/parallel-research-20261107/online-observability'
    if not build.resolve().is_relative_to(repo/'work'):
        raise ValueError('build must stay in repository work/')
    build.mkdir(parents=True,exist_ok=True)
    env=os.environ.copy()
    env.update(ZIG_LOCAL_CACHE_DIR=str(build/'zig-local-cache'),ZIG_GLOBAL_CACHE_DIR=str(build/'zig-global-cache'))
    source=repo/'reports/2026-11-07-fx6-queue-contract/observer/observe_osal_queue.c'
    expected_libs={'libc-2.25.so':'f9104526eb7e5d2ea533c1a209bb0b83e69367f569e4c966895c8e106e6382c9',
        'libdl-2.25.so':'6dde01ab92843eaf8c330f4cbd9b47186b14843c4e1de9f7c68ecacb3414403b',
        'ld-2.25.so':'90b4fe734ba7faa08d4591b1363bff478e7bde399a821fc0b2d021c062a58a9a'}
    guest_libraries=[fp(args.guest_lib_dir/n) for n in expected_libs]
    for item in guest_libraries:
        if item['sha256']!=expected_libs[Path(item['path']).name]:
            raise ValueError('guest library SHA mismatch')
    cpio_members={}
    with args.baseline_cpio.open('rb') as f:
        while True:
            head=f.read(110)
            if not head or head[:6] not in (b'070701',b'070702'):
                raise ValueError('invalid newc baseline CPIO')
            fields=[int(head[6+i*8:14+i*8],16) for i in range(13)]
            size,namesz=fields[6],fields[11]
            name=f.read(namesz).rstrip(b'\0').decode()
            f.seek((-f.tell())%4,1)
            if name=='TRAILER!!!':
                break
            base=Path(name).name
            if name.startswith('lib/') and base in expected_libs:
                digest=hashlib.sha256(f.read(size)).hexdigest()
                if digest!=expected_libs[base]:
                    raise ValueError('baseline CPIO guest libc/libdl/ld mismatch')
                cpio_members[name]={'bytes':size,'sha256':digest}
            else:
                f.seek(size,1)
            f.seek((-f.tell())%4,1)
    if len(cpio_members)!=3:
        raise ValueError('baseline CPIO missing guest runtime libraries')
    obj=build/'observe_osal_queue.o'
    library=build/'libfx6-queue-observer.so'
    commands=[
        [args.compiler,'-target','aarch64-linux-gnu','-std=c11','-O2','-fPIC','-ffreestanding',
         '-fno-omit-frame-pointer','-fno-optimize-sibling-calls','-mno-outline-atomics',
         '-Wall','-Wextra','-Werror','-c',str(source),'-o',str(obj)],
        [str(args.zig),'ld.lld','-shared','--hash-style=both','--soname=libfx6-queue-observer.so',
         '-z','noexecstack','-z','relro','-z','now','--fatal-warnings',
         '--no-undefined','--no-allow-shlib-undefined',str(obj),'--as-needed',
         *[str(args.guest_lib_dir/n) for n in expected_libs],'-o',str(library)],
    ]
    for i,command in enumerate(commands):
        result=subprocess.run(command,capture_output=True,text=True,env=env)
        (build/f'command-{i}-stdout.txt').write_text(result.stdout)
        (build/f'command-{i}-stderr.txt').write_text(result.stderr)
        result.check_returncode()
    with library.open('rb') as f:
        elf=ELFFile(f)
        if elf['e_machine']!='EM_AARCH64' or elf['e_type']!='ET_DYN':
            raise ValueError('wrong guest shared object architecture/type')
        dynsym=list(elf.get_section_by_name('.dynsym').iter_symbols())
        undefined=sorted({s.name for s in dynsym if s.name and s['st_shndx']=='SHN_UNDEF'})
        exported=sorted({s.name for s in dynsym if s.name and s['st_shndx']!='SHN_UNDEF' and s['st_info']['bind']=='STB_GLOBAL'})
        if set(undefined)!=EXPECTED_IMPORTS or exported!=['osal_rcv_msg_tmo']:
            raise ValueError('unexpected imports/exports or compiler runtime dependency')
        needed=[t.needed for t in elf.get_section_by_name('.dynamic').iter_tags() if t.entry.d_tag=='DT_NEEDED']
        if set(needed)!={'libc.so.6','libdl.so.2'}:
            raise ValueError('unexpected guest DSO dependency')
        versions=[]
        version_section=elf.get_section_by_name('.gnu.version_r')
        if version_section:
            for ver,aux in version_section.iter_versions():
                versions.append({'file':ver.name,'versions':[a.name for a in aux]})
        if {v for item in versions for v in item['versions']}!={'GLIBC_2.17'}:
            raise ValueError('unexpected guest GLIBC version requirement')
        if any(elf.get_section_by_name(n) for n in ('.init_array','.fini_array')):
            raise ValueError('unexpected constructor/destructor array')
        segments=[{'type':s['p_type'],'flags':s['p_flags']} for s in elf.iter_segments()]
        if any(s['type']=='PT_INTERP' or (s['type']=='PT_GNU_STACK' and s['flags']&1) for s in segments):
            raise ValueError('unexpected interpreter or executable stack')
        comment=elf.get_section_by_name('.comment').data().decode(errors='replace').replace('\0','\n').strip()
    result={'schema':'fx6-queue-observer-et-dyn-offline-v1','source':fp(source),'object':fp(obj),
        'shared_library':fp(library),'compiler':fp(args.compiler),'zig':fp(args.zig),
        'compiler_version':subprocess.check_output([args.compiler,'--version'],text=True).strip(),
        'zig_version':subprocess.check_output([str(args.zig),'version'],text=True).strip(),
        'linker_version':subprocess.check_output([str(args.zig),'ld.lld','--version'],text=True).strip(),
        'commands':commands,'build_env':{k:env[k] for k in ('ZIG_LOCAL_CACHE_DIR','ZIG_GLOBAL_CACHE_DIR')},
        'elf_type':'ET_DYN','elf_machine':'EM_AARCH64','undefined_symbols':undefined,
        'exported_symbols':exported,'dt_needed':needed,'program_headers':segments,'comment':comment,
        'guest_libraries_linked_dynamically':guest_libraries,'glibc_version_requirements':versions,
        'baseline_cpio':fp(args.baseline_cpio),'baseline_cpio_runtime_members':cpio_members,
        'guest_runtime_closure':{'libfx6-queue-observer.so':['libc.so.6','libdl.so.2'],
            'libc.so.6':['ld-linux-aarch64.so.1'],
            'libdl.so.2':['libc.so.6','ld-linux-aarch64.so.1'],
            'ld-linux-aarch64.so.1':[]},
        'guest_linked':True,'guest_loaded':False,'guest_executed':False,'cpio_changed':False,
        'closed_source_payload_linked':False,
        'limits':'Eight imports resolve against pinned guest glibc 2.25 with GLIBC_2.17 requirements under --no-undefined. ET_DYN success does not prove guest loader binding, ABI, call interception or timing.'}
    (build/'build-result.json').write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n')
    print(json.dumps(result,indent=2,ensure_ascii=False))


if __name__=='__main__':
    main()
