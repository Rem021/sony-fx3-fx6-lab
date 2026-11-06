"""Frozen input gate plus explicit GDB stop replies for read-only TCG probes.

Normal execution/resume remains QMP controlled. Z1 creates QEMU CPU breakpoint
records, not guest instructions. Only the inherited input and cleanup controls
write guest RAM; this observer never writes registers or original memory.
"""
import collections
import json
import re
import struct
import time
from gate_input101 import InputGate as FrozenGate, valid_command


class InputGate(FrozenGate):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.debug_stops = collections.deque()

    def packet(self, payload):
        data = payload.encode()
        self.sock.sendall(b'$'+data+b'#'+f'{sum(data)%256:02x}'.encode())
        while True:
            c = self.sock.recv(1)
            if not c:
                raise RuntimeError('GDB observation stream ended')
            if c != b'$':
                continue
            out = bytearray()
            while True:
                c = self.sock.recv(1)
                if c == b'#':
                    break
                if not c:
                    raise RuntimeError('GDB observation packet ended')
                out.extend(c)
            checksum = self.exact(2)
            if int(checksum, 16) != sum(out) % 256:
                raise RuntimeError('GDB observation checksum mismatch')
            self.sock.sendall(b'+')
            response = out.decode()
            if response.startswith(('T', 'S')):
                if payload in ('?', 's'):
                    return response
                self.debug_stops.append(response)
                continue
            if response.startswith('O') and response != 'OK':
                continue
            return response

    def command(self, *args, **kwargs):
        item = super().command(*args, **kwargs)
        (self.run/'ap102-host-input-gate.json').write_text(json.dumps(self.history, ensure_ascii=False, indent=2)+'\n')
        return item

    def virtual_read(self, address, size):
        if not 0 < size <= 4096:
            raise ValueError('bounded observation read only')
        self.connect()
        if self.packet('Qqemu.PhyMemMode:0') != 'OK':
            raise RuntimeError('GDB virtual-read mode rejected')
        try:
            value = self.packet(f'm{address:x},{size:x}')
            if value.startswith('E'):
                return None
            result = bytes.fromhex(value)
            return result if len(result) == size else None
        finally:
            if self.packet('Qqemu.PhyMemMode:1') != 'OK':
                raise RuntimeError('GDB physical input mode restoration failed')


