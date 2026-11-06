"""Extract factual line evidence from the collected Sony GPL excerpts."""
import hashlib,json,pathlib,re
ROOT=pathlib.Path(__file__).resolve().parent
def fact(path,rx):
 s=path.read_text(errors='replace')
 return {'path':str(path.relative_to(ROOT)),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
         'matches':[{'line':i+1,'text':x.strip()} for i,x in enumerate(s.splitlines()) if re.search(rx,x)]}
def analyze(receipt):
 fs=[ROOT/x['path'] for x in receipt['selected_files']]
 make=next((p for p in fs if p.name=='Makefile' and len(pathlib.Path(next(x['member'] for x in receipt['selected_files'] if ROOT/x['path']==p)).parts)<=2),None)
 version=None
 if make:
  vals=dict(re.findall(r'^(VERSION|PATCHLEVEL|SUBLEVEL)\s*=\s*(\d+)',make.read_text(),re.M));version='.'.join(vals[k] for k in ['VERSION','PATCHLEVEL','SUBLEVEL'])
 platforms=[]
 for p in fs:
  if p.suffix not in ('.dts','.dtsi'):continue
  s=p.read_text(errors='replace')
  if not re.search(r'compatible\s*=\s*"arm,cortex-a\d+"',s):continue
  cpus=re.findall(r'compatible\s*=\s*"(arm,cortex-a\d+)"',s)
  platforms.append({'file':str(p.relative_to(ROOT)),
    'root_compatible':re.findall(r'^\s*compatible\s*=\s*"([^"]+)"',s,re.M)[:1],
    'production_platform_candidate':bool(re.fullmatch(r'cxd(?:\d+|90xxx)\.dtsi',p.name)),
    'cpu_compatibles':cpus,'cpu_nodes_in_file':len(cpus),
    'gic_compatibles':sorted(set(re.findall(r'"(arm,(?:gic|cortex-a\d+-gic)[^"]*)"',s))),
    'optee_node':'linaro,optee-tz' in s,'crypt_emmc_node':'crypt_emmc' in s,
    'evidence':fact(p,r'compatible\s*=\s*"(?:cxd,cxd|arm,cortex|arm,gic|linaro,optee|cxd,crypt_emmc)')})
 configs=[fact(p,r'CONFIG_(?:ARM64|NR_CPUS|TEE|OPTEE|CXD90\w+|ARCH_CXD|MMC_CRYPT)\b') for p in fs if 'defconfig' in p.name]
 result={'model':receipt['model'],'archive_url':receipt['url'],'archive_sha256':receipt['sha256'],
         'kernel_version':version,'kernel_version_evidence':fact(make,r'^(VERSION|PATCHLEVEL|SUBLEVEL)\s*=') if make else None,
         'published_platform_files':platforms,'published_configs':configs,
         'source_scope':'Model-associated published GPL source, not proof of selected shipping DTB/config or exact physical silicon.'}
 return result
if __name__=='__main__':
 results=[]
 for p in sorted((ROOT/'receipts').glob('*-kernel*.json')):
  r=json.loads(p.read_text());results.append(analyze(r))
 (ROOT/'source-analysis.json').write_text(json.dumps(results,indent=2)+'\n')
 for r in results:
  print(r['model'],r['kernel_version'],[(x['root_compatible'],x['cpu_compatibles'],x['gic_compatibles'],x['optee_node'],x['crypt_emmc_node']) for x in r['published_platform_files']])
