"""Apply a verified GitHub source archive to the existing Football Know service."""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tarfile
import time
from datetime import datetime, timezone
import urllib.request

ROOT = Path('/opt/footballknow')
STATE = Path('/var/lib/footballknow')
UNIT_ROOT = Path('/etc/systemd/system')
UNITS = ['footballknow-web.service', 'footballknow-worker.service']
CADDYFILE = Path('/etc/caddy/Caddyfile')


def run(*args, check=True):
    return subprocess.run(args, check=check, capture_output=True, text=True)


def load_archive(path, digest, revision):
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != digest:
        raise ValueError('Archive checksum mismatch')
    content = {}
    prefix = f'12-{revision}/footballknow/'
    with tarfile.open(fileobj=io.BytesIO(raw), mode='r:gz') as bundle:
        for member in bundle.getmembers():
            if not member.isfile() or not member.name.startswith(prefix):
                continue
            relative = member.name[len(prefix):]
            parts = Path(relative).parts
            if not parts or '..' in parts or Path(relative).is_absolute():
                raise ValueError('Unsafe archive path')
            if any(part in {'state', 'private', '.venv', 'node_modules', '__pycache__'} for part in parts):
                raise ValueError('Private or generated state in source archive')
            allowed = (len(parts) == 1 and (relative.endswith('.py') or relative in {'requirements.txt', 'analysis-rules.txt'}))
            allowed |= parts[0] == 'football' and relative.endswith('.py')
            allowed |= relative.startswith('football/hkjc_queries/') and relative.endswith('.graphql')
            allowed |= parts[0] == 'public' and Path(relative).suffix in {'.html', '.css', '.js', '.mjs', '.json', '.svg', '.png', '.webp', '.ico'}
            allowed |= relative in {f'deploy/{name}' for name in UNITS} | {'deploy/update.py', 'deploy/Caddyfile'}
            if allowed:
                if member.size > 20000000:
                    raise ValueError('Unexpected file size')
                content[relative] = bundle.extractfile(member).read()
    for relative, raw in content.items():
        if relative.endswith('.py'):
            compile(raw, relative, 'exec')
    assert 'server.py' in content and 'public/rankings-page.mjs' in content
    for league, folder, expected in [('epl', '', 20), ('laliga', 'laliga/', 20), ('ucl', 'ucl/', 36), ('seriea', 'seriea/', 20), ('bundesliga', 'bundesliga/', 18)]:
        catalogue = json.loads(content[f'public/{folder}data.json'])
        assert len(catalogue['teams']) == expected
        table = json.loads(content[f'public/{folder}standings.json'])
        assert table['league'] == league and len(table['entries']) == expected
    return content


def stop_worker():
    run('systemctl', 'stop', '--no-block', 'footballknow-worker')
    time.sleep(2)
    run('systemctl', 'kill', '-s', 'SIGTERM', 'footballknow-worker', check=False)
    for _ in range(25):
        if run('systemctl', 'is-active', 'footballknow-worker', check=False).stdout.strip() in {'inactive', 'failed'}:
            return
        time.sleep(1)
    raise RuntimeError('Worker did not stop; release not applied')


