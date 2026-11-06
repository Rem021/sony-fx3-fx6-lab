from pathlib import Path
from io import BytesIO
import json,hashlib,struct
from elftools.elf.elffile import ELFFile
from capstone import Cs,CS_ARCH_ARM64,CS_MODE_LITTLE_ENDIAN
R=Path(__file__).resolve().parent;m=json.loads((R.parent/'original-uipc/ap-projection/full-v4/projection-manifest-full-v4.json').read_text());cs=Cs(CS_ARCH_ARM64,CS_MODE_LITTLE_ENDIAN)
def image(n):
 row=next(x for x in m['members'] if x['guest_path']==n);b=Path(row['local_file']).read_bytes();assert hashlib.sha256(b).hexdigest()==row['sha256'];e=ELFFile(BytesIO(b));ds=e.get_section_by_name('.dynsym');rs=e.get_section_by_name('.rela.plt');plt=e.get_section_by_name('.plt');mp={plt['sh_addr']+32+16*i:ds.get_symbol(v['r_info_sym']).name for i,v in enumerate(rs.iter_relocations())}
 def dis(a,n):
  seg=next(s for s in e.iter_segments() if s['p_type']=='PT_LOAD' and s['p_vaddr']<=a and a+n<=s['p_vaddr']+s['p_filesz']);off=seg['p_offset']+a-seg['p_vaddr'];return [{'va':hex(i.address),'bytes':i.bytes.hex(),'instruction':i.mnemonic+' '+i.op_str,'plt_symbol':mp.get(int(i.op_str[1:],16)) if i.mnemonic=='bl' else None} for i in cs.disasm(b[off:off+n],a)]
 return row,dis
out={}
for key,name,blocks in [('app','appFw.so',[(0x16efb90,32)]),('bt_core','libInfraBluetoothCore.so',[(0x1ff50,0x78)]),('bt','libInfraBluetooth.so',[(0xe990,0x60),(0x12960,0x58),(0x12b28,0x50)]),('ble','libInfraBluetoothLowEnergy.so',[(0x4f520,0x60),(0x4f3a0,0x70),(0x53c20,0xc0),(0x4f0ec,0x50)]),('bt_utils','libBTUtils.so',[(0x3770,0x6c)])]:
 row,dis=image('/usr/lib/'+name);out[key]={'source_sha256':row['sha256'],'blocks':{hex(a):dis(a,n) for a,n in blocks}}
p=R.parents[2]/'sony-firmware-20261024/stage47-runtime-provider-binding/official-files/nflasha3/vmlinux.bin';b=p.read_bytes();assert hashlib.sha256(b).hexdigest()=='da4a66fa29f6b4033233c0d8e7bd9a6f0ffab0cc18d85a44aa6f3830b7c4820c';a=0xffffff80082f6520;off=a-0xffffff8008080000;out['gpio_original_kernel']={'source_sha256':hashlib.sha256(b).hexdigest(),'instructions':[{'va':hex(i.address),'bytes':i.bytes.hex(),'instruction':i.mnemonic+' '+i.op_str} for i in cs.disasm(b[off:off+0x90],a)],'live_AP12_PC':'ffffff80082f6580 hw_gpio_set_mode_port+60, MMIO store, not NULL callback','GPL_reference':'Sony CXD900XX_GPIO(ch)=f101d000+1000*ch; GPIObank5=f1022000; offset34/38 PORTSEL set/clear. Full mapping/profile and register behavior still pending.'}
out['live_chain']={'AP32':'original appinit ENTER then RETURN; AppFw blocked after0127','AP33':'software0127 registration queued; native waiterfree0; later BLE native NULL BTBlog error object crash','AP34':'explicit unavailable BLE dlopenNULL reaches original IM failure (-1), then original appFw asserts infra_wrapper_bluetooth.cpp1804. REJECTED candidate; no successful Bluetooth support or accepted bypass.','AP35':'passive BT errors identify Core line1600, Bluetooth3616/627/203, BLE2595/2655/251 then nil logger418. No GPE draw, no UI.'}
(R/'app-bt-progress-proof.json').write_text(json.dumps(out,indent=2)+'\n');print(R/'app-bt-progress-proof.json')
