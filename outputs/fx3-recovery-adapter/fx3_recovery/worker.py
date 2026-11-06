"""Offline decoder for our fixed Linux worker candidate. No launch/transport."""
from pathlib import Path
from hashlib import sha256
import struct
import zlib
from .capture import BLOCK, CHUNKS, MAX_P1, FALSE_FLAGS, hex_value, shape
from .files import require, local_path, read_file, new_directory, encode

REQ = b'FX3P1REQv1'.ljust(16,b'\0')
CHUNK = b'FX3P1CHUNKv1'.ljust(16,b'\0')
MANIFEST = b'FX3P1MANv1'.ljust(16,b'\0')
NAME = b'cnflasha1'.ljust(16,b'\0')


def request(capture_id, window):
    require(hex_value(capture_id,32), 'nonzero capture ID required')
    first,count = shape(window)
    raw = struct.pack('<16s16sIIIIIIII',REQ,bytes.fromhex(capture_id),1,window,first,count,BLOCK,0,0,0)
    return raw[:52]+struct.pack('<III',zlib.crc32(raw[:52]),0,0)


def decode_window(directory, producer_returncode):
    require(type(producer_returncode) is int and producer_returncode==0,
            'normal producer return required in addition to saved manifest')
    p = local_path(directory)
    req = read_file(p/'request.bin',64)
    require(len(req)==64, 'request length differs')
    capture_id = req[16:32].hex()
    window = struct.unpack_from('<I',req,36)[0]
    require(req==request(capture_id,window), 'request bytes or CRC differ')
    first,count = shape(window)
    raw = read_file(p/'manifest.bin',128)
    require(len(raw)==128 and raw[:16]==MANIFEST, 'manifest magic or length differs')
    version,wire_window,start,num,total,offset,block,crc,major,minor = struct.unpack_from('<IIIIQQIIII',raw,16)
    status,guards,req_crc = struct.unpack_from('<iII',raw,96)
    require((version,wire_window,start,num,total,offset,block)==(1,window,first,count,MAX_P1,first*BLOCK,BLOCK)
            and major>0 and raw[64:80]==req[16:32] and raw[80:96]==NAME
            and status==0 and guards==63 and req_crc==zlib.crc32(req[:52]) and raw[108:]==b'\0'*20,
            'manifest source, range, guard or request differs')
    payload = bytearray(); chunks = []
    for local,index in enumerate(range(first,first+count)):
        row = read_file(p/f'chunk-{local:03d}.bin',BLOCK+128)
        require(len(row)==BLOCK+128 and row[:16]==CHUNK, 'chunk magic or size differs')
        v,w,i,s,size,off,want,actual,check,ma,mi,reserved = struct.unpack_from('<IIIiQQIIIIII',row,16)
        require((v,w,i,s,size,off,want,actual,ma,mi,reserved)==
                (1,window,index,0,MAX_P1,index*BLOCK,BLOCK,BLOCK,major,minor,0)
                and row[72:88]==req[16:32] and row[88:104]==NAME and row[104:128]==b'\0'*24,
                'chunk source, capture, status, range or count differs')
        data = row[128:]
        require(zlib.crc32(data)==check, 'chunk CRC differs')
        payload.extend(data); chunks.append({'index':index,'sha256':sha256(data).hexdigest()})
    require(zlib.crc32(payload)==crc, 'window CRC differs')
    return bytes(payload), {'window':window,'capture_id':capture_id,'selected_device':[major,minor],
        'request_sha256':sha256(req).hexdigest(),'manifest_sha256':sha256(raw).hexdigest(),
        'window_sha256':sha256(payload).hexdigest(),'chunks':chunks,
        'producer_return_supplied_by_caller':producer_returncode,
        'producer_return_independently_observed_on_camera':False, **FALSE_FLAGS}


def assemble_worker_windows(directories, returncodes, destination, body_tag):
    require(type(directories) is list and type(returncodes) is list and len(directories)==len(returncodes)==3,
            'exactly three ordered windows and return codes required')
    require(hex_value(body_tag,64), 'opaque local body grouping tag required')
    windows = [decode_window(p,rc) for p,rc in zip(directories,returncodes)]
    rows = [row for _,row in windows]
    require([r['window'] for r in rows]==[0,1,2] and len({r['capture_id'] for r in rows})==1
            and len({tuple(r['selected_device']) for r in rows})==1, 'mixed, reordered or duplicate capture windows')
    image = b''.join(data for data,_ in windows)
    require(len(image)==MAX_P1, 'assembled worker size differs')
    report = {'schema':'fx3-worker-offline-assembly-v1','status':'DECODED_OFFLINE_WORKER_FILES_ONLY',
        'bytes':len(image),'sha256':sha256(image).hexdigest(),'body_tag':body_tag,
        'windows':rows,'origin_verified':False,'same_point_in_time_snapshot_proven':False,
        'camera_operations':0, **FALSE_FLAGS}
    new_directory(destination,{'source.p1':image,'worker-evidence.json':encode(report)})
    require(read_file(Path(destination)/'source.p1',MAX_P1)==image, 'assembled local image readback differs')
    return report
