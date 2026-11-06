"""Exact FX3 original-library profiles. These are not current-body attestations."""
from hashlib import sha256
from .files import require

PROFILE = 'fx3-p1-reference-v1'
REFERENCE_IMAGES = {
    'e5b71cc24bf5232c2e182a979b60c5f080dcbabe2775b32214dc0f394cf53c67': 'FX3 official 2.04 P1 payload',
    'ab2cd5372fed3c742b586e28484c6bf0aa6ebfba1f6d8e450a19191abc5b6591': 'FX3 official 2.05 P1 payload',
}
LIBRARIES = {
    '/usr/lib/libsdfileinputupdaterapi.so': {
        'bytes': 60584,
        'sha256': '257164d1cdf88757b8c0e2ba08ac47b06c46007410af308b7a8571b442b00cd2',
        'patches': (
            (0x9fd4, '220440b900008052', '20008052c0035fd6', 'SDUUDConditionChecker::isVersionOK'),
            (0xabf0, 'fd7bbba9fd030091', '00008052c0035fd6', 'SignatureVerification::VerifySignature'),
        ),
        'preserved': ((0xa004, 0xa02c, 'isModelOK and isRegionOK'),),
    },
    '/usr/lib/libupdatercorecommon.so': {
        'bytes': 72864,
        'sha256': 'b2b066b963a42d96556f811a773579eb16a0358de1b3a9206a1845c0df99bb74',
        'patches': (
            (0xd208, '13008012', '13008052', 'RVchk4PI::chkFirmInfo_before result'),
            (0xd27c, 'f3c39f5a', '13008052', 'RVchk4PI::chkFirmInfo_before comparison result'),
        ),
        'preserved': (),
    },
}


def patched_library(raw, spec):
    require(len(raw) == spec['bytes'] and sha256(raw).hexdigest() == spec['sha256'],
            'unsupported updater library: whole-file fingerprint differs')
    require(raw[:6] == b'\x7fELF\x02\x01' and raw[18:20] == b'\xb7\x00', 'expected AArch64 ELF')
    result = bytearray(raw)
    for at, before, after, name in spec['patches']:
        old, new = bytes.fromhex(before), bytes.fromhex(after)
        require(len(old) == len(new) and result[at:at+len(old)] == old, 'original instruction differs: '+name)
        result[at:at+len(old)] = new
    for begin, end, name in spec['preserved']:
        require(result[begin:end] == raw[begin:end], 'preserved predicate changed: '+name)
    return bytes(result)
