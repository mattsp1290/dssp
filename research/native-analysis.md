# Initial native analysis

Target: the acquired SYNTHOR with SHA-256
`6bf2506dec8c582a82152f6acd42be472bec8a67689890324d9fe5c3fb46397c`.
These findings apply to those exact bytes. No target code was executed.

## Coverage

REA 6.8.0 with Ghidra 12.1.4 completed analysis with the explicit preset
`ghidra-default+disabled:Decompiler Switch Analysis`. The default attempt was
cancelled after remaining in DecompilerSwitchAnalyzer for several minutes;
a JVM thread dump identified that pass. Disabling it reduced the subsequent
startup to roughly a minute. Switch-table recovery is consequently limited.

The inventory has image base `0x10000`, 3,655 procedures (including external
functions/thunks), 3,215 defined strings, and 31 memory blocks. These counts
are not a measure of complete function discovery. Function boundaries are
missing in at least one important display-initialization region.

Overview Evidence: `ev_5c074fd04d4653776c590a8218884f3e3abf4325fd38a221e1a527075977a0e0`.
Provider profile digest:
`0ea988610b184253da7e1742f2cf306d523e136e3f2ea46f414fbcf3e7eeea59`.
Raw MCP responses remain local under ignored `artifacts/mcp/`.

The ELF dynamic section independently confirms 16 required shared libraries
and version references including GLIBC_2.30 and GLIBCXX_3.4.21. Full declared
requirements are recorded in [application-abi.json](application-abi.json).
These are application requirements, not a measurement of the installed libc.

The acquired zImage contains a gzip payload at offset 30072. Decompression
produces 25,116,204 bytes and a Linux 5.13.13-00056-g5031957dda5b version banner,
built with GCC 8.4.0 from Buildroot 2021.05.1-15-gaca838b851. See
[kernel.json](kernel.json) for hashes and details. The extlinux label kernel-4.4
is therefore stale. This identifies the acquired kernel image, not a live uname
measurement. No IKCFG_ST embedded-config marker was found in the decompressed
payload, so a kernel configuration has not been recovered by this check.

## Controls

The constructor-like function at `0xaec70` opens four
`/dev/input/by-path/platform-rotary@%d-event` paths, indexed 0–3, followed by
`platform-gpio-keys-event` and `platform-matrix-keypad-event` in the same directory.
The pseudocode passes flags 0 to open, then uses fcntl commands 3 and 4 to add
flag `0x800`. On the target's Linux ABI these correspond to read-only open,
F_GETFL/F_SETFL, and O_NONBLOCK.

String/reference coordinates:

| String address | Reference addresses | Meaning |
| --- | --- | --- |
| `0x32cf80` | `0xaffa8`, `0xaffc0` | Four rotary event paths |
| `0x32cfac` | `0xb0018` | Encoder push buttons |
| `0x32cfd8` | `0xb0050` | Matrix keypad |

This agrees with the DTB's four rotary-encoder nodes and gpio input nodes.
The DTB declares encoder push-button Linux codes 2–5 and a 3×6 keypad with
5 ms debounce. See hardware-map.json for all numeric codes. The association
between matrix coordinates and printed panel labels still needs a live test.

Pseudocode Evidence: `ev_c61dfbe4a162f69f840c577247aafb5a3c567470d7a98beb2d9022ed90c212bb`.

## USB audio gadget

Function `0x9372c` refers to gadget.sh, with fallback directory strings /root
and /home/linaro. It builds script text containing module loading for usb_f_uac2
and mounting configfs, and sets executable permissions on the script path.
The exact file-search helper behavior still needs verification against the
filesystem and helper code.

Function `0x93dcc` contains the diagnostic name AudioSlave::loadDevice. Its
pseudocode builds a configfs gadget below `/sys/kernel/config/usb_gadget/g1`,
including `functions/uac2.aud0` and `configs/c.1`. It supplies vendor 0x16C0,
manufacturer Percussa, product Percussa Audio, and writes capture/playback
channel masks, sample rates, and sample sizes. Both sample-size values are 4.
It links the function into the configuration and inspects `/sys/class/udc` for
a controller to bind. The helper at `0x93b10` has write/truncate/error-handling
paths and diagnostic strings identifying AudioSlave::writeTo.

Inference: a standalone replacement that needs USB audio must preserve or
reimplement this setup; merely launching an ALSA application may not recreate
the USB interface after boot. The USB channel mask and selected sample rate
remain arguments to trace, rather than constants established here.

The decompiler reports unsettled type propagation in `0x93dcc`; variable types
and reconstructed signatures are provisional.

Evidence:

- Script setup: `ev_901377c654910dda7234a6cb780bf92cb9518ab94248e0abd3537f82c3b14edf`.
- Gadget setup: `ev_0fb027df0f969a41173f6ed4db9823ab3ac6ab9d73ad656945425a0913213e1a`.
- Write helper: `ev_b70f454a3198c628000e43e97e8b725bbc528ded40d7cf71bfa3da2e134358bd`.

## Display

The string `/dev/dri/card0` at `0x35dcc8` is referenced by a decoded instruction
at `0x2a8d4`. Instructions at `0x2a8d0`–`0x2a8dc` load that string into r0,
set r1 to 2, and call the open thunk at `0x1b4e4`. After checking the returned
descriptor, `0x2a8f4` calls drmModeGetResources through thunk `0x1bc58`.
This establishes a DRM device-open path using O_RDWR.

No containing function is defined at `0x2a8d4` in this analysis. A direct
decompile request at that address fell back to interpreting it as a file offset
and returned unrelated function `0x3a484`; that output is excluded from these
findings. Always verify coordinates and function containment before treating
numeric decompile output as evidence for the intended location.

Instruction Evidence: `ev_44c5500f042670c4948f7ca9d5e528626626ca91000a72493c46bcb2658cc36d`.
Open-thunk Evidence: `ev_8eeb84405b3a1efa19c33506508c8352182058670fc5201ece744f232721b106`.

## ALSA

The snd_pcm_open thunk is at `0x1aba8`. Observed call sites are `0x112bf8`,
`0x11781c`, and `0x117870`. Function `0x112b5c` wraps PCM opening and reports
busy/unavailable-device errors. Function `0x11774c` probes playback/capture
capabilities and closes the probe handles. These are useful library-level
entry points, but do not yet establish the hardware card name, sample format,
channel ordering, buffer periods, or voltage calibration.

Evidence: `ev_51e499b292f78e8436f40034d0a2056673df9793ed72d7a9d8f4e34bf17069d4`
and `ev_b5d69b78ded99d2d5533bb3d4e1bd9931cf7a700a7e9de44a9af080265a12379`.

## Reproduce selected probes

```sh
export REA_GHIDRA_DISABLED_ANALYZERS='Decompiler Switch Analysis'
sh scripts/rea.sh search "$PWD/artifacts/original/boot/SYNTHOR" \
  'platform-|/dev/dri/card0|/sys/kernel/config' --mode regex --provider ghidra --format json
sh scripts/rea.sh decompile "$PWD/artifacts/original/boot/SYNTHOR" \
  0x93dcc --provider ghidra --format json
```

Use a persistent REA MCP session for multiple probes to avoid repeating import.
After exporting desired Evidence, close_binary releases its ephemeral project.
