#!/usr/bin/env python3
"""Original resource request building to unbound OSAL allocation branch.

Original global resource metadata constructor is permitted to write only its
known image-backed data object. No OSAL buffer/reply/thread return is invented.
"""
from pathlib import Path
import argparse
import datetime
import json
import struct
import sys
import traceback

STAGE=Path(__file__).resolve().parent
BASE=STAGE.parent
ROOT=BASE.parents[1]
sys.path.insert(0,str(BASE/'stage62-native-manager-factory'))
import manager_factory as last
f61=last.prev;f59=f61.prev;f58=f59.prev
r,im,V,n,p=last.r,last.im,last.V,last.n,last.p
G=V+0x60aa38
GSIZE=0x2010
FLAG=V+0x60ca40
PRIOR_SHA='8e539c1c0b65c360d58e0c9de3f1a5057bf62f63addf3ae00a7cc2415d0aa80d'
EXTRA=[(0x27bca0,0x27bd8c),(0x27bdb4,0x27bec8),(0x27bec8,0x27bf90),
  (0x960a4,0x960c8),(0x96240,0x962bc),(0x964ac,0x964bc),
  (0x989f4,0x98a08),(0x99004,0x99288),(0x992b4,0x992cc),(0x2f028,0x2f03c)]


class Guest(last.Guest):
    def __init__(self,*assets):
        super().__init__(*assets)
        self.ranges.extend((V+a,V+z) for a,z in EXTRA)
        self.boundaries.pop(V+0x27bdb4)
        self.boundaries.pop(V+0x960a4)
        self.boundaries[V+0x2f038]='before_unbound_osal_valloc_msg_wait_indirect_branch'
        self.boundaries[V+0x27bd8c]='before_unexecuted_resource_metadata_assertion'
        self.boundaries[V+0x96024]='before_unexecuted_message_error_diagnostic'
        self.global_stores=[];self.resource_constructor_entries=[];self.message_entries=[]
        self.allocation_entries=[]
        assert self.blob[G-V:G-V+GSIZE]==bytes(GSIZE)

    def code(self,u,pc,size,user):
        reg=lambda i:u.reg_read(getattr(r.reg,'UC_ARM64_REG_X'+str(i)))
        if pc==V+0x27bdb4:
            self.provider_entries.append({'pc':hex(pc),'LR':hex(reg(30)),
              'SP':hex(u.reg_read(r.reg.UC_ARM64_REG_SP)),
              'x0_x5':[hex(reg(i)) for i in range(6)],'body_executed':True,
              'provider_return_adapter':False})
            return f61.Guest.code(self,u,pc,size,user)
        if pc==V+0x27bca0:
            self.resource_constructor_entries.append({'pc':hex(pc),'object':hex(reg(0)),
              'LR':hex(reg(30)),'initial_global_object_zero':self.read(G,GSIZE)==bytes(GSIZE)})
        if pc==V+0x99004:
            msg=reg(2);data=self.read(msg+0x18,0xd8)
            self.message_entries.append({'pc':hex(pc),'message_object':hex(msg),
              'command':hex(reg(1)),'state_u32':last.word(self,msg+8),
              'size_u16':struct.unpack('<H',self.read(msg+0xc,2))[0],
              'source_u32':hex(last.word(self,msg+0x10)),
              'inline_payload216_hex':data.hex(),'payload_created_by_native_code':True})
        if pc==V+0x2f038:
            self.allocation_entries.append({'pc':hex(pc),'branch_X4':hex(reg(4)),
              'x0_x3':[hex(reg(i)) for i in range(4)],'LR':hex(reg(30)),
              'SP':hex(u.reg_read(r.reg.UC_ARM64_REG_SP)),
              'indirect_branch_executed':False,'buffer_or_OSAL_return_adapter':False})
        return super().code(u,pc,size,user)

    def store(self,u,access,address,size,value,user):
        if G<=address and address+size<=G+GSIZE:
            pc=u.reg_read(r.reg.UC_ARM64_REG_PC)
            assert V+0x27bca0<=pc<V+0x27bd8c or (pc==V+0x27be00 and address==FLAG and size==8)
            self.global_stores.append({'pc':hex(pc),'address':hex(address),'size':size,'value':hex(value)})
            return
        return super().store(u,access,address,size,value,user)


def phase(m,label,start,**regs):
    global LAST_PHASE
    e=last.phase(m,label,start,**regs);LAST_PHASE=e
    return e


