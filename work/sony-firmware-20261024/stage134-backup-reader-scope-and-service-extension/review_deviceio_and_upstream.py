#!/usr/bin/env python3
"""Static wrapper and pinned upstream syntax review; no foreign code import."""
from pathlib import Path
import ast
import hashlib
import json
import audit_readers

HERE = Path(__file__).resolve().parent


def main():
    core = audit_readers.Image('libsencore.so', 'a2907111c4a22314dcb12c25889e0e3142764c6a4a910a746e43908f76e7c410')
    functions = [core.function(n) for n in ('_ZN8DeviceIo4openEPKci', '_ZNK8DeviceIo5writeEPKvm')]
    assert core.instructions(0x15364, 4)[0]['asm'] == 'mov w1, w2'
    assert core.expect_call(0x15374, 'open')
    assert core.expect_call(0x15100, 'write')
    records = json.loads((HERE / 'upstream-read-interface-review.json').read_text())['records']
    selected = []
    wanted = {'_sendFileControlPacket', '_sendMemoryDumpPacket', 'readFile', 'readMemory', 'senserShellCommand'}
    for record in records:
        path = HERE / record['path']
        raw = path.read_bytes()
        assert hashlib.sha256(raw).hexdigest() == record['sha256']
        text = raw.decode()
        tree = ast.parse(text)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name in wanted:
                selected.append({'path': record['path'], 'function': node.name,
                                 'line_start': node.lineno, 'line_end': node.end_lineno,
                                 'source': ast.get_source_segment(text, node)})
    assert {r['function'] for r in selected} == wanted
    flags = 0x101241
    assert flags & 3 == 1 and flags & 0x40 and flags & 0x200 and flags & 0x101000 == 0x101000
    result = {'scope': 'Static forwarding proof and upstream packet layout, not device capability or complete auth flow',
              'core_functions': functions, 'open_flags_forwarded_unchanged': True,
              'hasp_flags': {'raw': hex(flags), 'Linux_interpretation': ['O_WRONLY', 'O_CREAT', 'O_TRUNC', 'O_SYNC'],
                             'source': 'https://github.com/torvalds/linux/blob/v4.9/include/uapi/asm-generic/fcntl.h'},
              'upstream_methods': selected,
              'upstream_file_read': 'pFunc ff01 command2, filename only; transport fragmentation is not device file-range bounding',
              'upstream_memory_read': 'pFunc ff03 base/size; no evidence of FX3 stock receiver or body-valid ranges',
              'upstream_serviceshell': 'starts/authenticates, switches service, re-enumerates and authenticates again before shell',
              'do_not_run_PMCA_device_enumeration_import_or_shell_under_cached_metadata_authority': True,
              'conditional_history_write_not_proof_every_authentication_writes_or_actual_target_file_exists': True,
              'device_code_IO_or_Sony_execution': False}
    with (HERE / 'deviceio-and-upstream-review.json').open('x') as handle:
        json.dump(result, handle, ensure_ascii=False, indent=2)
        handle.write('\n')
    print(json.dumps({'original_wrapper_functions': len(functions), 'upstream_method_definitions': len(selected),
                      'no_camera_operations': True}))


if __name__ == '__main__':
    main()
