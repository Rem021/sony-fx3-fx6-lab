"""Unit tests for Phase 46 global.xdb UX Database Inspector & 128-Page Multilingual Menu Tree Auditor.

Runs in BOTH Local Donor mode (`os.O_RDONLY`) and `FX3_FX6_FORCE_CLEAN_ROOM=1`
mode in under 0.25 seconds, keeping the combined `fx3-firmware-lab` test suite
(>= 155 tests) under 6 seconds.
"""

from __future__ import annotations

import json
import os
import sqlite3
import struct
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from typing import Dict, Optional
from unittest.mock import patch

from fx3_firmware_lab.__main__ import main as cli_main, run_audit_all
from fx3_firmware_lab.global_xdb_and_menu_tree_auditor import (
    ASSIGNABLE_PAGE_110_POOL,
    BIG6_CELL_TITLES,
    FX6_11_CATEGORIES,
    FX6_128_PAGE_DIRECTORY,
    PHASE_46_SCHEMA,
    TARGET_LANGUAGES,
    GlobalXdbAndMenuTreeReport,
    GlobalXdbParseError,
    analyze_global_xdb_and_menu_tree,
    audit_128_page_multilingual_menu_tree,
    audit_global_xdb_file_rdonly,
    build_clean_room_menu_fixtures,
    build_sparse_uxc_string_pack,
    build_synthetic_fontlist_dat,
    build_synthetic_global_xdb,
    build_synthetic_lang_uxb,
    evaluate_fx3_hardware_predicates,
    global_xdb_and_menu_tree_report_to_dict,
    inspect_sqlite_ux_db_rdonly,
    parse_fontlist_dat_bytes,
    parse_global_xdb_buffer,
    parse_lang_uxb_bytes,
)
from fx3_firmware_lab.haita_bk4_feature_analyzer import is_forced_clean_room
from fx3_firmware_lab.uxc_multilang_and_font_verifier import parse_uxc_string_pack_slots


PKG_ROOT = Path(__file__).resolve().parents[1]


