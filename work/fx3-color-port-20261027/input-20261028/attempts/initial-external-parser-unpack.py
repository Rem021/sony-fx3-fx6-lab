#!/usr/bin/env python3
"""Inventory original SquashFS initrds and extract selected ordinary update components."""
from pathlib import Path,PurePosixPath
from hashlib import sha256
import ipaddress,json,re,subprocess,sys,urllib.parse,urllib.request

HERE=Path(__file__).resolve().parent
PREV=HERE.parent/'package-20261028'


def download_pinned(url,pin):
    route=[];data=None
    try:data=urllib.request.urlopen(url,timeout=10).read();route.append(dict(method='system DNS',success=True))
    except OSError as error:route.append(dict(method='system DNS',success=False,error=str(error)))
    if data is None:
        host=urllib.parse.urlsplit(url).hostname
        request=urllib.request.Request('https://1.1.1.1/dns-query?name='+host+'&type=A',headers={'Accept':'application/dns-json'})
        dns=json.load(urllib.request.urlopen(request,timeout=15));assert dns['Status']==0
        addresses=[a['data'] for a in dns.get('Answer',[]) if a['type']==1 and ipaddress.ip_address(a['data']).is_global]
        for address in addresses:
            args=['curl','--silent','--show-error','--fail','--connect-timeout','8','--max-time','20','--resolve',host+':443:'+address,url]
            result=subprocess.run(args,capture_output=True);route.append(dict(method='per-request encrypted DNS address',address=address,exit_code=result.returncode))
            if result.returncode==0:data=result.stdout;break
    assert data is not None and sha256(data).hexdigest()==pin,'Pinned parser unavailable or changed'
    return data,route


def main():
    receipt=json.loads((PREV/'parser-source-receipt.json').read_bytes());work=HERE/'work';work.mkdir(exist_ok=True)
    wheel=work/'PySquashfsImage-0.9.0-py2.py3-none-any.whl';assert not wheel.is_symlink()
    if wheel.exists():data=wheel.read_bytes();route=[dict(method='verified task-local existing wheel')]
    else:data,route=download_pinned(receipt['url'],receipt['sha256']);wheel.write_bytes(data)
    assert sha256(data).hexdigest()==receipt['sha256']
    (HERE/'initrd-parser-source-receipt.json').write_text(json.dumps(dict(url=receipt['url'],version=receipt['version'],sha256=receipt['sha256'],bytes=len(data),route=route,wheel=str(wheel.relative_to(HERE)),tls_verification_enabled=True,global_network_settings_modified=False),indent=2)+'\n')
    sys.path.insert(0,str(wheel))
    from PySquashfsImage import SquashFsImage
    packages=json.loads((HERE/'updater-fat-extraction-results.json').read_bytes())['packages'];results=[]
    for package in packages:
        member=next(f for f in package['files'] if f['path']=='/boot/initrd.img');data=(HERE/member['output']).read_bytes()
        assert sha256(data).hexdigest()==member['sha256'] and data[:4]==b'hsqs'
        out=HERE/'initrd-components'/package['version'];out.mkdir(parents=True,exist_ok=True);rows=[];selected_bytes=0
        with SquashFsImage.from_bytes(data) as image:
            for entry in image:
                path=PurePosixPath(entry.path);assert '..' not in path.parts
                row=dict(path=str(path),size=entry.size,mode=entry.filemode)
                if entry.is_symlink:row.update(type='symlink',target=entry.readlink())
                elif entry.is_dir:row.update(type='directory')
                elif entry.is_file:
                    row['type']='file'
                    if re.search(r'sdfile|updater|crypt|skd|(^|/)(init|linuxrc)$|/etc/init|config.*\.xml',str(path),re.I):
                        assert 0<=entry.size<=32*1024*1024
                        raw=entry.read_bytes();assert len(raw)==entry.size
                        selected_bytes+=len(raw);assert selected_bytes<=128*1024*1024
                        dest=out/str(path).lstrip('/');assert dest.resolve().is_relative_to(out.resolve());dest.parent.mkdir(parents=True,exist_ok=True)
                        assert not dest.exists();dest.write_bytes(raw)
                        row.update(sha256=sha256(raw).hexdigest(),output=str(dest.relative_to(HERE)))
                else:row['type']='special_record_only'
                rows.append(row)
        result=dict(version=package['version'],source=member['output'],source_sha256=member['sha256'],entries=rows,selected_regular_bytes=selected_bytes)
        results.append(result);print('INITRD_INDEX_COMPLETE',package['version'],'entries',len(rows),'selected_bytes',selected_bytes,flush=True)
        for row in rows:
            if row.get('output'):print(row['path'],row['size'],flush=True)
    (HERE/'updater-initrd-inventory.json').write_text(json.dumps(dict(status='PASS_ORIGINAL_INITRD_SELECTED_COMPONENTS',packages=results,
        scope='Static decompression only; no mount, symlink/device creation or execution of extracted Sony files. Component names do not prove input acceptance or firmware compatibility.'),indent=2)+'\n')


if __name__=='__main__':main()
