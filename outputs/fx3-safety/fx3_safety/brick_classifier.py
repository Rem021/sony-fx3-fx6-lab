"""Deterministic FX3 Brick Taxonomy Classifier, Recovery Path Selector,
and 4-Layer Fail-Safe Overlay / Watchdog Hook Generator.

Incorporates both internal byte-level reverse engineering (FX3 7.02 / FX6 6.01)
and 2024-2026 Bionz XR (CXD90057 'Mira' + CXD90058 'Cetus', SY-1114 mainboard)
community & service findings (Multi-Terminal 1.8V UART BootROM 48000-baud RP2040
injection -> 18d1:4ee0 Fastboot, blink codes 5L6S / 7L7S / 6L, WF-12 Wi-Fi module
self-test bricks, and /etc/ld.so.preload dynamic busybox brick traps).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional


@dataclass(frozen=True)
class BrickDiagnosis:
    level: str  # LEVEL_0 .. LEVEL_4
    severity: str  # LOW, MEDIUM, HIGH, CRITICAL_HARDWARE
    title: str
    root_cause_summary: str
    software_usb_or_sd_recoverable: bool
    disassembly_free_uart_bootrom_recoverable: bool
    hardware_programmer_required: bool
    active_boot_chain_status: str
    primary_recovery_steps: List[str]
    fallback_recovery_steps: List[str]
    critical_warnings: List[str]


def classify_brick_state(
    *,
    led_symptom: str = "normal",
    usb_vid_pid: str = "none",
    display_state: str = "black",
    corrupted_regions: Optional[List[str]] = None,
    updater_mode_armed: bool = False,
    oneshot_overlay_used: bool = False,
    has_full_body_backup: bool = False,
) -> BrickDiagnosis:
    """Classify an FX3 failure / brick state and return the exact recovery protocol.

    Parameters
    ----------
    led_symptom:
        One of:
        - "normal"
        - "red_steady" (Stuck in /setting/updater/mode* or early userland hang)
        - "red_5L_6S" or "red_5_blinks" (5 Long + 6/7 Short: BODYDATA.DAT read/version/model mismatch)
        - "red_7L_7S" or "red_7_blinks" (7 Long + 7 Short: Interrupted update recovery loop in p1/loader)
        - "red_6L" (6 Long Blinks: Sub-component / WF-12 Wi-Fi or CP NOR post-write verification fault)
        - "no_led_dead" (Octal-SPI NOR / PMIC / PoP hardware fault)
    usb_vid_pid:
        One of:
        - "054C:0DA1" / "054C:0DA3" / "054C:0994" (Normal MSC / PTP / Charging)
        - "054C:0336" (Authenticated USB Service / Senser / Jiritsu Mode)
        - "054C:03E2" / "054C:096F" (USB Firmware Updater `sauu` / Post-Stop Service Residue)
        - "18D1:4EE0" (Google Fastboot v0.5 via Multi-Terminal 1.8V UART BootROM SRAM injection)
        - "none"
    display_state:
        One of: "normal_ui", "update_progress_or_error", "black", "boot_logo_freeze"
    corrupted_regions:
        Optional list of affected storage regions, e.g. ["p5_wbi"], ["p15_usr"], ["p10_preload"],
        ["p7_rootfs"], ["p3_system"], ["p2_backup"], ["p1_updater"], ["sector0"], ["spi_nor"]
    updater_mode_armed:
        True if p2:/setting/updater/mode (+ mode5/mode6) was armed before the fault.
    oneshot_overlay_used:
        True if modifications were applied via Layer-1/2 bind-mount + clear-before-exec token.
    has_full_body_backup:
        True if a verified same-body backup (Sector 0, p1, p2, p6, p18, NOR ddrtraining.dat) exists.
    """
    regions = set(corrupted_regions or [])

    # 0. Check if 5L+6S or 7L+7S SD Update Recovery Loop is active (when SPI NOR & Sector 0 are NOT explicitly destroyed)
    if led_symptom in ("red_5L_6S", "red_7L_7S") and "spi_nor" not in regions and "sector0" not in regions:
        is_5l6s = led_symptom == "red_5L_6S"
        return BrickDiagnosis(
            level="LEVEL_2_UPDATER_BLINK_LOOP_SD_RECOVERABLE",
            severity="MEDIUM",
            title=(
                "Level 2 Updater Blink Loop (5 Long + 6/7 Short — File/Version/Model Reject)"
                if is_5l6s
                else "Level 2 Updater Blink Loop (7 Long + 7 Short — Interrupted Update / Waiting for Slot 1)"
            ),
            root_cause_summary=(
                "Camera is alive inside the p1 (/dev/nflasha1) or loader update state machine with `/setting/updater/mode*` active. "
                + (
                    "5 Long + 6/7 Short blinks indicate `sdfileinput.elf` rejected `/BODYDATA.DAT` at Gate 1 (isVersionOK @ 0x9fd4, "
                    "e.g. skipped stepping-stone v2.04/v2.05 or same-version without mode6), Gate 2 (isModelOK @ 0xa004, e.g. ILME-FX3 "
                    "0x91030080 vs ILME-FX3A mismatch), or Gate 4 (VerifySignature @ 0xabf0 / truncated Creator's App transfer)."
                    if is_5l6s
                    else "7 Long + 7 Short blinks indicate a prior update was interrupted before `complete()` cleared `/setting/updater/mode*`, "
                    "and the recovery loader cannot find a readable, valid `/BODYDATA.DAT` in SD Slot 1."
                )
            ),
            software_usb_or_sd_recoverable=True,
            disassembly_free_uart_bootrom_recoverable=True,
            hardware_programmer_required=False,
            active_boot_chain_status="Bootloader -> p1 Updater Active (Polling SD Slot 1 for /BODYDATA.DAT)",
            primary_recovery_steps=[
                "1. Turn power switch OFF, remove NP-FZ100 battery and all memory cards/cables.",
                "2. Switch power to ON and hold the Shutter button for 30-60 seconds to discharge PMIC rails, then switch OFF.",
                "3. Take a standard 32GB or 64GB UHS-I SDHC/SDXC card (avoid CFexpress Type A or UHS-II V90 during recovery) and perform a full format (FAT32 or exFAT) on PC/Mac.",
                "4. Copy an intact, verified official `BODYDATA.DAT` (check exact byte size and SHA-256; verify ILME-FX3 vs ILME-FX3A; if body was < v2.04, test stepping-stone v2.04/v2.05 first) to `/BODYDATA.DAT` at card root.",
                "5. Insert the card into Slot 1 (leave Slot 2 empty), insert a 100% charged genuine Sony NP-FZ100 battery, and wait 15-20 minutes for the blink pattern to transition to normal `1 -> 3 -> 5` progress.",
            ],
            fallback_recovery_steps=[
                "If USB enumerates as 054C:0336 (Service) or 054C:03E2 (USB Updater): write `/setting/updater/mode6` (`sauu -s` verskip) or clear `/setting/updater/mode*` to return to normal boot."
            ],
            critical_warnings=[
                "Never use Sony Creators' App over Wi-Fi/BLE or an unregulated dummy battery for recovery flashing."
            ],
        )

    # 1. Check for Tier-0 / SPOF Hardware Brick (SPI NOR, Sector 0, 6 Long Blinks, or Dead Power)
    if (
        "spi_nor" in regions
        or "sector0" in regions
        or led_symptom in ("red_5_blinks", "red_7_blinks", "red_6L", "no_led_dead")
    ):
        cause_parts: List[str] = []
        if "spi_nor" in regions or led_symptom == "no_led_dead":
            cause_parts.append(
                "Octal-SPI NOR (infomisc.dat EXBL @ Sector 0, DGU.bin @ Sector 4, LdrBkup.bin @ Sector 68, "
                "loader_nor.bin @ Sector 72, MIS.bin+ddrtraining.dat @ Sector 512, or cpapp-b.bin @ Sector 4096) "
                "is corrupted or SY-1114 PMIC power rail failed."
            )
        if "sector0" in regions or led_symptom == "red_5_blinks":
            cause_parts.append(
                "eMMC UDA Sector 0 ('8246' '2.00' 30-partition table) or eMMC hardware initialization failed."
            )
        if led_symptom in ("red_7_blinks", "red_6L"):
            cause_parts.append(
                "6 Long or 7 Blinks indicate sub-component hardware verification failure during update — most commonly "
                "CP (CXD90058 Cetus TOPPERS cpapp-b.bin) NOR failure or latent BGA solder fault on the WF-12 Wi-Fi/Bluetooth module."
            )

        # Note: If CXD90057 48KB BootROM is intact and only eMMC Sector 0 (not SPI NOR/PMIC/WF-12 hardware) is damaged,
        # Multi-Terminal 1.8V UART BootROM injection (RP2040 48000 baud -> SRAM fastboot.bin -> 18d1:4ee0) can still rescue eMMC!
        uart_bootrom_possible = ("sector0" in regions) and ("spi_nor" not in regions) and (led_symptom != "red_6L")

        return BrickDiagnosis(
            level="LEVEL_4_SPOF_HARDWARE_BRICK",
            severity="CRITICAL_HARDWARE",
            title="Level 4 Hard Brick — SPOF Bootloader / Sector 0 / CP RTOS / WF-12 Hardware Fault",
            root_cause_summary=" ".join(cause_parts) or "Early ROM -> SPI NOR -> eMMC Sector 0 boot chain broken.",
            software_usb_or_sd_recoverable=False,
            disassembly_free_uart_bootrom_recoverable=uart_bootrom_possible,
            hardware_programmer_required=not uart_bootrom_possible,
            active_boot_chain_status="ROM / loader_nor.bin halted before Linux kernel load",
            primary_recovery_steps=[
                "1. Disconnect battery and external USB-PD power immediately.",
                "2. Attempt Disassembly-Free 15-Pin Multi-Terminal UART BootROM Rescue (`ILCE-7M4-RE` `uart_boot` method): "
                "Connect an RP2040-Zero in 1.8V open-drain mode to the Multi port (Back Row Pin 7=UART RX, Pin 8=UART TX, Pin 9=XReset, Pin 2=GND), "
                "stream the 48,000-baud BootROM handshake to load `fastboot.bin` into SRAM (`0x92028000`), and check if USB-C enumerates as Fastboot (`18D1:4EE0`).",
                "3. If Fastboot (`18D1:4EE0`) enumerates: restore the verified 512-byte eMMC Sector 0 (`8246` `2.00`) and boot partitions over USB-C.",
                "4. If Octal-SPI NOR is corrupted (or `WF-12` Wi-Fi/BT IC failed causing 6-Long-Blink update hang): "
                "attach a 1.8V Octal-SPI NOR programmer to the `SY-1114` mainboard and restore the same-body NOR dump "
                "(CRITICAL: preserve `ddrtraining.dat` at NOR offset `0x03e210fc` and Sector 512 `MIS.bin`!).",
            ],
            fallback_recovery_steps=[
                "If no same-body SPI NOR / calibration backup exists: official Sony Service `SY-1114` (`A-5027-829-B` / `A-5037-073-B`) "
                "mainboard replacement calibrated with Sony Adjust Station + SeusEX HASP dongle is required."
            ],
            critical_warnings=[
                "NEVER flash another camera's SPI NOR dump without splicing this board's own ddrtraining.dat (0x03e210fc), or PoP LPDDR training at 0xFE080000 will fail.",
                "NEVER overwrite p6 (Jiritsu), p18 (/lens/lensfile.bin), or p2 (psd.bin / defdet.bin) with donor images."
                if has_full_body_backup
                else "WARNING: has_full_body_backup=False! Without a prior per-body backup of ddrtraining.dat, p6, p18, and p2, full calibration cannot be reconstructed from BODYDATA.DAT alone.",
            ],
        )

    # 2. Check for Level 0: Warm Boot Image (p5 WBI) or One-Shot Overlay Auto-Recovery
    if regions == {"p5_wbi"} or (oneshot_overlay_used and "p15_usr" in regions and len(regions) == 1):
        return BrickDiagnosis(
            level="LEVEL_0_TRANSIENT_OR_ONESHOT_OVERLAY",
            severity="LOW",
            title="Level 0 Transient Fault — Auto-Recoverable via One-Shot Token / WBI Drop",
            root_cause_summary=(
                "Modification was confined to RAM VFS bind-mount (/usr/lib/appFw.so) with Clear-Before-Exec token "
                "(/tmp/mod_arm_once) or stale Warm Boot Image (p5 /dev/nflasha5 'WB40' / WBI0..2)."
            ),
            software_usb_or_sd_recoverable=True,
            disassembly_free_uart_bootrom_recoverable=True,
            hardware_programmer_required=False,
            active_boot_chain_status="p3 Kernel + p7 Rootfs + p15 Stock Partition Intact",
            primary_recovery_steps=[
                "1. Wait 45 seconds for the /sbin/init2 BusyBox watchdog to detect missing /dev/shm/fx3_ap_healthy and auto-reboot.",
                "2. Or remove the NP-FZ100 battery for 15 seconds (and eject the SD card if SD overlay is used), then reinsert and power on.",
                "3. Because /tmp/mod_arm_once was unlinked and synced BEFORE mount --bind, the next cold boot unconditionally mounts stock p15 (/usr).",
            ],
            fallback_recovery_steps=[
                "Once booted into stock OS, inspect /log/mod_crash_dmesg.log on p11 to diagnose the root cause."
            ],
            critical_warnings=[
                "Always ensure ud_wbi_drop.elf (or p5 512-byte zero-header image_drop=1 before image_mode=0) runs before toggling any bind-mount overlay."
            ],
        )

    # 3. Check for Level 3: p1 Updater Partition Corruption while Main OS (p3+p7+p15) is Healthy
    if regions == {"p1_updater"} and display_state == "normal_ui":
        return BrickDiagnosis(
            level="LEVEL_3_P1_UPDATER_CORRUPTION",
            severity="MEDIUM",
            title="Level 3 Updater Partition (p1 / nflasha1) Corruption — Main OS Healthy",
            root_cause_summary=(
                "Normal camera OS (p3 + p7 + p15) boots and operates, but p1 (/dev/nflasha1, LBA 0x80, 23.94 MiB VFAT) "
                "has a corrupted FAT12 chain, /p1chksum mismatch, or interrupted candidate patch."
            ),
            software_usb_or_sd_recoverable=True,
            disassembly_free_uart_bootrom_recoverable=True,
            hardware_programmer_required=False,
            active_boot_chain_status="Normal Boot (p3 -> p7 -> p15) Healthy; Updater Boot (p1) Impaired",
            primary_recovery_steps=[
                "1. Do NOT trigger an SD card or USB firmware update (up.sh mode2/5/6) until p1 is restored!",
                "2. Run `python3 -m fx3_recovery diagnose --bundle <bundle> --input <current.p1>` to classify p1 state (ORIGINAL, CANDIDATE, MIXED_KNOWN_SPANS).",
                "3. Run `python3 -m fx3_recovery rollback --bundle <bundle> --input <current.p1> --out <restore_dir>` to produce byte-exact restored.p1 and verify SHA-256.",
                "4. Restore verified source.p1 (preserving p1:/dat2 Model ID 91030080 and p1:/dat3 Region) while Main OS is running.",
            ],
            fallback_recovery_steps=[
                "Verify restored p1 with `python3 -m fx3_recovery inspect --input restored.p1 --out inspect_out` before re-enabling updates."
            ],
            critical_warnings=[
                "FX3 7.02 BODYDATA.DAT does NOT contain a replacement p1 (/boot/vmlinux.bin, /boot/initrd.img) image! Never format p1 without a full 25,100,288-byte source.p1 backup."
            ],
        )

    # 4. Check for `/etc/ld.so.preload` Dynamic BusyBox Trap (`p10_preload`) or Level 2 (`p2`/`p3`/`p7`)
    if any(r in regions for r in ("p3_system", "p2_backup", "p7_rootfs", "p10_preload")):
        if updater_mode_armed or usb_vid_pid in ("054C:096F", "054C:03E2") or display_state == "update_progress_or_error":
            return BrickDiagnosis(
                level="LEVEL_2_BOOT_CHAIN_FAULT_WITH_P1_ARMED",
                severity="HIGH",
                title="Level 2 Main Boot Chain (p2/p3/p7/p10) Fault — Recoverable via Armed p1 Updater",
                root_cause_summary=(
                    "Normal boot chain (p2:/Backup.bin 0xfa0080, p3:/vmlinux.bin/initrd.img, p7:/rootfs, or p10:/etc/ld.so.preload) is impaired, "
                    "but p2:/setting/updater/mode* (or LSI 0x376 updater flag) is active, routing loader_nor.bin into p1 (/dev/nflasha1)."
                ),
                software_usb_or_sd_recoverable=True,
                disassembly_free_uart_bootrom_recoverable=True,
                hardware_programmer_required=False,
                active_boot_chain_status="loader_nor.bin -> p1 (/boot/vmlinux.bin + /boot/initrd.img) Updater Environment Active",
                primary_recovery_steps=[
                    "1. Insert a freshly formatted exFAT/FAT32 UHS-I SD card in Slot 1 containing official FX3 7.02 BODYDATA.DAT at root (`/BODYDATA.DAT`).",
                    "2. If in mode5 (sdfileinput.elf) or mode6 (sauu -s verskip), allow the p1 updater to verify FDAT and reflash p2/p3/p7/p8/p10/p15.",
                    "3. If in mode2 (USB Updater 054C:03E2 / 054C:096F), connect via USB-C to Sony System Software Updater (or sauu host runner) to complete the update transaction.",
                    "4. Wait until the access lamp finishes blinking and the camera reboots cleanly (recreating /setting/updater/comp and clearing mode*).",
                ],
                fallback_recovery_steps=[
                    "If sdfileinput.elf rejects same-version BODYDATA.DAT because p2:/setting/updater/dat4 was already bumped to 0702: use a patched p1 (isVersionOK @ 0x9fd4) or sauu -s (mode6)."
                ],
                critical_warnings=[
                    "Never remove the battery while p1 updater is executing nor_loader_writer.sh (ud_cp_firmup.elf) or edisx.elf!"
                ],
            )
        else:
            preload_note = (
                " Because FX3's `busybox` is dynamically linked, a bad `/etc/ld.so.preload` on `p10` (`nflasha10`, 12 MiB VFAT) crashes every init/shell process at boot!"
                if "p10_preload" in regions
                else ""
            )
            return BrickDiagnosis(
                level="LEVEL_2_UNARMED_P2_P3_P7_BOOT_HANG",
                severity="CRITICAL_HARDWARE",
                title="Level 2 Unarmed Main Boot Chain Fault — Requires Multi-Port UART BootROM or ISP Rescue",
                root_cause_summary=(
                    "Disassembly of loader_nor.bin (0xfe0545dc..0xfe054a08) proves there is NO automatic watchdog failover "
                    "from Normal Boot (p3) to Updater Boot (p1). Because p2/p3/p7/p10 is broken and /setting/updater/mode* was NOT armed, "
                    "the camera hangs in Normal Boot before userland (im.elf / libObj.so / USB Service) can start." + preload_note
                ),
                software_usb_or_sd_recoverable=usb_vid_pid == "18D1:4EE0",
                disassembly_free_uart_bootrom_recoverable=True,
                hardware_programmer_required=False,
                active_boot_chain_status="Stuck in Normal Boot (p2/p3/p7/p10) prior to USB/SD service initialization",
                primary_recovery_steps=[
                    "1. DISASSEMBLY-FREE PRIMARY RESCUE (Multi-Terminal 1.8V UART BootROM Injection): "
                    "Connect an RP2040-Zero (`tools/uart_boot`, open-drain 1.8V) to the external 15-pin Sony Multi Terminal "
                    "(Back Row Pin 7=UART RX, Pin 8=UART TX, Pin 9=XReset `MULTI_RST`, Pin 2=GND).",
                    "2. Pull `MULTI_RST` and stream the 48,000-baud BootROM handshake to inject bare-metal `fastboot.bin` into SRAM (`0x92028000`). "
                    "UART will output `[mira] fastboot ready` at 115,200 baud and USB-C will enumerate as Google Fastboot (`18D1:4EE0`).",
                    "3. Over USB-C Fastboot (`18D1:4EE0`), either:",
                    "   a) Write `/setting/updater/mode` and `/setting/updater/mode6` into plaintext `p2` (`nflasha2`, LBA `0xC000`) so `loader_nor.bin` boots `p1` Updater on next reboot, OR",
                    "   b) If caused by `/etc/ld.so.preload` on `p10` (`nflasha10`), overwrite `/etc/ld.so.preload` with 512 bytes of whitespace (`0x20`), OR",
                    "   c) Directly flash back the verified backups of `p2` (LBA `0xC000`), `p3` (LBA `0x16000`), and `p7` (LBA `0xE4800`).",
                ],
                fallback_recovery_steps=[
                    "If Multi-Terminal UART bridge is unavailable: use eMMC ISP pads on the `SY-1114` board to write `/updater/mode` onto plaintext `p2` (LBA `0xC000`)."
                ],
                critical_warnings=[
                    "NEVER use `/etc/ld.so.preload` on Bionz XR cameras (`busybox` is dynamically linked); always use `libJit.so` (`nflasha6`) or our 4-Layer `init2` RAM `mount --bind` overlay.",
                    "Because `p2` (LBA `0xC000`) is UNENCRYPTED VFAT (`type=4, flag=1`), writing `/updater/mode` onto `p2` redirects `loader_nor.bin` into `p1` recovery without needing AES-XTS decryption!",
                ],
            )

    # 5. Default / Level 1: Userland Application (p15 /usr: im.elf / appFw.so) Crash or Hang
    usb_service_alive = usb_vid_pid in ("054C:0DA1", "054C:0DA3", "054C:0994", "054C:0336")
    return BrickDiagnosis(
        level="LEVEL_1_USERLAND_APPFW_SOFT_BRICK",
        severity="MEDIUM" if (usb_service_alive or updater_mode_armed) else "HIGH",
        title="Level 1 Userland Application (im.elf / appFw.so on p15) Soft Brick",
        root_cause_summary=(
            "Linux kernel (p3) and rootfs (p7) boot normally, but /usr/bin/im.elf or /usr/lib/appFw.so on p15 crashes "
            "(missing ELF symbol, C++ RTTI mismatch, Backup.bin enum assert, or futex deadlock). "
            + (
                f"USB ({usb_vid_pid}) is still reachable."
                if usb_service_alive
                else "im.elf failed before initializing USB Service (libsencore.so) and UIPC updater listener (libObj.so @ 0xEE0B0)."
            )
        ),
        software_usb_or_sd_recoverable=usb_service_alive or updater_mode_armed,
        disassembly_free_uart_bootrom_recoverable=True,
        hardware_programmer_required=False,
        active_boot_chain_status=(
            f"Kernel + p7 Rootfs Alive; USB ({usb_vid_pid}) Reachable"
            if usb_service_alive
            else "Kernel + p7 Rootfs Alive; Userland im.elf Dead/Hung (Black Screen / Steady Red Lamp)"
        ),
        primary_recovery_steps=(
            [
                "1. Connect camera in Mass Storage mode (054C:0DA1 / 054C:0994) and establish authenticated Stage 285/286 SERVICE session (054C:0336).",
                "2. Trigger p1 updater entry (`/bin/up.sh verskip` / `/setting/updater/mode` + `mode6`) or clear stuck `/setting/updater/mode1` + WBI (`image_drop=1`).",
                "3. Reboot into p1 updater and re-apply official FX3 7.02 BODYDATA.DAT in SD Slot 1.",
            ]
            if usb_service_alive
            else [
                "1. If Layer-3 init2 Watchdog was installed: wait 45s (up to 3 boot cycles) for the watchdog to write `/setting/updater/mode` + `mode5` (and unlink `comp`), automatically booting into p1 SD recovery.",
                "2. Once in p1 recovery, insert SD card with official BODYDATA.DAT in Slot 1 to restore stock p15 (/usr).",
                "3. If no watchdog was installed and im.elf died before USB/UIPC init: use the 15-pin Multi-Terminal 1.8V UART BootROM bridge (`RP2040` @ 48,000 baud -> `fastboot.bin` -> USB-C `18D1:4EE0`) to write `/updater/mode` + `mode6` onto plaintext `p2` (LBA `0xC000`).",
            ]
        ),
        fallback_recovery_steps=[
            "To prevent Level 1 soft bricks completely: never modify /dev/nflasha15 in-place; always use the 4-Layer Bind-Mount + Clear-Before-Exec + 45s Watchdog architecture."
        ],
        critical_warnings=[
            "Remember: on stock FX3, both SD/USB update triggering (libObj.so @ 0xED990) and USB Service Mode (libsencore.so) run INSIDE im.elf! Never modify p15 without an init2 watchdog hook."
        ],
    )


def generate_failsafe_init2_overlay_hook(
    *,
    mod_payload_path: str = "/log/mod/appFw.so",
    target_mount_path: str = "/usr/lib/appFw.so",
    oneshot_token_path: str = "/tmp/mod_arm_once",
    fail_counter_path: str = "/tmp/mod_fail_count",
    heartbeat_path: str = "/dev/shm/fx3_ap_healthy",
    watchdog_timeout_sec: int = 45,
    max_consecutive_failures: int = 3,
) -> str:
    """Generate the audited 4-Layer Fail-Safe BusyBox sh snippet for p7:/sbin/init2."""
    return f"""# === BEGIN FX3 4-LAYER FAIL-SAFE OVERLAY & WATCHDOG HOOK ===
