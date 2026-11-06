from pathlib import Path
import struct,sys
from capstone import *
from elftools.elf.elffile import ELFFile
ROOT=Path(__file__).resolve().parents[5]
AP=ROOT/'work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/appFw.so'
CP=ROOT/'work/sony-firmware-20261024/stage2/extraction/files/nflasha8/cpapp-b.bin'
a=AP.read_bytes();b=CP.read_bytes();e=ELFFile(AP.open('rb'));segs=[dict(s.header) for s in e.iter_segments() if s['p_type']=='PT_LOAD']
def read(v,n,cp=False):
 if cp:return b[v-0x108000:v-0x108000+n]
 s=next(s for s in segs if s['p_vaddr']<=v<s['p_vaddr']+s['p_filesz']);o=s['p_offset']+v-s['p_vaddr'];return a[o:o+n]
def dis(v,n,cp=False):
 c=Cs(CS_ARCH_ARM,CS_MODE_THUMB) if cp else Cs(CS_ARCH_ARM64,CS_MODE_ARM)
 return [{'va':hex(i.address),'bytes':i.bytes.hex(),'instruction':i.mnemonic+' '+i.op_str} for i in c.disasm(read(v,n,cp),v)]
def refs(data,val):
 out=[];p=0;needle=struct.pack('<I',val)
 while (p:=data.find(needle,p))>=0:
  if p%4==0:out.append(p)
  p+=1
 return out
if __name__=='__main__':
 if len(sys.argv)>1:
  for i in dis(int(sys.argv[1],16),int(sys.argv[2],16),'cp' in sys.argv):print(i['va'],i['instruction'])
 else:
  for name in ['VdfInputCmdSetYuvLayoutOption','VdfInputCmdUpdateYuv','VdfInputSetOsdLayout','VdfOsdSetOutputProcessor','VdfYuvLayoutSender']:
   o=b.find(name.encode());start=b.rfind(b'\0',0,o)+1;end=b.index(b'\0',o);print(b[start:end],hex(start+0x108000))
   for r in refs(b,start+0x108000):
    ti=r-4+0x108000
    for vr in refs(b,ti):
     vt=vr+4+0x108000; print('vt',hex(vt),'slots',[hex(x) for x in struct.unpack('<24I',read(vt,96,True))])
  c=Cs(CS_ARCH_ARM64,CS_MODE_ARM);ins=list(c.disasm(read(0x2de4000,0x16000),0x2de4000))
  for j,i in enumerate(ins[:-1]):
   if i.mnemonic=='adrp' and ins[j+1].mnemonic=='add':
    try:
     pg=int(i.op_str.split('#')[1],16);n=ins[j+1];v=pg+int(n.op_str.split('#')[1],16);s=read(v,300).split(b'\0')[0].decode()
     if any(x in s for x in ['vdf_update_yuv','vdf_set_osd_layout','vdf_set_yuv_layout_option']):print(hex(i.address),hex(v),s)
    except (ValueError,StopIteration,UnicodeError):pass
