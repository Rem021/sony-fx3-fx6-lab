"""Fixed-range acquisition engine with an implemented regular-file provider.

No USB or camera worker is implemented here. Provider claims and hashes are
integrity checks, not device attestation. The fixed P1 length is a research
profile, not a measured claim about the attached camera's current partition.
"""
from dataclasses import asdict, dataclass
from hashlib import sha256
from pathlib import Path
import json
import math
import os
import re
import secrets
import stat
import time
import zlib
from .fat import MAX_P1
from .files import check_volume, encode, local_path, read_file, require

BLOCK = 65536
CHUNKS = MAX_P1 // BLOCK
WINDOW = 128
SCHEMA = 'fx3-local-p1-capture-v1'
FALSE_FLAGS = {'camera_identity_verified': False, 'hardware_validated': False,
               'flashable': False, 'independent_recovery_proven': False}
# Preserve an interrupted/in-flight provider in this process. Never close,
# reset, or retry it from an exception handler. No live provider exists yet.
UNKNOWN_SOURCES = {}


def digest(data):
    return sha256(data).hexdigest()


def hex_value(value, length):
    return (type(value) is str and re.fullmatch('[0-9a-f]{'+str(length)+'}', value) is not None
            and value != '0'*length)


def shape(window):
    require(type(window) is int and 0 <= window < 3, 'window outside fixed P1 profile')
    return window*WINDOW, min(WINDOW, CHUNKS-window*WINDOW)


@dataclass(frozen=True)
class Request:
    capture_id: str
    nonce: str
    index: int
    offset: int
    count: int = BLOCK

    def __post_init__(self):
        require(hex_value(self.capture_id, 32) and hex_value(self.nonce, 32), 'invalid request identity')
        require(type(self.index) is int and 0 <= self.index < CHUNKS, 'chunk outside fixed P1 profile')
        require(type(self.offset) is int and self.offset == self.index*BLOCK
                and type(self.count) is int and self.count == BLOCK, 'read range is not fixed')


@dataclass(frozen=True)
class Reply:
    request: Request
    status: int
    actual: int
    data: bytes


class CaptureFailure(ValueError):
    def __init__(self, state, cause):
        super().__init__(state+': '+type(cause).__name__+': '+str(cause)[:256])
        self.state = state


