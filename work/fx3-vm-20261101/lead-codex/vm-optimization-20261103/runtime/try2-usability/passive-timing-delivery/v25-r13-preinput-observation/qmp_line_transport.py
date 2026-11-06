"""Bounded QMP JSON-lines transport; one writer, no resend after uncertainty.

Unlike socket.makefile().readline(), a socket timeout does not poison the
buffer. A partial old line remains buffered and its eventual old id is
discarded before the next command's response is accepted.
"""
from __future__ import annotations

import json
import socket
import time


class QmpDeadline(TimeoutError):
    pass


class QmpProtocolError(RuntimeError):
    pass


class QmpLineTransport:
    def __init__(self, sock: socket.socket, journal: list, *, started: float,
                 default_timeout: float = 3.0, max_line: int = 1 << 20,
                 clock=time.monotonic):
        if default_timeout <= 0 or max_line < 128:
            raise ValueError('invalid QMP bounds')
        self.sock = sock
        self.journal = journal
        self.started = started
        self.default_timeout = default_timeout
        self.max_line = max_line
        self.clock = clock
        self.buffer = bytearray()
        self.sequence = 0
        self.send_unknown = False

    def set_default_timeout(self, seconds: float):
        if not 0 < seconds <= 30:
            raise ValueError('QMP command timeout out of bounds')
        self.default_timeout = seconds

    def _remaining(self, deadline: float) -> float:
        remaining = deadline - self.clock()
        if remaining <= 0:
            raise QmpDeadline('QMP absolute command deadline expired')
        return remaining

    def _line(self, deadline: float) -> bytes:
        while True:
            self._remaining(deadline)  # even an event flood cannot extend a command
            end = self.buffer.find(b'\n')
            if end >= 0:
                if end > self.max_line:
                    raise QmpProtocolError('QMP line exceeds cap')
                line = bytes(self.buffer[:end])
                del self.buffer[:end + 1]
                return line
            if len(self.buffer) > self.max_line:
                raise QmpProtocolError('QMP unterminated line exceeds cap')
            self.sock.settimeout(self._remaining(deadline))
            try:
                part = self.sock.recv(65536)
            except socket.timeout as exc:
                raise QmpDeadline('QMP recv deadline expired; partial line preserved') from exc
            if not part:
                raise EOFError('QMP stream closed before a complete line')
            self.buffer.extend(part)

    def read_json(self, *, timeout: float | None = None):
        duration = self.default_timeout if timeout is None else timeout
        if duration <= 0:
            raise ValueError('QMP timeout must be positive')
        deadline = self.clock() + duration
        while True:
            raw = self._line(deadline)
            if not raw:
                raise QmpProtocolError('empty QMP line')
            try:
                value = json.loads(raw)
            except (UnicodeDecodeError, ValueError) as exc:
                raise QmpProtocolError('invalid QMP JSON line') from exc
            if not isinstance(value, dict):
                raise QmpProtocolError('QMP JSON line is not an object')
            return value

    def command(self, name: str, arguments=None, *, timeout: float | None = None):
        if self.send_unknown:
            raise QmpProtocolError('prior QMP send may be partial; transport cannot append or resend')
        duration = self.default_timeout if timeout is None else timeout
        if duration <= 0 or duration > 30:
            raise ValueError('QMP command timeout out of bounds')
        deadline = self.clock() + duration
        self.sequence += 1
        request_id = self.sequence
        request = {'execute': name, 'id': request_id}
        if arguments is not None:
            request['arguments'] = arguments
        self.journal.append({'request': request, 'elapsed_seconds': self.clock() - self.started})
        payload = (json.dumps(request, separators=(',', ':')) + '\n').encode()
        if len(payload) > 65536:
            raise QmpProtocolError('QMP outbound request exceeds cap')
        self.sock.settimeout(self._remaining(deadline))
        try:
            self.sock.sendall(payload)
        except socket.timeout as exc:
            self.send_unknown = True
            self.journal.append({'send_unknown_id': request_id, 'reason': 'send_deadline'})
            raise QmpDeadline('QMP send deadline expired; request outcome unknown, no resend') from exc
        except OSError as exc:
            self.send_unknown = True
            self.journal.append({'send_unknown_id': request_id, 'reason': repr(exc)})
            raise
        while True:
            # The same absolute deadline covers sends, partial responses,
            # asynchronous events and any number of stale prior-id replies.
            raw = self._line(deadline)
            if not raw:
                raise QmpProtocolError('empty QMP response line')
            try:
                response = json.loads(raw)
            except (UnicodeDecodeError, ValueError) as exc:
                raise QmpProtocolError('invalid QMP response JSON') from exc
            if not isinstance(response, dict):
                raise QmpProtocolError('QMP response is not an object')
            self.journal.append({'response': response})
            if 'event' in response and 'id' not in response:
                continue
            got = response.get('id')
            if type(got) is not int:
                raise QmpProtocolError('QMP response without integer id')
            if got < request_id:
                continue
            if got > request_id:
                raise QmpProtocolError('QMP future response id')
            if 'return' not in response and 'error' not in response:
                raise QmpProtocolError('QMP matched response has no return/error')
            return response
