#!/usr/bin/env python3
"""Install/reuse an exact, verified Flutter SDK on Linux x86-64.

Downloads from the official Flutter release archive — or, when the warm cache
is reachable and its sha256 matches, from Keshab's public, sha256-pinned
`sdk-cache` GitHub release (built by flutter-bootstrap/pack.sh; official SDK
files only, never credentials). Any warm-cache problem falls back to the
official archive. No sudo, shell profiles, global Git configuration,
credentials, or project files are changed. FB_WARM_CACHE=0 disables the warm
path; FB_WARM_CACHE_BASE overrides the release base URL.
"""
from __future__ import annotations

import argparse
import fcntl
import hashlib
from http.client import HTTPException
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys
import tempfile
import time
from urllib.error import HTTPError
from urllib.request import Request, urlopen

BASE_URL = 'https://storage.googleapis.com/flutter_infra_release/releases/'
VERSION = re.compile(r'[1-9][0-9]*\.[0-9]+\.[0-9]+\Z')
CONTENT_RANGE = re.compile(r'bytes ([0-9]+)-([0-9]+)/([0-9]+|\*)\Z')
CACHE = Path('/var/tmp') / f'agent-bootstrap-flutter-{os.getuid()}'
CHUNK_BYTES = 1024 * 1024
MAX_STALLS = 5
MAX_SEGMENTS = 32
RETRYABLE_HTTP = frozenset({408, 429, 500, 502, 503, 504})
WARM_BASE = 'https://github.com/Keshab1997/flutter-bootstrap/releases/download/sdk-cache'
WARM_SEGMENTS = 6


class SDKError(RuntimeError):
    pass


class _LocalWriteError(Exception):
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


def retryable(exc):
    if isinstance(exc, SDKError):
        return False
    if isinstance(exc, HTTPError):
        return exc.code in RETRYABLE_HTTP
    return isinstance(exc, (OSError, EOFError, HTTPException))


def open_official(url, timeout, offset=0):
    target = url if offset == 0 else Request(
        url, headers={'Range': f'bytes={offset}-', 'Connection': 'close'})
    response = urlopen(target, timeout=timeout)
    try:
        actual = response.geturl()
    except Exception:
        response.close()
        raise
    if actual != url:
        response.close()
        raise SDKError('Unexpected redirect from the official Flutter download URL.')
    return response


def fetch_manifest(url):
    for attempt in range(1, MAX_STALLS + 1):
        try:
            with open_official(url, timeout=30) as stream:
                raw = stream.read()
            break
        except Exception as exc:
            if isinstance(exc, HTTPError):
                exc.close()
            if not retryable(exc) or attempt >= MAX_STALLS:
                raise
            time.sleep(min(2 ** (attempt - 1), 8))
    return json.loads(raw.decode('utf-8'))


def stream_bounds(response, offset):
    headers = getattr(response, 'headers', None)
    status = getattr(response, 'status', None)
    raw_etag = (headers.get('ETag') or '').strip() if headers else ''
    etag = raw_etag if raw_etag and not raw_etag.startswith('W/') else None
    if offset > 0:
        if status == 206:
            raw_range = (headers.get('Content-Range') or '').strip() if headers else ''
            match = CONTENT_RANGE.fullmatch(raw_range)
            if not match:
                raise SDKError('Official Flutter archive returned an invalid Content-Range header.')
            start, end, total_raw = int(match.group(1)), int(match.group(2)), match.group(3)
            total = None if total_raw == '*' else int(total_raw)
            if start != offset or end < start or (total is not None and end >= total):
                raise SDKError('Official Flutter archive returned an unexpected byte range.')
            return offset, total, etag
        if status not in (None, 200):
            raise SDKError(f'Unexpected HTTP status {status} while resuming the official Flutter archive.')
    total = None
    if headers:
        length = (headers.get('Content-Length') or '').strip()
        if length:
            if not length.isdigit():
                raise SDKError('Official Flutter archive returned an invalid Content-Length header.')
            total = int(length)
    return 0, total, etag


