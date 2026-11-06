exec(open(__file__.replace('check_ap75_hooks.py','ap75_disasm.py')).read().split('for name,va,size in')[0])
import json,hashlib
out=[]
for name,va,expected in [('appFw.so',0x176fb4c,'fd7bbaa9fd030091f51300f9f50300aa'),('libObj.so',0x176ab0,'fd7bbba9fd030091f35301a9f30300aa'),('libObj.so',0x100c48,'fd7bbda9fd030091f30b00f9f30300aa'),('appFw.so',0x16ee6f8,'fd7bb8a9fd030091f35301a9f30300aa')]:
 p=P/name;b=p.read_bytes()
 with p.open('rb') as f:
  e=ELFFile(f);seg=next(s for s in e.iter_segments() if s['p_type']=='PT_LOAD' and s['p_vaddr']<=va<s['p_vaddr']+s['p_filesz']);off=va-seg['p_vaddr']+seg['p_offset']
 raw=b[off:off+16];assert raw.hex()==expected;ins=list(cs.disasm(raw,va));assert len(ins)==4;assert all(i.mnemonic in ['stp','mov','str'] for i in ins)
 out.append({'file':str(p),'file_sha256':hashlib.sha256(b).hexdigest(),'entry':hex(va),'bytes':raw.hex(),'instructions':[i.mnemonic+' '+i.op_str for i in ins],'pc_relative':False,'trampoline':'replay16bytes then absolute BR to original+16; original ABI and result forwarded'})
(R/'ap75-hook-instruction-review.json').write_text(json.dumps({'hooks':out,'IDeq':{'symbol':'_ZNK2ux4core2IDeqES1_','PLT':'0x1591aa0','GOT':'0x47cc0e0','callreturn':'0x176fb7c','return_test':'low8==0 exits at176fb80'},'getTimerInfo':{'symbol':'_ZN2ux6wgtsys10WidgetBase12getTimerInfoERKNS_4core2IDERNS0_9TimerTypeERjRS3_Rm','PLT':'0x1592be0','GOT':'0x47cc980','arguments':'this, IDref, TimerTyperef, uintref, IDref, ulongref','return_test':'low8==0 exits at176fbc0'},'config_call':'2191df4 BL16ee6f8 returns2191df8; wrapper also captures other callers'},indent=2)+'\n');print('4 exact prefixes verified; no PC-relative stolen instructions')
