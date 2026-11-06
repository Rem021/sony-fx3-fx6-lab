"""Explicit sanitized IORegistry cache query; no USB API, serial use or media IO."""
from pathlib import Path
import argparse,datetime,json,plistlib,subprocess,os
H=Path(__file__).resolve().parent
def sanitize(raw):
 if len(raw)>8*1024*1024:raise ValueError('cache byte limit')
 roots=plistlib.loads(raw)
 if isinstance(roots,dict):roots=[roots]
 if not isinstance(roots,list):raise ValueError('cache root')
 found=[];count=0
 def walk(nodes,depth=0):
  nonlocal count
  if depth>64 or not isinstance(nodes,list):raise ValueError('cache tree')
  for n in nodes:
   count+=1
   if count>10000 or not isinstance(n,dict):raise ValueError('cache node bound')
   if n.get('IOObjectClass')=='IOUSBHostDevice' and n.get('idVendor')==0x054c and n.get('idProduct')==0x0da1:
    location=n.get('locationID');registry=n.get('IORegistryEntryID')
    if type(location) is not int or not 0<location<2**32:raise ValueError('missing location cache')
    if type(registry) is not int or not 0<registry<2**64:raise ValueError('missing registry cache')
    found.append(dict(VID=0x054c,PID=0x0da1,locationID=location,location_hex=f'0x{location:08x}',
      registryID=registry,model=str(n.get('USB Product Name',''))[:120]))
   walk(n.get('IORegistryEntryChildren',[]),depth+1)
 walk(roots)
 return dict(source='Mac IORegistry cache only',candidate_count=len(found),candidates=found,
   unique_target_cache_candidate=len(found)==1,serial_values_selected_used_or_saved=False,raw_cache_saved=False,
   camera_interface_opened_or_commands_sent=False,
   same_unit_firmware_hash_health_or_USB_return_proven=False)

def self_test():
 secret='PRIVATE_SERIAL_MUST_NOT_APPEAR'
 device=dict(IOObjectClass='IOUSBHostDevice',idVendor=0x054c,idProduct=0x0da1,locationID=0x02100000,
  IORegistryEntryID=42,**{'USB Product Name':'ILME-FX3','USB Serial Number':secret})
 child=dict(device,IOObjectClass='IOUSBHostInterface');device['IORegistryEntryChildren']=[child]
 one=sanitize(plistlib.dumps([device]));assert one['candidate_count']==1 and secret not in json.dumps(one)
 many=sanitize(plistlib.dumps([device,dict(device,IORegistryEntryID=43)]));assert not many['unique_target_cache_candidate']
 assert sanitize(plistlib.dumps([]))['candidate_count']==0
 return dict(status='PASS_OFFLINE_CACHE_TARGET_PRIVACY_AND_ROOT_SELECTION',checks=3,live_queries=0)

if __name__=='__main__':
 a=argparse.ArgumentParser();x=a.add_mutually_exclusive_group(required=True)
 x.add_argument('--self-test',action='store_true');x.add_argument('--query-mac-cache',action='store_true')
 args=a.parse_args()
 if args.self_test:print(json.dumps(self_test()));raise SystemExit(0)
 v=plistlib.loads(subprocess.check_output(['/usr/sbin/diskutil','info','-plist','/Volumes/KAFU2T']))
 assert v.get('MountPoint')=='/Volumes/KAFU2T' and v.get('VolumeUUID','').upper()=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
 assert not (H/'current-cache-target.json').exists(),'no automatic repeated cache query'
 raw=subprocess.run(['/usr/sbin/ioreg','-a','-p','IOUSB','-l','-w','0'],capture_output=True,check=True,timeout=15).stdout
 result=sanitize(raw);result['observed_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
 fd=os.open(H/'current-cache-target.json',os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
 with os.fdopen(fd,'w') as f:json.dump(result,f,ensure_ascii=False,indent=2);f.write('\n')
 print(json.dumps(result,ensure_ascii=False))
