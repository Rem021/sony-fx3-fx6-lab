from pathlib import Path
import json,hashlib,subprocess,plistlib,struct,importlib.util
R=Path(__file__).resolve().parent;H=R/'helpers';D=R/'ap103-r2-soft-ldec';I=R.parents[1]/'lead-claude/impl/ldec-lz77';assert not D.exists()
assert plistlib.loads(subprocess.check_output(['diskutil','info','-plist','/Volumes/KAFU2T']))['VolumeUUID']=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
base=R/'ap102-r3-date-ordinary/candidate.json';assert sha(base)=='f693609ab5cd9e6cd6f50d63f7dde14b5d9f0eb77db3f1e7fea98407eb8ac3b0';v=json.loads(base.read_text())
assert 'AP103_HOST_ABI_BOUNDS_COPY_FAILURE_NO_PARTIAL_OUTPUT_ASAN_UBSAN_PASS' in (H/'check-ldec103-v1.log').read_text()
extra={}
for name in ['fx3-ldec-soft103-v1.ko','fx3-ldec-ioctl103-test-v2']:
 build=H/((name[:-3] if name.endswith('.ko')else name)+'-build.json');assert sha(H/name)==json.loads(build.read_text())['output_sha256'];extra['simulation/'+name]=(H/name).read_bytes()
for name in ['nine-patch-01-1355','panel-02-1228','icon-00-0']:
 for suffix in ['.ldec','.raw']:extra['simulation/ldec103/'+name+suffix]=(I/'samples'/(name+suffix)).read_bytes()
extra['simulation/ldec103/NOTICE.txt']=(I/'NOTICE.txt').read_bytes()
data=Path(v['initrd']['path']).read_bytes();assert sha(Path(v['initrd']['path']))==v['initrd']['sha256'];off=0;entries=[];changed=[]
while True:
 f=[int(data[off+6+i*8:off+14+i*8],16)for i in range(13)];n=data[off+110:off+110+f[11]-1].decode();off=(off+110+f[11]+3)&~3;b=data[off:off+f[6]];off=(off+f[6]+3)&~3
 if n=='TRAILER!!!':break
 if n=='init':
  init=b.decode();needle=' echo FX3_BACKUP_CP_INSMOD_BEGIN\n';assert init.count(needle)==1
  inserted=''' echo FX3_LDEC103_INIT_BEGIN
 /bin/busybox insmod /simulation/fx3-ldec-soft103-v1.ko
 ldec_rc=$?
 echo FX3_LDEC103_INSMOD_RC=$ldec_rc
 if [ "$ldec_rc" = 0 ] && [ ! -c /dev/ldec ]; then /bin/busybox mknod /dev/ldec c 251 205; fi
 /bin/busybox ls -l /dev/ldec
 if [ "$ldec_rc" != 0 ] || [ ! -c /dev/ldec ]; then echo FX3_LDEC103_INIT_FAILED; while true; do /bin/busybox sleep 1; done; fi
 /simulation/fx3-ldec-ioctl103-test-v2
 ldec_test_rc=$?
 echo FX3_LDEC103_SELFTEST_RC=$ldec_test_rc
 if [ "$ldec_test_rc" != 0 ]; then echo FX3_LDEC103_SELFTEST_FAILED; while true; do /bin/busybox sleep 1; done; fi
'''
  init=init.replace(needle,inserted+needle);assert 'insmod /usr/kmod/ldec.ko' not in init;b=init.encode();changed.append(n)
 entries.append((n,f,b))
names={n for n,_,_ in entries};assert not names&extra.keys();D.mkdir();out=bytearray()
def add(n,f,b,i):
 f=f.copy();raw=n.encode()+b'\0';f[0]=i;f[6]=len(b);f[11]=len(raw);out.extend(b'070701'+''.join(f'{x:08x}'for x in f).encode()+raw);out.extend(b'\0'*(-len(out)%4));out.extend(b);out.extend(b'\0'*(-len(out)%4))
