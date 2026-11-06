#!/usr/bin/env python3
"""Derive ABI2 own code from sealed153; never alter the sealed candidate."""
from pathlib import Path
from hashlib import sha256
import json

HERE=Path(__file__).resolve().parent
BASE=HERE.parent
ROOT=BASE.parents[1]
PRIOR=BASE/'stage153-Mac-owned-interface-trial'


def main():
    raw=(PRIOR/'final-receipt.json').read_bytes()
    assert sha256(raw).hexdigest()=='27fbc16f5e22e122de6bb144116be44454f5a52b5c07d9eef2361ae681f57460'
    pins={m['path']:m for m in json.loads(raw)['files']}
    records=[]
    for name in ['owner_trial.h','owner_core.c','owner_iokit.c','owner_fixture.c','owner_binding.py']:
        path=PRIOR/name;source=path.read_bytes()
        assert sha256(source).hexdigest()==pins[path.relative_to(ROOT).as_posix()]['sha256']
        text=source.decode()
        if name=='owner_trial.h':
            text=text.replace('#include <stddef.h>','#include <stddef.h>\n#include <stdatomic.h>')
            text=text.replace('#define FX3_OWNER_ABI 1u','#define FX3_OWNER_ABI 2u')
            text=text.replace('volatile uint32_t active_call_pending;','_Atomic uint32_t active_call_pending;')
            marker='typedef struct {\n    int32_t (*snapshot)'
            assert marker in text
            text=text.replace(marker,'typedef struct { uint32_t abi; _Atomic uint32_t stop_requested; uint32_t reserved[2]; } fx3_owner_control;\n'
                'typedef struct { _Atomic uint32_t released, entered; } fx3_fixture_gate;\n'+marker)
            text=text.replace('fx3_owner_result *, const fx3_owner_ops *, void *);','fx3_owner_result *, fx3_owner_control *, const fx3_owner_ops *, void *);')
        elif name=='owner_core.c':
            assert text.count('fx3_owner_result *r, const fx3_owner_ops *o')==2
            text=text.replace('fx3_owner_result *r, const fx3_owner_ops *o','fx3_owner_result *r, fx3_owner_control *control, const fx3_owner_ops *o')
            text=text.replace('return !r->clock_invalid && now < c->work_deadline_ns;',
                'return !r->clock_invalid && !atomic_load_explicit(&control->stop_requested,memory_order_acquire) && now < c->work_deadline_ns;')
            text=text.replace('ready(c,r,o,p,&last)','ready(c,r,control,o,p,&last)')
            text=text.replace('memset(r,0,sizeof(*r)); r->abi=FX3_OWNER_ABI; r->status=FX3_DENIED;',
                'size_t pending=offsetof(fx3_owner_result,active_call_pending);\n'
                '    memset(r,0,pending);\n'
                '    memset((uint8_t *)r+pending+sizeof(r->active_call_pending),0,sizeof(*r)-pending-sizeof(r->active_call_pending));\n'
                '    atomic_store_explicit(&r->active_call_pending,0,memory_order_release);\n'
                '    r->abi=FX3_OWNER_ABI; r->status=FX3_DENIED;')
            text=text.replace('if (!c || !o || c->abi',
                'if (!c || !o || !control || control->abi!=FX3_OWNER_ABI || control->reserved[0] || control->reserved[1] || c->abi')
        elif name=='owner_iokit.c':
            text=text.replace('int fx3_owner_run(const fx3_owner_config *c,fx3_owner_result *r)',
                'int fx3_owner_run(const fx3_owner_config *c,fx3_owner_result *r,fx3_owner_control *control)')
            text=text.replace('fx3_owner_core(c,r,&ops,&owner)','fx3_owner_core(c,r,control,&ops,&owner)')
        elif name=='owner_fixture.c':
            text=text.replace('#include <stdatomic.h>','#include <stdatomic.h>\n#include <time.h>\n#include <unistd.h>')
            text=text.replace('static atomic_flag running=ATOMIC_FLAG_INIT;',
                'static atomic_flag running=ATOMIC_FLAG_INIT;\nstatic fx3_fixture_gate *block_gate;\nstatic uint32_t block_phase;')
            text=text.replace('++f.calls[phase];',
                '++f.calls[phase];\n    if (block_gate && phase==block_phase) {\n'
                '        atomic_store_explicit(&block_gate->entered,phase,memory_order_release);\n'
                '        while (!atomic_load_explicit(&block_gate->released,memory_order_acquire)) { struct timespec t={0,1000000}; nanosleep(&t,NULL); }\n    }')
            text=text.replace('(void)p;\n    if ((f.option&CLOCK_BACKWARD)',
                '(void)p;\n    if (f.option&512) { struct timespec t; clock_gettime(CLOCK_MONOTONIC,&t); return (uint64_t)t.tv_sec*1000000000ull+(uint64_t)t.tv_nsec; }\n    if ((f.option&CLOCK_BACKWARD)')
            text=text.replace('(void)p; f.now+=(uint64_t)ms*1000000ull;',
                '(void)p; if (f.option&512) { struct timespec t={ms/1000,(long)(ms%1000)*1000000L}; nanosleep(&t,NULL); } else f.now+=(uint64_t)ms*1000000ull;')
            text=text.replace('return 0x46495833;','return 0x46495834;')
            text=text.replace('memset(&f,0,sizeof(f)); f.fail=fail;',
                'memset(&f,0,sizeof(f)); block_gate=NULL; block_phase=0; f.fail=fail;')
            text=text.replace('int fx3_owner_run(const fx3_owner_config *c,fx3_owner_result *r)',
                'int fx3_owner_run(const fx3_owner_config *c,fx3_owner_result *r,fx3_owner_control *control)')
            text=text.replace('fx3_owner_core(c,r,&ops,&f)','fx3_owner_core(c,r,control,&ops,&f)')
            text += '\n__attribute__((visibility("default"))) void fx3_owner_fixture_block(uint32_t phase,fx3_fixture_gate *gate) { block_phase=phase; block_gate=gate; }\n'
        elif name=='owner_binding.py':
            text=text.replace("marker() != 0x46495833", "marker() != 0x46495834")
            text=text.replace('C.POINTER(Config), C.POINTER(Result)]','C.POINTER(Config), C.POINTER(Result), C.POINTER(Control)]')
            text=text.replace('if result.abi != 1','if result.abi != 2')
            text += '\n\nclass Control(C.Structure):\n    _fields_ = [("abi",C.c_uint32),("stop_requested",C.c_uint32),("reserved0",C.c_uint32),("reserved1",C.c_uint32)]\n\nclass FixtureGate(C.Structure):\n    _fields_ = [("released",C.c_uint32),("entered",C.c_uint32)]\n'
        output=HERE/name
        with output.open('x') as handle:handle.write(text)
        records.append({'source_path':path.relative_to(ROOT).as_posix(),'source_sha256':sha256(source).hexdigest(),
            'output':name,'output_sha256':sha256(output.read_bytes()).hexdigest()})
    with (HERE/'source-derivation.json').open('x') as handle:json.dump({'prior_manifest_sha256':sha256(raw).hexdigest(),'files':records,'new_device_operations':0},handle,indent=2)
    (HERE/'prepare-executed.py').write_bytes(Path(__file__).read_bytes())
    print(json.dumps({'derived_files':len(records),'ABI':2,'native_library_loaded':False}))


if __name__=='__main__':main()
