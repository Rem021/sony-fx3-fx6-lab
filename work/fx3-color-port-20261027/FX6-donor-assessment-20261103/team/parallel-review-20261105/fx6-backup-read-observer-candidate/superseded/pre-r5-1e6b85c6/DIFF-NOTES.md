# r4 corrections vs pre-r4 b3cd

- Prelaunch accepted (`prelaunch, running=false`) with one QMP boot cont; after-map stop/query must paused; -S retained.
- Actual Observer + actual QMP/RSP/Sysregs four-stop socketpair E2E replaces fake Obs single-stop test; continued=4, non-final stops require c.
- QMP/RSP share Deadline; connect/command/XML/p/Z1/z1/cleanup clamp; no independent 2s/1s.
- `self.possibly` initialized; partial arm tracked; stop-unconfirmed skips breakpoint/inherited and exits own child unclean.
- Cleanup QMP quit before wait/reap; qemu exit/lock receipt; RSP/QMP closed; launcher parent fd closed; receipt persisted.
- `run_stop_only.py` default-disabled separate mode; no guest restore, fields two_keys_observed/host_cleanup_complete/unknown_not_attempted/boot_menu_passed false.
- API16 old restore contract remains unestablished; target shutdown/restore markers retained, no inference of absence.
