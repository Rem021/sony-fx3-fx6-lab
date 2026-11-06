from pathlib import Path
import subprocess,json,hashlib,os,plistlib
R=Path(__file__).resolve().parent;H=R/'helpers';n='fx3-ldec-ioctl103-test-v1';assert not(H/n).exists()
assert plistlib.loads(subprocess.check_output(['diskutil','info','-plist','/Volumes/KAFU2T']))['VolumeUUID']=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
args=[str(R/'toolchains/zig-aarch64-macos-0.17.0/zig'),'cc','-target','aarch64-linux-gnu.2.25','-O2',str(H/(n+'.c')),'-o',str(H/n)]
env=dict(os.environ,ZIG_GLOBAL_CACHE_DIR=str(R/'toolchains/zig-cache'),ZIG_LOCAL_CACHE_DIR=str(R/'toolchains/zig-local-cache'))
q=subprocess.run(args,env=env,capture_output=True,text=True);(H/(n+'-build.log')).write_text(q.stdout+q.stderr);assert q.returncode==0,q.stderr
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
(H/(n+'-build.json')).write_text(json.dumps({'args':args,'exit':q.returncode,'source_sha256':sha(H/(n+'.c')),'output_sha256':sha(H/n)},indent=2)+'\n');print('AP103_GUEST_IOCTL_TEST_BUILD_PASS')
