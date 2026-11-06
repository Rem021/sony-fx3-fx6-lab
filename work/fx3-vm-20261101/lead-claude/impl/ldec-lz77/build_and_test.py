#!/usr/bin/env python3
"""Compile/test host decoders, then read-only verify all 51,642 FX3 records.

Writes only beside this script. No QEMU, guest, runtime mutation or network.
Requires Python3, a C11 compiler and Pillow (only for PNG oracle/contact sheet).
"""
import collections
import ctypes
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import plistlib
import random
import subprocess
import sys
import unittest

sys.dont_write_bytecode = True
from decode_ldec import decode_details, decode_ldec, rgba4444, write_png, DecodeError
from resource_tools import ROOT, RESOURCES, PROOF, uxd_records, png_records


def sha(data): return hashlib.sha256(data).hexdigest()
def save(name, data): (ROOT / name).write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n")


class Info(ctypes.Structure):
    _fields_ = [(name, ctypes.c_size_t) for name in
                ("input_bytes", "output_bytes", "blocks", "raw_blocks", "literals", "matches", "max_distance")]


def load_c(path):
    lib = ctypes.CDLL(str(path))
    lib.ldec_soft_decode.argtypes = [ctypes.c_void_p, ctypes.c_size_t, ctypes.c_void_p, ctypes.c_size_t, ctypes.POINTER(Info)]
    lib.ldec_soft_decode.restype = ctypes.c_int
    def decode(src, size, validate=False):
        out = ctypes.create_string_buffer(b"\xa5" * size, size)
        status = lib.ldec_soft_decode(src, len(src), None if validate else out, size, None)
        return status, out.raw
    return lib, decode


