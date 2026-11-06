#!/usr/bin/env python3
"""Original lower rate lookup feeds original Start flag/extra preparation.

The queued Open remains suspended. Independent entries use another stack and
declared component/settings inputs. No lock return, kernel state, hardware,
Start submission or completed recording is synthesized.
"""
from pathlib import Path
import argparse
import datetime
import json
import struct
import sys
import traceback

STAGE = Path(__file__).resolve().parent
sys.path.insert(0, str(STAGE.parent / 'stage75-private-preset-storage'))
import private_storage as p
c, r, im, V, n, f = p.c, p.r, p.im, p.V, p.n, p.f
BASE, ROOT = p.BASE, p.ROOT
STATE = r.ARENA + 0x340000
STATE_SIZE = 0x2ab40
QOS = STATE + 0x2aa20
QUERY = r.ARENA + 0x3c0000
START = QUERY + 0x100
EXTRA = QUERY + 0x400
SETTINGS = QUERY + 0x800
SP = r.STACK + 0x2000
RATE = V + 0x225b7c


class Guest(p.StorageGuest):
    def __init__(self, *args):
        super().__init__(*args)
        self.lower_query = False
        self.native_rate_entries = []
        self.ranges.extend((V + a, V + z) for a, z in (
            (0x2304f0, 0x2304f8), (0x228c64, 0x228c7c),
            (0x227870, 0x227918), (0x246274, 0x24641c),
            (0x22c35c, 0x22c3ac), (0x27cf44, 0x27cf58),
            (0x248b24, 0x249548)))

    def code(self, u, pc, size, user):
        if self.lower_query and pc == RATE:
            # The inherited observer assumes the compiled adapter's frame.
            # This independent ORIGINAL caller has its own separately checked
            # destination; do not relabel it as another adapter call.
            self.observed_pc = pc
            rr = lambda i: u.reg_read(getattr(r.reg, 'UC_ARM64_REG_X' + str(i)))
            self.native_rate_entries.append({
                'pc': hex(pc), 'owner': hex(rr(0)), 'result': hex(rr(8)),
                'LR': hex(rr(30)), 'SP': hex(u.reg_read(r.reg.UC_ARM64_REG_SP)),
            })
            assert rr(0) == c.COMMON and rr(8) == QUERY
            return c.d.Guest.code(self, u, pc, size, user)
        return super().code(u, pc, size, user)


def linked(assets, modules, providers, adapter):
    m = Guest(assets, modules, providers, adapter)
    m.compiled_layout = p.t.layout(adapter)
    m.result_container_size = 56
    events = [n.link(m)]
    for row in m.import_bindings:
        assert m.read(int(row['actual_avcam_slot'], 16), 8) == r.p64(int(row['original_module_target'], 16))
    m.uc.mem_write(f.f58.SITE, m.patch)
    m.uc.mem_write(c.SITE, m.adapter_patch)
    m.uc.mem_protect(V, 4096, r.unicorn.UC_PROT_READ | r.unicorn.UC_PROT_EXEC)
    m.expected_data = {f.f59.GUARD: 1, f.f59.MUTE: 0, f.f59.CAT1: 1, f.f59.CAT2: 1}
    for at, value in m.expected_data.items():
        assert m.blob[at-V] == 0
        m.uc.mem_write(at, bytes([value]))
    m.uc.mem_protect(f.f59.MUTE & -4096, 4096, r.unicorn.UC_PROT_READ | r.unicorn.UC_PROT_WRITE)
    e = c.phase(m, 'original mute setter on declared logger', V + 0x27d898, x0=f.f59.LOG, x1=1)
    assert e['reason'] == 'returned'
    events.append(e)
    m.expected_data[f.f59.MUTE] = 1
    lo, hi = f.G & -4096, (f.G + f.GSIZE + 4095) & -4096
    m.uc.mem_protect(lo, hi-lo, r.unicorn.UC_PROT_READ | r.unicorn.UC_PROT_WRITE)
    m.boundaries[m.rate_return_pcs[0]] = 'after_corrected_adapter_query_before_independent_start_flags'
    return m, events


