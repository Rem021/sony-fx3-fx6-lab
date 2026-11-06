# 57项覆盖矩阵

所有行的完整调用约定/枚举/间接被调者/所有权仍未通过；条目链接是原码证据，不是适配许可。

| symbol | FX3→FX6 offset | FX6入口/零槽 | FX3 GOT窗口数 | FX6首基本块输入读取offset | 状态 |
|---|---|---|---|---|---|
| _ZN3mpr19gp_evtPbCamInfoFuncE | 0x98→0x98 | [0x212a038](fx6_ap-212a038.txt) | 4 | 0x4 | UNKNOWN |
| _ZN3mpr19gp_evtPbGpsInfoFuncE | 0xa0→0xa0 | [0x2128858](fx6_ap-2128858.txt) | 4 | 未见/见分支后unknown | LEAF_NO_MEMORY_ACCESS; full consumer contract UNKNOWN |
| _ZN3mpr19gp_evtRecPbTimeFuncE | 0x130→0x168 | [0x212b720](fx6_ap-212b720.txt) | 3 | 0x4 | UNKNOWN |
| _ZN3mpr22gp_evtEditFinishedFuncE | 0x140→0x178 | [0x213c17c](fx6_ap-213c17c.txt) | 3 | 0x0 | UNKNOWN |
| _ZN3mpr22gp_evtEditProgressFuncE | 0x138→0x170 | [0x2129824](fx6_ap-2129824.txt) | 3 | 0x14, 0x4 | UNKNOWN |
| _ZN3mpr22gp_evtLoadFinishedFuncE | 0x18→0x18 | [0x213ce24](fx6_ap-213ce24.txt) | 4 | 0x0 | UNKNOWN |
| _ZN3mpr24gp_evtInternalPbStopFuncE | 0xe0→0xe0 | [0x2129468](fx6_ap-2129468.txt) | 4 | 0x10 | UNKNOWN |
| _ZN3mpr24gp_evtPbStopFinishedFuncE | 0xb8→0xb8 | [0x213c7ac](fx6_ap-213c7ac.txt) | 4 | 0x0 | UNKNOWN |
| _ZN3mpr24gp_evtRepairFinishedFuncE | 0x168→0x1a0 | [0x213bee8](fx6_ap-213bee8.txt) | 3 | 0x0 | UNKNOWN |
| _ZN3mpr24gp_evtRepairProgressFuncE | 0x160→0x198 | [0x212942c](fx6_ap-212942c.txt) | 3 | 0x4, 0x8 | UNKNOWN |
| _ZN3mpr24gp_evtUnloadFinishedFuncE | 0x20→0x20 | [0x213cd74](fx6_ap-213cd74.txt) | 4 | 0x0 | UNKNOWN |
| _ZN3mpr25gp_evtAudioRecStartedFuncE | 0xe8→0xe8 | zero (bounded input) | 4 | n/a | UNKNOWN; producer slot remains zero for bounded valid input, not automatically compatible |
| _ZN3mpr25gp_evtAudioRecStoppedFuncE | 0xf0→0xf0 | zero (bounded input) | 4 | n/a | UNKNOWN; producer slot remains zero for bounded valid input, not automatically compatible |
| _ZN3mpr25gp_evtExitRecFinishedFuncE | 0x40→0x40 | [0x2139aa8](fx6_ap-2139aa8.txt) | 4 | 0x0 | UNKNOWN |
| _ZN3mpr25gp_evtInternalPbPauseFuncE | 0xd8→0xd8 | [0x212949c](fx6_ap-212949c.txt) | 4 | 未见/见分支后unknown | UNKNOWN |
| _ZN3mpr25gp_evtMovieRecStartedFuncE | 0x48→0x48 | [0x213cca4](fx6_ap-213cca4.txt) | 4 | 0x0 | UNKNOWN |
| _ZN3mpr25gp_evtMovieRecStoppedFuncE | 0x50→0x50 | [0x213cc0c](fx6_ap-213cc0c.txt) | 3 | 0x0 | UNKNOWN |
| _ZN3mpr25gp_evtPbPauseFinishedFuncE | 0xc8→0xc8 | [0x212885c](fx6_ap-212885c.txt) | 4 | 未见/见分支后unknown | LEAF_NO_MEMORY_ACCESS; full consumer contract UNKNOWN |
| _ZN3mpr25gp_evtPbStartFinishedFuncE | 0xb0→0xb0 | [0x213c854](fx6_ap-213c854.txt) | 4 | 0x0 | UNKNOWN |
| _ZN3mpr25gp_evtPowerOnFinishedFuncE | 0x150→0x188 | [0x213c064](fx6_ap-213c064.txt) | 3 | 0x0 | UNKNOWN |
| _ZN3mpr25gp_evtRecoveryStartedFuncE | 0x170→0x1a8 | [0x21293f8](fx6_ap-21293f8.txt) | 3 | 0x4 | UNKNOWN |
| _ZN3mpr26gp_evtEnterRecFinishedFuncE | 0x38→0x38 | [0x2139b24](fx6_ap-2139b24.txt) | 3 | 0x0 | UNKNOWN |
| _ZN3mpr26gp_evtPbChangedContentFuncE | 0xa8→0xa8 | [0x212f278](fx6_ap-212f278.txt) | 4 | 0x14, 0x8, 0x10, 0x14, 0x18 | UNKNOWN |
| _ZN3mpr26gp_evtPowerOffFinishedFuncE | 0x148→0x180 | [0x213c0f0](fx6_ap-213c0f0.txt) | 3 | 0x0 | UNKNOWN |
| _ZN3mpr26gp_evtRecoveryFinishedFuncE | 0x178→0x1b0 | [0x21293bc](fx6_ap-21293bc.txt) | 3 | 0x4, 0x8 | UNKNOWN |
| _ZN3mpr27gp_evtLoadMovieFinishedFuncE | 0x10→0x10 | [0x213cf38](fx6_ap-213cf38.txt) | 4 | 0x0 | UNKNOWN |
| _ZN3mpr27gp_evtLoadStillFinishedFuncE | 0x8→0x8 | [0x212954c](fx6_ap-212954c.txt) | 4 | 0xc, 0x8 | UNKNOWN |
| _ZN3mpr28gp_evtAudioWriteFinishedFuncE | 0x100→0x100 | [0x2128864](fx6_ap-2128864.txt) | 4 | 未见/见分支后unknown | LEAF_NO_MEMORY_ACCESS; full consumer contract UNKNOWN |
| _ZN3mpr28gp_evtMovieWriteFinishedFuncE | 0x60→0x60 | [0x213ca24](fx6_ap-213ca24.txt) | 4 | 0x0 | UNKNOWN |
| _ZN3mpr28gp_evtResetNecessityInfoFuncE | 0x180→0x1b8 | [0x2129380](fx6_ap-2129380.txt) | 3 | 0x4, 0x8 | UNKNOWN |
| _ZN3mpr28gp_evtStillWriteFinishedFuncE | 0x80→0x80 | [0x213c8d8](fx6_ap-213c8d8.txt) | 4 | 0x4 | UNKNOWN |
| _ZN3mpr29gp_evtAudioPbStopFinishedFuncE | 0x118→0x118 | zero (bounded input) | 3 | n/a | UNKNOWN; producer slot remains zero for bounded valid input, not automatically compatible |
| _ZN3mpr29gp_evtMovieRecAutoDividedFuncE | 0x78→0x78 | [0x212d9fc](fx6_ap-212d9fc.txt) | 4 | 0x76c, 0xc, 0x4, 0x8, 0x770, 0x76c | UNKNOWN |
| _ZN3mpr29gp_evtStillWriteCountdownFuncE | 0x88→0x88 | [0x213bce4](fx6_ap-213bce4.txt) | 2 | 0x4 | UNKNOWN |
| _ZN3mpr30gp_evtAudioPbPauseFinishedFuncE | 0x120→0x120 | zero (bounded input) | 3 | n/a | UNKNOWN; producer slot remains zero for bounded valid input, not automatically compatible |
| _ZN3mpr30gp_evtAudioPbStartFinishedFuncE | 0x108→0x108 | zero (bounded input) | 4 | n/a | UNKNOWN; producer slot remains zero for bounded valid input, not automatically compatible |
| _ZN3mpr30gp_evtMovieRecMediaChangedFuncE | 0x70→0x70 | [0x2129958](fx6_ap-2129958.txt) | 4 | 0x8, 0xc, 0x10 | UNKNOWN |
| _ZN3mpr30gp_evtMovieRecReelNoUpdateFuncE | 0x1a0→0x238 | zero (bounded input) | 2 | n/a | UNKNOWN; producer slot remains zero for bounded valid input, not automatically compatible |
| _ZN3mpr31gp_evtAllMovieWriteFinishedFuncE | 0x68→0x68 | [0x21294f8](fx6_ap-21294f8.txt) | 4 | 0x4 | UNKNOWN |
| _ZN3mpr31gp_evtGetRepairTimeFinishedFuncE | 0x158→0x190 | [0x213bfc0](fx6_ap-213bfc0.txt) | 3 | 0x0 | UNKNOWN |
| _ZN3mpr31gp_evtMovieRecStatusChangedFuncE | 0x28→0x28 | [0x214187c](fx6_ap-214187c.txt) | 3 | 0x4, 0x8, 0x9, 0x0 | UNKNOWN |
| _ZN3mpr31gp_evtStillRecStatusChangedFuncE | 0x30→0x30 | [0x212952c](fx6_ap-212952c.txt) | 4 | 未见/见分支后unknown | UNKNOWN |
| _ZN3mpr32gp_evtInternalAudioPbStoppedFuncE | 0x110→0x110 | zero (bounded input) | 3 | n/a | UNKNOWN; producer slot remains zero for bounded valid input, not automatically compatible |
| _ZN3mpr32gp_evtMovieRecFileNameUpdateFuncE | 0x1b8→0x240 | [0x2129360](fx6_ap-2129360.txt) | 2 | 未见/见分支后unknown | UNKNOWN |
| _ZN3mpr32gp_evtPbPauseReleaseFinishedFuncE | 0xd0→0xd0 | [0x2128860](fx6_ap-2128860.txt) | 4 | 未见/见分支后unknown | LEAF_NO_MEMORY_ACCESS; full consumer contract UNKNOWN |
| _ZN3mpr32gp_evtReadStillImageFinishedFuncE | 0xc0→0xc0 | [0x213c408](fx6_ap-213c408.txt) | 4 | 0x0 | UNKNOWN |
| _ZN3mpr32gp_evtStillTransferDataBuiltFuncE | 0x188→0x1c0 | [0x2139368](fx6_ap-2139368.txt) | 3 | 0x4 | UNKNOWN |
| _ZN3mpr33gp_evtInternalAudioRecStoppedFuncE | 0xf8→0xf8 | zero (bounded input) | 4 | n/a | UNKNOWN; producer slot remains zero for bounded valid input, not automatically compatible |
| _ZN3mpr33gp_evtInternalMovieRecStoppedFuncE | 0x58→0x58 | [0x2129658](fx6_ap-2129658.txt) | 3 | 0x8, 0x4, 0x20 | UNKNOWN |
| _ZN3mpr36gp_evtSetClipStatusInRecFinishedFuncE | 0x1a8→0x228 | [0x213ba30](fx6_ap-213ba30.txt) | 2 | 0x0 | UNKNOWN |
| _ZN3mpr37gp_evtAudioPbPauseReleaseFinishedFuncE | 0x128→0x128 | zero (bounded input) | 3 | n/a | UNKNOWN; producer slot remains zero for bounded valid input, not automatically compatible |
| _ZN3mpr37gp_evtSetClipStatusInPlayFinishedFuncE | 0x1b0→0x230 | [0x213bab4](fx6_ap-213bab4.txt) | 2 | 0x0 | UNKNOWN |
| _ZN3mpr37gp_evtSetEssenceMarkInRecFinishedFuncE | 0x190→0x1c8 | [0x213be64](fx6_ap-213be64.txt) | 4 | 0x0 | UNKNOWN |
| _ZN3mpr38gp_evtSetEssenceMarkInPlayFinishedFuncE | 0x198→0x1d0 | [0x213bde0](fx6_ap-213bde0.txt) | 4 | 0x0 | UNKNOWN |
| _ZN3mpr38gp_evtStillRecPriorityMediaChangedFuncE | 0x90→0x90 | [0x21294bc](fx6_ap-21294bc.txt) | 4 | 0x4, 0x8 | UNKNOWN |
| _ZN3mpr39gp_evtCheckDigitalSignatureFinishedFuncE | 0x1c0→0x248 | zero (bounded input) | 2 | n/a | UNKNOWN; producer slot remains zero for bounded valid input, not automatically compatible |
| _ZN3mpr49gp_evtGetDigitalSignatureInfoForMovieFinishedFuncE | 0x1c8→0x250 | zero (bounded input) | 2 | n/a | UNKNOWN; producer slot remains zero for bounded valid input, not automatically compatible |
