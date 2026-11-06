"""Offline immutable byte records only. No ELF execution, callbacks, or firmware output.
The canonical 60B record-only timer subset is deliberately narrower than RecPbTime.
Caller must separately establish live pointer/length and producer provenance; bytes
alone cannot establish those facts. Unknown fields raise, never report guest success.
"""
import struct

class UnsupportedRecord(ValueError):
    pass

def convert_record_timer(raw: bytes) -> bytes:
    if type(raw) is not bytes or len(raw) != 60:
        raise UnsupportedRecord('requires an immutable, exactly 60-byte snapshot')
    if struct.unpack_from('<I', raw)[0] != 0x1022:
        raise UnsupportedRecord('not the proven FX3 RecPbTime event')
    if raw[4] != 1:
        raise UnsupportedRecord('requires a changed movie-record counter')
    if raw[5:8] != bytes(3) or raw[20:] != bytes(40):
        raise UnsupportedRecord('playback/audio/noncanonical fields are unproved')
    # FX6 native event header. The FX6 AP leaf itself never reads p+0.
    return struct.pack('<I', 0x1029) + raw[4:]

def project_fx6_record_message(converted: bytes) -> bytes:
    """Diagnostic projection of 0x212b73c..0x212b764; no allocator or queue stub."""
    if type(converted) is not bytes or len(converted) != 60:
        raise UnsupportedRecord('invalid converted snapshot')
    back = struct.pack('<I', 0x1022) + converted[4:]
    if converted[:4] != struct.pack('<I', 0x1029) or convert_record_timer(back) != converted:
        raise UnsupportedRecord('outside record-only native representation')
    return struct.pack('<I', 0xec) + converted[8:20]
