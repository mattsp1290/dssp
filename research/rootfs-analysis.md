# Installed root filesystem and startup

The full 31,914,983,424-byte card image passed source/image SHA-256 comparison.
See [sd-backup.json](sd-backup.json). A second `--verify-existing` invocation
correctly refuses to overwrite the completed image. Restoration and booting a
spare card have not been tested.

`scripts/extract_rootfs.py` successfully extracted partition 7 after validating
GPT CRCs, the configured root PARTUUID, bounds, and filesystem magic. Its digest
and offset are recorded in [rootfs.json](rootfs.json). All inspection used
read-only debugfs against this local copy; no card contents were changed and
no target programs were executed.

## Startup chain

1. BusyBox inittab mounts filesystems and invokes `/etc/init.d/rcS`.
2. rcS invokes matching `S??*` scripts in filename order.
3. `/etc/init.d/S90synthor start` kills any existing SYNTHOR and backgrounds
   `/root/synthor.sh`, discarding its output.
4. That wrapper configures IRQ affinities, invokes `/root/gadget.sh`, sets the
   ALSA `PCM` mixer to 99%, disables `High-Pass Filter`, and repeatedly runs
   `/media/BOOT/SYNTHOR`. It stops restarting only when the exit status is 137.

The IRQ mask literals are 1 for IRQs 34/41/42/43, 2 for IRQ 35, and 4 for
IRQs 58/59. Their source comments label SD, USB, audio SDIO, and DMA roles;
these labels have not been checked against live interrupts. Do not assume IRQ
numbers remain valid after changing kernels.

`/etc/fstab` mounts `/dev/mmcblk1p6` at `/media/BOOT` as vfat. The active
wrapper directly executes the application; historical startx lines are comments.
The commented inittab SYNTHOR respawn line is also inactive.

Implication: a replacement userspace application can be introduced at the
existing launcher boundary on a spare card, retaining the kernel and drivers.
Simply terminating SYNTHOR may cause the wrapper to restart it, depending on
exit status. Any launcher design must account for this supervisor and restore
the original application on failure. This route is supported by static evidence
but has not been exercised on hardware.

## USB and physical audio

The active `/root/gadget.sh` only loads `usb_f_uac2` and mounts configfs. This
fits the [native findings](native-analysis.md): SYNTHOR contains the remaining
gadget configuration logic. A replacement application cannot assume that script
alone recreates the current USB audio interface.

`gadget.sh.backup` contains older configuration with PID 0x07bd and 8-channel
masks. It is not called by the inspected startup chain and differs from the
observed PID 0x08c1 and 24-channel USB interface. Treat it as historical evidence.

`/root/audio-tests.txt` contains candidate physical audio commands naming
`hw:CARD=ak4458ak5558aud,DEV=0` for eight-channel playback and
`hw:CARD=ak4458ak5558aud,DEV=1` for sixteen-channel capture, both S32_LE at
192 kHz. These are stored test instructions, not proof of the current runtime
configuration or channel ordering. They were not executed. The wrapper's mixer
comments suggest voltage calibration intent, but do not establish measured CV
scaling or safe output levels.

## Runtime baseline

`/usr/lib/os-release` identifies Buildroot 2021.05.1-16-g1654a69569.
`/etc/os-release` is a fast symlink to it; debugfs `cat` on that symlink produced
a short-read error, while reading its resolved target succeeded.
`/lib` contains libc-2.32.so and ld-2.32.so. A module directory matching the
boot kernel, `5.13.13-00056-g5031957dda5b`, is present. This rootfs release differs
slightly from the compiler provenance embedded in the kernel; retain both.

Small source-file sizes and SHA-256 hashes are in
[startup-files.json](startup-files.json). Original script text and debugfs
listings remain local under ignored `artifacts/rootfs-inspection/`.

## Next implementation milestone

Prepare a matching ARM hard-float compiler/sysroot and build a read-only
hardware inventory application: enumerate ALSA capabilities, DRM connectors,
and input events before enabling audio output. Test recovery on a spare card
before changing its launcher. Physical channel mapping, mixer semantics,
latency, calibration, and a custom boot/kernel build remain unresolved.
