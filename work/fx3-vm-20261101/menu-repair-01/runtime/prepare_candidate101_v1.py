from pathlib import Path
import json,hashlib,subprocess,plistlib,struct,importlib.util
R=Path(__file__).resolve().parent;D=R/'ap101-v1-native-backup-file';assert not D.exists();assert plistlib.loads(subprocess.check_output(['diskutil','info','-plist','/Volumes/KAFU2T']))['VolumeUUID']=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();authority='msg_ebab9bedf83a';source=R/'runs/ap100v1sync600-8d0d69c0/Backup-native-file-before-menu.bin';seed=source.read_bytes();assert sha(source)=='552fd5f8b422f855aecbe0c3918b56f83f60fb76ea9a3b6fc7a0291c26035d9e';assert len(seed)==2229740
banks=[]
for off in [0,0xd2000]:
 n=sum(struct.unpack_from('<2I',seed,off+24));b=seed[off:off+n];got=(sum(b)-sum(b[32:36]))&0xffffffff;stored=struct.unpack_from('<I',b,32)[0];assert got==stored;banks.append({'file_offset':off,'bytes':n,'checksum':stored,'checksum_valid':True,'sha256':hashlib.sha256(b).hexdigest()})
assert seed[0x8eb51]==seed[0x6e7ac]==0
for old,new in [('gate_input100.py','gate_input101.py'),('key_readback100.py','key_readback101.py'),('run_candidate100_v1.py','run_candidate101_v1.py'),('ap100_decide_v1.py','ap101_decide_v1.py')]:
 p=R/new;assert not p.exists();s=(R/old).read_text().replace('gate_input100','gate_input101').replace('key_readback100','key_readback101').replace('ap100-','ap101-').replace('msg_db11d2266751',authority)
 if new=='run_candidate101_v1.py':
  s=s.replace("    candidate = json.loads(candidate_path.read_text())", "    candidate = json.loads(candidate_path.read_text())\n    native_seed=input_check(candidate['native_Backup_seed'])")
  s=s.replace("    checks.append((Path(baseline['kernel']['path']), baseline['kernel']['sha256']))","    checks.append((Path(baseline['kernel']['path']), baseline['kernel']['sha256']))\n    checks.append((native_seed,candidate['native_Backup_seed']['sha256']))")
  a=s.index("                if 'FX3_AP89_BACKUP_REPLAY_VERIFIED' in serial_now and not replay_input_verified:");z=s.index('                seen_uptime=',a)
  s=s[:a]+'''                if 'FX3_AP101_NATIVE_LOAD_READBACK_WINDOW_BEGIN' in serial_now and not replay_input_verified:
                    qmp('stop')
                    before_AP='FX3_AP_NATURAL_BOOTIN_BEGIN' not in serial_now
                    input_path=run/'backup-native-load-before-AP.bin'
                    qmp('human-monitor-command',{'command-line':'pmemsave 0x404000000 0x221000 "'+str(input_path)+'"'})
                    raw=input_path.read_bytes();native=native_seed.read_bytes();parts=[]
                    for off in [0,0xd2000]:
                        n=sum(struct.unpack_from('<2I',native,off+24));loaded=raw[off:off+n];filepart=native[off:off+n]
                        checksum=(sum(loaded)-sum(loaded[32:36]))&0xffffffff
                        different=[i for i,(x,y) in enumerate(zip(loaded,filepart)) if x!=y]
                        parts.append({'offset':off,'native_file_bytes':n,'loaded_sha256':hashlib.sha256(loaded).hexdigest(),'file_sha256':hashlib.sha256(filepart).hexdigest(),'all_bytes_equal':loaded==filepart,'payload_after_header_equal':loaded[256:]==filepart[256:],'difference_count':len(different),'first_difference_offsets':different[:64],'loaded_first64_hex':loaded[:64].hex(),'loaded_checksum_valid':checksum==struct.unpack_from('<I',loaded,32)[0]})
                    verified=before_AP and 'FX3_BACKUP_INSMOD_RC=0' in serial_now and candidate['native_Backup_seed']['sha256'] in serial_now
                    proof={'method':'Original backup.ko Backup_load=1, native insmod return and actual source file SHA; QMP read-only bank snapshot after load, no RAM replay','path':str(input_path),'sha256':digest(input_path),'before_AP_bootin_marker':before_AP,'file_sha256':candidate['native_Backup_seed']['sha256'],'native_file_seen_and_module_load0':verified,'bank_comparison':parts,'force02cf0014':raw[0x8eb51],'force01070140':raw[0x6e7ac],'date02cf01b4':raw[0x9100c],'no_RAM_replay_helper':True}
                    (run/'ap101-native-load-readback.json').write_text(json.dumps(proof,indent=2)+'\\n')
                    if not verified:
                        early_stop_reason='AP101 original file/load/preAP identity gate failed';break
                    replay_input_verified=True
                    qmp('cont')
'''+s[z:]
 p.write_text(s);compile(s,str(p),'exec')
