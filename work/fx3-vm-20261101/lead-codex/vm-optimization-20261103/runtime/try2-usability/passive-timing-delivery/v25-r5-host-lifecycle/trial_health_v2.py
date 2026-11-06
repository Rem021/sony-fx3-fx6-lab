"""Separate lifecycle, guest protocol, and observed render health."""

def evaluate(*, lifecycle, observer_error, serial_failure, markers_complete,
             standby_observed, render_valid, black_after_ready, early_stop):
    protocol = bool(not observer_error and not serial_failure and markers_complete)
    render = bool(standby_observed and render_valid and not black_after_ready)
    healthy = bool(lifecycle and protocol and render and not early_stop)
    return protocol, render, healthy
