# AP85 handoff checkpoint 2026-11-02

## Current lifecycle

Task task_bf4f4211be76 / dispatch ctx_ee4f6943c8d7 remains ACTIVE; never worker_done. Worker orca_session_id:6cbe29fd-fb24-4199-bba8-b8ad99383477, Lead claude_9e4c5454_f5cd_4f55_aeef_607246611258. No active QEMU; both locks free, last PID6631 absent. Phase AP85_PARTIAL_OSD_COMPLETION_NEW_0400_AND_PAIR_BLOCK_WAIT_LEAD. Current candidate ap85-osd-software-ring-r4/candidate85-r4.json; preferred healthy baseline remains AP84r2. Final status msg_423d147f816b, newblocks escalations msg_909cd12c6713 (0400), msg_496544a1726b (latepair). Waiting for next Lead instruction; no protocol0400 reply or original-queue ownership change authorized.

## AP85 runs (all immutable)

- ap85osdring-85e55c0e,300s, v42+headlessv1/GPEv14guardv1: failed because headless ahead of capid obscured original CPversion caller identity. Exit0/reaped/unchanged/PIDabsent/locks free; missing many markers.
- ap85r2osdring-58753131,54.39s early stop: only preload order capid beforeheadless plus compact readonly im PID/maps/uptime in existing1s observer loop. Full boot/0152 nativefree0; capture failed−7 because nativebitmap enum1 was wrongly interpreted as GPE1(4B). ZeroACK.
- ap85r3osdring-8ba2cd27, early stop: headlessv2 maps native1/7→GPE0,2/8→GPE1 based original code. Allidentity/size/token/545 pass, but pread /proc/self/mem of nativeReadLock bits failed−8. ZeroACK; actual errno not captured, PFNMAP explanation inference.
- **ap85r4osdring-5dcb8371**,178.983s (300s upper bound, stopped for new0400 synchronous wait): v42+headlessv3+GPEv14guardv1. Exit0/reaped/unchanged/PIDabsent/bothlocksfree/missing[]/no fatal orsymbol error; im.elf endmaps at guestuptime176.62 alive.

## Proven final runtime behavior

0152 exact16B 0d205201100001800300010000eb8080→1152/12B 0d2052110c00018000005900, status590000/pendinghardware1. Nativelease128 free0. Originalrequest callerowned.

Headlessv3 passively shadows only successful original sends, never consumes/modifies/frees originals. NativeFB sems +88/+78, bitmapAddRef/ReadLock, same GPE command_lock via TLS tryguard. Under leases verify token/bank/vptr, originalbitmap format→GPE mapping, stride/bsize/545 extent, then CPU VA readable shared/dev/mem mapping and exactoffset+VA delta physical equality. Actualmemcpy+memcmp; reverse all releases beforecommitring/ACK. First frame bitmapformat1/GPE0/FBformat1, token402,640x480/stride640/span614400=bsize, physical43feb5100. bits7f007dc100 within shared7f007dc000..7f00873000 offset43feb5000.

8slot16MiB ring41e000000, FDT+native memrsv verifiednonoverlap, header10000/stride180000/pixelheader100. Guest ACKaftercopy/releases/ringcommit; hostQMP READONLY periodically/end exportsPNG with no ACKdependency. OriginalschemaUNPROVEN: explicit8Bzeroextension6003/6005 source8280074d→8288076c chosen safe fullreceive minimum(+4..7envelopewordread); notnativepacketlength/status/CPpanel equivalence.

Final1358 snapshots/1358 ACKqueued/1358 original nativeSigsuccess,duplicates/rejected/failed0; sampled74groups originalnativefree0→fd384 parentf2280/f22d0→osal_sig_sem result0/matched1→drawfrontwait parentf2228 returns0. Onlyone1003, then1005 retainedpixel_source_seq1. **Not1358newpixel draws.** OriginalUIupdate count2(AP84r2)→1360; dequeue2905/timer2873, timerproductionprobe2873, a18peak208/last0. Boot4taskbarrierpass, pin42/42, faceDMM4/4 andICDT3/3 maintained. GPEonlyFillRectfmt0/flagsff/dst43feb5100/result0 andFlush0; approximate/HV0.

Host232 checksum-valid observedslots,1126missing overwrittenintermediateseq,0tornrejects;14raw/28dualformatPNGs. Onlyfirst30seq8..15 observed/retained; don'tclaimallfirst30 orall30multiples retained. Allpixelsuniformblack, SHA614400B34c69899504b36f13e8b22120cf0fd894e61fcd6b046fb8535b79cc491fa3b3f matches independent final545physicalpayload. Viewedosd-frame-000008-format0-RGBA-opaque.png isblack. Secondformat1interpretation320x480 stride320 stayswithin614400B, RGBA/opaque hypotheses/noH/Vflip. No nonuniformmenu/noinput injection.

