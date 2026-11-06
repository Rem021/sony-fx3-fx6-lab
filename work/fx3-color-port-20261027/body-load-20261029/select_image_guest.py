#!/usr/bin/env python3
"""Original bodyExecute image choice, stopping before the mount operation."""
import hashlib,json,struct
from assemble_body_guest import Guest,View,sources,FIRM,FIRM_PIN,HERE,DATA,STACK,STOP,R

class SelectionGuest(Guest):
    def __init__(self,view,stream,marker_exists):
        self.marker_exists=marker_exists;self.mount_boundary=None
        super().__init__(view,stream)
        self.allowed.extend([(0x9064,0x90f8),(0xa0bc,0xa0c4),(0xa208,0xa27c),(0xc1a8,0xc1b8)])

    def code(self,u,pc,size,user):
        if pc in self.plt:
            raw=self.plt[pc];name=self.view.names.get(raw,raw)
            x=[u.reg_read(getattr(R,f'UC_ARM64_REG_X{i}')) for i in range(4)]
            if raw=='__xstat':
                assert x[0]==0 and self.string(x[1])=='/root/IAMUPDATER'
                self.events.append(dict(operation='declared_stat_fixture',path='/root/IAMUPDATER',exists=self.marker_exists))
                self.ret(0 if self.marker_exists else 0xffffffffffffffff);return
            if name.startswith('Updater::LoopMountPoint::LoopMountPoint'):self.ret(0);return
            if name.startswith('Updater::LoopMountPoint::Initialize'):
                self.events.append(dict(operation='mountpoint_initialize_record_only',path=self.string(x[1])));self.ret(0);return
            if name.startswith('Updater::LoopMountPoint::Mount'):
                self.mount_boundary=dict(operation='mount_request_boundary',image=self.string(x[1]),flags=x[2],native_call_executed=False)
                self.events.append(self.mount_boundary);u.emu_stop();return
        return super().code(u,pc,size,user)

    def until_mount(self):
        self.run(0xa244,[DATA+0x10]) # Original thread status Run; only mutexes are host no-ops.
        u=self.u
        for i in range(19,30):u.reg_write(getattr(R,f'UC_ARM64_REG_X{i}'),0x77770000+i)
        u.reg_write(R.UC_ARM64_REG_SP,STACK+0xf000);u.reg_write(R.UC_ARM64_REG_X0,DATA);u.reg_write(R.UC_ARM64_REG_X30,STOP)
        before=self.instructions;u.emu_start(0x9064,STOP+4,count=20000)
        assert self.mount_boundary is not None
        expected='/tmp_updater/updater/bodyimg' if self.marker_exists else '/usr/bin/udtrbody.bin'
        assert self.mount_boundary['image']==expected
        return dict(marker_fixture=self.marker_exists,selected_image=expected,stopped_pc=hex(u.reg_read(R.UC_ARM64_REG_PC)),original_instructions_until_boundary=self.instructions-before,
                    assembled_image_bytes=len(self.sink),assembled_image_sha256=hashlib.sha256(self.sink).hexdigest(),plaintext_cursor_after=self.position,events=self.events)

def main():
    from pathlib import Path
    source=next(s for s in sources() if Path(s['path']).name=='libupdatercorecommon.so');view=View(source['path'],source['sha256']);rows=[]
    with FIRM.open('rb') as stream:
        assert hashlib.file_digest(stream,'sha256').hexdigest()==FIRM_PIN;stream.seek(0);header=stream.read(512)
        for exists in [False,True]:
            g=SelectionGuest(view,stream,exists);g.prepare(header);rows.append(g.until_mount())
    assert all(r['assembled_image_sha256']=='62e86fad175e0326969d5f1cea29d780feb496ce8034acd2c9c3954320d8ccaa' for r in rows)
    result=dict(source_library_sha256=source['sha256'],original_fdat_sha256=FIRM_PIN,cases=rows,
                scope='Original BaseBodyLoader constructor, header checks, createBodyImage, thread running flag and beginning of bodyExecute select the image. stat presence/absence is a declared fixture, not an observed camera/rootfs state. Plaintext ring, file/directory and mutex adapters remain synthetic. Execution stops at the mount helper entry; no mount, chassis check, dlopen, target library, USB or camera execution. Incoming image assembly does not by itself mean that image is selected.')
    (HERE/'image-selection-guest-results.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(cases=2,without_marker=rows[0]['selected_image'],with_marker=rows[1]['selected_image'],mounts_executed=0)))

if __name__=='__main__':main()
