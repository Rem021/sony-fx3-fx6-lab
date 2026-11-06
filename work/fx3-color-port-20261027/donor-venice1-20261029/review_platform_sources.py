#!/usr/bin/env python3
"""Pin nearby kernel interfaces and distinguish them from private ISP/loaders."""
import hashlib,json,re,tarfile
from pathlib import Path
HERE=Path(__file__).resolve().parent
SELECTIONS={
 'linux-2.6.29-patched-armv7a.tar.gz':[
  ('kernel/arch/arm/mach-emxx/switch/switch-vup.c',r'SWITCH_VUP_ADDR_VUPCTRL|if_switch_ver_up'),
  ('kernel/arch/arm/mach-emxx/phyadr/phyadr.c',r'mmap|remap|pgprot|ioctl'),
  ('kernel/arch/arm/mach-emxx/csi/csi_datalink.c',r'spi1_csi_fdx_rw')],
 'linux-2.6.29-patched-arm.tar.gz':[
  ('kernel/arch/arm/mach-cxd9225gg/highmem/memoryDriver.c',r'kernel_virt_to_phys|kernel_phys_to_virt|pgprot_noncached')],
}
def main():
    target=HERE/'platform-source-review.json';assert not target.exists()
    reviews=json.loads((HERE/'OSS-kernel-review.json').read_text())['reviews'];out=[]
    for archive,wanted in SELECTIONS.items():
        path=HERE/'OSS'/archive;expected=next(r['sha256'] for r in reviews if Path(r['file']).name==archive)
        assert hashlib.sha256(path.read_bytes()).hexdigest()==expected
        select=dict(wanted);seen=set()
        with tarfile.open(path,'r|gz') as tar:
            for member in tar:
                if member.name not in select:continue
                assert member.isfile() and member.size<100000
                stream=tar.extractfile(member);b=stream.read(member.size+1);assert len(b)==member.size
                label='armv7a' if 'armv7a' in archive else 'arm'
                output=HERE/'selected-source'/label/member.name.removeprefix('kernel/')
                output.parent.mkdir(parents=True,exist_ok=True);assert not output.exists();output.write_bytes(b)
                lines=b.decode('utf-8',errors='replace').splitlines()
                hits=[dict(line=i,text=line) for i,line in enumerate(lines,1) if re.search(select[member.name],line)]
                assert hits
                out.append(dict(archive=archive,archive_sha256=expected,original_member=member.name,bytes=len(b),
                    sha256=hashlib.sha256(b).hexdigest(),output=str(output.relative_to(HERE)),relevant_lines=hits));seen.add(member.name)
        assert seen==set(select)
    result=dict(sources=out,interpretations=[
        'memoryDriver exposes reserved-memory address translation and noncached user mapping; source presence alone does not identify installed SoC, DRAM chip or normal RAW pipeline.',
        'The named CSI datalink calls spi1_csi_fdx_rw and uses GPIO handshaking; these files do not establish a CMOS RAW acquisition path.',
        'switch-vup supplies peripheral/version-update register operations; it is not a recovered DATA23213 type3/type4 package decrypter.',
        'No listed interface supplies the private full ISP, complete professional menus or FX3 firmware admission.'],
        source_builds_or_native_executions=0,device_actions=0,goal_complete=False)
    target.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(selected_source_files=len(out),private_firmware_loader_or_whole_ISP_recovered=False,device_actions=0)))
if __name__=='__main__':main()
