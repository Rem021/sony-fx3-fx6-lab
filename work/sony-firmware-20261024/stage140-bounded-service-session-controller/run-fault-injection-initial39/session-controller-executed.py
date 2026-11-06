"""Offline intent controller for one FX3 service session. No USB/OS transport exists here.

An adapter, credentials, real timing and corresponding user authority need separate
review. A receipt is input evidence; successful control transfer is not body completion.
"""
from dataclasses import dataclass, field
import math
import secrets
import struct


TERMINAL = {'REJECTED', 'UNKNOWN', 'FLOW_FINISHED', 'FLOW_FINISHED_WITH_ERRORS'}
OBSERVE = {'OBS_CAPTURED', 'OBS_SERVICE', 'OBS_NORMAL', 'OBS_DRIVER', 'OBS_CLOSED',
           'OBS_IDENTITY', 'OBS_RECOVERY'}
ACTIVE = {'CAPTURE', 'START_MSC', 'AUTH_MSC', 'CLOSE_STALE', 'OPEN_SERVICE',
          'START_SERVICE', 'AUTH_SERVICE', 'STOP', 'RESTORE', 'DISPOSE'}


class Rejected(ValueError):
    pass


@dataclass(frozen=True)
class Target:
    identity_tag: str
    port_tag: str
    model: str = 'ILME-FX3'
    firmware: str = '7.02'


@dataclass(frozen=True)
class Device:
    identity_tag: str
    port_tag: str
    mode: str
    vid: int
    pid: int
    interface_class: int
    same_body_proof: bool
    msc_driver_bound: bool = False


@dataclass(frozen=True)
class Snapshot:
    at: float
    devices: tuple[Device, ...]


@dataclass(frozen=True)
class Limits:
    session: float
    operation: float
    cache_age: float
    poll_gap: float
    polls_per_phase: int
    # These numbers are never represented as camera-validated by this module.
    hardware_validated: bool = field(default=False, init=False)


@dataclass(frozen=True)
class Action:
    token: str
    phase: str
    kind: str
    issued_at: float
    deadline: float
    wire: bytes = field(default=b'', repr=False)
    inert_only: bool = field(default=True, init=False)


@dataclass(frozen=True)
class Receipt:
    token: str
    outcome: str = 'ok'  # ok is transport return only, not camera consumption.
    operation_finished: bool = True
    effect_observed: bool = False
    wire: bytes = field(default=b'', repr=False)
    snapshot: Snapshot | None = None
    raw_return: int | None = None  # retained separately; never a completion criterion.


def auth_packet(command, payload=b''):
    if not 0 <= command <= 0xffff or len(payload) > 512:
        raise Rejected('invalid auth packet fields')
    return struct.pack('>HH', (~command) & 0xffff, 0) + payload.ljust(512, b'\0')


def parse_auth_response(wire):
    if not isinstance(wire, bytes) or len(wire) != 516:
        raise Rejected('authentication response must have exactly516 bytes')
    command, salt = struct.unpack('>HH', wire[:4])
    code = ((~command) & 0xffff) - salt
    if not 0 <= code <= 0xffff:
        raise Rejected('invalid authentication response code')
    return code, wire[4:]


