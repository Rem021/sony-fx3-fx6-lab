"""Verify public reference bytes using existing host crypto; no firmware execution."""
from pathlib import Path
from hashlib import sha256
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
import json, struct
H = Path(__file__).resolve().parent
rom = (H / 'reference/bootrom/CXD90057_Mira_0xFFFF0000.bin').read_bytes()
boot = (H / 'reference/emmc_boot/emmc_boot0.bin').read_bytes()
image = (H / 'reference/emmc_boot/esram_0xfe040000.bin').read_bytes()
u32 = lambda off: struct.unpack_from('<I', boot, off)[0]
start, load, length, entry = (u32(x) for x in [0x68, 0x6c, 0x74, 0x78])
assert boot[:4] == b'EXBL'
assert (start, load, length, entry) == (4, 0xfe040800, 0x2e000, 0xfe049000)
offsets = struct.unpack_from('<64I', rom, 0x6984)
pad = rom[0xb800:0xbc00]
assert all(i < len(pad) for i in offsets)
public_key = bytes(pad[i] for i in offsets)
plain = bytearray(boot[:0x800])
for off in range(0, length, 512):
    d = Cipher(algorithms.AES(public_key), modes.XTS((start + off // 512).to_bytes(16, 'little'))).decryptor()
    plain.extend(d.update(boot[start * 512 + off:start * 512 + off + 512]) + d.finalize())
assert plain == image and len(image) == 0x2e800
del public_key, pad, offsets, plain
result = dict(status='PUBLIC_BOOT0_TO_SRAM_EXACT_MATCH', sectors=length // 512,
    boot0_sha256=sha256(boot).hexdigest(), AP_ROM_sha256=sha256(rom).hexdigest(),
    SRAM_sha256=sha256(image).hexdigest(), SRAM_bytes=len(image),
    derived_key_printed_or_persisted=False, upstream_parser_executed=False,
    original_or_guest_execution=False, root_or_device_operations=0)
(H / 'public-SRAM-binding.json').open('x').write(json.dumps(result, indent=2) + '\n')
print(json.dumps({'public_SRAM_bytes_verified':len(image), 'encrypted_sectors':length // 512, 'device_operations':0}))
