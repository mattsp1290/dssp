#!/usr/bin/env python3
"""Read the identified SSP card into a new image; never write to the device."""
import hashlib
import argparse
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
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--verify-existing', action='store_true',
                        help='Verify a full-length partial image without recopying the card')
    args = parser.parse_args()
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
    if destination.exists():
        raise SystemExit('A completed image already exists; refusing overwrite.')
    size = card['Size']
    if args.verify_existing:
        if not partial.is_file() or partial.stat().st_size != size:
            raise SystemExit('Verification-only mode requires a full-length partial image.')
    elif partial.exists():
        raise SystemExit('A partial acquisition exists; inspect it or use --verify-existing.')
    elif shutil.disk_usage(destination.parent).free < size + 1024**3:
        raise SystemExit('Insufficient free space for the image plus 1 GiB headroom.')
    raw = '/dev/r' + card['DeviceIdentifier']
    print('Administrator authentication is used only to READ the raw card.', flush=True)
    if not args.verify_existing:
        print(f'Reading {raw} ({size} bytes) into {destination}', flush=True)
        subprocess.run(['sudo', '-v'], check=True)
        with partial.open('xb') as output:
            subprocess.run(['sudo', '-n', 'dd', f'if={raw}', 'bs=4m'], stdout=output, check=True)
    if partial.stat().st_size != size:
        raise SystemExit('Image length mismatch; partial file retained.')
    print('Hashing image and rereading card for independent verification...', flush=True)
    image_hash = sha256(partial)
    # Large raw-device reads avoid the severe overhead of shasum's small reads.
    digest = hashlib.sha256()
    source_bytes = 0
    reported_gib = 0
    print('Reading card in 4 MiB blocks for verification...', flush=True)
    reader = subprocess.Popen(['sudo', 'dd', f'if={raw}', 'bs=4m'], stdout=subprocess.PIPE)
    try:
        for block in iter(lambda: reader.stdout.read(4 * 1024**2), b''):
            digest.update(block)
            source_bytes += len(block)
            gib = source_bytes // 1024**3
            if gib > reported_gib:
                print(f'Verification read: {source_bytes / 1024**3:.1f} / '
                      f'{size / 1024**3:.1f} GiB', flush=True)
                reported_gib = gib
        reader.stdout.close()
        if reader.wait() != 0 or source_bytes != size:
            raise SystemExit('Verification read failed or length changed; partial file retained.')
    finally:
        if reader.poll() is None:
            reader.stdout.close()
            # Closing the pipe makes the read-only dd stop on SIGPIPE.
            reader.wait(timeout=15)
    source_hash = digest.hexdigest()
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