class SessionController:
    """Single-use pure controller. next_inert_action performs no action on a device."""
    def __init__(self, target, initial, limits, digest_provider, now=0.0):
        self.target, self.limits, self.digest_provider = target, limits, digest_provider
        self.phase, self.pending = 'CAPTURE', None
        self.ledger, self.errors = [], []
        self.serial = 0
        self.nonce = secrets.token_hex(16)
        self.last_now = now
        self.deadline = now + limits.session
        self.binding_at, self.mode = None, None
        self.captured, self.handle = False, False
        self.enter_intent, self.stop_intent = False, False
        self.starts = {'MSC': 0, 'SERVICE': 0}
        self.auth_exchanges = {'MSC': 0, 'SERVICE': 0}
        self.round, self.command, self.digest = 0, 1, b''
        self.polls, self.next_poll, self.resume = {}, now, None
        self.evidence = {'normal_USB': False, 'driver_restored': False,
                         'closed_driver_observed': False, 'physical_operation': False,
                         'worker_completion': False}
        if target.model != 'ILME-FX3' or target.firmware != '7.02':
            self._reject('wrong_model_or_version')
            return
        if any(not isinstance(x, str) or not 8 <= len(x) <= 128 for x in (target.identity_tag, target.port_tag)):
            self._reject('missing_target_identity')
            return
        numbers = [now, limits.session, limits.operation, limits.cache_age, limits.poll_gap]
        if not all(type(x) in (int, float) and math.isfinite(x) for x in numbers):
            self._reject('nonfinite_limits')
            return
        if min(numbers[1:]) <= 0 or not isinstance(limits.polls_per_phase, int) or limits.polls_per_phase < 1:
            self._reject('invalid_limits')
            return
        try:
            device = self._select(initial, now)
            if device is None or device.mode != 'MSC':
                raise Rejected('initial_MSC_not_proven')
            self._bind(initial, device)
        except Rejected as error:
            self._reject(str(error))

    def _record(self, event, **fields):
        # No raw identity, port, challenge, digest, response or wire bytes in ledger.
        self.ledger.append({'event': event, 'phase': self.phase, **fields})

    def _reject(self, reason):
        self.phase = 'REJECTED'
        self._record('rejected', reason=reason)

    def _unknown(self, reason):
        self.phase = 'UNKNOWN'
        self._record('unknown', reason=reason,
                     unresolved_token=self.pending.token if self.pending else None)

    def _time(self, now):
        if not isinstance(now, (int, float)) or not math.isfinite(now) or now < self.last_now:
            self._unknown('non_monotonic_clock')
            raise Rejected('non_monotonic_clock')
        self.last_now = now
        if self.phase in TERMINAL:
            return
        if self.pending and now > self.pending.deadline:
            self._unknown('deadline_does_not_cancel_backend_or_camera')
        elif now > self.deadline and self.phase != 'WAIT_PHYSICAL':
            self._unknown('whole_session_deadline')

    def _select(self, snapshot, now):
        if not isinstance(snapshot, Snapshot) or not math.isfinite(snapshot.at):
            raise Rejected('invalid_snapshot')
        if snapshot.at > now or now - snapshot.at > self.limits.cache_age:
            raise Rejected('stale_or_future_snapshot')
        matches = [d for d in snapshot.devices
                   if d.port_tag == self.target.port_tag or d.identity_tag == self.target.identity_tag]
        if len(matches) > 1:
            raise Rejected('ambiguous_identity')
        if not matches:
            return None
        d = matches[0]
        if d.identity_tag != self.target.identity_tag or d.port_tag != self.target.port_tag or d.same_body_proof is not True:
            raise Rejected('same_body_identity_unproven')
        profile = {'MSC': (0x054c, 0x0da1, 8), 'SERVICE': (0x054c, 0x0336, 255)}
        if d.mode not in profile or (d.vid, d.pid, d.interface_class) != profile[d.mode]:
            raise Rejected('unreviewed_USB_profile')
        return d

    def _bind(self, snapshot, device):
        self.binding_at, self.mode = snapshot.at, device.mode

    def _poll_again(self, now):
        self.polls[self.phase] = self.polls.get(self.phase, 0) + 1
        if self.polls[self.phase] >= self.limits.polls_per_phase:
            self._unknown('passive_observation_limit')
        else:
            self.next_poll = now + self.limits.poll_gap

    def next_inert_action(self, now):
        self._time(now)
        if self.phase in TERMINAL or self.phase == 'WAIT_PHYSICAL' or self.pending:
            return None
        if self.phase in OBSERVE and now < self.next_poll:
            return None
        if self.phase in ACTIVE and (
                self.binding_at is None or now - self.binding_at > self.limits.cache_age):
            self.resume, self.phase = self.phase, 'OBS_IDENTITY'
            self.next_poll = now
        phase = self.phase
        wire = b''
        if phase.startswith('START_'):
            mode = phase[6:]
            if self.starts[mode]:
                self._unknown('start_replay_forbidden')
                return None
            self.starts[mode] += 1
            self.enter_intent = True  # before an adapter could send the first transfer.
            wire = bytes.fromhex('4301ff37aad70000')
        elif phase.startswith('AUTH_'):
            mode = phase[5:]
            if self.auth_exchanges[mode] >= 7:
                self._unknown('authentication_budget')
                return None
            self.auth_exchanges[mode] += 1
            wire = auth_packet(self.command, b'\x01' + self.digest if self.command == 3 else b'')
        elif phase == 'STOP':
            if self.stop_intent or not self.enter_intent or not self.handle:
                self._unknown('stop_not_admitted')
                return None
            self.stop_intent = True  # an uncertain return still consumes the sole attempt.
            wire = bytes.fromhex('430100c855280000')
        elif phase in {'RESTORE', 'DISPOSE'} and (not self.captured or not self.handle):
            self._unknown('restoration_handle_or_lease_unproven')
            return None
        self.serial += 1
        kind = 'OBSERVE_CACHE' if phase in OBSERVE else phase
        token = self.nonce + '-' + str(self.serial)
        action = Action(token, phase, kind, now, min(self.deadline, now + self.limits.operation), wire)
        self.pending = action
        self._record('intent_before_dispatch', token=token, kind=kind, wire_bytes=len(wire), deadline=action.deadline)
        return action

    def _failure(self, phase, outcome, now):
        self.errors.append({'phase': phase, 'outcome': outcome})
        if phase in {'STOP', 'RESTORE', 'DISPOSE'}:
            if phase == 'STOP':
                self.phase = 'OBS_NORMAL'  # observe once/limited polls; never send stop again.
                self.next_poll = now
            else:
                self._unknown('restore_or_close_failure')
        elif self.enter_intent and self.captured and self.handle:
            self.phase, self.next_poll = 'OBS_RECOVERY', now
        elif not self.enter_intent and self.captured and self.handle:
            self.phase, self.next_poll = 'OBS_NORMAL', now
        else:
            self._unknown('no_confirmed_cleanup_handle')

    def accept(self, receipt, now):
        self._time(now)
        if self.phase in TERMINAL:
            self._record('late_or_terminal_receipt_ignored')
            return
        if not self.pending or receipt.token != self.pending.token:
            self._unknown('out_of_order_or_replayed_receipt')
            return
        action = self.pending
        if receipt.operation_finished is not True or receipt.outcome == 'pending':
            self._unknown('backend_may_still_be_inflight')
            return
        self.pending = None
        self._record('transport_receipt_not_completion', token=action.token,
                     outcome=receipt.outcome, raw_return=receipt.raw_return)
        if receipt.outcome not in {'ok', 'error', 'no_effect'}:
            self._unknown('unreviewed_receipt_type')
            return
        if action.phase in OBSERVE:
            if receipt.outcome != 'ok':
                self._unknown('cache_observation_error')
                return
            self._observation(receipt.snapshot, now)
            return
        if action.phase == 'CAPTURE':
            if receipt.outcome != 'ok' or receipt.effect_observed is not True:
                self._unknown('capture_effect_or_ownership_unproven')
                return
            self.captured, self.handle = True, True
        elif action.phase == 'CLOSE_STALE' and (receipt.outcome != 'ok' or receipt.effect_observed is not True):
            self.handle = False
            self._unknown('stale_handle_close_uncertain')
            return
        elif receipt.outcome != 'ok':
            self._failure(action.phase, receipt.outcome, now)
            return
        if action.phase.startswith('AUTH_'):
            try:
                self._auth_reply(receipt.wire)
            except Exception:
                # Provider/parser exceptions are not hidden; record bounded category,
                # avoid dumping a challenge/digest, and go through cleanup admission.
                self._failure(action.phase, 'authentication_or_provider_error', now)
            return
        transitions = {'CAPTURE': 'OBS_CAPTURED', 'START_MSC': 'AUTH_MSC',
                       'CLOSE_STALE': 'OPEN_SERVICE', 'OPEN_SERVICE': 'START_SERVICE',
                       'START_SERVICE': 'AUTH_SERVICE', 'STOP': 'OBS_NORMAL',
                       'RESTORE': 'OBS_DRIVER', 'DISPOSE': 'OBS_CLOSED'}
        if action.phase == 'CLOSE_STALE':
            self.handle = False
        elif action.phase == 'OPEN_SERVICE':
            if receipt.effect_observed is not True:
                self._unknown('service_handle_open_unproven')
                return
            self.handle = True
        elif action.phase == 'DISPOSE':
            self.handle = False
        self.phase = transitions[action.phase]
        self.next_poll = now

    def _auth_reply(self, wire):
        code, data = parse_auth_response(wire)
        if self.command == 1:
            if code not in (2, 8):
                raise Rejected('unexpected_challenge_code')
            digest = self.digest_provider(code, self.round, data)
            if not isinstance(digest, bytes) or len(digest) != (20 if code == 2 else 32):
                raise Rejected('invalid_provider_digest')
            self.digest, self.command = digest, 3
        elif self.command == 3:
            if code != 4:
                raise Rejected('unexpected_digest_ack')
            self.round += 1
            self.command = 5 if self.round == 3 else 1
        else:
            if code != 6 or data[0] != 1:
                raise Rejected('authentication_not_accepted')
            mode = self.phase[5:]
            self.phase = 'OBS_SERVICE' if mode == 'MSC' else 'STOP'
            self.round, self.command, self.digest = 0, 1, b''

    def _observation(self, snapshot, now):
        try:
            device = self._select(snapshot, now)
        except Rejected as error:
            self._unknown(str(error))
            return
        if device is None:
            self._poll_again(now)
            return
        phase = self.phase
        if phase == 'OBS_RECOVERY':
            self._bind(snapshot, device)
            if not self.handle or not self.enter_intent or self.stop_intent:
                self._unknown('cleanup_stop_not_admitted')
            else:
                self.phase = 'STOP'
            return
        expected = 'SERVICE' if phase == 'OBS_SERVICE' else 'MSC'
        if phase == 'OBS_IDENTITY':
            expected = self.mode
        if device.mode != expected:
            self._poll_again(now)
            return
        self._bind(snapshot, device)
        if phase in {'OBS_DRIVER', 'OBS_CLOSED'} and device.msc_driver_bound is not True:
            self._poll_again(now)
            return
        if phase == 'OBS_IDENTITY':
            self.phase, self.resume = self.resume, None
        elif phase == 'OBS_CAPTURED':
            self.phase = 'START_MSC'
        elif phase == 'OBS_SERVICE':
            self.phase = 'CLOSE_STALE'
        elif phase == 'OBS_NORMAL':
            self.evidence['normal_USB'] = True
            self.phase = 'RESTORE'
        elif phase == 'OBS_DRIVER':
            self.evidence['driver_restored'] = True
            self.phase = 'DISPOSE'
        elif phase == 'OBS_CLOSED':
            self.evidence['closed_driver_observed'] = True
            self.phase = 'WAIT_PHYSICAL'

    def confirm_physical(self, identity_tag, normal_menu, ordinary_record_replay, now):
        self._time(now)
        if self.phase != 'WAIT_PHYSICAL':
            raise Rejected('physical_confirmation_not_admitted')
        if identity_tag != self.target.identity_tag or normal_menu is not True or ordinary_record_replay is not True:
            self._unknown('physical_normal_operation_unproven')
            return
        self.evidence['physical_operation'] = True
        self.phase = 'FLOW_FINISHED_WITH_ERRORS' if self.errors else 'FLOW_FINISHED'
        self._record('external_physical_receipt_not_H265_or_recovery_acceptance')

    def report(self):
        return {'phase': self.phase, 'starts': dict(self.starts),
                'auth_exchanges': dict(self.auth_exchanges), 'stop_attempts': int(self.stop_intent),
                'evidence': dict(self.evidence), 'errors': list(self.errors), 'ledger': list(self.ledger),
                'body_identity_logged': False, 'wire_challenge_or_digest_logged': False,
                'actual_hardware_acceptance': False, 'live_transport_implemented': False,
                'live_release': False, 'goal_complete': False, 'persistent_write_release': False}
