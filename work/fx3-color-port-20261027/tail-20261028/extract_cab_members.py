#!/usr/bin/env python3
"""Extract selected original CAB members with system libarchive and a bounded xor read callback."""
from pathlib import Path
from hashlib import sha256,file_digest
import ctypes as C,json,os
from cab_index import Cabinet,HERE,SOURCE

SELECT={'FirmwareA1Data_ILMEFX3V204.dat','FirmwareA2Data_ILMEFX3V205.dat','FirmwareUpdaterImg.dll'}


def main():
    meta=json.loads((HERE/'cab-index-results.json').read_bytes())
    with SOURCE.open('rb') as f:assert file_digest(f,'sha256').hexdigest()==meta['source_sha256']
    expected={r['name']:r for r in meta['files']}
    lib=C.CDLL('/usr/lib/libarchive.2.dylib')
    lib.archive_version_string.restype=C.c_char_p
    lib.archive_read_new.restype=C.c_void_p
    lib.archive_read_support_format_cab.argtypes=[C.c_void_p]
    lib.archive_read_support_filter_none.argtypes=[C.c_void_p]
    lib.archive_read_free.argtypes=[C.c_void_p]
    lib.archive_error_string.argtypes=[C.c_void_p];lib.archive_error_string.restype=C.c_char_p
    lib.archive_read_next_header.argtypes=[C.c_void_p,C.POINTER(C.c_void_p)]
    lib.archive_entry_pathname.argtypes=[C.c_void_p];lib.archive_entry_pathname.restype=C.c_char_p
    lib.archive_entry_size.argtypes=[C.c_void_p];lib.archive_entry_size.restype=C.c_int64
    lib.archive_read_data.argtypes=[C.c_void_p,C.c_void_p,C.c_size_t];lib.archive_read_data.restype=C.c_ssize_t
    lib.archive_read_data_skip.argtypes=[C.c_void_p]
    OPEN=C.CFUNCTYPE(C.c_int,C.c_void_p,C.c_void_p)
    READ=C.CFUNCTYPE(C.c_ssize_t,C.c_void_p,C.c_void_p,C.POINTER(C.c_void_p))
    SKIP=C.CFUNCTYPE(C.c_int64,C.c_void_p,C.c_void_p,C.c_int64)
    CLOSE=C.CFUNCTYPE(C.c_int,C.c_void_p,C.c_void_p)
    lib.archive_read_open2.argtypes=[C.c_void_p,C.c_void_p,OPEN,READ,SKIP,CLOSE]
    cabinet=Cabinet();state={'offset':0,'buffer':None,'error':None};rows=[]
    @OPEN
    def opened(a,data):return 0
    @CLOSE
    def closed(a,data):return 0
    @READ
    def read(a,data,pointer):
        try:
            n=min(1024*1024,cabinet.size-state['offset'])
            if not n:return 0
            block=cabinet.read(state['offset'],n);state['offset']+=n
            state['buffer']=C.create_string_buffer(block,n);pointer[0]=C.addressof(state['buffer']);return n
        except Exception as e:state['error']=repr(e);return -1
    @SKIP
    def skip(a,data,n):
        if n<0:state['error']='negative skip';return -1
        amount=min(n,cabinet.size-state['offset']);state['offset']+=amount;return amount
    def check(code,where):
        error=lib.archive_error_string(a)
        assert code==0 and state['error'] is None,(where,code,state['error'],error.decode() if error else None)
    a=lib.archive_read_new();assert a
    out=HERE/'interim-members';out.mkdir(exist_ok=True);entry=C.c_void_p();buffer=C.create_string_buffer(1024*1024)
    try:
        check(lib.archive_read_support_format_cab(a),'enable CAB')
        check(lib.archive_read_support_filter_none(a),'enable plain filter')
        check(lib.archive_read_open2(a,None,opened,read,skip,closed),'open original cabinet')
        seen=[]
        while True:
            status=lib.archive_read_next_header(a,C.byref(entry))
            if status==1:break
            check(status,'next header')
            name=lib.archive_entry_pathname(entry).decode();length=lib.archive_entry_size(entry)
            assert name in expected and length==expected[name]['bytes'] and name not in seen
            seen.append(name)
            if name not in SELECT:check(lib.archive_read_data_skip(a),'skip member');continue
            dest=out/name;assert dest.parent==out
            if dest.exists():
                old=json.loads((out/(name+'.receipt.json')).read_bytes())
                with dest.open('rb') as f:assert file_digest(f,'sha256').hexdigest()==old['sha256']
                rows.append(old);check(lib.archive_read_data_skip(a),'skip previously extracted member');continue
            partial=dest.with_suffix(dest.suffix+'.part');assert not partial.exists()
            digest=sha256();count=0;last=0
            with partial.open('xb') as f:
                os.chmod(partial,0o600)
                while True:
                    n=lib.archive_read_data(a,buffer,len(buffer));assert n>=0,(name,lib.archive_error_string(a))
                    if not n:break
                    block=buffer.raw[:n];count+=n;assert count<=length
                    digest.update(block);f.write(block)
                    if count-last>=64*1024*1024:print('EXTRACTED',name,count,'/',length,flush=True);last=count
                f.flush();os.fsync(f.fileno())
            assert count==length and state['error'] is None
            partial.rename(dest);row=dict(name=name,bytes=count,sha256=digest.hexdigest(),source_exe_sha256=meta['source_sha256'])
            (out/(name+'.receipt.json')).write_text(json.dumps(row,indent=2)+'\n');rows.append(row)
            print('MEMBER_COMPLETE',name,count,row['sha256'],flush=True)
        assert len(seen)==len(expected) and SELECT=={r['name'] for r in rows}
        result=dict(status='PASS_ORIGINAL_CAB_SELECTED_MEMBERS_EXTRACTED',native_library=lib.archive_version_string().decode(),
                    source_exe_sha256=meta['source_sha256'],members=rows,all_member_headers_checked=len(seen),
                    scope='Native archive decompression only, no installer/DLL/firmware execution. Original installer byte complement is decoded on demand, without another full CAB copy. No modified firmware emitted or camera accessed.')
        (HERE/'cab-extraction-results.json').write_text(json.dumps(result,indent=2)+'\n')
        print(result['status'],'members',len(rows),flush=True)
    finally:lib.archive_read_free(a);cabinet.close()


if __name__=='__main__':main()
