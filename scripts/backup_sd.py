#!/usr/bin/env python3
"""Read the identified SSP card into a new image; never write to the device."""
import hashlib
import json
import plistlib
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def info(target):
    return plistlib.loads(subprocess.check_output(['diskutil', 'info', '-plist', target]))


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as source:
        for chunk in iter(lambda: source.read(4 * 1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def main():
    boot = info('/Volumes/BOOT')
    card = info(boot['ParentWholeDisk'])
    manifest = json.loads((ROOT / 'research/acquisition.json').read_text())
    expected = next(f['sha256'] for f in manifest['files'] if f['path'] == 'boot/SYNTHOR')
    if (boot.get('VolumeUUID') != '51702461-01E5-35F7-B93C-76C5FCA77862'
            or card.get('BusProtocol') != 'Secure Digital'
            or not card.get('WholeDisk')
            or card.get('WritableMedia') is not False
            or sha256('/Volumes/BOOT/SYNTHOR') != expected):
        raise SystemExit('Card identity/read-only checks failed; refusing acquisition.')
    destination = ROOT / 'artifacts/ssp-sd.img'
    destination.parent.mkdir(exist_ok=True)
    partial = destination.with_suffix('.img.partial')
    if destination.exists() or partial.exists():
        raise SystemExit('An image or partial acquisition already exists; inspect it first.')
    size = card['Size']
    if shutil.disk_usage(destination.parent).free < size + 1024**3:
        raise SystemExit('Insufficient free space for the image plus 1 GiB headroom.')
    raw = '/dev/r' + card['DeviceIdentifier']
    print(f'Reading {raw} ({size} bytes) into {destination}', flush=True)
    print('Administrator authentication is used only to READ the raw card.', flush=True)
    subprocess.run(['sudo', '-v'], check=True)
    with partial.open('xb') as output:
        subprocess.run(['sudo', '-n', 'dd', f'if={raw}', 'bs=4m'], stdout=output, check=True)
    if partial.stat().st_size != size:
        raise SystemExit('Image length mismatch; partial file retained.')
    print('Hashing image and rereading card for independent verification...', flush=True)
    image_hash = sha256(partial)
    result = subprocess.check_output(['sudo', 'shasum', '-a', '256', raw], text=True)
    source_hash = result.split()[0]
    if image_hash != source_hash:
        raise SystemExit('SHA-256 mismatch; partial file retained.')
    partial.rename(destination)
    report = {'image': destination.name, 'size': size, 'sha256': image_hash,
              'source_sha256': source_hash, 'verified': True,
              'device_at_acquisition': raw, 'boot_volume_uuid': boot['VolumeUUID']}
    destination.with_suffix('.img.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2), flush=True)


if __name__ == '__main__':
    main()
