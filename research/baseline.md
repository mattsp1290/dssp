# SSP baseline — 2026-11-06

This records the initial acquisition. Subsequent native analysis is documented
in [native-analysis.md](native-analysis.md), with working prerequisites and
backup procedures in [tooling.md](tooling.md). The original space constraint
below has since been resolved; full-image verification is tracked separately.

## Objective and approach

The end goal is custom firmware/software. First establish a replacement Linux
application running on the existing kernel and drivers, then evaluate whether
kernel or boot changes are actually necessary. Existing community applications
demonstrate this route; compatibility with this particular installation remains
to be tested.

## Observed on the connected unit

macOS reported Percussa Audio, 24 input and 24 output channels, at 48000 Hz.
IORegistry reported USB VID:PID `16c0:08c1`. The three observed interfaces were:

| Interface | Class | Subclass | Protocol |
| --- | --- | --- | --- |
| 0, Percussa Audio | 1 | 1 | 32 |
| 1, Percussa In | 1 | 2 | 32 |
| 2, Percussa Out | 1 | 2 | 32 |

These are audio control/streaming interfaces. No storage, serial, or network
interface was exposed in the observed configuration. This does not establish
what other modes the hardware could support.

The user connected the microSD card. macOS identified it as a 31.9 GB Secure
Digital device with seven partitions. BOOT was FAT32, 21.0 GB, mounted read-only;
the media itself was also reported read-only. Device identifiers are temporary:
it appeared as disk4, with BOOT at disk4s6 during this session.

Four files were copied into local `artifacts/original/boot/`; SHA-256 hashes of
each source and copy matched. See acquisition.json for sizes and hashes.
Presets and samples were not copied. The card was not modified by our commands.
This is a targeted acquisition, not a full backup.

`file` identifies SYNTHOR as a stripped, dynamically linked 32-bit little-endian
ARM EABI5 ELF with interpreter `/lib/ld-linux-armhf.so.3`. Its GNU/Linux ABI note
is reported as 5.12.0; that is not proof of the running kernel version.
The boot configuration label says kernel-4.4, selects zImage and
rk3288-percussa-engine-euro.dtb, specifies an ext4 root by PARTUUID, and includes
`console=ttyS2,115200n8` and `isolcpus=1,2,3`.
The root PARTUUID matches partition 7 (9.4 GB); its contents have not been read.
macOS's filesystem label for that partition is not reliable evidence against
the explicit ext4 boot configuration.

## Initial static leads

The following strings occur in the copied SYNTHOR. They identify investigation
targets, not verified call paths or a complete hardware API:

- `13072022`, `Jul 13 2022`: candidate application release/build markers.
- `GCC: (Buildroot 2021.05.1-15-gaca838b851) 8.4.0`: compiler provenance string.
- `libasound.so.2`, `snd_pcm_open`, `snd_pcm_readi`, `snd_pcm_writei`: ALSA leads.
- `libdrm.so.2`, `libgbm.so.1`, `libepoxy.so.0`, `/dev/dri/card0`: graphics leads.
- `/dev/input/by-path/platform-rotary@%d-event`: encoder input lead.
- `/dev/input/by-path/platform-gpio-keys-event`: button input lead.
- `/dev/input/by-path/platform-matrix-keypad-event`: keypad input lead.
- `/sys/kernel/config`, `/sys/class/udc`: USB gadget configuration leads.

## REA status and reproduction

REA 6.8.0 ran successfully with Node 24.22.1 supplied through npm exec. The
machine's default Node 22.9.0 is below REA's declared minimum. No global Node
version or agent configuration was changed.

From the repository root, after acquiring the files:

```sh
npx --yes --package=node@24.22.1 --package=rea-agents@6.8.0 \
  rea inspect-artifact "$PWD/artifacts/original/boot/SYNTHOR" --format json \
  > artifacts/synthor-rea.json
```

The initial npm acquisition emitted engine warnings from the older invoking npm
runtime; the launched Node was independently verified as v24.22.1.

REA verified the ELF root hash and size. Evidence ID:
`ev_557a53e94ffde091d510b25e3f05b743368e8323eb98a066e66c336700649cd4`.
This was artifact inventory only: no decompilation, function analysis, or target
execution occurred. REA explicitly recommends `open_binary` with a native
provider next. Its inventory did not identify architecture; the ARM result above
comes from macOS `file`.

No Ghidra/Hopper installation was found in the initial PATH/application check.
REA's Binwalk/Unblob firmware workflow is documented as verified on Linux x64;
direct analysis of the acquired ELF does not require filesystem extraction.
The Docker CLI exists, but its selected colima context is missing.

## Next milestones

- [x] Record USB exposure and acquire the principal BOOT files with hashes.
- [x] Run REA artifact inventory on the exact installed SYNTHOR.
- [ ] Preserve a complete SD image to a destination with sufficient space and
  verify recovery on a spare card. The Mac had about 17 GiB free, insufficient
  for an uncompressed 31.9 GB image.
- [ ] Configure a native analysis provider and map SYNTHOR startup, ALSA setup,
  display initialization, control events, USB gadget setup, and plugin loading.
  Record addresses, cross-references, and uncertainty for each finding.
- [ ] Inspect the device tree and Linux root filesystem to identify drivers,
  init scripts, library ABI, calibration, and device permissions. Preserve a
  matching sysroot for cross-compilation.
- [ ] Review the public SDK and existing standalone hosts; distinguish reusable
  source from undocumented behavior that needs reverse engineering.
- [ ] Build a minimal standalone application with screen output, encoder/button
  events, and controlled audio I/O. Verify sample formats, channel mapping,
  latency, and CV scaling on a spare card before expanding functionality.
- [ ] Add an application selection/recovery path and document reproducible
  deployment. Consider OS changes only after the application proof of concept.

## Sources and prior work

- [REA](https://github.com/morluto/rea) and its
  [firmware guide](https://github.com/morluto/rea/blob/main/docs/firmware-analysis.md).
- [Percussa SSP specifications](https://www.percussa.com/): Cortex-A17 platform.
- [Official SDK](https://github.com/percussa/ssp-sdk).
- [PercCmd](https://github.com/TheTechnobear/SSP/wiki/PercCmd): selecting standalone
  applications, including Synthor, TraxHost, and ER-301, on the Linux system.
- [Networking](https://github.com/TheTechnobear/SSP/wiki/Networking): development
  access through a USB-A Ethernet/Wi-Fi adapter, dependent on installed image.
- [Percussa update explanation](https://forum.percussa.com/t/regarding-firmware-updates-after-flashing-new-image-to-sd/791):
  separates the SD image from SYNTHOR application updates.

Existing local SSP SDK, plugin, and builder checkouts were found. The builder
references Percussa's 13072022 Buildroot toolchain. These are leads to inspect;
their contents and dependencies have not been validated for this project.
