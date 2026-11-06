"""Compare pinned payload requirements with stock FX3 data and named GPL references."""
from pathlib import Path
from hashlib import sha256
import json, re, struct
H = Path(__file__).resolve().parent
R = H.parents[2]
PAY = H / 'reference/payloads/fastboot'
GPL = H / 'reference-source/linux-kernel'
dt = json.loads((H / 'DTB-decoded.json').read_text())
nodes = {r['path']:r for r in dt['nodes']}
regs = {r['path']:r for r in dt['decoded_reg']}
capture = json.loads((H / 'payload-source-capture.json').read_text())
assert len(capture['files']) == 47
for row in capture['files']:
    assert sha256((R / row['output']).read_bytes()).hexdigest() == row['sha256']
pins = []
def pin(path, a, z, label):
    data = path.read_bytes()
    lines = data.splitlines(keepends=True)
    selected = b''.join(lines[a - 1:z])
    assert 1 <= a <= z <= len(lines)
    row = dict(label=label, source=str(path.relative_to(R)), source_sha256=sha256(data).hexdigest(),
        line_start=a, line_end_inclusive=z, bytes=len(selected), selected_sha256=sha256(selected).hexdigest())
    pins.append(row)
    return row
def pin_find(path, pattern, label):
    lines = path.read_text().splitlines()
    hits = [i for i, text in enumerate(lines, 1) if re.search(pattern, text)]
    assert len(hits) == 1, (path.name, pattern, hits)
    return pin(path, hits[0], hits[0], label)
def macro(path, name):
    match = re.search(r'^#define\s+' + name + r'\s+(0x[0-9a-fA-F]+|[0-9]+)(?:[uUlL]*)\b', path.read_text(), re.M)
    assert match, name
    pin_find(path, r'^#define\s+' + name + r'\s', name)
    return int(match.group(1), 0)
def dt_reg(path, index=0):
    return int(regs[path]['reg'][index]['translated_bus_address'], 16)
rows = []
for name, path, field, node in [
    ('SCU', PAY/'include/scu.h', 'SCU_BASE', '/soc/scu@F1388000'),
    ('USB_PHY', PAY/'include/usb_phy.h', 'USB_SS_BASE', '/soc/usbs'),
    ('DWC3', PAY/'include/dwc3_regs.h', 'DWC3_BASE', '/soc/usbs/usb@0')]:
    value = macro(path, field)
    assert dt_reg(node) == value
    rows.append(dict(resource=name, address=hex(value), comparison='MATCH_7_02_PACKAGE_DTB', node=node, actual_hardware_verified=False))
spacc = macro(PAY/'include/spacc.h', 'SPACC_BASE')
assert dt_reg('/soc/spacc@F7FC0000') == spacc
rows.append(dict(resource='SPACC', address=hex(spacc), comparison='MATCH_7_02_PACKAGE_DTB', node='/soc/spacc@F7FC0000', actual_hardware_verified=False))
spi = macro(PAY/'src/cetus.c', 'SPI0_BASE')
assert dt_reg('/soc/spi0@F1017000') == spi
rows.append(dict(resource='SPI0', address=hex(spi), comparison='MATCH_7_02_PACKAGE_DTB', node='/soc/spi0@F1017000', actual_hardware_verified=False))
sdhci = macro(PAY/'include/sdhci.h', 'SDHCI_BASE')
assert sdhci == macro(GPL/'drivers/udif/mach-cxd900xx/platform.c', 'EMMC0_IO_BASE') == 0xf10d6000
assert 'reg' not in nodes['/soc/emmc0']['properties']
rows.append(dict(resource='eMMC', address=hex(sdhci), comparison='MATCH_7_00_GPL_PLATFORM_ONLY',
    exact7_02_DTB_reg_available=False, actual_hardware_verified=False))
