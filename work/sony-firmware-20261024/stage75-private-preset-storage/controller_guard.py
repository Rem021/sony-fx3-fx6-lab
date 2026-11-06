#!/usr/bin/env python3
"""One extra guard probe on the already compiled single-controller writer."""
from pathlib import Path
import datetime
import json
import private_storage as p


def main():
    p.im.volume();s=p.STAGE;out=s/'controller-identity-result.json';assert not out.exists()
    completed=json.loads((s/'run-20261026/private-storage-results.json').read_text())
    assert completed['source_receipt']['script_sha256']==p.im.sha((s/'private_storage.py').read_bytes())
    mods,providers,kernel=p.c.d.link.build()
    code,ro,_=p.f.f58.object_image((p.f.f58.STAGE/'run-post-loader-patch-20261026/match_adapter.a64.o').read_bytes())
    wcode,wro,functions,_=p.c.old.object_image((s/'run-20261026/resource_alias.a64.o').read_bytes())
    adapter=p.c.object_image((s/'run-20261026/channel_adapter.a64.o').read_bytes())
    blob=(p.BASE/'stage2/extraction/files/nflasha3/av-cam.bin').read_bytes()
    assert p.im.sha(blob)==p.im.PINS['stage2/extraction/files/nflasha3/av-cam.bin']
    liro=(p.n.STAGE/'official-files/nflasha15/kmod/liro.ko').read_bytes()
    assets=blob,liro,kernel,code,ro,wcode,wro,functions
    m,events=p.linked(assets,mods,providers,adapter)
    # This address is deliberately outside every mapped data area. The new
    # controller-identity guard must reject it before any dereference.
    wrong=0xbad00001
    assert not any(a<=wrong<a+n for a,n in [(p.r.ARENA,p.r.ARENA_SIZE),(p.r.STACK,p.r.STACK_SIZE)])
    m.uc.mem_write(p.c.old.CONTROL,b'\x7b'*296)
    m.uc.mem_write(p.PRIVATE-p.GUARD,b'\x5a'*(256+2*p.GUARD))
    before=m.read(p.r.ARENA,p.r.ARENA_SIZE);reads=[]
    def observe(u,access,address,size,value,user):
        assert p.r.STACK<=address and address+size<=p.r.STACK+p.r.STACK_SIZE,(hex(address),size)
        reads.append({'pc':hex(u.reg_read(p.r.reg.UC_ARM64_REG_PC)),
                      'address':hex(address),'bytes':size})
    hook=m.uc.hook_add(p.r.unicorn.UC_HOOK_MEM_READ,observe)
    e=p.c.phase(m,'new compiled writer rejects another controller address before reading it',
                functions['fx3_candidate'],x0=wrong,x1=0,x2=0,x3=0,x4=p.c.old.EPOCH,x5=p.c.old.SESSION)
    events.append(e);m.uc.hook_del(hook)
    assert e['reason']=='returned' and m.uc.reg_read(p.r.reg.UC_ARM64_REG_X0)==1
    assert m.read(p.r.ARENA,p.r.ARENA_SIZE)==before
    assert all(p.r.STACK<=int(x['address'],16) and int(x['address'],16)+x['size']<=p.r.STACK+p.r.STACK_SIZE
               for x in m.prototype_stores)
    assert not m.rate_entries and not m.kernel_service_entries and not m.message_entries
    p.c.assert_images(m)
    result={'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'status':'PASS_OTHER_CONTROLLER_REJECTED_BEFORE_DEREFERENCE',
        'script_sha256':p.im.sha(Path(__file__).read_bytes()),
        'writer_object_sha256':p.im.sha((s/'run-20261026/resource_alias.a64.o').read_bytes()),
        'supplied_wrong_controller':hex(wrong),'result':1,'data_reads':reads,
        'entire_arena_unchanged':True,'events':events,'bounded_fragments':len(events),
        'model_contract_only_not_real_camera_allocation_capability':True,
        'Windows_UU_camera_operations':False,'goal_complete':False,'persistent_write_release':False}
    p.im.write_json(out,result)
    print(json.dumps({'status':result['status'],'bounded_fragments':len(events),'real_allocation_proven':False}))


if __name__=='__main__':main()
