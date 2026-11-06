"""Bind public A7 IV boot data to selected AP code; never execute firmware."""
from pathlib import Path
from hashlib import sha256, sha1
from capstone import Cs, CS_ARCH_ARM64, CS_MODE_LITTLE_ENDIAN
import json, struct

H = Path(__file__).resolve().parent
R = H.parents[2]
B = H.parent
capture = json.loads((H / 'source-capture.json').read_text())
for row in capture['files']:
    data = (R / row['output']).read_bytes()
    assert len(data) == row['bytes'] and sha256(data).hexdigest() == row['sha256']
    assert sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest() == row['git_blob_sha1']
rom = (H / 'reference/bootrom/CXD90057_Mira_0xFFFF0000.bin').read_bytes()
boot = (H / 'reference/emmc_boot/emmc_boot0.bin').read_bytes()
image_path = H / 'reference/emmc_boot/esram_0xfe040000.bin'
image = image_path.read_bytes()
u32 = lambda b, off: struct.unpack_from('<I', b, off)[0]
assert boot[:4] == b'EXBL'
start, load, length, entry = (u32(boot, x) for x in [0x68, 0x6c, 0x74, 0x78])
assert (start, load, length, entry) == (4, 0xfe040800, 0x2e000, 0xfe049000)
assert boot[:0x800] == image[:0x800] and len(image) == 0x800 + length
binding = json.loads((H / 'public-SRAM-binding.json').read_text())
assert binding['status'] == 'PUBLIC_BOOT0_TO_SRAM_EXACT_MATCH'
assert binding['boot0_sha256'] == sha256(boot).hexdigest()
assert binding['AP_ROM_sha256'] == sha256(rom).hexdigest()
assert binding['SRAM_sha256'] == sha256(image).hexdigest()

base = 0xfe040000
word = lambda a: u32(image, a - base)
def branch(a):
    w = word(a)
    assert w >> 26 == 0b100101
    n = w & 0x3ffffff
    if n & 0x2000000:
        n -= 0x4000000
    return a + 4 * n

def address(adrp, add):
    w, v = word(adrp), word(add)
    assert w & 0x9f000000 == 0x90000000
    imm = ((w >> 5) & 0x7ffff) << 2 | ((w >> 29) & 3)
    if imm & 0x100000:
        imm -= 0x200000
    assert v & 0xffc00000 == 0x91000000
    assert (v >> 5) & 31 == w & 31
    return (adrp & ~4095) + (imm << 12) + ((v >> 10) & 4095)

# The actual sequence consumer establishes 32B stride, callback+0, flags+8,
# label+16. An earlier exploratory print started at the label and is not the layout.
assert word(0xfe0606e0) == 0x8b181697
assert word(0xfe060760) == 0xf94002e8 and word(0xfe060768) == 0xd63f0100
assert word(0xfe060820) == 0x9100411c
# Mode3 reaches the updater table, independently of the condition's provenance.
assert word(0xfe05d708) == 0x71000c5f
assert address(0xfe05d710, 0xfe05d714) == 0xfe069cc8
assert branch(0xfe05d6d0) == 0xfe06066c
table = 0xfe069cc8
entries = []
for n in range(20):
    off = table - base + n * 32
    callback, flags = struct.unpack_from('<QQ', image, off)
    label = image[off + 16:off + 32].split(b'\0', 1)[0].decode('ascii')
    entries.append(dict(index=n, address=hex(base + off), callback=hex(callback), flags=hex(flags), label=label))
    if callback == 0:
        break
selected = next(r for r in entries if int(r['callback'], 16) == 0xfe04f190)
assert selected['label'].strip() == 'Ld Kernel UPD'
# Selected callback chooses partition1, then its ordinary FAT file access paths.
assert word(0xfe04f19c) == 0x320003e0 and branch(0xfe04f1b8) == 0xfe059e94
assert branch(0xfe059f20) == 0xfe058b54
assert word(0xfe058b60) == 0x8b20d136
assert word(0xfe059f40) == 0x52954aa9 and word(0xfe059f58) == 0x7108011f
paths = []
for p, q, call in [(0xfe04f1d8, 0xfe04f1dc, 0xfe04f1e0),
                   (0xfe04f2d0, 0xfe04f2d4, 0xfe04f2dc),
                   (0xfe04f2e8, 0xfe04f2ec, 0xfe04f2f4),
                   (0xfe04f304, 0xfe04f308, 0xfe04f310),
                   (0xfe04f31c, 0xfe04f320, 0xfe04f328)]:
    target = address(p, q)
    path = image[target - base:].split(b'\0', 1)[0].decode('ascii')
    paths.append(dict(address=hex(target), path=path, call_site=hex(call), target_function=hex(branch(call))))