def bounded(m, label, start, allowed, **regs):
    """Require all stores in declared outputs/state and separate stack."""
    stores = []
    allowed = [*allowed, (r.STACK, SP)]
    before = m.read(r.ARENA, r.ARENA_SIZE)
    def observe(u, access, at, size, value, user):
        assert any(a <= at and at+size <= z for a, z in allowed), (hex(at), size)
        stores.append({'pc': hex(u.reg_read(r.reg.UC_ARM64_REG_PC)), 'address': hex(at), 'bytes': size})
    hook = m.uc.hook_add(r.unicorn.UC_HOOK_MEM_WRITE, observe)
    try:
        e = c.phase(m, label, V+start, sp=SP, **regs)
    finally:
        m.uc.hook_del(hook)
    assert e['reason'] == 'returned', e['reason']
    assert e['SP_before'] == e['SP_after'] == hex(SP)
    after = m.read(r.ARENA, r.ARENA_SIZE)
    changed = [r.ARENA+i for i, (a, b) in enumerate(zip(before, after)) if a != b]
    assert all(any(a <= at < z for a, z in allowed) for at in changed)
    e['bounded_stores'] = stores
    e['whole_arena_outside_declared_state_and_outputs_unchanged'] = True
    return e


def flag_case(m, seed, label, target=None, timing=False):
    # These are declared component/settings inputs, not an actual active MAIN
    # component, a full constructor, or a claim of natural runtime sequencing.
    m.uc.mem_write(STATE, bytes(STATE_SIZE))
    m.uc.mem_write(STATE+0x738, struct.pack('<I', 14))
    m.uc.mem_write(START, bytes(0x170))
    m.uc.mem_write(EXTRA, bytes(0x300))
    settings = bytearray(0x38)
    if target is not None:
        settings[4] = settings[6] = 1
        struct.pack_into('<I', settings, 8, target)
        struct.pack_into('<I', settings, 0x10, 25999360)
    if timing:
        settings[0x28] = 1
    m.uc.mem_write(SETTINGS, bytes(settings))
    events = [bounded(m, 'original optional-parameter initializer '+label, 0x248b24,
                      [(QOS, QOS+0x100)], x0=QOS)]
    events.append(bounded(m, 'independent original optional-parameter reset '+label, 0x248b84,
                          [(QOS, QOS+0x100)], x0=QOS))
    if target is not None or timing:
        events.append(bounded(m, 'original settings setter '+label, 0x248b8c,
                              [(QOS, QOS+0x100)], x0=QOS, x1=SETTINGS))
    query_before = m.read(QUERY, 56)
    preset_before = m.read(p.PRIVATE, 256)
    selected_before = m.read(c.COMMON+0xe000, 8)
    pending_before = m.read(m.pending_start, m.pending_end-m.pending_start)
    events.append(bounded(m, 'complete original Start flag/extra preparation '+label, 0x246274,
                          [(STATE, STATE+STATE_SIZE), (START, START+0x170), (EXTRA, EXTRA+0x300)],
                          x0=STATE, x1=START, x2=EXTRA, x3=EXTRA+0x100, x4=QUERY))
    assert m.uc.reg_read(r.reg.UC_ARM64_REG_X0) == 1
    raw = m.read(EXTRA, 0x300)
    mask = struct.unpack_from('<I', raw)[0]
    rate_word = struct.unpack_from('<I', raw, 0x18)[0]
    decoded = ((((rate_word >> 8)+1) << (6+(rate_word & 255))) if mask & 0x80 else None)
    assert decoded == target
    assert m.read(START, 5) == bytes([0, 1, int(bool(mask)), 2, 0])
    assert bool(mask & 0x100) == timing
    if timing:
        assert struct.unpack_from('<H', raw, 0x1e)[0] == struct.unpack_from('<H', query_before, 0x2c)[0] == 8008
        assert struct.unpack_from('<I', raw, 0x20)[0] == struct.unpack_from('<I', query_before, 0x30)[0] == 240000
    assert m.read(QUERY, 56) == query_before
    assert m.read(p.PRIVATE, 256) == preset_before and m.read(c.COMMON+0xe000, 8) == selected_before
    assert m.read(m.pending_start, m.pending_end-m.pending_start) == pending_before
    c.assert_images(m)
    return {'seed': seed, 'label': label, 'events': events,
            'declared_settings_hex': settings.hex(), 'original_query_hex': query_before.hex(),
            'start_first5_hex': m.read(START, 5).hex(), 'extra_first64_hex': raw[:64].hex(),
            'extra_mask': mask, 'decoded_optional_target': decoded,
            'copied_tail_fields': ([8008, 240000] if timing else None),
            'original_pending_stack_query_and_selected16M_preset_preserved': True,
            'actual_live_component_shared_lock_Start_transport_or_recording_proven': False}


