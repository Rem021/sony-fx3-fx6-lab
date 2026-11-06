"""Bounds-checked FDT data reader; no mount, firmware code or device access."""
from pathlib import Path
from hashlib import sha256
import struct, json, re
H = Path(__file__).resolve().parent
p = H / 'originals/7.02-setting-cxd90057.dtb'
b = p.read_bytes()
head = struct.unpack_from('>10I', b)
magic, total, off_struct, off_strings, off_rsv, version, compat, cpu, strsize, structsize = head
assert magic == 0xd00dfeed and total == len(b) and version == 17 and compat <= 17
assert off_struct + structsize <= total and off_strings + strsize <= total and off_rsv % 8 == 0
strings = b[off_strings:off_strings + strsize]
end = off_struct + structsize
def cstr(data, pos, stop):
    z = data.find(b'\0', pos, stop)
    assert z >= pos
    return data[pos:z].decode('ascii'), z + 1
nodes = []
stack = []
pos = off_struct
while pos < end:
    token, = struct.unpack_from('>I', b, pos)
    pos += 4
    if token == 1:
        name, pos = cstr(b, pos, end)
        pos = (pos + 3) & ~3
        parent = stack[-1]['path'] if stack else None
        path = (parent.rstrip('/') + '/' + name) if parent else '/'
        assert not any(n['path'] == path for n in nodes)
        node = dict(path=path, parent=parent, properties={})
        nodes.append(node)
        stack.append(node)
    elif token == 2:
        assert stack
        stack.pop()
    elif token == 3:
        assert stack and pos + 8 <= end
        length, nameoff = struct.unpack_from('>II', b, pos)
        pos += 8
        assert pos + length <= end and nameoff < len(strings)
        name, _ = cstr(strings, nameoff, len(strings))
        assert name not in stack[-1]['properties']
        stack[-1]['properties'][name] = b[pos:pos + length].hex()
        pos = (pos + length + 3) & ~3
    elif token == 4:
        pass
    elif token == 9:
        assert not stack and pos == end
        break
    else:
        raise ValueError(('unknown FDT token', token, pos - 4))
assert nodes and nodes[0]['path'] == '/' and pos == end
by_path = {n['path']:n for n in nodes}
def raw(node, name):
    return bytes.fromhex(node['properties'][name])
def cell_prop(node, name, default):
    if name not in node['properties']:
        return default
    x = raw(node, name)
    assert len(x) == 4
    return int.from_bytes(x, 'big')
def number(data):
    return int.from_bytes(data, 'big')
def translate(addr, length, bus):
    if bus['parent'] is None:
        return addr
    parent = by_path[bus['parent']]
    if 'ranges' not in bus['properties']:
        return None
    ranges = raw(bus, 'ranges')
    if not ranges:
        return translate(addr, length, parent)
    ac = cell_prop(bus, '#address-cells', 2)
    pc = cell_prop(parent, '#address-cells', 2)
    sc = cell_prop(bus, '#size-cells', 1)
    stride = (ac + pc + sc) * 4
    assert stride > 0 and len(ranges) % stride == 0
    for off in range(0, len(ranges), stride):
        child = number(ranges[off:off + ac * 4])
        up = number(ranges[off + ac * 4:off + (ac + pc) * 4])
        size = number(ranges[off + (ac + pc) * 4:off + stride])
        if child <= addr and addr + length <= child + size:
            return translate(up + addr - child, length, parent)
    return None
decoded = []
for n in nodes:
    if 'reg' not in n['properties'] or n['parent'] is None:
        continue
    parent = by_path[n['parent']]
    ac = cell_prop(parent, '#address-cells', 2)
    sc = cell_prop(parent, '#size-cells', 1)
    data = raw(n, 'reg')
    stride = (ac + sc) * 4
    assert stride > 0 and len(data) % stride == 0
    entries = []
    for off in range(0, len(data), stride):
        addr = number(data[off:off + ac * 4])
        size = number(data[off + ac * 4:off + stride])
        phys = translate(addr, size, parent)
        entries.append(dict(bus_address=hex(addr), bytes=size, translated_bus_address=hex(phys) if phys is not None else None))
    decoded.append(dict(path=n['path'], parent_address_cells=ac, parent_size_cells=sc, reg=entries,
                        status=raw(n, 'status').rstrip(b'\0').decode() if 'status' in n['properties'] else 'absent',
                        compatible=raw(n, 'compatible').rstrip(b'\0').decode().split('\0') if 'compatible' in n['properties'] else []))
reservations = []
rpos = off_rsv
while True:
    assert rpos + 16 <= total
    a, z = struct.unpack_from('>QQ', b, rpos)
    rpos += 16
    if not a and not z:
        break
    reservations.append(dict(address=hex(a), bytes=z))
result = dict(source_sha256=sha256(b).hexdigest(), total_bytes=total, nodes=nodes,
    decoded_reg=decoded, reservation_map=reservations, source='7.02 package setting DTB, not running body DT',
    translation_scope='FDT ranges only; driver-specific syscon/MFD offsets are not resolved into actual MMIO addresses',
    runtime_fixups_or_actual_hardware_proven=False, original_or_guest_execution=False, device_operations=0)
(H / 'DTB-decoded.json').open('x').write(json.dumps(result, indent=2) + '\n')
selected = [n for n in decoded if re.search(r'memory|emmc|mmc|usb|scu|spi|gpio|sio|timer', n['path'], re.I)]
print(json.dumps(dict(nodes=len(nodes), selected=selected), indent=2))
