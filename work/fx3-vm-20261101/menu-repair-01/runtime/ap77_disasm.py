exec(open(__file__.replace('ap77_disasm.py','ap75_disasm.py')).read().split('for name,va,size in')[0])
import json
out={};p=P/'appFw.so';b=p.read_bytes()
with p.open('rb') as f:
 e=ELFFile(f)
 for va,n in [(0x16f2220,0x470),(0x16f16bc,0x2dc),(0x16f1a48,0x140),(0x16f1d08,0xb0),(0x16f2098,0x180),(0x16f1998,0xb0)]:
  seg=next(s for s in e.iter_segments() if s['p_type']=='PT_LOAD' and s['p_vaddr']<=va<s['p_vaddr']+s['p_filesz']);off=va-seg['p_vaddr']+seg['p_offset'];ins=[{'va':hex(i.address),'bytes':i.bytes.hex(),'instruction':i.mnemonic+' '+i.op_str} for i in cs.disasm(b[off:off+n],va)];out[hex(va)]=ins;print('\nFUNCTION',hex(va));print('\n'.join(i['va']+' '+i['bytes']+' '+i['instruction'] for i in ins))
(R/'ap77-instruction-review.json').write_text(json.dumps(out,indent=2)+'\n')