base=R/'ap100-v1-touch-backup-sync/candidate.json';v=json.loads(base.read_text());data=Path(v['initrd']['path']).read_bytes();assert sha(Path(v['initrd']['path']))==v['initrd']['sha256'];off=0;entries=[];changed=[];removed=[]
remove={'simulation/fx3-backup-replay-v1','simulation/ap89-backup-ram.bin'}
while True:
 f=[int(data[off+6+i*8:off+14+i*8],16) for i in range(13)];n=data[off+110:off+110+f[11]-1].decode();off=(off+110+f[11]+3)&~3;b=data[off:off+f[6]];off=(off+f[6]+3)&~3
 if n=='TRAILER!!!':break
 if n in remove:removed.append(n);continue
 if n=='setting/Backup.bin':b=seed;changed.append(n)
 if n=='init':
  text=b.decode();a=text.index(' echo FX3_AP89_BACKUP_REPLAY_BEGIN');z=text.index(' /simulation/fx3-file100-observer-v1 &',a);text=text[:a]+''' echo FX3_AP101_NATIVE_LOAD_READBACK_WINDOW_BEGIN bounded_seconds=5 original_backupfile_load=1 AP_not_started=1 RAM_replay_absent=1
 /bin/busybox sha256sum /setting/Backup.bin
 /bin/busybox sleep 5
 echo FX3_AP101_NATIVE_LOAD_READBACK_WINDOW_END
'''+text[z:];b=text.encode();changed.append(n)
 entries.append((n,f,b))
assert set(changed)=={'setting/Backup.bin','init'} and set(removed)==remove;D.mkdir();out=bytearray()
def add(n,f,b,i):
 f=f.copy();raw=n.encode()+b'\0';f[0]=i;f[6]=len(b);f[11]=len(raw);out.extend(b'070701'+''.join(f'{x:08x}' for x in f).encode()+raw);out.extend(b'\0'*(-len(out)%4));out.extend(b);out.extend(b'\0'*(-len(out)%4))
for i,(n,f,b) in enumerate(entries,1):add(n,f,b,i)
add('TRAILER!!!',[0]*13,b'',len(entries)+1);cp=D/'guest.cpio';cp.write_bytes(out);sp=importlib.util.spec_from_file_location('fdt',R.parents[1]/'fx3-audit/prepare_virt_dtb.py');m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m);tree,p,res,meta=m.parse(Path(v['dtb']['path']).read_bytes());chosen=next(n for k,n in tree['items'] if k=='node' and n['name']=='chosen');chosen['items']=[(k,(q[0],struct.pack('>Q',0x440000000+len(out)))) if k=='prop' and q[0]=='linux,initrd-end' else (k,q) for k,q in chosen['items']];dt=D/'guest.dtb';dt.write_bytes(m.encode(tree,res,meta));v['dtb']={'path':str(dt),'sha256':sha(dt)};v['initrd']={'path':str(cp),'sha256':sha(cp)};v.pop('backup_replay');v['native_Backup_seed']={'path':str(source),'sha256':sha(source),'bytes':len(seed),'native_bank_checks':banks};v['host_step_contract']['authority']=authority
conditional=['FX3_SYNC100_DMA_COPY','FX3_SYNC100_NATIVE_CALLBACK_RETURN','FX3_TOUCH100_COMMIT','FX3_TOUCH100_CONSUMED','const_alpha=','FX3_DATE98_LIVE'];v['conditional_markers']={x:'Original operation may not occur when saved setup is already complete; report actual presence separately' for x in conditional};v['required_markers']=[x for x in v['required_markers'] if x!='FX3_AP89_BACKUP_REPLAY_VERIFIED' and x not in conditional];v['required_markers']+=['FX3_AP101_NATIVE_LOAD_READBACK_WINDOW_BEGIN','FX3_BACKUP_INSMOD_RC=0'];v['scope']='AP101 baselineAP100 exact models unchanged. Remove guest RAM replay helper/input entirely; replace CPIO /setting/Backup.bin with original native AP100 saved file generation7 SHA552fd5f8..., checksums/force0 verified before pack. Original backup.ko Backup_load=1 executes native file loader; readonly preAP bank readback and sourceSHA. No host/guest RAM business-data injection. 600 seconds native already-completed setup boot, UUD4/4 force0/date set, actual standby PNG then MENU; seek original Language setting toEnglish only via stepped native buttons; original save and actual O_RDONLY new file generations if present. Preserve AP100 raw snapshots and all frozen artifacts.';v['ap101_contract']={'authority':authority,'original_seed_replaced_only_in_new_candidate':True,'RAM_replay_removed':sorted(remove),'all_other_simulation_and_original_ELF_bodies_identical':True,'official_language_path':'https://helpguide.sony.net/ilc/2210/v1/en/contents/TP1000845207.html'};(D/'candidate.json').write_text(json.dumps(v,indent=2)+'\n')
from cpio_audit import parse,audit
_,bm=parse(Path(json.loads(base.read_text())['initrd']['path']));_,am=parse(cp);assert set(bm)-set(am)==remove;assert [n for n in bm if n in am and bm[n]!=am[n]]==changed;ar=audit(cp,R.parents[3]/'outputs/fx3-vm/share/fx3-original-app-loader-probe.cpio');assert ar['safe_to_unpack'];(D/'cpio-audit.json').write_text(json.dumps(ar,indent=2)+'\n');init=D/'init-reviewed.sh';init.write_bytes(am['init']);subprocess.run(['/bin/sh','-n',str(init)],check=True);(D/'build-receipt.json').write_text(json.dumps({'base':str(base),'base_sha256':sha(base),'changed_member_bodies':changed,'removed_simulation_members':removed,'all_other_members_unchanged':True,'DTB_only_initrd_end':True,'source_file_SHA_and_checksums':v['native_Backup_seed'],'authority':authority},indent=2)+'\n');print(D/'candidate.json')
