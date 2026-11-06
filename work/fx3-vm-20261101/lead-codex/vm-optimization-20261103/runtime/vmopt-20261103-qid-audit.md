# AP104 / AP105 QID generation audit

Read-only parser: `vmopt-20261103-qid-audit.py` and `vmopt-20261103-gpe-generation.py`; input is each immutable run's original `serial.log`. The scripts select successful dynamic flags `0x2a` allocation by `module=0x82` for GPE, pair by QID **and successive generation**, then read explicit `SendDrawComp` returns and `0x4a` releases. A release can race ahead of the completion function's return in the log, so the order gate is allocation before completion entry and release, not completion return before release. Each `event` is unique within each serial log; no duplicate event lines were found.

| Original run | All dynamic allocations | GPE (`module=0x82`) | Other modules | GPE explicit success / failed | GPE release | Unfetched |
|---|---:|---:|---:|---:|---:|---:|
| AP104 light4save1200 | 219 | 78 | 141 | 77 / 1 | 78 | 1 |
| AP105 vmopt baseline | 323 | 182 | 141 | 182 / 0 | 182 | 0 |

The old `pending_receives=140` is an artifact of treating *all* `0x2a` dynamic allocations as GPE draw batches. Of 141 non-GPE allocations, one record has no usable QID; the other 140 have separate QIDs, principally `module=0x1cf` and other modules. Their `0x4a` releases do not imply `SendDrawComp` and they must not be counted as pending GPE completions. The module 0x82 allocations each have exactly one explicit completion and one dynamic release in AP105; max outstanding GPE completion for each run is one. AP104 generation 77 of QID `0x808261c0` has explicit completion **result=0 errno=1018** after 50.011503008 s, despite a successful release; the original 5000 ms budget was not met. AP105's 182 successful matched generations have maximum allocation-return to completion-return of 2839.466 ms and no missing completion, but this is not a direct `ReceiveDrawComp` entry measurement and does not prove every possible draw will meet 5000 ms.

JSON evidence: `vmopt-20261103-qid-audit-ap104.json`, `vmopt-20261103-qid-audit-ap105.json`, `vmopt-20261103-generations-ap104.json`, `vmopt-20261103-generations-ap105.json`. QID generation is *observed repeated allocation order* within each run, not a native generation field; log gaps and unobserved draws remain unknown. The AP104 and AP105 draw workloads differ.

For the date UI, Sony's [FX3 Ver.2+ Area/Date/Time guide](https://helpguide.sony.net/ilc/2210/v1/en/contents/TP1000843992.html) identifies the menu path; Sony's [control wheel guide](https://helpguide.sony.net/ilc/2210/v1/en/contents/TP1000867591.html) says center press confirms a selection. The observed edit screenshot shows a bottom `● OK` button. A single center ENTER on the unchanged date edit page is the next bounded attempt; its outcome must be read back visually and from native data.
