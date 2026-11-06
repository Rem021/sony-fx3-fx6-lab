#!/usr/bin/env python3
"""Adapter to the frozen r6 HostRunner with the FX3MS2 provider.

The frozen r6 HostRunner source is not modified.  This adapter:
- wraps the RSP factory with one aggregate 128 x 4-byte read budget;
- records the full appFw ELF header/PHDR/four-code-word identity at the first
  appFw stop, where that paused epoch is valid, before any key data read;
- does NOT repeat the identity scan at an earlier QMP stop.  The earlier stop
  and the first appFw hit are different pause epochs because the observer sends
  `c` between them; reusing the earlier identity there would not be valid.

The frame is snapshot_atomic=0.  The first-stop identity proves the bytes at
that paused state; it does NOT prove the multi-read map was atomic, nor current
PTE permissions.  See ADMISSION.md: runtime admission remains blocked.
"""
import hashlib
import json
import struct
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
CAND = HERE.parent
R6 = Path('/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/parallel-review-20261105/fx6-backup-read-observer-candidate')
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(R6 / 'observer'))
import host_runner
import fx3ms2 as FP

NEW_CPIO = CAND / 'work/fx6-map-collector-shortread-grmreal46.cpio'
NEW_SHA = '277bee6d68cfec6714eb7ded3d90f93d8cd5da7fd45e3c68fd473bfe55e3da0e'
NEW_BYTES = 453200828

SHARED_RSP_MAX_READS = 128
SHARED_RSP_READ_SIZE = 4


def _sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def identity_reads(elf_path=None):
    b = Path(elf_path or host_runner.observer_core.APP_ELF).read_bytes()
    phoff = struct.unpack_from('<Q', b, 32)[0]
    es, n = struct.unpack_from('<HH', b, 54)
    return 16 + (es * n) // 4 + 4


IDENTITY_READS = identity_reads()


class SharedBudgetRSP:
    """One aggregate 128 x 4-byte read budget for Observer identity + keys.

    The check happens before the wrapped RSP sends any command; an over-budget
    read is rejected locally and never reaches the GDB server.
    """
    def __init__(self, base, max_reads=SHARED_RSP_MAX_READS):
        self.base = base
        self.max_reads = max_reads
        self.reads = 0
        self.rejected = 0
        self.record_path = None

    def virtual_read(self, addr, size):
        if size != SHARED_RSP_READ_SIZE:
            raise ValueError('shared budget only permits 4-byte reads')
        if self.reads >= self.max_reads:
            self.rejected += 1
            raise RuntimeError('shared RSP read budget exhausted before command')
        self.reads += 1
        return self.base.virtual_read(addr, size)

    def __getattr__(self, name):
        return getattr(self.base, name)


_ORIGINAL_OBSERVER = host_runner.observer_core.Observer


class ObserverV2(_ORIGINAL_OBSERVER):
    """Frozen Observer plus a first-stop identity record; no cross-epoch reuse."""
    def __init__(self, mapping, rsp, tls_reader=None, clock=time.monotonic):
        super().__init__(mapping, rsp, tls_reader, clock=clock)
        self._first_identity_recorded = False

    def on_stop(self, stop):
        super().on_stop(stop)
        if self.identity is not None and not self._first_identity_recorded:
            shared = getattr(self.rsp, 'base', None)
            record_path = getattr(shared, 'record_path', None)
            if record_path is not None:
                record = {
                    'schema': 'fx6-map-first-stop-identity-v1',
                    'checked_at_first_appfw_stop': True,
                    'source': 'Observer.verify_live_identity at first appFw entry stop, before key data read',
                    'mapping_pid': self.m.get('pid'),
                    'mapping_seq': self.m.get('frame_seq'),
                    'mapping_bias': hex(self.m['ap']['bias']),
                    'mapping_snapshot_atomic': False,
                    'mapping_read_count': self.m.get('read_count'),
                    'mapping_eintr_count': self.m.get('eintr_count'),
                    'identity': self.identity,
                    'identity_reads_expected': IDENTITY_READS,
                    'shared_reads_after_first_stop': getattr(shared, 'reads', None),
                    'shared_budget_max_reads': getattr(shared, 'max_reads', None),
                    'prearm_identity_reused_across_epochs': False,
                    'note': ('full ELF header + PHDR + four code words compared with pinned APP_ELF at the first appFw pause; '
                             'the earlier QMP-stop epoch is not reused because the guest continues before this stop'),
                }
                Path(record_path).write_text(json.dumps(record, indent=2) + '\n')
            self._first_identity_recorded = True


def build_runner(root, deps_factory=None, shared_budget=SHARED_RSP_MAX_READS):
    base = host_runner.baseline_binding.verify_artifacts()
    if _sha(NEW_CPIO) != NEW_SHA or NEW_CPIO.stat().st_size != NEW_BYTES:
        raise RuntimeError('new CPIO preflight mismatch')
    host_runner.baseline_binding.TARGET = NEW_CPIO
    host_runner.baseline_binding.TARGET_SHA = NEW_SHA
    host_runner.baseline_binding.TARGET_BYTES = NEW_BYTES
    deps = deps_factory() if deps_factory is not None else host_runner.real_deps(root)
    provider = FP.FramedProviderV2(cpio_sha=NEW_SHA)
    box = {}

    def verify():
        if _sha(NEW_CPIO) != NEW_SHA or NEW_CPIO.stat().st_size != NEW_BYTES:
            raise RuntimeError('new CPIO preflight drift')
        return {**host_runner.baseline_binding.verify_artifacts(),
                'new_cpio_sha256': NEW_SHA, 'new_cpio_bytes': NEW_BYTES}

    def mapping(serial, deadline=None):
        m = FP.wait_mapping(provider, serial, deadline)
        box['mapping'] = m
        return m

    base_rsp_factory = deps['rsp_factory']

    def verifying_rsp_factory(run, deadline=None):
        base_rsp = base_rsp_factory(run, deadline)
        shared = SharedBudgetRSP(base_rsp, shared_budget)
        shared.record_path = Path(run) / 'first-stop-identity.json'
        box['shared_rsp'] = shared
        return shared

    deps['verify_artifacts'] = verify
    deps['mapping_provider'] = mapping
    deps['rsp_factory'] = verifying_rsp_factory
    deps['stop_only'] = True
    deps['prearm_box'] = box
    host_runner.observer_core.Observer = ObserverV2
    runner = host_runner.HostRunner(deps)
    runner.prearm_box = box
    return runner
