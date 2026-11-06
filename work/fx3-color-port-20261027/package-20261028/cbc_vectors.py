#!/usr/bin/env python3
"""Re-encode bounded FDAT vectors using native Apple AES, never a full firmware package."""
from pathlib import Path
from hashlib import sha256
import json,struct,ctypes,ast,urllib.request,warnings

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
FW=ROOT/'work/sony-firmware-20261024'
SOURCE='https://raw.githubusercontent.com/DavidBuchanan314/fwtool.py/3955d7890fc38daf942bb52827599bfe35de4a14/fwtool/sony/constants.py'
PIN='f9ff02a3889b587cd5bad5f4362fb73fee2f8f3591fc3ed6003eb8ac92d0622a'


def crypt(data,key,iv=None,decrypt=False,ecb=False):
    assert len(data)%16==0 and len(key) in [16,24,32]
    if not ecb:assert iv is not None and len(iv)==16
    lib=ctypes.CDLL('/usr/lib/system/libcommonCrypto.dylib');fn=lib.CCCrypt
    fn.argtypes=[ctypes.c_uint32,ctypes.c_uint32,ctypes.c_uint32,ctypes.c_void_p,ctypes.c_size_t,
                 ctypes.c_void_p,ctypes.c_void_p,ctypes.c_size_t,ctypes.c_void_p,ctypes.c_size_t,
                 ctypes.POINTER(ctypes.c_size_t)]
    fn.restype=ctypes.c_int32
    src=ctypes.create_string_buffer(data,len(data));kb=ctypes.create_string_buffer(key,len(key))
    ib=ctypes.create_string_buffer(iv,16) if iv is not None else None
    out=ctypes.create_string_buffer(len(data)+16);moved=ctypes.c_size_t()
    result=fn(int(decrypt),0,2 if ecb else 0,kb,len(key),ib,src,len(data),out,len(out),ctypes.byref(moved))
    assert result==0 and moved.value==len(data),(result,moved.value,len(data))
    return out.raw[:moved.value]


def pack(payload,last):
    assert 0<len(payload)<=1020
    tail=struct.pack('<H',len(payload)|(0x8000 if last else 0))+payload+b'\xff'*(1020-len(payload))
    return struct.pack('<H',sum(struct.unpack('<511H',tail))&0xffff)+tail


def main():
    src=urllib.request.urlopen(SOURCE,timeout=20).read();assert sha256(src).hexdigest()==PIN
    with warnings.catch_warnings():
        warnings.simplefilter('ignore',SyntaxWarning);tree=ast.parse(src)
    keys={}
    for node in tree.body:
        if isinstance(node,ast.Assign):
            for target in node.targets:
                if isinstance(target,ast.Name) and target.id in ['key_aes','key_cxd90057_k8']:
                    keys[target.id]=ast.literal_eval(node.value)
    # Keys are public format constants, used only in memory and not printed or copied into outputs.
    m=json.loads((FW/'fx3-7.02-offline-manifest.json').read_bytes())
    outer=json.loads((FW/'ufu-header-analysis.json').read_bytes())['packages']['fx3-7.02']
    base=outer['fdat_payload_offset'];body_size=outer['fdat_payload_size']-0x110
    count=body_size//1024;assert body_size%1024==0 and count==m['decrypted_blocks']
    rows=[];vectors=HERE/'experimental-vectors';vectors.mkdir(exist_ok=True)
    with (FW/'fx3-7.02-BODYDATA.DAT').open('rb') as encrypted,(FW/'fx3-7.02-decrypted.fdat').open('rb') as plain:
        encrypted.seek(base+body_size);tail=encrypted.read(0x110);assert len(tail)==0x110
        for i in [0,1,256,count//2,count-2,count-1]:
            encrypted.seek(base+i*1024);original=encrypted.read(1024)
            if i:
                encrypted.seek(base+i*1024-16);iv=encrypted.read(16)
            else:iv=tail[:16]
            plain.seek(i*1020);payload=plain.read(min(1020,m['decrypted_fdat_size']-i*1020))
            raw=pack(payload,i==count-1)
            def encode(block):
                return (crypt(block[:512],keys['key_aes'],ecb=True)+crypt(block[512:],keys['key_cxd90057_k8'],iv)) if i==0 else crypt(block,keys['key_cxd90057_k8'],iv)
            def decode(block):
                return (crypt(block[:512],keys['key_aes'],decrypt=True,ecb=True)+crypt(block[512:],keys['key_cxd90057_k8'],iv,decrypt=True)) if i==0 else crypt(block,keys['key_cxd90057_k8'],iv,decrypt=True)
            recreated=encode(raw);assert recreated==original
            assert decode(original)==raw
            changed=bytearray(payload);changed[min(900,len(changed)-1)]^=1
            changed_raw=pack(changed,i==count-1);changed_cipher=encode(changed_raw)
            assert changed_cipher!=original and decode(changed_cipher)==changed_raw
            assert sum(struct.unpack('<511H',changed_raw[2:]))&0xffff==struct.unpack_from('<H',changed_raw)[0]
            # Isolated 1 KiB vectors cannot serve as a firmware update. No full modified package is emitted.
            (vectors/f'block-{i:06d}-original.bin').write_bytes(original)
            (vectors/f'block-{i:06d}-experimental.bin').write_bytes(changed_cipher)
            rows.append(dict(block=i,last=i==count-1,payload_bytes=len(payload),original_cipher_sha256=sha256(original).hexdigest(),
                             recreated_bytes_match=True,experimental_cipher_sha256=sha256(changed_cipher).hexdigest(),
                             experimental_roundtrip=True,original_u16_checksum=struct.unpack_from('<H',raw)[0],
                             experimental_u16_checksum=struct.unpack_from('<H',changed_raw)[0]))
    result=dict(status='PASS_BOUNDED_CBC_REENCODING_AND_BLOCK_CHECKSUM_VECTORS',constants_source=SOURCE,
                constants_source_sha256=PIN,native_crypto='/usr/lib/system/libcommonCrypto.dylib CCCrypt',
                official_package_sha256=m['source_sha256'],samples=rows,
                tail=dict(bytes=len(tail),iv_bytes=16,remaining_bytes=256,sha256=sha256(tail).hexdigest(),
                          meaning='The remaining 256 bytes are retained as uninterpreted verification material. No signature scheme or camera acceptance is established.'),
                scope='Six isolated vectors only, including the legacy ECB header half-block and CBC boundaries. Original cipher bytes reproduced exactly. Encryption primitive and per-block checksum are not proof of a signed, model-compatible, accepted or bootable firmware package. No full modified FDAT/UFU emitted.')
    (HERE/'cbc-vector-results.json').write_text(json.dumps(result,indent=2)+'\n')
    print(result['status'],'vectors',len(rows),'full modified firmware emitted',False)


if __name__=='__main__':main()
