#!/usr/bin/env python3
"""Focused static receipts; no camera code execution or emulation."""
import pathlib,importlib.util,json,hashlib
P=pathlib.Path(__file__).resolve().parent
s=importlib.util.spec_from_file_location('service_static',P/'static_service.py')
m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
c=m.Native('/usr/lib/libsencore.so');sn=m.Native('/usr/bin/sen.elf');pro=m.Native('/usr/lib/libpro00.so')
def block(n,a,z):
 syms={v['va']:v['name'] for v in n.funcs};rows=[]
 for i in n.md.disasm(n.data(a,z-a),a):
  name=''
  if i.mnemonic in ('bl','b'):
   try:t=int(i.op_str[1:],16);name=n.plt.get(t,syms.get(t,''))
   except ValueError:pass
  rows.append({'va':hex(i.address),'bytes':i.bytes.hex(),'instruction':i.mnemonic+' '+i.op_str,'branch_symbol':name})
 return {'path':n.path,'sha256':hashlib.sha256(n.blob).hexdigest(),'start':hex(a),'end':hex(z),'instructions':rows}
r={'method':'original ext2 bytes and static disassembly only',
 'blocks':[block(c,0x10994,0x10d3c),block(c,0xe60c,0xe73c),block(c,0xec9c,0xecd0),
           block(c,0x118ac,0x119e4),block(c,0xd724,0xd908),block(c,0x11a4c,0x11b48),
           block(c,0x12860,0x128a0),block(c,0xeb00,0xebcc),
           block(c,0xdb68,0xdd00),block(sn,0x401f80,0x402100),
           block(sn,0x402b78,0x402bd8),block(pro,0x9a4,0xa6c)],
 'file_helper_callers':[{'pc':hex(i.address),'owner':c.owner(i.address)} for i in c.ins if i.mnemonic=='bl' and i.op_str=='#0x10994'],
 'generic_plugin_inventory':[n for n in m.entries if n.startswith('/usr/lib/libpro')],
 'libSnr_inventory_matches':[n for n in m.entries if 'libsnr' in n.lower()],
 'WBI_write_constant':{'va':'0x54e36','bytes':c.data(0x54e36,4).hex(),'text':c.data(0x54e36,4).decode()},
 'mode_change_script':json.loads((P/'dynamic-extra.json').read_text())['selected']['/usr/bin/change_mode.sh']}
# Record static imports of the local file helper separately from the command
# dispatcher. Absence here is not a claim about all ancestors or runtime state.
r['local_file_helper_branch_symbols']=[i['branch_symbol'] for i in r['blocks'][0]['instructions'] if i['branch_symbol']]
(P/'focused-evidence.json').write_text(json.dumps(r,indent=2)+'\n')
print('file helper branch symbols',r['local_file_helper_branch_symbols'])
for b in r['blocks']:
 if b['start'] in ('0xec9c','0x401f80'):
  print(b['path'],b['start']);print('\n'.join(x['va']+': '+x['instruction']+' '+x['branch_symbol'] for x in b['instructions']))
print('WBI original constant',r['WBI_write_constant'])
