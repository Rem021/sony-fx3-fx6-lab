"""Exact-preserving fast negative guard for two costly case-insensitive scans.

The full original regex always runs when a prefix may be present. Special
Unicode case-insensitive ASCII matches fall back to the original regex.
"""
import re

ASSERT = re.compile(r'assert at|Assertion|exception monitor|FX3_SIGNAL_OBSERVE[^\n]*signal=6(?: |$)', re.I)
RM = re.compile(r'FX3_RM_[A-Z_]*REJECT|FX3_RM_UNKNOWN|unknown\s+key|invalid\s+from_type', re.I)
ASSERT_FOLDED = re.compile(r'assert at|assertion|exception monitor|fx3_signal_observe[^\n]*signal=6(?: |$)')
RM_FOLDED = re.compile(r'fx3_rm_[a-z_]*reject|fx3_rm_unknown|unknown\s+key|invalid\s+from_type')
SPECIAL = 'İıſK'


def _possible(folded, prefixes, pattern):
    for prefix in prefixes:
        pos = folded.find(prefix)
        while pos >= 0:
            if pattern.match(folded, pos):
                return True
            pos = folded.find(prefix, pos + 1)
    return False


def guarded_rejects(text):
    folded = text.casefold()
    special = any(char in text for char in SPECIAL)
    maybe_assert = special or _possible(folded, ('assert', 'exception', 'fx3_signal_observe'), ASSERT_FOLDED)
    assert_reject = bool(ASSERT.search(text)) if maybe_assert else False
    maybe_rm = special or _possible(folded, ('fx3_rm_', 'unknown', 'invalid'), RM_FOLDED)
    rm_reject = bool(RM.search(text)) if maybe_rm else False
    return assert_reject, rm_reject