class KernelObserver:
    def __init__(self, run, gate, qmp, proof):
        self.run, self.gate, self.qmp = run, gate, qmp
        self.proof = proof
        self.points = {}
        self.base = None
        self.records = []
        self.total_pause = 0
        self.removed = False

    def install(self, base):
        if self.base is not None:
            return
        self.gate.connect()
        self.base = base
        for point in self.proof['kernel_points']:
            address = base+point['offset']
            raw = self.gate.virtual_read(address, 4)
            if raw is None:
                raise RuntimeError('Original kernel probe word unavailable')
            if point['relocated_call']:
                valid = int.from_bytes(raw, 'little') & 0xfc000000 == 0x94000000
            else:
                valid = raw.hex() == point['raw']
            if not valid:
                raise RuntimeError('Original kernel probe word mismatch: '+point['label'])
            if self.gate.packet(f'Z1,{address:x},4') != 'OK':
                raise RuntimeError('QEMU TCG read-only breakpoint unavailable')
            self.points[address] = dict(point, runtime_word=raw.hex(), runtime_address=hex(address))
        self.save()

    def read(self, address, size):
        value = self.gate.virtual_read(address, size)
        return {'address': hex(address), 'bytes': size, 'raw': None if value is None else value.hex()}

    def message(self, pointer, reply=False):
        if pointer < 0xffffff8000000000:
            return {'pointer': hex(pointer), 'unavailable': True}
        value = self.gate.virtual_read(pointer-24, 64)
        result = {'pointer': hex(pointer), 'header24_and_body40_hex': None if value is None else value.hex()}
        if value:
            body = value[24:]
            result.update(op=struct.unpack_from('<H', body)[0], status=struct.unpack_from('<h', body, 2)[0],
                          raw_u32_offset4=hex(struct.unpack_from('<I', body, 4)[0]),
                          raw_u32_offset16=hex(struct.unpack_from('<I', body, 16)[0]),
                          physical=hex(struct.unpack_from('<Q', body, 24)[0]),
                          capacity=struct.unpack_from('<I', body, 32)[0],
                          source=hex(struct.unpack_from('<I', value, 12)[0]))
        if value and not reply:
            result['request_unit'] = hex(struct.unpack_from('<I', value, 28)[0])
        result['message_layout'] = 'native_40B_DMM_reply' if reply else 'native_40B_DMM_request'
        return result

    def poll(self):
        if self.base is None or self.removed:
            return False
        status = self.qmp('query-status')
        if status.get('return', {}).get('status') != 'debug':
            return False
        started = time.monotonic()
        # cpu_handle_guest_debug already selects actual c_cpu/g_cpu. qC
        # reports the first process CPU in this QEMU and must not select Hg.
        stop = 'QMP debug; native QEMU stopped-CPU register context'
        raw = bytes.fromhex(self.gate.packet('g'))
        if len(raw) < 264:
            raise RuntimeError('Short AArch64 native register read')
        regs = struct.unpack_from('<33Q', raw)
        pc, fp = regs[32], regs[29]
        if pc not in self.points:
            raise RuntimeError('Unexpected QEMU debug stop at '+hex(pc))
        point = self.points[pc]
        label = point['label']
        record = {'index': len(self.records)+1, 'host_monotonic': started,
                  'stop_reply': stop, 'point': point,
                  'registers': {f'x{i}': hex(regs[i]) for i in list(range(8))+[19, 20, 21, 22, 23, 29, 30]},
                  'SP': hex(regs[31]), 'PC': hex(pc), 'x0_signed32': struct.unpack('<i', raw[:4])[0],
                  'read_only_original_memory_and_registers': True}
        if label == 'DMM_send_original_request':
            record['request'] = self.message(regs[1])
        if label in ('DMM_receive_original_args', 'DMM_receive_actual_return'):
            record['frame_local_4c_to_60'] = self.read(fp+0x4c, 20)
            value = self.gate.virtual_read(fp+0x58, 8)
            if value and label == 'DMM_receive_actual_return' and regs[0] == 0:
                record['reply'] = self.message(int.from_bytes(value, 'little'), reply=True)
        if label in ('malloc_actual_return', 'cache_type_actual_return', 'physical_to_VA_actual_return',
                     'old_file_load_actual_return', 'local_file_save_actual_return'):
            record['local_merge_frame_70_to_a0'] = self.read(fp+0x70, 48)
        if label == 'DMM_malloc_entry':
            record['native_info_before'] = self.read(regs[0], 24)
            record['requested_capacity'] = regs[1]
        self.records.append(record)
        self.save()
        # Execute exactly the original stopped instruction on its actual CPU.
        removed = self.gate.packet(f'z1,{pc:x},4')
        if removed != 'OK':
            raise RuntimeError('Failed to remove native observation breakpoint: '+removed)
        stepped = self.gate.packet('s')
        if not stepped.startswith(('T05', 'S05')):
            raise RuntimeError('Original instruction single-step failed: '+stepped)
        if self.gate.packet(f'Z1,{pc:x},4') != 'OK':
            raise RuntimeError('Failed to rearm native observation breakpoint')
        record['step_stop'] = stepped
        record['observer_pause_seconds'] = time.monotonic()-started
        self.total_pause += record['observer_pause_seconds']
        self.save()
        self.qmp('cont')
        return True

    def close(self):
        if self.removed:
            return
        errors = []
        for address in self.points:
            response = self.gate.packet(f'z1,{address:x},4')
            if response != 'OK':
                errors.append({'address': hex(address), 'response': response})
        if errors:
            # QEMU's initial '?' query clears only c_cpu. Deliberately use it
            # on every enumerated CPU during cleanup, never while observing.
            threads = []
            response = self.gate.packet('qfThreadInfo')
            while response.startswith('m'):
                threads.extend(response[1:].split(','))
                response = self.gate.packet('qsThreadInfo')
            if response != 'l' or not threads:
                raise RuntimeError('Cannot enumerate CPUs for breakpoint cleanup')
            for thread in threads:
                if self.gate.packet('Hc'+thread) != 'OK':
                    raise RuntimeError('Cannot select cleanup CPU')
                reply = self.gate.packet('?')
                if not reply.startswith(('T', 'S')):
                    raise RuntimeError('Cannot clear cleanup CPU breakpoints')
            self.fallback_clear_all_CPUs = threads
        self.removal_replies_nonzero = errors
        unchanged = []
        for address, point in self.points.items():
            value = self.gate.virtual_read(address, 4)
            unchanged.append({'address': hex(address), 'same_original_runtime_word': value is not None and value.hex() == point['runtime_word']})
        self.removed = True
        self.original_words_unchanged = unchanged
        self.save()
        if not all(x['same_original_runtime_word'] for x in unchanged):
            raise RuntimeError('Original kernel probe words changed')

    def save(self):
        (self.run/'ap102-kernel-observations.json').write_text(json.dumps({
            'method': 'QEMU TCG Z1 CPU breakpoint table; no guest text/register writes; exact original instruction single-step',
            'base_from_guest_sysfs': None if self.base is None else hex(self.base),
            'installed_points': list(self.points.values()), 'records': self.records,
            'total_observer_pause_seconds': self.total_pause,
            'breakpoints_removed': self.removed,
            'removal_replies_nonzero': getattr(self, 'removal_replies_nonzero', None),
            'fallback_clear_all_CPUs': getattr(self, 'fallback_clear_all_CPUs', None),
            'original_words_unchanged': getattr(self, 'original_words_unchanged', None),
            'timing_limit': 'Debug stops pause all vCPUs; wall clock is not uninterrupted guest idle time',
        }, indent=2)+'\n')
