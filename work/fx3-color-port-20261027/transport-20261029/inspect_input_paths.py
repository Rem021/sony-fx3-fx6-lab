#!/usr/bin/env python3
"""Static original update-input libraries; never load or execute Sony code."""
from pathlib import Path
import hashlib,json,subprocess
from elftools.elf.elffile import ELFFile
from capstone import Cs,CS_ARCH_ARM64,CS_MODE_LITTLE_ENDIAN

HERE=Path(__file__).resolve().parent
SOURCE=HERE.parent/'input-20261028/engine-rootfs/2.05'
TARGETS={
 'libupdaterapi.so':['UFPDecryptorModule::exec_write_firm','UFPDecryptorModule::exec_chk_guard','UFPDecryptorModule::UFPDecryptorModule','UFPDecryptorModule::WaitForFirmwareCopyCompletion','UFPDecryptorModule::execute','SignatureVerification::VerifySignature','SignatureVerification::verifyKey','UpdaterManager::SwitchMode','UpdaterManager::ReadyToSwitchMode','UpdaterManager::Initialize','GetUpdater'],
 'libuudfileinputupdaterapi.so':['UUDFileDecryptorModule::execWriteFirm','UUDFileDecryptorModule::UUDFileDecryptorModule','UFPDecryptorModule::exec_write_firm','UFPDecryptorModule::UFPDecryptorModule','UFPDecryptorModule::WaitForFirmwareCopyCompletion','SignatureVerification::VerifySignature','SignatureVerification::verifyKey'],
 'libcryptfileinputupdaterapi.so':['CryptFileInputUpdaterManager::verifyFile','MsDecryptorModule::verifySum'],
 'libfileinputupdaterapi.so':['FileInputUpdaterManager::verifyFile']}

def main():
    HERE.mkdir(exist_ok=True);out=HERE/'disassembly';out.mkdir(exist_ok=True)
    rows=[]
    for name,filters in TARGETS.items():
        p=SOURCE/'usr/lib'/name;raw=p.read_bytes()
        with p.open('rb') as stream:
            e=ELFFile(stream);assert e['e_machine']=='EM_AARCH64'
            symbols=list(e.get_section_by_name('.dynsym').iter_symbols())
            pretty=subprocess.check_output(['c++filt'],input='\n'.join(s.name for s in symbols),text=True).splitlines()
            defs={s['st_value']:n for s,n in zip(symbols,pretty) if s['st_shndx']!='SHN_UNDEF'}
            plt=e.get_section_by_name('.plt');relas=e.get_section_by_name('.rela.plt')
            imports={plt['sh_addr']+32+16*i:pretty[r['r_info_sym']] for i,r in enumerate(relas.iter_relocations())}
            assert plt['sh_size']==32+16*relas.num_relocations()
            labels={**defs,**imports};slices=[]
            for sym,label in zip(symbols,pretty):
                if sym['st_shndx']=='SHN_UNDEF' or not any(f in label for f in filters):continue
                va,n=sym['st_value'],sym['st_size'];assert n
                for segment in e.iter_segments():
                    if segment['p_type']=='PT_LOAD' and segment['p_vaddr']<=va and va+n<=segment['p_vaddr']+segment['p_filesz']:
                        offset=segment['p_offset']+va-segment['p_vaddr'];break
                else:raise AssertionError((label,'no file-backed code'))
                code=raw[offset:offset+n];lines=[];calls=[]
                for ins in Cs(CS_ARCH_ARM64,CS_MODE_LITTLE_ENDIAN).disasm(code,va):
                    annotation=''
                    if ins.mnemonic in ['bl','b'] and ins.op_str.startswith('#'):
                        target=int(ins.op_str[1:],0)
                        if target in labels:
                            annotation=' ; '+labels[target].split('(')[0]
                            calls.append(dict(site=hex(ins.address),target=hex(target),label=labels[target]))
                    lines.append(f'{ins.address:08x} {ins.mnemonic:10} {ins.op_str}{annotation}')
                f=out/(name+'-'+label.split('(')[0].replace('::','-')+'-'+hex(va)[2:]+'.txt')
                f.write_text('\n'.join(lines)+'\n')
                slices.append(dict(label=label,va=hex(va),file_offset=offset,bytes=n,sha256=hashlib.sha256(code).hexdigest(),calls=calls,disassembly=str(f.relative_to(HERE))))
            previous=SOURCE.parent/'2.04/usr/lib'/name
            rows.append(dict(path=str(p),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),identical_to_204=previous.exists() and previous.read_bytes()==raw,functions=slices,
                             rsa_verify_imported=any(n=='RSA_verify' for n in pretty)))
    result=dict(files=rows,scope='Historical original 2.05 update engine static functions, separately byte-compared to 2.04. Does not prove these paths are present or reachable on the current 7.02 body; no Sony executable, device or transport run.')
    (HERE/'input-path-static-results.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'libraries':len(rows),'functions':sum(len(r['functions']) for r in rows),'rsa_imports':[Path(r['path']).name for r in rows if r['rsa_verify_imported']]}))

if __name__=='__main__':main()
