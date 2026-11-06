#!/usr/bin/env python3
"""Decode archived PNG bytes independently of UI preview and bound the delta."""
import hashlib
import json
from pathlib import Path
from PIL import Image

HERE = Path(__file__).resolve().parent
RUNS = HERE.parent.parent / 'runs'
CASES = {
    '48a838e5': ('trial-frame.png', 'internal-observe-01.png'),
    'c017e6ed': ('view-step-01-seq-240-2914275caea5.png',
                 'internal-stale-01-f37ae114-current.png'),
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    out = {}
    for suffix, names in CASES.items():
        run = RUNS / ('try2mssallinternal-' + suffix)
        paths = [run / n for n in names]
        images = [Image.open(p).convert('RGBA') for p in paths]
        assert all(im.size == (640, 480) and im.getchannel('A').getextrema() == (255, 255)
                   for im in images)
        pixels = [(x, y) for y in range(480) for x in range(640)
                  if images[0].getpixel((x, y)) != images[1].getpixel((x, y))]
        out[suffix] = {
            'images': [{'path': str(p), 'sha256': sha(p)} for p in paths],
            'different_rgba_pixels': len(pixels),
            'bbox_left_top_right_exclusive_bottom_exclusive':
                [min(x for x, y in pixels), min(y for x, y in pixels),
                 max(x for x, y in pixels) + 1, max(y for x, y in pixels) + 1],
            'outside_native_fill_rect_358_4_454_30':
                sum(not (358 <= x < 454 and 4 <= y < 30) for x, y in pixels),
            'same_pixel_example_HD_134_15':
                [list(im.getpixel((134, 15))) for im in images],
            'all_alpha_255': True,
        }
        assert out[suffix]['outside_native_fill_rect_358_4_454_30'] == 0
    (HERE / 'pixel-difference.json').write_text(json.dumps(out, indent=2) + '\n')
    print(json.dumps(out, indent=2))


if __name__ == '__main__':
    main()
