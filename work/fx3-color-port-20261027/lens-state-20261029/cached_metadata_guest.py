#!/usr/bin/env python3
"""Original UFP metadata comparisons; live-query branch stops before OSAL."""
from pathlib import Path
import hashlib,json,struct,sys
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'ap-input-20261029'))
from current_static import View,sources
sys.path.insert(0,str(HERE.parent/'marker-20261029'))
from keytag_factory_guest import Guest as LoaderGuest,STACK,STOP,R

BASE=0x40000000

class Guest(LoaderGuest):
    def __init__(self,view,fixture):
        super().__init__([(BASE,view)]);self.fixture=fixture;self.boundary=None;self.global_writes=[]
        f=dict(incoming_model=0x91a00080,cached_model=0x91a00080,incoming_region=0,cached_region=0,incoming_version=0x0102,cached_version=0x0101,skip_version=0,query_live=0)
        f.update(fixture);self.declared=f
        for offset,key,fmt in [(0x15208,'incoming_model','I'),(0x1520c,'incoming_region','I'),(0x15210,'incoming_version','H'),
                               (0x2525c,'cached_model','I'),(0x25260,'cached_region','I'),(0x25264,'cached_version','H'),(0x252b8,'skip_version','I'),(0x151f4,'query_live','I')]:
            self.u.mem_write(BASE+offset,struct.pack('<'+fmt,f[key]))

    def write_guard(self,u,access,address,size,value,user):
        if BASE+0x2525c<=address and address+size<=BASE+0x25266:
            self.global_writes.append(dict(address=hex(address),bytes=size,value=value,pc=hex(u.reg_read(R.UC_ARM64_REG_PC))));return
        return super().write_guard(u,access,address,size,value,user)

    def code(self,u,pc,size,user):
        self.steps+=1;assert self.steps<2000
        if pc==STOP:u.emu_stop();return
        if pc in self.plt:
            assert self.plt[pc]=='osal_valloc_msg_wait'
            self.boundary=dict(operation='before_OSAL_allocation',pc=hex(pc),service=hex(u.reg_read(R.UC_ARM64_REG_X0)),message_bytes=u.reg_read(R.UC_ARM64_REG_X2),native_call=False)
            assert self.boundary['service']=='0x912503d0' and self.boundary['message_bytes']==20
            u.emu_stop();return
        assert BASE+0x1dbc<=pc<BASE+0x1f64,('outside original metadata-check window',hex(pc))

    def execute(self):
        u=self.u
        for i in range(19,30):u.reg_write(getattr(R,f'UC_ARM64_REG_X{i}'),0x77770000+i)
        u.reg_write(R.UC_ARM64_REG_SP,STACK+0xf000);u.reg_write(R.UC_ARM64_REG_X30,STOP)
        u.emu_start(BASE+0x1dbc,STOP+4,count=2000)
        if self.boundary:assert u.reg_read(R.UC_ARM64_REG_PC)==int(self.boundary['pc'],16)
        else:
            assert u.reg_read(R.UC_ARM64_REG_PC)==STOP and u.reg_read(R.UC_ARM64_REG_SP)==STACK+0xf000
            assert all(u.reg_read(getattr(R,f'UC_ARM64_REG_X{i}'))==0x77770000+i for i in range(19,30))
        return dict(declared_metadata=self.declared,returned=self.boundary is None,result=hex(u.reg_read(R.UC_ARM64_REG_X0)) if self.boundary is None else None,boundary=self.boundary,
                    original_cached_metadata_writes=self.global_writes,instructions=self.steps)

def main():
    source=next(r for r in sources() if Path(r['path']).name=='libupdaterufp.so');view=View(source['path'],source['sha256'])
    fixtures=[('newer_version',{},'0x1'),('same_version',dict(incoming_version=0x0101),'0x142'),('older_version',dict(incoming_version=0x0100),'0x142'),
              ('model_mismatch',dict(cached_model=0x91a00081),'0x140'),('region_mismatch',dict(cached_region=1),'0x141'),
              ('skip_version_older',dict(skip_version=1,incoming_version=0x0100),'0x1'),('skip_version_model_mismatch',dict(skip_version=1,cached_model=0x91a00081),'0x140'),
              ('normal_live_query_flag',dict(query_live=1),None)]
    rows=[]
    for name,fixture,expected in fixtures:
        row=Guest(view,fixture).execute();row['case']=name
        if expected is None:
            assert not row['returned'] and row['boundary'] and len(row['original_cached_metadata_writes'])==3
            assert all(w['value']==0 for w in row['original_cached_metadata_writes'])
        else:assert row['returned'] and row['result']==expected and not row['original_cached_metadata_writes']
        rows.append(row)
    result=dict(source=source['path'],source_sha256=source['sha256'],original_window=dict(va='0x1dbc',bytes=0x1a8,sha256=hashlib.sha256(view.read(0x1dbc,0x1a8)).hexdigest()),cases=rows,
                scope='Original UFP metadata comparison window executes over explicitly synthetic incoming/cached model, region, version, skip flag and live-query flag. Seven cases select its existing cache-only branch, which normal lens preparation does not select; no service reply is fabricated. Live-query=1 clears cached fields then stops at original OSAL allocation entry with no allocation/send/receive. Results characterize local comparison/error rules, not actual lens identity, real state, whole preparation, normal API admission, process launch, native target loading, USB or camera.')
    (HERE/'cached-metadata-results.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(cases=len(rows),model_error='0x140',region_error='0x141',version_error='0x142',live_query_clears_cache_and_stops=True,native_ipc_calls=0,camera_actions=0)))

if __name__=='__main__':main()
