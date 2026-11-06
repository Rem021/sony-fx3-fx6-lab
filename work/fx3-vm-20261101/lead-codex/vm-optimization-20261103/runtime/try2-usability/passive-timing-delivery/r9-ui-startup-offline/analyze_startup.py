#!/usr/bin/env python3
"""Read existing logs, selected CPIO members and ELF ranges; write only HERE."""
from pathlib import Path
import collections
import datetime
import hashlib
import json
import plistlib
import re
import subprocess
import struct

HERE = Path(__file__).resolve().parent
PROJECT = next(p for p in HERE.parents if p.name == 'Mac')
TRY2 = HERE.parents[1]
RUNTIME = PROJECT / 'work/fx3-vm-20261101/menu-repair-01/runtime'
HELPERS = RUNTIME / 'helpers'
LIB = RUNTIME.parent / 'original-uipc/ap-projection/regular-files/usr/lib'
RUNS = ['v25diag-web-r3-91001f82', 'v25diag-web-r6-0dfbd0ab',
        'v25procdiag-web-r6-d4254d75']
INPUTS = {}


def sha_file(path):
    with path.open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def pin(path):
    path = path.resolve()
    INPUTS[str(path.relative_to(PROJECT))] = {'bytes': path.stat().st_size,
                                             'sha256': sha_file(path)}
    return path


def fields(text):
    return dict(re.findall(r'\b([A-Za-z_][A-Za-z_0-9]*)=([^\s]+)', text))


def parse_run(name):
    run = TRY2 / 'runs' / name
    raw = pin(run / 'serial.log').read_bytes()
    rows, offset = [], 0
    # LF-only line numbers match rg/nl; retained raw fragments may interleave.
    for number, line in enumerate(raw.split(b'\n'), 1):
        rows.append((number, offset, line))
        offset += len(line) + 1

    def records(token):
        key = token.encode()
        result = []
        for number, off, line in rows:
            at = line.find(key)
            if at < 0:
                continue
            text = line[at:].decode(errors='replace').rstrip('\r')
            result.append({'LF_line': number, 'byte_offset': off + at,
                           'fields': fields(text), 'text': text})
        return result

    wire = records('FX3_UI_WIRE ')
    gates = {}
    for idx in range(12):
        recs = records(f'FX3_UI_GATE_SAMPLE id={idx} ')
        decisions = []
        for rec in recs:
            value = rec['fields'].get('decision_a18')
            if value and value.isdecimal():
                decisions.append(int(value))
        signed = [x - (1 << 32) if x & (1 << 31) else x for x in decisions]
        gates[str(idx)] = {'logged_records': len(recs), 'first': recs[:1], 'last': recs[-1:],
                           'logged_signed_decision_min': min(signed) if signed else None,
                           'logged_signed_decision_max': max(signed) if signed else None,
                           'logged_signed_branch_le_2': sum(x <= 2 for x in signed)}
    tokens = ['FX3_TIMER_BOUND ', 'FX3_TIMER_SNAPSHOT ', 'FX3_PRESET_CONTEXT_BOUND ', 'FX3_UI_GATE_BOUND ',
              'FX3_UI_CONFIG_DONE ', 'FX3_TIMER_ENTRY ', 'FX3_TIMER_ID ',
              'FX3_TIMER_TABLE ', 'FX3_TIMER_INFO ', 'FX3_TIMER_RETURN ',
              'FX3_UI_FILL_EXEC ', 'FX3_UI_FILL_RETURN ', 'FX3_GPE_CMD op=',
              'FX3_GPE104_CMD_RETURN ', 'FX3_OSD_HEADLESS_BOUND ',
              'FX3_OSD_OWNER_START ', 'FX3_OSD_OWNER_GUI ', 'FX3_OSD_OWNER_CURRENT ',
              'FX3_OSD102_COMMIT ', 'FX3_OSD_NATIVE_SIGNAL ', 'FX3_KEY96_POLL ']
    markers = {}
    for token in tokens:
        rs = records(token)
        markers[token] = {'raw_occurrences': raw.count(token.encode()),
                          'LF_records': len(rs), 'first': rs[:1], 'last': rs[-1:]}
    recvs = [r for r in records('FX3_UIPC_RECV_BEGIN ')
             if r['fields'].get('queue') in ['0x8280074d', '0x8280084d', '0x8288076c']]
    screens = records('FX3_AP89_SCREEN_CREATE ')
    cmd = json.loads(pin(run / 'command.json').read_text())
    receipt = json.loads(pin(run / 'receipt.json').read_text())
    counters = {'available': False}
    counter_path = run / 'ui-gate-counters.bin'
    if counter_path.is_file():
        data = pin(counter_path).read_bytes()
        header = struct.unpack_from('<8Q', data)
        assert header[0] == 0x3145544147335846 and header[2] in (0, 1)
        values = struct.unpack_from('<96Q', data, 0x100 + header[2] * 0x1000)
        counters = {'available': True, 'header': header, 'count0_to11': values[:12],
                    'peak_gate': values[65], 'gate_hist': values[73:79],
                    'backlog_skip': values[64+16], 'time_skip': values[64+17],
                    'time_pass': values[64+18], 'a12_nonzero': values[64+21],
                    'a13_nonzero': values[64+22],
                    'timer_dequeue': values[64+20], 'last_a18': values[64+24],
                    'scope': 'final full-run counters, not startup-only or lossless program execution proof'}
    for filename in ['trial-cleanup-phase.json', 'trial-web-final-receipt.json']:
        if (run / filename).is_file():
            pin(run / filename)
    cpio = next(a.split('file=', 1)[1].split(',addr=', 1)[0] for a in cmd['args']
                if a.startswith('loader,file=') and '.cpio,' in a)
    return {'run': str(run.relative_to(PROJECT)), 'serial': INPUTS[str((run/'serial.log').relative_to(PROJECT))],
            'duration_seconds': receipt['duration_seconds'], 'guest_cpio': cpio,
            'receipt_status': {k: receipt.get(k) for k in ['qemu_exit', 'process_reaped',
                                'PID_absent', 'lifecycle_pass', 'health_pass', 'host_observer_error']},
            'wire_count': len(wire), 'wire_raw_count': raw.count(b'FX3_UI_WIRE '),
            'first65_wire': [dict(r, ordinal=i+1) for i, r in enumerate(wire[:65])],
            'markers': markers, 'gates': gates, 'ui_recv_begin': recvs,
            'screens_first8': screens[:8],
            'existing_ui_gate_counters': counters}


