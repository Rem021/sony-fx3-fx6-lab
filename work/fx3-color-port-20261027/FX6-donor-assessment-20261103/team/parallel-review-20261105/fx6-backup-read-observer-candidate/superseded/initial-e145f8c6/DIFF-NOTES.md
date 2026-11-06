# Difference from `first-ap-readonly-observer`

This is a **new candidate**, not a copy of the old run authorization or old run directory.

| Item | Old observer | New candidate |
|---|---|---|
| Target | CAPID `audio_dispatch` + FX6 AP first CAP call | Current target AppFw `set_model_for_boot_screen` two Backup reads |
| Guest CPIO | `guest-three-entry` `bb618bd2…` | `guest-hybrid-fx6kernel-capid-grmreal46` `3a08f89d…` (not loosened) |
| AppFw | donor `appFw.so` `a1c58b69…` | target `appFw-future-skip.so` `b1fe2274…` |
| Breakpoint targets | CAPID VA `0x1e730`, AP return `0x20ef7a0` | key thunks `0x2169784`/`0x21697d4`; exact returns `0x11f67d4`/`0x11f67f4` |
| Identity | CAP/AP from early maps + live ELF | current complete early map epoch with all AppFw PT_LOADs + live AppFw ELF header/PHDR/four words |
| Guest writes | old runner API16 8B restore in cleanup | **none**: no API16 restore; only Z1/z1; no M/G/P |
| Authorization | consumed historical windows | none; default-disabled and no execution adapter |

The reusable design is the strict `T05thread` parser, Z1/z1-only RSP surface, bounded `g/p/m` reads, two-stage map/live identity, and fail-closed cleanup. No old authorization, old ASLR, old candidate, or old run is inherited.