assert [r['path'] for r in paths] == ['\\boot\\loadaddr.txt', '\\boot\\vmlinux.bin', '\\boot\\initrd.img', '\\boot\\kemco.txt', '\\boot\\cxd90057.dtb']

md = Cs(CS_ARCH_ARM64, CS_MODE_LITTLE_ENDIAN)
md.skipdata = True
cuts = []
for a, z, label in [(0xfe05d6a0, 0xfe05d71c, 'mode3-sequence-select'),
                    (0xfe0606dc, 0xfe060770, 'sequence-callback-consumer'),
                    (0xfe06081c, 0xfe060840, 'sequence-label-consumer'),
                    (0xfe04f190, 0xfe04f230, 'updater-partition1-and-config'),
                    (0xfe04f2c8, 0xfe04f334, 'updater-boot-files'),
                    (0xfe059e94, 0xfe059f64, 'partition-FAT-selector'),
                    (0xfe058b54, 0xfe058bc8, 'partition-read-source'),
                    (0xfe049000, 0xfe049080, 'generic-entry128')]:
    data = image[a - base:z - base]
    out = H / 'pins' / (label + '.txt')
    out.parent.mkdir(exist_ok=True)
    out.open('x').write('\n'.join(f'{i.address:08x} {i.bytes.hex()} {i.mnemonic:8} {i.op_str}' for i in md.disasm(data, a)) + '\n')
    cuts.append(dict(start=hex(a), end_exclusive=hex(z), bytes=len(data), sha256=sha256(data).hexdigest(), output=str(out.relative_to(R))))
current = B / 'stage182-boot-selector-and-recovery-admission/current-updater-evidence/nor-loader-members/loader_nor.bin'
other = current.read_bytes()
assert sha256(other).hexdigest() == '4358c839cfb1f22d5eb4e53d67817c42c4e877ba8b0aff375d355ce6294c4942'
assert image[0x9000:0x9080] == other[:128] and image.find(other) == -1

result = dict(source_model='A7 IV2.00 public boot0/SRAM; not FX3 body', commit=capture['commit'],
    boot0_sha256=sha256(boot).hexdigest(), AP_ROM_sha256=sha256(rom).hexdigest(),
    SRAM_sha256=sha256(image).hexdigest(), SRAM_source=str(image_path.relative_to(R)),
    EXBL=dict(start_sector=start, load_address=hex(load), load_bytes=length, entry=hex(entry)),
    whole_public_boot0_to_supplied_SRAM_match=True,
    derived_key_printed_or_persisted=False, upstream_parser_executed=False,
    mode3_selects_sequence=hex(table), sequence_layout=dict(bytes=32, callback_offset=0, flags_offset=8, label_offset=16),
    sequence_entries=entries, selected_callback=selected, selected_partition=1,
    partition_selection_link='callbackw0=1 -> FE059E94 -> FE058B54 partition-indexed read and FAT BPB checks',
    boot_file_paths=paths, selected_original_ranges=cuts,
    FX3_NOR_comparison=dict(source=str(current.relative_to(R)), sha256=sha256(other).hexdigest(),
       entry128_equal=True, complete_binary_equal=False, same_program_or_AP_boot0_identity_proven=False),
    limits=['mode3 value, table and callback are reference A7IV evidence only; FX3 currently installed AP boot0 still absent',
            'selected consumer has runtime flags, earlier steps and failure paths; no boot or independent recovery has run',
            'AP UART/SPI/USB boot alternatives cannot be excluded by missing printable USB strings',
            'reference boot0/ROM/addresses are not a payload to upload to FX3'],
    actual_camera_operations=0, original_or_guest_execution=False, goal_complete=False, persistent_write_release=False)
(H / 'AP-reference-boot-proof.json').open('x').write(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
print(json.dumps(dict(public_source_files=len(capture['files']), whole_SRAM_binding=True, sequence_mode=3,
    selected_partition=1, boot_files=len(paths), pinned_ranges=len(cuts), FX3_boot0_obtained=False, device_operations=0)))