def download(url, filename, expected_sha):
    # Resume across transient TLS/stream drops with HTTP Range, then verify the
    # complete archive against the official manifest SHA-256 before unpacking.
    sha = hashlib.sha256()
    offset = 0
    expected_total = None
    expected_etag = None
    stalls = 0
    segments = 0
    with filename.open('wb') as output:
        while True:
            segments += 1
            before = offset
            try:
                with open_official(url, timeout=90, offset=offset) as source:
                    start, total, etag = stream_bounds(source, offset)
                    if start == 0 and offset > 0:
                        try:
                            output.seek(0)
                            output.truncate()
                        except OSError as exc:
                            raise _LocalWriteError(exc) from exc
                        sha = hashlib.sha256()
                        offset = 0
                        before = 0
                        expected_total = None
                        expected_etag = None
                    if start > 0 and expected_etag and etag and etag != expected_etag:
                        raise SDKError('Official Flutter archive changed mid-download. Nothing was installed.')
                    if etag and expected_etag is None:
                        expected_etag = etag
                    if total is not None:
                        if expected_total is not None and total != expected_total:
                            raise SDKError('Official Flutter archive size changed mid-download. Nothing was installed.')
                        expected_total = total
                    while chunk := source.read(CHUNK_BYTES):
                        try:
                            output.write(chunk)
                        except OSError as exc:
                            raise _LocalWriteError(exc) from exc
                        sha.update(chunk)
                        offset += len(chunk)
                        if expected_total is not None and offset > expected_total:
                            raise SDKError('Official Flutter archive exceeded Content-Length. Nothing was installed.')
                if expected_total is not None and offset < expected_total:
                    raise EOFError(f'Official archive closed early at {offset}/{expected_total} bytes.')
                break
            except _LocalWriteError as exc:
                raise exc.args[0] from exc
            except Exception as exc:
                if isinstance(exc, HTTPError):
                    exc.close()
                if not retryable(exc):
                    raise
                if offset > 0 and (expected_total is None or offset == expected_total) and sha.copy().hexdigest() == expected_sha:
                    break
                output.flush()
                progressed = offset > before
                stalls = 0 if progressed else stalls + 1
                if stalls >= MAX_STALLS or segments >= MAX_SEGMENTS:
                    raise SDKError(
                        f'Official Flutter archive download failed after {segments} attempts '
                        f'({offset} bytes received): {exc}'
                    ) from exc
                mib = offset / (1024 * 1024)
                print(
                    f'Retrying Flutter archive download from {mib:.1f} MiB '
                    f'(attempt {segments + 1}, {exc.__class__.__name__})…',
                    file=sys.stderr,
                    flush=True,
                )
                time.sleep(0.5 if progressed else min(2 ** (stalls - 1), 8))
    if expected_total is not None and offset != expected_total:
        raise SDKError('Official Flutter archive length did not match Content-Length. Nothing was installed.')
    if sha.hexdigest() != expected_sha:
        raise SDKError('Official Flutter archive did not match the manifest SHA-256. Nothing was installed.')


def _warm_enabled(env):
    return str(env.get('FB_WARM_CACHE', '1')) != '0'


def _warm_base(env):
    return str(env.get('FB_WARM_CACHE_BASE') or WARM_BASE).rstrip('/')


def _warm_manifest(env):
    """The pinned warm-cache manifest. The probe goes through the module-level
    urlopen so offline/mocked environments fail here cheaply and the official
    path takes over."""
    with urlopen(_warm_base(env) + '/cache-manifest.json', timeout=15) as stream:
        manifest = json.loads(stream.read().decode('utf-8'))
    return manifest if isinstance(manifest, dict) else {}


def _valid_entry(entry) -> bool:
    return (isinstance(entry, dict) and isinstance(entry.get('asset'), str)
            and bool(re.fullmatch(r'[0-9a-f]{64}', str(entry.get('sha256', ''))))
            and isinstance(entry.get('bytes'), int) and entry['bytes'] > 0)