class PrivateDirectory:
    """Exclusive local evidence writer; no overwrite, unlink, or rename API."""
    def __init__(self, path):
        check_volume()
        self.path = local_path(path)
        parent = os.open(self.path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            os.mkdir(self.path.name, 0o700, dir_fd=parent)
            self.fd = os.open(self.path.name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
            os.fsync(parent)
        finally:
            os.close(parent)

    def create(self, name):
        require(type(name) is str and re.fullmatch('[a-z0-9_.-]+', name) is not None
                and name not in ('.', '..'), 'invalid evidence name')
        return os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=self.fd)

    def put(self, name, data):
        with os.fdopen(self.create(name), 'wb') as f:
            require(f.write(data) == len(data), 'short evidence write')
            f.flush(); os.fsync(f.fileno())
        os.fsync(self.fd)

    def close(self):
        os.close(self.fd)


class Journal:
    def __init__(self, directory):
        self.stream = os.fdopen(directory.create('journal.jsonl'), 'wb')
        self.chain = '0'*64
        self.whole = sha256()
        self.sequence = 0

    def add(self, event, **fields):
        row = {'sequence': self.sequence, 'previous_sha256': self.chain, 'event': event, **fields}
        raw = (json.dumps(row, sort_keys=True, separators=(',', ':'))+'\n').encode()
        require(self.stream.write(raw) == len(raw), 'short journal write')
        self.stream.flush(); os.fsync(self.stream.fileno())
        self.chain = digest(raw); self.whole.update(raw); self.sequence += 1

    def close(self):
        self.stream.close()


STAT_FIELDS = ('st_dev', 'st_ino', 'st_size', 'st_mtime_ns', 'st_ctime_ns', 'st_mode', 'st_nlink')


class RegularFileSource:
    """Pins one O_RDONLY descriptor. Devices, links, and other sizes rejected."""
    def __init__(self, path, expected_sha256):
        self.fd = os.open(local_path(path), os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        try:
            info = os.fstat(self.fd)
            require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1, 'single-link regular file required')
            require(info.st_size == MAX_P1, 'local input must have the exact full P1 profile length; no padding')
            self.baseline = tuple(getattr(info, name) for name in STAT_FIELDS)
            self.expected = expected_sha256
            self.finished = False
            require(self._hash() == self.expected, 'local source SHA differs from external expected SHA')
        except BaseException:
            os.close(self.fd)
            raise

    def _hash(self):
        result = sha256()
        for offset in range(0, MAX_P1, 1024*1024):
            count = min(1024*1024, MAX_P1-offset)
            data = os.pread(self.fd, count, offset)
            require(len(data) == count, 'short source fingerprint read')
            result.update(data)
        self.identify()
        return result.hexdigest()

    def identify(self):
        now = os.fstat(self.fd)
        require(tuple(getattr(now, name) for name in STAT_FIELDS) == self.baseline, 'pinned local source changed')
        return {'kind': 'local-regular-file', 'bytes': MAX_P1, 'expected_sha256': self.expected,
                'descriptor_identity_sha256': digest(encode(list(self.baseline)))}

    def read_at(self, request, deadline):
        # Deadline is advisory during a blocking OS call. The owner checks it
        # again after return; it never spawns a second call on a timeout.
        require(not self.finished, 'source already finalized')
        return Reply(request, 0, len(data := os.pread(self.fd, request.count, request.offset)), data)

    def finish(self):
        require(self._hash() == self.expected, 'source contents changed after capture')
        self.finished = True

    def close(self):
        os.close(self.fd)


def capture_local(source, destination, expected_sha256, body_tag):
    return _capture(lambda: RegularFileSource(source, expected_sha256), destination,
                    expected_sha256, body_tag)


def _capture(factory, destination, expected_sha256, body_tag, *, clock=time.monotonic,
             total_seconds=600.0, call_seconds=5.0):
    """Internal provider contract; no plugin discovery or device activation.

    Factory injection exists for fault tests and future reviewed integration.
    Only the local-file identity kind is admitted in this release.
    """
    require(hex_value(expected_sha256, 64) and hex_value(body_tag, 64), 'expected SHA and opaque body tag required')
    require(type(total_seconds) is float and math.isfinite(total_seconds) and 0 < total_seconds <= 600
            and type(call_seconds) is float and math.isfinite(call_seconds) and 0 < call_seconds <= 5,
            'invalid fixed read budget')
    directory = PrivateDirectory(destination)
    journal = None; source = None; in_flight = False; close_started = False
    capture_id = secrets.token_hex(16)
    plan = {'schema': SCHEMA, 'capture_id': capture_id, 'body_tag': body_tag,
            'source_kind': 'local-regular-file', 'image_bytes': MAX_P1, 'block_bytes': BLOCK,
            'chunks': CHUNKS, 'window_counts': [shape(w)[1] for w in range(3)],
            'expected_sha256': expected_sha256, 'total_seconds': total_seconds, 'call_seconds': call_seconds,
            'origin_verified': False, 'automatic_retry': False, **FALSE_FLAGS}
    try:
        directory.put('plan.json', encode(plan)); journal = Journal(directory)
        start = last_clock = clock()
        require(math.isfinite(start), 'invalid monotonic clock')

        def now():
            nonlocal last_clock
            value = clock()
            require(math.isfinite(value) and value >= last_clock, 'monotonic clock moved backwards')
            last_clock = value
            require(value < start+total_seconds, 'total capture deadline reached')
            return value

        journal.add('opening-local-source'); source = factory()
        identity = source.identify()
        require(type(identity) is dict and identity.get('kind') == 'local-regular-file'
                and type(identity.get('bytes')) is int and identity['bytes'] == MAX_P1
                and identity.get('expected_sha256') == expected_sha256, 'unsupported or mismatched source identity')
        directory.put('source-identity.json', encode(identity)); journal.add('source-pinned')
        previous = None
        for window in range(3):
            first, count = shape(window); rows = []; window_hash = sha256()
            for index in range(first, first+count):
                now(); require(source.identify() == identity, 'source identity drift before read')
                request = Request(capture_id, secrets.token_hex(16), index, index*BLOCK)
                deadline = min(now()+call_seconds, start+total_seconds)
                journal.add('read-in-flight', request=asdict(request))
                in_flight = True
                reply = source.read_at(request, deadline)
                in_flight = False
                require(now() < deadline, 'read returned after its deadline')
                require(type(reply) is Reply and reply.request == request and type(reply.status) is int
                        and reply.status == 0 and type(reply.actual) is int and reply.actual == BLOCK
                        and type(reply.data) is bytes and len(reply.data) == BLOCK,
                        'short, oversized, failed, or mismatched read reply')
                require(source.identify() == identity, 'source identity drift after read')
                directory.put(f'chunk-{index:03d}.bin', reply.data)
                row = {'request': asdict(request), 'sha256': digest(reply.data), 'crc32': zlib.crc32(reply.data)}
                rows.append(row); window_hash.update(reply.data)
                journal.add('read-saved', index=index, sha256=row['sha256'])
            manifest = {'capture_id': capture_id, 'window': window, 'start': first, 'count': count,
                        'previous_manifest_sha256': previous, 'window_sha256': window_hash.hexdigest(), 'chunks': rows}
            raw = encode(manifest); directory.put(f'window-{window}.json', raw); previous = digest(raw)
            journal.add('window-saved', window=window, manifest_sha256=previous)
        require(source.identify() == identity, 'source identity drift at completion')
        journal.add('source-final-fingerprint-start')
        now(); source.finish(); now()
        journal.add('source-final-fingerprint-verified')
        close_started = True
        source.close()
        source = None
        journal.add('local-source-closed')
        directory.put('source-closed.json', encode({'capture_id': capture_id, 'source_kind': 'local-regular-file',
                                                  'close_returned_normally': True, **FALSE_FLAGS}))
        # Re-read durable evidence, not the buffers just returned by the provider.
        image, final_hash = _assemble(directory.path, plan)
        require(final_hash == previous, 'final window binding differs')
        require(digest(image) == expected_sha256, 'assembled image differs from external expected SHA')
        directory.put('source.p1', image)
        require(read_file(directory.path/'source.p1', MAX_P1) == image, 'published image readback differs')
        journal.add('local-image-readback-verified', sha256=expected_sha256)
        journal.close()
        journal_sha = journal.whole.hexdigest(); journal = None
        receipt = {'schema': SCHEMA, 'status': 'COMPLETE_LOCAL_FILE_ONLY', 'capture_id': capture_id,
                   'plan_sha256': digest(encode(plan)), 'final_window_sha256': final_hash,
                   'image_sha256': expected_sha256, 'image_bytes': MAX_P1, 'journal_sha256': journal_sha,
                   'source_identity_sha256': digest(encode(identity)), 'automatic_retry': False, **FALSE_FLAGS}
        directory.put('complete.json', encode(receipt))
        return receipt
    except BaseException as cause:
        close_error = None
        state = 'UNKNOWN_IN_FLIGHT' if in_flight else ('UNKNOWN_CLOSE' if close_started and source is not None else 'INCOMPLETE')
        if source is not None and not in_flight and not close_started:
            try:
                close_started = True; source.close(); source = None
            except BaseException as error:
                close_error = type(error).__name__; state = 'UNKNOWN_CLOSE'
        if source is not None:
            UNKNOWN_SOURCES[capture_id] = source
        failure = {'schema': SCHEMA, 'capture_id': capture_id, 'state': state,
                   'cause_type': type(cause).__name__, 'reason': str(cause)[:256], 'close_error_type': close_error,
                   'automatic_retry': False, 'pending_provider_retained': source is not None, **FALSE_FLAGS}
        try:
            if journal is not None:
                journal.add('capture-stopped', **failure); journal.close(); journal = None
            directory.put('failure.json', encode(failure))
        except BaseException:
            pass  # Preserve all existing files even if the evidence disk is full.
        raise CaptureFailure(state, cause) from cause
    finally:
        if journal is not None:
            journal.close()
        directory.close()


def _json(path, limit=256*1024):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result, 'duplicate JSON key')
            result[key] = value
        return result
    return json.loads(read_file(path, limit), object_pairs_hook=unique,
                      parse_constant=lambda _: (_ for _ in ()).throw(ValueError('non-finite JSON')))


