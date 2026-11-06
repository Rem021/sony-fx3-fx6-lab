# Corrected candidate vs old observer / e145

- New task `task_a11971763fc5`; old candidate e145f8c6 retained only as snapshot.
- Guest is target `3a08f89d…` (not old `bb618bd2…`); appFw `b1fe2274…` (not old `a1c58b69…`).
- New breakpoints: AppFw thunk `0x2169784`/`0x21697d4`, exact returns `0x11f67d4`/`0x11f67f4`, slots b4/c4.
- RSP is now actual `observer/rsp_readonly.py`, not Fake-only: strict checksum, stream, ACK/console/async T05, unique hex thread; old observer code unchanged.
- `gdb_cpu_thread` replaces guest TID semantics; `guest_tid=unknown`; same CPU is not guest-thread proof; cross-CPU is unknown.
- Map requires latest complete block, >=page rows, inode/offset/perms; no fallback.
- Budget 128×4B identity+data; current ELF 104; short read reject; total/observe time enforced.
- `possibly_installed` before Z1; lost ACK remains possibly installed; residual never resumes.
- Private output: index20 new serial path, index31 target CPIO; no historical serial output.
- Inherited API16/unbind cleanup preserved as required callback; adapter itself makes no new guest write. Missing callback blocks clean status.
- No new VM/guest/QMP interaction, no platform/Backup/CPIO/helper change.
