#!/usr/bin/env python3
"""Read bounded XAR metadata and component archives without installer actions."""
import datetime
import hashlib
import json
from pathlib import Path, PurePosixPath
import plistlib
import struct
import subprocess
import xml.etree.ElementTree as ET
import zlib

HERE = Path(__file__).resolve().parent


def main():
    assert not (HERE / 'XAR-structure.json').exists()
    volume = plistlib.loads(subprocess.check_output(['diskutil','info','-plist','/Volumes/KAFU2T']))
    assert volume['VolumeUUID'] == 'F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
    original = json.loads((HERE / 'PKG-extraction.json').read_text())
    raw = (HERE / 'AXSMDriveSoftware.pkg').read_bytes()
    assert hashlib.sha256(raw).hexdigest() == original['pkg_sha256']
    magic, header, version, packed, size, algorithm = struct.unpack_from('>4sHHQQI',raw)
    assert magic == b'xar!' and header == 28 and version == 1 and packed < 1024*1024 and size < 4*1024*1024 and algorithm == 1
    compressed = raw[header:header+packed]
    decoder = zlib.decompressobj()
    xml = decoder.decompress(compressed,size+1)
    assert len(xml) == size and decoder.eof and not decoder.unused_data
    root = ET.fromstring(xml)
    toc = root.find('toc')
    heap = header + packed
    checksum = toc.find('checksum')
    assert checksum.attrib['style'] == 'sha1' and int(checksum.findtext('size')) == 20
    checksum_offset = heap + int(checksum.findtext('offset'))
    assert hashlib.sha1(compressed).digest() == raw[checksum_offset:checksum_offset+20]
    rows = []
    def walk(node, prefix=PurePosixPath()):
        for item in node.findall('file'):
            name = item.findtext('name')
            assert name and '/' not in name and name not in ['.','..'] and '\0' not in name
            path = prefix / name
            row = {'path':str(path), 'type':item.findtext('type')}
            data = item.find('data')
            if data is not None:
                offset, length, outsize = [int(data.findtext(k)) for k in ['offset','length','size']]
                assert 0 <= offset <= len(raw)-heap and 0 <= length <= len(raw)-heap-offset and 0 <= outsize < 64*1024*1024
                block = raw[heap+offset:heap+offset+length]
                archived_hash, extracted_hash = data.find('archived-checksum'),data.find('extracted-checksum')
                assert archived_hash.attrib['style'] == extracted_hash.attrib['style'] == 'sha1'
                assert hashlib.sha1(block).hexdigest() == archived_hash.text.lower()
                encoding = data.find('encoding').attrib['style']
                if encoding == 'application/octet-stream':
                    output = block
                elif encoding == 'application/x-gzip':
                    dec = zlib.decompressobj(15+32)
                    output = dec.decompress(block,outsize+1)
                    assert dec.eof and not dec.unused_data
                else:
                    raise ValueError(encoding)
                assert len(output) == outsize and hashlib.sha1(output).hexdigest() == extracted_hash.text.lower()
                row.update(heap_offset=offset, archived_bytes=length, bytes=outsize, encoding=encoding,
                           archived_and_extracted_SHA1_verified=True, sha256=hashlib.sha256(output).hexdigest())
                if name in ['Payload','Scripts','PackageInfo','Distribution']:
                    target = HERE / 'components' / Path(str(path))
                    target.parent.mkdir(parents=True,exist_ok=True)
                    with target.open('xb') as stream:
                        stream.write(output)
                    row['saved_path'] = str(target.relative_to(HERE))
                    row['first8_hex'] = output[:8].hex()
            rows.append(row)
            walk(item,path)
    walk(toc)
    result = {'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source_sha256':original['pkg_sha256'],
              'toc_compressed_SHA1_verified':True,'toc_xml_sha256':hashlib.sha256(xml).hexdigest(),
              'file_entries':len(rows),'entries':rows,'installer_signature_chain_verified':False,
              'scripts_or_installer_executed':False,'device_actions':0,
              'scope':'All ordinary XAR streams checked by internal SHA1; only component archives/metadata saved as non-executable data. No system install or permission change.'}
    (HERE / 'XAR-structure.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'XAR_entries':len(rows),'saved':[{'path':r['path'],'bytes':r['bytes'],'first8':r['first8_hex']} for r in rows if r.get('saved_path') and r['path'].endswith('Payload')]},ensure_ascii=False))


if __name__ == '__main__':
    main()
