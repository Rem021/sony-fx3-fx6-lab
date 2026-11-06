"""Boot-region worker wire/build/local assembly; no camera transport or launch.

The reference profile fingerprints ordinary main-p3 module files only. It is
not an installed-p1 or loaded-driver attestation, body identity, or recovery.
"""
from hashlib import sha256
from pathlib import Path
import struct
import subprocess
import zlib
from .capture import BLOCK, FALSE_FLAGS, PrivateDirectory, hex_value
from .files import encode, new_directory, read_file, require
from .elflink import link_objects, MAX_OBJECT

UNIT=131072
MAX_BOOT=255*UNIT
WINDOW=128
REQ=b'FX3BOOTREQv1'.ljust(16,b'\0')
CHUNK=b'FX3BOOTCHUNKv1'.ljust(16,b'\0')
MANIFEST=b'FX3BOOTMANv1'.ljust(16,b'\0')
FILE_PROFILE=(
    ('/kmod/emmc.ko',341024,'14d17ea8065e3bc751a699dc644f00d247225640175d2957fb2a44bea39e5e4d'),
    ('/kmod/crypt-emmc.ko',14592,'521589c8eac8b851f1cab29f95f449c7bbaf31639a01331d3bf0ca8866b488b8'),
    ('/kmod/devno.ko',6344,'cca1d9acd87a718c7742d168ea0de402b01a7c04cd40433ff2ca4071150dbc23'))
PROFILE=sha256(b'fx3-7.02-main-p3-boot-read-reference-v1\0'+b''.join(bytes.fromhex(x[2]) for x in FILE_PROFILE)).digest()
SOURCE_SHA='06af135abf4e04ccb7cbc0727d4275ed4faf892fce6175f394a93aa7ce0aaaf5'
ENTRY_SOURCE=(b'.section .text\n.global _start\n.type _start,%function\n_start:\n'
              b'    bl fx3_boot_read_window\n    mov x8, #93\n    svc #0\n    b .\n'
              b'.size _start, .-_start\n.section .note.GNU-stack,"",%progbits\n')
BOOT_FALSE={**FALSE_FLAGS,'same_body_origin_verified':False,'loaded_driver_identity_verified':False,
            'installed_p1_identity_verified':False,'hardware_partition_access_restored':False,
            'boot_contents_plaintext_verified':False}


def geometry(total):
    require(type(total) is int and UNIT<=total<=MAX_BOOT and total%UNIT==0,
            'boot size must be an observed 1..255 multiplier of128KiB; no default size')
    return total//BLOCK


