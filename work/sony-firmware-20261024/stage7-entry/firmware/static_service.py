#!/usr/bin/env python3
"""Read-only ext2/ELF static analysis. Never load/execute firmware code."""
import sys, pathlib, json, hashlib, importlib.util, io, re, posixpath
sys.dont_write_bytecode=True
from elftools.elf.elffile import ELFFile
from capstone import Cs,CS_ARCH_ARM64,CS_MODE_ARM
OUT=pathlib.Path(__file__).resolve().parent
SRC=OUT.parents[1]/'stage2/extraction'
sp=importlib.util.spec_from_file_location('ext2',SRC/'read_filesystems.py')
mod=importlib.util.module_from_spec(sp);sp.loader.exec_module(mod)
fs={p:mod.Ext2(SRC/f'nflasha{p}.img') for p in ('7','15')}
entries={}
for p in fs:
 for e in json.loads((SRC/f'nflasha{p}-files.json').read_text())['files']:
  entries[('/usr' if p=='15' else '')+e['path']]=(p,e)
def read(name,seen=()):
 assert name not in seen
 p,e=entries[name];b=fs[p].data(e['inode'])
 if e['type']==0xa000:
  t=b.decode();return read(posixpath.normpath(t if t.startswith('/') else posixpath.join(posixpath.dirname(name),t)),seen+(name,))
 assert e['type']==0x8000
 return b,name
class Native:
 def __init__(self,name):
  self.blob,self.path=read(name);self.e=ELFFile(io.BytesIO(self.blob));self.md=Cs(CS_ARCH_ARM64,CS_MODE_ARM);self.md.skipdata=True
  sec=self.e.get_section_by_name('.dynsym')
  self.syms=[{'name':s.name,'va':s['st_value'],'size':s['st_size'],'defined':s['st_shndx']!='SHN_UNDEF','type':s['st_info']['type']} for s in sec.iter_symbols() if s.name]
  self.funcs=[s for s in self.syms if s['defined'] and s['type']=='STT_FUNC' and s['size']]
  plt=self.e.get_section_by_name('.plt');rel=self.e.get_section_by_name('.rela.plt')
  self.plt={plt['sh_addr']+32+16*i:sec.get_symbol(r['r_info_sym']).name for i,r in enumerate(rel.iter_relocations())} if plt and rel else {}
  self.ins=[]
  for t in self.e.iter_sections():
   if t['sh_flags']&4:self.ins.extend(self.md.disasm(t.data(),t['sh_addr']))
 def owner(self,pc):return next((s['name'] for s in self.funcs if s['va']<=pc<s['va']+s['size']),None)
 def va(self,o):
  for s in self.e.iter_segments():
   if s['p_type']=='PT_LOAD' and s['p_offset']<=o<s['p_offset']+s['p_filesz']:return s['p_vaddr']+o-s['p_offset']
  return None
 def data(self,a,n):
  for s in self.e.iter_segments():
   if s['p_type']=='PT_LOAD' and s['p_vaddr']<=a and a+n<=s['p_vaddr']+s['p_filesz']:
    o=s['p_offset']+a-s['p_vaddr'];return self.blob[o:o+n]
  raise ValueError(hex(a))
 def info(self):
  dyn=self.e.get_section_by_name('.dynamic');needed=[t.needed for t in dyn.iter_tags() if t.entry.d_tag=='DT_NEEDED']
  calls=[]
  terms=('dlopen','dlsym','system','exec','open','fopen','read','write','ioctl','send','recv','connect','socket','uipc','testcmd','repair','reboot','mount','unlink','chmod','rename')
  for idx,i in enumerate(self.ins):
   if i.mnemonic not in ('bl','b'):continue
   try:target=int(i.op_str[1:],16)
   except ValueError:continue
   n=self.plt.get(target,'')
   if any(t in n.lower() for t in terms):calls.append({'pc':hex(i.address),'target':hex(target),'name':n,'owner':self.owner(i.address),'context':[f'{j.address:x}: {j.mnemonic} {j.op_str}' for j in self.ins[max(0,idx-6):idx+4]]})
  strings=[]
  for m in re.finditer(rb'[ -~]{5,}',self.blob):
   s=m.group().decode()
   if any(t.lower() in s.lower() for t in ['.so','/dev/','/proc/','/setting/','/boot/','/usr/','smode','senser','repair','file_','file ','appfw','app.elf','bootin','wbi','UIPC','read_file','write_file','sender']):
    strings.append({'offset':hex(m.start()),'va':hex(self.va(m.start())) if self.va(m.start()) is not None else None,'text':s})
  # Bounded ADRP+ADD textual xrefs are observations, not a full def-use analysis.
  targets={int(s['va'],16):s['text'] for s in strings if s['va']};refs=[];regs={}
  for i in self.ins:
   if i.mnemonic=='adrp':
    a=re.fullmatch(r'(x\d+), #0x([0-9a-f]+)',i.op_str)
    if a:regs[a[1]]=(int(a[2],16),i.address)
   elif i.mnemonic=='add':
    a=re.fullmatch(r'(x\d+), (x\d+), #0x([0-9a-f]+)',i.op_str)
    if a and a[2] in regs and i.address-regs[a[2]][1]<=24:
     v=regs[a[2]][0]+int(a[3],16)
     if v in targets:refs.append({'pc':hex(i.address),'va':hex(v),'string':targets[v],'owner':self.owner(i.address)})
  return {'path':self.path,'bytes':len(self.blob),'sha256':hashlib.sha256(self.blob).hexdigest(),'needed':needed,'symbols':self.syms,'interesting_calls':calls,'strings':strings,'string_xrefs':refs}
def main():
 names=['/usr/bin/sen.elf','/usr/bin/bootin.elf','/usr/lib/libsencore.so','/usr/lib/libpro00.so','/usr/lib/libtestcmd.so','/usr/lib/libtestcmd_scn.so']
 result={n:Native(n).info() for n in names}
 scripts={}
 for n in ['/sbin/init','/sbin/init2','/sbin/initrc/setup_rootfs','/sbin/initrc/insmod_drv1','/sbin/initrc/insmod_drv2','/sbin/initrc/setup_nflash','/sbin/initrc/setup_shielding','/sbin/initrc/fstab','/sbin/initrc/fstab.ext']:
  b,path=read(n);scripts[n]={'path':path,'sha256':hashlib.sha256(b).hexdigest(),'text':b.decode()}
 output={'method':'mmap ACCESS_READ ext2 and static ELF parsing/disassembly only; no firmware execution/emulation/device access','files':result,'scripts':scripts,'libpro_inventory':[n for n in entries if re.search(r'/libpro[0-9A-Fa-f]+\.so$',n)]}
 (OUT/'runtime-static.json').write_text(json.dumps(output,indent=2)+'\n')
 for n,r in result.items():
  print('\nFILE',n,r['sha256'],'needed',r['needed'])
  print('SYMS',[s for s in r['symbols'] if s['defined'] and any(t in s['name'].lower() for t in ['sen','pro','file','repair','exec','init','mode'])])
  print('REFS',r['string_xrefs'])
  print('CALLS',[(c['pc'],c['name'],c['owner']) for c in r['interesting_calls']][:90])
 print('SCRIPTS',scripts)
if __name__=='__main__':main()