dirs=['simulation/ldec103'];new_entries=[(n,[0,0o40755,0,0,2,0,0,0,0,0,0,0,0],b'')for n in dirs]
for n,b in extra.items():new_entries.append((n,[0,0o100755 if n.endswith('test-v2')else 0o100644,0,0,1,0,0,0,0,0,0,0,0],b))
for i,(n,f,b)in enumerate(entries+new_entries,1):add(n,f,b,i)
add('TRAILER!!!',[0]*13,b'',len(entries+new_entries)+1);cp=D/'guest.cpio';cp.write_bytes(out)
sp=importlib.util.spec_from_file_location('fdt',R.parents[1]/'fx3-audit/prepare_virt_dtb.py');m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m);tree,_,res,meta=m.parse(Path(v['dtb']['path']).read_bytes());start,size=0x41d300000,0x100000
for at in range(0,len(res)-16,16):
 a,n=struct.unpack_from('>QQ',res,at);assert not(a<start+size and start<a+n)
assert res[-16:]==b'\0'*16;res=res[:-16]+struct.pack('>QQ',start,size)+res[-16:]
chosen=next(n for k,n in tree['items']if k=='node'and n['name']=='chosen');chosen['items']=[(k,(q[0],struct.pack('>Q',0x440000000+len(out))))if k=='prop'and q[0]=='linux,initrd-end'else(k,q)for k,q in chosen['items']];dt=D/'guest.dtb';dt.write_bytes(m.encode(tree,res,meta));v['dtb']={'path':str(dt),'sha256':sha(dt)};v['initrd']={'path':str(cp),'sha256':sha(cp)}
v['scope']='AP103 software /dev/ldec synchronous decoder under original ioctl1 32-byte ABI, native node251:205; all AP102-r3 original files/other device models/Backup seed unchanged. Separate1MiB FDT reservation used only by pre-AP ioctl selftest. Original hardware ldec.ko not loaded. After actual highlighter/icons/background verification, native same-value date confirmation then ordinary inline toggle and standby idle>=60s, maximum600s four cores and screenshot reviewed before every button.'
v['ap103_contract']={'authority':'msg_29cd3974555b','baseline':str(base),'baseline_sha256':sha(base),'synthetic_ldec':True,'original_ldec_hw':False,'ABI':{'command':1,'bytes':32,'major':251,'minor':205,'no_encoded_magic_or_size':True,'no_output_length_writeback':True},'test_reservation':{'physical':hex(start),'bytes':size},'decoder_core':{'path':str(I/'ldec_soft.c'),'sha256':sha(I/'ldec_soft.c')},'guest_selftest_required':True,'malformed_error_mapping_scope':'Original badcmd/channel=-22, copy/allocation/hardwareinvalid=-5; exact malformedhardware stream behavior unproven.'}
v['required_markers']+=['FX3_LDEC103_BOUND major=251 minor=205 ioctl_bytes=32 command=1 result=0','FX3_LDEC103_GUEST_IOCTL_SELFTEST_PASS','FX3_LDEC103_SELFTEST_RC=0']
(D/'candidate.json').write_text(json.dumps(v,indent=2)+'\n')
from cpio_audit import parse,audit
_,bm=parse(Path(json.loads(base.read_text())['initrd']['path']));_,am=parse(cp);diff=[n for n in bm if bm[n]!=am[n]];assert diff==['init'];assert set(am)-set(bm)==set(extra)|set(dirs)
assert hashlib.sha256(am['setting/Backup.bin']).hexdigest()==v['native_Backup_seed']['sha256'];ar=audit(cp,R.parents[3]/'outputs/fx3-vm/share/fx3-original-app-loader-probe.cpio');assert ar['safe_to_unpack'];(D/'cpio-audit.json').write_text(json.dumps(ar,indent=2)+'\n');(D/'init-reviewed.sh').write_bytes(am['init']);subprocess.run(['/bin/sh','-n',str(D/'init-reviewed.sh')],check=True)
(D/'build-receipt.json').write_text(json.dumps({'baseline':str(base),'baseline_SHA256':sha(base),'changed_existing_member_bodies':diff,'added_members':sorted(set(am)-set(bm)),'all_other_existing_members_unchanged':True,'DTB_changes':['initrd-end','AP103 isolated selftest reservation41d300000/1MiB'],'original_ldec_not_loaded':True,'native_Backup_seed_unchanged':True},indent=2)+'\n');print(D/'candidate.json')
