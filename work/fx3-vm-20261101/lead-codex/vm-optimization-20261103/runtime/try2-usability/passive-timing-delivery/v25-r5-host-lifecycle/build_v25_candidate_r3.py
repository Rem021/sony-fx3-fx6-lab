#!/usr/bin/env python3
"""Guarded offline derivation from frozen r2; no QEMU operation."""
from pathlib import Path
import hashlib, importlib.util, json
HERE=Path(__file__).resolve().parent
PREV=HERE.parent/'v25-menu-osd-diagnostic'
BASE=PREV/'vmopt-20261104-v25-menu-osd-diagnostic-r2'
BUILDER=HERE.parent/'build_candidate.py'
OUTPUT=HERE/'vmopt-20261104-v25-menu-osd-diagnostic-r3'
MEMBER='simulation/fx3-osd-headless-v5.so'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
 if OUTPUT.exists():raise FileExistsError(OUTPUT)
 old=json.loads((BASE/'candidate.json').read_text())
 if sha(BASE/'candidate.json')!='c1467c2673b700b1988335694bcbf67dfb03c90c9acf486bc2b61c4b04867795':raise ValueError('r2 candidate changed')
 if sha(BUILDER)!='7245eca988c5a6f0dd7fc3e2ac178a6162af1411908b12c1849d067c7e256cb1':raise ValueError('builder changed')
 source=HERE/'src/fx3-osd-headless-v25-r3.c';so=HERE/'build/fx3-osd-headless-v25-r3.so'
 spec=importlib.util.spec_from_file_location('fx3_v4_cpio_builder',BUILDER);mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
 mod.OLD=BASE;mod.BUILD=HERE/'build';mod.NEW=OUTPUT
 mod.BASE_SHA=sha(BASE/'candidate.json')
 mod.REPLACEMENTS={MEMBER:(so.name,old['v25_diagnostic_contract']['new_member_sha256'],sha(so))}
 mod.main()
 manifest=OUTPUT/'candidate.json';candidate=json.loads(manifest.read_text())
 contract=dict(old['v25_diagnostic_contract'])
 contract.update({'base_candidate':str(BASE/'candidate.json'),'base_sha256':sha(BASE/'candidate.json'),
 'old_member_sha256':old['v25_diagnostic_contract']['new_member_sha256'],
 'new_member_sha256':sha(so),'source_sha256':sha(source),
 'changed_members':candidate['passive_timing_contract']['changed_members'],
 'diagnostic_version':2,'diagnostic_busy_drops_header_word':5,
 'multiwriter_policy':'single trylock, count busy drop, never wait or call original under lock',
 'runtime_validated':False})
 candidate['passive_timing_contract']=old['passive_timing_contract']
 candidate['v25_diagnostic_contract']=contract
 manifest.write_text(json.dumps(candidate,indent=2)+'\n')
 receipt=json.loads((OUTPUT/'build-receipt.json').read_text())
 receipt.update({'candidate_sha256':sha(manifest),'source_sha256':sha(source),
 'so_sha256':sha(so),'builder_sha256':sha(BUILDER),'QEMU_started':False,'guest_validated':False})
 (OUTPUT/'build-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
 print(json.dumps({'candidate':str(manifest),'candidate_sha256':sha(manifest),
 'cpio_sha256':receipt['initrd_sha256'],'dtb_sha256':receipt['dtb_sha256'],
 'changed_members':receipt['changed_members']},indent=2))
if __name__=='__main__':main()
