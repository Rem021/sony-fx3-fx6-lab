#!/usr/bin/env python3
"""Read-only verification of existing Sony OSS archives; HEAD only, no download."""
import base64,datetime,hashlib,json,re,tarfile,urllib.request
from pathlib import Path
root=Path('/Volumes/KAFU2T/AI/Projects/Mac/work')
items=[('FX3 Ver7.00',root/'fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/fx6-boot-readiness/early-kernel/sony-oss-fx3/linux-kernel.tar.gz','https://prodgpl.blob.core.windows.net/download/B2B/ILME-FX3_Ver.7.00/linux-kernel.tar.gz'),('FX6 V6.00 main',root/'fx3-vm-20261101/lead-claude/research/port-candidates/gpl-archives/FX6/linux-kernel.tar.gz','https://prodgpl.blob.core.windows.net/download/B2B/2026031201_ILME_FX6_V600/linux-kernel.tar.gz'),('FX6 V6.00 -u',root/'fx3-vm-20261101/lead-claude/research/port-candidates/gpl-archives/FX6/linux-kernel-u.tar.gz','https://prodgpl.blob.core.windows.net/download/B2B/2026031201_ILME_FX6_V600/linux-kernel-u.tar.gz')]
result={'checked_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'network_action':'HEAD only; no archive or firmware downloaded','archives':[]}
tokens=[b'osal_rcv_msg_tmo',b'u_osal_rcv_msg_tmo',b'osal_dynamic_id',b'osal_snd_msg']
selected=['drivers/udif/cdev.c','include/linux/udif/macros.h','include/linux/udif/wait.h','include/linux/udif/types.h','kernel/time/timer.c','COPYING']
for label,path,url in items:
 sha,md5=hashlib.sha256(),hashlib.md5()
 with path.open('rb') as f:
  while True:
   chunk=f.read(1024*1024)
   if not chunk:break
   sha.update(chunk);md5.update(chunk)
 row={'label':label,'local_path':str(path),'url':url,'bytes':path.stat().st_size,'sha256':sha.hexdigest(),'md5_base64':base64.b64encode(md5.digest()).decode(),'file_count':0,'source_files_scanned':0,'source_bytes_scanned':0,'osal_uipc_path_matches':[],'exact_symbol_matches':[],'selected_source_metadata':[]}
 try:
  with urllib.request.urlopen(urllib.request.Request(url,method='HEAD'),timeout=20) as response:
   row['remote']={k:response.headers.get(k) for k in ['Content-Length','Content-MD5','ETag','Last-Modified']};row['remote']['status']=response.status;row['remote']['final_url']=response.url
  row['local_matches_remote_length']=int(row['remote']['Content-Length'])==row['bytes'];row['local_matches_remote_md5']=row['remote']['Content-MD5']==row['md5_base64']
 except Exception as error:row['remote_error']=str(error)
 with tarfile.open(path,'r|gz') as archive:
  for member in archive:
   if not member.isfile():continue
   row['file_count']+=1
   if re.search(r'(?:^|/)(?:osal|uipc)(?:/|[._-])',member.name,re.I):row['osal_uipc_path_matches'].append(member.name)
   relevant=member.name.endswith(('.c','.h','.S','.txt')) or member.name.endswith(('Makefile','COPYING','Kconfig'))
   if not relevant:continue
   data=archive.extractfile(member).read();row['source_files_scanned']+=1;row['source_bytes_scanned']+=len(data)
   hits=[token.decode() for token in tokens if token in data]
   if hits:row['exact_symbol_matches'].append({'member':member.name,'tokens':hits})
   if member.name.endswith('/Makefile') and member.name.count('/')==1:row['top_makefile']={'member':member.name,'first_lines':data.decode(errors='replace').splitlines()[:5]}
   for suffix in selected:
    if member.name.endswith('/'+suffix):
     lines=data.decode(errors='replace').splitlines();row['selected_source_metadata'].append({'member':member.name,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),'line_count':len(lines),'sony_copyright_lines':[i for i,line in enumerate(lines,1) if 'Sony Corporation' in line],'focus_line_numbers':[i for i,line in enumerate(lines,1) if any(key in line for key in ['static long cdev_ioctl','warning ret =','tmo) * HZ','MAX_SCHEDULE_TIMEOUT','timeout < 0','UDIF_ERR_TIMEOUT'])]})
 result['archives'].append(row)
print(json.dumps(result,ensure_ascii=False,indent=2))
