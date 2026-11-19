"""Install only the public Jingzang site on its separate host, preserving Caddy sites."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import tarfile


ROOT = Path('/srv/jingzang')
CADDY = Path('/etc/caddy/Caddyfile')
BEGIN = '# BEGIN FOOTBALLKNOW JINGZANG\n'
END = '# END FOOTBALLKNOW JINGZANG\n'


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def load_files(archive, checksum, revision):
    if digest(archive.read_bytes()) != checksum:
        raise ValueError('Archive checksum mismatch')
    prefix = f'12-{revision}/footballknow/'
    public_prefix = prefix + 'public/jingzang/'
    files = {}
    with tarfile.open(archive, 'r:gz') as bundle:
        config = bundle.extractfile(prefix + 'deploy/Caddyfile.culture').read().decode('utf-8')
        for member in bundle.getmembers():
            if not member.name.startswith(public_prefix) or member.isdir():
                continue
            name = member.name[len(public_prefix):]
            path = PurePosixPath(name)
            if not member.isfile() or not name or path.is_absolute() or '..' in path.parts:
                raise ValueError('Unsafe culture archive member')
            if path.suffix not in {'.html', '.js', '.css', '.json', '.png', '.jpg', '.jpeg', '.webp', '.svg', '.ico'}:
                continue
            if member.size > 20_000_000 or name in files:
                raise ValueError('Unexpected culture archive member')
            files[name] = bundle.extractfile(member).read()
    assert {'index.html', 'jingzang.js', 'index.json', 'fanti.json', 'videos.json'} <= files.keys()
    catalogue = json.loads(files['index.json'])
    assert catalogue and isinstance(catalogue, list)
    for book in catalogue:
        parts = [f"books/{book['id']}/{part}.json" for part in range(len(book['parts']))] if book.get('parts') else [f"books/{book['id']}.json"]
        assert sum(len(json.loads(files[name])) for name in parts) == len(book['ch'])
    assert 'tripitaka.shop' in config and '/srv/jingzang/current' in config
    return files, config


def run(*args):
    return subprocess.run(args, check=True, capture_output=True, text=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--archive', type=Path, required=True)
    parser.add_argument('--sha256', required=True)
    parser.add_argument('--revision', required=True)
    parser.add_argument('--caddy-base-sha256', required=True)
    args = parser.parse_args()
    assert os.geteuid() == 0 and re.fullmatch(r'[0-9a-f]{40}', args.revision)
    assert all(re.fullmatch(r'[0-9a-f]{64}', item) for item in [args.sha256, args.caddy_base_sha256])
    assert ROOT.resolve() == ROOT and CADDY.is_file()
    before = CADDY.read_bytes()
    assert digest(before) == args.caddy_base_sha256, 'Caddy changed; review before applying'
    files, site_config = load_files(args.archive, args.sha256, args.revision)
    original = before.decode('utf-8')
    if BEGIN in original:
        assert original.count(BEGIN) == original.count(END) == 1
        left, rest = original.split(BEGIN, 1)
        _, right = rest.split(END, 1)
        original = left + right
    else:
        assert END not in original and 'tripitaka.shop' not in original
    combined = original.rstrip() + '\n\n' + BEGIN + site_config.rstrip() + '\n' + END
    current = ROOT / 'current'
    assert not current.exists() or current.is_symlink()
    previous = os.readlink(current) if current.is_symlink() else None
    release = ROOT / 'releases' / args.revision
    assert not release.exists(), 'Release directory already exists'
    release.mkdir(parents=True, mode=0o755)
    for directory in [ROOT, ROOT / 'releases', release]:
        directory.chmod(0o755)
    for name, raw in files.items():
        target = release / name
        target.parent.mkdir(parents=True, exist_ok=True)
        for directory in [target.parent, *target.parent.parents]:
            if directory == release.parent:
                break
            directory.chmod(0o755)
        target.write_bytes(raw)
        target.chmod(0o644)
    metadata = {'revision': args.revision, 'publishedAt': datetime.now(timezone.utc).isoformat(),
                'archiveSha256': args.sha256, 'files': {name: digest(raw) for name, raw in files.items()}}
    (release / 'jingzang-release.json').write_text(json.dumps(metadata, ensure_ascii=False), encoding='utf-8')
    (release / 'jingzang-release.json').chmod(0o644)
    candidate = CADDY.with_name('Caddyfile.jingzang-candidate')
    candidate.write_text(combined, encoding='utf-8')
    candidate.chmod(0o644)
    run('caddy', 'validate', '--config', str(candidate), '--adapter', 'caddyfile')
    assert digest(CADDY.read_bytes()) == args.caddy_base_sha256, 'Caddy changed during preparation'
    backup = Path('/var/backups/jingzang') / datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')
    backup.mkdir(parents=True, mode=0o700)
    shutil.copy2(CADDY, backup / 'Caddyfile')
    (backup / 'previous.json').write_text(json.dumps({'current': previous, 'revision': args.revision}))
    temporary_link = ROOT / ('.current-' + args.revision[:12])
    temporary_link.symlink_to(release, target_is_directory=True)
    os.replace(temporary_link, current)
    try:
        os.replace(candidate, CADDY)
        run('systemctl', 'reload', 'caddy')
        run('systemctl', 'is-active', 'caddy')
    except Exception:
        shutil.copy2(backup / 'Caddyfile', CADDY)
        if previous:
            temporary_link.symlink_to(previous, target_is_directory=True)
            os.replace(temporary_link, current)
        else:
            current.unlink()
        run('systemctl', 'reload', 'caddy')
        raise
    print(json.dumps({'installed': args.revision, 'cultureFiles': len(files), 'root': str(current), 'backup': str(backup)}))


if __name__ == '__main__':
    main()
