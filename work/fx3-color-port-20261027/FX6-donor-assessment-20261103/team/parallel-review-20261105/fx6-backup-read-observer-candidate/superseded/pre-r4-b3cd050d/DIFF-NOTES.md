# r2 corrections vs prior candidate/old observer

- New task `task_b82d76ef57c1`; current snapshot `superseded/pre-r2-3f182d91/`; e145 snapshot retained.
- `HostRunner` real full lifecycle code added; cleanup no longer trusts `qmp.call('stop')`, callback false/exception/timeout, qemu wait, quit, lock release; only fully confirmed path is clean; child live/unknown retains locks.
- `prepare` derives 34 argv from hash-verified baseline; only index20 new private serial and index31 target CPIO; env exactly five; target/APP hash+size; no mutable plan initrd.
- Latest-map-only, whole file-backed coverage, header/PHDR/code address map/permission checks; one-page/offset/perms/truncation tests.
- 180s monotonic deadline from launch/prepare; observation 150s; cleanup budget; fake no-map/no-hit/timeout.
- `gdb_cpu_thread` retained; `guest_tid=unknown`; same CPU is not guest-thread proof; cross-CPU unknown.
- API16 inherited restore audited against 3a08 helper/observer/unbind: F100FILE/API16 protocol not established; no synthetic callback or CPIO/helper modification; real clean blocked.
- Old observer and platform/CPIO/Backup unchanged.

- r3: QMP capabilities/timeouts/events; -S boot cont before maps; RSP c after every stop; cleanup quit before wait; qemu exit/lock_released; stop-unconfirmed skips breakpoints; no daemon callback.
- Real socketpair QMP/RSP tests and actual HostRunner stateful E2E added.
