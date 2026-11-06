#!/usr/bin/env python3
"""Decode bytes/table/predicates only; no instruction emulation or guest calls."""

import plistlib, subprocess
assert plistlib.loads(subprocess.check_output(['/usr/sbin/diskutil','info','-plist','/Volumes/KAFU2T']))['VolumeUUID']=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
from pathlib import Path
import json,struct
HERE=Path(__file__).resolve().parent;ROOT=next(p for p in HERE.parents if p.name=='Mac')
def sections(data):
 off=struct.unpack_from('<Q',data,40)[0];size,num,si=struct.unpack_from('<HHH',data,58);ss=[struct.unpack_from('<IIQQQQIIQQ',data,off+i*size) for i in range(num)];st=ss[si];strings=data[st[4]:st[4]+st[5]]
 return {strings[x[0]:strings.find(b'\0',x[0])].decode():x for x in ss}
def main():
 p=ROOT/'work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/full-v4/regular-files/usr/kmod/grm_ma.ko';d=p.read_bytes();sec=sections(d);s=sec['.rodata'];table=d[s[4]:s[4]+13];jumps={str(i+1):hex(0xe8+struct.unpack('b',bytes([v]))[0]*4) for i,v in enumerate(table)};assert jumps['1']=='0x118' and jumps['3']=='0x138'
 (HERE/'MA-DISPATCH-TABLE.json').write_text(json.dumps(dict(section='.rodata',file_offset=s[4],bytes=table.hex(),formula='text+0xe8 + sign_extend(table[command-1])*4',targets=jumps,command1='0x118 -> CALL relocation ma_dmm_open_impl',command3='0x138 -> CALL relocation ma_create_msp_impl'),indent=2)+'\n')
 d=(HERE/'libObj.so').read_bytes();s=sections(d)['.text'];checked=[]
 for at,expected in [(0x103368,0x924006e0),(0x10336c,0xf110031f),(0x103370,0xfa408800),(0xf9794,0x52800062),(0xf97bc,0x97fd74b1)]:
  o=s[4]+at-s[3];word=struct.unpack_from('<I',d,o)[0];assert word==expected;checked.append(dict(VA=hex(at),file_offset=hex(o),instruction_word=hex(word),matched=True))
 checks={'UI_physical_4_aligned':0x41dc00000&3==0,'UI_bytes_gt_0x400':0x10000>0x400,'UI_in_first_f96f4_band':0x41dc00000-0x400000000<=0x1fffffffe,'native_file_flags_match_compiled_uc_mask':bool(0x101002&0x101000),'mmap_phys_end_below_48bits':(0x41dc00000+0x10000)<1<<48,'size_0x400_fails_explicit_gate':not(0x400>0x400),'misaligned_address_fails_explicit_gate':(0x41dc00002&3)!=0};assert all(checks.values())
 (HERE/'STATIC-PREDICATE-CHECKS.json').write_text(json.dumps(dict(scope='Python integer arithmetic of decoded original predicates only; no guest execution, mock native call, or allocator success proof',checked_original_words=checked,checks=checks,count=len(checks)),indent=2)+'\n');print('decoded MA1/MA3; checked original words',len(checked),'and arithmetic predicates',len(checks))
if __name__=='__main__':main()