def selected_members(archive, wanted):
    """Seek over unselected payloads; no comparison or extraction of the archive."""
    result = {}
    with archive.open('rb') as f:
        while True:
            start = f.tell()
            header = f.read(110)
            if not header:
                break
            assert header[:6] == b'070701'
            values = [int(header[6+i*8:14+i*8], 16) for i in range(13)]
            name = f.read(values[11])[:-1].decode()
            body = (start + 110 + values[11] + 3) & ~3
            f.seek(body)
            canonical = name.removeprefix('./')
            if canonical in wanted:
                remaining, h, captured = values[6], hashlib.sha256(), bytearray()
                while remaining:
                    chunk = f.read(min(remaining, 1024*1024))
                    assert chunk
                    h.update(chunk)
                    if canonical == 'init': captured.extend(chunk)
                    remaining -= len(chunk)
                result[canonical] = {'bytes': values[6], 'sha256': h.hexdigest()}
                if canonical == 'init':
                    result[canonical]['selected_environment_lines'] = [
                        {'line': i+1, 'text': s} for i, s in enumerate(captured.decode().splitlines())
                        if 'FX3_OSD_' in s or 'LD_PRELOAD=' in s and 'timer-observe' in s]
            if canonical == 'TRAILER!!!': break
            f.seek((body + values[6] + 3) & ~3)
    assert set(result) == set(wanted), set(wanted) - set(result)
    return result


