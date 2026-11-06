"""Compare exact old regex decisions with a safe negative prefilter."""
import hashlib
import json
import random
from pathlib import Path

from guarded_reject import ASSERT, RM, guarded_rejects

HERE = Path(__file__).resolve().parent
RUN = HERE.parents[1] / 'runtime/runs/vmopt-20261103-save1800-836febd8/serial.log'
AP104 = HERE.parents[3] / 'menu-repair-01/runtime/runs/ap104light4save1200-2e5d177c/serial.log'
SOURCES = [(RUN, '54dd1237d678dfd5aa2cd03d0b087a5a45a438d69ab63c7365c587a6272270ec'),
           (AP104, '546cb84e55fe55b57c820a71334d53d43548ab8001b440e99c33c737ceef9845')]


def old(text):
    return bool(ASSERT.search(text)), bool(RM.search(text))


def main():
    rng = random.Random(6329)
    alphabet = 'abcXYZ_ \n\rİıſKé中文'
    checked = 0
    for _ in range(5000):
        text = ''.join(rng.choices(alphabet, k=rng.randrange(0, 300)))
        if rng.randrange(4) == 0:
            text += rng.choice(['assert at', 'Assertion', 'exception monitor',
                                'FX3_SIGNAL_OBSERVE x signal=6 ', 'FX3_RM_FOO_REJECT',
                                'FX3_RM_UNKNOWN', 'unknown\n key', 'invalid \t from_type'])
        assert guarded_rejects(text) == old(text)
        checked += 1
    rows = []
    for path, digest in SOURCES:
        data = path.read_bytes()
        assert hashlib.sha256(data).hexdigest() == digest
        for fraction in (0.1, 0.5, 1.0):
            text = data[:int(len(data)*fraction)].decode(errors='replace')
            assert guarded_rejects(text) == old(text)
            rows.append({'path':path.name,'sha256':digest,'fraction':fraction,'old_result':old(text)})
    result={'random_cases':checked,'real_prefixes':rows,'all_equal':True}
    (HERE/'guard-test.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
