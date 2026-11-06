#!/usr/bin/env python3
"""Extract original update-engine members with source-pinned, read-only FDAT access.

Per-request DNS fallback preserves TLS hostname validation and source SHA-256.
No Sony code, installer, updater, signing, MMIO, USB or camera execution.
"""
from pathlib import Path
from hashlib import sha256
import ast,importlib.util,json,os,subprocess,sys,urllib.request,warnings,zlib

HERE=Path(__file__).resolve().parent
PREV=HERE.parent/'tail-20261028'
sys.path.insert(0,str(PREV))
import read_original_fdat as reader

SELECT=('0400_updater/dev/nflasha1','0401_updater_sum/updater.sum','0300_partconf/partinf.conf','0100_config/mount.conf')


def public_keys():
    url=reader.cbc.SOURCE;pin=reader.cbc.PIN;attempts=[];data=None
    try:
        response=urllib.request.urlopen(url,timeout=10);data=response.read()
        attempts.append(dict(route='system DNS',success=True))
    except OSError as error:
        attempts.append(dict(route='system DNS',success=False,error=str(error)))
    dns=None
    if data is None:
        query='https://1.1.1.1/dns-query?name=raw.githubusercontent.com&type=A'
        request=urllib.request.Request(query,headers={'Accept':'application/dns-json'})
        dns=json.load(urllib.request.urlopen(request,timeout=15));assert dns['Status']==0
        addresses=[answer['data'] for answer in dns['Answer'] if answer['type']==1 and answer['name']=='raw.githubusercontent.com']
        assert addresses
        for address in addresses:
            args=['curl','--silent','--show-error','--fail','--connect-timeout','8','--max-time','20',
                  '--resolve','raw.githubusercontent.com:443:'+address,url]
            result=subprocess.run(args,capture_output=True)
            attempts.append(dict(route='per-request explicit DNS address, original TLS hostname',address=address,
                exit_code=result.returncode,error=result.stderr.decode(errors='replace') if result.returncode else None))
            if result.returncode==0:
                data=result.stdout;break
    assert data is not None and sha256(data).hexdigest()==pin,'Pinned public format source unavailable or changed'
    with warnings.catch_warnings():
        warnings.simplefilter('ignore',SyntaxWarning);tree=ast.parse(data)
    keys={}
    for node in tree.body:
        if isinstance(node,ast.Assign):
            for target in node.targets:
                if isinstance(target,ast.Name) and target.id in ('key_aes','key_cxd90057_k0','key_cxd90057_k8'):
                    keys[target.id]=ast.literal_eval(node.value)
    assert len(keys)==3
    (HERE/'format-source-receipt.json').write_text(json.dumps(dict(publisher_url=url,bytes=len(data),sha256=pin,
        attempts=attempts,encrypted_dns_response=dns,tls_verification_enabled=True,global_network_settings_modified=False,
        constants_copied_into_artifacts=False,scope='Public fixed format source consumed as AST literals in memory only; no source code execution.'),indent=2)+'\n')
    return keys


def main():
    original_receipt=json.loads((PREV/'final-receipt.json').read_bytes())
    for name in ('read_original_fdat.py','interim-fdat-inventory.json'):
        row=next(row for row in original_receipt['files'] if row['path']==name)
        assert sha256((PREV/name).read_bytes()).hexdigest()==row['sha256']
    keys=public_keys();meta=json.loads((PREV/'interim-fdat-inventory.json').read_bytes());rows=[]
    for package in meta['packages']:
        path=PREV/package['source'];fdat=reader.FDAT(path,keys,package['source_sha256'])
        version=package['header']['firmware_version'];items=[];outdir=HERE/'original-update-engine'/version;outdir.mkdir(parents=True,exist_ok=True)
        for name in SELECT:
            member=next(item for item in package['tar_members'] if item['name']==name);dest=outdir/Path(name).name
            assert not dest.exists();h=sha256();crc=0;written=0
            with dest.open('xb') as out:
                os.chmod(dest,0o600)
                while written<member['size']:
                    length=min(4*1024*1020,member['size']-written)
                    block=fdat.read(package['header']['firmware_offset']+member['data_offset_in_tar']+written,length)
                    out.write(block);h.update(block);crc=zlib.crc32(block,crc);written+=len(block)
                out.flush();os.fsync(out.fileno())
            items.append(dict(member=name,bytes=written,sha256=h.hexdigest(),crc32=f'{crc:08x}',output=str(dest.relative_to(HERE))))
        sums=(outdir/'updater.sum').read_text();image=next(item for item in items if item['member'].endswith('nflasha1'))
        assert image['crc32'] in sums.lower(),sums
        info=fdat.summary();info['source']=str(path.resolve())
        rows.append(dict(version=version,source_checkpoint='../tail-20261028',source=info,members=items,original_updater_sum=sums,updater_crc32_matches=True));fdat.close()
        print('ORIGINAL_UPDATE_ENGINE_COMPLETE',version,image['bytes'],image['sha256'],'CRC32',image['crc32'],flush=True)
    result=dict(status='PASS_ORIGINAL_INTERIM_UPDATE_ENGINE_EXTRACTED',packages=rows,
        images_identical=rows[0]['members'][0]['sha256']==rows[1]['members'][0]['sha256'],
        scope='Only original selected members extracted. Actual CBC read blocks and original updater CRC32 checked; full package plaintext coverage, tail verification, installer/updater execution and camera admission not established.')
    (HERE/'original-update-engine-results.json').write_text(json.dumps(result,indent=2)+'\n')


if __name__=='__main__':main()