def main():
    volume = plistlib.loads(subprocess.check_output(['diskutil','info','-plist','/Volumes/KAFU2T']))
    assert volume['VolumeUUID'] == 'F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
    runs = {n: parse_run(n) for n in RUNS}
    binding = {}
    for name in ['ioctl-trace-v12', 'fx3-timer-observe-v3',
                 'fx3-preset-context-v6-save102', 'fx3-ui-gate-v11',
                 'fx3-osd-headless-v7-observe102']:
        source, binary, build = (HELPERS/(name+s) for s in ['.c','.so','-build.json'])
        for p in [source, binary, build]: pin(p)
        b = json.loads(build.read_text())
        binding[name] = {'source_sha256': sha_file(source), 'binary_sha256': sha_file(binary),
                         'build_exit': b.get('exit'),
                         'source_matches_build': b.get('source_sha256') == sha_file(source),
                         'binary_matches_build': b.get('output_sha256') == sha_file(binary)}
    for name in ['fx3-osd-core-v4-frame.h', 'fx3-osd-owner-core-v1.h',
                 'fx3-display-probes-v1.S']:
        pin(HELPERS/name)
    for name in ['appFw.so','libObj.so','libosal_uipc.so']: pin(LIB/name)
    for relative in ['passive-timing-delivery/r6-zero-frame-offline-review/REPORT.md',
                     'passive-timing-delivery/r6-zero-frame-offline-review/COMPARISON.json',
                     'passive-timing-delivery/v25-r9-ab-host/run_trial_v25_diag_r3.py',
                     'passive-timing-delivery/v25-r9-ab-host/quiesced_diag_readback.py',
                     'runs/v25diag-web-r6-0dfbd0ab/ab-zero-key-observation.json']:
        pin(TRY2/relative)
    timing = TRY2 / 'mss-all-key-contrast/passive-timing-next'
    ap_source = timing / 'src/fx3-preset-context-v6-save102-timing.c'
    ap_binary = timing / 'build/ap-timing.so'
    ap_build = timing / 'build-receipt.json'
    osd_root = HERE.parent / 'v25-menu-osd-diagnostic-r3'
    osd_source = osd_root / 'src/fx3-osd-headless-v25-r3.c'
    osd_binary = osd_root / 'build/fx3-osd-headless-v25-r3.so'
    osd_build = osd_root / 'vmopt-20261104-v25-menu-osd-diagnostic-r3/build-receipt.json'
    for p in [ap_source, ap_binary, ap_build, osd_source, osd_binary, osd_build,
              osd_root/'FREEZE-r3.json', osd_root/'build/compile-r3.command.json']:
        pin(p)
    ab = next(row for row in json.loads(ap_build.read_text())['rows'] if row['kind'] == 'ap')
    ob = json.loads(osd_build.read_text())
    for name, source, binary, expected_source, expected_binary in [
        ('preset-timing', ap_source, ap_binary, ab['candidate_source_sha256'], ab['output_sha256']),
        ('osd-v25-r3', osd_source, osd_binary, ob['source_sha256'], ob['so_sha256'])]:
        binding[name] = {'source': str(source.relative_to(PROJECT)),
                         'binary': str(binary.relative_to(PROJECT)),
                         'source_sha256': sha_file(source), 'binary_sha256': sha_file(binary),
                         'source_matches_build': sha_file(source) == expected_source,
                         'binary_matches_build': sha_file(binary) == expected_binary}
    aliases = {'simulation/ioctl-trace.so': 'ioctl-trace-v12',
               'simulation/fx3-timer-observe-v1.so': 'fx3-timer-observe-v3',
               'simulation/fx3-preset-context-v2-screen.so': 'preset-timing',
               'simulation/fx3-ui-gate-v1.so': 'fx3-ui-gate-v11',
               'simulation/fx3-osd-headless-v5.so': 'osd-v25-r3'}
    wanted = ['init', *aliases, 'usr/lib/appFw.so', 'usr/lib/libObj.so', 'usr/lib/libosal_uipc.so']
    archives = {}
    for cpio in sorted({r['guest_cpio'] for r in runs.values()}):
        members = selected_members(Path(cpio), wanted)
        for member, helper in aliases.items():
            members[member]['matches_helper_binary'] = members[member]['sha256'] == binding[helper]['binary_sha256']
            members[member]['actual_helper_binding'] = helper
            assert members[member]['matches_helper_binary'], member
        for name in ['appFw.so','libObj.so','libosal_uipc.so']:
            members['usr/lib/'+name]['matches_original_projection'] = members['usr/lib/'+name]['sha256'] == sha_file(LIB/name)
        archives[cpio] = {'only_selected_members_hashed': True, 'members': members}
    ranges = [('app-gui-send', 'appFw.so',0x16ee598,0x16ee8a8),
              ('app-timer-1004','appFw.so',0x176fb4c,0x176fbf8),
              ('app-main-gate','appFw.so',0x16f2450,0x16f2674),
              ('app-update-and-draw','appFw.so',0x16f1998,0x16f1a48),
              ('app-backlog-producer','appFw.so',0x16f1a48,0x16f1bc0),
              ('app-backlog-consumer','appFw.so',0x16f1d10,0x16f1d80),
              ('app-a12-candidate-writer1','appFw.so',0x21dfa40,0x21dfa64),
              ('app-a12-candidate-writer2','appFw.so',0x21f115c,0x21f1180),
              ('libObj-original-fill','libObj.so',0x100c48,0x100cfc),
              ('libObj-framebuffer-draw','libObj.so',0x16ea10,0x16eae4),
              ('libosal-send-recv-ioctl','libosal_uipc.so',0x3a10,0x3ce0)]
    disassembly = []
    for label, name, start, stop in ranges:
        args=['xcrun','llvm-objdump','--disassemble',f'--start-address={start:#x}',
              f'--stop-address={stop:#x}',str(LIB/name)]
        text = subprocess.check_output(args,text=True)
        dest = HERE/(label+'.txt')
        dest.write_text(text)
        disassembly.append({'file': dest.name, 'ELF': str((LIB/name).relative_to(PROJECT)),
                            'ELF_sha256': sha_file(LIB/name), 'start': hex(start),
                            'stop_exclusive': hex(stop), 'argv': args})
    # Verify read inputs still match after all analysis; no original is modified.
    for relative, expected in INPUTS.items():
        assert sha_file(PROJECT/relative) == expected['sha256'], relative
    out = {'created_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
           'volume_uuid': volume['VolumeUUID'], 'runs': runs, 'helper_build_binding': binding,
           'targeted_cpio_members': archives, 'disassembly': disassembly,
           'input_files_unchanged_sha256': INPUTS, 'vm_started': False,
           'historical_tests_reexecuted': False, 'guest_or_helper_modified': False}
    (HERE/'EVIDENCE.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'runs': {n: {'wire': r['wire_count'],
                     'timer': r['markers']['FX3_TIMER_ENTRY ']['LF_records'],
                     'fill': r['markers']['FX3_UI_FILL_EXEC ']['LF_records']} for n,r in runs.items()},
                     'helper_binding': binding, 'disassembly_ranges':len(ranges),
                     'unchanged_inputs':len(INPUTS)},indent=2))


if __name__ == '__main__': main()
