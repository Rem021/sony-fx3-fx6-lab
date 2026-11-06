"""Read public documents as data; verify a pinned repository diff, not a device."""
from pathlib import Path
from hashlib import sha1, sha256
import json, re
H=Path(__file__).resolve().parent;B=H.parent
def load(p):return json.loads(p.read_text())
def digest(p):return sha256(p.read_bytes()).hexdigest()
def put(n,v):
    with (H/n).open('x') as f:f.write(json.dumps(v,ensure_ascii=False,indent=2)+'\n')

fetch=load(H/'diff-fetch.json');assert fetch['returncode']==0
diff=(H/'qemu-new-commits.diff').read_bytes()
assert sha256(diff).hexdigest()==fetch['sha256']=='f411f466d092a94f2967eef412e5666302a8685c375e2e940d3599d4d7e6d32f'
rows=load(H/'documents-fetch.json');assert len(rows)==2
for r in rows:
    p=H/r['path'];assert r['returncode']==0 and p.stat().st_size==r['bytes'] and digest(p)==r['sha256']
old=(H/'old-QEMU_M2_PROGRESS.md').read_bytes();new=(H/'new-QEMU_M2_PROGRESS.md').read_bytes()
assert new.startswith(old)
suffix=new[len(old):]
lines=diff.decode().splitlines(keepends=True)
paths=[x.strip().split(' b/',1)[1] for x in lines if x.startswith('diff --git ')]
assert paths==['docs/QEMU_M2_PROGRESS.md']
assert len([x for x in lines if x.startswith('@@ ')])==1
added=''.join(x[1:] for x in lines if x.startswith('+') and not x.startswith('+++'))
assert added.encode()==suffix and len(suffix.splitlines())==764
assert not [x for x in lines if x.startswith('-') and not x.startswith('---')]
blobs={}
for name,data,expected in [('old',old,'2fc1718'),('new',new,'a659cfe')]:
    blob=sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()
    assert blob.startswith(expected);blobs[name]=blob
headings=[dict(line=i,text=s) for i,s in enumerate(new.decode().splitlines(),1)
          if i>len(old.splitlines()) and s.startswith('# ')]
assert len(headings)==12
for token in ['第一百零三层','第一百一十四层','帧仍 0','ZVE10_GPE_PACKET = 19','0x3e014d']:
    assert token in suffix.decode()
proof=[]
for token in ['内嵌 initramfs','像素全零','ZVE10_GPE_PACKET = 19','帧仍 0','backup 服务队列']:
    proof.append(dict(token=token,lines=[i for i,s in enumerate(new.decode().splitlines(),1)
                                       if i>len(old.splitlines()) and token in s]))
# Clarify the first capture's existing-file refusal without changing sealed240.
partial=B/'stage240-runtime-plan-and-anonymous-clone-bridge/public-reference/YuuLuo--a7c2-service-preload-README.md'
prior=B/'stage228-real-entrypoint-portability-audit/reference/a7c2--README.md'
assert partial.read_bytes()==prior.read_bytes()
assert digest(partial)=='3088b8667c21eca9bdda534e6719c0e5839c3f2d8085a39aef8ab98f58a5b7a1'
put('public-capture-clarification.json',dict(
    status='INITIAL_CAPTURE_FILE_EQUALS_PREVIOUSLY_PINNED_UNCHANGED_HEAD',
    current_capture=str(partial.relative_to(B)), prior_capture=str(prior.relative_to(B)),
    sha256=digest(partial), bytes=partial.stat().st_size,
    initial_network_attempt_completed_YuuLuo_then_failed_later=True,
    second_attempt_exclusive_create_refused_existing_file_not_download_content_error=True,
    no_sealed240_files_changed=True))
put('delta-audit.json',dict(
    status='PINNED_FULL_DIFF_VERIFIED_DOCUMENT_ONLY_NO_NEW_FX3_RECOVERY_IMPLEMENTATION',
    old_head=fetch['old_head'],new_head=fetch['new_head'],changed_paths=paths,
    added_lines=764,deleted_lines=0,old_lines=len(old.splitlines()),new_lines=len(new.splitlines()),
    git_blob_sha1=blobs,source_records=rows,headings=headings,scope_proof_lines=proof,
    delta_sha256=sha256(diff).hexdigest(),
    report_covers_ZVE10_and_ZV1M2_emulator_work_not_FX3=True,
    contains_documented_local_QEMU_code_snippets_but_no_repository_source_file_change=True,
    author_reports_19_startup_packets_but_zero_frames_and_backup_queue_block=True,
    emulator_or_hardware_recovery_reproduced_by_us=False,
    original_firmware_or_downloaded_code_executed=False,
    new_camera_USB_cache_admin_auth_upload_firmware_operations=0,
    actual_FX3_entry_backup_restore_and_MAIN_HEVC_gates_changed=False,
    first_flash_released=False))
print(json.dumps(dict(status='PASS',changed_paths=paths,added_lines=764,deleted_lines=0,new_FX3_recovery_code=False)))
