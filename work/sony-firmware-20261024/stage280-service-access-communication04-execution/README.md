# Stage 280: Real-Hardware Execution of Fixed SERVICE Access Communication 04 (`fx3-702-service-access-communication-20261101-04`)

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
