#!/usr/bin/env python3
"""Validate a worker task.json — the exact scope of one assignment.

    python3 captain/task_spec.py path/to/task.json
    python3 captain/task_spec.py --json path/to/task.json   # normalised spec

Every brief must pass this before it is published. It enforces the things that
keep a worker's job narrow and safe:

  repo        Keshab1997/<name>
  worker      A, B or C
  task        unique lowercase letters/digits/hyphens
  allowed     1–40 exact repo-relative files, never shared surfaces or secrets
  commit      one short single-line conventional message
  check       {"kind": "preflight"} or a single named test file
  arena       {"branch": "auto", "base_sha": null | full 40-hex SHA}

Exits 0 with `valid: <task>` or 1 with the first problem found.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path, PurePosixPath
import re
import sys

OWNER = 'Keshab1997'
SHA = re.compile(r'[0-9a-f]{40}\Z')
REPO = re.compile(OWNER + r'/[A-Za-z0-9][A-Za-z0-9_.-]{0,99}\Z')
TASK = re.compile(r'[a-z0-9][a-z0-9-]{0,63}\Z')
MAX_FILES = 40

# Shared surfaces, generated files and anything carrying credentials stay with
# the Captain; a worker patch must never touch them.
RESERVED = {'pubspec.yaml', 'pubspec.lock', 'lib/main.dart', 'lib/app/app.dart',
            'lib/app/router.dart', 'firestore.rules', '.gitignore', '.gitmodules',
            '.gitattributes', 'agents.md', 'google-services.json', 'key.properties',
            'gh_app.py', 'device_pair.py', 'app-meta.json', 'setup.sh',
            'gh_token.txt', 'gh_refresh_token.txt', 'token.txt', 'pat.txt',
            'device_state.json'}
RESERVED_DIRS = {'.git', '.github', 'secret', 'secrets', '.dart_tool', 'android', 'ios'}
CREDENTIAL_SUFFIXES = ('.g.dart', '.jks', '.keystore', '.pem', '.key', '.p12', '.pfx')


class SpecError(ValueError):
    pass


def relative_path(value):
    if not isinstance(value, str) or not value or len(value) > 300:
        raise SpecError('Use exact repo-relative files, not globs or directory paths.')
    path = PurePosixPath(value)
    if (path.as_posix() != value or path.is_absolute() or value.startswith(('-', ':'))
            or not path.parts or '..' in path.parts
            or any(ch in '\\*?[' or ord(ch) < 32 for ch in value)):
        raise SpecError(f'Not a literal repo-relative path: {value!r}')
    return path


def allowed_path(value):
    path = relative_path(value)
    name = path.name.lower()
    parts = {part.lower() for part in path.parts}
    if (str(path).lower() in RESERVED
            or parts & RESERVED_DIRS
            or name.startswith('.env')
            or name.endswith(CREDENTIAL_SUFFIXES)):
        raise SpecError(f'Reserved or credential path, not assignable to a worker: {path}')
    return str(path)


def validate_task(data):
    required = {'repo', 'worker', 'task', 'allowed', 'commit', 'check'}
    optional = {'arena', 'base_sha', 'base_branch', 'tracker'}
    if not isinstance(data, dict) or not required.issubset(data) or not set(data).issubset(required | optional):
        raise SpecError('Task JSON needs repo, worker, task, allowed, commit, check; '
                        'optional arena, base_sha, base_branch, tracker.')
    if not isinstance(data['repo'], str) or not REPO.fullmatch(data['repo']):
        raise SpecError(f'Repo must be {OWNER}/<name>.')
    if data['worker'] not in ('A', 'B', 'C'):
        raise SpecError('Worker must be A, B, or C.')
    if not isinstance(data['task'], str) or not TASK.fullmatch(data['task']):
        raise SpecError('Use a unique lowercase task ID with letters, digits, or hyphens.')
    if not isinstance(data['allowed'], list) or not 1 <= len(data['allowed']) <= MAX_FILES:
        raise SpecError(f'List 1–{MAX_FILES} exact allowed files.')
    files = [allowed_path(name) for name in data['allowed']]
    if len(set(files)) != len(files):
        raise SpecError('Duplicate allowed files.')
    message = data['commit']
    if (not isinstance(message, str) or not 1 <= len(message) <= 160
            or message.strip() != message or any(ord(c) < 32 for c in message)):
        raise SpecError('Use a short, single-line commit message.')
    if 'arena' in data and ('base_sha' in data or 'base_branch' in data):
        raise SpecError('Use either arena.{branch, base_sha} or base_sha/base_branch, not both.')
    if 'arena' in data:
        arena = data['arena']
        if (not isinstance(arena, dict) or set(arena) != {'branch', 'base_sha'}
                or arena.get('branch') != 'auto'
                or not (arena.get('base_sha') is None or SHA.fullmatch(str(arena.get('base_sha'))))):
            raise SpecError('arena needs branch "auto" and base_sha (full 40-hex SHA or null).')
    elif 'base_branch' in data and data['base_branch'] not in (None, 'main'):
        raise SpecError('Only base_branch "main" is supported in the Arena lane.')
    if 'base_sha' in data and data['base_sha'] is not None:
        if not isinstance(data['base_sha'], str) or not SHA.fullmatch(data['base_sha']):
            raise SpecError('base_sha must be a full commit SHA or null.')
    if data.get('tracker') is not None and not (
            isinstance(data['tracker'], str)
            and re.fullmatch(rf'https://github\.com/{OWNER}/[A-Za-z0-9._-]+/issues/\d+', data['tracker'])):
        raise SpecError(f'tracker must be a {OWNER} GitHub issue URL or null.')
    check = data['check']
    if not isinstance(check, dict) or 'kind' not in check:
        raise SpecError('Set a check: {"kind": "preflight"} or {"kind": "test", "test": "test/x_test.dart"}.')
    if set(check) == {'kind'} and check['kind'] == 'preflight':
        pass
    elif set(check) == {'kind', 'test'} and check['kind'] == 'test':
        test = relative_path(check['test'])
        if test.parts[0] != 'test' or len(test.parts) < 2 or not test.name.endswith('_test.dart'):
            raise SpecError('Specify one matching test/<name>_test.dart file.')
    else:
        raise SpecError('Invalid check. Allowed: {"kind":"preflight"} or {"kind":"test","test":...}.')
    return data


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('task_file', type=Path, help='task.json to validate')
    parser.add_argument('--json', action='store_true', help='print the normalised spec')
    args = parser.parse_args()
    try:
        spec = validate_task(json.loads(args.task_file.read_text()))
    except (OSError, json.JSONDecodeError, SpecError) as exc:
        print(f'invalid: {exc}', file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(spec, indent=1, ensure_ascii=False))
    else:
        print(f'valid: {spec["task"]} ({spec["worker"]} on {spec["repo"]}, '
              f'{len(spec["allowed"])} files, check={spec["check"]["kind"]})')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
