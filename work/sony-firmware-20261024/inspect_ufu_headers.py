"""Read-only Sony UFU header probe. Does not connect to any camera or execute firmware.
Uses public constant literals from pinned fwtool source, parsed as AST (never executed).
Only downloads 64 KiB prefix and 16-byte IV plus nearby tail range for each package.
"""
import ast, datetime, hashlib, json, pathlib, struct, urllib.request, zlib
from Crypto.Cipher import AES
ROOT=pathlib.Path(__file__).resolve().parent
PIN='3955d7890fc38daf942bb52827599bfe35de4a14'
BASE='https://raw.githubusercontent.com/DavidBuchanan314/fwtool.py/'+PIN+'/'
URLS={'fx3-7.02':'https://support.d-imaging.sony.co.jp/download/NEX/ey8d8a84ee/BODYDATA.DAT?fm=jp','zve1-2.02':'https://support.d-imaging.sony.co.jp/download/NEX/ng461782bf/BODYDATA.DAT?fm=jp'}

def get_range(url,start,end):
    req=urllib.request.Request(url,headers={'Range':f'bytes={start}-{end}'})
    with urllib.request.urlopen(req,timeout=25) as r:
        if r.status!=206: raise ValueError(f'Range unsupported: {r.status}')
        expected=end-start+1
        b=r.read(expected+1)
        if len(b)!=expected: raise ValueError('Unexpected range length')
        return b, {'status':r.status,'url':r.url,'headers':dict(r.headers),'sha256':hashlib.sha256(b).hexdigest()}

src=urllib.request.urlopen(BASE+'fwtool/sony/constants.py',timeout=20).read()
keys={}
for node in ast.parse(src).body:
    if isinstance(node,ast.Assign):
        for target in node.targets:
            if isinstance(target,ast.Name) and target.id in ['key_aes','key_cxd90057_k0','key_cxd90057_k8']:
                keys[target.id]=ast.literal_eval(node.value)
summary={'timestamp_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'method':'first FDAT block decryption only; no full package CRC or signature verification','source_commit':PIN,'constants_source':BASE+'fwtool/sony/constants.py','constants_source_sha256':hashlib.sha256(src).hexdigest(),'packages':{}}
for name,url in URLS.items():
    prefix=(ROOT/(name+'-first64KiB.bin')).read_bytes()
    assert prefix[:8]==b'\x89UFU\r\n\x1a\n'
    receipt=json.loads((ROOT/(name+'-range-receipt.json')).read_text())
    total=int(receipt['headers']['Content-Range'].split('/')[-1])
    offset=8;chunks=[];payload_offset=payload_size=None;usb=[]
    while offset+8<=len(prefix):
        size,typ=struct.unpack_from('>I4s',prefix,offset)
        chunks.append({'header_offset':offset,'type':typ.decode('ascii'),'size':size,'payload_offset':offset+8})
        if typ==b'UDID':
            count=struct.unpack_from('>I',prefix,offset+8)[0]
            for i in range(count):
                pid,vid,mode=struct.unpack_from('>HHB',prefix,offset+12+8*i)
                usb.append({'vid':hex(vid),'pid':hex(pid),'mode':mode})
        if typ==b'FDAT':
            payload_offset,payload_size=offset+8,size
            break
        offset+=8+size
    if payload_offset is None: raise ValueError('No FDAT in prefix')
    iv_offset=payload_offset+payload_size-0x110
    tail,tail_receipt=get_range(url,iv_offset,total-1)
    (ROOT/(name+'-tail.bin')).write_bytes(tail)
    enc=prefix[payload_offset:payload_offset+1024]
    first=AES.new(keys['key_aes'],AES.MODE_ECB).decrypt(enc[:512])
    block=None;chosen=None
    for keyname in ['key_cxd90057_k0','key_cxd90057_k8']:
        trial=first+AES.new(keys[keyname],AES.MODE_CBC,tail[:16]).decrypt(enc[512:])
        expected,flags=struct.unpack_from('<HH',trial,0)
        calc=sum(struct.unpack('<511H',trial[2:]))&0xffff
        data=trial[4:4+(flags&0x7fff)]
        if calc==expected and data[:8]==b'UDTRFIRM':
            block=trial;chosen=keyname;break
    if block is None: raise ValueError('No matching key/checksum')
    data=block[4:]
    header={'magic':data[:8].decode(),'checksum':hex(struct.unpack_from('<I',data,8)[0]),'version_tag':data[12:16].decode(),'mode_type':data[16:17].decode(),'luw_flag':data[20:21].decode(),'firmware_version':f'{data[33]:x}.{data[32]:02x}','model_id':hex(struct.unpack_from('<I',data,36)[0]),'region_id':hex(struct.unpack_from('<I',data,40)[0]),'firmware_offset':struct.unpack_from('<I',data,48)[0],'firmware_size':struct.unpack_from('<I',data,52)[0],'filesystem_count':struct.unpack_from('<I',data,56)[0]}
    header['header_crc32_matches']=zlib.crc32(data[12:512])==int(header['checksum'],16)
    header['first_block_checksum_matches']=True
    fs=[]
    for i in range(28):
        p=64+16*i;mode=data[p:p+1]
        if mode==b'\0':continue
        ofs,sz=struct.unpack_from('<II',data,p+4)
        fs.append({'mode':mode.decode(),'offset':ofs,'size':sz})
    header['filesystems']=fs
    summary['packages'][name]={'source_url':url,'total_package_bytes':total,'prefix_sha256':receipt['sample_sha256'],'chunks':chunks,'usb_descriptors':usb,'fdat_payload_offset':payload_offset,'fdat_payload_size':payload_size,'crypter':chosen,'tail_receipt':tail_receipt,'fdathdr':header,'full_package_downloaded':False,'complete_firmware_decrypted':False,'repacked_or_camera_written':False}
(ROOT/'ufu-header-analysis.json').write_text(json.dumps(summary,indent=2,ensure_ascii=False)+'\n')
print(json.dumps(summary,indent=2,ensure_ascii=False))
