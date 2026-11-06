#!/usr/bin/env python3
"""Additional selected regular-file reads from extracted images, never execute payloads."""
import pathlib,hashlib,json,sys
BASE=pathlib.Path(__file__).resolve().parent
sys.path.insert(0,str(BASE))
from read_filesystems import Ext2,FAT16
SELECTIONS={'15':['/lib/libJiritsu.so','/lib/libOnDemandLoader.so','/lib/libInfraUsbCmn.so','/kmod/codec_drv.ko','/scenario/CAMERA_SCN_MOVIE_REC_START.so','/codec/vcd_firmware.bin','/codec/vcd_firmware_imola2_fpga.bin','/codec/vcd_firmware_imola2.bin','/bin/up.sh','/bin/common.src','/bin/compat_firmware.sh','/bin/sen.elf','/bin/bootin.elf','/lib/libmpr.so','/scenario/MPR_SCN_EXEC_FACTORY_MODE.so','/scenario/MPR_SCN_EXEC_WIFI_TEST.so'],'7':['/lib/ld-2.25.so','/sbin/init','/sbin/init2','/sbin/initrc/setup_rootfs','/root/chassis','/sbin/initrc/fstab','/sbin/initrc/fstab.root','/sbin/initrc/setup_console'],'3':['/av-cam.bin']}
def main():
 rows=[]
 for part,names in SELECTIONS.items():
  fs=FAT16(BASE/f'nflasha{part}.img') if part=='3' else Ext2(BASE/f'nflasha{part}.img');files={e['path']:e for e in fs.walk()}
  for name in names:
   e=files[name];assert e['type']==0x8000;b=fs.data(e['inode']) if 'inode' in e else fs.data(e['cluster'],e['size']);assert len(b)==e['size'];dest=BASE/'files'/f'nflasha{part}'/name.lstrip('/');assert dest.resolve().is_relative_to((BASE/'files').resolve());dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(b);rows.append({**e,'extracted_path':str(dest),'sha256':hashlib.sha256(b).hexdigest(),'first32_hex':b[:32].hex()})
 (BASE/'supplementary-extracted-manifest.json').write_text(json.dumps(rows,indent=2));print(json.dumps(rows,indent=2))
if __name__=='__main__':main()
