# Phase 49 — 128-Page Instant Menu Search & Jump Catalog, Live `EN/ZH/JA` `GPE0` Pixel-Diff Verifier & HTTP Socket Reset Hardening (`--port 18773`)

- **Date**: 2026-11-14
- **Lane / Worker**: Hydrogen-42 (`h42-phase49-vm-trial-search-socket-hardening`)
- **Isolated Verification Port**: `127.0.0.1:18773` (port-scoped workdir `/private/tmp/fx6-live-gpe0-run-18773`, runner PID `69820`, QEMU PID `69849`, cleanly stopped after verification; live user session on port `8768` untouched)
- **Live QEMU Kernel/Guest**: `LIVE_GPE0_READY` in `52.38s` (`nz=357888`, `text_ok=32`, `available_langs=["en", "zh", "ja"]`), strictly preserving 100% backward compatibility with Phases 19, 23, 30, and 40.

## Summary of Implemented Deliverables

1. **Zero-Traceback HTTP Client Disconnect Hardening (`HardenedThreadingHTTPServer` & `make_handler`)**
   - Added `CLIENT_DISCONNECT_ERRNOS` (`EPIPE`, `ECONNRESET`, `ECONNABORTED`, `ETIMEDOUT`, `ENOTCONN`, `ESHUTDOWN`), `_is_client_disconnect_exc()`, and `HardenedThreadingHTTPServer` overriding `handle_error()` in [run_fx6_menu_trial.py](../../outputs/fx3-vm-trial/run_fx6_menu_trial.py).
   - Wrapped `handle_one_request()`, `finish()`, `_safe_send_error()`, `_send_bytes()`, `_send_json()`, `do_GET()`, and `do_POST()` (plus `Handler.timeout = 15.0` and malformed `Content-Length` handling) so rapid browser refreshes, aborted `/frame.png` / `/api/frame.png` fetches, or truncated `POST` bodies close cleanly and increment `socket_disconnect_count` / `server.client_disconnects` with zero `Exception occurred during processing of request` stack traces on stderr.

2. **11-Category / 128-Page Bilingual (`中文` + `EN`) Menu Catalog & Instant Search/Jump Bar (`GET /api/menu_catalog`, `POST /api/jump_page`)**
   - Added `MENU_CATEGORIES_BILINGUAL` (all 11 FX6 categories), `FLAGSHIP_MENU_CATALOG` (15 flagship pages including `Big-6 Home`, `Shooting -> Cine EI / S&Q / Shutter`, `Project -> Base Look / Rec Format`, `Paint/Look -> User 3D LUT`, `TC/Media -> Dual CFexpress Slot`, `Monitoring -> Output / Display`, `Audio -> XLR-H1 4ch`, `Thumbnail`, `Technical -> P4 ND Lock / IBIS`, `Network -> P12 Airplane Guard`, `Maintenance -> Version`, and `Assignable Buttons Page 110`), plus curated bilingual metadata and classification for all 128 `fx6_all_pages[0..127]` entries (`154` total catalog entries).
   - Added `build_menu_catalog()` and relevance-ranked `search_menu_catalog()` (supporting English, Chinese, hex offsets, and category filters) exposed via `GET /api/menu_catalog` (with `?q=` / `?query=` / `?category=`) and `POST /api/jump_page` (jumping by `page_id`, `idx128`, bilingual `query`/`q`, `menu_cat`, or `page`).
   - Added `🔍 搜索菜单 / Quick Jump (128 Pages)` filter box, category dropdown, 14 one-click jump pills, and filtered result jump list inside `HTML_UI`.