def linked(assets):
    m=Guest(*assets);events=[n.link(m)]
    m.uc.mem_write(f58.SITE,m.patch)
    m.uc.mem_protect(V,4096,r.unicorn.UC_PROT_READ|r.unicorn.UC_PROT_EXEC)
    m.expected_data={f59.GUARD:1,f59.MUTE:0,f59.CAT1:1,f59.CAT2:1}
    for at,value in m.expected_data.items():
        assert m.blob[at-V]==0;m.uc.mem_write(at,bytes([value]))
    m.uc.mem_protect(f59.MUTE&~4095,4096,r.unicorn.UC_PROT_READ|r.unicorn.UC_PROT_WRITE)
    e=phase(m,'original mute setter1 on declared logger input',0x27d898,x0=f59.LOG,x1=1)
    assert e['reason']=='returned';events.append(e);m.expected_data[f59.MUTE]=1
    # Only data pages around the original resource-metadata object become RW.
    # Stores still must match the exact object range and original writer PCs.
    lo=G&~4095;hi=(G+GSIZE+4095)&~4095
    m.uc.mem_protect(lo,hi-lo,r.unicorn.UC_PROT_READ|r.unicorn.UC_PROT_WRITE)
    return m,events


def prefix(m,events,descriptor,seed):
    m.uc.mem_write(last.MANAGER,bytes([seed])*last.MANAGER_SIZE)
    m.uc.mem_write(last.CTX,bytes(0x390));m.uc.mem_write(last.FACTORY,bytes([seed])*last.FACTORY_SIZE)
    for label,start,at,size,args in (
      ('original manager constructor',0x22cc8c,last.MANAGER,last.MANAGER_SIZE,{'x0':last.MANAGER}),
      ('original factory construction and bindings',0x226d2c,last.FACTORY,last.FACTORY_SIZE,
        {'x0':last.FACTORY,'x1':last.MANAGER}),
      ('original factory free-queue reset',0x2270d4,last.FACTORY,last.FACTORY_SIZE,{'x0':last.FACTORY})):
        events.append(last.isolated_constructor(m,label,start,at,size,**args))
    assert not m.all_logs and len(m.manager_bindings)==8
    assert last.word(m,last.FACTORY+8)==8 and last.word(m,last.FACTORY+0x55ec8)==6
    m.uc.mem_write(last.CTX+0x108,struct.pack('<I',1));m.uc.mem_write(last.CTX+0x118,r.p64(last.MESSAGE))
    m.uc.mem_write(last.MESSAGE,bytes(0xc0));m.uc.mem_write(last.MESSAGE+8,r.p64(last.IDENTITY))
    m.uc.mem_write(last.IDENTITY,struct.pack('<I',p.UID));m.uc.mem_write(last.MESSAGE+0x20,descriptor)
    m.uc.mem_write(r.SP-0x2000,bytes([seed])*0x3000)
    e=phase(m,'original queued request on native factory to channel entry',0x22f34c,x0=last.CTX)
    events.append(e);assert e['reason']=='boundary: before_original_buffer_channel_preparation'


def assert_image(m):
    raw=bytearray(m.read(V,len(m.blob)))
    assert raw[0x1ec:0x884]==m.read(n.MDATA,0x698);raw[0x1ec:0x884]=m.blob[0x1ec:0x884]
    assert raw[f58.SITE-V:f58.SITE-V+4]==m.patch
    raw[f58.SITE-V:f58.SITE-V+4]=m.blob[f58.SITE-V:f58.SITE-V+4]
    for at,value in m.expected_data.items():
        assert raw[at-V]==value;raw[at-V]=m.blob[at-V]
    assert raw[FLAG-V:FLAG-V+8]==r.p64(1)
    raw[G-V:G-V+GSIZE]=m.blob[G-V:G-V+GSIZE]
    assert raw==m.blob
    assert m.read(f58.BRIDGE,len(m.code_bytes))==m.code_bytes
    assert m.read(f58.CONST,len(m.ro_bytes))==m.ro_bytes


def one_case(assets,label,descriptor,seed,expected):
    m,events=linked(assets);prefix(m,events,descriptor,seed)
    assert m.real_returns[0]['W0']==expected
    source=int(m.bridge_entries[0]['source'],16);raw=m.read(source,152)
    assert raw[:136]==descriptor and m.read(last.COMMON+0xe110,136)==descriptor
    m.boundaries.pop(V+0x21dd54)
    e=phase(m,'same native request builds resource metadata and message to unbound allocation '+label,
      0x21dd54,independent=False)
    events.append(e)
    assert e['reason']=='boundary: before_unbound_osal_valloc_msg_wait_indirect_branch',e['reason']
    assert len(m.resource_constructor_entries)==len(m.message_entries)==len(m.allocation_entries)==1
    assert m.resource_constructor_entries[0]['object']==hex(G)
    assert m.resource_constructor_entries[0]['initial_global_object_zero']
    assert m.global_stores and m.provider_entries[0]['body_executed']
    msg=m.message_entries[0];payload=bytes.fromhex(msg['inline_payload216_hex'])
    assert msg['command']=='0x61003c' and msg['state_u32']==2 and msg['size_u16']==216
    assert msg['source_u32']=='0x806800f3'
    expected_payload=bytearray(216)
    struct.pack_into('<HHI',expected_payload,0,0x20,0,0x470)
    struct.pack_into('<HH',expected_payload,0x14,0x1111,0x11)
    assert payload==bytes(expected_payload)
    alloc=m.allocation_entries[0]
    assert alloc['branch_X4']=='0x0' and alloc['x0_x3'][0]=='0x61003c'
    assert alloc['x0_x3'][2:]==['0xd8','0x1'] and alloc['LR']==hex(V+0x9911c)
    assert m.read(V+0x584,8)==bytes(8)
    assert m.read(source,152)==raw and m.read(last.COMMON+0xe110,136)==descriptor
    assert_image(m)
    return {'label':label,'seed':seed,'native_row':expected,'source98_hex':raw.hex(),
      'source_and_common_descriptor_unchanged':True,'channel_entry':m.channel_entries[0],
      'resource_provider_entry':m.provider_entries[0],
      'original_resource_metadata_constructor':m.resource_constructor_entries[0],
      'original_global_stores':m.global_stores,'global_metadata_object_hex':m.read(G,GSIZE).hex(),
      'global_record_count':last.word(m,G+0x2000),
      'native_message':msg,'unbound_allocation':alloc,'events':events,
      'OSAL_buffer_allocation_sync_send_reply_real_thread_or_Hal_executed':False,
      'partial_dispatcher_logger_external_storage_and_request_fixtures_remain':True}


