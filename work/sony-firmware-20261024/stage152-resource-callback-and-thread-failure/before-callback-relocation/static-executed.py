"""Pinned firmware images as data, with explicitly bounded original functions."""
from pathlib import Path
from hashlib import sha256
import importlib.util
import json

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
ROOT = BASE.parents[1]
MWF_SHA = '06a80e89d1bba839bf4ea83492fb1fe0490037a8c8c46bf21d7ac46657d47a26'
OBJ_ENTRIES = [0xea58c, 0xea924, 0xea9b4, 0xea750, 0xea488, 0xec458, 0xec4bc, 0xec51c, 0xeb95c, 0xec3f4]
MWF_ENTRIES = [0x36d78, 0x3808c, 0x38238, 0x2f420, 0x2f3c0]


def images():
    prior = BASE / 'stage149-normal-cooperator-and-NIN-checkpoint'
    raw = (prior / 'final-receipt.json').read_bytes()
    assert sha256(raw).hexdigest() == '889e9553cdc213579b7f1a0575d10d1de73dcde0bbc19704aaa9b2bc2ba24c6d'
    source = prior / 'normal_cooperator.py'
    member = next(m for m in json.loads(raw)['files'] if m['path'] == source.relative_to(ROOT).as_posix())
    assert sha256(source.read_bytes()).hexdigest() == member['sha256']
    spec = importlib.util.spec_from_file_location('fixed_resource_source', source)
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    obj, unused_core = helper.images()
    latest = BASE / 'stage151-latest-A7CII-HEVC-evidence'
    raw = (latest / 'final-receipt.json').read_bytes()
    assert sha256(raw).hexdigest() == '9a511f3b70ab5d2cb596ea9ce20a7fec4e2e300f1d544d8174db8252afb82c54'
    saved = latest / 'preserved-stage150-work.json'
    member = next(m for m in json.loads(raw)['files'] if m['path'] == saved.relative_to(ROOT).as_posix())
    assert sha256(saved.read_bytes()).hexdigest() == member['sha256']
    path = BASE / 'stage150-normal-resource-and-thread-transition/work/originals/libMWF.so'
    member = next(m for m in json.loads(saved.read_text())['files'] if m['path'] == path.relative_to(ROOT).as_posix())
    assert sha256(path.read_bytes()).hexdigest() == member['sha256'] == MWF_SHA
    image_type = type(obj)
    image_type.__init__.__globals__['LIB'] = path.parent
    mwf = image_type('libMWF.so', MWF_SHA)
    return helper, obj, mwf


def main():
    helper, obj, mwf = images()
    of, mf = helper.spans(obj, OBJ_ENTRIES), helper.spans(mwf, MWF_ENTRIES)
    ins = {int(i['pc'], 16): i for f in of for i in f['instructions']}
    expected = {
        0xea97c: 'bl #0x55a50', 0xea980: 'mov w0, #1', 0xea988: 'strb w0, [x21, #0xd9]',
        0xea9ac: 'b #0x56e40', 0xea858: 'mov x0, x27', 0xea864: 'ldrb w0, [x19, #0x50]',
        0xea8cc: 'mov w0, #4', 0xea8d0: 'str w0, [x24]', 0xec538: 'bl #0x57190',
        0xec53c: 'str xzr, [x19]', 0xec504: 'mov x0, #-1', 0xec508: 'str x0, [x19]'}
    for pc, asm in expected.items():
        assert ins[pc]['asm'] == asm, (hex(pc), ins[pc])
    relocs = {r['r_offset']: r for r in obj.elf.get_section_by_name('.rela.dyn').iter_relocations()}
    selected = {0x262110: 0xeac50, 0x262f58: 0x2ce0ac, 0x262f40: 0xea750, 0x261758: 0xea1dc}
    for offset, value in selected.items():
        assert relocs[offset]['r_info_type'] == 1027 and relocs[offset]['r_info_sym'] == 0
        assert relocs[offset]['r_addend'] == value
    report = {'object_functions': of, 'middleware_functions': mf,
        'selected_relative_relocations': {hex(k): hex(v) for k, v in selected.items()},
        'thread_creation_return_not_checked_before_flag': True,
        'cancel_and_join_wrapper_returns_not_tested_by_worker_before_following_transition': True,
        'actual_OS_resource_queue_or_camera_state_proven': False,
        'new_device_operations': 0}
    with (HERE / 'original-resource-static.json').open('x') as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
        handle.write('\n')
    (HERE / 'static-executed.py').write_bytes(Path(__file__).read_bytes())
    print(json.dumps({'object_functions': len(of), 'middleware_functions': len(mf), 'new_device_operations': 0}))


if __name__ == '__main__':
    main()
