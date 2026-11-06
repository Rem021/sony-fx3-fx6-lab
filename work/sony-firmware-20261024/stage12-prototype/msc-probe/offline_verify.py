#!/usr/bin/env python3
"""Only static source / synthetic fixtures. Never imports a Windows DLL or opens devices.

This is a reference-model check, not execution/compilation of the C# or PowerShell.
The separate clang syntax-only fixture checks the MSVC x64 target ABI.
"""
import copy
import datetime
import hashlib
import json
import re
import struct
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
checks = []

def check(name, result):
    if not result:
        raise AssertionError(name)
    checks.append(name)

def select(rows):
    if len(rows) != 1:
        raise ValueError("exactly one candidate required")
    x = rows[0]
    if not (x.get("AncestryProven") and x.get("InterfaceActive") and x.get("DiskStarted") and x.get("UsbStarted")
            and x.get("UsbHardwareIdentity") == "USB\\VID_054C&PID_0DA1"
            and x.get("BusDescription") == "ILME-FX3"
            and x.get("DiskService", "").casefold() == "disk"
            and x.get("UsbService", "").casefold() == "usbstor"
            and x.get("DiskNodeSha256") and x.get("UsbParentSha256")
            and x.get("DiskInterfacePath", "").startswith("\\\\?\\")
            and "physicaldrive" not in x.get("DiskInterfacePath", "").casefold()):
        raise ValueError("incomplete identity/path")
    return x

def rejected(rows):
    try:
        select(rows)
        return False
    except ValueError:
        return True

def decode(response):
    if len(response) < 36 or len(response) > 96 or response[4] < 31:
        raise ValueError("incomplete header")
    for b in response[8:36]:
        if not 0x20 <= b <= 0x7e:
            raise ValueError("non-ASCII")
    return [response[8:16].decode("ascii").rstrip(" "), response[16:32].decode("ascii").rstrip(" "), response[32:36].decode("ascii").rstrip(" ")]

def decode_rejected(response):
    try:
        decode(response)
        return False
    except ValueError:
        return True

