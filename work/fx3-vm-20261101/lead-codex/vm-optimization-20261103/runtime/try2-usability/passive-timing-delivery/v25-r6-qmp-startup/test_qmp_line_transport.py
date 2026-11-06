"""Real socketpair fault injection: timeout must not poison cleanup commands."""
import json
import socket
import threading
import time

from qmp_line_transport import QmpDeadline, QmpLineTransport, QmpProtocolError


def recv_line(sock):
    raw = bytearray()
    while not raw.endswith(b'\n'):
        part = sock.recv(4096)
        if not part:
            raise EOFError('test peer closed')
        raw.extend(part)
    return json.loads(raw)


def test_late_partial_and_event():
    client, peer = socket.socketpair()
    events = []
    def server():
        try:
            peer.sendall(b'{"QMP":{"version":{},"capabilities":[]}}\n')
            first = recv_line(peer)
            assert first['id'] == 1
            peer.sendall(b'{"return":{"late":')  # old response is incomplete
            time.sleep(.08)
            peer.sendall(b'true},"id":1}\n{"event":"TEST","data":{}}\n')
            second = recv_line(peer)
            assert second['id'] == 2 and second['execute'] == 'cont'
            peer.sendall(b'{"return":{},')
            time.sleep(.01)
            peer.sendall(b'"id":2}\n')
        except Exception as exc:
            events.append(repr(exc))
        finally:
            peer.close()
    thread = threading.Thread(target=server)
    thread.start()
    journal = []
    qmp = QmpLineTransport(client, journal, started=time.monotonic())
    assert 'QMP' in qmp.read_json(timeout=.5)
    try:
        qmp.command('query-cpus-fast', timeout=.03)
    except QmpDeadline:
        pass
    else:
        raise AssertionError('partial old QMP line should time out')
    assert qmp.command('cont', timeout=.5) == {'return': {}, 'id': 2}
    assert [x['response'].get('id') for x in journal if 'response' in x] == [1, None, 2]
    client.close()
    thread.join(timeout=2)
    assert not thread.is_alive() and not events, events


def test_event_flood_deadline():
    client, peer = socket.socketpair()
    def server():
        try:
            recv_line(peer)
            for _ in range(100):
                peer.sendall(b'{"event":"FLOOD","data":{}}\n')
                time.sleep(.001)
        except OSError:
            pass
        finally:
            peer.close()
    thread = threading.Thread(target=server)
    thread.start()
    qmp = QmpLineTransport(client, [], started=time.monotonic())
    begin = time.monotonic()
    try:
        qmp.command('query-status', timeout=.025)
    except QmpDeadline:
        pass
    else:
        raise AssertionError('event stream extended absolute deadline')
    assert time.monotonic() - begin < .15
    client.close()
    thread.join(timeout=2)


def test_disconnect_and_oversize():
    for mode in ('eof', 'oversize'):
        client, peer = socket.socketpair()
        def server():
            recv_line(peer)
            if mode == 'oversize':
                peer.sendall(b'x' * 256)
            peer.close()
        thread = threading.Thread(target=server)
        thread.start()
        qmp = QmpLineTransport(client, [], started=time.monotonic(), max_line=128)
        try:
            qmp.command('query-status', timeout=.5)
        except (EOFError if mode == 'eof' else QmpProtocolError):
            pass
        else:
            raise AssertionError(mode + ' did not fail explicitly')
        client.close()
        thread.join(timeout=2)


def test_partial_send_poison():
    client, peer = socket.socketpair()
    client.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 1024)
    peer.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 1024)
    qmp = QmpLineTransport(client, [], started=time.monotonic())
    try:
        qmp.command('human-monitor-command',
                    {'command-line': 'x' * 60000}, timeout=.02)
    except QmpDeadline as exc:
        assert 'send' in str(exc)
    else:
        raise AssertionError('socketpair did not exercise bounded send')
    assert qmp.send_unknown is True
    try:
        qmp.command('cont', timeout=.2)
    except QmpProtocolError as exc:
        assert 'cannot append or resend' in str(exc)
    else:
        raise AssertionError('partial inbound JSON was extended by next command')
    client.close()
    peer.close()


if __name__ == '__main__':
    test_late_partial_and_event()
    test_event_flood_deadline()
    test_disconnect_and_oversize()
    test_partial_send_poison()
    print('QMP transport socketpair recv recovery/send poison/event/EOF/oversize PASS')
