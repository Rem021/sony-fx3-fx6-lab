#!/usr/bin/env python3
from pathlib import Path
import json,struct,re,stat,posixpath,hashlib,argparse,plistlib,subprocess
ROOT=Path('/Volumes/KAFU2T/AI/Projects/Mac');BASE=ROOT/'work/fx3-vm-20261101';OUT=BASE/'fx3-audit'
sha=lambda b:hashlib.sha256(b).hexdigest()
def cpio_files(p):
 b=p.read_bytes();o=0;files={}
 while True:
  assert b[o:o+6]==b'070701';v=[int(b[o+6+i*8:o+14+i*8],16) for i in range(13)];o+=110;n='/'+b[o:o+v[11]-1].decode();o=(o+v[11]+3)&~3;d=b[o:o+v[6]];o=(o+v[6]+3)&~3
  if n=='/TRAILER!!!':break
  assert n not in files;files[n]=(v[1],d)
 return files
def canonical(files,p):
 seen=set()
 while stat.S_ISLNK(files[p][0]):
  assert p not in seen;seen.add(p);t=files[p][1].decode();p=posixpath.normpath(t if t.startswith('/') else posixpath.join(posixpath.dirname(p),t))
 return p
def ring_rows(p):
 b=(p/'printk-ring.bin').read_bytes();first,nxt,o,end=struct.unpack_from('<QQII',(p/'printk-indices.bin').read_bytes());rows=[]
 for i in range(first,nxt):
  ts,ln,tl,dl,fac,fl=struct.unpack_from('<QHHHBB',b,o);assert ln>=16 and ln%4==0 and tl+dl+16<=ln and o+ln<=len(b)
  rows.append(b[o+16:o+16+tl].decode());o+=ln
 assert o==end
 return rows
ap=argparse.ArgumentParser();ap.add_argument('--minimal-run',required=True);ap.add_argument('--loader-run',required=True);ap.add_argument('--output',required=True);a=ap.parse_args()
expected_kernel='da4a66fa29f6b4033233c0d8e7bd9a6f0ffab0cc18d85a44aa6f3830b7c4820c';qpath=ROOT/'outputs/fx3-vm/bin/qemu-system-aarch64';qh=sha(qpath.read_bytes());reports={}
for profile,rid in [('minimal',a.minimal_run),('app-loader',a.loader_run)]:
 p=BASE/'host/runs'/rid;receipt=json.loads((p/'receipt.json').read_text());serial=(p/'serial.log').read_bytes();text=serial.decode();assert receipt['inputs_unchanged'] and receipt['process_reaped'] and receipt['qemu_exit']==0 and receipt['host_observer_error'] is None
 assert receipt['source_kernel_sha256']==expected_kernel and receipt['qemu_runtime_sha256']==qh
 assert not receipt['guest_exception_markers'] and receipt['physical_devices_disks_network_or_firmware_writes']==0
 assert 'FX3_ORIGINAL_BUSYBOX_REACHED' in text
 uname=next(x.strip() for x in text.splitlines() if x.startswith('Linux ') and '4.9.337-scel+' in x)
 rows=ring_rows(p);skips=[]
 for r in json.loads((OUT/'minimal-linux-blacklist-evidence.json').read_text())['rows']:
  name=r['name'];assert any('blacklisting initcall '+name in x for x in rows);assert any('initcall '+name+' blacklisted' in x for x in rows);skips.append(name)
 reports[profile]={'run':str(p),'receipt_sha256':sha((p/'receipt.json').read_bytes()),'serial_sha256':sha(serial),'status':receipt['status'],'uname':uname,'raw_printk_records_independently_parsed':len(rows),'seven_original_initcalls_actually_skipped':skips,'qemu_runtime_sha256':qh,'kernel_sha256':expected_kernel,'process_reaped':True}
 if profile=='minimal':assert 'FX3_VM_PROBE_END' in text
 else:
  markers=['FX3_LD_VERIFY_RC_bootin=0','FX3_LD_LIST_RC_bootin=0','FX3_LD_VERIFY_RC_im=0','FX3_LD_LIST_RC_im=0','FX3_APPLICATION_LOADER_PROBE_END'];assert all(x in text for x in markers)
  files=cpio_files(OUT/'fx3-original-app-loader-probe.cpio');original=json.loads((OUT/'application-loader-probe.json').read_text())['original_elfs'];idx={x['guest_path']:x for x in original}
  for r in original:assert sha(files[r['guest_path']][1])==r['sha256']
  providers=[]
  for app in ['bootin','im']:
   segment=text.split('FX3_LD_LIST_BEGIN_'+app,1)[1].split('FX3_LD_LIST_RC_'+app+'=0',1)[0]
   for soname,path in re.findall(r'\s(\S+)\s+=>\s+(/\S+)\s+\(',segment):
    target=canonical(files,path);h=sha(files[target][1]);assert idx[target]['sha256']==h;providers.append({'application':app,'soname':soname,'runtime_path':path,'canonical_original_path':target,'sha256':h})
  assert '=> not found' not in text and len(providers)==25
  reports[profile].update({'required_markers':markers,'original_elf_count':len(original),'mapped_library_provider_rows':providers,'app_main_or_ui_claimed':False})
vol=plistlib.loads(subprocess.check_output(['diskutil','info','-plist','/Volumes/KAFU2T']));assert vol['VolumeUUID']=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
proof={'status':'FINAL_NATIVE_MAC_FX3_CORE_AND_LOADER_INDEPENDENTLY_VERIFIED','qemu_binary':str(qpath),'qemu_binary_sha256':qh,'profiles':reports,'limits':'Minimal custom init and explicit unsupported-device blacklist. Full original AP main/menu/capture require separate proof.'};p=Path(a.output).resolve();assert p.is_relative_to(OUT.resolve()) and not p.exists();p.write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'status':proof['status'],'qemu_sha256':qh,'profiles':{k:{'run':v['run'],'ring_rows':v['raw_printk_records_independently_parsed'],'status':v['status']} for k,v in reports.items()}},ensure_ascii=False))
