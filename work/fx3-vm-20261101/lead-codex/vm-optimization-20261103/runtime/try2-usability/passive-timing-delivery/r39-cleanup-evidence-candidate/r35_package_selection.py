"""Fixed r36 selector/identity checks only. No launch, QMP, browser or logging."""
from pathlib import Path
import hashlib,json
HOST=Path(__file__).resolve().parent
DEL=HOST.parent
APPROVED_HOST=Path('/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/lead-codex/vm-optimization-20261103/runtime/try2-usability/passive-timing-delivery/r39-cleanup-evidence-candidate')
PACKAGE=DEL/'r36-fixed-slot-package'
CANDIDATE_SHA='0bf214178ab8e60d1ac7755e1d1b2fcc0d2c325ff8473abd50402f09ab81fab4'
CPIO_SHA='49c1e110475fa15b692a3bf79fdf15189b82929cc7d643e27cd5f2d383d77fff'
CPIO_BYTES=453213884
PROFILE='r35-diagnostic-r36-n64-r39'
LABEL='v35diag-n64-r36-r39'
PINS={'r30-startup-observation-candidate/SHA256SUMS':'e04a86e60d0b311d57df50a6060064f6f57e02a33d3c04c015922e6a37749a49','r30-startup-observation-candidate/SOURCE-FREEZE.json':'10265a99fd1a74dc23d85477c82f078485863b92ed664e12132e0a9cf41ce717','r30-startup-observation-candidate/CORE-SOURCE-FREEZE.json':'3591a3fcbb79c2b1617ba47f4fa4de5b79f2057f717198393e433156f69dc5e9','r35-existing-log-observation-candidate/SHA256SUMS':'c7aee1bf7a35320e3c8d08eec03214957832008197741feb971433f19c524a71','r35-existing-log-observation-candidate/SOURCE-FREEZE.json':'dd4f8a2045220a045c32b8a0a686227f08e4e8c2edc7adca8964a12ddedc66e4','r36-fixed-slot-package/SHA256SUMS':'9a06c51caa6bc3517bedb9db06a72452fe4a12156ed3838034821caf151ecf03'}
PINS.update({'r37-diagnostic-runner-candidate/SHA256SUMS':'ede0cfdc07066faf00d98e6934e5125dc10d598f8e228d8364ca0cf6fab1155c','r37-diagnostic-runner-candidate/SOURCE-FREEZE.json':'861b26c5aefbe393a5e58e1015914e517f0bb9e928c6f5e572a9f56816084ca9','r37-diagnostic-runner-candidate/CORE-SOURCE-FREEZE.json':'7752a6fd7cdb74def7a3cfa9659ed6a1a4f6ab23708a5aaaed5f345e7c46f303'})
def sha(p):
 with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def exact_regular(path):
 p=Path(path)
 if not p.is_absolute() or not p.is_file() or any(x.is_symlink() for x in [p,*p.parents]) or p.resolve()!=p:raise ValueError('r39 regular exact path required: '+str(p))
 return p
def output_root(path):
 p=Path(path)
 if HOST!=APPROVED_HOST or not p.is_absolute() or p.parent!=HOST/'run-inputs' or any(x.is_symlink() for x in [p,*p.parents]) or p.resolve()!=p:raise ValueError('r39 exclusive run-inputs boundary required')
 return p
def options(ns):
 if ns.r35_diagnostic_package and (not ns.snapshot_tail or ns.gate_publish_interval!=64 or ns.review_procdiag_r4e or ns.internal_hoststep):raise ValueError('r35 package requires snapshot-tail/N64; procdiag/N1/internal forbidden')
def verify_package(run_dir):
 output_root(run_dir)
 groups={}
 for rel,h in PINS.items():
  p=exact_regular(DEL/rel)
  if sha(p)!=h:raise ValueError('r39 frozen input identity changed: '+rel)
  groups[rel]=h
 p=exact_regular(PACKAGE/'candidate.json')
 if sha(p)!=CANDIDATE_SHA:raise ValueError('r36 manifest identity changed')
 c=json.loads(p.read_text());initrd=exact_regular(c['initrd']['path'])
 if initrd!=PACKAGE/'guest.cpio' or c['initrd']['sha256']!=CPIO_SHA or initrd.stat().st_size!=CPIO_BYTES or sha(initrd)!=CPIO_SHA:raise ValueError('r36 CPIO path/size/hash changed')
 dtb=exact_regular(c['dtb']['path']);expected_dtb=DEL/'v25-menu-osd-diagnostic-r3/vmopt-20261104-v25-menu-osd-diagnostic-r3/guest.dtb'
 if dtb!=expected_dtb or c['dtb']['sha256']!='5aa2beacb0b0e1f5b83f4589f9bba8b148cd73f87b6058e0f648e05c5347855b' or sha(dtb)!=c['dtb']['sha256']:raise ValueError('fixed DTB changed')
 if c['memory_mib']!=5120 or c['initrd_load_address']!='0x440000000':raise ValueError('fixed platform profile changed')
 return {'profile':PROFILE,'package_root':str(PACKAGE),'candidate':str(p),'candidate_sha256':CANDIDATE_SHA,'initrd':str(initrd),'initrd_sha256':CPIO_SHA,'initrd_bytes':CPIO_BYTES,'load_address':'0x440000000','dtb':str(dtb),'dtb_sha256':c['dtb']['sha256'],'label':LABEL,'provenance_manifest_pins':groups,'scope':'selection only; no VM authority; original runner admission still required'}
