# Project Charter — Plateworks ShutterLock

_Chartered 2026-10-14, the day the project started. The plan it follows is `docs/superpowers/plans/2026-10-14-a7s-iii-feature-research.md`._

## What it is

A published map of what the Sony A7S III firmware carries and how each feature is gated, made by reading the firmware and the camera's settings table. The first targets are shutter angle and Cine EI, both shipped on the FX3, which shares the A7S III's sensor and BIONZ XR processor. The map says, for each feature: present or absent, flag-gated or code-gated, with an evidence address.

It is a Plateworks Tools property. The register is a research notebook: evidence, procedures, and a feature table, written for an A7S III owner who wants to know what is possible before touching their camera.

It is not a firmware distributor. The repo never holds Sony firmware, decryption keys, camera backups, or serial numbers.

## Why

In 2026-09 and 2026-10 three public efforts opened the BIONZ XR platform: the update files decrypt, the A7 IV has a hardware recovery door, and one settings byte shows the shutter-angle icon on an A7 IV. Nobody has run any of it on an A7S III. The gap is the map.

## Vision / done state

**Milestone 1, the map:** the feature table for the A7S III 5.01 firmware, diffed against the FX3, plus the camera's settings-table inventory. Published.

**Milestone 2, flag-gated features on Dom's camera:** each flag-gated feature switched on, tested, and restored, with screenshots.

**Milestone 3, code-gated features:** only on a second body or with a proven A7S III recovery path. Its own plan, later. Not assumed.

## The gate

Dom's A7S III is the camera that shoots the prints, and it is the only one. Nothing writes to it until the feature is shown to be flag-gated and the restore procedure is written. Code-gated features stop at the gate. That rule is in the plan and in `CLAUDE.md`, and it does not move.

## Current status (2026-10-15): parked

Parked on 2026-10-15 by Dom's decision. The first-pass findings are the useful output, and the next step, the dial-guard trace, could not be completed. The local checkout was removed; this repo is the whole record. To resume, clone it and rebuild `tools/`, `firmware/` and `decrypted/` with the steps in `README.md`.

### Status on 2026-10-14


Task 1 first pass done. Both update files are decrypted, and `docs/feature-table.md` holds the first feature table. The A7S III runs as its own product class, `OT_UUD`, not the FX3's `ALCIN_UUD`. Shutter-angle display and de-squeeze are flag-gated candidates. Cine EI is probably code-gated through the base-sensitivity menu rule. Angle control by dial is unknown until an instruction-level trace. Task 2, the read-only camera inventory, is next.

## Location & filing

- **Repo folder:** `20-29 Properties/29 Plateworks ShutterLock/`
- **GitHub:** `domalhambra/plateworks-shutterlock`, public.
- **Workspace filing:** Projects table row in the workspace `CLAUDE.md`; `local` row in `00-09 System/01 Docs/allowlist-ledger.md`; JDex row 29.
- **Number 29** was registered for Plateworks Payment Links for one commit on 2026-10-13 and withdrawn before any folder existed. No document ever cited a folder 29, so the number was free.

## Tooling

Python 3 · `fwtool.py` on the CXD90057 branch (pull request 52) for update decryption · `Sony-PMCA-RE` for service mode · Ghidra for disassembly. The tool clones and the decrypted trees live outside the repo and are gitignored by path.

## Verification gates

- A feature-table row counts only with an evidence address. No address means "unknown", never "absent".
- A settings backup is saved twice and the hashes match before any read is trusted.
- A write to the camera is followed by a restore, confirmed by a read, before the next write.
- `scripts/docs_check.py` runs in the test run.

## Milestones

- [x] Charter filed, folder 29 created — 2026-10-14
- [x] Task 0: both update files decrypted and unpacked — 2026-10-14
- [x] Task 1, first pass: the feature table with evidence addresses — 2026-10-14
- [ ] Task 1, second pass: instruction-level traces of the dial guard and the `OT_UUD` menu catalogue
- [ ] Task 2: the settings-table inventory from the camera, read-only
- [ ] Task 3: the gate decision
- [ ] Task 4: flag-gated features switched on and restored, with screenshots
- [ ] Task 6: repo public, link posted to the A7 IV repo and the Reddit thread

## Guardrails / principles

- **The only-camera rule.** See The gate.
- **No Sony material in the repo.** No firmware, keys, backups, serial numbers, or decrypted files. The `.gitignore` names the paths and the check enforces the README's claim.
- **Evidence over assertion.** Every claim about the firmware carries an address or a diff.
- **Credit the upstream work.** Every method here was opened by DavidBuchanan314, ma1co, and leogenot. Their repos are named at the top of the README.
