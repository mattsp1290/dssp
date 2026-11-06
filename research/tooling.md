# Analysis and acquisition tools

## Pinned working configuration

- REA 6.8.0, Node 24.22.1 through `scripts/rea.sh`.
- Ghidra 12.1.4, official archive `ghidra_12.1.4_PUBLIC_20260921.zip`.
- Archive SHA-256: `ddac49f903da9d5bac833e5cc79395098b9c33cfd3279be5f31bd00387d2d4db`.
- Existing Homebrew JDK 23, ARM64. Ghidra 12.1.4 requires JDK 21 or newer.
- Native macOS ARM64 components built using the release's
  `support/gradle/gradlew buildNatives` (successful).
- `dtc`/`fdtget` 1.8.1 and e2fsprogs 1.47.4 installed via Homebrew.

The first Homebrew install supplied Ghidra 12.2 and JDK 25. REA 6.8.0 rejected
that Ghidra version, although the current upstream main documentation says it
is accepted. The published package's observed check takes precedence. The
separate 12.1.4 installation passes `doctor --provider ghidra`; the general
doctor also checks unrelated providers and agent registrations.

The wrapper defaults to an adjacent `../tools/ghidra_12.1.4_PUBLIC` directory
and this Mac's Homebrew JDK path. Override `GHIDRA_INSTALL_DIR` and `JAVA_HOME`
on other machines. It does not change global Node selection or agent settings.

```sh
sh scripts/rea.sh doctor --provider ghidra --format json
export REA_GHIDRA_DISABLED_ANALYZERS='Decompiler Switch Analysis'
sh scripts/rea.sh analyze "$PWD/artifacts/original/boot/SYNTHOR" \
  --provider ghidra --format json > artifacts/synthor-overview.json
python3 scripts/inspect_device_tree.py > research/hardware-map.json
```

The analyzer override is specific to the observed stall described in
[native-analysis.md](native-analysis.md). It reduces switch recovery coverage.

Source: [Ghidra release](https://github.com/NationalSecurityAgency/ghidra/releases/tag/Ghidra_12.1.4_build)
and the release's bundled GettingStarted.md native-build instructions.

## Full card acquisition

On this Mac, raw card reads require administrator authentication. Run:

```sh
python3 scripts/backup_sd.py
```

The script identifies the card from the mounted BOOT volume, requires read-only
Secure Digital media, checks the known BOOT UUID and SYNTHOR digest, and verifies
free space. It creates a new `artifacts/ssp-sd.img.partial` exclusively, streams
the entire raw card using a privileged read, verifies its byte count, then
compares the local SHA-256 with a second full card read. Only a matching image
is renamed to `ssp-sd.img` and accompanied by `ssp-sd.img.json`.

Authentication may be requested again for the second read if sudo's credential
cache expires. Interrupted or failed acquisitions leave the partial file for
inspection; rerunning refuses to overwrite it. The script never writes to the
card. A verified image still needs a restore-and-boot test on a spare card to
establish recovery in practice.

If copying completed but verification was interrupted, stop the previous
process before running `python3 scripts/backup_sd.py --verify-existing`.
This requires a full-length partial image and repeats identity/hash checks
without recopying. Verification streams `sudo dd` with 4 MiB raw-device reads
into SHA-256; directly running shasum on the raw device used small reads and
proved substantially slower on this SD reader.

After verification:

```sh
python3 scripts/extract_rootfs.py
/opt/homebrew/opt/e2fsprogs/sbin/debugfs -R 'ls -l /etc/init.d' artifacts/rootfs.img
```

Extraction validates GPT header/table CRCs, locates the root PARTUUID specified
by extlinux.conf, checks its bounds and ext filesystem magic, and copies that
partition to a new local file. `debugfs` defaults to read-only; do not add `-w`
when inspecting the acquired filesystem. Original images and extracted files
remain ignored by Git.
