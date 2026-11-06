#!/usr/bin/env python3
"""Verify original FDAT signatures with the official updater's public PEM key.

Only public RSA arithmetic and SHA-256. No signing, private key parameters,
ROM/MMIO reads, Sony code execution, modified package output or device access.
"""
from pathlib import Path
from hashlib import sha256,sha1,file_digest
import base64,json,struct

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
PREV=HERE.parent/'tail-20261028'
DER_SHA256_PREFIX=bytes.fromhex('3031300d060960864801650304020105000420')


def tlv(data,offset=0):
    assert 0<=offset<len(data);tag=data[offset];offset+=1
    length=data[offset];offset+=1
    if length&128:
        count=length&127;assert 1<=count<=4 and offset+count<=len(data)
        length=int.from_bytes(data[offset:offset+count],'big');offset+=count
    assert offset+length<=len(data)
    return tag,data[offset:offset+length],offset+length


def public_pem(data):
    lines=data.splitlines();assert lines[0]==b'-----BEGIN PUBLIC KEY-----' and lines[-1]==b'-----END PUBLIC KEY-----'
    der=base64.b64decode(b''.join(lines[1:-1]),validate=True);tag,sequence,end=tlv(der);assert tag==0x30 and end==len(der)
    tag,algorithm,pos=tlv(sequence);assert tag==0x30 and algorithm==bytes.fromhex('06092a864886f70d0101010500')
    tag,bits,end=tlv(sequence,pos);assert tag==3 and end==len(sequence) and bits[0]==0
    tag,pair,end=tlv(bits[1:]);assert tag==0x30 and end==len(bits)-1
    tag,modulus,pos=tlv(pair);assert tag==2 and modulus[0]==0
    tag,exponent,end=tlv(pair,pos);assert tag==2 and end==len(pair)
    n=int.from_bytes(modulus,'big');e=int.from_bytes(exponent,'big');assert n.bit_length()==2048 and e==65537
    return n,e,sha256(der).hexdigest()


def main():
    keypath=HERE/'engine-rootfs/2.05/etc/VerificationKey.pem';key=keypath.read_bytes()
    assert key==(HERE/'engine-rootfs/2.04/etc/VerificationKey.pem').read_bytes()
    modulus,exponent,der_digest=public_pem(key)
    key_hash=sha1(key).digest();zero_index=key_hash.find(b'\0')
    current=json.loads((ROOT/'work/sony-firmware-20261024/fx3-7.02-offline-manifest.json').read_bytes())
    paths=[(ROOT/'work/sony-firmware-20261024/fx3-7.02-BODYDATA.DAT',current['source_sha256'])]
    for path in sorted((PREV/'interim-members/mspack').glob('*.dat')):
        paths.append((path,json.loads(path.with_suffix(path.suffix+'.receipt.json').read_bytes())['sha256']))
    outputs=HERE/'original-signatures';outputs.mkdir(exist_ok=True);results=[]
    for path,pin in paths:
        with path.open('rb') as f:
            assert file_digest(f,'sha256').hexdigest()==pin
            pos=8
            while True:
                f.seek(pos);length,kind=struct.unpack('>I4s',f.read(8))
                assert pos+8+length<=path.stat().st_size
                if kind==b'FDAT':break
                pos+=8+length
            start=pos+8;body_length=length-272;assert body_length>0 and body_length%1024==0
            f.seek(start+body_length);iv=f.read(16);signature=f.read(256);assert len(signature)==256
            sig=int.from_bytes(signature,'big');encoded=pow(sig,exponent,modulus).to_bytes(256,'big')
            end=encoded.find(b'\0',2) if encoded[:2]==b'\0\1' else -1
            padding_ok=end>=10 and encoded[2:end]==b'\xff'*(end-2)
            message=encoded[end+1:] if padding_ok else b''
            digest_info_ok=padding_ok and len(message)==len(DER_SHA256_PREFIX)+32 and message.startswith(DER_SHA256_PREFIX)
            expected=message[-32:] if digest_info_ok else None
            names={'ciphertext_body':sha256(),'iv_then_ciphertext_body':sha256(iv)}
            f.seek(0);prefix=f.read(start);names['ufu_prefix_ciphertext_iv']=sha256(prefix)
            mutations={0:sha256(),min(body_length-1,12345678):sha256(),body_length-1:sha256()}
            f.seek(start);done=0
            while done<body_length:
                data=f.read(min(8*1024*1024,body_length-done));assert data
                for context in names.values():context.update(data)
                for offset,context in mutations.items():
                    if done<=offset<done+len(data):
                        changed=bytearray(data);changed[offset-done]^=1;context.update(changed)
                    else:context.update(data)
                done+=len(data)
            names['ciphertext_body_then_iv']=names['ciphertext_body'].copy();names['ciphertext_body_then_iv'].update(iv)
            names['ufu_prefix_ciphertext_iv'].update(iv)
            values={name:context.digest() for name,context in names.items()}
            changes=[]
            for offset,context in mutations.items():
                context.update(iv);modified=context.digest();changes.append(dict(ciphertext_offset=offset,
                    retained_signature_accepts=expected is not None and modified==expected,changed_sha256=modified.hex()))
            changed_iv=bytearray(iv);changed_iv[0]^=1;context=names['ciphertext_body'].copy();context.update(changed_iv)
            changes.append(dict(iv_offset=0,retained_signature_accepts=expected is not None and context.digest()==expected,changed_sha256=context.hexdigest()))
            matches=[name for name,value in values.items() if expected==value]
            dest=outputs/(path.stem+'.rsa2048-signature.bin');assert not dest.exists();dest.write_bytes(signature)
            row=dict(name=path.name,source=str(path),source_sha256=pin,fdat_offset=start,fdat_bytes=length,
                ciphertext_body_bytes=body_length,iv_bytes=16,signature_bytes=256,signature_sha256=sha256(signature).hexdigest(),
                original_signature_output=str(dest.relative_to(HERE)),signature_less_than_modulus=sig<modulus,
                pkcs1_v1_5_padding_valid=padding_ok,sha256_digest_info_valid=digest_info_ok,
                digest_info_sha256=expected.hex() if expected else None,coverage_matches=matches,
                candidate_hashes={name:value.hex() for name,value in values.items()},in_memory_single_byte_mutations=changes)
            results.append(row);print(path.name,'PKCS1',padding_ok,'SHA256_DigestInfo',digest_info_ok,'coverage',matches,flush=True)
    assert len(results)==3 and all(row['coverage_matches']==['ciphertext_body_then_iv'] and row['sha256_digest_info_valid'] for row in results)
    assert all(not change['retained_signature_accepts'] for row in results for change in row['in_memory_single_byte_mutations'])
    result=dict(status='PASS_ORIGINAL_FDAT_RSA2048_SHA256_VERIFICATION',key_path=str(keypath.relative_to(HERE)),pem_sha256=sha256(key).hexdigest(),
        public_key_der_sha256=der_digest,modulus_bits=modulus.bit_length(),public_exponent=exponent,official_key_identical_in_both_initrds=True,
        key_file_sha1_comparison_first_nul_index=zero_index,packages=results,
        scope='Official embedded public key only. Original signatures and precise candidate coverage tested; changed bytes remain in memory and no full modified package is emitted. Does not execute actual key-trust OSAL service, complete updater, boot or recovery, and does not establish signing capability.')
    (HERE/'official-key-rsa-verification-results.json').write_text(json.dumps(result,indent=2)+'\n')


if __name__=='__main__':main()
