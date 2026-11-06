"""Capture original current kernel GPIO spans and annotated branch targets; no guest."""
from pathlib import Path
from hashlib import sha256
from capstone import Cs,CS_ARCH_ARM64,CS_MODE_LITTLE_ENDIAN
import importlib.util,json
H=Path(__file__).resolve().parent;B=H.parent;R=H.parents[2]
selection=json.loads((H/'current-kernel-symbol-selection.json').read_text());parser=R/selection['parser_source'];assert sha256(parser.read_bytes()).hexdigest()==selection['parser_sha256']
s=importlib.util.spec_from_file_location('gpio209symbols',parser);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);k=m.KernelSymbols();current=R/selection['kernel_source'];assert current.read_bytes()==k.raw
md=Cs(CS_ARCH_ARM64,CS_MODE_LITTLE_ENDIAN);md.detail=True;byoff={r['file_offset']:r['name'] for r in k.rows};outdir=H/'current-kernel-cuts';outdir.mkdir();cuts=[]
for name in ['hw_gpio_set_mode_port','gpio_set_data_bit','gpio_set_data_port','gpio_set_mode_bit','gpio_set_mode_port','gpio_ioctl','gpio_probe']:
 a,z=k.span(name);raw=k.raw[a:z];lines=[]
 for i in md.disasm(raw,a):
  notes=''
  if i.mnemonic in ['bl','b'] and len(i.operands)==1:
   target=i.operands[0].imm
   if target in byoff:notes=' ; '+byoff[target]
  lines.append(f'{i.address:08x} {i.bytes.hex()} {i.mnemonic:8} {i.op_str}'+notes)
 out=outdir/(name+'.txt');out.open('x').write('\n'.join(lines)+'\n');cuts.append(dict(symbol=name,start=a,end_exclusive=z,bytes=z-a,sha256=sha256(raw).hexdigest(),output=str(out.relative_to(R))))
(H/'current-GPIO-function-capture.json').open('x').write(json.dumps(dict(kernel_source=selection['kernel_source'],kernel_sha256=selection['kernel_sha256'],ranges=cuts,span_definition='next greater kallsyms address; not asserted DWARF function size',Sony_code_or_guest_execution=False,root_or_device_operations=0),indent=2)+'\n')
print('data symbols',[(r['name'],hex(r['file_offset']),r['type']) for r in k.rows if ('gpio' in r['name'] or r['name']=='ginfo') and r['type'] not in ['t','T']][:70])
for name in ['hw_gpio_set_mode_port','gpio_set_data_bit']:
 print('\n'+name+'\n'+(outdir/(name+'.txt')).read_text())
