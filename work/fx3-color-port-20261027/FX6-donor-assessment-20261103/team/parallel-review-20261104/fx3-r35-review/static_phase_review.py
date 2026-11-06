#!/usr/bin/env python3
"""Reviewer-owned text/data model; never import/execute candidate or its tests."""
from pathlib import Path
import hashlib
import itertools
import json

HERE = Path(__file__).resolve().parent
ROOT = Path('/Volumes/KAFU2T/AI/Projects/Mac')
D = ROOT / 'work/fx3-vm-20261101/lead-codex/vm-optimization-20261103/runtime/try2-usability/passive-timing-delivery/r35-existing-log-observation-candidate'
EXPECTED = '8b12932497189be9163f2c98ff7273ff097380c62c6142ef0196f4a68669986b'
text = (D / 'src/r35-log.inc').read_bytes()
assert hashlib.sha256(text).hexdigest() == EXPECTED
for fragment in (
    b'unsigned bits=flag!=1?1:0;',
    b'if(!p.w[6]&&!p.w[9])bits|=2;',
    b'if(p.w[6]>=1)bits|=4;if(p.w[6]==2)bits|=8;',
    b'if(p.w[9]>=1)bits|=16;if(p.w[9]==2)bits|=32;',
    b'if(p.w[14])bits|=64;',
    b'if((bits&~r35_seen)&&r35_logs<7&&r35_bytes<=2048-R35_SUFFIX_BYTES)',
    b'r35_seen|=bits;r35_logs++;r35_bytes+=R35_SUFFIX_BYTES;',
):
    assert fragment in text

def bits(pub, bind, loss, flag=1):
    if flag != 1:
        return 1
    result = 2 if not pub and not bind else 0
    if pub >= 1:
        result |= 4
    if pub == 2:
        result |= 8
    if bind >= 1:
        result |= 16
    if bind == 2:
        result |= 32
    if loss:
        result |= 64
    return result

orders = [p for p in itertools.permutations('pPbB')
          if p.index('p') < p.index('P') and p.index('b') < p.index('B')]
assert len(orders) == 6
cases = []
# Each first sight of an independent phase advances a previously unseen bit.
# Vary where the first loss is logged, with and without early unknown/clean logs.
for order in orders:
    for loss_at in range(5):
        for early_unknown, early_clean in itertools.product((False, True), repeat=2):
            seen = logs = pub = bind = loss = 0
            events = []
            def observe(label, flag=1):
                global seen, logs
                current = bits(pub, bind, loss, flag)
                emitted = bool(current & ~seen) and logs < 7 and logs * 184 <= 2048 - 184
                if emitted:
                    seen |= current
                    logs += 1
                events.append({'event': label, 'pub': pub, 'bind': bind,
                               'loss': loss, 'flag': flag, 'bits': current,
                               'emitted': emitted, 'ordinal': logs})
                return emitted
            if early_unknown:
                assert observe('early_unknown', 3)
            if early_clean:
                assert observe('ready_clean')
            for index in range(5):
                if index == loss_at:
                    loss = 1
                    assert observe('first_loss')
                if index == 4:
                    break
                phase = order[index]
                if phase == 'p': pub = 1
                if phase == 'P': pub = 2
                if phase == 'b': bind = 1
                if phase == 'B': bind = 2
                assert observe(phase), (order, loss_at, early_unknown, early_clean, events)
            assert not observe('unchanged_repeat')
            assert pub == bind == 2 and logs <= 7 and logs * 184 <= 1288
            cases.append({'order': ''.join(order), 'loss_at': loss_at,
                          'early_unknown': early_unknown, 'early_clean': early_clean,
                          'logs': logs, 'bytes': logs * 184, 'events': events})

result = {'scope': 'reviewer static formula/data model only; not compiled-C execution, '
                   'not native scheduling or guest validation',
          'source_sha256': EXPECTED, 'source_lines': [26, 36],
          'case_count': len(cases), 'all_independent_advances_exported': True,
          'maximum_logs': max(c['logs'] for c in cases),
          'maximum_bytes': max(c['bytes'] for c in cases), 'cases': cases}
(HERE / 'phase-fix-model.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps({k: v for k, v in result.items() if k != 'cases'}, indent=2))
