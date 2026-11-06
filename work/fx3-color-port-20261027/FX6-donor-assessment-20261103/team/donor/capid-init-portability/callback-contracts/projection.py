"""Offline byte-field projections only. Never returns an mpr Init record or pointers."""
import struct
class UnknownContract(ValueError): pass
def project(kind, record):
    if type(record) is not bytes: raise UnknownContract('immutable bytes required')
    if kind != 'load_still_observed_fields': raise UnknownContract('callback/Init contract not closed')
    if len(record) != 20: raise UnknownContract('only the observed 20-byte dispatch copy domain is supported')
    # FX6 212956c reads +c; 2129574 reads +8; cmp/cset implements zero test.
    # These values are projections, not a claim that opaque identifiers or enums are portable.
    return {'opaque_u32_at_c':struct.unpack_from('<I',record,12)[0],
            'zero_test_at_8':int(struct.unpack_from('<I',record,8)[0]==0)}