def quantized_png(rgba, mode="high_nibble", canonical=False):
    out = bytearray(len(rgba) // 2)
    for p in range(0, len(rgba), 4):
        channels = [x >> 4 if mode == "high_nibble" else (x + 8) // 17 for x in rgba[p:p + 4]]
        if canonical and channels[3] == 0: channels[:3] = [0,0,0]
        value = channels[0] << 12 | channels[1] << 8 | channels[2] << 4 | channels[3]
        out[p // 2:p // 2 + 2] = value.to_bytes(2, "little")
    return bytes(out)


def crop4444(raw, width, height, canonical=False):
    stride = ((width + 15) & ~15) * 2
    result = b"".join(raw[y * stride:y * stride + width * 2] for y in range(height))
    if canonical:
        x = bytearray(result)
        for p in range(0,len(x),2):
            if x[p] & 15 == 0: x[p:p+2] = b"\0\0"
        result = bytes(x)
    return result


def main():
    # Verify volume identity before making even a build directory.
    volume = plistlib.loads(subprocess.check_output(["diskutil", "info", "-plist", "/Volumes/KAFU2T"]))
    if volume.get("VolumeUUID") != "F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B":
        raise RuntimeError("wrong/unmounted target volume")
    for name in ("results", "build", "samples"): (ROOT / name).mkdir(exist_ok=True)
    cc = os.environ.get("CC", "clang")
    shared = ROOT / "build/libldec_soft.dylib"
    flags = ["-std=c11", "-O2", "-Wall", "-Wextra", "-Werror", "-pedantic"]
    subprocess.run([cc, *flags, "-dynamiclib", str(ROOT / "ldec_soft.c"), "-o", str(shared)], check=True)
    subprocess.run([cc, *flags, "-target", "aarch64-none-elf", "-ffreestanding", "-fno-builtin",
                    "-c", str(ROOT / "ldec_soft.c"), "-o", str(ROOT / "build/ldec_soft-aarch64.o")], check=True)
    sanitizer = ROOT / "build/test_c_sanitized"
    subprocess.run([cc, *flags, "-g", "-fsanitize=address,undefined", "-fno-omit-frame-pointer",
                    str(ROOT / "ldec_soft.c"), str(ROOT / "tests/test_c.c"), "-o", str(sanitizer)], check=True)
    subprocess.run([str(sanitizer)], check=True)
    subprocess.run([sys.executable, "-B", str(ROOT / "infer_format.py")], check=True)
    lib, cdecode = load_c(shared)
    spec = importlib.util.spec_from_file_location("test_decoder", ROOT / "tests/test_decoder.py")
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    mod.DecoderTests.cdecode = staticmethod(cdecode)
    tests = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromModule(mod))
    if not tests.wasSuccessful(): return 1

    # Deterministic malformed-byte differential checks; C destination unchanged on rejection.
    rng = random.Random(0x1dec2026)
    rejected = accepted = 0
    seed = mod.packed_block([65,66,(15,2)])
    for _ in range(3000):
        src = bytearray(seed)
        for _ in range(rng.randrange(1,4)):
            src[rng.randrange(len(src))] = rng.randrange(256)
        target = rng.choice([1,32,65,66,67,128])
        try: py = decode_ldec(src, target)
        except DecodeError: py = None
        code, c = cdecode(bytes(src), target)
        assert (code == 0) == (py is not None)
        if py is not None:
            assert c == py; accepted += 1
        else:
            assert c == b"\xa5" * target; rejected += 1

    from PIL import Image, ImageDraw
    proof = json.loads(PROOF.read_text())
    source_receipts = []
    png_data = (RESOURCES / "image.uxb").read_bytes()
    expected_png = next(r for r in proof["resources"]["other_files"] if r["path"].endswith("/image.uxb"))
    assert sha(png_data) == expected_png["sha256"]
    pngs = list(png_records(png_data)); assert len(pngs) == 831
    png_by_dim, png_by_id, png_lookup = collections.Counter(), set(), collections.defaultdict(list)
    for p in pngs:
        start = p["source_offset"]
        image = Image.open(io.BytesIO(png_data[start:start + p["source_bytes"]])).convert("RGBA")
        assert image.size == (p["width"], p["height"])
        dim = image.size; png_by_dim[dim] += 1; png_by_id.add(p["id_low24"])
        for mode in ("high_nibble", "nearest"):
            for canonical in (False,True):
                key = (*dim, mode, canonical, sha(quantized_png(image.tobytes(), mode, canonical)))
                png_lookup[key].append({k:p[k] for k in ("bank","index","id_low24")})
    summary = {"scope":"host/offline only; original hardware equivalence and guest integration unproven",
               "total_records":0, "length_matches":0, "python_c_byte_matches":0,
               "total_output_bytes":0, "source_bytes":0, "failures":[], "files":[],
               "proof_sha256":sha(PROOF.read_bytes()), "png_records":len(pngs),
               "png_same_id_records":0, "png_dimension_candidate_records":0,
               "png_pixel_matches":[], "sample_images":[],
               "tests":{"unit_methods":tests.testsRun,"mutations_accepted":accepted,"mutations_rejected":rejected,
                        "aarch64_freestanding_compile":"passed (not linked or guest executed)",
                        "c_sanitizers":"address,undefined passed"}}
    cache = {}
    block_sizes = collections.Counter(); block_types = collections.Counter(); raw_reserved = collections.Counter()
    terminators = collections.Counter(); max_distance = 0
    chosen = {("image_00_43.uxc",215):"icon-00-215", ("image_01_43.uxc",29):"icon-01-29",
              ("image_02_43.uxc",0):"icon-02-0", ("image_00_43.uxc",0):"icon-00-0",
              ("image_01_43.uxc",1355):"nine-patch-01-1355", ("image_02_43.uxc",201):"nine-patch-02-201",
              ("image_01_43.uxc",1356):"highlight-fill-01-1356", ("image_01_43.uxc",1357):"highlight-fill-01-1357",
              ("image_01_43.uxc",1533):"highlight-frame-01-1533",
              ("image_02_43.uxc",1228):"panel-02-1228",
              ("image_02_43.uxc",1840):"tiny-02-1840", ("image_02_43.uxc",1603):"tiny-02-1603"}
    ledger = (ROOT / "results/all_records.jsonl").open("w")
    for path in sorted(RESOURCES.glob("image_*.uxc")):
        data = path.read_bytes()
        expected = next(x for x in proof["resources"]["files"] if x["path"].endswith("/" + path.name))
        digest = sha(data); assert digest == expected["sha256"]
        records = list(uxd_records(data)); assert len(records) == expected["valid_records"]
        receipt = {"file":path.name,"sha256":digest,"bytes":len(data),"records":len(records),"length_matches":0,"failures":0}
        source_receipts.append(receipt)
        for rec in records:
            summary["total_records"] += 1
            start, size = rec["source_offset"], rec["source_bytes"]
            source = data[start:start+size]
            source_hash = sha(source)
            key = (source_hash, rec["output_bytes"])
            row = {"file":path.name, **rec, "source_sha256":source_hash}
            try:
                # Decode every record in C. Byte-compare Python on each unique stream+size.
                code, raw_c = cdecode(source, rec["output_bytes"])
                if code: raise RuntimeError("C status " + str(code))
                output_hash = sha(raw_c)
                if key not in cache:
                    raw_py, info = decode_details(source, rec["output_bytes"])
                    if raw_py != raw_c: raise RuntimeError("Python/C byte mismatch")
                    cache[key] = (output_hash,info)
                cached_hash, info = cache[key]
                if output_hash != cached_hash: raise RuntimeError("repeated stream C mismatch")
                expected_blocks = (rec["output_bytes"] + 4095) // 4096
                expected_sizes = [4096] * (expected_blocks - 1) + [rec["output_bytes"] - 4096 * (expected_blocks - 1)]
                if info.block_sizes != expected_sizes: raise RuntimeError("non-4KiB hardware record structure")
                summary["length_matches"] += 1; summary["python_c_byte_matches"] += 1
                summary["total_output_bytes"] += len(raw_c); summary["source_bytes"] += size
                receipt["length_matches"] += 1
                block_sizes.update(info.block_sizes); block_types.update(info.block_types)
                raw_reserved.update(info.raw_reserved); terminators.update(info.terminator_codes)
                max_distance = max(max_distance, info.max_distance)
                row.update(status="ok", output_sha256=output_hash, block_count=len(info.block_sizes))
                dim = (rec["width"],rec["height"])
                if rec["id_low24"] in png_by_id: summary["png_same_id_records"] += 1
                if dim in png_by_dim:
                    summary["png_dimension_candidate_records"] += 1
                    for canonical in (False,True):
                        visible_hash = sha(crop4444(raw_c,*dim,canonical))
                        for mode in ("high_nibble","nearest"):
                            hits = png_lookup.get((*dim,mode,canonical,visible_hash))
                            if hits: summary["png_pixel_matches"].append({"file":path.name,"index":rec["index"],"mode":mode,"transparent_rgb_ignored":canonical,"png":hits})
                name = chosen.get((path.name,rec["index"]))
                if name:
                    rgba = rgba4444(raw_c,*dim)
                    write_png(ROOT / "samples" / (name + ".png"),*dim,rgba)
                    (ROOT / "samples" / (name + ".raw")).write_bytes(raw_c)
                    (ROOT / "samples" / (name + ".ldec")).write_bytes(source)
                    alpha = collections.Counter(rgba[3::4])
                    rgb_adj_equal = sum(rgba[p:p+4] == rgba[p-4:p] for p in range(4,len(rgba),4)) / max(1,len(rgba)//4-1)
                    sample = {**row,"name":name,"alpha_histogram":dict(alpha),"adjacent_rgba_equal_fraction":rgb_adj_equal,
                              "role":"geometry candidate; runtime resource identity unproven"}
                    summary["sample_images"].append(sample)
            except (DecodeError,RuntimeError) as error:
                row.update(status="failed",error=str(error)); summary["failures"].append(row); receipt["failures"] += 1
            ledger.write(json.dumps(row,sort_keys=True) + "\n")
        summary["files"].append(receipt)
        assert sha(path.read_bytes()) == digest, "source changed during run"
        print(f"{path.name}: {receipt['length_matches']}/{len(records)} exact; unique streams so far {len(cache)}",flush=True)
    ledger.close()
    assert sha((RESOURCES / "image.uxb").read_bytes()) == expected_png["sha256"]
    for entry in (proof["original_libObj"],proof["original_ldec"]):
        assert sha(Path(entry["path"]).read_bytes()) == entry["sha256"]
    summary.update(unique_stream_size_pairs=len(cache), block_size_histogram=dict(block_sizes),
                   block_type_histogram={hex(k):v for k,v in block_types.items()},
                   raw_reserved_histogram=dict(raw_reserved), terminator_code_histogram=dict(terminators),
                   max_distance=max_distance, all_hardware_record_blocks_4k_except_final=True,
                   originals_hashes_unchanged=True, length_match_rate=summary["length_matches"] / summary["total_records"],
                   ledger_sha256=sha((ROOT / "results/all_records.jsonl").read_bytes()))
    # Contact sheet composites against a checkerboard so alpha edges remain inspectable.
    sheet = Image.new("RGB",(1000, 10 + 250 * ((len(summary["sample_images"])+2)//3)),(35,35,35)); draw = ImageDraw.Draw(sheet)
    for i,sample in enumerate(summary["sample_images"]):
        x,y = (i%3)*333,(i//3)*250
        im = Image.open(ROOT / "samples" / (sample["name"]+".png")).convert("RGBA")
        scale = min(315 / im.width, 210 / im.height, 4)
        im = im.resize((max(1,int(im.width * scale)),max(1,int(im.height * scale))),Image.Resampling.NEAREST)
        bg = Image.new("RGBA",im.size)
        bd = ImageDraw.Draw(bg)
        for ty in range(0,im.height,8):
            for tx in range(0,im.width,8): bd.rectangle((tx,ty,tx+7,ty+7),fill=(180,180,180,255) if (tx//8+ty//8)%2 else (100,100,100,255))
        bg.alpha_composite(im); sheet.paste(bg.convert("RGB"),(x+8,y+25))
        draw.text((x+8,y+8),sample["name"],fill=(255,255,255))
    sheet.save(ROOT / "samples/contact-sheet.png")
    save("results/batch_summary.json",summary)
    save("results/failures.json",summary["failures"])
    save("results/build_receipt.json",{"compiler":subprocess.check_output([cc,"--version"],text=True).splitlines()[0],
         "python":sys.version,"sources":{str(p.relative_to(ROOT)):sha(p.read_bytes()) for p in
             sorted([*ROOT.glob("*.py"),*ROOT.glob("*.c"),*ROOT.glob("*.h"),*(ROOT/"tests").glob("*.py"),*(ROOT/"tests").glob("*.c")])},
         "tests":summary["tests"],"source_resources":source_receipts})
    assert summary["total_records"] == 51642
    print(f"PASS: exact {summary['length_matches']}/51642; Python/C {summary['python_c_byte_matches']}; failures {len(summary['failures'])}",flush=True)
    return 0 if not summary["failures"] else 1


if __name__ == "__main__": sys.exit(main())