def _ensure_zstd(cache, env, manifest):
    """System zstd, else the sha-pinned self-contained bundle from the warm
    release (binary + its non-libc shared libs, run via LD_LIBRARY_PATH),
    else (None, None) so the caller falls back to the official archive."""
    found = shutil.which('zstd')
    if found:
        return [found], env
    tools = cache / 'tools'
    binary = tools / 'bin' / 'zstd'
    if not binary.is_file():
        entry = (manifest.get('tools') or {}).get('zstd_bundle')
        if not _valid_entry(entry) or not shutil.which('curl'):
            return None, None
        bundle = cache / '.zstd-bundle.tar.gz'
        try:
            if not _warm_download(_warm_base(env) + '/' + entry['asset'],
                                  bundle, entry['sha256'], entry['bytes']):
                return None, None
            tools.mkdir(parents=True, exist_ok=True)
            if subprocess.run(['tar', '-xzf', str(bundle), '-C', str(tools)],
                              capture_output=True, timeout=120).returncode != 0:
                return None, None
        finally:
            bundle.unlink(missing_ok=True)
    if not binary.is_file():
        return None, None
    zenv = dict(env)
    lib = str(tools / 'lib')
    zenv['LD_LIBRARY_PATH'] = lib + (os.pathsep + zenv['LD_LIBRARY_PATH']
                                     if zenv.get('LD_LIBRARY_PATH') else '')
    return [str(binary)], zenv