class TestActiveGlobalXdbAndMenuTreeAudit(unittest.TestCase):
    _active_report: Optional[GlobalXdbAndMenuTreeReport] = None

    @classmethod
    def setUpClass(cls) -> None:
        cls._active_report = analyze_global_xdb_and_menu_tree()

    def test_01_active_mode_passes_with_o_rdonly_and_sha256(self) -> None:
        rep = self._active_report
        assert rep is not None
        self.assertTrue(rep.all_checks_passed, msg=f"Errors: {rep.errors}")
        self.assertEqual(rep.schema_version, PHASE_46_SCHEMA)
        self.assertTrue(rep.o_rdonly_enforced)
        self.assertTrue(rep.sqlite_wal_shm_forbidden)
        self.assertTrue(rep.all_hardware_predicates_safe)
        self.assertTrue(rep.zero_null_pointer_hazards)
        self.assertEqual(len(rep.report_sha256), 64)
        self.assertEqual(rep.menu_tree_audit.categories_verified, 11)
        self.assertEqual(rep.menu_tree_audit.pages_audited, 128)
        self.assertEqual(rep.menu_tree_audit.total_descriptor_rows, 2224)
        self.assertEqual(rep.menu_tree_audit.missing_resids_total, 0)
        self.assertEqual(rep.menu_tree_audit.corrupt_utf8_total, 0)

        if not is_forced_clean_room() and rep.mode == "LOCAL_DONOR_VERIFIED":
            self.assertEqual(rep.fx6_global_xdb.file_bytes, 1792)
            self.assertEqual(rep.fx6_global_xdb.top_slot_count, 7)
            self.assertEqual(rep.fx6_global_xdb.non_dummy_resource_entries, 63)
            self.assertEqual(rep.fx6_global_xdb.referenced_files_present, 63)
            self.assertEqual(rep.fx3_global_xdb.file_bytes, 11664)
            self.assertEqual(rep.fx3_global_xdb.top_slot_count, 239)
            self.assertEqual(rep.fx3_global_xdb.non_dummy_resource_entries, 117)
            self.assertEqual(rep.fx3_global_xdb.referenced_files_present, 117)

    def test_02_active_report_json_serializable_without_raw_bytes(self) -> None:
        rep = self._active_report
        assert rep is not None
        payload = global_xdb_and_menu_tree_report_to_dict(rep)
        encoded = json.dumps(payload, sort_keys=True)
        self.assertNotIn("b'", encoded)
        decoded = json.loads(encoded)
        self.assertEqual(decoded["report_sha256"], rep.report_sha256)
        self.assertEqual(decoded["menu_tree_audit"]["pages_audited"], 128)

    def test_03_all_11_categories_have_4_language_titles(self) -> None:
        rep = self._active_report
        assert rep is not None
        cats = rep.menu_tree_audit.category_entries
        self.assertEqual(len(cats), 11)
        expected_names = [c[1] for c in FX6_11_CATEGORIES]
        self.assertEqual([c.category_name for c in cats], expected_names)
        for cat in cats:
            self.assertTrue(cat.valid, msg=f"Invalid category {cat.category_name}")
            for lang in TARGET_LANGUAGES:
                self.assertTrue(bool(cat.resolved_titles.get(lang)), msg=f"Missing {lang} in {cat.category_name}")
                self.assertEqual(cat.missing_by_language[lang], 0)

    def test_04_big6_home_and_p10_assignable_page110_verified(self) -> None:
        rep = self._active_report
        assert rep is not None
        mt = rep.menu_tree_audit
        self.assertTrue(mt.big6_home_verified)
        self.assertEqual(mt.big6_home_row_count, 98)
        self.assertEqual(len(mt.big6_cell_titles), 6)
        self.assertIn("ND Filter", mt.big6_cell_titles)
        self.assertEqual(mt.big6_cell_titles["ND Filter"]["simplifiedchinese"], "ND滤镜")
        self.assertTrue(mt.assignable_p10_page110_verified)
        self.assertEqual(mt.assignable_p10_row_count, 54)
        self.assertEqual(mt.assignable_p10_pool_count, 30)

    def test_05_hardware_predicates_map_to_deterministic_fx3_safe_states(self) -> None:
        rep = self._active_report
        assert rep is not None
        by_id = {h.predicate_id: h for h in rep.hardware_predicates}
        self.assertEqual(
            set(by_id.keys()),
            {"VARIABLE_ND", "SDI_12G_OUTPUT", "SMART_GRIP_HANDLE_ZOOM", "WLAN_AIRPLANE_GATE"},
        )
        self.assertEqual(by_id["VARIABLE_ND"].fx3_safe_state, "LOCKED_CLEAR")
        self.assertEqual(by_id["SDI_12G_OUTPUT"].fx3_safe_state, "HDMI_FALLBACK")
        self.assertEqual(by_id["SMART_GRIP_HANDLE_ZOOM"].fx3_safe_state, "INTERNAL_MIC_FALLBACK")
        self.assertEqual(by_id["WLAN_AIRPLANE_GATE"].fx3_safe_state, "AIRPLANE_ISOLATED")
        for h in rep.hardware_predicates:
            self.assertTrue(h.valid, msg=f"Predicate {h.predicate_id} invalid")
            self.assertTrue(h.multilang_labels_verified)
            self.assertTrue(h.appfw_marker_found)
            self.assertFalse(h.null_pointer_hazard)
            self.assertFalse(h.missing_widget_hazard)
            self.assertEqual(h.nvram_flash_mutation_bytes, 0)


