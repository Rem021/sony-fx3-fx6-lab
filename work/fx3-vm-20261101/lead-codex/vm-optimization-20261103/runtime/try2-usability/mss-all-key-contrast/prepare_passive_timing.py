#!/usr/bin/env python3
"""Prepare source-only passive guest clock candidate from fixed, existing hooks.

No CPIO, DTB, original source or running guest is modified by this script.
"""
from pathlib import Path
import difflib
import hashlib
import json

HERE = Path(__file__).resolve().parent
TOP = HERE.parents[4]
TRY2 = HERE.parent
HELPERS = TOP / 'menu-repair-01/runtime/helpers'
SOURCES = {
    'rm': (TRY2 / 'src/fx3-rm-empty-provider-v8-long-use.c',
           'ebe58c4f01fd53d265fac597a6bcde7f3e12df922b69035e11dc9a3d40ff9160'),
    'ap': (HELPERS / 'fx3-preset-context-v6-save102.c',
           '32bb3b5ae43ddab667c655941784daf028f26ce4c9ce6cca7e91268c4bb72663'),
    'osd': (HELPERS / 'fx3-osd-headless-v7-observe102.c',
            '24234cb7a54c37e93f2b5d63e1bd7faba7b7cf225f60e62e1233f3032469dad2'),
}
OUT = HERE / 'passive-timing-next/src'
OUT.mkdir(parents=True, exist_ok=True)

def sha(data):
    return hashlib.sha256(data).hexdigest()

def one(text, old, new):
    assert text.count(old) == 1, (old[:90], text.count(old))
    return text.replace(old, new, 1)

def add_fields_to_existing_log(text, marker, fields, args):
    lines = [line for line in text.splitlines(True) if marker in line]
    assert len(lines) == 1, (marker, len(lines))
    old = lines[0]
    new = old.replace(marker, marker + fields, 1)
    anchor = new.index(marker)
    quote_end = new.index('"', anchor)
    comma = new.index(',', quote_end)
    new = new[:comma+1] + args + new[comma+1:]
    return one(text, old, new)

rows = []
for kind, (source, expected) in SOURCES.items():
    original_bytes = source.read_bytes()
    assert sha(original_bytes) == expected, source
    original = original_bytes.decode()
    text = original
    if kind == 'rm':
        text = one(text,
                   'int rc=fn(dst,p,tmo),after=*__errno_location();',
                   'U wait_enter_ns=dst==0x807a0020U?now():0;W wait_enter_step=__atomic_load_n(&key_step,__ATOMIC_ACQUIRE);*__errno_location()=saved;int rc=fn(dst,p,tmo),after=*__errno_location();U wait_return_ns=dst==0x807a0020U?now():0;W wait_return_step=__atomic_load_n(&key_step,__ATOMIC_ACQUIRE);*__errno_location()=after;')
        text = one(text,
                   'FX3_KEY_INPUT_RECV step=%u key=%#x status=%u from_type=%u source=%#x native_result=0\\n",key_step,',
                   'FX3_KEY_INPUT_RECV step=%u key=%#x status=%u from_type=%u source=%#x native_result=0 clock_id=1 wait_enter_ns=%lu wait_return_ns=%lu wait_enter_step=%u wait_return_step=%u tid=%ld downstream_processing_unproven=1\\n",key_step,')
        text = one(text, 'ng(*p));}*__errno_location()=after;return rc;}',
                   'ng(*p),wait_enter_ns,wait_return_ns,wait_enter_step,wait_return_step,syscall(178));}*__errno_location()=after;return rc;}')
    elif kind == 'ap':
        text = one(text,
                   '__attribute__((visibility("hidden"))) void fx3_display_event(struct ctx *c,U *r){',
                   'static U timing_ns(void){int saved=*__errno_location();struct ts t={0};int rc=clock_gettime(1,&t);*__errno_location()=saved;return rc?0:(U)t.s*1000000000UL+t.n;}\n__attribute__((visibility("hidden"))) void fx3_display_event(struct ctx *c,U *r){')
        text = add_fields_to_existing_log(text, 'FX3_AP89_SCREEN_OPEN_ENTER ',
                                          'clock_id=1 ns=%lu tid=%ld ', 'timing_ns(),syscall(178),')
        text = add_fields_to_existing_log(text, 'FX3_AP89_SCREEN_CREATE ',
                                          'clock_id=1 ns=%lu tid=%ld ', 'timing_ns(),syscall(178),')
    else:
        text = one(text, 'extern int *__errno_location(void);',
                   'extern int *__errno_location(void);\nstruct timing_ts{long s,n;};extern int clock_gettime(int,struct timing_ts *);')
        text = one(text, 'static long owner;',
                   'static long owner;\nstatic U timing_ns(void){int saved=*__errno_location();struct timing_ts t={0};int rc=clock_gettime(1,&t);*__errno_location()=saved;return rc?0:(U)t.s*1000000000UL+t.n;}')
        for marker in ['FX3_OSD_OWNER_CURRENT ', 'FX3_OSD_HEADLESS_VALIDATE ',
                       'FX3_OSD_HEADLESS_COPY ', 'FX3_OSD102_COMMIT ']:
            text = add_fields_to_existing_log(text, marker, 'clock_id=1 ns=%lu tid=%ld ',
                                              'timing_ns(),syscall(178),')
    target = OUT / (source.stem + '-timing.c')
    target.write_text(text)
    diff = ''.join(difflib.unified_diff(original.splitlines(True), text.splitlines(True),
                                        fromfile=str(source), tofile=str(target)))
    (OUT / (source.stem + '-timing.diff')).write_text(diff)
    rows.append({'kind': kind, 'source': str(source), 'source_sha256': expected,
                 'candidate_source': str(target), 'candidate_sha256': sha(text.encode()),
                 'diff': str(OUT / (source.stem + '-timing.diff')),
                 'only_existing_log_sites_changed': True, 'new_original_instruction_hook': False})

(HERE / 'passive-timing-next/source-receipt.json').write_text(json.dumps({
    'status': 'source_only_not_build_or_guest_validated', 'clock': 'guest CLOCK_MONOTONIC id=1',
    'rows': rows, 'new_log_lines': 0, 'new_dynamic_allocations': 0,
    'new_threads': 0, 'new_instruction_hooks': 0,
}, indent=2) + '\n')
print(json.dumps([{'kind': row['kind'], 'candidate_sha256': row['candidate_sha256']}
                  for row in rows], indent=2))
