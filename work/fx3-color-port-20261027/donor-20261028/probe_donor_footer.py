#!/usr/bin/env python3
"""Read-only type4 footer/layout probes. Never infers a cipher from alignment."""
from pathlib import Path
import hashlib,importlib.util,json,struct

HERE=Path(__file__).resolve().parent

def main():
    previous=HERE.parent/'input-20261028'
    spec=importlib.util.spec_from_file_location('previous_public_rsa',previous/'verify_original_fdat_rsa.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    key=(previous/'engine-rootfs/2.05/etc/VerificationKey.pem').read_bytes()
    assert hashlib.sha256(key).hexdigest()=='8281413b5607446939613e07d020b2c7d8ee2371349099de56bc8288f7be0a43'
    modulus,exponent,der_sha=module.public_pem(key)
    inventory=json.loads((HERE/'donor-inner-source-inventory.json').read_text())
    rows=[]
    for source in inventory['files']:
        path=Path(source['path']);n=path.stat().st_size
        with path.open('rb') as stream:
            assert hashlib.file_digest(stream,'sha256').hexdigest()==source['sha256']
            stream.seek(n-16);tail=stream.read(16)
            value=struct.unpack('<Q',tail[:8])[0]
            padded=(value+7)&-8;residual=n-padded
            assert tail[8:]==b' '*8 and residual==296
            offsets=sorted({0,8,16,24,256,264,280,n-256,n-272,n-280,n-288,n-296})
            probes=[]
            for off in offsets:
                stream.seek(off);signature=stream.read(256);assert len(signature)==256
                for endian in ['big','little']:
                    sig=int.from_bytes(signature,endian)
                    encoded=pow(sig,exponent,modulus).to_bytes(256,'big')
                    end=encoded.find(b'\0',2) if encoded[:2]==b'\0\1' else -1
                    valid=end>=10 and encoded[2:end]==b'\xff'*(end-2)
                    probes.append(dict(offset=off,relative_to_end=off-n,endian=endian,
                                       signature_less_than_modulus=sig<modulus,pkcs1_v1_5_padding_valid=valid,
                                       public_modexp_prefix_hex=encoded[:4].hex()))
            rows.append(dict(version=source['version'],source=source['path'],sha256=source['sha256'],bytes=n,
                             last16_hex=tail.hex(),tail_little_endian_u64=value,n_minus_value=n-value,
                             u64_mod8=value%8,u64_mod16=value%16,n_minus_ceil_u64_to8=residual,
                             formula='N == ceil(footer_u64 / 8) * 8 + 296',formula_matches=True,
                             rsa_probes=probes))
    result=dict(status='THREE_ORIGINAL_FOOTERS_SHARE_LENGTH_RELATION',files=rows,
                public_key_pem_sha256=hashlib.sha256(key).hexdigest(),public_key_der_sha256=der_sha,
                rsa_valid_candidates=sum(p['pkcs1_v1_5_padding_valid'] for r in rows for p in r['rsa_probes']),
                limits=['The footer word is an observed length-like value; its semantic meaning is not proven.',
                        'The 296 residual does not locate or identify a header, signature, IV, key, digest, or encrypted region.',
                        'No padding of decrypted bytes was inspected. Eight-byte layout alignment does not establish a cipher.',
                        'RSA probes test only these 12 offsets and two byte orders under the FX3 FDAT public key. Negative results do not rule out RSA, other keys, other locations, or other signature schemes.'])
    (HERE/'donor-footer-results.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'versions':len(rows),'same_length_relation':True,'rsa_probes':sum(len(r['rsa_probes']) for r in rows),'valid_pkcs1':result['rsa_valid_candidates']}))

if __name__=='__main__':main()