## New blockers, do not paper over

1. VDF0400 exact10B 0d2000040a0001800000 dst92840747/source81cf61c2 atserial21809; absentAP84r2. OriginalappFw2de7260 BLosal_snd_msg→success2de72f4→2de72fc timeout−1→2de7300 osal_rcv_msg_tmo. SeqQueueCommon346 lasttwo full/proc snapshotsfd3/ioctl80000007→kernelosal_rcv_msg_tmo. CPcontractunreviewed, nofabricatedreply.
2. After1358 nativeACKs consumed, next1002 acceptedbutmatching1005descriptorneverobserved. Finalringstage1/pending1005 persists102.017hostseconds, noACKoutstanding/softwareerror. Actualallocator/send/queue cause unproven; don’tinferpool exhaustion solelyfromcount. Currenthelper has **no explicit pair deadline** (onlyownerbounded run), recordedasopen. Mustadd passiveallocator/sender/thread evidence and boundedpairtimeout(noACK), beforeclaimingrobust completeconsumer. A7reference hasqueue-owningreceive→release whereasthisrunexplicitlypassiveshadow; noownershipchangeorfreeoriginalswithoutLeaddecision.

## Durable artifacts and scripts

- reports/2026-11-01-fx3-vm-resumed-repair/ap85-software-osd-ring.md +README indexed; STATE synchronized.
- ap85{a,r2,r3,r4}-review.json; review_osd85.py→review_speed85.py→review_face85_base.py (optimized cachedbrightnessstart, olderreview_face83 wasquadratic; oldsource preserved). ReadsSTATElast_run, runonlyafterownVMends. Reviewendmaps and nativecompletion/publication vsnewframe distinction.
- ap85-new-blocks-proof.json +prove_new_blocks85.py (originalAPraw/syncwrapper,SeqCommon,ringtail,pixelhash)
- ap85-format-domain-proof.json +prove_format85.py (nativeBpp ef074/1de628, Fill101890/1e220c mappings)
- ap85-audit-input-check.json +check_audit85.py (72blocks/17sources, extraDataflow/Objdisasm; noauditregeneration)
- ap85-post11a-requests.json (allcapturedselectedservice requests/stacks, rawUIPCdrop limits honest)
- ap85-comparison.json +finalize_osd85.py (don'trerununnecessarily; reportfreshfinalscope)
- prepare_peaking85.py→capidv42 frozenused. helpers/fx3-osd-core-v{1,2,3}.h andheadless-v{1,2,3}.c/.so frozenused; **newversionsonly** ifchanges.
- prepare_gpe_guard85.py→GPEv14guardv1 onlysharedlockexports; originalGPEv14unchanged.
- build_headless85{,_v2,_v3}.py (cosmetic stdout “headlessv1built” forcopies, actual filenames/JSONcorrect)
- prepare_osd85.py,r3.py,r4.py; r2builtinline, add_endmaps85.py beforefirstrun (neverrerunonusedcandidate)
- run_osd_candidate85{,_r2,_r3,_r4}.py; r2onwards accepts run/STOP_FOR_REVIEW throughsameownerQMPconnection, breaks→stop/snapshot/quit. Originalrunner frozen. SecondexternalQMPconnection can'tgetgreetingwhileownerholdsconnection; failedattemptdidnotmutateguest. Don'tuseexternalstop_osd85_block.py again.
- osd_ring85{,_v2,_v3}.py readonlyQMPread/hash/PNG; v3records26wordsinclCPUmapidentity.
- ASan/UBSan host receipts: peaking85-host-check.json,osd-core-v3-host-check.json,headless-native-v3-host-check.json,osd-cpu-mapping-host-check.json,gpe-guard-host-check.json; ringv3synthetichostcheckosd-ring-v3-host-check.json. Nativecapture/ringcodeextractedunchanged19leasepaths; mapsparseractualfunctiontestlargefile/chunks/overlong/5negative; runtimeactualnativebindings separatelyproved.
- ap85-a7c2-latest-recheck.json: API SSL EOF, webfallbackcurrentmainREADME/headlesssourceaccessible, latestimmutablecommitnotrecovered. Referencehttps://github.com/chocotan/a7c2-qemu andrawmainheadless-osd.c; maintainerstillseparatesmenuusablefromoriginalcaptureJPG/MP4incomplete. LocalpinnedsourceSHA55c695...d582used; noA7privateoffsetcopied.

## Await next instruction

NoVM/locksactive. Lastfinalstatusmsg423d147f816b explicitlyno worker_done. A blocking `orca orchestration check --wait --timeout-ms50000` wasstarted(session53331), pollorstartnewcheckandackanydelivery. Heartbeatswhileactiveevery5min; checkwaititselfliveness. Noautounrelatedwork. Preserveoriginals/oldruns/helpers; nogit/device/networktoVM/trashdeletion.
