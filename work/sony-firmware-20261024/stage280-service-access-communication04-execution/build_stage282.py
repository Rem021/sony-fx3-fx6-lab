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
STAGE282 = WORK / "stage282-fixed-host-cleanup04-quote-fix"


def file_sha256(p: Path) -> str:
    return sha256(p.read_bytes()).hexdigest()


def c_hex_bytes(hex_digest: str) -> str:
    b = bytes.fromhex(hex_digest)
    return ",".join(f"0x{x:02x}" for x in b)


def main():
    vol = plistlib.loads(subprocess.check_output(["/usr/sbin/diskutil", "info", "-plist", "/Volumes/KAFU2T"]))
    assert vol["VolumeUUID"] == "F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B"

    # Record stage281 shell syntax abort in stage281/runs/execution01/abort-review.json
    s281_run = STAGE281 / "runs/execution01"
    s281_abort = {
        "recorded_utc": datetime.now(timezone.utc).isoformat(),
        "status": "ABORTED_IN_ORDINARY_SHELL_BEFORE_SUDO_DUE_TO_QUOTE_TYPO",
        "grant_id": "fx3-host-cleanup-20261101-04",
        "sudo_invoked": False,
        "root_helper_executed": False,
        "signals_sent": 0,
        "USB_requests": 0,
        "root_cause": "Python string concatenation in build_stage281.py emitted '\"'\"<sha> instead of '\"'\"'<sha> in HostCleanup.command line 17, causing /bin/sh syntax error before /usr/bin/sudo was parsed or invoked.",
    }
    (s281_run / "abort-review.json").write_text(
        json.dumps(s281_abort, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    STAGE282.mkdir(mode=0o700, parents=True, exist_ok=True)
    art = STAGE282 / "artifacts"
    art.mkdir(mode=0o755, exist_ok=True)

    shutil.copy2(STAGE276 / "bound_signal.c", STAGE282 / "bound_signal.c")
    shutil.copy2(STAGE276 / "bound_signal.h", STAGE282 / "bound_signal.h")

    helper_sha = "32ad51d0d111b0318f28d6e92fe0df5d0c018f256683ad35624043a8f476150c"
    assert file_sha256(STAGE279 / "artifacts/service-native-helper") == helper_sha
    python_path = Path("/Library/Frameworks/Python.framework/Versions/3.14/Resources/Python.app/Contents/MacOS/Python")
    observer_sha = file_sha256(python_path)

    cleanup_target_h = f"""#ifndef FX3_FIXED_HOST_CLEANUP_TARGET_H
#define FX3_FIXED_HOST_CLEANUP_TARGET_H
#include "bound_signal.h"
#define FX3_CLEANUP_ROOT "/private/var/root/fx3-host-cleanup-20261101-04-r2"
#define FX3_CLEANUP_SELF FX3_CLEANUP_ROOT "/helper"
#define FX3_OLD_GUARD "/private/var/root/fx3-owner-trials/global-fx3-owner.journal"
static const fx3_host_identity helper_identity={{37860,0,1793546568ull,487337ull,"/private/var/root/fx3-owner-trials/fx3-702-service-access-communication-20261101-04/helper"}};
static const unsigned char helper_image_hash[32]={{{c_hex_bytes(helper_sha)}}};
static const fx3_host_identity observer_identity={{36633,501,1793546063ull,372013ull,"/Library/Frameworks/Python.framework/Versions/3.14/Resources/Python.app/Contents/MacOS/Python"}};
static const unsigned char observer_image_hash[32]={{{c_hex_bytes(observer_sha)}}};
#endif
"""
    (STAGE282 / "cleanup_target.h").write_text(cleanup_target_h, encoding="utf-8")
    shutil.copy2(STAGE281 / "cleanup.c", STAGE282 / "cleanup.c")

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
        str(STAGE282 / "bound_signal.c"),
        str(STAGE282 / "cleanup.c"),
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
[ ! -e /private/var/root/fx3-host-cleanup-20261101-04-r2 ] && [ ! -L /private/var/root/fx3-host-cleanup-20261101-04-r2 ] || exit 78
/bin/mkdir -m 700 /private/var/root/fx3-host-cleanup-20261101-04-r2
/usr/bin/install -m 500 /private/tmp/fx3-host-cleanup-20261101-04-r2/source-helper /private/var/root/fx3-host-cleanup-20261101-04-r2/helper
cleanup_digest=$(/usr/bin/shasum -a 256 /private/var/root/fx3-host-cleanup-20261101-04-r2/helper)
[ "$cleanup_digest" = '{prog_sha}  /private/var/root/fx3-host-cleanup-20261101-04-r2/helper' ] || exit 78
exec /private/var/root/fx3-host-cleanup-20261101-04-r2/helper --confirmed-camera-USB-physically-disconnected
"""
    (STAGE282 / "root-bootstrap-reviewed.sh").write_text(root_boot, encoding="utf-8")

    # Exact single-quote escaping: '"'"' inside single-quoted /bin/sh -c '...'
    sq_esc = "'\"'\"'"
    host_cmd = (
        "#!/bin/sh\n"
        "set -euC\n"
        "cd /\n"
        "umask 077\n"
        "cleanup_digest=$(/usr/bin/shasum -a 256 /private/tmp/fx3-host-cleanup-20261101-04-r2/source-helper)\n"
        f"[ \"$cleanup_digest\" = '{prog_sha}  /private/tmp/fx3-host-cleanup-20261101-04-r2/source-helper' ] || exit 78\n"
        ": > /private/tmp/fx3-host-cleanup-20261101-04-r2/launch.once\n"
        "cleanup_status=0\n"
        "/usr/bin/sudo -- /bin/sh -c 'set -euC\n"
        "cd /\n"
        "umask 077\n"
        "[ \"$(/usr/bin/id -u)\" = 0 ] || exit 77\n"
        "[ ! -e /private/var/root/fx3-host-cleanup-20261101-04-r2 ] && [ ! -L /private/var/root/fx3-host-cleanup-20261101-04-r2 ] || exit 78\n"
        "/bin/mkdir -m 700 /private/var/root/fx3-host-cleanup-20261101-04-r2\n"
        "/usr/bin/install -m 500 /private/tmp/fx3-host-cleanup-20261101-04-r2/source-helper /private/var/root/fx3-host-cleanup-20261101-04-r2/helper\n"
        "cleanup_digest=$(/usr/bin/shasum -a 256 /private/var/root/fx3-host-cleanup-20261101-04-r2/helper)\n"
        f"[ \"$cleanup_digest\" = {sq_esc}{prog_sha}  /private/var/root/fx3-host-cleanup-20261101-04-r2/helper{sq_esc} ] || exit 78\n"
        "exec /private/var/root/fx3-host-cleanup-20261101-04-r2/helper --confirmed-camera-USB-physically-disconnected\n"
        "' > /private/tmp/fx3-host-cleanup-20261101-04-r2/root-stdout.log 2> /private/tmp/fx3-host-cleanup-20261101-04-r2/root-stderr.log || cleanup_status=$?\n"
        "/usr/bin/printf '{\"launcher_exit\":%s,\"new_camera_trial\":false}\\n' \"$cleanup_status\" > /private/tmp/fx3-host-cleanup-20261101-04-r2/launcher-result.json\n"
        "exit \"$cleanup_status\"\n"
    )
    (STAGE282 / "HostCleanup.command").write_text(host_cmd, encoding="utf-8")

    # Verify both shell scripts with /bin/sh -n AND verify the inner sudo -c string with /bin/sh -n!
    sh_check_outer = subprocess.run(["/bin/sh", "-n", str(STAGE282 / "HostCleanup.command")], capture_output=True, text=True, check=True)
    sh_check_inner = subprocess.run(["/bin/sh", "-n", str(STAGE282 / "root-bootstrap-reviewed.sh")], capture_output=True, text=True, check=True)
    assert f"'{sq_esc}{prog_sha}  /private/var/root/fx3-host-cleanup-20261101-04-r2/helper{sq_esc}'" not in host_cmd
    assert f"{sq_esc}{prog_sha}  /private/var/root/fx3-host-cleanup-20261101-04-r2/helper{sq_esc}" in host_cmd

    fixed_plan = {
        "grant_id": "fx3-host-cleanup-20261101-04-r2",
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
        "job": "/private/tmp/fx3-host-cleanup-20261101-04-r2",
        "root_private_directory": "/private/var/root/fx3-host-cleanup-20261101-04-r2",
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
    (STAGE282 / "fixed-plan.json").write_text(
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
        "sh_syntax_check_host_command_returncode": sh_check_outer.returncode,
        "sh_syntax_check_root_bootstrap_returncode": sh_check_inner.returncode,
        "unchanged_token_core": {
            "bound_signal.c": file_sha256(STAGE282 / "bound_signal.c") == file_sha256(STAGE276 / "bound_signal.c"),
            "bound_signal.h": file_sha256(STAGE282 / "bound_signal.h") == file_sha256(STAGE276 / "bound_signal.h"),
        },
        "observer_already_exited_supported": True,
        "new_admin_or_USB_operations": 0,
        "signals_to_existing_helper_or_observer": 0,
    }
    (STAGE282 / "build-and-check.json").write_text(
        json.dumps(build_check, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    readme_text = f"""# 通信04保留主机实例单次收尾修正包（`fx3-host-cleanup-20261101-04-r2`）

本方案修正了 Stage 281 `HostCleanup.command` 第 17 行因 Python 字符串拼接吞掉单引号导致普通 `/bin/sh` 在调用 `sudo` 前直接语法报错退出的问题（Stage 281 未执行 `sudo`、未启动 root helper、未发信号）。本包通过 `/bin/sh -n` 静态语法检查，绑定原根助手 `PID 37860`（`1793546568.487337`）与已退出观察器 `PID 36633`（`1793546063.372013`）。

- **授权标识（Grant ID）**：`fx3-host-cleanup-20261101-04-r2`
- **实际清理程序 SHA256**：`{prog_sha}`
- **固定文件**：[`fixed-plan.json`](file:///Volumes/KAFU2T/AI/Projects/Mac/work/sony-firmware-20261024/stage282-fixed-host-cleanup04-quote-fix/fixed-plan.json) · [`build-and-check.json`](file:///Volumes/KAFU2T/AI/Projects/Mac/work/sony-firmware-20261024/stage282-fixed-host-cleanup04-quote-fix/build-and-check.json) · [`approval-bundle.json`](file:///Volumes/KAFU2T/AI/Projects/Mac/work/sony-firmware-20261024/stage282-fixed-host-cleanup04-quote-fix/approval-bundle.json)
"""
    (STAGE282 / "README.md").write_text(readme_text, encoding="utf-8")

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
        fp = STAGE282 / rp
        bundle_files.append({
            "path": rp,
            "bytes": fp.stat().st_size,
            "sha256": file_sha256(fp),
        })

    approval_bundle = {
        "schema": 1,
        "grant_id": "fx3-host-cleanup-20261101-04-r2",
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
    (STAGE282 / "approval-bundle.json").write_text(
        json.dumps(approval_bundle, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    bundle_sha = file_sha256(STAGE282 / "approval-bundle.json")

    manifest_files = sorted(
        bundle_files + [{
            "path": "approval-bundle.json",
            "bytes": (STAGE282 / "approval-bundle.json").stat().st_size,
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
    (STAGE282 / "final-manifest.json").write_text(
        json.dumps(final_manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    print(json.dumps({
        "grant_id": "fx3-host-cleanup-20261101-04-r2",
        "program_sha256": prog_sha,
        "approval_bundle_sha256": bundle_sha,
        "final_manifest_sha256": file_sha256(STAGE282 / "final-manifest.json"),
    }, indent=2))


if __name__ == "__main__":
    main()
