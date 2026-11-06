# dssp
REA + SSP = dssp?

Research toward custom software for the Percussa SSP, using REA to investigate
the existing application and hardware interfaces.

Start with [the baseline investigation](research/baseline.md) and
[the acquisition manifest](research/acquisition.json).

Current milestone: copied and verified the installed SYNTHOR executable, kernel,
device tree, and boot configuration; completed REA/Ghidra native inspection and
mapped initial control, display, USB gadget, and ALSA entry points. No custom
application has been built or deployed yet.

- [Native findings and limitations](research/native-analysis.md)
- [Hardware declarations](research/hardware-map.json)
- [Tool setup, backup, and extraction procedures](research/tooling.md)

Original binaries and raw local analysis stay under ignored `artifacts/`.
This repository tracks findings, provenance, and reproducible procedures.
