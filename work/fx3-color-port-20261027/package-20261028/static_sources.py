#!/usr/bin/env python3
"""Pin original updater helpers and explicit cross-library/PLT boundaries."""
from pathlib import Path
from hashlib import sha256
import json,io,re
from elftools.elf.elffile import ELFFile
from elftools.elf.sections import SymbolTableSection
from capstone import Cs,CS_ARCH_ARM64,CS_MODE_ARM

HERE=Path(__file__).resolve().parent


def main():
    inventory=json.loads((HERE/'verifier-library-inventory.json').read_bytes());sources=[]
    out=HERE/'disassembly';out.mkdir(exist_ok=True)
    selected={'libcryptfileinputupdaterapi.so':r'searchFDAT|verifyFile|CrcChecker',
              'libupdatercorecommon.so':r'DecryptorModule.*(decryptEv|calSumEv|getHd|verifySumEv|executeEv)',
              'libupdatertalk.so':r'Dec_Scramble',
              'libInfraCryptCore.so':r'^icc_verifyDataCore$'}
    for row in inventory['libraries']:
        name=Path(row['output']).name
        if name not in selected:continue
        b=(HERE/row['output']).read_bytes();assert sha256(b).hexdigest()==row['sha256']
        e=ELFFile(io.BytesIO(b));plt=e.get_section_by_name('.plt');rel=e.get_section_by_name('.rela.plt');dyn=e.get_section_by_name('.dynsym')
        targets={plt['sh_addr']+32+i*16:dyn.get_symbol(r['r_info_sym']).name for i,r in enumerate(rel.iter_relocations())}
        seen=set()
        for s in row['symbols']:
            a=int(s['va'],16);n=s['bytes']
            if not (n and s['type']=='STT_FUNC' and re.search(selected[name],s['name'])) or (a,n) in seen:continue
            seen.add((a,n));seg=next(s for s in e.iter_segments() if s['p_type']=='PT_LOAD' and s['p_vaddr']<=a and a+n<=s['p_vaddr']+s['p_filesz'])
            off=a-seg['p_vaddr']+seg['p_offset'];raw=b[off:off+n];calls=[];lines=[]
            for i in Cs(CS_ARCH_ARM64,CS_MODE_ARM).disasm(raw,a):
                label=''
                if i.mnemonic in ['b','bl'] and i.op_str.startswith('#'):
                    target=int(i.op_str[1:],16);label=targets.get(target,'')
                    if label:calls.append(dict(caller=hex(i.address),plt=hex(target),symbol=label))
                lines.append(f'{i.address:08x}: {i.mnemonic} {i.op_str}'+(' ; '+label if label else ''))
            dest=out/f'{name}-{a:08x}-{a+n:08x}.txt';dest.write_text('\n'.join(lines)+'\n')
            sources.append(dict(library=row['output'],library_sha256=row['sha256'],symbol=s['name'],va=hex(a),
                                file_offset=hex(off),bytes=n,sha256=sha256(raw).hexdigest(),
                                disassembly=str(dest.relative_to(HERE)),plt_calls=calls))
    result=dict(status='PASS_PINNED_UPDATER_HELPERS_AND_BOUNDARIES',source_spans=sources,
                exclusions=[dict(library='libCryptoController.so',reason='Symbol namespace is DefInfraVericLiveStreaming. Crypto naming alone does not establish firmware update verification.'),
                            dict(library='libInfraCryptCore.so',reason='CodeMeter protection and generic verification entry are present; no FDAT tail input or call path to this verifier has been established. Mere presence is not proof of a manufacturer signature gate.')],
                remaining='Locate the actual fourth-generation CBC/256-byte-tail consumer before claiming re-encryption plus checksums produces an accepted update. Raw WBI string candidates are not function or scene identification.')
    (HERE/'static-source-results.json').write_text(json.dumps(result,indent=2)+'\n')
    print(result['status'],'source slices',len(sources))


if __name__=='__main__':main()
