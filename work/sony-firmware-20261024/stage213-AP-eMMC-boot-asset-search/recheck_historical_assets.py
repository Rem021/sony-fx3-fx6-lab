"""Re-index two pinned original packages with reviewed host CBC/tar readers.

No source mutation, old-stage logging, target code execution or device calls.
Public format constants stay only in memory and are not printed or saved.
"""
from pathlib import Path
from hashlib import sha256,file_digest
import ast,ctypes,io,json,struct,subprocess,tarfile,types,urllib.request,warnings,zlib
H=Path(__file__).resolve().parent;B=H.parent;R=H.parents[2]
T=R/'work/fx3-color-port-20261027/tail-20261028'
C=T.parent/'package-20261028/cbc_vectors.py'
source=C.read_bytes();tree=ast.parse(source)
constants={}
for n in tree.body:
    if isinstance(n,ast.Assign):
        for t in n.targets:
            if isinstance(t,ast.Name) and t.id in ['SOURCE','PIN']:constants[t.id]=ast.literal_eval(n.value)
assert constants['PIN']=='f9ff02a3889b587cd5bad5f4362fb73fee2f8f3591fc3ed6003eb8ac92d0622a'
urls=[constants['SOURCE'],'https://cdn.jsdelivr.net/gh/DavidBuchanan314/fwtool.py@3955d7890fc38daf942bb52827599bfe35de4a14/fwtool/sony/constants.py']
errors=[]
for url in urls:
    try:
        pub=urllib.request.urlopen(url,timeout=20).read()
        assert sha256(pub).hexdigest()==constants['PIN']
        break
    except (OSError,urllib.error.URLError) as ex:errors.append(dict(url=url,error=str(ex)))
else:
    # The Python TLS path failed. The system HTTPS client is a separate transport;
    # its stdout remains in memory, with the same fixed source digest requirement.
    trial=subprocess.run(['/usr/bin/curl','--fail','--location','--connect-timeout','10',
        '--max-time','30','--silent','--show-error',urls[0]],capture_output=True)
    if trial.returncode!=0:
        (H/'format-fetch-failure.json').open('x').write(json.dumps(dict(errors=errors,
            curl_returncode=trial.returncode,curl_error=trial.stderr.decode(errors='replace')),indent=2)+'\n')
        raise RuntimeError('Pinned format source unavailable by both transports; no package claim made')
    pub=trial.stdout;assert sha256(pub).hexdigest()==constants['PIN'];url=urls[0]
    errors.append(dict(transport='system curl',result='success; same pinned hash; memory only'))
with warnings.catch_warnings():
    warnings.simplefilter('ignore',SyntaxWarning);public_tree=ast.parse(pub)
keys={}
for n in public_tree.body:
    if isinstance(n,ast.Assign):
        for t in n.targets:
            if isinstance(t,ast.Name) and t.id in ['key_aes','key_cxd90057_k0','key_cxd90057_k8']:
                keys[t.id]=ast.literal_eval(n.value)
assert len(keys)==3
ns=dict(ctypes=ctypes)
crypt=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='crypt')
exec(compile(ast.Module(body=[crypt],type_ignores=[]),'<reviewed host Apple AES wrapper>','exec'),ns)
cbc=types.SimpleNamespace(crypt=ns['crypt'])
reader=T/'read_original_fdat.py';src=reader.read_bytes()
nodes=[n for n in ast.parse(src).body if isinstance(n,(ast.ClassDef,ast.FunctionDef)) and n.name in ['FDAT','View','inventory']]
ns=dict(Path=Path,sha256=sha256,file_digest=file_digest,io=io,struct=struct,tarfile=tarfile,zlib=zlib,cbc=cbc,HERE=T)
exec(compile(ast.Module(body=nodes,type_ignores=[]),'<reviewed host FDAT and tar classes>','exec'),ns)
prior=json.loads((T/'interim-fdat-inventory.json').read_text());outputs=[]
for row in prior['packages']:
    f=ns['FDAT'](T/row['source'],keys,row['source_sha256'])
    try:
        members=ns['inventory'](f);assert members==row['tar_members']
        hits=[m for m in members if any(s in m['name'].lower() for s in ['loader_emmc','nflashab','boot0','0200_loader'])]
        nor=next(m for m in members if m['name']=='0750_nor_loader/loader_nor.tar')
        data=f.read(f.header['firmware_offset']+nor['data_offset_in_tar'],nor['size'])
        with tarfile.open(fileobj=io.BytesIO(data),mode='r:') as tar:
            inners=[dict(name=m.name,bytes=m.size,sha256=sha256(tar.extractfile(m).read()).hexdigest()) for m in tar if m.isfile()]
        assert len(inners)==4 and not any('emmc' in m['name'].lower() or 'boot0' in m['name'].lower() for m in inners)
        outputs.append(dict(source=str(f.path.relative_to(R)),source_sha256=f.sha256,
            source_bytes=f.path.stat().st_size,version=f.header['firmware_version'],model_id=f.header['model_id'],
            outer_CRC32_verified=f.outer_crc32,header_CRC32_verified=True,
            outer_tar_members=len(members),member_inventory_matches_prior=True,
            AP_boot_asset_name_matches=hits,NOR_archive_sha256=sha256(data).hexdigest(),NOR_members=inners,
            checked_plaintext_blocks=len(f.checked),all_plaintext_blocks_checked=len(f.checked)==f.count,
            source_open_readonly=True))
    finally:f.close()
out=dict(status='RECHECKED_TWO_HISTORICAL_PACKAGE_TOP_AND_NOR_INNER_INVENTORIES',
    packages=outputs,reader_path=str(reader.relative_to(R)),reader_sha256=sha256(src).hexdigest(),
    AES_wrapper_path=str(C.relative_to(R)),AES_wrapper_sha256=sha256(source).hexdigest(),
    public_format_url=url,public_format_sha256=sha256(pub).hexdigest(),public_format_preceding_errors=errors,
    bounded_absence_scope='Reviewed top-level package names and NOR inner members only; not a proof of global unavailability or all opaque content.',
    no_current_body_identity_attestation=True,original_stage_files_modified=False,
    Sony_code_or_guest_execution=False,root_or_device_operations=0)
(H/'historical-AP-asset-recheck.json').open('x').write(json.dumps(out,indent=2)+'\n')
print(json.dumps(dict(packages=len(outputs),versions=[r['version'] for r in outputs],
    outer_member_counts=[r['outer_tar_members'] for r in outputs],AP_name_matches=[r['AP_boot_asset_name_matches'] for r in outputs],
    NOR_inner_counts=[len(r['NOR_members']) for r in outputs],Sony_or_device_execution=False)))
