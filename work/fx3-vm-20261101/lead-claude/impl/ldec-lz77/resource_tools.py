"""Read-only UX table/record parsing. Formula follows libObj 1213fc..121500."""
from pathlib import Path
import struct

ROOT = Path(__file__).resolve().parent
MAC = next(p for p in ROOT.parents if p.name == "Mac")
RESOURCES = MAC / "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app"
PROOF = MAC / "work/fx3-vm-20261101/lead-claude/audits/ui-image-resource-load/ui-image-load-proof.json"


def table_entries(data, table=8):
    def u16(p): return struct.unpack_from("<H", data, p)[0]
    word = struct.unpack_from("<I", data, table + 4)[0]
    count, header, kind = word & 8191, data[table] & 124, data[table] & 3
    base = table + header + ((word >> 11) & 32764)
    missing, rows = [], []
    for index in range(count):
        if kind == 1:
            offset = struct.unpack_from("<I", data, table + header + 4 * index)[0]
        elif kind in (0, 3):
            cutoff = u16(table + 8) if kind == 3 else count
            slot = index if index <= cutoff else 2 * index - cutoff
            p = table + header + 2 * slot
            encoded = u16(p)
            if encoded == 65535:
                missing.append(index)
                continue
            if kind == 3 and encoded & 32768:
                encoded = ((encoded & 32767) << 16) | u16(p + 2)
            offset = encoded * 4
        else:
            raise ValueError("unsupported table kind")
        if offset == 0xffffffff:
            missing.append(index)
            continue
        record = base + offset
        if not 0 <= record < len(data):
            raise ValueError("record outside file")
        rows.append((index, record))
    return rows, missing


def uxd_records(data):
    if data[:4] != b"uxd\x07":
        raise ValueError("not uxd v7")
    rows, _ = table_entries(data)
    for index, r in rows:
        tag, word, w, h = struct.unpack_from("<IIHH", data, r)
        if (tag >> 26) & 31 != 6 or (word >> 28) & 7 != 4 or (word >> 16) & 63:
            raise ValueError("outside verified type6/encoding4/fmt0 corpus")
        footer = r + 4 + (12 + 8 * data[r + 12] if word & (1 << 27) else 8)
        length, relative = struct.unpack_from("<II", data, footer)
        source = r + 4 + relative
        if not (w and h and length and source >= footer + 8 and source + length <= len(data)):
            raise ValueError("invalid descriptor extent")
        yield {"index": index, "record_offset": r, "tag": tag,
               "id_low24": tag & 0xffffff, "word": word,
               "width": w, "height": h, "metadata": data[r + 12:footer].hex(),
               "source_offset": source, "source_bytes": length,
               "output_bytes": ((w + 15) & ~15) * h * 2}


def png_records(data):
    if data[:4] != b"uxb\x07":
        raise ValueError("not uxb v7")
    roots, _ = table_entries(data)
    for bank, table in roots:
        rows, _ = table_entries(data, table)
        for index, r in rows:
            tag, word, w, h = struct.unpack_from("<IIHH", data, r)
            if (tag >> 26) & 31 != 4 or (word >> 28) & 7 != 1:
                raise ValueError("not inline PNG")
            footer = r + 4 + (10 + 8 * data[r + 12] if word & (1 << 27) else 8)
            length = struct.unpack_from("<I", data, footer)[0]
            source = footer + 4
            if data[source:source + 8] != b"\x89PNG\r\n\x1a\n" or source + length > len(data):
                raise ValueError("invalid PNG span")
            yield {"bank": bank, "index": index, "id_low24": tag & 0xffffff,
                   "width": w, "height": h, "source_offset": source, "source_bytes": length}