def shape(total,window):
    chunks=geometry(total)
    require(type(window) is int and 0<=window<(chunks+WINDOW-1)//WINDOW,'window outside reported boot region')
    first=window*WINDOW
    return first,min(WINDOW,chunks-first)


def request(capture_id,target,window,expected_total=0):
    require(hex_value(capture_id,32),'nonzero capture ID required')
    require(target in ('boot0','boot1'),'fixed boot0/boot1 target required')
    require(type(window) is int and 0<=window<=3,'invalid boot window')
    require(type(expected_total) is int,'integer geometry required')
    if expected_total:shape(expected_total,window)
    else:require(window==0,'geometry discovery is permitted only in window0')
    role=int(target[-1]);raw=bytearray(128)
    raw[:16]=REQ;raw[16:32]=bytes.fromhex(capture_id)
    struct.pack_into('<IIIIQ',raw,32,1,role,window,BLOCK,expected_total)
    raw[56:88]=PROFILE
    # Scope codes disclose potential access selection and panic; not consent.
    struct.pack_into('<IIII',raw,88,3,252,126+role,1)
    struct.pack_into('<I',raw,124,zlib.crc32(raw[:124]))
    return bytes(raw)


def create_request(capture_id,target,window,expected_total,destination):
    raw=request(capture_id,target,window,expected_total)
    info={'schema':'fx3-boot-request-artifact-v1','target':target,'window':window,
          'expected_total':expected_total,'capture_id':capture_id,'request_sha256':sha256(raw).hexdigest(),
          'file_profile':'official7.02 main-p3 reference; updater marker rejected',
          'kernel_access_selection_may_change':True,'kernel_failure_may_panic':True,
          'camera_operations':0,**BOOT_FALSE}
    new_directory(destination,{'fx3-boot-request-v1.bin':raw,'request-info.json':encode(info)})
    return info


def decode_window(directory,producer_returncode):
    require(type(producer_returncode) is int and producer_returncode==0,
            'normal producer return required; manifest existence alone is insufficient')
    req=read_file(Path(directory)/'request.bin',128)
    require(len(req)==128 and req[:16]==REQ,'boot request magic/length differs')
    capture_id=req[16:32].hex();role,window=struct.unpack_from('<II',req,36)
    require(role in (0,1),'boot target differs')
    target='boot'+str(role);expected_total=struct.unpack_from('<Q',req,48)[0]
    require(req==request(capture_id,target,window,expected_total),'boot request CRC, fields or profile differ')
    raw=read_file(Path(directory)/'manifest.bin',256)
    require(len(raw)==256 and raw[:16]==MANIFEST,'boot manifest magic/length differs')
    v,t,w,first,count,block,total,offset,full_crc,major,minor,guards=struct.unpack_from('<IIIIIIQQIIII',raw,16)
    start,num=shape(total,window)
    windows=(geometry(total)+WINDOW-1)//WINDOW
    name=('nflashaB'+str(role)).encode().ljust(16,b'\0');req_sha=sha256(req).digest()
    footer=struct.unpack_from('<IIIIi',raw,168)
    require((v,t,w,first,count,block,offset,major,minor,guards)==
            (1,role,window,start,num,BLOCK,start*BLOCK,252,126+role,255)
            and (not expected_total or expected_total==total)
            and raw[72:88]==req[16:32] and raw[88:104]==name and raw[104:136]==PROFILE
            and raw[136:168]==req_sha and footer==(zlib.crc32(req[:124]),windows,1,3,0)
            and raw[188:]==bytes(68),'boot manifest range/profile/source/guard/status differs')
    data=bytearray();rows=[]
    for local,index in enumerate(range(start,start+num)):
        row=read_file(Path(directory)/f'chunk-{local:03d}.bin',BLOCK+256)
        require(len(row)==BLOCK+256 and row[:16]==CHUNK,'boot chunk magic/length differs')
        fields=struct.unpack_from('<IIIIQQIIIIII',row,16)
        ver,rr,ww,ii,size,off,want,actual,check,ma,mi,effects=fields
        require((ver,rr,ww,ii,size,off,want,actual,ma,mi,effects)==
                (1,role,window,index,total,index*BLOCK,BLOCK,BLOCK,252,126+role,3)
                and row[72:88]==req[16:32] and row[88:104]==name and row[104:136]==PROFILE
                and row[136:168]==req_sha and row[168:256]==bytes(88),'boot chunk request/source/range differs')
        body=row[256:];require(zlib.crc32(body)==check,'boot chunk CRC differs')
        data.extend(body);rows.append({'index':index,'sha256':sha256(body).hexdigest()})
    require(zlib.crc32(data)==full_crc,'boot window CRC differs')
    return bytes(data),{'capture_id':capture_id,'target':target,'window':window,'first':start,'count':num,
        'total_bytes':total,'windows':windows,'selected_device':[252,126+role],
        'expected_total':expected_total,'profile_sha256':PROFILE.hex(),
        'request_sha256':req_sha.hex(),'manifest_sha256':sha256(raw).hexdigest(),
        'window_sha256':sha256(data).hexdigest(),'chunks':rows,
        'producer_return_supplied_by_caller':True,'kernel_access_selection_may_change':True,
        'kernel_failure_may_panic':True,**BOOT_FALSE}


def assemble_windows(directories,producer_returns,destination,body_tag):
    require(type(directories) in (list,tuple) and 1<=len(directories)<=4 and
            type(producer_returns) in (list,tuple) and len(directories)==len(producer_returns),'one to four boot windows required')
    require(hex_value(body_tag,64),'opaque local body grouping tag required; not device attestation')
    image=bytearray();reports=[];identity=None
    for i,(path,code) in enumerate(zip(directories,producer_returns)):
        data,info=decode_window(path,code)
        key=(info['capture_id'],info['target'],info['total_bytes'],info['profile_sha256'])
        if identity is None:identity=key
        require(key==identity and info['window']==i and (i==0 or info['expected_total']==info['total_bytes']),
                'boot windows mixed, reordered or later geometry not bound')
        image.extend(data);reports.append(info)
    require(len(reports)==reports[0]['windows'] and len(image)==identity[2],'boot region incomplete')
    digest=sha256(image).hexdigest();out=PrivateDirectory(destination)
    try:
        filename='source.'+identity[1]
        out.put(filename,image)
        require(sha256(read_file(out.path/filename,MAX_BOOT)).hexdigest()==digest,'boot image readback differs')
        report={'schema':'fx3-local-boot-assembly-v1','status':'ASSEMBLED_LOCAL_BOOT_WORKER_RECORDS_ONLY',
                'image':filename,'sha256':digest,'bytes':len(image),'target':identity[1],
                'body_tag':body_tag,'body_tag_operator_supplied':True,'windows':reports,
                'producer_return_supplied_by_caller':True,'atomic_snapshot_proven':False,
                'kernel_access_selection_may_change':True,'kernel_failure_may_panic':True,
                'read_view':'selected boot-read decrypt callbacks omitted; actual bytes/restore unverified',
                'camera_operations':0,**BOOT_FALSE}
        out.put('complete.json',encode(report));return report
    finally:out.close()


def build_worker(destination):
    tool=Path(__file__).resolve().parents[1]
    source=tool/'native/fx3_boot_reader.c';entry=tool/'native/boot_entry.S'
    require(sha256(read_file(source,65536)).hexdigest()==SOURCE_SHA and read_file(entry,1024)==ENTRY_SOURCE,
            'boot worker source/entry pin differs')
    directory=PrivateDirectory(destination)
    try:
        directory.put('plan.json',encode({'worker_source_sha256':SOURCE_SHA,
            'entry_source_sha256':sha256(ENTRY_SOURCE).hexdigest(),'profile_sha256':PROFILE.hex(),
            'file_profile':FILE_PROFILE,'updater_marker_rejected':True,
            'kernel_access_selection_may_change':True,'kernel_failure_may_panic':True,
            'camera_operations':0,**BOOT_FALSE}))
        builds=[];objects=[]
        for path,name in ((source,'worker.o'),(entry,'entry.o')):
            out=directory.path/name;require(not out.exists(),'object output exists')
            argv=['/usr/bin/xcrun','clang','-target','aarch64-linux-gnu','-O2','-ffreestanding','-fno-builtin',
                  '-fno-stack-protector','-fno-unwind-tables','-fno-asynchronous-unwind-tables',
                  '-Wall','-Wextra','-Werror','-c',str(path),'-o',str(out)]
            result=subprocess.run(argv,text=True,capture_output=True,umask=0o077)
            require(result.returncode==0,'boot cross-compile failed: '+result.stderr[:512])
            data=read_file(out,MAX_OBJECT);objects.append((name,data));builds.append({'argv':argv,'sha256':sha256(data).hexdigest()})
        raw,report=link_objects(objects,worker_symbol='fx3_boot_read_window')
        require(sha256(read_file(source,65536)).hexdigest()==SOURCE_SHA and read_file(entry,1024)==ENTRY_SOURCE,
                'boot source changed during build')
        directory.put('worker.elf',raw);require(read_file(directory.path/'worker.elf',MAX_OBJECT)==raw,'boot ELF readback differs')
        report.update(worker_symbol='fx3_boot_read_window',builds=builds,file_profile=FILE_PROFILE,
                      boot_capture_candidate=True,updater_marker_rejected=True,
                      kernel_access_selection_may_change=True,kernel_failure_may_panic=True,**BOOT_FALSE)
        directory.put('link.json',encode(report));return report
    finally:directory.close()