3. **Deterministic On-Demand Multilingual (`EN` vs `ZH` vs `JA`) In-Guest `GPE0` Diff Verifier (`POST /api/verify_multilang_diff`, `GET /api/verify_multilang_diff`)**
   - Added `compute_gpe0_frame_diff()` and `FX6LiveGpe0Session.verify_multilang_diff(page=None)` plus the `驗 / Verify EN-ZH-JA GPE0` button and `#multilang-diff-readout` status box in `HTML_UI`.
   - Switches `en -> zh -> ja` in-guest (restoring the user's prior language and page in `finally:` even on error), captures raw `1024x540` `GPE0` (`0x41e001000`, `2,211,840` bytes) frames, computes exact SHA-256 digests and pairwise byte/pixel deltas (`en_vs_zh_diff_bytes > 0`, `zh_vs_ja_diff_bytes > 0`, `en_vs_ja_diff_bytes > 0`), and asserts monotonic `ack_seq`. Fails closed with `missing_lang_packs` (`400`) in clean-room mode and `vm_not_ready` (`409`) when QEMU is stopped.

## Isolated Live QEMU Verification (`--port 18773`)

### Socket Reset / Broken Pipe Stress Audit
- Executed abrupt `SO_LINGER(1, 0)` socket resets on `/frame.png`, `/api/frame.png`, `/api/status`, and a truncated `POST /api/jump_page` payload while QEMU was live on `127.0.0.1:18773`:
  - `socket_disconnect_count = 2`
  - Runner log audit (`log_lines = 3`): `has_traceback = false`, `has_http_request_exception = false`, `has_broken_pipe_trace = false`, `has_conn_reset_trace = false`, `has_appfw_segv = false`.

### Catalog Search & Live `/api/jump_page` Results
- `GET /api/menu_catalog`: `total_categories = 11`, `total_pages_128 = 128`, `total_entries = 154`, `quick_jump_pills = 14`.
- `GET /api/menu_catalog?q=LUT`: `7` matches; `GET /api/menu_catalog?q=卡槽`: `3` matches.

| Jump Request | Resolved `page_id` | Page / Cat | `ack_seq` | `gpe0_nonzero_px` | `text_ok` | `1024x540` PNG Size / SHA-256 (`[0:16]`) |
|---|---|---|---:|---:|---:|---|
| `{"page_id": "cat_2_shooting"}` | `cat_2_shooting` | `p1 / cat=2` | `2` | `461,136` | `20` | `26,298 B` / `f8a4c7fecb553b24` |
| `{"page_id": "cat_4_paint_look"}` | `cat_4_paint_look` | `p1 / cat=4` | `3` | `461,136` | `19` | `24,551 B` / `29b5926391699b4e` |
| `{"page_id": "assignable_p110"}` | `assignable_p110` | `p4` | `4` | `435,494` | `33` | `34,024 B` / `a14bce5748dcce84` |
| `{"page_id": "network_p12_guard"}` | `network_p12_guard` | `p5` | `5` | `461,624` | `31` | `19,990 B` / `73f0b60c1ef50c9b` |
| `{"idx128": 110}` | `p128_110` | `p24 (idx128=110)` | `6` | `461,624` | `3` | `10,328 B` / `a6d7af7aebac1324` |
| `{"query": "XLR-H1"}` | `tc_audio_meter_4ch` | `p17` | `7` | `333,680` | `9` | `13,629 B` / `085eb40e4c3c5796` |
| `{"page_id": "big6_home"}` | `big6_home` | `p0` | `8` | `357,888` | `32` | `25,970 B` / `6205d6a1813cc467` |

### Live In-Guest `EN -> ZH -> JA` `GPE0` Pixel-Diff Receipts (Starting From `lang="zh"` -> Restored `"zh"`)

1. **Three-Layer Menu (`page=1`)** (`ack_seq`: `9 -> 10 -> 11 -> 12 -> 13`, `ack_seq_monotonic = true`, `restored_lang = "zh"`):
   - `en` (`seq=10`, `nz=461,136`): `sha256 = f0e3f093d55094a4761f13ca4a139753e1aeae6babbeeaa86acddd291c512144`
   - `zh` (`seq=11`, `nz=461,136`): `sha256 = 7a72f75b0a594a9bf444dd2d857e5113272612052461004c880122976fbce30d`
   - `ja` (`seq=12`, `nz=461,136`): `sha256 = e181562c08c495a6cc903cc1a2a508eb0d092067fbe78af5217c7c392ba0078d`
   - Pairwise deltas: `en_vs_zh_diff_bytes = 108,064` (`31,242 px`), `zh_vs_ja_diff_bytes = 71,704` (`20,816 px`), `en_vs_ja_diff_bytes = 95,131` (`27,527 px`), `all_distinct = true`.

2. **Big-6 Home (`page=0`)** (`ack_seq`: `13 -> 14 -> 15 -> 16 -> 17`, `ack_seq_monotonic = true`, `restored_lang = "zh"`):
   - `en` (`seq=14`, `nz=357,888`): `sha256 = 99c4dfa35a3f04d562a3978bcee6fd5de582d15b4c02b446774acf0ba792e8d5`
   - `zh` (`seq=15`, `nz=357,888`): `sha256 = 60f3b64bb26b169dcbc943d0f18fc53dad79ce5056d13622e85745c94dbf1560`
   - `ja` (`seq=16`, `nz=357,888`): `sha256 = 8209c4e849e859808c5672517ae516085c3c2022c26c3f4be15f8cd2ef2104de`
   - Pairwise deltas: `en_vs_zh_diff_bytes = 79,962` (`26,654 px`), `zh_vs_ja_diff_bytes = 34,308` (`11,436 px`), `en_vs_ja_diff_bytes = 77,652` (`25,884 px`), `all_distinct = true`.

- Final live check: `ack_seq == cmd_seq == 18`, `crashed = false`, `0` tracebacks, port `18773` & PIDs `69820` / `69849` confirmed cleanly terminated.

## Dual-Mode Automated Tests (`outputs/fx3-vm-trial/tests/test_vm_trial.py`)

- Expanded from `59` to **`81` unit tests** (`+22` new tests in `TestPhase49MenuCatalogMultilangDiffAndSocketHardening`).
- **Local Donor Mode**: `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-vm-trial /usr/bin/python3 -B -m unittest outputs/fx3-vm-trial/tests/test_vm_trial.py` -> **81 tests in 4.203s OK**.
- **Clean-Room Mode**: `FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-vm-trial /usr/bin/python3 -B -m unittest outputs/fx3-vm-trial/tests/test_vm_trial.py` -> **81 tests in 4.119s OK**.
