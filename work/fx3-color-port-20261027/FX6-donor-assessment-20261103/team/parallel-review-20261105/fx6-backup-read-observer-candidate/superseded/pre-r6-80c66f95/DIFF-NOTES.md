# r5 corrections

- stop-only CLI now invokes HostRunner(real_deps, stop_only=True), serializes receipt, uses two_keys_observed && host_cleanup_complete for exit; default gates retained; fake main E2E.
- RSP absolute phase deadlines; no 1s/2s reset; partial T05 and expired deadline socketpair tests; connect/constructor close and no TypeError re-dispatch.
- preflight target/app/baseline hashes before 180s; postflight actual/injected hashes and input_unchanged in receipt; runtime_evidence source explicit.
- API16 old restore contract remains unestablished; target shutdown/restore markers retained; no synthetic callback.
