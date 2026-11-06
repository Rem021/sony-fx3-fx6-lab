#!/usr/bin/env python3
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
import json
import os
import plistlib
import shutil
import subprocess

ROOT = Path("/Volumes/KAFU2T/AI/Projects/Mac")
WORK = ROOT / "work/sony-firmware-20261024"
STAGE276 = WORK / "stage276-fixed-host-cleanup03-plan"
STAGE279 = WORK / "stage279-fixed-service-access-communication04"
STAGE280 = WORK / "stage280-service-access-communication04-execution"
STAGE281 = WORK / "stage281-fixed-host-cleanup04-plan"


def file_sha256(p: Path) -> str:
    return sha256(p.read_bytes()).hexdigest()


def c_hex_bytes(hex_digest: str) -> str:
    b = bytes.fromhex(hex_digest)
    return ",".join(f"0x{x:02x}" for x in b)


def main():
    vol = plistlib.loads(subprocess.check_output(["/usr/sbin/diskutil", "info", "-plist", "/Volumes/KAFU2T"]))
    assert vol["VolumeUUID"] == "F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B"

    # 1. Record physical-disconnect.json in stage280
    phys_disc = {
        "recorded_utc": datetime.now(timezone.utc).isoformat(),
        "user_statement": "现在就在显示选择USB连接模式那个菜单。然后拔下USB，菜单和拍摄都一切正常。现在断开了",
        "screen_before_unplug": "显示选择USB连接模式菜单（对应STOP后重枚举的054C:096F USB Bus-powered Device）",
        "all_camera_side_USB_physically_disconnected_user_confirmed": True,
        "remain_disconnected": True,
        "battery_shooting_UI_and_menu_normal_user_confirmed": True,
        "sony_current_cache_nodes": [],
        "cached_metadata_only": True,
        "active_USB_requests": 0,
    }
    (STAGE280 / "physical-disconnect.json").write_text(
        json.dumps(phys_disc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    # 2. Prepare Stage 281 directory
    STAGE281.mkdir(mode=0o700, parents=True, exist_ok=True)
    art = STAGE281 / "artifacts"
    art.mkdir(mode=0o755, exist_ok=True)

    # Copy bound_signal.c and bound_signal.h byte-for-byte from Stage 276
    shutil.copy2(STAGE276 / "bound_signal.c", STAGE281 / "bound_signal.c")
    shutil.copy2(STAGE276 / "bound_signal.h", STAGE281 / "bound_signal.h")

    helper_sha = "32ad51d0d111b0318f28d6e92fe0df5d0c018f256683ad35624043a8f476150c"
    assert file_sha256(STAGE279 / "artifacts/service-native-helper") == helper_sha
    python_path = Path("/Library/Frameworks/Python.framework/Versions/3.14/Resources/Python.app/Contents/MacOS/Python")
    observer_sha = file_sha256(python_path)

    cleanup_target_h = f"""#ifndef FX3_FIXED_HOST_CLEANUP_TARGET_H
#define FX3_FIXED_HOST_CLEANUP_TARGET_H
#include "bound_signal.h"
#define FX3_CLEANUP_ROOT "/private/var/root/fx3-host-cleanup-20261101-04"
#define FX3_CLEANUP_SELF FX3_CLEANUP_ROOT "/helper"
#define FX3_OLD_GUARD "/private/var/root/fx3-owner-trials/global-fx3-owner.journal"
static const fx3_host_identity helper_identity={{37860,0,1793546568ull,487337ull,"/private/var/root/fx3-owner-trials/fx3-702-service-access-communication-20261101-04/helper"}};
static const unsigned char helper_image_hash[32]={{{c_hex_bytes(helper_sha)}}};
static const fx3_host_identity observer_identity={{36633,501,1793546063ull,372013ull,"/Library/Frameworks/Python.framework/Versions/3.14/Resources/Python.app/Contents/MacOS/Python"}};
static const unsigned char observer_image_hash[32]={{{c_hex_bytes(observer_sha)}}};
#endif
"""
    (STAGE281 / "cleanup_target.h").write_text(cleanup_target_h, encoding="utf-8")

    cleanup_c = """/* Fixed host-only cleanup for communication 04. No USB, IOKit, camera, driver or firmware API.
 * Executes only after distinct approval and user-confirmed physical removal. */
#include "cleanup_target.h"
#include <CommonCrypto/CommonDigest.h>
#include <errno.h>
#include <fcntl.h>
#include <signal.h>
#include <stdio.h>
#include <string.h>
#include <sys/mount.h>
#include <sys/stat.h>
#include <time.h>
#include <unistd.h>
static uint32_t u32(const unsigned char *p){return (uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24;}
static uint64_t u64(const unsigned char *p){return u32(p)|((uint64_t)u32(p+4)<<32);}
static int unchanged(const struct stat *a,const struct stat *b){
    return a->st_dev==b->st_dev && a->st_ino==b->st_ino && a->st_size==b->st_size &&
        a->st_mtimespec.tv_sec==b->st_mtimespec.tv_sec && a->st_mtimespec.tv_nsec==b->st_mtimespec.tv_nsec &&
        a->st_ctimespec.tv_sec==b->st_ctimespec.tv_sec && a->st_ctimespec.tv_nsec==b->st_ctimespec.tv_nsec;
}
static int hash_file(const char *path,unsigned char digest[32],struct stat *identity,unsigned char *tail){
    int fd=open(path,O_RDONLY|O_NOFOLLOW|O_CLOEXEC|O_NONBLOCK);if(fd<0)return -1;
    struct stat before,after;struct statfs fs;int ok=0;
    if(fstat(fd,&before) || !S_ISREG(before.st_mode) || before.st_nlink!=1 ||
       before.st_uid!=0 || before.st_size<=0 || before.st_size>8*1024*1024 ||
       fstatfs(fd,&fs) || (fs.f_flags&MNT_IGNORE_OWNERSHIP))goto end;
    CC_SHA256_CTX ctx;CC_SHA256_Init(&ctx);unsigned char block[4096];off_t at=0;
    while(at<before.st_size){
        size_t n=(size_t)(before.st_size-at);if(n>sizeof(block))n=sizeof(block);
        if(pread(fd,block,n,at)!=(ssize_t)n)goto end;
        CC_SHA256_Update(&ctx,block,(CC_LONG)n);at+=(off_t)n;
    }
    if(tail && (before.st_size%256 || before.st_size>2048*256 ||
       pread(fd,tail,256,before.st_size-256)!=256))goto end;
    if(fstat(fd,&after) || !unchanged(&before,&after))goto end;
    CC_SHA256_Final(digest,&ctx);*identity=before;ok=1;
end:close(fd);return ok?0:-1;
}
static int image(const fx3_host_identity *e,const unsigned char expected[32]){
    unsigned char digest[32];struct stat identity;
    return !hash_file(e->path,digest,&identity,NULL) && !memcmp(digest,expected,32);
}
static int gone(const fx3_host_identity *e){
    for(unsigned i=0;i<200;i++){
        int state=fx3_host_same_process(e);if(state==0)return 1;if(state<0)return -1;
        struct timespec wait={0,10000000};nanosleep(&wait,NULL);
    }return 0;
}
static int record(int directory,const char *text){
    int fd=openat(directory,"result.json",O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW|O_CLOEXEC,0400);
    if(fd<0)return -1;size_t n=strlen(text);
    int ok=write(fd,text,n)==(ssize_t)n && !fsync(fd);if(close(fd))ok=0;return ok?0:-1;
}
int main(int argc,char **argv){
    if(geteuid()!=0){fputs("FX3_HOST_CLEANUP_DENIED:root_required\\n",stderr);return 77;}
    if(argc!=2 || strcmp(argv[1],"--confirmed-camera-USB-physically-disconnected"))return 64;
    char self[PROC_PIDPATHINFO_MAXSIZE]={0};struct stat directory_stat,self_stat;
    if(proc_pidpath(getpid(),self,sizeof(self))<=0 || strcmp(self,FX3_CLEANUP_SELF) ||
       lstat(self,&self_stat) || !S_ISREG(self_stat.st_mode) || self_stat.st_uid ||
       self_stat.st_nlink!=1 || (self_stat.st_mode&07777)!=0500)return 65;
    int directory=open(FX3_CLEANUP_ROOT,O_RDONLY|O_DIRECTORY|O_NOFOLLOW|O_CLOEXEC);if(directory<0)return 65;
    struct statfs fs;
    if(fstat(directory,&directory_stat) || directory_stat.st_uid || (directory_stat.st_mode&07777)!=0700 ||
       fstatfs(directory,&fs) || (fs.f_flags&MNT_IGNORE_OWNERSHIP)){close(directory);return 65;}
    int once=openat(directory,"entry.once",O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW|O_CLOEXEC,0400);
    if(once<0){close(directory);return 67;}
    const char mark[]="host-only cleanup; fixed PIDs; no camera actions; no retry\\n";
    int consumed=write(once,mark,sizeof(mark)-1)==sizeof(mark)-1 && !fsync(once);close(once);
    if(!consumed){close(directory);return 68;}
    audit_token_t helper={0},observer={0};
    unsigned char guard_before[32]={0},guard_after[32]={0},tail[256]={0};struct stat gb,ga;
    int helper_signal=0,helper_absent=0,observer_signal=0,observer_absent=0,guard_same=0,error=0;
    const char *status="DENIED_BEFORE_SIGNALS";
    int initial_observer=fx3_host_same_process(&observer_identity);
    if(!image(&helper_identity,helper_image_hash) || !image(&observer_identity,observer_image_hash) ||
       fx3_host_capture_token(&helper_identity,&helper) || initial_observer<0 ||
       (initial_observer==1 && fx3_host_capture_token(&observer_identity,&observer))){
        error=errno;goto finish;
    }
    if(hash_file(FX3_OLD_GUARD,guard_before,&gb,tail) || (gb.st_mode&07777)!=0600 ||
       memcmp(tail,"FX3-GUARD-v1",12) || u32(tail+20)!=1 || u32(tail+28)!=(uint32_t)helper_identity.pid ||
       u32(tail+32)!=helper_identity.uid || u64(tail+40)!=helper_identity.sec || u64(tail+48)!=helper_identity.usec){
        error=EINVAL;goto finish;
    }
    /* This explicit forced host termination is a distinct exception to 279's
     * no-kill policy. It is never issued to a PID without its audit version. */
    if(fx3_host_same_process(&helper_identity)!=1 || fx3_host_signal_token(&helper,SIGKILL)){
        error=errno;goto finish;
    }
    helper_signal=SIGKILL;helper_absent=gone(&helper_identity);
    if(helper_absent!=1){status="UNKNOWN_HELPER_EXIT";error=errno;goto finish;}
    status="HELPER_GONE_OBSERVER_UNRESOLVED";
    int observed=fx3_host_same_process(&observer_identity);
    if(observed==1){
        if(initial_observer!=1 || fx3_host_signal_token(&observer,SIGTERM)){error=errno;goto finish;}
        observer_signal=SIGTERM;observer_absent=gone(&observer_identity);
    }else observer_absent=observed==0?1:-1;
    if(observer_absent!=1){error=errno;goto finish;}
    if(hash_file(FX3_OLD_GUARD,guard_after,&ga,NULL) || !unchanged(&gb,&ga) || memcmp(guard_before,guard_after,32)){
        status="HOST_PROCESSES_GONE_GUARD_CHECK_UNKNOWN";error=errno;goto finish;
    }
    guard_same=1;status="HOST_CLEANUP_ONLY_OLD_TRIAL_STILL_UNKNOWN";
finish:;
    char text[1200];int n=snprintf(text,sizeof(text),
        "{\\"status\\":\\"%s\\",\\"helper_PID\\":%d,\\"helper_signal\\":%d,\\"helper_absent\\":%d,\\"observer_PID\\":%d,\\"observer_signal\\":%d,\\"observer_absent\\":%d,\\"old_guard_bytes_unchanged\\":%s,\\"old_trial_COMPLETE\\":false,\\"new_trial_authorized\\":false,\\"USB_requests\\":0,\\"firmware_writes\\":0,\\"automatic_retry\\":false,\\"error\\":%d}\\n",
        status,helper_identity.pid,helper_signal,helper_absent,observer_identity.pid,observer_signal,observer_absent,guard_same?"true":"false",error);
    int logged=n>0 && (size_t)n<sizeof(text) && !record(directory,text);
    if(n>0 && (size_t)n<sizeof(text)){fputs(text,stdout);fflush(stdout);}close(directory);
    return helper_absent==1 && observer_absent==1 && guard_same && logged?0:69;
}
"""
    (STAGE281 / "cleanup.c").write_text(cleanup_c, encoding="utf-8")

    out_bin = art / "fixed-host-cleanup"
    compile_argv = [
        "/usr/bin/xcrun",
        "clang",
        "-std=c11",
        "-O1",
        "-g",
        "-Wall",
        "-Wextra",
        "-Werror",
        "-Wno-deprecated-declarations",
        str(STAGE281 / "bound_signal.c"),
        str(STAGE281 / "cleanup.c"),
        "-o",
        str(out_bin),
    ]
    comp = subprocess.run(compile_argv, capture_output=True, text=True, check=True)
    prog_sha = file_sha256(out_bin)

    deps = subprocess.check_output(["/usr/bin/otool", "-L", str(out_bin)], text=True)
    undef = subprocess.check_output(["/usr/bin/nm", "-u", str(out_bin)], text=True)
    ord_run = subprocess.run([str(out_bin)], capture_output=True, text=True)
    assert ord_run.returncode == 77
    assert ord_run.stderr == "FX3_HOST_CLEANUP_DENIED:root_required\n"

    root_boot = f"""set -euC
cd /
umask 077
[ "$(/usr/bin/id -u)" = 0 ] || exit 77
[ ! -e /private/var/root/fx3-host-cleanup-20261101-04 ] && [ ! -L /private/var/root/fx3-host-cleanup-20261101-04 ] || exit 78
/bin/mkdir -m 700 /private/var/root/fx3-host-cleanup-20261101-04
/usr/bin/install -m 500 /private/tmp/fx3-host-cleanup-20261101-04/source-helper /private/var/root/fx3-host-cleanup-20261101-04/helper
cleanup_digest=$(/usr/bin/shasum -a 256 /private/var/root/fx3-host-cleanup-20261101-04/helper)
[ "$cleanup_digest" = '{prog_sha}  /private/var/root/fx3-host-cleanup-20261101-04/helper' ] || exit 78
exec /private/var/root/fx3-host-cleanup-20261101-04/helper --confirmed-camera-USB-physically-disconnected
"""
    (STAGE281 / "root-bootstrap-reviewed.sh").write_text(root_boot, encoding="utf-8")

    host_cmd = f"""#!/bin/sh
set -euC
cd /
umask 077
cleanup_digest=$(/usr/bin/shasum -a 256 /private/tmp/fx3-host-cleanup-20261101-04/source-helper)
[ "$cleanup_digest" = '{prog_sha}  /private/tmp/fx3-host-cleanup-20261101-04/source-helper' ] || exit 78
: > /private/tmp/fx3-host-cleanup-20261101-04/launch.once
cleanup_status=0
/usr/bin/sudo -- /bin/sh -c 'set -euC
cd /
umask 077
[ "$(/usr/bin/id -u)" = 0 ] || exit 77
[ ! -e /private/var/root/fx3-host-cleanup-20261101-04 ] && [ ! -L /private/var/root/fx3-host-cleanup-20261101-04 ] || exit 78
/bin/mkdir -m 700 /private/var/root/fx3-host-cleanup-20261101-04
/usr/bin/install -m 500 /private/tmp/fx3-host-cleanup-20261101-04/source-helper /private/var/root/fx3-host-cleanup-20261101-04/helper
cleanup_digest=$(/usr/bin/shasum -a 256 /private/var/root/fx3-host-cleanup-20261101-04/helper)
[ "$cleanup_digest" = '"'"{prog_sha}  /private/var/root/fx3-host-cleanup-20261101-04/helper'"'" ] || exit 78
exec /private/var/root/fx3-host-cleanup-20261101-04/helper --confirmed-camera-USB-physically-disconnected
' > /private/tmp/fx3-host-cleanup-20261101-04/root-stdout.log 2> /private/tmp/fx3-host-cleanup-20261101-04/root-stderr.log || cleanup_status=$?
/usr/bin/printf '{{"launcher_exit":%s,"new_camera_trial":false}}\\n' "$cleanup_status" > /private/tmp/fx3-host-cleanup-20261101-04/launcher-result.json
exit "$cleanup_status"
"""
    (STAGE281 / "HostCleanup.command").write_text(host_cmd, encoding="utf-8")

    fixed_plan = {
        "grant_id": "fx3-host-cleanup-20261101-04",
        "maximum_root_program_invocations": 1,
        "authorized": False,
        "physical_precondition": "all camera-side USB data cables physically unplugged and remain unplugged; healthy battery UI/menu confirmed",
        "helper_identity": {
            "uid": 0,
            "pid": 37860,
            "sec": 1793546568,
            "usec": 487337,
            "path": "/private/var/root/fx3-owner-trials/fx3-702-service-access-communication-20261101-04/helper",
            "image_sha256": "",
        },
        "helper_image_sha256": helper_sha,
        "helper_signal": "SIGKILL(9) once with exact kernel audit PID/version",
        "observer_identity": {
            "uid": 501,
            "pid": 36633,
            "sec": 1793546063,
            "usec": 372013,
            "path": "/Library/Frameworks/Python.framework/Versions/3.14/Resources/Python.app/Contents/MacOS/Python",
            "image_sha256": observer_sha,
        },
        "observer_image_sha256": observer_sha,
        "observer_signal": "SIGTERM(15) once only after helper confirmed gone if still alive; if already exited (observed==0), record observer_absent=1 without signaling",
        "no_PID_only_signal_fallback": True,
        "root_program_sha256": prog_sha,
        "job": "/private/tmp/fx3-host-cleanup-20261101-04",
        "root_private_directory": "/private/var/root/fx3-host-cleanup-20261101-04",
        "root_guard_read_only": "/private/var/root/fx3-owner-trials/global-fx3-owner.journal",
        "global_guard_not_modified": True,
        "original_trial_stays_UNKNOWN": True,
        "USB_or_camera_commands": 0,
        "firmware_write": False,
        "privacy_permission_changes": False,
        "automatic_retry": False,
        "Terminal_opened": False,
        "admin_verification_requested": False,
        "new_trial_authorized": False,
        "source_actual_runtime_review": str(STAGE280 / "actual-runtime-review.json"),
        "source_physical_disconnect": str(STAGE280 / "physical-disconnect.json"),
    }
    (STAGE281 / "fixed-plan.json").write_text(
        json.dumps(fixed_plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    build_check = {
        "recorded_utc": datetime.now(timezone.utc).isoformat(),
        "compile_argv": compile_argv,
        "compile_returncode": comp.returncode,
        "compile_stderr": comp.stderr,
        "program_sha256": prog_sha,
        "dependencies": deps,
        "undefined_symbols": undef,
        "ordinary_UID": os.getuid(),
        "ordinary_run_return": ord_run.returncode,
        "ordinary_stderr": ord_run.stderr,
        "ordinary_run_denied_before_target_access": True,
        "unchanged_token_core": {
            "bound_signal.c": file_sha256(STAGE281 / "bound_signal.c") == file_sha256(STAGE276 / "bound_signal.c"),
            "bound_signal.h": file_sha256(STAGE281 / "bound_signal.h") == file_sha256(STAGE276 / "bound_signal.h"),
        },
        "observer_already_exited_supported": True,
        "prior_validation_receipts": [
            {
                "path": str(STAGE276 / "runs/execution01/actual-host-cleanup.json"),
                "sha256": file_sha256(STAGE276 / "runs/execution01/actual-host-cleanup.json"),
            }
        ],
        "new_admin_or_USB_operations": 0,
        "signals_to_existing_helper_or_observer": 0,
    }
    (STAGE281 / "build-and-check.json").write_text(
        json.dumps(build_check, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    readme_text = f"""# 通信04保留主机实例的单次收尾方案（`fx3-host-cleanup-20261101-04`）

本方案只处理 Mac 上的通信04保留根助手 `PID 37860`（出生时间 `1793546568.487337`）与观察器 `PID 36633`（出生时间 `1793546063.372013`，已自行退出）。**已编译并核对，尚未批准、暂存或启动。** 用户已确认拔下 USB 前相机显示“选择USB连接模式”菜单（对应 `STOP` 后重枚举的 `054C:096F` `USB Bus-powered Device`），拔下全部 USB 线后纯电池供电下拍摄界面和菜单一切正常；独立缓存核对当前无任何 Sony USB 节点（`sony_candidates_count = 0`）。整个收尾期间保持 USB 断开，本程序不调用任何 USB/IOKit 接口。

## 固定操作与范围

- **授权标识（Grant ID）**：`fx3-host-cleanup-20261101-04`
- **最大管理员调用次数**：`1`（必要时在 Terminal 完成一次 `sudo` / Touch ID 验证）
- **绑定目标**：
  1. 原根助手：`UID 0`、`PID 37860`、出生时间 `1793546568.487337`、路径 `/private/var/root/fx3-owner-trials/fx3-702-service-access-communication-20261101-04/helper`、映像 SHA256 `{helper_sha}`。
  2. 原观察器：`UID 501`、`PID 36633`、出生时间 `1793546063.372013`、Python 路径与映像 SHA256 `{observer_sha}`（当前已退出，`fx3_host_same_process == 0`，程序仅核对并记录 `observer_absent = 1, observer_signal = 0`，不向已退出或复用的 PID 发送任何信号）。
- **执行动作**：
  1. 只用 `task_name_for_pid` 读取原根助手的内核 `audit_token_t` 并核对 PID 版本与路径。
  2. 只读核对 `/private/var/root/fx3-owner-trials/global-fx3-owner.journal` 尾部确属 `PID 37860`（`1793546568.487337`）。
  3. 仅向匹配的 `PID 37860` audit token 发送一次 `SIGKILL(9)` 并等待其退出（最多约 2 秒）。
  4. 复核 `PID 36633` 已退出（`observer_absent == 1`）且根日志字节与摘要完全未变，写出 `/private/var/root/fx3-host-cleanup-20261101-04/result.json`。
- **实际清理程序 SHA256**：`{prog_sha}`
- **固定文件**：[`fixed-plan.json`](file:///Volumes/KAFU2T/AI/Projects/Mac/work/sony-firmware-20261024/stage281-fixed-host-cleanup04-plan/fixed-plan.json) · [`build-and-check.json`](file:///Volumes/KAFU2T/AI/Projects/Mac/work/sony-firmware-20261024/stage281-fixed-host-cleanup04-plan/build-and-check.json) · [`approval-bundle.json`](file:///Volumes/KAFU2T/AI/Projects/Mac/work/sony-firmware-20261024/stage281-fixed-host-cleanup04-plan/approval-bundle.json)
"""
    (STAGE281 / "README.md").write_text(readme_text, encoding="utf-8")

    bundle_rel_paths = [
        "HostCleanup.command",
        "README.md",
        "artifacts/fixed-host-cleanup",
        "artifacts/fixed-host-cleanup.dSYM/Contents/Info.plist",
        "artifacts/fixed-host-cleanup.dSYM/Contents/Resources/DWARF/fixed-host-cleanup",
        "artifacts/fixed-host-cleanup.dSYM/Contents/Resources/Relocations/aarch64/fixed-host-cleanup.yml",
        "bound_signal.c",
        "bound_signal.h",
        "build-and-check.json",
        "cleanup.c",
        "cleanup_target.h",
        "fixed-plan.json",
        "root-bootstrap-reviewed.sh",
    ]
    bundle_files = []
    for rp in bundle_rel_paths:
        fp = STAGE281 / rp
        bundle_files.append({
            "path": rp,
            "bytes": fp.stat().st_size,
            "sha256": file_sha256(fp),
        })

    approval_bundle = {
        "schema": 1,
        "grant_id": "fx3-host-cleanup-20261101-04",
        "maximum_root_program_invocations": 1,
        "scope": "HOST_ONLY_FIXED_AUDIT_TOKEN_CLEANUP_AFTER_PHYSICAL_CAMERA_DISCONNECT",
        "helper_PID": 37860,
        "helper_signal": 9,
        "observer_PID": 36633,
        "observer_signal": 15,
        "USB_requests": 0,
        "firmware_write": False,
        "old_journal_write": False,
        "automatic_retry": False,
        "files": bundle_files,
    }
    (STAGE281 / "approval-bundle.json").write_text(
        json.dumps(approval_bundle, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    bundle_sha = file_sha256(STAGE281 / "approval-bundle.json")

    manifest_files = sorted(
        bundle_files + [{
            "path": "approval-bundle.json",
            "bytes": (STAGE281 / "approval-bundle.json").stat().st_size,
            "sha256": bundle_sha,
        }],
        key=lambda x: x["path"],
    )
    final_manifest = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "files": manifest_files,
        "self_excluded": True,
        "approved": False,
        "staged": False,
        "root_or_USB_operations": 0,
    }
    (STAGE281 / "final-manifest.json").write_text(
        json.dumps(final_manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    print(json.dumps({
        "grant_id": "fx3-host-cleanup-20261101-04",
        "program_sha256": prog_sha,
        "approval_bundle_sha256": bundle_sha,
        "final_manifest_sha256": file_sha256(STAGE281 / "final-manifest.json"),
    }, indent=2))


if __name__ == "__main__":
    main()