def health(content):
    for league, folder in [('epl', ''), ('laliga', 'laliga/'), ('ucl', 'ucl/'), ('seriea', 'seriea/'), ('bundesliga', 'bundesliga/')]:
        catalogue = json.loads(content[f'public/{folder}data.json'])
        team_id = catalogue['teams'][0]['id']
        with urllib.request.urlopen(f'http://127.0.0.1:8765/api/analysis/{team_id}?league={league}', timeout=25) as response:
            result = json.load(response)
        assert result['report']['team']['id'] == team_id
        assert 'lineupEvidence' in result
    with urllib.request.urlopen('http://127.0.0.1:8765/api/auth/me', timeout=10) as response:
        assert json.load(response)['authenticated'] is False


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--archive', type=Path, required=True)
    parser.add_argument('--sha256', required=True)
    parser.add_argument('--revision', required=True)
    parser.add_argument('--caddy-base-sha256', help='Update Caddy only when its current configuration matches this reviewed checksum')
    args = parser.parse_args()
    assert os.geteuid() == 0 and re.fullmatch(r'[0-9a-f]{40}', args.revision)
    assert re.fullmatch(r'[0-9a-f]{64}', args.sha256)
    assert ROOT.resolve() == Path('/opt/footballknow') and (ROOT / 'server.py').is_file()
    assert (STATE / 'admin.sqlite3').is_file()
    content = load_archive(args.archive, args.sha256, args.revision)
    if args.caddy_base_sha256:
        assert re.fullmatch(r'[0-9a-f]{64}', args.caddy_base_sha256)
        assert hashlib.sha256(CADDYFILE.read_bytes()).hexdigest() == args.caddy_base_sha256, 'Caddy configuration changed; review before replacing'
        assert 'deploy/Caddyfile' in content
    # Avoid replacing fresher production snapshots with older repository samples.
    for relative, raw in list(content.items()):
        target = ROOT / relative
        if relative.startswith('public/') and relative.endswith('.json') and target.exists():
            try:
                old, new = json.loads(target.read_bytes()), json.loads(raw)
                if old.get('updatedAt', '') > new.get('updatedAt', ''):
                    del content[relative]
            except (ValueError, AttributeError):
                pass
    # Validation uses the archive catalogues even when a fresher deployed snapshot is retained.
    validation = load_archive(args.archive, args.sha256, args.revision)
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')
    backup = Path('/var/backups/footballknow') / f'expanded-{args.revision[:12]}-{stamp}'
    backup.mkdir(parents=True, mode=0o700)
    existed = []
    stopped = False
    applied = False
    try:
        stopped = True
        stop_worker()
        for relative in content:
            target = ROOT / relative
            if target.is_file():
                saved = backup / 'app' / relative
                saved.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(target, saved)
                existed.append(relative)
        for unit in UNITS:
            shutil.copy2(UNIT_ROOT / unit, backup / unit)
        if args.caddy_base_sha256:
            shutil.copy2(CADDYFILE, backup / 'Caddyfile')
        (backup / 'manifest.json').write_text(json.dumps({'revision': args.revision, 'existed': existed, 'files': list(content)}, indent=2))
        owner = (ROOT / 'public').stat()
        applied = True
        for relative, raw in content.items():
            target = ROOT / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            if relative.startswith(('public/', 'football/')):
                for parent in [target.parent, *target.parent.parents]:
                    if parent == ROOT:
                        break
                    os.chown(parent, owner.st_uid, owner.st_gid)
                    parent.chmod(0o755)
            temporary = target.with_name(target.name + '.release')
            temporary.write_bytes(raw)
            temporary.chmod(0o644)
            os.chown(temporary, owner.st_uid, owner.st_gid)
            os.replace(temporary, target)
        for folder in ['public/match-details', 'public/laliga/match-details', 'public/ucl/match-details', 'public/seriea/match-details', 'public/bundesliga/match-details', 'public/finance/history', 'public/finance/companies', 'public/finance/quote-cache', 'public/racing/horses']:
            path = ROOT / folder
            path.mkdir(parents=True, exist_ok=True)
            path.chmod(0o755)
            os.chown(path, owner.st_uid, owner.st_gid)
        for unit in UNITS:
            shutil.copy2(ROOT / 'deploy' / unit, UNIT_ROOT / unit)
        if args.caddy_base_sha256:
            run('caddy', 'validate', '--config', str(ROOT / 'deploy/Caddyfile'), '--adapter', 'caddyfile')
            temporary_caddy = CADDYFILE.with_name('Caddyfile.footballknow-release')
            shutil.copyfile(ROOT / 'deploy/Caddyfile', temporary_caddy)
            temporary_caddy.chmod(0o644)
            os.replace(temporary_caddy, CADDYFILE)
            run('systemctl', 'reload', 'caddy')
        run('systemctl', 'daemon-reload')
        run('systemctl', 'restart', 'footballknow-web')
        for attempt in range(20):
            try:
                health(validation)
                break
            except Exception:
                if attempt == 19:
                    raise
                time.sleep(1)
        release = {'revision': args.revision, 'publishedAt': datetime.now(timezone.utc).isoformat(), 'archiveSha256': args.sha256,
                   'codeHashes': {name: hashlib.sha256(raw).hexdigest() for name, raw in content.items() if not name.endswith('.json')}}
        (ROOT / 'public/release.json').write_text(json.dumps(release, ensure_ascii=False, indent=2))
        (ROOT / 'public/release.json').chmod(0o644)
        print(json.dumps({'installed': args.revision, 'files': len(content), 'backup': str(backup)}, ensure_ascii=False))
    except Exception:
        if applied:
            for relative in content:
                target = ROOT / relative
                if relative in existed:
                    shutil.copy2(backup / 'app' / relative, target)
                elif target.exists():
                    target.unlink()
            for unit in UNITS:
                shutil.copy2(backup / unit, UNIT_ROOT / unit)
            if args.caddy_base_sha256:
                shutil.copy2(backup / 'Caddyfile', CADDYFILE)
                run('systemctl', 'reload', 'caddy', check=False)
            run('systemctl', 'daemon-reload', check=False)
            run('systemctl', 'restart', 'footballknow-web', check=False)
        raise
    finally:
        if stopped:
            run('systemctl', 'start', 'footballknow-worker')
    print(run('systemctl', 'is-active', 'footballknow-web', 'footballknow-worker', 'caddy').stdout)


if __name__ == '__main__':
    main()