def _assemble(directory, plan):
    image = bytearray(); previous = None; nonces = set()
    for window in range(3):
        raw = read_file(directory/f'window-{window}.json', 256*1024)
        manifest = _json(directory/f'window-{window}.json')
        first, count = shape(window)
        require(manifest.get('capture_id') == plan['capture_id'] and type(manifest.get('window')) is int
                and manifest['window'] == window and type(manifest.get('start')) is int and manifest['start'] == first
                and type(manifest.get('count')) is int and manifest['count'] == count
                and manifest.get('previous_manifest_sha256') == previous,
                'window chain, capture, or range differs')
        rows = manifest.get('chunks')
        require(type(rows) is list and len(rows) == count, 'window chunk count differs')
        window_hash = sha256()
        for index, row in zip(range(first, first+count), rows):
            require(type(row) is dict and type(row.get('request')) is dict, 'invalid chunk record')
            request = Request(**row['request'])
            require(request.capture_id == plan['capture_id'] and request.index == index and request.nonce not in nonces,
                    'chunk request replay, gap, or capture mismatch')
            nonces.add(request.nonce)
            data = read_file(directory/f'chunk-{index:03d}.bin', BLOCK)
            require(len(data) == BLOCK and digest(data) == row.get('sha256') and type(row.get('crc32')) is int
                    and zlib.crc32(data) == row['crc32'], 'durable chunk size or hash differs')
            image.extend(data); window_hash.update(data)
        require(window_hash.hexdigest() == manifest.get('window_sha256'), 'window bytes hash differs')
        previous = digest(raw)
    require(len(image) == MAX_P1, 'assembled size differs')
    return bytes(image), previous


