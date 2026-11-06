#!/usr/bin/env python3
"""Derive ABI3 with required preselected body tag from sealed154 own code."""
from pathlib import Path
from hashlib import sha256
import json

HERE=Path(__file__).resolve().parent
BASE=HERE.parent
ROOT=BASE.parents[1]


def main():
    prior=BASE/'stage154-isolated-owner-supervisor'
    raw=(prior/'final-receipt.json').read_bytes()
    assert sha256(raw).hexdigest()=='179ccacabb5c1cd30f6ad85c704499a27f15e2952ad6309fa80087742fdbc8bf'
    pins={m['path']:m for m in json.loads(raw)['files']}
    records=[]
    for name in ['owner_trial.h','owner_core.c','owner_iokit.c','owner_fixture.c','owner_ipc.c','owner_binding.py']:
        p=prior/name;data=p.read_bytes();assert sha256(data).hexdigest()==pins[p.relative_to(ROOT).as_posix()]['sha256']
        text=data.decode()
        if name=='owner_trial.h':
            text=text.replace('#define FX3_OWNER_ABI 2u','#define FX3_OWNER_ABI 3u')
            text=text.replace('uint8_t privacy_key[32];','uint8_t privacy_key[32];\n    uint8_t expected_body_tag[32];')
        elif name=='owner_core.c':
            text=text.replace('!tag_present(c->privacy_key))','!tag_present(c->privacy_key) || !tag_present(c->expected_body_tag))')
            text=text.replace('if (rc || !identity(c,&r->before)) goto cleanup;',
                'if (rc || !identity(c,&r->before) || memcmp(c->expected_body_tag,r->before.body_tag,32)) goto cleanup;')
        elif name=='owner_fixture.c':text=text.replace('0x46495834','0x46495835')
        elif name=='owner_binding.py':
            text=text.replace("('privacy_key', C.c_uint8 * 32)]","('privacy_key', C.c_uint8 * 32), ('expected_body_tag', C.c_uint8 * 32)]")
            text=text.replace('0x46495834','0x46495835').replace('result.abi != 2','result.abi != 3')
        with (HERE/name).open('x') as f:f.write(text)
        records.append({'source':p.relative_to(ROOT).as_posix(),'source_sha256':sha256(data).hexdigest(),'output':name,
            'output_sha256':sha256(text.encode()).hexdigest()})
    with (HERE/'source-derivation.json').open('x') as f:json.dump({'ABI':3,'sources':records,'new_device_operations':0},f,indent=2)
    (HERE/'prepare-executed.py').write_bytes(Path(__file__).read_bytes())
    print(json.dumps({'ABI':3,'sources':len(records),'real_native_loaded':False}))


if __name__=='__main__':main()