# Placed in p7:/sbin/init2 AFTER `busybox mount -a -T $FSTAB` and BEFORE `/usr/bin/bootin.elf &`
MOD_ACTIVE=0
if [ -f "{oneshot_token_path}" ] && [ -f "{mod_payload_path}" ]; then
    # Layer 2: Clear-Before-Exec (Immediate unlink + sync guarantees next battery pull boots stock)
    rm -f "{oneshot_token_path}"
    busybox sync

    # Increment fail counter until heartbeat proves healthy UI boot
    FAILS=0
    if [ -f "{fail_counter_path}" ]; then
        FAILS=$(cat "{fail_counter_path}" 2>/dev/null || echo 0)
    fi
    FAILS=$((FAILS + 1))
    echo "$FAILS" > "{fail_counter_path}"
    busybox sync

    if [ "$FAILS" -le {max_consecutive_failures} ]; then
        # Layer 1: RAM VFS Bind-Mount Overlay (p15 /usr remains 100% untouched RO on eMMC)
        rm -f "{heartbeat_path}" 2>/dev/null
        if busybox mount --bind "{mod_payload_path}" "{target_mount_path}" 2>/dev/null; then
            MOD_ACTIVE=1
        fi
    else
        # Layer 4: Consecutive failure threshold reached -> Pre-arm p1 Updater Recovery
        mkdir -p /setting/updater 2>/dev/null
        rm -f /setting/updater/comp 2>/dev/null
        : > /setting/updater/mode
        : > /setting/updater/mode5
        rm -f "{fail_counter_path}"
        busybox sync
    fi
fi

if [ "$MOD_ACTIVE" = "1" ]; then
    # Layer 3: Detached Userspace Liveness Watchdog
    (
        sleep {watchdog_timeout_sec}
        if ! busybox pidof im.elf >/dev/null 2>&1 || [ ! -f "{heartbeat_path}" ]; then
            busybox dmesg > /log/mod_crash_dmesg.log 2>&1
            busybox umount -l "{target_mount_path}" 2>/dev/null
            rm -f "{oneshot_token_path}" 2>/dev/null
            busybox sync
            busybox reboot -f
        else
            # Boot succeeded and UI heartbeat confirmed -> reset failure counter
            rm -f "{fail_counter_path}" 2>/dev/null
            busybox sync
        fi
    ) &
fi
# === END FX3 4-LAYER FAIL-SAFE OVERLAY & WATCHDOG HOOK ===
"""
