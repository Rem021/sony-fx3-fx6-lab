exec(open(__file__.replace('ap75_symbols.py','ap75_disasm.py')).read().split('for name,va,size in')[0])
p=P/'appFw.so';b=p.read_bytes()
with p.open('rb') as f:
 e=ELFFile(f)
 def data(va,n):
  s=next(s for s in e.iter_segments() if s['p_type']=='PT_LOAD' and s['p_vaddr']<=va<s['p_vaddr']+s['p_filesz']);return b[va-s['p_vaddr']+s['p_offset']:va-s['p_vaddr']+s['p_offset']+n]
 for va in [0x1591aa0,0x1592be0,0x16ee6f8]:
  ins=list(cs.disasm(data(va,16),va));print(hex(va),[(i.bytes.hex(),i.mnemonic,i.op_str) for i in ins])
  if ins[0].mnemonic=='adrp':
   page=int(ins[0].op_str.split('#')[1],16);off=int(ins[1].op_str.split('#')[1].split(']')[0],16);got=page+off
   for sec in e.iter_sections():
    if sec['sh_type'] in ['SHT_RELA','SHT_REL']:
     for r in sec.iter_relocations():
      if r['r_offset']==got:print('GOT',hex(got),e.get_section(sec['sh_link']).get_symbol(r['r_info_sym']).name)
