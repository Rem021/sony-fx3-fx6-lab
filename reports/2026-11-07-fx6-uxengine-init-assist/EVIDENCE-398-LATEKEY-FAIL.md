# Evidence 398 — late MENU key injection fails; no native paint

Date: 2026-11-07 (PST) · Runtime line: DeepSeek (handoff)
Candidate: **398** `...grmreal395-skiplock.cpio` (same payload as 395), runner
`run_gpecap25_398_latekey.py`
Run: **`cp-bind-0bd36667`** (600 s, completed)
Purpose: move the MENU/DOWN/SET/RIGHT injection from 35 s to **90 s** (after the
presenter/UI init) and see whether native input triggers the first paint.

## 1. Result

- The key thread failed before writing anything:
  `keyinject-error.txt` = `FileNotFoundError(2, 'No such file or directory')`.
- No `FX3_KEY96_DOWN` / `FX3_NATIVE_KEY_RECV` / `FX3_KEY96_UP` appears in the serial.
- `gpe0.bin` (50 s) and `gpe0-late.bin` (510 s) are both **2,211,840 B, all zero**
  (1 unique value).
- The presenter path still runs (same 395 payload), and AppFw still idles in
  `osal_rcv_msg_tmo`.

## 2. Why the key gate cannot wake the native UI

`InputGate` (from `menu-repair-01/runtime/gate_input96.py`) is not a file protocol; it
connects to QEMU’s **gdb chardev socket** and writes 12 bytes at guest physical
`0x41df00008`. The shim’s `poll_key_gate()` reads that mailbox, but it is called only from
`flush_pixels_to_osd()` — the **software compatibility renderer**, which is inactive on
the native path. So even a successful mailbox write would not be seen by the native
`I-InputEvent` threads.

The `FileNotFoundError` itself is the gdb socket path missing at injection time (the
chardev socket is transient and the runner’s client lifecycle can remove it); this is a
second, independent reason the late-key experiment cannot work as written.

## 3. Consequence for the goal

The remaining trigger must be an **OSAL/IPC message** or a **GRM screen-update job**, not
the shim mailbox. The next step is to interpose the OSAL message API
(`osal_snd_msg`, `osal_rcv_msg_tmo`, `osal_reg_msg_queue_cb`,
`osal_valloc_msg_wait`) inside the guest and observe the UI queue, then synthesize the
screen-update message.

## 4. Artifacts

| Item | Value |
|---|---|
| run 398 | `cp-bind-0bd36667`, serial 1,560,309 B, SHA-256 `78cec6a245db62bcecdbbaa734c01b7af14a7d4930fb30ceb07ea2b418bb7aa9`, reason `wall_timeout` |
| gpe0 | 50 s and 510 s: all zero |
| key error | `FileNotFoundError(2, 'No such file or directory')` |

Durable copies in `work/fx6-385-17b9f-calltrace-20261107/`
(`serial-398.log`, `run-receipt-398.json`, `vm-candidate-gpecap25-398-latekey.json`,
`run_gpecap25_398_latekey.py`).
