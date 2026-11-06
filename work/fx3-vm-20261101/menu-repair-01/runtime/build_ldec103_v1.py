from pathlib import Path
import subprocess,json,hashlib,os,plistlib
R=Path(__file__).resolve().parent;H=R/'helpers';I=R.parents[1]/'lead-claude/impl/ldec-lz77';name='fx3-ldec-soft103-v1'
assert plistlib.loads(subprocess.check_output(['diskutil','info','-plist','/Volumes/KAFU2T']))['VolumeUUID']=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
assert not (H/(name+'.ko')).exists()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
samples=['nine-patch-01-1355','panel-02-1228','icon-00-0']
host=['clang','-O1','-g','-fsanitize=address,undefined','-fno-omit-frame-pointer',str(H/'check-ldec103-v1.c'),'-o',str(H/'check-ldec103-v1')]
q=subprocess.run(host,text=True,capture_output=True);assert q.returncode==0,q.stderr
q=subprocess.run([str(H/'check-ldec103-v1')]+[str(I/'samples'/(n+s))for n in samples for s in ['.ldec','.raw']],text=True,capture_output=True)
(H/'check-ldec103-v1.log').write_text(q.stdout+q.stderr);assert q.returncode==0,q.stdout+q.stderr
asm='''.section .modinfo,"a"
.asciz "license=GPL"
.asciz "author=FX3 VM compatibility model"
.asciz "depends=devno"
.asciz "vermagic=4.9.337-scel+ SMP preempt mod_unload aarch64"
.section .gnu.linkonce.this_module,"aw"
.balign 64
.global __this_module
.type __this_module,%object
__this_module:
.zero 24
.asciz "fx3_ldec_soft103_v1"
.zero 0x158-(.-__this_module)
.quad init_module
.zero 0x2b8-(.-__this_module)
.quad cleanup_module
.zero 0x300-(.-__this_module)
.size __this_module, .-__this_module
'''
unit=H/(name+'-module-unit.c');unit.write_text('#include "'+name+'.c"\n__asm__('+json.dumps(asm)+');\n')
env=dict(os.environ,ZIG_GLOBAL_CACHE_DIR=str(R/'toolchains/zig-cache'),ZIG_LOCAL_CACHE_DIR=str(R/'toolchains/zig-local-cache'))
args=[str(R/'toolchains/zig-aarch64-macos-0.17.0/zig'),'cc','-target','aarch64-linux-gnu.2.25','-ffreestanding','-fno-builtin','-fno-stack-protector','-fno-pic','-mcmodel=large','-mgeneral-regs-only','-mno-outline-atomics','-fno-asynchronous-unwind-tables','-fno-unwind-tables','-O2','-nostdlib','-c',str(unit),'-o',str(H/(name+'.ko'))]
q=subprocess.run(args,env=env,text=True,capture_output=True);(H/(name+'-build.log')).write_text(q.stdout+q.stderr);assert q.returncode==0,q.stderr
(H/(name+'-build.json')).write_text(json.dumps({'args':args,'exit':q.returncode,'source_sha256':sha(H/(name+'.c')),'output_sha256':sha(H/(name+'.ko')),'decoder_sha256':sha(I/'ldec_soft.c'),'header_sha256':sha(I/'ldec_soft.h'),'license_sha256':sha(I/'NOTICE.txt'),'host_test_log_sha256':sha(H/'check-ldec103-v1.log'),'authority':'msg_29cd3974555b','synthetic_ldec':True,'original_ldec_hw':False},indent=2)+'\n')
print(q.stdout+q.stderr);print('AP103_SOFT_DEVICE_HOST_TEST_AND_AARCH64_BUILD_PASS')