def _warm_download(url, target, expected_sha, size):
    """Segmented download: GitHub's CDN throttles one sustained stream to
    ~20-30 MB/s after its burst credit, while parallel ranges each get their
    own bucket (~150+ MB/s aggregate on 6 segments, measured). True only when
    the assembled file matches size and sha256."""
    chunk = -(-size // WARM_SEGMENTS)
    procs = []
    for i in range(WARM_SEGMENTS):
        start = i * chunk
        if start >= size:
            break
        end = min(start + chunk, size) - 1
        part = target.with_name(f'{target.name}.part{i}')
        procs.append((part, subprocess.Popen(
            ['curl', '-fsSL', '--retry', '3', '--retry-delay', '1', '--max-time', '900',
             '-r', f'{start}-{end}', '-o', str(part), url],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)))
    ok = bool(procs) and all(p.wait() == 0 for _, p in procs)
    if ok:
        with target.open('wb') as out:
            for part, _ in procs:
                with part.open('rb') as fh:
                    shutil.copyfileobj(fh, out, 1024 * 1024)
    for part, _ in procs:
        part.unlink(missing_ok=True)
    if not ok or target.stat().st_size != size:
        target.unlink(missing_ok=True)
        return False
    sha = hashlib.sha256()
    with target.open('rb') as fh:
        while block := fh.read(1024 * 1024):
            sha.update(block)
    if sha.hexdigest() != expected_sha:
        target.unlink(missing_ok=True)
        return False
    return True


def _install_warm(version, root, cache, env):
    """Install from the warm cache; True when `root` holds a verified SDK.
    Every failure mode returns False so the caller can use the official
    archive; `root` is only ever created by the final atomic rename."""
    manifest = _warm_manifest(env)
    entry = (manifest.get('entries') or {}).get(version)
    if not _valid_entry(entry):
        return False
    if not shutil.which('curl'):
        return False
    zstd, zenv = _ensure_zstd(cache, env, manifest)
    if zstd is None:
        return False
    started = time.time()
    with tempfile.TemporaryDirectory(prefix='.warm-', dir=cache) as temp:
        temp = Path(temp)
        archive = temp / Path(entry['asset']).name
        if not _warm_download(_warm_base(env) + '/' + entry['asset'],
                              archive, entry['sha256'], entry['bytes']):
            return False
        decoder = subprocess.Popen(zstd + ['-dcq', str(archive)], stdout=subprocess.PIPE, env=zenv)
        unpacker = subprocess.Popen(['tar', '-xf', '-', '-C', str(temp), '--no-same-owner'],
                                    stdin=decoder.stdout, env=env)
        if decoder.stdout:
            decoder.stdout.close()
        if unpacker.wait(timeout=600) != 0 or decoder.wait(timeout=60) != 0:
            return False
        archive.unlink(missing_ok=True)
        dirs = sorted(p for p in temp.iterdir() if p.is_dir())
        unpacked = temp / 'flutter' if (temp / 'flutter').is_dir() else (dirs[0] if len(dirs) == 1 else None)
        if unpacked is None or unpacked.is_symlink() or installed_version(unpacked, env) != version:
            return False
        unpacked.rename(root)
    print(f'Installed Flutter {version} from the warm cache in {time.time() - started:.0f}s.',
          file=sys.stderr, flush=True)
    return True


def restore_pub_cache(cache, env):
    """Best-effort: seed an empty PUB_CACHE from the warm release's pub-cache
    snapshot (sha256-pinned; public pub.dev packages only). Never raises,
    never touches a non-empty cache, and costs no network when disabled."""
    try:
        if not _warm_enabled(env):
            return False
        # Honour the caller's PUB_CACHE (setup.sh uses /var/tmp/pub-cache);
        # fall back to a pub-cache next to the SDK cache.
        pub = Path(str(env['PUB_CACHE'])) if env.get('PUB_CACHE') else cache / 'pub-cache'
        if pub.exists() and any(pub.iterdir()):
            return False
        manifest = _warm_manifest(env)
        entry = (manifest.get('pub') or {}).get('cache')
        if not _valid_entry(entry) or not shutil.which('curl'):
            return False
        zstd, zenv = _ensure_zstd(cache, env, manifest)
        if zstd is None:
            return False
        started = time.time()
        prepare_cache(cache)
        pub.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        # Stage beside the destination so the final rename stays on one filesystem.
        stage = pub.parent if pub.parent != cache else cache
        with tempfile.TemporaryDirectory(prefix='.pubwarm-', dir=str(stage)) as temp:
            temp = Path(temp)
            archive = temp / Path(entry['asset']).name
            if not _warm_download(_warm_base(env) + '/' + entry['asset'],
                                  archive, entry['sha256'], entry['bytes']):
                return False
            staging = temp / 'out'
            staging.mkdir()
            decoder = subprocess.Popen(zstd + ['-dcq', str(archive)],
                                       stdout=subprocess.PIPE, env=zenv)
            unpacker = subprocess.Popen(['tar', '-xf', '-', '-C', str(staging), '--no-same-owner'],
                                        stdin=decoder.stdout, env=env)
            if decoder.stdout:
                decoder.stdout.close()
            if unpacker.wait(timeout=600) != 0 or decoder.wait(timeout=60) != 0:
                return False
            archive.unlink(missing_ok=True)
            extracted = staging / 'pub-cache'
            if not extracted.is_dir():
                dirs = [p for p in staging.iterdir() if p.is_dir()]
                if len(dirs) != 1:
                    return False
                extracted = dirs[0]
            if pub.exists():
                shutil.rmtree(pub)
            extracted.rename(pub)
        print(f'Seeded PUB_CACHE from the warm snapshot in {time.time() - started:.0f}s.',
              file=sys.stderr, flush=True)
        return True
    except Exception:
        return False


def install(version, root, cache, env):
    # Extract and validate in private staging; never reuse a partial install.
    if _warm_enabled(env):
        try:
            if _install_warm(version, root, cache, env):
                return
        except Exception as exc:  # any cache problem -> the official path
            print(f'Warm cache unavailable ({exc.__class__.__name__}); using the official archive…',
                  file=sys.stderr, flush=True)
    print(f'Installing Flutter {version} from the official archive (cold cache)…', file=sys.stderr, flush=True)
    url, digest = release(fetch_manifest(BASE_URL + 'releases_linux.json'), version)
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
                restore_pub_cache(cache, env)
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
        restore_pub_cache(cache, env)
        return root
    except (OSError, EOFError, ValueError, HTTPException, subprocess.SubprocessError) as exc:
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