def one_seed(assets, modules, providers, adapter, descriptor, seed):
    m, events = linked(assets, modules, providers, adapter)
    global CURRENT_GUEST
    CURRENT_GUEST = m
    c.prepare(m, events, descriptor, seed, None)
    m.uc.mem_write(p.PRIVATE-p.GUARD, bytes([seed])*(256+2*p.GUARD))
    e = c.phase(m, 'queued original Open through corrected adapter to query return', V+0x22f34c, x0=f.last.CTX)
    assert e['reason'] == 'boundary: after_corrected_adapter_query_before_independent_start_flags'
    events.append(e)
    assert m.query_proof['saved_LR_unchanged']
    m.pending_start = m.uc.reg_read(r.reg.UC_ARM64_REG_SP)
    m.pending_end = r.SP+0x1000
    pending = m.read(m.pending_start, m.pending_end-m.pending_start)
    assert m.pending_start > SP
    m.uc.mem_write(QUERY, bytes([seed])*56)
    m.lower_query = True
    e = bounded(m, 'independent original lower query wrapper and native owner lookup', 0x2304f0,
                [(QUERY, QUERY+56)], x0=f.last.CTX, x1=0, x8=QUERY)
    events.append(e)
    m.lower_query = False
    result = m.read(QUERY, 56)
    assert struct.unpack_from('<3Q', result) == (25999360, 16000000, 26000000)
    assert result[0x2e:0x30] == bytes([seed])*2 and result[0x34:0x38] == bytes([seed])*4
    writes = [w for w in e['bounded_stores'] if QUERY <= int(w['address'], 16) < QUERY+56]
    covered = set()
    for w in writes:
        a = int(w['address'], 16)-QUERY
        covered.update(range(a, a+w['bytes']))
    assert covered == set(range(0x34))-set(range(0x2e, 0x30))
    assert len(m.native_rate_entries) == 1
    assert m.read(m.pending_start, m.pending_end-m.pending_start) == pending
    cases = [flag_case(m, seed, 'optional disabled'),
             flag_case(m, seed, 'explicit target16M', 16000000),
             flag_case(m, seed, 'explicit target20M override control', 20000000),
             flag_case(m, seed, 'explicit timing option only', timing=True)]
    assert not m.kernel_service_entries and not m.message_entries and not m.admitted_channel_entries
    assert c.old.control(m)['live'] == 1
    return {'seed': seed, 'events': events, 'native_lookup_rate_entries': m.native_rate_entries,
            'native_lower_query_hex': result.hex(), 'query_written_offsets': sorted(covered),
            'corrected_adapter_query': m.query_proof, 'cases': cases,
            'suspended_Open_not_resumed': True, 'actual_main_recording_or_recovery_proven': False}


