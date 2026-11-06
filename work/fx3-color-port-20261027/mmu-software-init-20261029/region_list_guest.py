#!/usr/bin/env python3
"""Inspect original post-MMU region setup in explicitly separated RAM fragments."""
import hashlib,json,sys
from pathlib import Path
sys.dont_write_bytecode=True
from software_init_guest import SoftwareGuest,old,snapshot
HERE=Path(__file__).resolve().parent
class RegionGuest(SoftwareGuest):
    def write(self,u,access,at,size,value,user):
        if 0xff4308<=at and at+size<=0xff4360:
            self.init[at-old.BASE:at-old.BASE+size]=b'\1'*size
            self.writes+=1
            return
        super().write(u,access,at,size,value,user)
    def code(self,u,pc,size,user):
        if pc==0x5548dc:
            assert bytes(u.mem_read(pc,4))==bytes.fromhex('4ff07ff5')
            self.allowed_barriers.append(dict(PC=hex(pc),instruction='dsb sy',
                scope='Original DSB executed in software-only Unicorn; no physical observer, cache or TLB is modeled.'))
            self.instructions+=1
            return
        super().code(u,pc,size,user)
def main():
    out=HERE/'region-list-results.json';assert not out.exists()
    raw=old.SOURCE.read_bytes();assert hashlib.sha256(raw).hexdigest()==old.PIN
    strict=RegionGuest(raw)
    full_entry=strict.call(0x54ad18)
    assert full_entry['boundary']['PC']=='0x555d34'
    g=RegionGuest(raw)
    boot=g.call(0x1083a4,stops={0x108728:'before_CPU_setup_call'})
    init=g.call(0x553d48,[old.ROOT]);assert init['boundary']['reason']=='returned'
    pools=g.call(0x54ad3c,stops={0x54ae54:'before_original_mutex_initializer_call'})
    assert pools['boundary']['PC']=='0x54ae54'
    # The original mutex initializer is a separate external-state boundary.
    # No success value is supplied. Start the later independent region-list
    # fragment, which does not acquire or inspect that mutex before this stop.
    regions=g.call(0x54ae5c,stops={0x54b3b4:'before_following_cache_helper'})
    results=dict(CP_sha256=old.PIN,strict_original_entry=full_entry,
        bootstrap=boot,software_initializer=init,original_free_pool_fragment=pools,
        original_post_mutex_region_fragment=regions,
        original_table_provider_VA='0x569f74',original_region_table_VA='0xd22a84',
        original_region_count=19,original_mapping_calls=g.mapping_calls,
        modeled_DSB_events=g.allowed_barriers,
        snapshot=snapshot(g,'after_original_region_fragment_in_RAM'),
        scope='Independent RAM fragments, not normal cold boot or full 0x54ad18 completion. Original cache initializer/CPU context, mutex initialization/event signaling and subsequent cache helper are not executed or supplied as successful. All region tables and mapping calls use original CP data and opcodes. No candidate DmmCfg data, physical buffer, RAW pixels, Sony native process or device action.')
    out.write_text(json.dumps(results,indent=2)+'\n')
    print(json.dumps(dict(strict=full_entry['boundary'],pools=pools['boundary'],regions=regions['boundary'],
        region_instructions=regions['original_instructions'],region_writes=regions['original_RAM_writes'],
        queries=[dict(address=x['address'],attributes=x['attributes'],query_R0=x['attribute_call']['registers'][0],
        pointer_R0=x['pointer_call']['registers'][0]) for x in results['snapshot']['cases']])) )
if __name__=='__main__':main()
