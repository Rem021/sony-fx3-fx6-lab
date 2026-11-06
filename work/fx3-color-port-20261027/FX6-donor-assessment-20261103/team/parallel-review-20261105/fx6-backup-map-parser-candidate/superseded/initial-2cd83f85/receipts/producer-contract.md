# Producer source boundary (extracted from the frozen grmreal46 CPIO `/init`)

Source: `guest-hybrid-fx6kernel-capid-grmreal46.cpio:/init` (read-only extraction in `work/cpio/init`).

## IM_ENDMAPS

Lines 58-62 (and the other five copies) are:

```sh
for im_pid in $(/bin/busybox pidof im.elf); do
  echo FX3_AP_IM_ENDMAPS_${im_pid}_BEGIN
  /bin/busybox cat /proc/uptime
  /bin/busybox grep '/usr/bin/im.elf' /proc/$im_pid/maps
  echo FX3_AP_IM_ENDMAPS_${im_pid}_END
done
```

Therefore the official `IM_ENDMAPS` body is **im.elf rows only**. It is not a
`cat /proc/<pid>/maps` contract, and appFw/lib rows between those markers are
foreign/interleaved output. They cannot be credited to that block. The begin
line is the boundary; a complete END is required. A missing/different END
invalidates the block.

## EARLY_MAPS

Lines 349-351:

```sh
echo FX3_AP_EARLY_MAPS_${im_pid}_${early}_BEGIN
/bin/busybox cat /proc/uptime /proc/$im_pid/maps
echo FX3_AP_EARLY_MAPS_${im_pid}_${early}_END
```

EARLY is the full-map producer. A complete EARLY block may own appFw rows. The
current r6 appFw rows are in an IM_ENDMAPS block, not EARLY; the 66ed appFw
rows are in an EARLY block whose END is missing. Neither is admissible under
the frozen producer contract.

## Future full IM

A future producer that changes the body to `cat /proc/$im_pid/maps` would need
an explicit `full_proc_maps` producer contract and a complete same-pid block.
The parser supports that structurally for review/tests, but does not infer it
from the current log. The default remains `official_im_elf`.
