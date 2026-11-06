"""Incrementally read a QEMU serial file while exposing read_text-equivalent snapshots.

No log file is modified. The retained text is intentional: candidate105 still
does historical searches, so dropping old bytes would change its decisions.
"""
import codecs
import os
from pathlib import Path


class SerialSnapshot:
    def __init__(self, path):
        self.path = Path(path)
        self.identity = None
        self.offset = 0
        self.mtime_ns = None
        self.anchor = b''
        self.decoder = codecs.getincrementaldecoder('utf-8')('replace')
        self.text = ''
        self.pending_cr = False
        self._snapshot = ''
        self.resets = 0
        self.bytes_read = 0

    def _reset(self):
        self.identity = None
        self.offset = 0
        self.anchor = b''
        self.decoder = codecs.getincrementaldecoder('utf-8')('replace')
        self.text = ''
        self.pending_cr = False
        self._snapshot = ''
        self.resets += 1

    def _append_text(self, part):
        if self.pending_cr:
            if part.startswith('\n'):
                part = part[1:]
            self.text += '\n'
            self.pending_cr = False
        if part.endswith('\r'):
            part = part[:-1]
            self.pending_cr = True
        self.text += part.replace('\r\n', '\n').replace('\r', '\n')

    def poll(self):
        try:
            stream = self.path.open('rb')
        except FileNotFoundError:
            if self.identity is not None:
                self._reset()
            return ''
        with stream:
            meta = os.fstat(stream.fileno())
            identity = (meta.st_dev, meta.st_ino)
            restart = self.identity is not None and (
                identity != self.identity or meta.st_size < self.offset or
                (meta.st_size == self.offset and meta.st_mtime_ns != self.mtime_ns)
            )
            if not restart and self.anchor:
                stream.seek(self.offset - len(self.anchor))
                restart = stream.read(len(self.anchor)) != self.anchor
            if restart:
                self._reset()
            self.identity = identity
            stream.seek(self.offset)
            chunk = stream.read()
            self.offset += len(chunk)
            self.mtime_ns = meta.st_mtime_ns
            if chunk:
                self.bytes_read += len(chunk)
                self.anchor = (self.anchor + chunk)[-64:]
                part = self.decoder.decode(chunk, final=False)
                if part:
                    self._append_text(part)
                clone = codecs.getincrementaldecoder('utf-8')('replace')
                clone.setstate(self.decoder.getstate())
                tail = clone.decode(b'', final=True)
                self._snapshot = self.text + ('\n' if self.pending_cr else '') + tail
            return self._snapshot
