#!/usr/bin/env python3
"""Fault injection into inert intents only. No camera/driver/USB package is imported."""
from pathlib import Path
from hashlib import sha256
from dataclasses import replace
import ast
import importlib.util
import json
import struct
import sys

HERE = Path(__file__).resolve().parent
OUT = HERE / 'run-fault-injection'
TAG, PORT = 'fixture-body-identity-private', 'fixture-physical-port-private'


def load_core():
    spec = importlib.util.spec_from_file_location('fx3_inert_session', HERE / 'session_controller.py')
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def main():
    s = load_core()
    source = (HERE / 'session_controller.py').read_bytes()
    parsed = ast.parse(source)
    imports = [n.module for n in ast.walk(parsed) if isinstance(n, ast.ImportFrom)]
    imports += [a.name for n in ast.walk(parsed) if isinstance(n, ast.Import) for a in n.names]
    assert set(imports) <= {'dataclasses', 'math', 'secrets', 'struct'}
    assert not any(isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id in {'open', 'exec', 'eval', '__import__'} for n in ast.walk(parsed))
    assert s.auth_packet(1) == bytes.fromhex('fffe0000') + bytes(512)
    assert s.auth_packet(5) == bytes.fromhex('fffa0000') + bytes(512)
    assert s.auth_packet(3, b'\x01' + bytes([0xa5]) * 32) == bytes.fromhex('fffc000001') + bytes([0xa5]) * 32 + bytes(479)
    code, data = s.parse_auth_response(bytes.fromhex('fff60003') + b'\x01' + bytes(511))
    assert code == 6 and data[0] == 1
    for wire in (bytes(515), bytes(517), bytes.fromhex('ffff0001') + bytes(512)):
        try:
            s.parse_auth_response(wire)
            raise AssertionError('invalid frame accepted')
        except s.Rejected:
            pass

    def digest(family, round_number, challenge):
        # A test digest, NOT Sony credentials or successful cryptographic authentication.
        length = 20 if family == 2 else 32
        return sha256(b'OFFLINE_FIXTURE_ONLY' + bytes([family, round_number]) + challenge).digest()[:length]

    target = s.Target(TAG, PORT)
    limits = s.Limits(session=40.0, operation=2.0, cache_age=5.0, poll_gap=0.05, polls_per_phase=4)
    def device(mode='MSC', driver=True, **changes):
        d = s.Device(TAG, PORT, mode, 0x054c, 0x0da1 if mode == 'MSC' else 0x0336,
                     8 if mode == 'MSC' else 255, True, driver)
        return replace(d, **changes)
    def snapshot(now=0.0, d=None):
        return s.Snapshot(now, (d or device(),))
    def response(code, payload=b''):
        salt = 3
        return struct.pack('>HH', (~(code + salt)) & 0xffff, salt) + payload.ljust(512, b'\0')

    class World:
        def __init__(self, family, provider):
            self.mode, self.driver, self.family = 'MSC', True, family
            self.provider = provider
            self.sequences = {'MSC': [], 'SERVICE': []}
            self.challenges = {}
        def reply(self, a, now):
            if a.phase == 'DERIVE_DIGEST':
                try:
                    value=self.provider(a.digest_family,a.digest_round,a.private_payload)
                    return s.Receipt(a.token,wire=value)
                except Exception:
                    return s.Receipt(a.token,outcome='error')
            if a.kind == 'OBSERVE_CACHE':
                return s.Receipt(a.token, snapshot=snapshot(now, device(self.mode, self.driver)))
            if a.phase == 'CAPTURE':
                self.driver = False
                return s.Receipt(a.token, effect_observed=True)
            if a.phase.startswith('START_'):
                assert a.wire == bytes.fromhex('4301ff37aad70000')
            if a.phase.startswith('AUTH_'):
                mode = a.phase[5:]
                commands = [1, 3, 1, 3, 1, 3, 5]
                index = len(self.sequences[mode])
                assert index < len(commands) and len(a.wire) == 516
                header, salt = struct.unpack('>HH', a.wire[:4])
                command = (~header) & 0xffff
                assert command == commands[index] and salt == 0
                self.sequences[mode].append(command)
                if command == 1:
                    challenge = bytes([0x30 + index]) * 512
                    self.challenges[mode] = challenge
                    wire = response(self.family, challenge)
                elif command == 3:
                    expected = b'\x01' + digest(self.family, index // 2, self.challenges[mode])
                    assert a.wire[4:] == expected.ljust(512, b'\0')
                    wire = response(4)
                else:
                    wire = response(6, b'\x01')
                    if mode == 'MSC':
                        self.mode = 'SERVICE'
                return s.Receipt(a.token, wire=wire)
            if a.phase == 'STOP':
                assert a.wire == bytes.fromhex('430100c855280000')
                self.mode, self.driver = 'MSC', False
            elif a.phase == 'RESTORE':
                self.driver = True
            return s.Receipt(a.token, effect_observed=True)

    results = []
    def drive(name, inject=None, family=8, target_override=None, initial=None, limit_override=None,
              provider=None, confirm=True, first_time=0.0):
        c = s.SessionController(target_override or target, initial or snapshot(), limit_override or limits)
        w, now, actions = World(family, provider or digest), first_time, []
        for unused in range(250):
            if c.phase in s.TERMINAL:
                break
            if c.phase == 'WAIT_PHYSICAL':
                if confirm:
                    c.confirm_physical(TAG, True, True, now)
                break
            a = c.next_inert_action(now)
            if a is None:
                now += 0.06
                continue
            actions.append({'phase': a.phase, 'kind': a.kind, 'wire_bytes': len(a.wire)})
            assert a.inert_only and a.kind not in {'RESET', 'FLASH', 'FILE_READ', 'FILE_WRITE'}
            if inject:
                custom = inject(c, w, a, now)
            else:
                custom = None
            receipt = custom if custom is not None else w.reply(a, now)
            c.accept(receipt, now + 0.001)
            assert c.starts['MSC'] <= 1 and c.starts['SERVICE'] <= 1 and int(c.stop_intent) <= 1
            assert max(c.auth_exchanges.values()) <= 7
            now += 0.01
        else:
            raise AssertionError('unbounded inert flow: ' + name)
        report = c.report()
        encoded = json.dumps(report)
        assert TAG not in encoded and PORT not in encoded and 'OFFLINE_FIXTURE_ONLY' not in encoded
        assert not report['actual_hardware_acceptance'] and not report['live_release']
        assert not report['evidence']['worker_completion']
        results.append({'name': name, 'actions': actions, 'report': report})
        return c, w, actions

    for family in (8, 2):
        c,w,a = drive('complete_fixture_family' + str(family), family=family)
        assert c.phase == 'FLOW_FINISHED' and c.starts == {'MSC': 1, 'SERVICE': 1}
        assert c.auth_exchanges == {'MSC': 7, 'SERVICE': 7} and c.stop_intent
        assert w.sequences == {'MSC': [1,3,1,3,1,3,5], 'SERVICE': [1,3,1,3,1,3,5]}

    initial_cases = [
        ('wrong_model', {'target_override': replace(target, model='ILME-FX3A')}),
        ('wrong_version', {'target_override': replace(target, firmware='7.01')}),
        ('missing_identity', {'target_override': replace(target, identity_tag='')}),
        ('stale_initial', {'initial': snapshot(-6)}),
        ('future_initial', {'initial': snapshot(1)}),
        ('ambiguous_initial', {'initial': s.Snapshot(0.0, (device(),device()))}),
        ('same_body_unproven', {'initial': snapshot(d=device(same_body_proof=False))}),
        ('wrong_MSC_PID', {'initial': snapshot(d=device(pid=0x0336))}),
        ('already_service_not_initial_MSC', {'initial': snapshot(d=device('SERVICE'))}),
        ('nonfinite_limit', {'limit_override': replace(limits, operation=float('nan'))}),
        ('negative_limit', {'limit_override': replace(limits, cache_age=-1)})]
    for name, kwargs in initial_cases:
        c,w,a = drive(name, **kwargs)
        assert c.phase == 'REJECTED' and not a

    def once(phase, transform):
        used = False
        def inject(c,w,a,now):
            nonlocal used
            if not used and a.phase == phase:
                used = True
                return transform(c,w,a,now)
            return None
        return inject

    faults = [
        ('MSC_invalid_challenge', 'AUTH_MSC', lambda c,w,a,n:s.Receipt(a.token, wire=response(9))),
        ('MSC_truncated_response', 'AUTH_MSC', lambda c,w,a,n:s.Receipt(a.token, wire=b'x'*515)),
        ('SERVICE_transport_error_finished', 'AUTH_SERVICE', lambda c,w,a,n:s.Receipt(a.token, outcome='error', raw_return=5)),
        ('SERVICE_denied_auth', 'AUTH_SERVICE', lambda c,w,a,n:s.Receipt(a.token, wire=response(6,b'\0')))]
    for name, phase, transform in faults:
        c,w,a = drive(name, inject=once(phase, transform))
        assert c.phase == 'FLOW_FINISHED_WITH_ERRORS' and c.stop_intent
        assert sum(x['phase']=='STOP' for x in a) == 1

    def failed_provider(*unused):
        raise ValueError(TAG + ' private provider text must not be logged')
    c,w,a = drive('provider_exception', provider=failed_provider)
    assert c.phase == 'FLOW_FINISHED_WITH_ERRORS' and c.auth_exchanges['MSC'] == 1
    c,w,a = drive('provider_wrong_digest_length', provider=lambda *unused:b'bad')
    assert c.phase == 'FLOW_FINISHED_WITH_ERRORS' and c.auth_exchanges['MSC'] == 1

    def final_denial(c,w,a,now):
        if a.phase=='AUTH_SERVICE' and a.wire[:2]==bytes.fromhex('fffa'):
            w.reply(a,now)
            return s.Receipt(a.token,wire=response(6,b'\0'))
        return None
    c,w,a=drive('SERVICE_final_acceptance_denied',inject=final_denial)
    assert c.phase=='FLOW_FINISHED_WITH_ERRORS' and c.auth_exchanges['SERVICE']==7
    def wrong_digest_ack(c,w,a,now):
        if a.phase=='AUTH_MSC' and a.wire[:2]==bytes.fromhex('fffc'):
            w.reply(a,now)
            return s.Receipt(a.token,wire=response(5))
        return None
    c,w,a=drive('MSC_digest_ack_invalid',inject=wrong_digest_ack)
    assert c.phase=='FLOW_FINISHED_WITH_ERRORS' and c.auth_exchanges['MSC']==2

    for phase in ('CAPTURE','START_MSC','AUTH_MSC','DERIVE_DIGEST','STOP','RESTORE','DISPOSE'):
        c,w,a = drive('pending_' + phase, inject=once(phase, lambda c,w,a,n:s.Receipt(a.token,outcome='pending',operation_finished=False)))
        assert c.phase == 'UNKNOWN'
        before = len(a)
        assert c.next_inert_action(c.last_now+0.01) is None and len(a)==before

    def stop_error_but_effect(c,w,a,now):
        r = w.reply(a,now)
        return replace(r, outcome='error', raw_return=5)
    c,w,a = drive('stop_error_already_effected', inject=once('STOP',stop_error_but_effect))
    assert c.phase == 'FLOW_FINISHED_WITH_ERRORS' and sum(x['phase']=='STOP' for x in a)==1
    c,w,a = drive('stop0_no_observed_effect', inject=once('STOP',lambda c,w,a,n:s.Receipt(a.token,raw_return=0)))
    assert c.phase == 'UNKNOWN' and sum(x['phase']=='STOP' for x in a)==1
    c,w,a = drive('restore0_driver_not_bound',inject=once('RESTORE',lambda c,w,a,n:s.Receipt(a.token,raw_return=0)))
    assert c.phase == 'UNKNOWN' and not c.evidence['driver_restored']
    def dispose_loses_driver(c,w,a,now):
        w.driver=False
        return s.Receipt(a.token,raw_return=0)
    c,w,a = drive('dispose0_loses_driver',inject=once('DISPOSE',dispose_loses_driver))
    assert c.phase == 'UNKNOWN' and not c.evidence['closed_driver_observed']

    for name, d in [('replaced_body',device('SERVICE',identity_tag='different-fixture-body')),
                    ('rebind_proof_missing',device('SERVICE',same_body_proof=False))]:
        c,w,a=drive(name,inject=once('OBS_SERVICE',lambda c,w,a,n,d=d:s.Receipt(a.token,snapshot=snapshot(n,d))))
        assert c.phase == 'UNKNOWN' and not any(x['phase'] in {'OPEN_SERVICE','START_SERVICE','STOP'} for x in a)
    c,w,a=drive('ambiguous_reenumeration',inject=once('OBS_SERVICE',lambda c,w,a,n:s.Receipt(a.token,snapshot=s.Snapshot(n,(device('SERVICE'),device('SERVICE'))))))
    assert c.phase == 'UNKNOWN'
    for phase in ('CLOSE_STALE','OPEN_SERVICE'):
        c,w,a=drive('failed_' + phase,inject=once(phase,lambda c,w,a,n:s.Receipt(a.token,outcome='error')))
        assert c.phase == 'UNKNOWN' and not any(x['phase']=='STOP' for x in a)

    c,w,a=drive('capture0_ownership_unproven',inject=once('CAPTURE',lambda c,w,a,n:s.Receipt(a.token,raw_return=0)))
    assert c.phase=='UNKNOWN' and not any(x['phase']=='START_MSC' for x in a)
    c,w,a=drive('close_stale0_effect_unproven',inject=once('CLOSE_STALE',lambda c,w,a,n:s.Receipt(a.token,raw_return=0)))
    assert c.phase=='UNKNOWN' and not any(x['phase'] in {'OPEN_SERVICE','STOP'} for x in a)

    c,w,a=drive('cache_expires_before_capture',first_time=6.0)
    assert a[0]['phase']=='OBS_IDENTITY' and c.phase=='FLOW_FINISHED'
    c,w,a=drive('whole_session_deadline_before_capture',first_time=41.0)
    assert c.phase=='UNKNOWN' and not a
    c,w,a=drive('physical_receipt_still_missing',confirm=False)
    assert c.phase=='WAIT_PHYSICAL' and not c.evidence['physical_operation']
    c.confirm_physical(TAG,False,True,c.last_now+1)
    assert c.phase=='UNKNOWN'
    results.append({'name':'physical_confirmation_rejected','report':c.report()})

    replay=s.SessionController(target,snapshot(),limits)
    old=replay.next_inert_action(0)
    replay.accept(s.Receipt(old.token,effect_observed=True),0.01)
    replay.accept(s.Receipt(old.token,effect_observed=True),0.02)
    assert replay.phase=='UNKNOWN' and replay.next_inert_action(0.03) is None
    results.append({'name':'same_session_receipt_replay_rejected','report':replay.report()})

    # Session tokens reject stale receipts from a different controller.
    left=s.SessionController(target,snapshot(),limits)
    right=s.SessionController(target,snapshot(),limits)
    la,ra=left.next_inert_action(0),right.next_inert_action(0)
    assert la.token!=ra.token
    left.accept(s.Receipt(ra.token,effect_observed=True),0.01)
    assert left.phase=='UNKNOWN' and left.next_inert_action(0.02) is None
    results.append({'name':'cross_session_receipt_rejected','report':left.report()})
    late=s.SessionController(target,snapshot(),limits)
    action=late.next_inert_action(0)
    late.accept(s.Receipt(action.token,effect_observed=True),2.01)
    assert late.phase=='UNKNOWN' and late.next_inert_action(2.02) is None
    results.append({'name':'late_completed_receipt_does_not_resume','report':late.report()})
    clock=s.SessionController(target,snapshot(),limits)
    clock.next_inert_action(1)
    try:
        clock.next_inert_action(0)
        raise AssertionError('backwards clock accepted')
    except s.Rejected:
        pass
    assert clock.phase=='UNKNOWN'
    results.append({'name':'backwards_clock_rejected','report':clock.report()})

    # Existing source/authority pins are read only; fixtures never become consent.
    prior=HERE.parent/'stage139-service-callback-bridge-and-queue-return'
    goal_before=(HERE/'goal-status-before.json').read_bytes()
    assert (HERE.parent/'GOAL_STATUS.json').read_bytes()==goal_before
    assert json.loads(goal_before)['authorization']['service_auth_mode_or_stop'] is False
    contract=json.loads((prior/'first-service-trial-contract.json').read_text())
    assert not contract['future_pilot_acceptance_is_not_the_whole_goal']['live_release']
    assert not any(name in sys.modules for name in ('usb','usb.core','usb1'))
    OUT.mkdir(exist_ok=False)
    (OUT/'session-controller-executed.py').write_bytes(source)
    (OUT/'test-executed.py').write_bytes(Path(__file__).read_bytes())
    result={'status':'PASS_INERT_SESSION_FAULT_INJECTION_NOT_USB_AUTHENTICATION_OR_DEVICE_RECOVERY',
        'controller_sha256':sha256(source).hexdigest(),'test_sha256':sha256(Path(__file__).read_bytes()).hexdigest(),
        'case_count':len(results),'cases':results,'codec_golden_vectors':4,'malformed_codec_cases':3,
        'dummy_digest_provider_not_Sony_credentials_or_cryptographic_proof':True,
        'credential_computation_is_external_inert_task_not_inline_callback':True,
        'identities_snapshots_hardware_effects_and_physical_receipts_all_fixtures':True,
        'test_limits':{'session':40,'operation':2,'cache_age':5,'poll_gap':0.05,'polls_per_phase':4,'hardware_validated':False},
        'only_inert_intents_emitted':True,'USB_driver_Windows_or_camera_operations':0,
        'current_authorization_unchanged':True,'live_transport_implemented':False,
        'goal_complete':False,'persistent_write_release':False}
    with (OUT/'results.json').open('x') as handle:
        json.dump(result,handle,ensure_ascii=False,indent=2);handle.write('\n')
    print(json.dumps({'status':result['status'],'cases':len(results),'golden_codec_vectors':4,
                      'dummy_credentials_only':True,'actual_device_operations':0}))


if __name__=='__main__':
    main()