def run(out):
    prior = BASE/'stage77-upstream-recovery-boundaries/final-receipt.json'
    assert im.sha(prior.read_bytes()) == '44971a4749e8838b4f7a1edb5b289ae836bc612f4141f80cee24f4cba624e0c4'
    for row in json.loads(prior.read_text())['files']:
        assert im.sha((ROOT/row['path']).read_bytes()) == row['sha256']
    assert (BASE/'GOAL_STATUS.json').read_bytes() == (STAGE/'goal-status-before.json').read_bytes()
    mods, providers, kernel = c.d.link.build()
    code, ro, _ = f.f58.object_image((f.f58.STAGE/'run-post-loader-patch-20261026/match_adapter.a64.o').read_bytes())
    wp = p.STAGE/'run-20261026/resource_alias.a64.o'
    ap = p.STAGE/'run-20261026/channel_adapter.a64.o'
    wcode, wro, functions, _ = c.old.object_image(wp.read_bytes())
    adapter = c.object_image(ap.read_bytes())
    blob = (BASE/'stage2/extraction/files/nflasha3/av-cam.bin').read_bytes()
    assert im.sha(blob) == im.PINS['stage2/extraction/files/nflasha3/av-cam.bin']
    liro = (n.STAGE/'official-files/nflasha15/kmod/liro.ko').read_bytes()
    assets = blob, liro, kernel, code, ro, wcode, wro, functions
    cases = [one_seed(assets, mods, providers, adapter, c.d.p.inputs()[0][1], seed) for seed in (0xa5, 0xc3)]
    result = {
        'created_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'status': 'PASS_NATIVE_LOWER_QUERY_START_FLAGS_OPTIONAL_RATE_AND_TAIL_COPY',
        'cases': cases,
        'bounded_fragments': sum(len(x['events'])+sum(len(z['events']) for z in x['cases']) for x in cases),
        'original_regions': [{'start': hex(a), 'end': hex(z), 'instructions': im.dump(blob, a, z, V)} for a, z in (
            (0x24ce94, 0x24cec0), (0x22ba98, 0x22baf0), (0x2304f0, 0x2304f8),
            (0x228c64, 0x228c7c), (0x246274, 0x24641c), (0x248b24, 0x249548))],
        'source_receipt': {'script_sha256': im.sha(Path(__file__).read_bytes()),
                           'storage_runner_sha256': im.sha((p.STAGE/'private_storage.py').read_bytes()),
                           'writer_object_sha256': im.sha(wp.read_bytes()), 'adapter_object_sha256': im.sha(ap.read_bytes()),
                           'avcam_sha256': im.sha(blob), 'LIRO_sha256': im.sha(liro), 'kernel_sha256': im.sha(kernel)},
        'scope': [
            'Independent original lower query uses the native registered owner map and unchanged selected16M preset; no locked wrapper was executed.',
            'Complete original flag/extra helper consumes that original query tail on declared MAIN component/settings inputs. Original Open stays suspended on another stack.',
            'Optional target control can encode20M despite the still-selected16M preset. The actual downstream precedence and current camera settings remain unproven.',
            'Timing option copies query2c/30 into extra1e/20. Ratio240000/8008 equals30000/1001, but field naming and hardware timing still require downstream evidence.',
            'No actual component initialization, legal reentrancy/concurrency, shared sync, full Start, VCD/hardware, recording, backup or recovery proof.'],
        'Windows_UU_camera_operations': False, 'goal_complete': False, 'persistent_write_release': False,
    }
    im.write_json(out/'start-flags-results.json', result)
    (out/'executed-source.py').write_bytes(Path(__file__).read_bytes())
    print(json.dumps({'status': result['status'], 'bounded_fragments': result['bounded_fragments'], 'cases': 8, 'hardware_proven': False}))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--output', required=True)
    args = ap.parse_args()
    im.volume()
    out = Path(args.output).resolve()
    assert STAGE in out.parents and not out.exists()
    out.mkdir()
    try:
        run(out)
    except Exception:
        (out/'attempt-source.py').write_bytes(Path(__file__).read_bytes())
        im.write_json(out/'attempt-failure.json', {'traceback': traceback.format_exc(), 'passing_result': False})
        if 'CURRENT_GUEST' in globals():
            m = CURRENT_GUEST
            im.write_json(out/'failure-state.json', {'pc': hex(m.uc.reg_read(r.reg.UC_ARM64_REG_PC)),
                                                    'reason': m.reason, 'last_pcs': [hex(x) for x in m.pcs[-12:]]})
        raise


if __name__ == '__main__':
    main()