class TestGlobalXdbAndCompanionParsers(unittest.TestCase):
    def test_06_synthetic_fx6_global_xdb_structure(self) -> None:
        raw = build_synthetic_global_xdb("fx6_601")
        res = parse_global_xdb_buffer(raw, body="fx6_601", source_mode="SYNTHETIC_CLEAN_ROOM")
        self.assertTrue(res.valid, msg=f"Errors: {res.errors}")
        self.assertEqual(res.container_format, "SONY_UXA7")
        self.assertEqual(res.header_magic_hex, "75786107")
        self.assertEqual(res.hdr_flag, 9)
        self.assertEqual(res.top_slot_count, 7)
        self.assertEqual(res.dummy_slot_count, 0)
        self.assertEqual(res.non_dummy_resource_entries, 63)

    def test_07_synthetic_fx3_global_xdb_handles_dummy_slots(self) -> None:
        raw = build_synthetic_global_xdb("fx3_702")
        res = parse_global_xdb_buffer(raw, body="fx3_702", source_mode="SYNTHETIC_CLEAN_ROOM")
        self.assertTrue(res.valid, msg=f"Errors: {res.errors}")
        self.assertEqual(res.top_slot_count, 12)
        self.assertGreater(res.dummy_slot_count, 0)
        self.assertEqual(res.active_slot_count + res.dummy_slot_count, res.top_slot_count)

    def test_08_global_xdb_rejects_truncated_and_bad_magic(self) -> None:
        short = parse_global_xdb_buffer(b"uxa\x07\x00\x00")
        self.assertFalse(short.valid)
        self.assertTrue(any("Truncated" in e for e in short.errors))

        bad = bytearray(build_synthetic_global_xdb("fx6_601"))
        bad[0:4] = b"BAD!"
        res_bad = parse_global_xdb_buffer(bytes(bad))
        self.assertFalse(res_bad.valid)
        self.assertTrue(any("Invalid global.xdb magic" in e for e in res_bad.errors))

    def test_09_global_xdb_rejects_bad_hdr_flag_and_oob_offset(self) -> None:
        bad_flag = bytearray(build_synthetic_global_xdb("fx6_601"))
        struct.pack_into("<H", bad_flag, 8, 99)
        res_flag = parse_global_xdb_buffer(bytes(bad_flag))
        self.assertFalse(res_flag.valid)
        self.assertTrue(any("hdr_flag" in e for e in res_flag.errors))

        bad_off = bytearray(build_synthetic_global_xdb("fx6_601"))
        struct.pack_into("<I", bad_off, 16, 0x7FFF00)
        res_off = parse_global_xdb_buffer(bytes(bad_off))
        self.assertFalse(res_off.valid)
        self.assertTrue(any("out of bounds" in e for e in res_off.errors))

    def test_10_global_xdb_rejects_invalid_utf8_in_string_entry(self) -> None:
        raw = bytearray(build_synthetic_global_xdb("fx6_601"))
        pos = raw.find(b"lang.uxb")
        self.assertNotEqual(pos, -1)
        raw[pos] = 0xFF
        res = parse_global_xdb_buffer(bytes(raw))
        self.assertFalse(res.valid)
        self.assertTrue(any("UTF-8" in e for e in res.errors))

    def test_11_audit_global_xdb_file_rdonly_detects_missing_disk_closure(self) -> None:
        raw = build_synthetic_global_xdb("fx6_601")
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "global.xdb"
            p.write_bytes(raw)
            res_missing = audit_global_xdb_file_rdonly(p, body="fx6_601", check_disk_closure=True)
            self.assertFalse(res_missing.valid)
            self.assertGreater(len(res_missing.referenced_files_missing), 0)

            res_no_disk = audit_global_xdb_file_rdonly(p, body="fx6_601", check_disk_closure=False)
            self.assertTrue(res_no_disk.valid)

    def test_12_sqlite_ux_db_rdonly_immutable_creates_no_wal_or_shm(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "ux_test.xdb"
            conn = sqlite3.connect(str(db_path))
            conn.execute("CREATE TABLE menu_nodes (id INTEGER PRIMARY KEY, label TEXT)")
            conn.execute("INSERT INTO menu_nodes VALUES (1, 'Shooting')")
            conn.commit()
            conn.close()

            # Remove any journal if present, then inspect read-only
            magic_hex, tables = inspect_sqlite_ux_db_rdonly(db_path)
            self.assertEqual(magic_hex, b"SQLite format 3\x00".hex())
            self.assertEqual(tables, ("menu_nodes",))
            self.assertFalse((Path(tmp) / "ux_test.xdb-wal").exists())
            self.assertFalse((Path(tmp) / "ux_test.xdb-shm").exists())
            self.assertFalse((Path(tmp) / "ux_test.xdb-journal").exists())

            audit = audit_global_xdb_file_rdonly(db_path, body="sqlite_test", check_disk_closure=False)
            self.assertTrue(audit.valid)
            self.assertEqual(audit.container_format, "SQLITE3_RDONLY")
            self.assertEqual(audit.sqlite_table_names, ("menu_nodes",))

    def test_13_sqlite_inspector_rejects_non_sqlite_magic(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "not_sqlite.xdb"
            p.write_bytes(build_synthetic_global_xdb("fx6_601"))
            with self.assertRaises(GlobalXdbParseError):
                inspect_sqlite_ux_db_rdonly(p)

    def test_14_lang_uxb_parse_and_error_handling(self) -> None:
        raw = build_synthetic_lang_uxb(namespace_id=4, count=36)
        magic_hex, ns_id, cnt, errs = parse_lang_uxb_bytes(raw)
        self.assertEqual(errs, ())
        self.assertEqual(magic_hex, "75786207")
        self.assertEqual(ns_id, 4)
        self.assertEqual(cnt, 36)

        _mh, _ns, _c, bad_errs = parse_lang_uxb_bytes(b"BAD!" + raw[4:])
        self.assertGreater(len(bad_errs), 0)

    def test_15_fontlist_dat_parse_fx6_and_fx3(self) -> None:
        fl6 = build_synthetic_fontlist_dat("fx6_601")
        m6, e6 = parse_fontlist_dat_bytes(fl6)
        self.assertEqual(e6, ())
        self.assertEqual(len(m6), 5)
        self.assertIn("FONT_S_CHINESE", m6)

        fl3 = build_synthetic_fontlist_dat("fx3_702")
        m3, e3 = parse_fontlist_dat_bytes(fl3)
        self.assertEqual(e3, ())
        self.assertEqual(len(m3), 6)
        self.assertIn("FONT_ICONS", m3)

        _mb, eb = parse_fontlist_dat_bytes(b"\xff\xfe")
        self.assertGreater(len(eb), 0)

    def test_16_sparse_uxc_string_pack_cjk_roundtrip(self) -> None:
        pack = build_sparse_uxc_string_pack(
            {0x0208: "用户", 0x0493: "繪製/外觀", 0x0D4A: "User Menu編集"},
            namespace_id=2,
        )
        ns, slots, slot_map, _empty, corrupt, errs = parse_uxc_string_pack_slots(pack)
        self.assertEqual(errs, [])
        self.assertEqual(corrupt, 0)
        self.assertEqual(ns, 2)
        self.assertGreaterEqual(slots, 0x0D4B)
        self.assertEqual(slot_map[0x0208][1], "用户")
        self.assertEqual(slot_map[0x0493][1], "繪製/外觀")
        self.assertEqual(slot_map[0x0D4A][1], "User Menu編集")


class TestMenuTreeCompletenessAndPredicates(unittest.TestCase):
    def _load_clean_room_parsed(self):
        fx = build_clean_room_menu_fixtures()
        uxc_packs = fx["uxc_packs"]
        lang_maps: Dict[str, Dict[int, Dict[int, tuple]]] = {}
        for lang in TARGET_LANGUAGES:
            _, _, m1, _, _, _ = parse_uxc_string_pack_slots(uxc_packs[f"string_{lang}.uxc"])
            _, _, m2, _, _, _ = parse_uxc_string_pack_slots(uxc_packs[f"string_{lang}_2.uxc"])
            lang_maps[lang] = {1: m1, 2: m2}
        from fx3_firmware_lab.global_xdb_and_menu_tree_auditor import _load_cmn_slot_set

        cmn_sets = {}
        for fn in ("image_00_169.uxc", "style_cmn.uxc", "lang_cmn.uxc", "color_cmn.uxc"):
            ns_id, sset = _load_cmn_slot_set(uxc_packs[fn])
            cmn_sets[ns_id] = sset
        return fx["appfw_bytes"], lang_maps, cmn_sets

    def test_17_clean_room_128_page_elf64_audit_passes(self) -> None:
        appfw_bytes, lang_maps, cmn_sets = self._load_clean_room_parsed()
        rep = audit_128_page_multilingual_menu_tree(
            appfw_bytes,
            lang_maps,
            cmn_sets,
            source_mode="SYNTHETIC_CLEAN_ROOM",
        )
        self.assertTrue(rep.valid, msg=f"Errors: {rep.errors}")
        self.assertEqual(rep.pages_audited, 128)
        self.assertEqual(rep.total_descriptor_rows, 2224)
        self.assertEqual(rep.null_proto_hazards, 0)
        self.assertEqual(rep.null_name_hazards, 0)
        self.assertEqual(rep.missing_resids_total, 0)

    def test_18_missing_simplified_chinese_label_fails_audit(self) -> None:
        appfw_bytes, lang_maps, cmn_sets = self._load_clean_room_parsed()
        # Delete User category (0x02004208 -> ns=2, idx=0x0208) from Simplified Chinese
        del lang_maps["simplifiedchinese"][2][0x0208]
        rep = audit_128_page_multilingual_menu_tree(
            appfw_bytes,
            lang_maps,
            cmn_sets,
            source_mode="SYNTHETIC_CLEAN_ROOM",
        )
        self.assertFalse(rep.valid)
        self.assertTrue(any("Category 0 (User)" in e for e in rep.errors))

    def test_19_missing_japanese_assignable_button_label_fails_audit(self) -> None:
        appfw_bytes, lang_maps, cmn_sets = self._load_clean_room_parsed()
        # Delete Assignable Button title (0x0200211e -> ns=1, idx=0x011e) from Japanese
        del lang_maps["japanese"][1][0x011E]
        rep = audit_128_page_multilingual_menu_tree(
            appfw_bytes,
            lang_maps,
            cmn_sets,
            source_mode="SYNTHETIC_CLEAN_ROOM",
        )
        self.assertFalse(rep.valid)
        self.assertFalse(rep.assignable_p10_page110_verified)

    def test_20_null_descriptor_proto_triggers_null_pointer_hazard(self) -> None:
        appfw_bytes, lang_maps, cmn_sets = self._load_clean_room_parsed()
        mut = bytearray(appfw_bytes)
        # Page 110 base_va = 0x02EB75F0, load_vaddr = 0x02E90000, load_file_off = 0x1000
        p110_off = 0x1000 + (0x02EB75F0 - 0x02E90000)
        struct.pack_into("<Q", mut, p110_off, 0)  # Null prototype pointer!
        rep = audit_128_page_multilingual_menu_tree(
            bytes(mut),
            lang_maps,
            cmn_sets,
            source_mode="SYNTHETIC_CLEAN_ROOM",
        )
        self.assertFalse(rep.valid)
        self.assertEqual(rep.null_proto_hazards, 1)

        preds = evaluate_fx3_hardware_predicates(bytes(mut), lang_maps, rep)
        self.assertTrue(all(p.null_pointer_hazard for p in preds))

    def test_21_missing_appfw_marker_flags_predicate_hazard(self) -> None:
        appfw_bytes, lang_maps, cmn_sets = self._load_clean_room_parsed()
        rep = audit_128_page_multilingual_menu_tree(
            appfw_bytes,
            lang_maps,
            cmn_sets,
            source_mode="SYNTHETIC_CLEAN_ROOM",
        )
        mut = appfw_bytes.replace(b"set_nd_filter_mode_i", b"set_xx_filter_mode_i")
        preds = evaluate_fx3_hardware_predicates(mut, lang_maps, rep)
        nd_pred = next(p for p in preds if p.predicate_id == "VARIABLE_ND")
        self.assertFalse(nd_pred.valid)
        self.assertFalse(nd_pred.appfw_marker_found)
        self.assertTrue(nd_pred.missing_widget_hazard)

    def test_22_directory_constants_pinned_to_128_pages_and_30_assignables(self) -> None:
        self.assertEqual(len(FX6_128_PAGE_DIRECTORY), 128)
        self.assertEqual([p[0] for p in FX6_128_PAGE_DIRECTORY], list(range(128)))
        self.assertEqual(sum(p[3] for p in FX6_128_PAGE_DIRECTORY), 2224)
        self.assertEqual(len(BIG6_CELL_TITLES), 6)
        self.assertEqual(len(ASSIGNABLE_PAGE_110_POOL), 30)


class TestCliAndIntegrationPhase46(unittest.TestCase):
    def test_23_env_force_clean_room_respected(self) -> None:
        with patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}):
            rep = analyze_global_xdb_and_menu_tree()
        self.assertTrue(rep.all_checks_passed)
        self.assertEqual(rep.mode, "CLEAN_ROOM_SYNTHETIC_VERIFIED")
        self.assertEqual(rep.menu_tree_audit.pages_audited, 128)

    def test_24_cli_audit_xdb_menu_clean_room_in_process(self) -> None:
        buf = StringIO()
        with redirect_stdout(buf):
            rc = cli_main(["audit-xdb-menu", "--clean-room"])
        self.assertEqual(rc, 0)
        data = json.loads(buf.getvalue())
        self.assertTrue(data["all_checks_passed"])
        self.assertEqual(data["mode"], "CLEAN_ROOM_SYNTHETIC_VERIFIED")
        self.assertEqual(data["schema_version"], PHASE_46_SCHEMA)

    def test_25_run_audit_all_includes_all_8_auditors(self) -> None:
        all_res = run_audit_all(clean_room=True)
        self.assertTrue(all_res["all_checks_passed"])
        expected_keys = {
            "ufu_container_audit",
            "haita_bk4_feature_audit",
            "uxc_ldec_asset_audit",
            "uxc_multilang_and_font_audit",
            "sensor_codec_compatibility_audit",
            "cube_lut_and_rtmd_audit",
            "wbi_hibdrv_and_elf_abi_audit",
            "global_xdb_and_menu_tree_audit",
        }
        self.assertTrue(expected_keys.issubset(set(all_res.keys())))
        self.assertTrue(all_res["global_xdb_and_menu_tree_audit"]["all_checks_passed"])

    def test_26_cli_audit_xdb_menu_subprocess_deterministic(self) -> None:
        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env["FX3_FX6_FORCE_CLEAN_ROOM"] = "1"
        env["PYTHONPATH"] = str(PKG_ROOT)
        p1 = subprocess.run(
            [sys.executable, "-B", "-m", "fx3_firmware_lab", "audit-xdb-menu", "--clean-room"],
            capture_output=True,
            text=True,
            env=env,
            check=True,
        )
        p2 = subprocess.run(
            [sys.executable, "-B", "-m", "fx3_firmware_lab", "audit-xdb-menu", "--clean-room"],
            capture_output=True,
            text=True,
            env=env,
            check=True,
        )
        self.assertEqual(p1.stdout, p2.stdout)
        parsed = json.loads(p1.stdout)
        self.assertTrue(parsed["all_checks_passed"])
        self.assertNotIn("b'", p1.stdout)

    def test_27_strict_o_rdonly_and_immutable_sqlite_in_module(self) -> None:
        mod_path = PKG_ROOT / "fx3_firmware_lab" / "global_xdb_and_menu_tree_auditor.py"
        src = mod_path.read_text(encoding="utf-8")
        self.assertIn("os.O_RDONLY", src)
        self.assertIn("mode=ro&immutable=1", src)
        self.assertNotIn("os.O_RDWR", src)
        self.assertNotIn("os.O_WRONLY", src)
        self.assertNotIn("subprocess.", src)

    def test_28_clean_room_active_report_matches_schema_contract(self) -> None:
        rep = analyze_global_xdb_and_menu_tree(clean_room=True)
        self.assertTrue(rep.all_checks_passed)
        self.assertEqual(rep.menu_tree_audit.source_mode, "SYNTHETIC_CLEAN_ROOM")
        self.assertEqual(len(rep.menu_tree_audit.sample_pages), 17)
        self.assertTrue(all(sp.valid for sp in rep.menu_tree_audit.sample_pages))


if __name__ == "__main__":
    unittest.main()
