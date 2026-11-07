#!/usr/bin/env python3
"""Extract selected SSP hardware declarations with fdtget (read-only)."""
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DTB = ROOT / 'artifacts/original/boot/rk3288-percussa-engine-euro.dtb'


def prop(node, name, kind='x'):
    text = subprocess.check_output(['fdtget', '-t', kind, str(DTB), node, name], text=True).strip()
    return text if kind == 's' else [int(item, 16) for item in text.split()]


report = {
    'dtb_sha256': hashlib.sha256(DTB.read_bytes()).hexdigest(),
    'board_compatible': prop('/', 'compatible', 's'),
    'audio_compatible': prop('/audio-cpld', 'compatible', 's'),
    'panel': {name: prop('/lvds-panel/panel-timing', name)[0]
              for name in ('clock-frequency', 'hactive', 'vactive')},
    'encoders': [{'node': f'/rotary@{i}',
                  'driver': prop(f'/rotary@{i}', 'compatible', 's'),
                  'axis': prop(f'/rotary@{i}', 'linux,axis')[0],
                  'gpios_raw': prop(f'/rotary@{i}', 'gpios')}
                 for i in range(4)],
    'encoder_buttons': [{'label': prop(f'/gpio-keys/e{i}sw', 'label', 's'),
                         'linux_code': prop(f'/gpio-keys/e{i}sw', 'linux,code')[0]}
                        for i in range(1, 5)],
    'keypad': {'rows': prop('/matrix-keypad', 'keypad,num-rows')[0],
               'columns': prop('/matrix-keypad', 'keypad,num-columns')[0],
               'debounce_ms': prop('/matrix-keypad', 'debounce-delay-ms')[0],
               'keys': [{'row': word >> 24, 'column': (word >> 16) & 255,
                          'linux_code': word & 65535}
                         for word in prop('/matrix-keypad', 'linux,keymap')]},
    'limitations': ['Device-tree declarations only; runtime event behavior and physical button labels are unverified.',
                    'GPIO cells contain phandle references, not physical header pin numbers.']
}
print(json.dumps(report, indent=2))