for resource, value, gplfile, pattern in [
    ('TIMER0', macro(PAY/'include/timer.h', 'TIMER0_BASE'), GPL/'drivers/udif/mach-cxd900xx/include/mach/platform.h', r'^#define\s+CXD900XX_TIMER_BASE'),
    ('SIO0', 0xf1005000, GPL/'drivers/udif/mach-cxd900xx/platform.c', r'^#define\s+SIO_IO_BASE'),
    ('GPIO_formula_base', 0xf101d000, GPL/'drivers/udif/mach-cxd900xx/include/mach/platform.h', r'^#define\s+CXD900XX_GPIO')]:
    pin_find(gplfile, pattern, resource)
    assert hex(value).lower() in gplfile.read_text().lower()
    rows.append(dict(resource=resource, address=hex(value), comparison='MATCH_7_00_GPL_REFERENCE_ONLY', actual_hardware_verified=False))

# Resolve clock and reset phandles instead of comparing raw flattened words.
def raw(node, key):
    return bytes.fromhex(nodes[node]['properties'][key])
phandles = {int.from_bytes(bytes.fromhex(n['properties']['phandle']), 'big'):n['path']
    for n in dt['nodes'] if 'phandle' in n['properties']}
usb = '/soc/usbs'
clock_pairs = list(struct.iter_unpack('>II', raw(usb, 'clocks')))
clock_names = raw(usb, 'clock-names').rstrip(b'\0').decode().split('\0')
assert len(clock_pairs) == len(clock_names) == 4
driver = GPL/'drivers/clk/cxd/clk-cxd-900xx.c'
binding = GPL/'include/dt-bindings/clock/cxd-900xx-clk.h'
clock_rows = []
for token, bit in [('REF',12),('PCLK',13),('ACLK',14),('SUS',15)]:
    name = 'CXD_CLK_GATE_USB_' + (token if token in ('PCLK','ACLK') else token+'_CLK')
    ident = macro(binding, name)
    pattern = r'\{' + name + r',.*0x00,\s*' + str(bit) + r'\}'
    pin_find(driver, pattern, name+' bit')
    (handle, index), node_name = next((p,n) for p,n in zip(clock_pairs,clock_names) if p[1]==ident)
    assert phandles[handle].endswith('/clock-controller@0')
    clock_rows.append(dict(id=index, name=node_name, source_gate_bit=bit, register_bank_offset=0, reference_only=True))
reset_pairs = list(struct.iter_unpack('>II', raw(usb, 'resets')))
assert [p[1] for p in reset_pairs] == [11,10,9,8]
assert all(phandles[p[0]].endswith('/rst@300') for p in reset_pairs)
assert int.from_bytes(raw(phandles[reset_pairs[0][0]], 'reg')[0:8], 'big') == 0x300
pin_find(GPL/'drivers/reset/reset-cxd900xx.c', r'return regmap_write.*bank \* 16 \+ 4', 'reset assert offset')
pin_find(GPL/'drivers/reset/reset-cxd900xx.c', r'ret = regmap_write.*bank \* 16 \+ 8', 'reset deassert offset')

link = PAY/'fastboot.ld'
text = link.read_text()
assert re.search(r'ESRAM \(rwx\) : ORIGIN = 0xFE020000, LENGTH = 64K', text)
assert re.search(r'USBDMA \(rw\) : ORIGIN = 0xFE100000, LENGTH = 1M', text)
pin_find(link, r'ESRAM \(rwx\)', 'AP code/stack region')
pin_find(link, r'USBDMA \(rw\)', 'USB DMA region')
pin_find(GPL/'drivers/udif/mach-cxd900xx/include/mach/platform.h', r'^#define\s+CXD900XX_ESRAM_BASE', 'ESRAM reference base')
pin_find(GPL/'drivers/udif/mach-cxd900xx/include/mach/platform.h', r'^#define\s+CXD900XX_ESRAM_SIZE', 'ESRAM reference window')
assert 0xfe000000 <= 0xfe020000 < 0xfe030000 <= 0xfe100000 < 0xfe200000 <= 0xff000000
pin_find(PAY/'src/dwc3.c', r'DRAM is not trained', 'SRAM design comment')
pin_find(PAY/'src/fastboot.c', r'^#define DOWNLOAD_MAX', 'staged transfer limit')
mem = regs['/memory@400000000']['reg'][0]
assert mem['bytes'] == 1 << 33

