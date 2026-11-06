from pathlib import Path
import struct,json,hashlib,time
PHYS=0x41d400000

def capture(qmp,run,label):
 run=Path(run);header=run/('file100-'+label+'-header.bin');qmp('human-monitor-command',{'command-line':f'pmemsave {hex(PHYS)} 0x1000 "{header}"'});b=header.read_bytes();v=struct.unpack_from('<8s8Q',b);magic,seq,gen,n,fnv,error,control,restore,restore_seen=v
 result={'label':label,'native_path':'/setting/Backup.bin','header_path':str(header),'source':'guest O_RDONLY two complete equal reads; observer reservation only','sequence':seq,'generation':gen,'bytes':n,'source_read_error':error,'shutdown_control':control,'restore_status':restore,'restore_seen':restore_seen,'host_monotonic':time.monotonic(),'valid':False}
 if magic==b'F100FILE' and seq and not seq%2 and gen and 0<n<=0x230000 and not error:
  p=run/('Backup-native-file-'+label+'.bin');qmp('human-monitor-command',{'command-line':f'pmemsave {hex(PHYS+4096)} {hex(n)} "{p}"'});data=p.read_bytes();h=14695981039346656037
  for c in data:h=((h^c)*1099511628211)&0xffffffffffffffff
  result.update({'path':str(p),'sha256':hashlib.sha256(data).hexdigest(),'fnv64':hex(h),'guest_fnv64':hex(fnv),'valid':len(data)==n and h==fnv,'read_only_file_snapshot_not_RAM_Backup_substitution':True})
 (run/('file100-'+label+'.json')).write_text(json.dumps(result,indent=2)+'\n');return result
