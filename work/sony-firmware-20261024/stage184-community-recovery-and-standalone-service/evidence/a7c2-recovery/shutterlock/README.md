# Plateworks ShutterLock

**Parked since 2026-10-15.** The findings are in `docs/feature-table.md`. To resume, follow Run it below.

A map of what the Sony A7S III firmware carries and how each feature is gated, read from the decrypted update file and from the camera's own settings table. The first targets are shutter angle and Cine EI, both shipped on the FX3, which shares the A7S III's sensor and processor. The register is a research notebook: every claim carries an evidence address. Python 3, Markdown, and three upstream tools.

This repo holds no Sony material. No firmware, no decrypted tree, no key, no camera backup, no serial number. Those live under gitignored paths and never leave the Mac.

The methods here were opened by three people. Read their work first:

- [DavidBuchanan314/ILCE-7M4-RE](https://github.com/DavidBuchanan314/ILCE-7M4-RE): the A7 IV serial boot door and the eMMC keys.
- [ma1co/fwtool.py](https://github.com/ma1co/fwtool.py), pull request 52: BIONZ XR update decryption.
- [leogenot/sony-a7iv-feature-research](https://github.com/leogenot/sony-a7iv-feature-research): the service-mode settings method on the A7 IV.

## Run it

Everything below runs on a Mac with Python 3 and Homebrew. The camera is not needed for the firmware work.

```bash
python3 -m venv venv && ./venv/bin/pip install pycryptodomex pyyaml pyusb asn1crypto tlslite-ng certifi
```

```bash
git clone https://github.com/ma1co/fwtool.py tools/fwtool.py && git -C tools/fwtool.py fetch origin pull/52/head:pr52 && git -C tools/fwtool.py checkout pr52
```

```bash
git clone https://github.com/ma1co/Sony-PMCA-RE tools/Sony-PMCA-RE && brew install libusb
```

Download the update files yourself from Sony's support pages. The file is named `BODYDATA.DAT` for both cameras; keep each in its own folder: `firmware/ilce-7sm3-5.01/` and `firmware/ilme-fx3-7.02/`. Then decrypt:

```bash
./venv/bin/python tools/fwtool.py/fwtool.py unpack -f firmware/ilce-7sm3-5.01/BODYDATA.DAT -o decrypted/ilce-7sm3-5.01
```

## Prove a change

```bash
python3 scripts/docs_check.py --require docs/decisions.md --known-absent tools/ --known-absent firmware/ --known-absent decrypted/ --known-absent backups/
```

A feature-table row counts only with an evidence address. A row with no address is "unknown", never "absent".

## Ship it

There is nothing to deploy. A change is shipped when it is pushed to `main` with its docs: the table row, the decision row, the index row.

## The gate

Nothing writes to the camera until the feature is shown to be flag-gated and the restore procedure is written. Code-gated features stop. The plan says why, and `CLAUDE.md` says it again.

## Where to go next

| Want to | Read |
|---|---|
| See what was found | `docs/feature-table.md` |
| Understand the project | `PROJECT_CHARTER.md` |
| Follow the work | `docs/superpowers/plans/2026-10-14-a7s-iii-feature-research.md` |
| Find any document | `docs/README.md` |
| See what was decided and why | `docs/decisions.md` |
| Work here with an agent | `CLAUDE.md`, then `AGENTS.md` |
