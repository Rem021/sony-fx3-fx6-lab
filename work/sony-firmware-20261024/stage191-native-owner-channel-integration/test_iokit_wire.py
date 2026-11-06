"""Run real SDK-shaped fake vtable calls, never real USB or privilege changes."""
from dataclasses import replace
from hashlib import sha256
from pathlib import Path
from unittest.mock import patch
import ctypes as C
import importlib.util
import json
import os
import struct
import sys
import threading
import time
import traceback

import iokit_fixture_api as api
import iokit_wire as w

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
ROOT = BASE.parents[1]


def load_fixed(name, directory, manifest_sha, filename):
    manifest = (BASE/directory/'final-receipt.json').read_bytes()
    assert sha256(manifest).hexdigest() == manifest_sha
    path = BASE/directory/filename
    rec = next(x for x in json.loads(manifest)['files'] if x['path'] == path.relative_to(ROOT).as_posix())
    assert path.stat().st_size == rec['bytes'] and sha256(path.read_bytes()).hexdigest() == rec['sha256']
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def main():
    out = HERE/(sys.argv[1] if len(sys.argv) == 2 else 'run-tests')
    out.mkdir(exist_ok=False)
    for name in ('iokit_wire.h', 'iokit_wire.c', 'fake_iokit.c', 'iokit_wire.py', 'iokit_fixture_api.py', 'test_iokit_wire.py'):
        (out/name).write_bytes((HERE/name).read_bytes())
    cases, flows = [], []
    report = {'status': 'RUNNING', 'cases': cases, 'inert_flows': flows,
              'real_USB_or_camera_operations': 0, 'root_admin_or_privacy_changes': 0}
    def done(name, **data):
        cases.append({'name': name, **data})
    def rejects(call):
        try:
            call()
        except (w.Rejected, api.Rejected, w.WireFault):
            return
        raise AssertionError('expected rejection')
    try:
        s = load_fixed('fixed_iokit_controller', 'stage140-bounded-service-session-controller',
                       '5cc7e18aea8ae5d407bdf075bd9d8e4031ecf838fac84fa76b870b362ca19816', 'session_controller.py')
        p = load_fixed('fixed_iokit_provider', 'stage145-initial-MSC-native-route',
                       '2aeee45831cca4cfa09c2e4c20500ff0dfbc56cb752fde928998e0223b5f002d', 'mode_digest_provider.py')
        lib = api.FixtureLibrary()
        def clock(ref):
            return lib.stat(ref, 16)/1e9
        def counts(ref):
            return [lib.stat(ref, i) for i in range(3)]
        def binding(ref):
            mode = ref.mode
            return w.Binding(mode, 0x054c, 0x0da1 if mode == 'MSC' else 0x0336, 0x02100000,
                             'fixture-body-0001', 'fixture-port-0001', 'fixture-owner-'+mode,
                             'fixture-connect-'+mode, ref, 0x81 if mode == 'MSC' else 0x83,
                             2 if mode == 'MSC' else 4, 512, True, True)
        def observation(b, at):
            return w.Observation(at, b.mode, b.identity_tag, b.port_tag, b.owner_generation, b.connection_tag, True, True)
        def device(mode='MSC', driver=False):
            return s.Device('fixture-body-0001', 'fixture-port-0001', mode, 0x054c,
                            0x0da1 if mode == 'MSC' else 0x0336, 8 if mode == 'MSC' else 255, True, driver)
        def packet(code, data=b''):
            return struct.pack('>HH', (~code)&0xffff, 0)+data.ljust(512, b'\0')
        def setup(auth=False, reverse=False):
            ref = lib.create(reverse=reverse)
            b = binding(ref)
            now = clock(ref)
            budget = w.SessionBudget(61)
            wire = w.from_fixture(lib, b, budget, lambda: clock(ref))
            ctl = s.SessionController(s.Target(b.identity_tag, b.port_tag), s.Snapshot(now, (device(driver=True),)),
                                      s.Limits(60, 3, 2, 0.01, 4), now=now)
            a = ctl.next_inert_action(now)
            ctl.accept(s.Receipt(a.token, effect_observed=True), now)
            a = ctl.next_inert_action(now)
            ctl.accept(s.Receipt(a.token, snapshot=s.Snapshot(now, (device(),))), now)
            wire.observe(observation(b, now))
            a = ctl.next_inert_action(now)
            assert a.phase == 'START_MSC'
            if auth:
                assert wire.execute(ctl, a).status == 'CONTROL_OK'
                ctl.accept(s.Receipt(a.token, raw_return=0), now)
                rejects(wire.arm_authentication_after_start)
                wire.observe(observation(b, now))
                wire.arm_authentication_after_start()
                a = ctl.next_inert_action(now)
                assert a.phase == 'AUTH_MSC'
            return ref, b, budget, wire, ctl, a

        for fault, want in [(0, 'CONTROL_OK'), (1, 'CONTROL_STALL'), (2, 'CONTROL_TIMEOUT'),
                            (3, 'DISCONNECTED'), (13, 'INVALID_NATIVE_COUNT'), (15, 'CONTROL_ERROR'),
                            (8, 'LATE_RETURN'), (9, 'CLOCK_INVALID'), (10, 'OWNER_LOST'),
                            (11, 'OWNER_LOST'), (16, 'CANCEL_REQUESTED'), (17, 'LATE_RETURN')]:
            ref, b, budget, wire, ctl, action = setup()
            lib.fault(ref, 1, fault)
            result = wire.execute(ctl, action)
            assert result.status == want, (fault, result.public())
            assert counts(ref) == [1, 0, 0]
            assert [lib.stat(ref, i) for i in range(7, 12)] == [0x43, 1, 0x37ff, 0xd7aa, 0]
            assert 0 < lib.stat(ref, 3) <= 1000 and lib.stat(ref, 3) == lib.stat(ref, 4)
            rejects(lambda: wire.execute(ctl, action))
            assert not result.device_effect_or_queue_worker_completion_proven
            done('control-'+str(fault), result=result.public())
            lib.dispose(ref)

        for op in (2, 3):
            failures = [(1, 'BULK_STALL'), (2, 'BULK_TIMEOUT'), (3, 'DISCONNECTED'),
                        (7, 'BUFFER_OR_OUTBOUND_MUTATION'), (8, 'LATE_RETURN'), (9, 'CLOCK_INVALID'),
                        (10, 'OWNER_LOST'), (11, 'OWNER_LOST'), (15, 'BULK_ERROR'),
                        (16, 'CANCEL_REQUESTED'), (17, 'LATE_RETURN')]
            failures += [(4, 'BUFFER_OR_OUTBOUND_MUTATION')] if op == 2 else [(5, 'SHORT_TRANSFER'), (6, 'INVALID_NATIVE_COUNT')]
            for fault, want in failures:
                ref, b, budget, wire, ctl, action = setup(auth=True)
                lib.set_reply(ref, packet(8, b'\x01'+b'x'*511))
                lib.fault(ref, op, fault)
                result = wire.execute(ctl, action)
                assert result.status == want, (op, fault, result.public())
                assert counts(ref) == [1, 1, int(op == 3)]
                assert not result.reply and budget.failed and budget.exchanges['MSC'] == 1
                rejects(lambda: wire.execute(ctl, action))
                assert len(result.calls) == op-1
                if fault in (1, 2, 3, 15):
                    assert result.calls[-1]['raw_return'] != 0
                if op == 3 and fault == 2:
                    assert result.calls[-1]['reported_count'] == 516
                    assert result.calls[-1]['transferred'] is None and not result.calls[-1]['actual_count_known']
                done('bulk-'+str(op)+'-fault-'+str(fault), result=result.public())
                lib.dispose(ref)

        for reverse in (False, True):
            ref, b, budget, wire, ctl, action = setup(auth=True, reverse=reverse)
            lib.set_reply(ref, packet(8, b'PRIVATE_FIXTURE_ONLY'.ljust(512, b'x')))
            result = wire.execute(ctl, action)
            assert result.status == 'AUTH_REPLY_VALID'
            assert not result.calls[0]['actual_count_known'] and result.calls[0]['transferred'] is None
            assert result.calls[1]['actual_count_known'] and result.calls[1]['transferred'] == 516
            assert lib.stat(ref, 5) == (1 if reverse else 2) and lib.stat(ref, 6) == (2 if reverse else 1)
            assert lib.sent(ref) == action.wire and 'PRIVATE_FIXTURE_ONLY' not in json.dumps(result.public())
            done('IOKit-pipe-index-and-unknown-write-count-'+str(reverse), result=result.public())
            lib.dispose(ref)

        ref, b, budget, wire, ctl, action = setup()
        action = replace(action, deadline=1.0004)
        ctl.pending = action
        assert wire.execute(ctl, action).status == 'CONTROL_OK' and lib.stat(ref, 3) == 1
        done('submillisecond-positive-timeout')
        lib.dispose(ref)

        for change in ({'handle': 0x1234}, {'handle': False}, {'ep_in': 0x83}, {'max_packet': 1024},
                       {'authentication_endpoint_roles_reviewed': False}, {'exclusive_ownership_confirmed': False}):
            ref = lib.create()
            rejects(lambda: w.from_fixture(lib, replace(binding(ref), **change), w.SessionBudget(61), lambda: clock(ref)))
            assert counts(ref) == [0, 0, 0]
            done('binding-reject-'+str(next(iter(change))))
            lib.dispose(ref)
        ref = lib.create()
        forged = replace(ref, _address=0x1234)
        rejects(lambda: lib.refresh(forged))
        with patch.object(os, 'getpid', return_value=os.getpid()+1):
            rejects(lambda: lib.refresh(ref))
        lib.dispose(ref)
        rejects(lambda: lib.refresh(ref))
        done('unregistered-forked-disposed-contexts-rejected-before-dereference')
        class Trap:
            def __getattr__(self, name):
                raise AssertionError('native lookup before live gate: '+name)
        with patch.object(C, 'CDLL', side_effect=AssertionError('real loader forbidden')):
            rejects(lambda: w.from_live(Trap(), b, w.SessionBudget(61), lambda: 1))
            with patch.object(w, 'live_authority', return_value=None):
                rejects(lambda: w.from_live(Trap(), b, w.SessionBudget(61), lambda: 1))
        done('live-denied-before-native-lookup-even-with-synthetic-authority')

        for change in ({'wire': bytes(515)}, {'wire': packet(0xff01)}, {'wire': packet(1, b'\x01')},
                       {'wire': bytearray(packet(1))}, {'kind': 'CAPTURE'}):
            ref, b, budget, wire, ctl, action = setup(auth=True)
            invalid = replace(action, **change)
            ctl.pending = invalid
            rejects(lambda: wire.execute(ctl, invalid))
            assert counts(ref) == [1, 0, 0]
            done('auth-shape-rejected-'+str(next(iter(change))))
            lib.dispose(ref)

        ref, b, budget, wire, ctl, action = setup(auth=True)
        lib.fault(ref, 2, 12)
        results, errors = [], []
        def run_blocked():
            try:
                results.append(wire.execute(ctl, action))
            except BaseException as error:
                errors.append(type(error).__name__)
        lib.set_reply(ref, packet(8))
        worker = threading.Thread(target=run_blocked)
        worker.start()
        try:
            deadline = time.monotonic()+2
            while not lib.stat(ref, 17) and time.monotonic() < deadline:
                time.sleep(0.002)
            assert lib.stat(ref, 17) == 1 and lib.pending(ref) == 2
            for call in (lambda: wire.execute(ctl, action), wire.invalidate,
                         lambda: lib.dispose(ref), lambda: lib.refresh(ref), lambda: lib.invalidate(ref)):
                rejects(call)
            # Direct same-process C guard also returns BUSY; it never closes the fixture.
            assert lib.library.fx3_io_refresh(ref._address, ref.generation) == 2
            assert lib.library.fx3_io_invalidate(ref._address, ref.generation) == 2
            assert lib.library.fx3_iokit_fixture_dispose(ref._address) == 2
            assert worker.is_alive() and lib.pending(ref) == 2
        finally:
            lib.release(ref)  # Release our fake callback only, not cancel a device call.
            worker.join(timeout=2)
        assert not worker.is_alive() and not errors and results[0].status == 'AUTH_REPLY_VALID'
        assert counts(ref) == [1, 1, 1] and lib.pending(ref) == 0
        done('real-blocked-fake-C-call-retains-owner-and-refuses-cleanup', result=results[0].public())
        lib.dispose(ref)

        # A completed STALL can admit only a separately requested STOP after fresh observation.
        ref, b, budget, wire, ctl, action = setup(auth=True)
        lib.fault(ref, 2, 1)
        assert wire.execute(ctl, action).status == 'BULK_STALL'
        ctl.accept(s.Receipt(action.token, outcome='error'), clock(ref))
        check = ctl.next_inert_action(clock(ref))
        ctl.accept(s.Receipt(check.token, snapshot=s.Snapshot(clock(ref), (device(),))), clock(ref))
        stop = ctl.next_inert_action(clock(ref))
        assert stop.phase == 'STOP'
        rejects(lambda: wire.execute(ctl, stop))
        wire.observe(observation(b, clock(ref)))
        lib.fault(ref, 0, 0)
        result = wire.execute(ctl, stop)
        assert result.status == 'CONTROL_OK' and counts(ref) == [2, 1, 0]
        assert [lib.stat(ref, i) for i in (9, 10)] == [0xc800, 0x2855]
        another = replace(stop, token=stop.token+'-new')
        ctl.pending = another
        rejects(lambda: wire.execute(ctl, another))
        done('explicit-single-STOP-only-after-new-owner-observation', result=result.public())
        lib.dispose(ref)

        # Full pure-controller flows: all body/driver/physical observations are invented fixtures.
        for family in (2, 8):
            refs = {m: lib.create(m, generation=1 if m == 'MSC' else 2) for m in ('MSC', 'SERVICE')}
            now = 1.0
            budget = w.SessionBudget(61)
            provider = p.ModeDigestProvider()
            ctl = s.SessionController(s.Target('fixture-body-0001', 'fixture-port-0001'),
                                      s.Snapshot(now, (device(driver=True),)), s.Limits(60, 3, 2, 0.01, 4), now=now)
            mode, driver = 'MSC', True
            wires, actions = {}, []
            rounds = {'MSC': 0, 'SERVICE': 0}
            for unused in range(120):
                for ref in refs.values():
                    assert lib.set_clock(ref, now) == 0
                now = clock(refs['MSC'])
                if ctl.phase == 'WAIT_PHYSICAL':
                    ctl.confirm_physical('fixture-body-0001', True, True, now)
                    break
                action = ctl.next_inert_action(now)
                assert action is not None
                if action.kind == 'OBSERVE_CACHE':
                    receipt = s.Receipt(action.token, snapshot=s.Snapshot(now, (device(mode, driver),)))
                elif action.phase in ('CAPTURE', 'OPEN_SERVICE'):
                    if action.phase == 'CAPTURE':
                        driver = False
                    wires[mode] = w.from_fixture(lib, binding(refs[mode]), budget, lambda ref=refs[mode]: clock(ref))
                    receipt = s.Receipt(action.token, effect_observed=True)
                elif action.phase == 'CLOSE_STALE':
                    wires['MSC'].invalidate()
                    receipt = s.Receipt(action.token, effect_observed=True)
                elif action.phase == 'DERIVE_DIGEST':
                    receipt = s.Receipt(action.token, wire=provider.compute_bound_task(provider.bind_inert_task(ctl, action)))
                elif action.phase.startswith(('START_', 'AUTH_')) or action.phase == 'STOP':
                    wire = wires[mode]
                    wire.observe(observation(binding(refs[mode]), now))
                    if action.phase.startswith('AUTH_'):
                        cmd = (~struct.unpack('>H', action.wire[:2])[0])&0xffff
                        if cmd == 1:
                            reply = packet(family if mode == 'MSC' else 8, b'\x01'+bytes([rounds[mode]+7])*511)
                        elif cmd == 3:
                            reply = packet(4)
                            rounds[mode] += 1
                        else:
                            assert cmd == 5
                            reply = packet(6, b'\x01')
                        lib.set_reply(refs[mode], reply)
                    result = wire.execute(ctl, action)
                    assert result.status in ('CONTROL_OK', 'AUTH_REPLY_VALID'), result.public()
                    actions.append({'phase': action.phase, **result.public()})
                    receipt = s.Receipt(action.token, wire=result.reply, raw_return=result.calls[-1]['raw_return'])
                    if action.phase.startswith('START_'):
                        wire.observe(observation(binding(refs[mode]), now))
                        wire.arm_authentication_after_start()
                    if action.phase == 'AUTH_MSC' and budget.auth['MSC']['complete']:
                        mode = 'SERVICE'
                    if action.phase == 'STOP':
                        mode, driver = 'MSC', False
                else:
                    if action.phase == 'RESTORE':
                        driver = True
                    if action.phase == 'DISPOSE':
                        wires['SERVICE'].invalidate()
                    receipt = s.Receipt(action.token, effect_observed=True)
                now = (round(now*1e9)+10000000)/1e9
                ctl.accept(receipt, now)
            else:
                raise AssertionError('fixture flow did not finish')
            assert ctl.phase == 'FLOW_FINISHED' and budget.exchanges == {'MSC': 7, 'SERVICE': 7}
            assert budget.starts == {'MSC': 1, 'SERVICE': 1} and budget.stop and len(budget.tokens) == 17
            total = [sum(counts(ref)[i] for ref in refs.values()) for i in range(3)]
            assert total == [3, 14, 14]
            assert all(not x['device_effect_or_queue_worker_completion_proven'] for x in actions)
            flows.append({'MSC_reference_family': family, 'fixture_calls': total, 'actions': actions,
                          'controller_report': ctl.report(), 'all_body_mode_driver_and_physical_evidence_synthetic': True})
            for ref in refs.values():
                lib.dispose(ref)
        assert not lib.refs
        report['status'] = 'PASS_SDK_TYPED_IOKIT_FAKE_VTABLE_AND_INERT_CONTROLLER_ONLY'
    except BaseException as error:
        report['status'] = 'FAIL'
        report['error'] = {'type': type(error).__name__, 'text': str(error), 'traceback': traceback.format_exc()}
        raise
    finally:
        report['case_count'], report['flow_count'] = len(cases), len(flows)
        report['sources'] = {name: sha256((out/name).read_bytes()).hexdigest() for name in (
            'iokit_wire.h', 'iokit_wire.c', 'fake_iokit.c', 'iokit_wire.py', 'iokit_fixture_api.py', 'test_iokit_wire.py')}
        (out/'results.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps({'status': report['status'], 'cases': len(cases), 'inert_flows': len(flows), 'real_USB': 0}))


if __name__ == '__main__':
    main()
