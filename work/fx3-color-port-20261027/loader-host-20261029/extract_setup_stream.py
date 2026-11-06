#!/usr/bin/env python3
"""Bounded ISSetupStream v3 reader, adapted from MIT ISx format source.

Reference: lifenjoiner/ISx, commit 3c4177ddd0519244490ff8e78d380110c8dacdc8.
ISx copyright (c) 2017-2025 YX Hao; MIT notice in reference/LICENSE.
This decodes only InstallShield's public installer obfuscation, not Sony firmware.
No installer, custom action, MSI engine, native Sony code or device is executed.
"""
import hashlib,json,struct,zlib
from pathlib import Path,PureWindowsPath
HERE=Path(__file__).resolve().parent
def main():
    out=HERE/'setup-stream-unpack.json';assert not out.exists()
    source=HERE/'originals/SncToolbox_Setup.exe';raw=source.read_bytes()
    assert hashlib.sha256(raw).hexdigest()=='52feb1eac680e2da5ed17da333e979b9985b293a363596cf2bc1f35764cce1a7'
    base=0x103400;assert raw[base:base+14]==b'ISSetupStream\x00'
    count,kind=struct.unpack_from('<HI',raw,base+14);assert (count,kind)==(3,3)
    target=HERE/'host-extracted';target.mkdir();rows=[];pos=base+46
    nibble=bytes(((x<<4)|(x>>4))&255 for x in range(256))
    for index in range(count):
        header=pos;namebytes,flags=struct.unpack_from('<II',raw,pos);size=struct.unpack_from('<I',raw,pos+10)[0]
        compressed=struct.unpack_from('<H',raw,pos+22)[0]
        assert 0<namebytes<520 and namebytes%2==0 and flags==6 and compressed==1
        name=raw[pos+24:pos+24+namebytes].decode('utf-16-le');path=PureWindowsPath(name)
        assert not path.is_absolute() and len(path.parts)==1 and '..' not in path.parts and '\0' not in name
        pos+=24+namebytes;assert pos+size<=len(raw)
        seed=name.encode('utf8');key=bytes(v^[0x13,0x35,0x86,0x07][j%4] for j,v in enumerate(seed))
        mask=bytes(key[i%len(key)]^255 for i in range(1024));mask64=mask*64
        d=zlib.decompressobj(15);h=hashlib.sha256();output_bytes=0;encoded_hash=hashlib.sha256()
        dest=target/name;assert not dest.exists()
        with dest.open('xb') as f:
            for o in range(0,size,65536):
                part=raw[pos+o:pos+min(o+65536,size)];assert o%1024==0
                encoded_hash.update(part)
                decoded=(int.from_bytes(part.translate(nibble),'little')^int.from_bytes(mask64[:len(part)],'little')).to_bytes(len(part),'little')
                data=d.decompress(decoded,512*1024*1024-output_bytes+1)
                output_bytes+=len(data);assert output_bytes<=512*1024*1024 and not d.unconsumed_tail and not d.unused_data
                h.update(data);f.write(data)
            assert d.eof and not d.unused_data and not d.unconsumed_tail
        rows.append(dict(index=index,name=name,header_offset=header,data_offset=pos,encoded_bytes=size,flags=flags,
            InstallShield_obfuscation='name-derived public ISx byte transform; key index resets every1024 bytes',
            zlib_complete=True,zlib_adler_checked=True,encoded_sha256=encoded_hash.hexdigest(),bytes=output_bytes,sha256=h.hexdigest(),output=str(dest.relative_to(HERE))))
        print(json.dumps(dict(member=name,encoded_bytes=size,output_bytes=output_bytes,zlib_complete=True)),flush=True)
        pos+=size
    assert pos==len(raw)
    result=dict(source_sha256=hashlib.sha256(raw).hexdigest(),stream_offset=base,stream_type=kind,files=count,
        parsed_end=pos,source_bytes=len(raw),members=rows,reference_commit='3c4177ddd0519244490ff8e78d380110c8dacdc8',
        scope='Static host-installer unpack only; this public InstallShield transform is not a VENICE type3 decoder. No native Sony execution, MSI actions, installation, host privilege change or devices.')
    out.write_text(json.dumps(result,indent=2)+'\n')
if __name__=='__main__':main()
