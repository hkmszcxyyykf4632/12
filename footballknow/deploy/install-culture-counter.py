"""Install the independent counter from a verified repository release archive."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tarfile
import time
from urllib.request import urlopen

ROOT = Path('/opt/jingzang-counter')
UNIT = Path('/etc/systemd/system/jingzang-counter.service')
SERVICE = '''[Unit]
Description=Jingzang homepage visits
After=network.target

[Service]
Type=simple
DynamicUser=yes
StateDirectory=jingzang-counter
Environment=CULTURE_STATE_DIR=/var/lib/jingzang-counter
WorkingDirectory=/opt/jingzang-counter
ExecStart=/usr/bin/python3 /opt/jingzang-counter/culture_counter_service.py
Restart=on-failure
RestartSec=3
NoNewPrivileges=yes
PrivateTmp=yes
ProtectSystem=strict
ProtectHome=yes
MemoryMax=96M
TasksMax=32

[Install]
WantedBy=multi-user.target
'''


def run(*args, check=True):
    return subprocess.run(args, check=check, capture_output=True, text=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--archive', type=Path, required=True)
    parser.add_argument('--sha256', required=True)
    parser.add_argument('--revision', required=True)
    args = parser.parse_args()
    assert os.geteuid() == 0
    assert re.fullmatch(r'[0-9a-f]{40}', args.revision)
    assert hashlib.sha256(args.archive.read_bytes()).hexdigest() == args.sha256
    assert ROOT.resolve() == ROOT and not UNIT.is_symlink()
    prefix = f'12-{args.revision}/footballknow/'
    files = {}
    with tarfile.open(args.archive, 'r:gz') as bundle:
        for source, name in [('football/visits.py', 'visits.py'), ('deploy/culture_counter_service.py', 'culture_counter_service.py')]:
            member = bundle.getmember(prefix + source)
            assert member.isfile() and member.size < 100_000
            raw = bundle.extractfile(member).read()
            compile(raw, name, 'exec')
            files[name] = raw
    backup = Path('/var/backups/jingzang-counter') / datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%f')
    backup.mkdir(parents=True, mode=0o700)
    old_files = {name: (ROOT / name).read_bytes() if (ROOT / name).is_file() else None for name in files}
    old_unit = UNIT.read_bytes() if UNIT.exists() else None
    was_active = run('systemctl', 'is-active', '--quiet', 'jingzang-counter', check=False).returncode == 0
    for name, raw in old_files.items():
        if raw is not None:
            (backup / name).write_bytes(raw)
    if old_unit is not None:
        (backup / UNIT.name).write_bytes(old_unit)
    ROOT.mkdir(parents=True, exist_ok=True, mode=0o755)
    ROOT.chmod(0o755)
    try:
        for name, raw in files.items():
            (ROOT / name).write_bytes(raw)
            (ROOT / name).chmod(0o644)
        UNIT.write_text(SERVICE, encoding='utf-8')
        UNIT.chmod(0o644)
        run('systemctl', 'daemon-reload')
        run('systemctl', 'enable', '--now', 'jingzang-counter')
        run('systemctl', 'restart', 'jingzang-counter')
        for attempt in range(20):
            try:
                with urlopen('http://127.0.0.1:8766/api/visits', timeout=2) as response:
                    total = json.load(response)['total']
                assert total >= 100000
                break
            except (OSError, ValueError):
                if attempt == 19:
                    raise
                time.sleep(.25)
        run('systemctl', 'is-active', '--quiet', 'jingzang-counter')
    except Exception:
        run('systemctl', 'stop', 'jingzang-counter', check=False)
        for name, raw in old_files.items():
            if raw is not None:
                (ROOT / name).write_bytes(raw)
        if old_unit is not None:
            UNIT.write_bytes(old_unit)
        else:
            run('systemctl', 'disable', 'jingzang-counter', check=False)
            UNIT.unlink(missing_ok=True)
        run('systemctl', 'daemon-reload')
        if was_active:
            run('systemctl', 'start', 'jingzang-counter')
        raise
    print(json.dumps({'installed': args.revision, 'total': total, 'backup': str(backup)}))


if __name__ == '__main__':
    main()