def run(out):
    prior=last.STAGE/'final-receipt.json';assert im.sha(prior.read_bytes())==PRIOR_SHA
    for x in json.loads(prior.read_text())['files']:assert im.sha((ROOT/x['path']).read_bytes())==x['sha256']
    assert (BASE/'GOAL_STATUS.json').read_bytes()==(STAGE/'goal-status-before.json').read_bytes()
    obj=f58.STAGE/'run-post-loader-patch-20261026/match_adapter.a64.o';code,ro,_=f58.object_image(obj.read_bytes())
    wobj=f61.old.STAGE/'run-bounded-stores-20261026/resource_alias.a64.o'
    wcode,wro,functions,_=f61.old.object_image(wobj.read_bytes())
    blob=(BASE/'stage2/extraction/files/nflasha3/av-cam.bin').read_bytes()
    assert im.sha(blob)==im.PINS['stage2/extraction/files/nflasha3/av-cam.bin']
    module=(n.STAGE/'official-files/nflasha15/kmod/liro.ko').read_bytes()
    kernel=(n.STAGE/'official-files/nflasha3/vmlinux.bin').read_bytes()
    assets=blob,module,kernel,code,ro,wcode,wro,functions;inp=p.inputs()
    cases=[one_case(assets,'target FH priorA5',inp[0][1],0xa5,386),
      one_case(assets,'target FH priorC3',inp[0][1],0xc3,386),
      one_case(assets,'stock UHD control',inp[3][1],0xc3,431)]
    proof={'status':'PASS_NATIVE_RESOURCE_MESSAGE_TO_UNBOUND_OSAL_ALLOCATION',
      'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
      'bounded_fragments':sum(len(c['events']) for c in cases),'cases':cases,
      'original_regions':[{'start':hex(a),'end':hex(z),'instructions':im.dump(blob,a,z,V)} for a,z in EXTRA],
      'scope':{'original_global_metadata_constructor_and_message_payload_executed':True,
        'resource_provider_body_executes_but_allocation_indirect_branch_does_not':True,
        'OSAL_return_buffer_sync_send_reply_scheduler_or_hardware_adapter':False,
        'UU_Windows_camera_interface_auth_mode_driver_files_module_WBI_flash':False,
        'goal_complete':False,'persistent_write_release':False}}
    im.write_json(out/'resource-message-results.json',proof)
    (out/'executed-source.py').write_bytes(Path(__file__).read_bytes())
    im.write_json(out/'source-receipt.json',{'script_sha256':im.sha(Path(__file__).read_bytes()),
      'avcam_sha256':im.sha(blob),'LIRO_sha256':im.sha(module),'kernel_sha256':im.sha(kernel),
      'wrapper_object_sha256':im.sha(obj.read_bytes()),'previous_manifest_sha256':PRIOR_SHA,'volume_uuid':im.VOLUME})
    print(json.dumps({'status':proof['status'],'bounded_fragments':proof['bounded_fragments'],
      'global_records':[c['global_record_count'] for c in cases],'goal_complete':False}))


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--output',required=True)
    args=ap.parse_args();im.volume();out=Path(args.output).resolve()
    assert STAGE in out.parents and not out.exists();out.mkdir()
    try:run(out)
    except Exception:
        (out/'attempt-source.py').write_bytes(Path(__file__).read_bytes())
        if 'LAST_PHASE' in globals():im.write_json(out/'last-phase-at-failure.json',LAST_PHASE)
        im.write_json(out/'attempt-failure.json',{'traceback':traceback.format_exc(),'passing_result':False})
        raise


if __name__=='__main__':main()