def verify_capture(destination, expected_sha256):
    """Re-check local evidence with an external digest; never attest a camera."""
    require(hex_value(expected_sha256, 64), 'external expected SHA required')
    p = local_path(destination)
    require(not (p/'failure.json').exists(), 'failed/unknown capture cannot be admitted')
    plan = _json(p/'plan.json'); complete = _json(p/'complete.json'); closed = _json(p/'source-closed.json')
    require(plan.get('schema') == SCHEMA and hex_value(plan.get('capture_id'), 32)
            and hex_value(plan.get('body_tag'), 64) and plan.get('source_kind') == 'local-regular-file'
            and plan.get('origin_verified') is False and plan.get('automatic_retry') is False
            and plan.get('image_bytes') == MAX_P1 and plan.get('block_bytes') == BLOCK
            and plan.get('chunks') == CHUNKS and plan.get('window_counts') == [128,128,127]
            and plan.get('expected_sha256') == expected_sha256, 'plan binding differs')
    for item in (plan, complete, closed):
        require(all(item.get(k) is False for k in FALSE_FLAGS), 'unearned camera or recovery verification flag')
    require(complete.get('schema') == SCHEMA and complete.get('status') == 'COMPLETE_LOCAL_FILE_ONLY'
            and complete.get('capture_id') == closed.get('capture_id') == plan['capture_id']
            and complete.get('plan_sha256') == digest(read_file(p/'plan.json', 256*1024))
            and complete.get('image_sha256') == expected_sha256 and complete.get('image_bytes') == MAX_P1
            and complete.get('automatic_retry') is False and closed.get('source_kind') == 'local-regular-file'
            and closed.get('close_returned_normally') is True, 'completion/close binding differs')
    identity = _json(p/'source-identity.json')
    require(identity.get('kind') == 'local-regular-file' and identity.get('bytes') == MAX_P1
            and identity.get('expected_sha256') == expected_sha256
            and digest(read_file(p/'source-identity.json', 256*1024)) == complete.get('source_identity_sha256'),
            'local identity binding differs')
    require(digest(read_file(p/'journal.jsonl', 2*1024*1024)) == complete.get('journal_sha256'), 'journal differs')
    image, last = _assemble(p, plan)
    require(last == complete.get('final_window_sha256') and digest(image) == expected_sha256,
            'assembled evidence differs from expected SHA')
    require(read_file(p/'source.p1', MAX_P1) == image, 'image differs from reassembled chunks')
    return {'status': 'VERIFIED_LOCAL_CAPTURE_ONLY', 'sha256': expected_sha256, 'bytes': MAX_P1,
            'chunks': CHUNKS, 'windows': 3, 'origin_verified': False, **FALSE_FLAGS}
