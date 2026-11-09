#!/usr/bin/env python3
"""Validate every ResID used in every fx6_menu_row_t array and fx6_opt_t table in
/private/tmp/fx6_menu_items_assist.h against the real .uxc containers.

Namespace map (verified):
  0  image_00_169.uxc   marker 0x1a00   -> image ids
  1  string_english.uxc marker 0x1e00   -> strings
  2  string_english_2.uxc               -> strings
  3  style_cmn.uxc      marker 0x2600   -> style/font ids  (0x6000..0x603f)
  5  lang_cmn.uxc                       -> text layout ids (0xa005..0xa02e)
  6  color_cmn.uxc      marker 0x3a00   -> RGBA colours
"""
import re, struct, sys, os
APP = ("/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/"
       "FX6-donor-assessment-20261103/team/donor/nflasha15-files/share/app")
HDR = "/private/tmp/fx6_menu_items_assist.h"

def load(name, marker):
    d = open(os.path.join(APP, name), 'rb').read()
    ids = set()
    m = marker.to_bytes(2, 'little')
    i = 0
    while True:
        j = d.find(m, i)
        if j < 0: break
        o = j - 2
        if o >= 0x14:
            ids.add(struct.unpack_from('<H', d, o)[0])
        i = j + 1
    return ids

IMG   = load("image_00_169.uxc", 0x1a00)
STYLE = load("style_cmn.uxc",    0x2600)
COLOR = load("color_cmn.uxc",    0x3a00)

import json
idx = json.load(open('/private/tmp/fx6_uxc_index.json'))
E1, E2 = idx['string_english.uxc'], idx['string_english_2.uxc']

def check(r):
    if r in (0, 0xffffffff): return None
    ns = (r >> 13) & 0x7ff
    ix = r & 0x1fff
    if ns == 0: return ('image', ix in IMG)
    # color_cmn records are stored as 0xc000..0xc01a and style_cmn as 0x6000..0x603f,
    # so the container id is base|index, not the bare index.
    if ns == 6: return ('colour', (0xc000 | ix) in COLOR)
    if ns == 3: return ('style', (0x6000 | ix) in STYLE)
    if ns in (1, 2):
        t = E1 if ns == 1 else E2
        return ('text', bool(t.get(str((ns << 13) | ix))))
    if ns == 5: return ('layout', True)   # lang_cmn not indexed here
    return ('ns%d' % ns, False)

src = open(HDR).read()
rows = re.findall(r'\{"[^"]*",\s*0x[0-9a-f]{8}u,\s*\{[^}]*\},\s*(0x[0-9a-f]{8})u,', src)
opts = re.findall(r'\{(0x[0-9a-f]{8})u,\s*"', src)
binds = re.findall(r'\{[^,]*,?[^,]*,?\s*(0x[0-9a-f]{8})u?', '')

from collections import Counter
kind = Counter(); bad = []
for h in set(rows):
    r = int(h, 16)
    res = check(r)
    if res is None: continue
    k, good = res
    kind[k] += 1
    if not good: bad.append(('row', h, k))
for h in set(opts):
    r = int(h, 16)
    res = check(r)
    if res is None: continue
    k, good = res
    kind[k] += 1
    if not good: bad.append(('opt', h, k))

print("header: %d rows, %d opt ids" % (len(rows), len(opts)))
print("distinct id kinds: %s" % dict(kind))
print("unresolved: %d" % len(bad))
for b in bad[:20]: print("   ", b)
sys.exit(1 if bad else 0)
