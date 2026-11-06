#!/usr/bin/env python3
"""Fork the sealed guest-only writer with an exact FH profile and match view."""
from pathlib import Path
import json
import sys

STAGE=Path(__file__).resolve().parent
BASE=STAGE.parent
sys.path.insert(0,str(BASE/'stage54-native-open-matcher-input'))
import open_matcher_input as f


def main():
    f.im.volume()
    old=BASE/'stage37-compiled-scoped-writer'
    source=(old/'scoped_writer.c').read_text()
    assert f.im.sha((old/'scoped_writer.c').read_bytes())==next(x['sha256'] for x in
      json.loads((old/'final-receipt.json').read_text())['files'] if x['path'].endswith('/scoped_writer.c'))
    source=source.replace('#define MAGIC 0x4658334733373031ULL','#define MAGIC 0x4658334735373031ULL')
    a=source.index('INLINE int profile(');z=source.index('INLINE int audit(',a)
    source=source[:a]+'''static const u8 expected_hd16m[136]={
#include "expected_hd16m.inc"
};
INLINE int target_descriptor(const u8 *d) {
    for (u32 i=0;i<136;i++) if (d[i]!=expected_hd16m[i]) return 0;
    return 1;
}
INLINE int profile(const u8 *o) {
    return target_descriptor(o+0xe110) &&
        *(const u32*)(o+0xe470)==0x19450;
}
'''+source[z:]
    source+='''

/* This is OUR guest-only ABI, never a Sony hook. A separate temporary view
 * changes only the quality used for table matching. Original source/common
 * descriptor stays FH/16M. Full owner/session/epoch/locking provenance is NOT
 * implemented; these are strict experimental inputs and a private lock only.
 */
u64 fx3_match_view(Control *c,const u8 *src,u8 *dst,u64 epoch,u64 session) {
    if (!c || c->magic!=MAGIC) return BAD_ABI;
    u64 unlocked=0;
    if (!__atomic_compare_exchange_n(&c->lock,&unlocked,1,0,
                                    __ATOMIC_ACQUIRE,__ATOMIC_RELAXED)) return BUSY;
    if (c->epoch!=epoch || c->session!=session) return done(c,BAD_ABI);
    if (c->fault || !audit(c)) return done(c,FAULT);
    if (!c->gate || c->phase || c->live) return done(c,CLOSED);
    if (c->observed_epoch!=c->epoch) return done(c,EPOCH);
    if (!c->owner || (c->owner&7)) return done(c,OWNER);
    if (!src || !dst || ((u64)src&3) || ((u64)dst&3)) return done(c,SCOPE);
    if ((u64)src>MAX64-152 || (u64)dst>MAX64-152) return done(c,SCOPE);
    if ((u64)src<(u64)dst+152 && (u64)dst<(u64)src+152) return done(c,SCOPE);
    const u8 *o=(const u8*)c->owner;
    if (!target_descriptor(src) || !target_descriptor(o+0xe110)) return done(c,SCOPE);
    if (*(const u32*)(src+0x88)!=1 || *(const u32*)(src+0x8c)!=10 ||
        *(const u32*)(src+0x90)!=25) return done(c,SCOPE);
    for (u32 i=0;i<152;i++) dst[i]=src[i];
    *(u32*)(dst+0x38)=6;
    return done(c,OK);
}
'''
    descriptor=f.inputs()[0][1];assert len(descriptor)==136
    expected=(old/'expected_ff.inc').read_bytes()
    outputs={'resource_alias.c':source.encode(),'expected_ff.inc':expected,
      'expected_hd16m.inc':(','.join(hex(x) for x in descriptor)+'\n').encode()}
    for name,raw in outputs.items():
        p=STAGE/name
        with p.open('xb') as out:out.write(raw)
    f.im.write_json(STAGE/'prototype-source-origin.json',{
      'source':str((old/'scoped_writer.c').relative_to(f.ROOT)),
      'source_sha256':f.im.sha((old/'scoped_writer.c').read_bytes()),
      'transformations':['new prototype magic','exact original136byte FH descriptor guard',
        'new separate152byte matcher view with quality6 only; original descriptor unchanged'],
      'expected_descriptor_hex':descriptor.hex(),
      'outputs':{n:f.im.sha(raw) for n,raw in outputs.items()},
      'camera_hook_or_real_epoch_binding':False})


if __name__=='__main__':main()
