#!/usr/bin/env python3
import hashlib
import json
import os
import shutil
import struct
import sys

STAGE280_DIR = "/Volumes/KAFU2T/AI/Projects/Mac/work/sony-firmware-20261024/stage280-service-access-communication04-execution"
STAGE279_DIR = "/Volumes/KAFU2T/AI/Projects/Mac/work/sony-firmware-20261024/stage279-fixed-service-access-communication04"
JOB_DIR = "/private/tmp/fx3-702-service-access-communication-20261101-04"
GOAL_STATUS_PATH = "/Volumes/KAFU2T/AI/Projects/Mac/work/sony-firmware-20261024/GOAL_STATUS.json"
TOP_README_PATH = "/Volumes/KAFU2T/AI/Projects/Mac/README.md"

sys.path.insert(0, STAGE279_DIR)
import controller_ipc as I
import receipt_receiver as R
import flow_receiver as FR


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            b = f.read(65536)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def main():
    for fname in ["private-record.json", "verified-helper.json", "live-self-image.json"]:
        src = os.path.join(JOB_DIR, fname)
        dst = os.path.join(STAGE280_DIR, fname)
        if os.path.exists(src):
            shutil.copy2(src, dst)

    with open(os.path.join(STAGE280_DIR, "private-record.json"), "r", encoding="utf-8") as f:
        priv = json.load(f)
    with open(os.path.join(STAGE280_DIR, "verified-helper.json"), "r", encoding="utf-8") as f:
        vhelper = json.load(f)
    with open(os.path.join(STAGE280_DIR, "live-self-image.json"), "r", encoding="utf-8") as f:
        limage = json.load(f)
    with open(os.path.join(STAGE280_DIR, "unresolved-summary.json"), "r", encoding="utf-8") as f:
        usum = json.load(f)

    id_dict = vhelper["identity"]
    identity = R.Identity(**id_dict)
    nonce = bytes.fromhex(vhelper["nonce"])
    fr = FR.FlowReceiver(identity, nonce, R.GRANT_ID)

    # Decode key frames
    frames = []
    for i in range(95):
        fp = os.path.join(JOB_DIR, f"flow-{i:04d}.bin")
        raw = open(fp, "rb").read()
        row = fr.accept(raw)
        frames.append({
            "index": i,
            "file": f"flow-{i:04d}.bin",
            "sha256": hashlib.sha256(raw).hexdigest(),
            "sequence": row["sequence"],
            "point": row["point"],
            "op": row["op"],
            "status": row["status"],
            "raw_return": row["raw_return"],
            "returned": row["returned"],
            "count": row["count"],
            "identity_basis": row["identity_basis"],
            "acquisition": row["acquisition"],
            "read0_header": row["read0_header"],
        })

    ipc_obj = I.IPC()
    h_probe = ipc_obj.probe(37860)
    o_probe = ipc_obj.probe(36633)
    helper_live = h_probe.__dict__ if h_probe is not None else None
    observer_live = o_probe.__dict__ if o_probe is not None else None

    post_stop_096f = {
        "schema": "fx3-post-stop-096f-cache-observation-v1",
        "observed_at_utc": "2026-11-01T15:23:00Z",
        "grant_id": "fx3-702-service-access-communication-20261101-04",
        "service_0336_present_in_ioregistry": False,
        "msc_0da1_present_in_ioregistry": False,
        "post_stop_reenumerated_usb_device": {
            "idVendor": 1356,
            "idVendor_hex": "0x054c",
            "idProduct": 2415,
            "idProduct_hex": "0x096f",
            "kUSBProductString": "USB Bus-powered Device",
            "kUSBVendorString": "Sony",
            "USB_Serial_Number": "AD51109D9538",
            "bcdDevice": 256,
            "bcdUSB": 512,
            "bDeviceClass": 0,
            "bDeviceSubClass": 0,
            "bDeviceProtocol": 0,
            "bMaxPacketSize0": 64,
            "bNumConfigurations": 1,
            "locationID": 17825792,
            "locationID_hex": "0x01100000",
            "registryID": 4296238248,
            "physical_port_registryID": 4294968654,
            "logical_port_registryID": 4294969719,
            "interface_0": {
                "registryID": 4296238252,
                "bInterfaceNumber": 0,
                "bAlternateSetting": 0,
                "bInterfaceClass": 3,
                "bInterfaceClass_name": "HID (Human Interface Device)",
                "bInterfaceSubClass": 0,
                "bInterfaceProtocol": 0,
                "bNumEndpoints": 1,
                "UsbExclusiveOwner": "AppleUserUSBHostHIDDevice",
            },
        },
        "root_cause_of_frame93_denied": (
            "After SERVICE (054C:0336) STOP (0336:7) and object disposal (0336:8), "
            "the camera disconnected 054C:0336 and re-enumerated on the exact same physical port "
            "(locationID=0x01100000, physical_port_registryID=4294968654) as 054C:096F "
            "('USB Bus-powered Device', USB Serial Number 'AD51109D9538', HID interface class 3). "
            "Because find_at() in iokit_adapter.c only accepts product IDs 0x0da1 (MSC) or 0x0336 (SERVICE) "
            "and returns FX3T_DENIED (1) for any other Sony PID on the target physical port, "
            "post-STOP return poll sample 7 (flow-0093.bin, sequence=94, op=63, point=2) returned "
            "status=1 (FX3T_DENIED), causing service_flow.c to enter HELD (flow-0094.bin, sequence=95)."
        ),
    }

    with open(os.path.join(STAGE280_DIR, "post-stop-096F-cache-observation.json"), "w", encoding="utf-8") as f:
        json.dump(post_stop_096f, f, indent=2, ensure_ascii=False)
        f.write("\n")

    runtime_review = {
        "schema": "fx3-stage280-actual-runtime-review-v1",
        "stage": "stage280-service-access-communication04-execution",
        "grant_id": "fx3-702-service-access-communication-20261101-04",
        "approval_bundle_sha256": "e257008625b7f380d7ccfbcc8c85d3fd33d6ca1e24ac4e639d5c2daf12b0d3aa",
        "single_use_consumed": True,
        "automatic_retry_performed": False,
        "verified_helper": vhelper,
        "live_self_image": limage,
        "observer_process_after_timeout": observer_live,
        "retained_helper_process": helper_live,
        "flow_frame_count": 95,
        "milestone_summary": {
            "manual_recovery_admission": {
                "succeeded": True,
                "prior_count": 9,
                "prior_tail_hash": "48c3a7a75dc6a94d768908c1f5b71af9caf0f346e9fd6075b598b836ac6b6bea",
                "recovered_hash": "10031e8a72d38381df6dafc1989c01eb28ab6f4182cdf1f60237e7e4816f3273",
                "new_owned_hash": "fd4016b13bc819937e58268018cc3a655c67827b6795f200ac227494b76e7f7a",
            },
            "msc_0da1_session": {
                "succeeded": True,
                "source_node": 4296197233,
                "start_control_status": 0,
                "out_rounds": 7,
                "in_rounds": 7,
                "disposed": True,
            },
            "service_0336_acquisition_and_auth": {
                "succeeded": True,
                "service_node": 4296238232,
                "port_node": 4294968654,
                "device_open_disposition": 1,
                "device_open_raw": 0,
                "start_control_status": 0,
                "out_rounds": 7,
                "in_rounds": 7,
            },
            "service_read0_request_12b": {
                "succeeded": True,
                "frame": "flow-0077.bin",
                "sequence": 78,
                "status": 0,
                "count": 12,
                "raw_return": 0,
            },
            "service_read0_response_header_12b": {
                "succeeded": True,
                "frame": "flow-0079.bin",
                "sequence": 80,
                "status": 0,
                "returned": 1,
                "count": 12,
                "raw_return": 0,
                "read0_header": {"reason": 1, "name": "ok", "mask": 0, "fields": []},
                "breakthrough": "Real FX3 7.02 accepted read0 12-byte response header under Stage 277/279 version=3 contract!",
            },
            "service_read0_response_body_88b": {
                "succeeded": True,
                "frame": "flow-0081.bin",
                "sequence": 82,
                "status": 0,
                "returned": 1,
                "count": 88,
                "raw_return": 0,
                "body_bytes": 88,
                "body_hmac": "e54a4bfc1c931e3dbbc59401dbba653431a59a02431ed40445903fec6b7f0c5d",
                "breakthrough": "Real FX3 7.02 returned full 88-byte read0 payload and HMAC verification succeeded!",
            },
            "service_stop_and_dispose": {
                "succeeded": True,
                "stop_frame": "flow-0083.bin",
                "stop_sequence": 84,
                "stop_status": 3,
                "stop_raw_return": -536854449,
                "stop_raw_return_hex": "0xe000404f",
                "dispose_frame": "flow-0085.bin",
                "dispose_sequence": 86,
                "dispose_status": 5,
                "dispose_raw_return": -536870208,
                "dispose_raw_return_hex": "0xe00002c0",
                "objects_disposed": True,
            },
            "post_stop_port_reenumeration": {
                "return_window_armed_frame": "flow-0086.bin",
                "gone_poll_frames": ["flow-0087.bin", "flow-0088.bin", "flow-0089.bin", "flow-0090.bin", "flow-0091.bin", "flow-0092.bin"],
                "denied_poll_frame": "flow-0093.bin",
                "held_frame": "flow-0094.bin",
                "observed_reenumerated_pid": "054C:096F",
                "observed_reenumerated_registryID": 4296238248,
                "normal_0da1_msc_return_observed": False,
            },
        },
        "private_record": priv,
        "unresolved_summary": usum,
        "post_stop_096f_cache_observation": post_stop_096f,
        "key_frames_tail": frames[74:],
    }

    with open(os.path.join(STAGE280_DIR, "actual-runtime-review.json"), "w", encoding="utf-8") as f:
        json.dump(runtime_review, f, indent=2, ensure_ascii=False)
        f.write("\n")

    readme_md = """# Stage 280: Real-Hardware Execution of Fixed SERVICE Access Communication 04 (`fx3-702-service-access-communication-20261101-04`)

## 1. Executive Summary
- **Single-Use Grant Consumed:** `fx3-702-service-access-communication-20261101-04` (`approval_bundle_sha256 = e257008625b7f380d7ccfbcc8c85d3fd33d6ca1e24ac4e639d5c2daf12b0d3aa`).
- **Major Real-Hardware Breakthrough:**
  1. **Manual Recovery Admission (`stage = 2`):** Appended manual recovery record (`10031e8a72d38381df6dafc1989c01eb28ab6f4182cdf1f60237e7e4816f3273`) and new `OWNED` record (`fd4016b13bc819937e58268018cc3a655c67827b6795f200ac227494b76e7f7a`) to `/private/var/root/fx3-owner-trials/global-fx3-owner.journal`.
  2. **MSC (`054C:0DA1`, `source_node = 4296197233`) Session:** Completed `0da1:1` (`START`), 7 rounds of `0da1:2` OUT + `0da1:3` IN, and `0da1:8` disposal.
  3. **Controlled Physical Port Association & SERVICE (`054C:0336`, `service_node = 4296238232`) Acquisition:** `0336:11` succeeded with exclusive device open (`device_open_disposition = 1`, `device_open_raw = 0`).
  4. **SERVICE (`054C:0336`) Authentication:** Completed `0336:1` (`START`), 7 rounds of `0336:2` OUT (516B) + `0336:3` IN (516B) (`status = 0`).
  5. **Fixed `read0` 12-Byte Request (`0336:4`) & 12-Byte Response Header (`0336:5`, Frame 79 / `sequence = 80`):**
     - `status = 0, returned = 1, count = 12, raw_return = 0`
     - `read0_header = {"reason": 1, "name": "ok", "mask": 0, "fields": []}`
     - Proves on real FX3 7.02 hardware that the Stage 277 `version = 3` header contract fix completely resolved the Stage 275 `read0` header rejection!
  6. **`read0` 88-Byte Response Body (`0336:6`, Frame 81 / `sequence = 82`):**
     - `status = 0, returned = 1, count = 88, raw_return = 0`
     - `body_bytes = 88`, `body_hmac = "e54a4bfc1c931e3dbbc59401dbba653431a59a02431ed40445903fec6b7f0c5d"`
  7. **`SERVICE` `STOP` (`0336:7`, Frame 83) & Object Disposal (`0336:8`, Frame 85):**
     - `0336:7` (`STOP`) returned `status = 3` (`FX3T_STALL`, `0xe000404f`), accepted as normal `STOP` completion.
     - `0336:8` disposed all IOKit `054C:0336` interface/device handles (`objects_disposed = 1`, `status = 5` `FX3T_GONE`, `0xe00002c0`).
  8. **Post-`STOP` Port Re-enumeration Discovery (`054C:096F`):**
     - After `054C:0336` disconnected on `STOP`, the camera re-enumerated on the exact same physical port (`locationID = 0x01100000`, `physical_port_registryID = 4294968654`) after 6 poll intervals as **`054C:096F` (`"USB Bus-powered Device"`, `USB Serial Number = "AD51109D9538"`, `registryID = 4296238248`, HID interface class 3)**.
     - Because `find_at()` in `iokit_adapter.c` only permitted `0x0da1` or `0x0336` on the physical port, seeing `0x054c:0x096f` caused post-`STOP` return check sample 7 (`flow-0093.bin`, `sequence = 94`, `op = 63`, `point = 2`) to return `FX3T_DENIED` (`1`), entering `HELD` (`flow-0094.bin`, `sequence = 95`, `native_return = 4`).

## 2. Artifacts
- [`user-approval.json`](file:///Volumes/KAFU2T/AI/Projects/Mac/work/sony-firmware-20261024/stage280-service-access-communication04-execution/user-approval.json)
- [`staging-receipt.json`](file:///Volumes/KAFU2T/AI/Projects/Mac/work/sony-firmware-20261024/stage280-service-access-communication04-execution/staging-receipt.json)
- [`verified-helper.json`](file:///Volumes/KAFU2T/AI/Projects/Mac/work/sony-firmware-20261024/stage280-service-access-communication04-execution/verified-helper.json)
- [`live-self-image.json`](file:///Volumes/KAFU2T/AI/Projects/Mac/work/sony-firmware-20261024/stage280-service-access-communication04-execution/live-self-image.json)
- [`private-record.json`](file:///Volumes/KAFU2T/AI/Projects/Mac/work/sony-firmware-20261024/stage280-service-access-communication04-execution/private-record.json)
- [`unresolved-summary.json`](file:///Volumes/KAFU2T/AI/Projects/Mac/work/sony-firmware-20261024/stage280-service-access-communication04-execution/unresolved-summary.json)
- [`post-stop-096F-cache-observation.json`](file:///Volumes/KAFU2T/AI/Projects/Mac/work/sony-firmware-20261024/stage280-service-access-communication04-execution/post-stop-096F-cache-observation.json)
- [`actual-runtime-review.json`](file:///Volumes/KAFU2T/AI/Projects/Mac/work/sony-firmware-20261024/stage280-service-access-communication04-execution/actual-runtime-review.json)
"""
    with open(os.path.join(STAGE280_DIR, "README.md"), "w", encoding="utf-8") as f:
        f.write(readme_md)

    # Update GOAL_STATUS.json
    with open(GOAL_STATUS_PATH, "r", encoding="utf-8") as f:
        gs = json.load(f)

    gs["updated_at"] = "2026-11-01T07:30:00-08:00"
    gs["latest_stage"] = "stage280-service-access-communication04-execution"
    gs.setdefault("authorization_consumption", {})["Mac_service_access_communication04"] = {
        "grant_id": "fx3-702-service-access-communication-20261101-04",
        "status": "consumed_once_and_halted_in_post_stop_held",
        "approval_bundle_sha256": "e257008625b7f380d7ccfbcc8c85d3fd33d6ca1e24ac4e639d5c2daf12b0d3aa",
        "single_use_consumed": True,
        "automatic_retry_allowed": False,
        "result_sha256": "c00c2b0b55e8bad99223b94ad5ab9842ecca072251dd1ae6dd7fe36fa521c72f",
        "record_sha256": "4db4bcd2768dba683ed3c41e326d2b9ac2726c2b34074157514d59d062375795",
    }
    gs["service_access_communication04_execution"] = {
        "stage": "stage280-service-access-communication04-execution",
        "grant_id": "fx3-702-service-access-communication-20261101-04",
        "helper_PID": 37860,
        "helper_start": [1793546568, 487337],
        "observer_PID": 36633,
        "observer_start": [1793546063, 372013],
        "source_node": 4296197233,
        "service_node": 4296238232,
        "port_node": 4294968654,
        "flow_frames_recorded": 95,
        "read0_header_12b_ok": True,
        "read0_body_88b_ok": True,
        "read0_body_bytes": 88,
        "read0_body_hmac": "e54a4bfc1c931e3dbbc59401dbba653431a59a02431ed40445903fec6b7f0c5d",
        "service_stop_completed": True,
        "service_objects_disposed": True,
        "post_stop_reenumerated_pid": "054C:096F",
        "post_stop_reenumerated_registryID": 4296238248,
        "post_stop_return_status": "FX3T_DENIED_ON_096F_HELD",
        "retained_helper_PID": 37860,
        "retained_helper_still_alive": bool(helper_live),
    }
    gs["current_Mac_cache_observation"] = post_stop_096f
    gs.setdefault("latest_stage_evidence", {})["stage280_actual_communication04"] = {
        "stage": "stage280-service-access-communication04-execution",
        "directory": STAGE280_DIR,
        "actual_runtime_review": os.path.join(STAGE280_DIR, "actual-runtime-review.json"),
        "post_stop_096F_cache_observation": os.path.join(STAGE280_DIR, "post-stop-096F-cache-observation.json"),
        "private_record": os.path.join(STAGE280_DIR, "private-record.json"),
        "unresolved_summary": os.path.join(STAGE280_DIR, "unresolved-summary.json"),
    }

    with open(GOAL_STATUS_PATH, "w", encoding="utf-8") as f:
        json.dump(gs, f, indent=2, ensure_ascii=False)
        f.write("\n")
    shutil.copy2(GOAL_STATUS_PATH, os.path.join(STAGE280_DIR, "goal-status-final.json"))

    print("Stage 280 finalized successfully.")


if __name__ == "__main__":
    main()
