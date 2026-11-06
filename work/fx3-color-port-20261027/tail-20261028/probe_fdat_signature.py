#!/usr/bin/env python3
"""Test original FDAT trailers with snapshot public RSA parameters only.

No private key reading, key derivation, ROM/MMIO access, signing, modified
firmware output, Sony code execution, or device I/O.
"""
from pathlib import Path
from hashlib import sha256,sha512,file_digest
import json,struct
from wbi_page_table_candidates import Snapshot,HERE,ROOT

SHA512_DER_PREFIX=bytes.fromhex('3051300d060960864801650304020305000440')


def main():
    s=Snapshot();identity=json.loads((HERE/'skd-snapshot-code-results.json').read_bytes())
    root=int(identity['root_physical_address'],16);base=int(identity['library_base_candidate'],16)
    exponent_raw=s.virtual(root,base+0x20d968,3);exponent=int.from_bytes(exponent_raw,'big');assert exponent==65537
    keys=[]
    for mode in range(5):
        raw=s.virtual(root,base+0x20d460+mode*257,257);n=int.from_bytes(raw,'big')
        assert raw[0]==0 and n.bit_length()==2048
        keys.append((mode,n,dict(mode=mode,modulus_bits=n.bit_length(),modulus_sha256=sha256(raw).hexdigest(),public_exponent=exponent)))
    s.close()
    fw=ROOT/'work/sony-firmware-20261024'
    current=json.loads((fw/'fx3-7.02-offline-manifest.json').read_bytes())
    paths=[(fw/'fx3-7.02-BODYDATA.DAT',current['source_sha256'])]
    for path in sorted((HERE/'interim-members/mspack').glob('*.dat')):
        paths.append((path,json.loads(path.with_suffix(path.suffix+'.receipt.json').read_bytes())['sha256']))
    results=[]
    for path,expected in paths:
        with path.open('rb') as f:
            assert file_digest(f,'sha256').hexdigest()==expected
            pos=8;offset=None;length=None
            while pos<path.stat().st_size:
                f.seek(pos);n,kind=struct.unpack('>I4s',f.read(8))
                assert pos+8+n<=path.stat().st_size
                if kind==b'FDAT':offset=pos+8;length=n;break
                pos+=8+n
            assert offset is not None and length%1024==272
            body_length=length-272
            f.seek(offset+body_length);iv=f.read(16);signature=f.read(256);assert len(signature)==256
            sig=int.from_bytes(signature,'big');trials=[];digests=[]
            for mode,modulus,keymeta in keys:
                encoded=pow(sig,exponent,modulus).to_bytes(256,'big')
                end=encoded.find(b'\0',2) if encoded[:2]==b'\0\1' else -1
                padding_ok=end>=10 and encoded[2:end]==b'\xff'*(end-2)
                message=encoded[end+1:] if padding_ok else b''
                sha512_info=padding_ok and len(message)==len(SHA512_DER_PREFIX)+64 and message.startswith(SHA512_DER_PREFIX)
                trials.append(dict(key_mode=mode,signature_less_than_modulus=sig<modulus,pkcs1_v1_5_padding_valid=padding_ok,
                    sha512_digest_info_valid=sha512_info,decoded_block_sha256=sha256(encoded).hexdigest()))
                if sha512_info:digests.append((mode,message[-64:]))
            matches=[];candidate_hashes={}
            if digests:
                contexts={'ciphertext_body':sha512(),'iv_then_ciphertext_body':sha512(iv)}
                f.seek(0);prefix=f.read(offset);contexts['ufu_prefix_ciphertext_iv']=sha512(prefix)
                f.seek(offset);remaining=body_length
                while remaining:
                    data=f.read(min(8*1024*1024,remaining));assert data;remaining-=len(data)
                    for context in contexts.values():context.update(data)
                contexts['ciphertext_body_then_iv']=contexts['ciphertext_body'].copy();contexts['ciphertext_body_then_iv'].update(iv)
                contexts['ufu_prefix_ciphertext_iv'].update(iv)
                candidate_hashes={name:ctx.digest() for name,ctx in contexts.items()}
                if path.name=='fx3-7.02-BODYDATA.DAT':
                    with (fw/'fx3-7.02-decrypted.fdat').open('rb') as plain:
                        candidate_hashes['plaintext_fdat']=file_digest(plain,'sha512').digest()
                        plain.seek(current['firmware_tar_offset']);h=sha512()
                        while data:=plain.read(8*1024*1024):h.update(data)
                        candidate_hashes['plaintext_firmware_tar']=h.digest()
                for mode,digest in digests:
                    for name,value in candidate_hashes.items():
                        if digest==value:matches.append(dict(key_mode=mode,coverage=name,sha512=digest.hex()))
            row=dict(name=path.name,source_sha256=expected,fdat_offset=offset,fdat_bytes=length,
                signature_sha256=sha256(signature).hexdigest(),public_key_trials=trials,coverage_matches=matches,
                candidate_hashes={name:value.hex() for name,value in candidate_hashes.items()})
            results.append(row);print(path.name,'valid_DigestInfo_modes',[m for m,_ in digests],'coverage_matches',[(m['key_mode'],m['coverage']) for m in matches],flush=True)
    result=dict(status='ORIGINAL_FDAT_PUBLIC_RSA_TRAILER_PROBES',public_keys=[meta for _,_,meta in keys],
        snapshot_source_sha256=identity['source_sha256'],packages=results,
        scope='Public RSA modulus/exponent, original signature bytes, and hash comparisons only. No private parameters read or derived, no signatures generated, no modified full firmware emitted. Even a valid original signature does not establish signing capability, full updater admission, rollback, recovery or boot behavior.')
    (HERE/'fdat-public-rsa-probe-results.json').write_text(json.dumps(result,indent=2)+'\n')


if __name__=='__main__':main()
