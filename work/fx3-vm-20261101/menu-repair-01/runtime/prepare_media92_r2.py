from pathlib import Path
from elftools.elf.elffile import ELFFile
from capstone import *
import json,subprocess,hashlib
R=Path(__file__).resolve().parent;H=R/'helpers';P=R.parent/'original-uipc/ap-projection/regular-files/usr/lib/appFw.so';va=0x2eacd48
with P.open('rb') as f:
 e=ELFFile(f);s=next(s for s in e.iter_segments() if s['p_type']=='PT_LOAD' and s['p_vaddr']<=va and va+4<=s['p_vaddr']+s['p_filesz']);b=s.data()[va-s['p_vaddr']:va-s['p_vaddr']+4]
i=next(Cs(CS_ARCH_ARM64,CS_MODE_LITTLE_ENDIAN).disasm(b,va));assert i.mnemonic=='bl';word=int.from_bytes(b,'little');proof=json.loads((R/'ap92-passive-original-proof.json').read_text());proof['points']['A']=[{'va':hex(va),'bytes':b.hex(),'asm':i.mnemonic+' '+i.op_str,'scope':'original app osal_snd_msg callsite; exact28B insertedslot1/2 filter, source from existingcapid originalmetadata marker; no ABItyped replacement'}];(R/'ap92-r2-original-proof.json').write_text(json.dumps(proof,indent=2)+'\n')
s=(H/'fx3-media-observe-v1.c').read_text();s=s.replace('static struct pool test_pool,pool_D,pool_M;','static struct pool test_pool,pool_D,pool_M,pool_A;')
needle=' case 0xe6dc: stack(r[30],r[29]);break;'
s=s.replace(needle,r''' case 0x22eacd48:{W tag=word(r[1]);if((W)r[0]==0x5503e0&&(tag==0x10002||tag==0x10003)){dprintf(2,"FX3_MEDIA_INSERT_SEND eid=%lu tid=%ld ns=%lu destination=%#x tag=%#x bytes=28 original_native_callsite=2eacd48 original_send_follows=1 synthetic=0 source_in_existing_BOOT_QUEUE_SEND=1\n",eid,syscall(178),stamp(),(W)r[0],tag);raw("NATIVE_INSERT_FULL28",r[1],28);stack(c->pc+4,r[29]);}break;}
'''+needle)
needle='app_base=a->base;sample("app_bound");';assert s.count(needle)==1
s=s.replace(needle,'W native_word=0;if(!peek(a->base+0x2eacd48,&native_word,4)||native_word!=%#xU){dprintf(2,"FX3_MEDIA_BIND_REJECT module=A reason=native_send_word\\n");goto out;}rc=install(&pool_A,a->base+0x2eacd48,%#xU,0x22eacd48,31);if(rc){dprintf(2,"FX3_MEDIA_BIND_REJECT module=A reason=native_send_install result=%%d\\n",rc);goto out;}app_base=a->base;sample("app_bound");'%(word,word))
s=s.replace("id&0x100000?'M':'D',id&0xfffff", "id==0x22eacd48?'A':id&0x100000?'M':'D',id==0x22eacd48?0x2eacd48:id&0xfffff")
(H/'fx3-media-observe-v2.c').write_text(s)
args=json.loads((H/'fx3-media-observe-v1-build.json').read_text())['args'];args=[a.replace('fx3-media-observe-v1','fx3-media-observe-v2') for a in args];p=subprocess.run(args,capture_output=True,text=True);v={'args':args,'exit':p.returncode,'stderr':p.stderr,'source_sha256':hashlib.sha256(s.encode()).hexdigest(),'A_point':proof['points']['A'][0]};print(p.returncode,p.stderr)
if not p.returncode:v['output_sha256']=hashlib.sha256((H/'fx3-media-observe-v2.so').read_bytes()).hexdigest()
(H/'fx3-media-observe-v2-build.json').write_text(json.dumps(v,indent=2)+'\n');raise SystemExit(p.returncode)