def main():
    source = (HERE / "Fx3OneInquiry.cs").read_text()
    metadata = (HERE / "Fx3CachedAssociations.cs").read_text()
    wrapper = (HERE / "Review-Fx3Msc.ps1").read_text()
    check("active code behind undefined symbol", "#if FX3_APPROVED_ONE_INQUIRY" in source and "#define FX3_APPROVED_ONE_INQUIRY" not in source)
    active = source.split("#if FX3_APPROVED_ONE_INQUIRY", 1)[1].split("#endif", 1)[0]
    inactive = source.split("#if FX3_APPROVED_ONE_INQUIRY", 1)[0]
    check("native device functions absent from inactive source", "extern" not in inactive)
    check("one application DeviceIoControl call site", len(re.findall(r"if\s*\(!DeviceIoControl\(", active)) == 1)
    check("one application CreateFile call site", active.count("= CreateFileW(") == 1)
    check("active method private and uncalled", source.count("AttemptOne(") == 1 and "static byte[] AttemptOne(" in active)
    active_signature = active.split("static byte[] AttemptOne(", 1)[1].split(") {", 1)[0]
    check("no arbitrary-CDB parameter", "public static byte[] FixedCdb()" in source and "cdb" not in active_signature.lower())
    check("no device APIs in metadata collector", "extern" not in re.sub(r"\[DllImport\(\"(?:setupapi|cfgmgr32)\.dll\".*?\n\s*(?:\[return:.*?\]\s*)?static extern[^;]+;", "", metadata, flags=re.S))
    check("wrapper defaults DryRun", "[string]$Mode = 'DryRun'" in wrapper)
    check("wrapper has no active option", "ValidateSet('DryRun','CachedAssociations')" in wrapper and "Fx3OneInquiry.cs" not in wrapper)
    check("wrapper does not auto-elevate", all(x not in wrapper.lower() for x in ("runas", "start-process", "get-disk", "win32_diskdrive")))
    # Rebuild exactly the literal packet builder contract. No object/device I/O.
    cdb = bytes([0x12, 0, 0, 0, 0x60, 0])
    check("fixed six-byte CDB source", "new byte[] { 0x12, 0, 0, 0, 0x60, 0 }" in source)
    check("fixed packet constants source", "HeaderBytes = 56, DataOffset = 64, AllocationLength = 96, PacketBytes = 160" in source)
    check("fixed timeout source", "TimeoutSeconds = 3" in source)
    packet = bytearray(160)
    struct.pack_into("<H", packet, 0, 56)
    packet[6:9] = bytes([6, 0, 1])
    struct.pack_into("<II", packet, 12, 96, 3)
    struct.pack_into("<Q", packet, 24, 64)
    packet[36:42] = cdb
    check("CDB exactly INQUIRY EVPD=0 allocation96", bytes(packet[36:42]) == bytes.fromhex("12 00 00 00 60 00"))
    check("sense length and offset zero", packet[7] == 0 and packet[32:36] == bytes(4))
    check("no data-out payload", packet[64:] == bytes(96))
    check("all unassigned bytes zero", set(i for i, v in enumerate(packet) if v) == {0, 6, 8, 12, 16, 24, 36, 40})
    good = dict(DiskInterfacePath="\\\\?\\synthetic_fixture_only", DiskNodeSha256="a" * 64,
        UsbParentSha256="b" * 64, UsbHardwareIdentity="USB\\VID_054C&PID_0DA1", BusDescription="ILME-FX3",
        DiskService="disk", UsbService="USBSTOR", DiskStarted=True, UsbStarted=True,
        InterfaceActive=True, AncestryProven=True)
    check("synthetic unique healthy target accepted", select([good]) is good)
    check("zero targets refused", rejected([]))
    check("two matching targets refused", rejected([good, copy.deepcopy(good)]))
    for field, value in [
        ("DiskInterfacePath", ""), ("DiskInterfacePath", "\\\\.\\PhysicalDrive0"),
        ("DiskInterfacePath", "\\\\?\\PhysicalDrive0"), ("DiskInterfacePath", "\\\\.\\PhysicalDrive1"),
        ("UsbParentSha256", ""), ("DiskNodeSha256", ""), ("UsbHardwareIdentity", "USB\\VID_054C&PID_0DF2"),
        ("BusDescription", "ILCE-7CM2"), ("UsbService", "WinUSB"), ("DiskService", "unknown"),
        ("DiskStarted", False), ("UsbStarted", False), ("InterfaceActive", False), ("AncestryProven", False)]:
        row = copy.deepcopy(good); row[field] = value
        check("refuse " + field + "=" + repr(value), rejected([row]))
    wrong = copy.deepcopy(good); wrong["UsbService"] = "WinUSB"
    check("one healthy plus one unhealthy candidate still ambiguous", rejected([good, wrong]))
    header = bytearray(96); header[4] = 91
    header[8:36] = b"SYNTH   " + b"FIXTURE ONLY    " + b"0000"
    check("synthetic standard header decoder", decode(header) == ["SYNTH", "FIXTURE ONLY", "0000"])
    check("decoder refuses truncated header", decode_rejected(header[:35]))
    check("decoder refuses oversized transfer", decode_rejected(header + b"\0"))
    short_claim = bytearray(header); short_claim[4] = 30
    check("decoder refuses incomplete header declaration", decode_rejected(short_claim))
    non_ascii = bytearray(header); non_ascii[8] = 0xff
    check("decoder refuses malformed identifier text", decode_rejected(non_ascii))
    cache = json.loads((ROOT / "stage6-safety/windows-msc-inventory/sony-pnp-inventory.json").read_text())
    check("existing cache is parent-only and cannot bind disk", "candidates" not in cache and not any("DiskInterfacePath" in x for x in cache["sony_camera_candidate_nodes"]))
    check("existing cache expected USB identity", all(x["vid"] == "054C" and x["pid"] == "0DA1" for x in cache["sony_camera_candidate_nodes"]))
    command = ["clang", "-target", "x86_64-pc-windows-msvc", "-fsyntax-only", "-x", "c", str(HERE / "layout_fixture.c")]
    r = subprocess.run(command, capture_output=True, text=True, check=False)
    check("clang MSVC x64 ABI static assertions", r.returncode == 0)
    result = dict(schema="fx3-msc-source-only-verification/1", captured_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        result="PASS", check_count=len(checks), checks=checks, synthetic_packet_hex=packet.hex(),
        synthetic_packet_sha256=hashlib.sha256(packet).hexdigest(), clang_command=command,
        clang_stderr=r.stderr, camera_or_windows_executed=False, device_calls=0,
        limitations=["C# and PowerShell were not compiled or run; reference selector is a specification fixture, not implementation execution",
                     "Clang verifies own typedef layout for the Microsoft x64 target, not installed Windows SDK/runtime",
                     "No target disk path, per-body identity, alignment mask, or active driver behavior is proven"])
    (HERE / "offline-verification.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"result": "PASS", "check_count": len(checks), "device_calls": 0}))

if __name__ == "__main__":
    main()