# Normal service startup only calls darwin_init; it does not arm/feed counters.
main = (PAY/'src/main.c').read_text()
assert re.findall(r'\b(darwin_\w+)\s*\(', main) == ['darwin_init']
sources = list((PAY/'src').glob('*.c'))
callers = []
for path in sources:
    for n, line in enumerate(path.read_text().splitlines(), 1):
        if re.search(r'\bdarwin_write_block\s*\(', line):
            callers.append(dict(file=path.name,line=n,text=line.strip()))
assert len(callers) == 1 and callers[0]['file'] == 'darwin.c' and callers[0]['text'].startswith('int darwin_write_block(')
pin_find(PAY/'src/main.c', r'^\s*darwin_init\(', 'normal-start Darwin operation')
wdt = json.loads((H/'Darwin-WDT-source-proof.json').read_text())
assert wdt['counter_table'] == '0x200026fc' and len(wdt['reload_source_examples']) == 3
unknown = [
    'FX3 AP/CP ROM hashes and ROM_LED_INIT function atFFFF0784 are not identified on current body',
    'BootROM entry wiring, GPIO/serial timing and required RP2040 bridge remain unvalidated/unavailable',
    'SIO channel0, GPIO port4 bit2 XCS and4MHz timer are reference assumptions without FX3 board/runtime binding',
    'Cetus reset/boot strap and uploaded CP monitor must be adapted; main calls bring_up before USB and eMMC',
    'Darwin counters/reload addresses match static FX3 code, but read command16, framing/pins, live counters, timer cadence and keepalive are not proven',
    'raw/cleartext partition mapping, encryption, same-body boot0/p1 and inverse restore still require target evidence',
    'reference transfer code exposes write/execute/reset operations; no FX3 upload or first hardware test is authorized by this comparison']
result = dict(status='STATIC_COMMON_RESOURCES_AND_TARGET_MCU_FIELDS_BOUND_NOT_A_RUNNABLE_FX3_PAYLOAD',
    payload_commit=capture['commit'], resource_comparisons=rows,
    USB_clock_bindings=clock_rows, USB_clock_gate_mask=hex(sum(1<<r['source_gate_bit'] for r in clock_rows)),
    USB_reset_ids=[p[1] for p in reset_pairs], USB_reset_mask='0xf00',
    SRAM_layout=dict(code_stack_start='0xfe020000', code_stack_end_exclusive='0xfe030000',
                    DMA_start='0xfe100000', DMA_end_exclusive='0xfe200000',
                    falls_in_reference_16MiB_address_window=True, actual_usable_SRAM_capacity_proven=False,
                    full_DDR_training_is_not_a_reference_link_layout_prerequisite=True),
    package_DTB_declared_DDR_bytes=mem['bytes'], actual_body_DDR_capacity_inferred=False,
    normal_main_contains_explicit_Darwin_counter_feed=False, main_Darwin_write_block_callers=callers,
    target_MCU_counter_fields_bound=True, unresolved=unknown, source_line_pins=pins,
    source7_00_GPL_is_not_exact7_02_build=True, firmware_or_guest_executed=False, root_or_device_operations=0,
    target_payload_compiled_uploaded_or_run=False, persistent_write_release=False, goal_complete=False)
(H/'hardware-profile-comparison.json').open('x').write(json.dumps(result,indent=2)+'\n')
print(json.dumps(dict(resource_comparisons=len(rows), USB_clocks=len(clock_rows), line_pins=len(pins),
    DDR_training_required_by_reference_link_layout=False, target_MCU_static_fields_bound=True, device_operations=0)))
