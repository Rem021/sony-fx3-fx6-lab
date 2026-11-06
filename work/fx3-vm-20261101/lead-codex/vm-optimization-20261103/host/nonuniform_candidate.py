"""Host-only replacement for the per-pixel Python nonuniform RGBA scan.

The renderer emits packed RGBA. A trailing partial pixel is counted as a
difference, matching the old slice comparison against the first four bytes.
"""


def nonuniform_rgba(pixels: bytes) -> bool:
    complete = len(pixels) // 4
    return (len(pixels) > 4 and len(pixels) % 4 != 0) or (
        complete > 1 and pixels[:complete * 4] != pixels[:4] * complete
    )
