#!/usr/bin/env python3
"""Copy the boot-config-selected root partition from a verified local SD image."""
import hashlib
import json
import re
import shutil
import struct
import uuid
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
image = ROOT / 'artifacts/ssp-sd.img'
report = json.loads(image.with_suffix('.img.json').read_text())
if report.get('verified') is not True or image.stat().st_size != report['size']:
    raise SystemExit('A completed, verified acquisition is required.')
config = (ROOT / 'artifacts/original/boot/extlinux/extlinux.conf').read_text()
part_uuid = uuid.UUID(re.search(r'root=PARTUUID=([0-9a-fA-F-]+)', config).group(1))
with image.open('rb') as source:
    source.seek(512)
    header = bytearray(source.read(512))
    if header[:8] != b'EFI PART':
        raise SystemExit('GPT header not found at sector 1.')
    length, checksum = struct.unpack_from('<II', header, 12)
    if not 92 <= length <= 512:
        raise SystemExit('Unexpected GPT header length.')
    struct.pack_into('<I', header, 16, 0)
    if zlib.crc32(header[:length]) != checksum:
        raise SystemExit('GPT header CRC mismatch.')
    entries_lba, count, entry_size, entries_crc = struct.unpack_from('<QIII', header, 72)
    if not 128 <= entry_size <= 4096 or not 1 <= count <= 4096:
        raise SystemExit('Unexpected GPT partition table dimensions.')
    source.seek(entries_lba * 512)
    table = source.read(count * entry_size)
    if len(table) != count * entry_size or zlib.crc32(table) != entries_crc:
        raise SystemExit('GPT partition table CRC mismatch.')
    matches = []
    for index in range(count):
        entry = table[index * entry_size:(index + 1) * entry_size]
        if uuid.UUID(bytes_le=entry[16:32]) == part_uuid:
            first, last = struct.unpack_from('<QQ', entry, 32)
            matches.append((index + 1, first * 512, (last - first + 1) * 512))
    if len(matches) != 1:
        raise SystemExit('Root partition UUID is absent or ambiguous.')
    index, offset, size = matches[0]
    if size <= 0 or offset + size > image.stat().st_size:
        raise SystemExit('Invalid partition extent.')
    source.seek(offset + 1024 + 56)
    if source.read(2) != b'\x53\xef':
        raise SystemExit('Expected ext-family filesystem superblock is absent.')
    destination = ROOT / 'artifacts/rootfs.img'
    if shutil.disk_usage(destination.parent).free < size + 1024**3:
        raise SystemExit('Insufficient free space.')
    partial = destination.with_suffix('.img.partial')
    if destination.exists():
        raise SystemExit('rootfs.img already exists; refusing overwrite.')
    digest = hashlib.sha256()
    source.seek(offset)
    with partial.open('xb') as output:
        remaining = size
        while remaining:
            block = source.read(min(4 * 1024**2, remaining))
            if not block:
                raise SystemExit('Unexpected EOF; partial file retained.')
            output.write(block)
            digest.update(block)
            remaining -= len(block)
    partial.rename(destination)
    result = {'partition': index, 'partuuid': str(part_uuid), 'offset': offset,
              'size': size, 'sha256': digest.hexdigest(), 'image_sha256': report['sha256']}
    destination.with_suffix('.img.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))
