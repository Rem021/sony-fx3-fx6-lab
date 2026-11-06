"""Pure, bounded classification of one FX3 input and its observed pixels.

Native receive proves queue delivery only. A changed immutable PNG proves a
later observed image, not which downstream handler produced it.
"""
from dataclasses import dataclass

ACK_DEADLINE_SECONDS = 12.0
VISUAL_WAIT_SECONDS = 6.0
MENU_VISUAL_WAIT_SECONDS = 30.0

@dataclass(frozen=True)
class Decision:
    state: str
    input_received: bool
    visual_change_observed: bool
    terminal: bool
    fault: str | None = None

def classify(command, step, up_seen, both_native_events, frame, now, native_shutdown=False):
    """Classify without sending, retrying, or modifying the guest."""
    if native_shutdown:
        return Decision('native_shutdown', False, False, True, 'native shutdown observed')
    if command is None:
        return Decision('idle', False, False, False)
    sent = command['sent_monotonic']
    if step not in up_seen or not both_native_events:
        if now - sent > ACK_DEADLINE_SECONDS:
            return Decision('unknown_ack', False, False, True, 'native down/up evidence missing')
        return Decision('input_pending', False, False, False)
    ack_time = up_seen[step][0]
    changed = (frame is not None
               and frame['sequence'] > command['before_command_sequence']
               and frame['PNG_sha256'] != command['before_command_png_sha256'])
    if changed and now - ack_time >= 1.0:
        return Decision('visual_changed', True, True, True)
    wait = MENU_VISUAL_WAIT_SECONDS if command['key'] == 0x1ab else VISUAL_WAIT_SECONDS
    if now - ack_time >= wait:
        return Decision('no_change_observed', True, False, True)
    return Decision('visual_pending', True, False, False)

def late_change(previous, current):
    """A distinct later frame after no-change release; attribution stays unknown."""
    return bool(previous and current and current['sequence'] > previous['sequence']
                and current['PNG_sha256'] != previous['PNG_sha256'])
