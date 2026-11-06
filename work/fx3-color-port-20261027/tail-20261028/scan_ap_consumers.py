#!/usr/bin/env python3
"""Inventory actual updater/tail candidates across original AP ELF files, without execution."""
from pathlib import Path
from hashlib import sha256,file_digest
import sys,json,io,re
from elftools.elf.elffile import ELFFile
from elftools.elf.sections import SymbolTableSection

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
FS=ROOT/'work/sony-firmware-20261024/stage2/extraction'
TOKENS=[b'AES_cbc_encrypt\0',b'EVP_DigestVerifyFinal\0',b'EVP_DigestVerify\0',b'RSA_verify\0',b'RSA_public_decrypt\0',
        b'iCrypt_VerifyData\0',b'FDAT',b'BODYDATA.DAT',b'AesCbc',b'CBC_Decrypt',b'cbc_decrypt']


def main():
    sys.path.insert(0,str(HERE.parent/'binding-20261028'));from resource_binding_guest import image
    image()
    meta=json.loads((FS/'partition-carve-manifest.json').read_bytes());p=FS/'nflasha15.img'
    pin=next(x['sha256'] for x in meta if x['source_member']=='0700_part_image/dev/nflasha15')
    with p.open('rb') as f:assert file_digest(f,'sha256').hexdigest()==pin
    sys.path.insert(0,str(FS));from read_filesystems import Ext2
    fs=Ext2(p);rows=[];count=0;regular=0;total=0
    for entry in fs.walk():
        if entry['type']!=0x8000:continue
        regular+=1;b=fs.data(entry['inode']);total+=len(b)
        if b[:4]!=b'\x7fELF':continue
        count+=1;found=[]
        for token in TOKENS:
            offsets=[];start=0
            while (o:=b.find(token,start))>=0:offsets.append(hex(o));start=o+len(token)
            if offsets:found.append(dict(token=token.rstrip(b'\0').decode(),file_offsets=offsets))
        if not found:continue
        elf=ELFFile(io.BytesIO(b));symbols=[]
        for sec in elf.iter_sections():
            if isinstance(sec,SymbolTableSection):
                for s in sec.iter_symbols():
                    if re.search(r'AES|EVP_DigestVerify|RSA_|Verify|Decrypt|decrypt|fdat|FDAT',s.name):
                        symbols.append(dict(name=s.name,va=hex(s['st_value']),bytes=s['st_size'],section=s['st_shndx']))
        dynamic=elf.get_section_by_name('.dynamic')
        needed=[t.needed for t in dynamic.iter_tags() if t.entry.d_tag=='DT_NEEDED'] if dynamic else []
        rows.append(dict(path=entry['path'],inode=entry['inode'],bytes=len(b),sha256=sha256(b).hexdigest(),
                         hits=found,needed=needed,relevant_symbols=symbols))
        print(entry['path'],','.join(r['token'] for r in found),flush=True)
    result=dict(status='PASS_ORIGINAL_AP_ELF_CONSUMER_CANDIDATE_INVENTORY',partition_sha256=pin,
                regular_files_read=regular,bytes_read=total,elf_files=count,candidates=rows,
                scope='All regular AP filesystem files read without mounts. Presence/imports of crypto or FDAT identifiers are candidates, not proof of the update verification call chain. Protected/stripped code or other processors may not expose these names.')
    (HERE/'ap-consumer-candidates.json').write_text(json.dumps(result,indent=2)+'\n')
    print(result['status'],'ELF',count,'candidates',len(rows),flush=True)


if __name__=='__main__':main()
