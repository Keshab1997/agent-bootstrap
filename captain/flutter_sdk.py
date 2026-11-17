#!/usr/bin/env python3
"""Install/reuse an exact, verified Flutter SDK on Linux x86-64.

Downloads only from the official Flutter release archive. No sudo, shell
profiles, global Git configuration, credentials, or project files are changed.
"""
from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys
import tempfile
from urllib.request import urlopen

BASE_URL = 'https://storage.googleapis.com/flutter_infra_release/releases/'
VERSION = re.compile(r'[1-9][0-9]*\.[0-9]+\.[0-9]+\Z')
CACHE = Path('/var/tmp') / f'agent-bootstrap-flutter-{os.getuid()}'


class SDKError(RuntimeError):
    pass


def release(manifest, version):
    if not VERSION.fullmatch(version):
        raise SDKError('Pin an exact stable Flutter version, for example 3.50.0.')
    expected = f'stable/linux/flutter_linux_{version}-stable.tar.xz'
    for item in manifest.get('releases', []):
        if (item.get('version') == version and item.get('channel') == 'stable'
                and item.get('dart_sdk_arch', 'x64') == 'x64' and item.get('archive') == expected):
            digest = item.get('sha256', '')
            if isinstance(digest, str) and re.fullmatch(r'[0-9a-f]{64}', digest):
                return BASE_URL + expected, digest
            raise SDKError(f'Official Flutter {version} release has no valid SHA-256.')
    raise SDKError(f'No official Linux x86-64 stable Flutter {version}; ask the Captain for the correct pin.')


def tool_env(env, root=None, cache=CACHE):
    result = dict(env)
    result.pop('PUB_HOSTED_URL', None)
    result.pop('FLUTTER_STORAGE_BASE_URL', None)
    result.pop('FLUTTER_ROOT', None)
    result['FLUTTER_SUPPRESS_ANALYTICS'] = 'true'
    result['CI'] = 'true'
    result['PUB_CACHE'] = str(cache / 'pub-cache')
    if root is not None:
        result['PATH'] = os.pathsep.join((str(root / 'bin'), result.get('PATH', os.defpath)))
    return result


def installed_version(root, env):
    exe = root / 'bin' / 'flutter'
    if not exe.is_file() or not (root / 'bin' / 'dart').is_file():
        return None
    try:
        p = subprocess.run([str(exe), '--version', '--machine'], cwd=root, env=env,
                           capture_output=True, text=True, timeout=90)
        if p.returncode == 0:
            return json.loads(p.stdout).get('frameworkVersion')
    except (OSError, ValueError, subprocess.TimeoutExpired):
        pass
    return None


def prepare_cache(cache):
    cache.mkdir(mode=0o700, parents=True, exist_ok=True)
    state = cache.stat()
    if cache.is_symlink() or state.st_uid != os.getuid() or state.st_mode & 0o077:
        raise SDKError(f'Refusing to use a non-private Flutter cache: {cache}')


def open_official(url, timeout):
    response = urlopen(url, timeout=timeout)
    if response.geturl() != url:
        response.close()
        raise SDKError('Unexpected redirect from the official Flutter download URL.')
    return response


def download(url, filename, expected_sha):
    sha = hashlib.sha256()
    with open_official(url, timeout=90) as source, filename.open('wb') as output:
        while chunk := source.read(1024 * 1024):
            sha.update(chunk)
            output.write(chunk)
    if sha.hexdigest() != expected_sha:
        raise SDKError('Official Flutter archive did not match the manifest SHA-256. Nothing was installed.')


def install(version, root, cache, env):
    # Extract and validate in private staging; never reuse a partial install.
    print(f'Installing Flutter {version} from the official archive (cold cache)…', file=sys.stderr, flush=True)
    with open_official(BASE_URL + 'releases_linux.json', timeout=20) as stream:
        url, digest = release(json.load(stream), version)
    with tempfile.TemporaryDirectory(prefix='.install-', dir=cache) as temp:
        temp = Path(temp)
        archive = temp / 'flutter.tar.xz'
        download(url, archive, digest)
        subprocess.run(['tar', '-xf', str(archive), '-C', str(temp), '--no-same-owner'],
                       check=True, timeout=300, env=env)
        unpacked = temp / 'flutter'
        if unpacked.is_symlink() or installed_version(unpacked, env) != version:
            raise SDKError(f'Official archive did not produce a usable Flutter {version} SDK.')
        unpacked.rename(root)


def ensure_flutter(version, env, cache=CACHE):
    if not VERSION.fullmatch(version):
        raise SDKError('Pin an exact stable Flutter version, for example 3.50.0.')
    try:
        env = tool_env(env, cache=cache)
        existing = shutil.which('flutter', path=env.get('PATH', os.defpath))
        if existing:
            other = Path(existing).resolve().parent.parent
            if installed_version(other, env) == version:
                prepare_cache(cache)
                return other
        if not (sys.platform == 'linux' and platform.machine().lower() in {'x86_64', 'amd64'}):
            raise SDKError('Automatic install needs Linux x86-64 or an exact trusted Flutter SDK on PATH.')
        prepare_cache(cache)
        root = cache / version
        with (cache / (version + '.lock')).open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            if root.exists() or root.is_symlink():
                if root.is_symlink() or installed_version(root, env) != version:
                    raise SDKError(f'Invalid Flutter cache at {root}; inspect it before replacing anything.')
            else:
                install(version, root, cache, env)
        return root
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        raise SDKError(f'Flutter {version} setup failed: {exc}') from exc


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('version', help='exact stable Flutter version')
    args = parser.parse_args()
    env = {k: v for k, v in os.environ.items() if not k.startswith(('GIT_', 'GH_', 'GITHUB_'))}
    try:
        root = ensure_flutter(args.version, env)
    except SDKError as exc:
        parser.exit(1, str(exc) + '\n')
    print(root)


if __name__ == '__main__':
    main()
