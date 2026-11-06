#!/usr/bin/env python3
"""Pin public maintainer metadata reference; never import/execute its parser."""
import datetime,hashlib,json,subprocess,urllib.request
from pathlib import Path
HERE=Path(__file__).resolve().parent
REPO='DavidBuchanan314/ILCE-7M4-RE';FILE='scripts/parse_emmc_boot0.py'
def get(url):
    request=urllib.request.Request(url,headers={'User-Agent':'FX3-offline-metadata-research'})
    try:
        with urllib.request.urlopen(request,timeout=25) as r:return r.read(),r.status,r.geturl()
    except Exception as e:
        attempts=HERE/'attempts';attempts.mkdir(exist_ok=True)
        n=1
        while (attempts/f'network-fallback-{n}.json').exists():n+=1
        (attempts/f'network-fallback-{n}.json').write_text(json.dumps(dict(url=url,error_type=type(e).__name__,error=str(e),
            fallback='System curl with normal certificate verification; no security downgrade.'),indent=2)+'\n')
        result=subprocess.run(['/usr/bin/curl','--fail','--location','--silent','--show-error','--max-time','25',
            '--write-out','\n%{http_code}\n%{url_effective}',url],capture_output=True,check=True)
        body,status,final=result.stdout.rsplit(b'\n',2)
        return body,int(status),final.decode()
def main():
    out=HERE/'public-layout-reference.json';assert not out.exists()
    refs=HERE/'references';refs.mkdir(exist_ok=True)
    api=f'https://api.github.com/repos/{REPO}/commits?path={FILE}&per_page=1'
    cached=refs/'commit-api.raw.json'
    if cached.exists():data=cached.read_bytes()
    else:
        data,status,url=get(api);assert status==200
        cached.write_bytes(data)
    commits=json.loads(data);assert isinstance(commits,list) and commits
    revision=commits[0]['sha'];assert len(revision)==40
    source_url=f'https://raw.githubusercontent.com/{REPO}/{revision}/{FILE}'
    source,status,final=get(source_url);text=source.decode()
    assert 'assert boot0.startswith(b"EXBL")' in text
    assert 'esram = boot0[:0x800]' in text and 'assert load_addr == 0xfe04_0800' in text
    f=refs/'parse_emmc_boot0.py.source.txt';assert not f.exists();f.write_bytes(source)
    evidence=dict(retrieved_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),repository=f'https://github.com/{REPO}',
        file=FILE,commit=revision,commit_url=f'https://github.com/{REPO}/commit/{revision}',source_url=source_url,
        bytes=len(source),sha256=hashlib.sha256(source).hexdigest(),saved_source=str(f.relative_to(HERE)),HTTP_status=status,
        metadata_only_facts=dict(magic='EXBL',information_prefix_bytes=0x800,prefix_target_base='0xfe040000',
            next_stage_load_address_check='0xfe040800',start_sector_u32_offset='0x68',load_address_u32_offset='0x6c',
            load_bytes_u32_offset='0x74',entrypoint_u32_offset='0x78'),
        scope='Primary maintainer reference for another model. Only metadata layout is compared. Source is stored as text and not executed/imported; no BootROM/boot0 binary, key material, derivation, decryption, other-model payload or device operation is obtained/run. This does not establish FX3 boot0 availability or exact model compatibility.')
    out.write_text(json.dumps(evidence,indent=2)+'\n')
    print(json.dumps({k:evidence[k] for k in ['commit','bytes','sha256','metadata_only_facts']}))
if __name__=='__main__':main()
