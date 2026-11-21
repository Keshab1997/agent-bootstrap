#!/usr/bin/env python3
"""Fetch, start, check, diff, publish, mention, or review one bounded Captain task.

Device-Flow tasks (default) manage an isolated clone under the workbench and
push to agent/<worker>/<task> using gh_app.py pairing; optional Arena-linked
tasks checkpoint the attached arena/* branch. Nothing here opens or closes a
PR, writes main, runs CI, resets edits, or starts an authorization flow.
"""
from __future__ import annotations

import argparse
import base64
from contextlib import contextmanager
import fcntl
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
import tempfile

from flutter_sdk import SDKError, VERSION, ensure_flutter, tool_env

OWNER = 'Keshab1997'
ROOT = Path.home() / 'agent-workbench'
BOOTSTRAP = Path(__file__).resolve().parent.parent
SHA = re.compile(r'[0-9a-f]{40}(?:[0-9a-f]{24})?\Z')
REPO = re.compile(OWNER + r'/[A-Za-z0-9][A-Za-z0-9_.-]{0,99}\Z')
TASK = re.compile(r'[a-z0-9][a-z0-9-]{0,63}\Z')
BRANCH_REF = re.compile(r'(?:main|(?:agent|arena)/[A-Za-z0-9._/-]+)\Z')
ISSUE_URL = re.compile(r'https://github\.com/(' + OWNER + r')/([A-Za-z0-9][A-Za-z0-9_.-]{0,99})/issues/(\d+)\Z')
BRIEF_URL = re.compile(
    r'https://github\.com/(' + OWNER + r'/[A-Za-z0-9][A-Za-z0-9_.-]{0,99})/(?:blob|tree)/'
    r'([0-9a-f]{40})/docs/agent-briefs/([a-z0-9][a-z0-9-]{0,63})/([a-z0-9][a-z0-9-]{0,63})'
    r'/(?:BRIEF\.md|task\.json)(?:[?#].*)?\Z'
)
KEY_PATTERN = re.compile(rb'(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,}|-----BEGIN (?:[A-Z0-9]+ )?PRIVATE KEY-----)')
RESERVED = {'pubspec.yaml', 'pubspec.lock', 'lib/main.dart', 'lib/app/app.dart',
            'lib/app/router.dart', 'firestore.rules', '.gitignore', '.gitmodules',
            '.gitattributes', 'gh_app.py', 'device_pair.py', 'app-meta.json',
            'setup.sh', 'vault.py'}

# Only the independently paired worker's own saved token. Git sees it via
# the credential protocol, never a command argument or a token-bearing URL.
HELPER = r'''!f() {
    [ "$1" = get ] || return 0;
    protocol= host= path=;
    while IFS= read -r line && [ -n "$line" ]; do
      case "$line" in
        protocol=*) protocol=${line#protocol=} ;;
        host=*) host=${line#host=} ;;
        path=*) path=${line#path=} ;;
      esac;
    done;
    [ "$protocol" = https ] && [ "$host" = github.com ] &&
      [ "$path" = "$WORKER_GIT_PATH" ] && [ -s "$WORKER_TOKEN_FILE" ] || return 0;
    printf "username=x-access-token\npassword="; cat -- "$WORKER_TOKEN_FILE";
}; f'''


class LaneError(RuntimeError):
    pass


def is_sha(value):
    return isinstance(value, str) and SHA.fullmatch(value) is not None


def relative_path(value):
    if not isinstance(value, str) or not value or len(value) > 300:
        raise LaneError('Use exact repo-relative files, not globs or directory paths.')
    path = PurePosixPath(value)
    if (path.as_posix() != value or path.is_absolute() or value.startswith(('-', ':'))
            or not path.parts or '..' in path.parts
            or any(ch in '\\*?[' or ord(ch) < 32 for ch in value)):
        raise LaneError(f'Not a literal repo-relative path: {value!r}')
    return path


def allowed_path(value):
    path = relative_path(value)
    name = path.name.lower()
    parts = [p.lower() for p in path.parts]
    if (str(path).lower() in RESERVED
            or set(parts) & {'.git', '.github', 'secret', 'secrets', '.dart_tool'}
            or parts[0] in {'android', 'ios', 'tool'}
            or name.startswith('.env') or name.endswith(('.g.dart', '.jks', '.keystore', '.pem', '.key', '.p12', '.pfx'))
            or name in {'agents.md', 'google-services.json', 'key.properties', 'gh_token.txt',
                        'gh_refresh_token.txt', 'token.txt', 'pat.txt', 'device_state.json'}):
        raise LaneError(f'Reserved or credential path, not assignable to a worker: {path}')
    return str(path)


def validate_branch_ref(value):
    if (not isinstance(value, str) or not BRANCH_REF.fullmatch(value)
            or '..' in value or value.endswith(('/', '.lock')) or '//' in value):
        raise LaneError(f'Invalid branch ref {value!r}; expected main, agent/*, or arena/*.')
    return value


def validate_task(data):
    required = {'repo', 'worker', 'task', 'allowed', 'commit', 'check'}
    optional = {'arena', 'base_sha', 'base_branch', 'tracker'}
    if not isinstance(data, dict) or not required.issubset(data) or not set(data).issubset(required | optional):
        raise LaneError('Task JSON needs repo, worker, task, allowed, commit, check, and optional base_sha/base_branch/tracker/arena.')
    if not isinstance(data['repo'], str) or not REPO.fullmatch(data['repo']) or data['repo'].lower().endswith('.git'):
        raise LaneError(f'Repo must be {OWNER}/<name>.')
    if data['worker'] not in ('A', 'B', 'C'):
        raise LaneError('Worker must be A, B, or C.')
    if not isinstance(data['task'], str) or not TASK.fullmatch(data['task']):
        raise LaneError('Use a unique lowercase task ID with letters, digits, or hyphens.')
    if not isinstance(data['allowed'], list) or not 1 <= len(data['allowed']) <= 40:
        raise LaneError('List 1–40 exact allowed files.')
    files = [allowed_path(name) for name in data['allowed']]
    if len(set(files)) != len(files):
        raise LaneError('Duplicate allowed files.')
    message = data['commit']
    if (not isinstance(message, str) or not 1 <= len(message) <= 160
            or message.strip() != message or any(ord(c) < 32 for c in message)):
        raise LaneError('Use a short, single-line commit message.')
    if 'arena' in data and ('base_sha' in data or 'base_branch' in data):
        raise LaneError('Use either arena.{branch, base_sha} or top-level base_sha/base_branch, not both.')
    if 'arena' in data:
        arena = data['arena']
        if (not isinstance(arena, dict) or set(arena) != {'branch', 'base_sha'}
                or not isinstance(arena['branch'], str)
                or not (arena['branch'] == 'auto' or arena['branch'].startswith('arena/'))
                or not (arena['base_sha'] is None or is_sha(arena['base_sha']))):
            raise LaneError('arena needs branch (arena/* or auto) and base_sha (full SHA or null for a first task).')
    if 'base_sha' in data and data['base_sha'] is not None and not is_sha(data['base_sha']):
        raise LaneError('base_sha must be a full commit SHA or null.')
    if 'base_branch' in data and data['base_branch'] is not None:
        validate_branch_ref(data['base_branch'])
    if 'tracker' in data and data['tracker'] is not None:
        if not isinstance(data['tracker'], str) or not ISSUE_URL.fullmatch(data['tracker']):
            raise LaneError(f'tracker must be a {OWNER} GitHub issue URL or null.')
    check = data['check']
    if not isinstance(check, dict) or 'kind' not in check:
        raise LaneError('Set a check profile: preflight, flutter, pytest, or selftest.')
    kind = check['kind']
    if kind in ('preflight', 'selftest') and set(check) == {'kind'}:
        pass
    elif kind == 'flutter' and set(check) == {'kind', 'version', 'test'}:
        if not isinstance(check['version'], str) or not VERSION.fullmatch(check['version']):
            raise LaneError('Flutter needs an exact stable SDK pin, not the minimum SDK version.')
        test = relative_path(check['test'])
        if test.parts[0] != 'test' or len(test.parts) < 2 or not test.name.endswith('_test.dart'):
            raise LaneError('Specify one matching test/<name>_test.dart file.')
    elif kind == 'pytest' and set(check) == {'kind', 'target'}:
        test = relative_path(check['target'])
        if test.parts[0] not in ('test', 'tests') or (len(test.parts) > 1 and test.suffix != '.py'):
            raise LaneError('Pytest target must be tests, test, or one Python file within them.')
    else:
        raise LaneError('Invalid check profile or unsupported check fields.')
    return data


def command_env():
    return {k: v for k, v in os.environ.items()
            if not k.startswith(('GIT_', 'GH_', 'GITHUB_', 'WORKER_'))}


def items(result):
    return [os.fsdecode(part) for part in result.stdout.split(b'\0') if part]


def save_json(path, data):
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=path.parent,
                                     prefix='.state-', delete=False) as out:
        try:
            json.dump(data, out, ensure_ascii=False, indent=2)
            out.write('\n')
            out.flush()
            os.replace(out.name, path)
        finally:
            if os.path.exists(out.name):
                os.unlink(out.name)


def inspect_patch(patch):
    # A heuristic for common credential forms, not a substitute for review.
    if KEY_PATTERN.search(patch):
        raise LaneError('Possible credential in patch. Stop without copying it to logs or chat.')


class Lane:
    def __init__(self, task, root=ROOT, *, checkout=None, review=False, _test_remote=None):
        self.task = validate_task(task)
        self.worker, self.slug = task['worker'], task['task']
        self.arena = task.get('arena')
        self.linked = self.arena is not None and not review
        self.branch = None if self.arena is not None else f'agent/{self.worker}/{self.slug}'
        name = task['repo'].split('/')[1]
        root = Path(root).resolve()
        if self.linked or review:
            if checkout is None:
                raise LaneError('Pass --checkout with the verified repository worktree path.')
            self.dir = Path(checkout).resolve()
        else:
            if checkout is not None:
                raise LaneError('Standalone manages its own clone; do not pass an Arena checkout.')
            self.dir = root / 'repos' / self.worker / name
        self.states = root / 'tasks' / ('linked' if self.linked else 'standalone') / self.worker / name
        self.state_file = self.states / (self.slug + '.json')
        self.origin_record = self.states / '.origin.json'
        self.remote = _test_remote or f'https://github.com/{task["repo"]}.git'
        self.production = _test_remote is None
        secrets = Path(os.environ.get('GH_SECRET_DIR') or BOOTSTRAP / 'secrets')
        self.token_file = Path(os.environ.get('GITHUB_TOKEN_FILE') or secrets / 'gh_token.txt').resolve()

    @contextmanager
    def locked(self):
        self.states.mkdir(mode=0o700, parents=True, exist_ok=True)
        with (self.states / '.lock').open('a') as lock:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as exc:
                raise LaneError('Another command is running for this worker/repo. Do not run a duplicate.') from exc
            yield

    def git(self, *args, cwd=None, network=False, check=True, index=None):
        env = command_env()
        env.update(GIT_TERMINAL_PROMPT='0', GIT_NO_REPLACE_OBJECTS='1',
                   GIT_ALLOW_PROTOCOL='https' if self.production else 'file')
        opts = ['-c', 'core.fileMode=false', '-c', 'core.fsmonitor=false', '-c', 'http.followRedirects=false']
        if args[0] == 'push':
            opts += ['-c', 'remote.origin.mirror=false']
        if self.linked and self.production:
            # Use the existing Git access for the linked checkout. Do not put
            # independent OAuth credentials in this path or try to reopen it.
            if 'GIT_ASKPASS' in os.environ:
                env['GIT_ASKPASS'] = os.environ['GIT_ASKPASS']
        else:
            env.update(GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL=os.devnull, GIT_ASKPASS='/bin/false')
            opts += ['-c', 'credential.helper=']
            if self.production and network and self.token_file.is_file():
                env.update(WORKER_TOKEN_FILE=str(self.token_file), WORKER_GIT_PATH=f'{self.task["repo"]}.git')
                opts += ['-c', 'credential.useHttpPath=true', '-c', 'credential.helper=' + HELPER]
        if index is not None:
            env['GIT_INDEX_FILE'] = str(index)
        p = subprocess.run(['git', *opts, '--literal-pathspecs', *args], cwd=cwd or self.dir,
                           env=env, capture_output=True, timeout=120)
        if check and p.returncode:
            if network:
                # Don't surface an upstream response, helper output or URL
                # that could contain credentials.
                hint = ('Check the linked chat can still push; do not replace its access.' if self.linked else
                        'Check network, repo permissions and your workspace’s own saved login with gh_app.py status.')
                raise LaneError(f'git {args[0]} failed (exit {p.returncode}). {hint} Keep your work.')
            error = p.stderr.decode(errors='replace').strip()
            raise LaneError(f'git {args[0]} failed: {error or p.returncode}')
        return p

    def text(self, *args, **kwargs):
        return self.git(*args, **kwargs).stdout.decode(errors='replace').strip()

    def check_origin(self, recorded=None):
        if self.dir.is_symlink() or self.text('rev-parse', '--show-toplevel') != str(self.dir):
            raise LaneError('Not the expected repository root.')
        remote = self.git('remote', 'get-url', '--all', 'origin', check=False)
        if remote.returncode and recorded and 'origin' not in self.text('remote').splitlines():
            # Arena can drop .git/config between turns. Restore only the URL
            # recorded after a prior verified clone/worktree check.
            self.git('remote', 'add', 'origin', recorded)
        url = self.text('remote', 'get-url', '--all', 'origin')
        permitted = {self.remote}
        if self.production and self.linked:
            permitted.add(self.remote.removesuffix('.git'))
        if (url not in permitted or (recorded and url != recorded)
                or self.text('remote', 'get-url', '--push', '--all', 'origin') != url):
            raise LaneError('The fetch/push URLs do not match the verified repository. Do not overwrite origin.')
        return url

    def ensure_checkout(self, start=False):
        record = json.loads(self.origin_record.read_text()) if self.origin_record.is_file() else None
        if record and (record['workdir'] != str(self.dir) or record['remote'] not in {self.remote, self.remote.removesuffix('.git')}):
            raise LaneError('The registered checkout or origin changed. Preserve it and tell the Captain.')
        if not self.linked and not self.dir.exists() and not self.dir.is_symlink():
            if not start or record:
                raise LaneError('Managed checkout is missing. Do not recreate it over unsaved work.')
            self.dir.parent.mkdir(parents=True, exist_ok=True)
            self.git('clone', '--depth', '1', '--single-branch', '--no-tags', '--no-recurse-submodules',
                     '--branch', 'main', '--', self.remote, str(self.dir), cwd=self.dir.parent, network=True)
        elif not record and not (self.linked and start):
            raise LaneError('Not a registered checkout. Do not adopt another worker’s or the Captain’s tree.')
        url = self.check_origin(record['remote'] if record else None)
        if not record:
            save_json(self.origin_record, {'workdir': str(self.dir), 'remote': url})

    def check_branch(self, branch):
        if self.arena is None:
            ok = branch == self.branch
        else:
            expected = self.arena['branch']
            ok = branch.startswith('arena/') and (expected == 'auto' or branch == expected)
        if not ok or self.git('check-ref-format', 'refs/heads/' + branch, check=False).returncode:
            raise LaneError('Wrong or detached task branch. Leave the checkout and its Arena binding alone.')

    def load(self, *, allow_check_revision=False):
        if not self.state_file.is_file():
            raise LaneError('Task is not started. Run start with the original Captain task JSON.')
        state = json.loads(self.state_file.read_text())
        saved = state.get('task')
        if saved != self.task:
            can_revise = (
                allow_check_revision
                and isinstance(saved, dict)
                and not state.get('pushed')
                and not state.get('commit')
                and {k: v for k, v in saved.items() if k != 'check'}
                == {k: v for k, v in self.task.items() if k != 'check'}
            )
            if not can_revise:
                raise LaneError('Task spec or saved state changed. Keep the original or ask for a new task ID.')
            state['task'] = self.task
            state.pop('checked_tree', None)
            state.pop('check_result', None)
        if not isinstance(state.get('branch'), str) or not is_sha(state.get('base_sha')):
            raise LaneError('Task spec or saved state changed. Keep the original or ask for a new task ID.')
        self.ensure_checkout()
        self.check_branch(state['branch'])
        self.branch = state['branch']
        return state

    def active_head(self):
        if self.text('branch', '--show-current') != self.branch:
            raise LaneError(f'Task checkout is not on {self.branch}. Do not switch over another task’s work.')
        return self.text('rev-parse', '--verify', 'HEAD')

    def clean(self):
        return not self.git('status', '--porcelain=v1', '-z', '--untracked-files=all').stdout

    def _tree_entry(self, treeish, path):
        raw = items(self.git('ls-tree', '-z', treeish, '--', path))
        if not raw:
            return None
        meta, _ = raw[0].split('\t', 1)
        mode, kind, sha = meta.split(' ')
        return (mode, sha) if kind == 'blob' and mode in ('100644', '100755') else ('special', mode, sha)

    def _index_entry(self, path, index=None):
        raw = items(self.git('ls-files', '--stage', '-z', '--', path, index=index))
        if not raw:
            return None
        if len(raw) != 1:
            return ('conflict',)
        meta, _ = raw[0].split('\t', 1)
        mode, sha, stage = meta.split(' ')
        return (mode, sha) if stage == '0' and mode in ('100644', '100755') else ('special', mode, sha)

    def _remove_verified_file(self, rel_path):
        target = self.dir / rel_path
        if target.is_symlink() or not target.is_file():
            raise LaneError(f'Refusing to remove unexpected path while syncing checkpoint: {rel_path!r}')
        resolved = target.resolve()
        if self.dir not in resolved.parents:
            raise LaneError(f'Path escapes checkout root: {rel_path!r}')
        target.unlink()
        parent = target.parent
        while parent != self.dir:
            try:
                parent.rmdir()
            except OSError:
                break
            parent = parent.parent

    def reconcile_restored_checkpoint(self, target, *, preserve_allowed=False):
        """Fast-forward a restored Arena branch to its verified published checkpoint.

        Arena can resume a hibernated linked session with local HEAD back at an
        earlier ancestor commit while the workspace snapshot already holds the
        published checkpoint's files (or a clean tree at that ancestor). Advance
        the existing arena/* ref only when GitHub's live branch tip equals
        `target`, local HEAD is an ancestor of `target`, and no staged, tracked,
        or untracked file contains unsaved changes outside the verified state.
        """
        if not self.linked or not is_sha(target):
            return None
        branch = self.text('branch', '--show-current')
        self.check_branch(branch)
        ref = 'refs/heads/' + branch
        if self.git('symbolic-ref', '-q', 'HEAD', check=False).stdout.decode(errors='replace').strip() != ref:
            return None
        head = self.text('rev-parse', '--verify', 'HEAD')
        if head == target:
            return None
        if self.git('ls-files', '-u').stdout:
            raise LaneError('The index has conflicts. Do not commit or push.')
        if self.remote_sha(branch) != target:
            return None
        track = 'refs/remotes/origin/' + branch
        self.git('fetch', '--no-tags', '--no-recurse-submodules', 'origin', f'+{ref}:{track}', network=True)
        if self.text('rev-parse', '--verify', track + '^{commit}') != target:
            raise LaneError('Remote branch moved during fetch. Reconcile with the Captain.')
        if self.git('merge-base', '--is-ancestor', head, target, check=False).returncode:
            if self.text('rev-parse', '--is-shallow-repository') == 'true':
                self.git('fetch', '--no-tags', '--no-recurse-submodules', '--deepen=64',
                         'origin', f'+{ref}:{track}', network=True, check=False)
                if self.git('merge-base', '--is-ancestor', head, target, check=False).returncode:
                    self.git('fetch', '--no-tags', '--no-recurse-submodules', '--unshallow',
                             'origin', f'+{ref}:{track}', network=True, check=False)
            if self.git('merge-base', '--is-ancestor', head, target, check=False).returncode:
                return None
        if self.clean():
            # Clean ancestor clone with no local edits or untracked files.
            self.git('merge', '--ff-only', target)
            return head
        # Protect any staged change that is not already identical to target.
        for path in items(self.git('diff', '--cached', '--no-renames', '--name-only', '-z', head, '--')):
            idx = self._index_entry(path)
            tgt = self._tree_entry(target, path)
            if ((idx is not None and len(idx) != 2) or (tgt is not None and len(tgt) != 2)
                    or (idx[1] if idx else None) != (tgt[1] if tgt else None)):
                return None
        allowed = set(self.task['allowed']) if preserve_allowed else set()
        stale_deleted = []
        with tempfile.TemporaryDirectory(prefix='.reconcile-', dir=self.states) as temp:
            index = Path(temp) / 'index'
            self.git('read-tree', target, index=index)
            self.git('add', '-A', '--', '.', index=index)
            diffs = items(self.git('diff', '--cached', '--no-renames', '--name-only', '-z', target, '--', index=index))
            for path in diffs:
                wt = self._index_entry(path, index=index)
                if wt is not None and len(wt) != 2:
                    return None
                if path in allowed:
                    continue
                # An overlay restore onto a fresh ancestor clone can leave a
                # file deleted in head..target on disk at its exact head blob.
                tgt = self._tree_entry(target, path)
                old = self._tree_entry(head, path)
                disk = self.dir / path
                if (tgt is not None or old is None or len(old) != 2 or wt is None
                        or wt[1] != old[1] or disk.is_symlink() or not disk.is_file()):
                    return None
                stale_deleted.append(path)
        self.git('update-ref', '-m', f'fastlane: sync restored checkpoint {target[:12]}', ref, target, head)
        self.git('read-tree', target)
        for path in stale_deleted:
            self._remove_verified_file(path)
        # Re-apply executable bits recorded in target without touching allowed edits.
        for entry in items(self.git('ls-files', '--stage', '-z')):
            meta, path = entry.split('\t', 1)
            if meta.startswith('100755 ') and path not in allowed:
                disk = self.dir / path
                if disk.is_file() and not disk.is_symlink():
                    disk.chmod(disk.stat().st_mode | 0o111)
        self.git('update-index', '-q', '--refresh', check=False)
        if self.active_head() != target or (not preserve_allowed and not self.clean()):
            raise LaneError('Restored checkout did not settle cleanly at the pinned checkpoint. Report to the Captain.')
        return head

    def sync_resumed_state(self, state):
        """Reconcile HEAD if Arena restored an older ancestor commit mid-task."""
        if not self.linked:
            return state
        commit = state.get('commit')
        if commit and is_sha(commit):
            restored = self.reconcile_restored_checkpoint(commit)
        elif not state.get('pushed') and state.get('remote_base') == state['base_sha']:
            restored = self.reconcile_restored_checkpoint(state['base_sha'], preserve_allowed=True)
        else:
            restored = None
        if restored:
            state['restored_from'] = restored
            save_json(self.state_file, state)
        return state

    def remote_sha(self, branch):
        ref = 'refs/heads/' + branch
        p = self.git('ls-remote', '--exit-code', 'origin', ref, network=True, check=False)
        if p.returncode == 2:
            return None
        if p.returncode != 0:
            raise LaneError('Cannot verify the GitHub ref. Check network and existing access; keep the work.')
        columns = p.stdout.decode().strip().split('\t')
        if len(columns) != 2 or columns[1] != ref or not is_sha(columns[0]):
            raise LaneError('Unexpected remote branch response.')
        return columns[0]

    def start(self):
        if self.state_file.is_file():
            state = self.sync_resumed_state(self.load())
            if not state.get('pushed'):
                self.active_head()
            return state
        completed = []
        for path in self.states.glob('*.json'):
            if path.name.startswith('.'):
                continue
            state = json.loads(path.read_text())
            if not state.get('pushed'):
                raise LaneError(f'{path.stem} is unfinished here. Resume/publish it first; do not reset it.')
            completed.append(state)
        self.ensure_checkout(start=True)
        restored = None
        if self.linked:
            self.branch = self.text('branch', '--show-current')
            self.check_branch(self.branch)
            pinned = self.arena['base_sha']
            if completed:
                prior_bases = {s['base_sha'] for s in completed}
                latest = [s for s in completed if s['commit'] not in prior_bases]
                if (len(latest) != 1 or latest[0]['branch'] != self.branch
                        or not pinned or self.arena['branch'] != self.branch):
                    raise LaneError('Next linked task needs the exact branch and the Captain’s verified last checkpoint.')
            if pinned and self.arena['branch'] == self.branch:
                restored = self.reconcile_restored_checkpoint(pinned)
            if completed and latest[0]['commit'] != pinned:
                prev = latest[0]['commit']
                # Permit advancing past an intermediate checkpoint that ran in a
                # lost workbench, never rewinding to an older commit.
                if self.git('merge-base', '--is-ancestor', prev, pinned, check=False).returncode:
                    raise LaneError('Next linked task needs the exact branch and the Captain’s verified last checkpoint.')
            if not self.clean():
                raise LaneError('Local changes exist. Preserve them; no new task was started.')
            base = self.active_head()
            if pinned and base != pinned:
                raise LaneError('Local HEAD differs from the Captain’s pinned base. Do not rewrite the branch.')
            last = self.remote_sha(self.branch)
            if last and last != base:
                raise LaneError('Local and remote Arena tips differ. Reconcile with the Captain before editing.')
            if (completed and last is None and not pinned) or ((not pinned or last is None) and self.remote_sha('main') != base and not pinned):
                raise LaneError('A new Arena checkpoint must start at main or a pinned, published baseline.')
        else:
            if not self.clean():
                raise LaneError('Local changes exist. Preserve them; no new task was started.')
            if self.text('branch', '--list', self.branch) or self.remote_sha(self.branch):
                raise LaneError('Task branch already exists without matching saved state. Use a fresh task ID.')
            pinned = self.task.get('base_sha')
            base_branch = self.task.get('base_branch') or 'main'
            base_ref = f'refs/heads/{base_branch}'
            track_ref = f'refs/remotes/origin/{base_branch}'
            self.git('fetch', '--no-tags', '--no-recurse-submodules', 'origin',
                     f'+{base_ref}:{track_ref}', network=True)
            if not pinned:
                base = self.text('rev-parse', '--verify', f'{track_ref}^{{commit}}')
            else:
                if self.git('cat-file', '-e', f'{pinned}^{{commit}}', check=False).returncode:
                    if self.text('rev-parse', '--is-shallow-repository') == 'true':
                        self.git('fetch', '--no-tags', '--no-recurse-submodules', '--unshallow',
                                 'origin', f'+{base_ref}:{track_ref}', network=True, check=False)
                    if self.git('cat-file', '-e', f'{pinned}^{{commit}}', check=False).returncode:
                        self.git('fetch', '--no-tags', '--no-recurse-submodules',
                                 'origin', pinned, network=True, check=False)
                    if self.git('cat-file', '-e', f'{pinned}^{{commit}}', check=False).returncode:
                        raise LaneError(f'Pinned base_sha {pinned[:12]} was not found on {base_branch} or origin.')
                if self.task.get('base_branch') and self.git(
                        'merge-base', '--is-ancestor', pinned, f'{track_ref}^{{commit}}', check=False).returncode:
                    raise LaneError(f'Pinned base_sha {pinned[:12]} is not on base_branch {base_branch}.')
                base = pinned
            self.git('switch', '-c', self.branch, base)
            last = None
        state = {'task': self.task, 'base_sha': base, 'branch': self.branch, 'remote_base': last, 'pushed': False}
        if restored:
            state['restored_from'] = restored
        save_json(self.state_file, state)
        return state

    def verify_files(self, files):
        if not files:
            raise LaneError('No task file changes.')
        outside = set(files) - set(self.task['allowed'])
        if outside:
            raise LaneError('Out-of-scope paths: ' + ', '.join(repr(p) for p in sorted(outside)))

    def snapshot(self, *, show_diff=False):
        if self.git('ls-files', '-u').stdout:
            raise LaneError('The index has conflicts. Do not commit or push.')
        files = sorted(set(items(self.git('diff', '--no-renames', '--name-only', '-z', 'HEAD', '--'))
                           + items(self.git('ls-files', '--others', '--exclude-standard', '-z'))))
        self.verify_files(files)
        # Read the proposed tree including new files, without staging in the
        # real index or altering the worker’s edits.
        with tempfile.TemporaryDirectory(prefix='.snapshot-', dir=self.states) as temp:
            index = Path(temp) / 'index'
            self.git('read-tree', 'HEAD', index=index)
            self.git('add', '--', *files, index=index)
            entries = items(self.git('ls-files', '--stage', '-z', '--', *files, index=index))
            if any(entry.startswith(('120000 ', '160000 ')) for entry in entries):
                raise LaneError('Symlinks and submodules are not allowed in worker patches.')
            return self.inspect_staged(index, show_diff)

    def inspect_staged(self, index, show_diff):
        opts = {'index': index}
        files = sorted(items(self.git('diff', '--cached', '--no-renames', '--name-only', '-z', 'HEAD', '--', **opts)))
        self.verify_files(files)
        patch = self.git('diff', '--cached', '--no-ext-diff', '--no-textconv', '--', **opts).stdout
        inspect_patch(patch)
        self.git('diff', '--cached', '--check', '--', **opts)
        if show_diff:
            sys.stdout.buffer.write(patch)
        return self.text('write-tree', **opts), files

    def run_gate(self, files):
        check = self.task['check']
        kind = check['kind']
        env = command_env()

        def run(*args, environment=env):
            p = subprocess.run(args, cwd=self.dir, env=environment, timeout=300)
            if p.returncode:
                raise LaneError(f'{Path(args[0]).name} check failed (exit {p.returncode}); see its output above.')

        if kind != 'flutter':
            snapshot = self.snapshot()
            if kind == 'preflight':
                run(sys.executable, '-B', 'tool/preflight.py')
                return 'preflight passed', snapshot
            if kind == 'pytest':
                run(sys.executable, '-m', 'pytest', '-q', check['target'])
                return f'pytest {check["target"]} passed', snapshot
            run(sys.executable, '-B', 'selftest.py')
            return 'selftest passed', snapshot
        if (not (self.dir / 'pubspec.lock').is_file()
                or self.git('ls-files', '--error-unmatch', '--', 'pubspec.lock', check=False).returncode):
            raise LaneError('A tracked pubspec.lock is required; ask the Captain for this repo’s gate.')
        test = check['test']
        if not (self.dir / test).is_file():
            raise LaneError(f'Targeted test file not found: {test}')
        version = check['version']
        sdk = ensure_flutter(version, env)
        flutter_env = tool_env(env, sdk)
        flutter = str(sdk / 'bin' / 'flutter')
        run(flutter, 'pub', 'get', '--enforce-lockfile', environment=flutter_env)
        dart_files = [file for file in files if file.endswith('.dart') and (self.dir / file).is_file()]
        if dart_files:
            run(str(sdk / 'bin' / 'dart'), 'format', *dart_files, environment=flutter_env)
        snapshot = self.snapshot()
        preflight = (self.dir / 'tool' / 'preflight.py').is_file()
        if preflight:
            run(sys.executable, '-B', 'tool/preflight.py')
        run(flutter, 'test', '--no-pub', test, environment=flutter_env)
        return ('preflight passed; ' if preflight else '') + f'Flutter {version}: {test} passed', snapshot

    def check(self):
        state = self.sync_resumed_state(self.load(allow_check_revision=True))
        if state.get('pushed') or state.get('commit'):
            raise LaneError('A commit is already recorded. Retry publish, not another edit.')
        if self.active_head() != state['base_sha'] or self.git('diff', '--cached', '--quiet', check=False).returncode:
            raise LaneError('HEAD or index changed outside the lane. Preserve it and report the mismatch.')
        # A failed re-check must not silently reuse an older successful result.
        state.pop('checked_tree', None)
        state.pop('check_result', None)
        save_json(self.state_file, state)
        _, files = self.snapshot()
        result, tested = self.run_gate(files)
        tree, files = self.snapshot()
        if (tested != (tree, files) or self.active_head() != state['base_sha']
                or self.git('diff', '--cached', '--quiet', check=False).returncode):
            raise LaneError('The gate or a concurrent edit changed the tested worktree. Review and rerun check.')
        state.update(checked_tree=tree, check_result=result, files=files)
        save_json(self.state_file, state)
        return state

    def inspect_range(self, base, tip):
        if self.text('show', '-s', '--format=%P', tip) != base:
            raise LaneError('The reported tip is not a single checkpoint commit on the reported base.')
        files = sorted(items(self.git('diff', '--no-renames', '--name-only', '-z', base, tip, '--')))
        self.verify_files(files)
        entries = items(self.git('ls-tree', '-r', '-z', tip, '--', *files))
        if any(entry.startswith(('120000 ', '160000 ')) for entry in entries):
            raise LaneError('Symlinks and submodules are not allowed in worker patches.')
        patch = self.git('diff', '--no-ext-diff', '--no-textconv', base, tip, '--').stdout
        inspect_patch(patch)
        self.git('diff', '--check', base, tip, '--')
        return files, patch

    def diff(self):
        state = self.sync_resumed_state(self.load())
        head = self.active_head()
        if head == state['base_sha']:
            self.snapshot(show_diff=True)
        else:
            if not self.matches_commit(state, head):
                raise LaneError('HEAD is not the checked task commit. Preserve it and tell the Captain.')
            _, patch = self.inspect_range(state['base_sha'], head)
            sys.stdout.buffer.write(patch)

    def matches_commit(self, state, head):
        return (state.get('commit', head) == head and self.clean()
                and self.text('show', '-s', '--format=%P', head) == state['base_sha']
                and self.text('rev-parse', 'HEAD^{tree}') == state.get('checked_tree')
                and self.text('show', '-s', '--format=%s', head) == self.task['commit'])

    def publish(self):
        state = self.sync_resumed_state(self.load())
        remote = self.remote_sha(self.branch)
        if state.get('pushed'):
            if remote != state['commit']:
                raise LaneError('Previously published branch moved or disappeared. Reconcile with the Captain.')
            return state
        head = self.active_head()
        tree = state.get('checked_tree')
        if not tree or not state.get('check_result'):
            raise LaneError('Run check successfully, then review diff before publishing.')
        prior = state['remote_base']
        if remote != prior and not (remote == head and head != state['base_sha']):
            raise LaneError('Remote branch moved or disappeared. Do not overwrite it.')
        if head == state['base_sha']:
            if state.get('commit'):
                raise LaneError('Recorded task commit is no longer checked out; do not recreate it.')
            checked_now, files = self.snapshot()
            if checked_now != tree or files != state['files']:
                raise LaneError('Changes differ from the tested tree. Run check again.')
            if (self.git('diff', '--cached', '--quiet', check=False).returncode
                    and self.text('write-tree') != tree):
                raise LaneError('The existing index contains other changes. Do not include them.')
            self.git('add', '--', *files)
            if self.text('write-tree') != tree:
                raise LaneError('Staged tree changed since check. Nothing was committed.')
            self.git('-c', 'user.name=Keshab Sarkar', '-c', 'user.email=Keshab1997@users.noreply.github.com',
                     'commit', '-m', self.task['commit'])
            head = self.active_head()
        if not self.matches_commit(state, head):
            raise LaneError('HEAD is not the single checked task commit, or new local changes exist.')
        # Recover if a turn stopped after commit or after push. Persist before
        # networking and require a second ref read before reporting success.
        state['commit'] = head
        save_json(self.state_file, state)
        if remote != head:
            namespace = 'refs/heads/' + self.branch
            self.git('push', '--no-follow-tags', '--recurse-submodules=no', 'origin', f'{head}:{namespace}', network=True)
        if self.remote_sha(self.branch) != head:
            raise LaneError('Push was not verified at the expected branch and SHA.')
        state['pushed'] = True
        save_json(self.state_file, state)
        return state

    def review(self, branch, base, tip):
        """Fetch-only Captain verification; never stages, merges, or declares review passed."""
        if not is_sha(base) or not is_sha(tip) or base == tip:
            raise LaneError('Review needs the two distinct full SHAs from the PUSHED report.')
        self.check_origin()
        self.check_branch(branch)
        expected_base = self.arena['base_sha'] if self.arena else self.task.get('base_sha')
        if expected_base and expected_base != base:
            raise LaneError('Reported base does not match the approved task base.')
        self.git('fetch', '--no-tags', '--no-recurse-submodules', 'origin', 'refs/heads/' + branch, network=True)
        if self.text('rev-parse', '--verify', 'FETCH_HEAD^{commit}') != tip:
            raise LaneError('Remote tip differs from the PUSHED report. Reconcile before proceeding.')
        files, patch = self.inspect_range(base, tip)
        print(f'Verified {self.task["repo"]} {self.slug}: {branch} {base}..{tip}',
              '\nFiles: ' + ', '.join(files), '\nRead this diff and run the integration gate before landing.', flush=True)
        sys.stdout.buffer.write(patch)
        self._ledger_record(branch, base, tip)

    def mention(self, tracker_url=None, brief_url=None, *, api_fn=None):
        """Post the @Keshab1997 checkpoint mention to the approved tracking issue."""
        state = self.sync_resumed_state(self.load())
        if not state.get('pushed'):
            raise LaneError('Publish and verify the remote branch before posting a tracker mention.')
        url = tracker_url or self.task.get('tracker')
        if not url:
            raise LaneError('No tracking issue URL in task JSON or --tracker; report in chat instead.')
        m = ISSUE_URL.fullmatch(url.strip())
        if not m:
            raise LaneError(f'tracker must be a {OWNER} GitHub issue URL (got {url!r}).')
        owner, repo_name, issue_num = m.groups()
        api = api_fn or gh_api
        comments_path = f'/repos/{owner}/{repo_name}/issues/{issue_num}/comments'
        comments = api('GET', comments_path + '?per_page=100') or []
        needle = state['commit'][:7]
        for comment in comments:
            body = comment.get('body') or ''
            if 'checkpoint ready' in body and self.slug in body and needle in body:
                html_url = comment.get('html_url') or url
                state['mention_url'] = html_url
                save_json(self.state_file, state)
                return html_url, False
        lines = [f'@{OWNER} — checkpoint ready for review', '']
        if brief_url:
            lines.append(f'Brief: {brief_url}')
        lines.append(f'Commit: https://github.com/{self.task["repo"]}/commit/{state["commit"]}')
        lines.extend(['', '```text', self.describe(state, confirmed=True), '```'])
        created = api('POST', comments_path, {'body': '\n'.join(lines)})
        html_url = (created or {}).get('html_url') or url
        state['mention_url'] = html_url
        save_json(self.state_file, state)
        return html_url, True

    def _ledger_record(self, branch, base, tip):
        """Best-effort Captain ledger update after a successful review. A
        missing LEDGER.json, a missing entry, or any error never fails the
        review itself — GitHub refs stay the source of truth."""
        try:
            path = Path(__file__).resolve().with_name('LEDGER.json')
            if not path.is_file():
                return
            import importlib.util
            spec = importlib.util.spec_from_file_location('captain_ledger', path.with_name('ledger.py'))
            ledger = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(ledger)
            data = ledger.load(path)
            entry = next((e for e in data['entries']
                          if (e.get('repo'), e.get('worker'), e.get('task'))
                          == (self.task['repo'], self.worker, self.task['task'])), None)
            if entry is None:
                print(f'ledger: no entry for {self.task["repo"]}/{self.task["task"]} — '
                      'run captain/ledger.py upsert', flush=True)
                return
            if any(h.get('sha') == tip and h.get('status') == 'verified' for h in entry.get('history', [])):
                return
            entry.setdefault('history', []).append(
                {'sha': tip, 'status': 'verified', 'utc': ledger.now(),
                 'base_sha': base, 'by': 'worker_lane review'})
            entry['sha'] = tip
            entry['status'] = 'verified'
            entry['branch'] = entry.get('branch') or branch
            entry['base_sha'] = entry.get('base_sha') or base
            entry['updated_utc'] = ledger.now()
            ledger.save(path, data)
            print(f'ledger: recorded verified {tip[:7]} for {entry["repo"]} '
                  f'{entry.get("batch")}/{self.worker}/{entry["task"]}', flush=True)
        except Exception as exc:
            print(f'ledger: skipped ({exc.__class__.__name__})', flush=True)

    def describe(self, state, confirmed=False):
        if state.get('pushed'):
            title = f'AGENT {self.worker} PUSHED' if confirmed else 'Checkpoint recorded (publish re-verifies the remote)'
            return '\n'.join([
                title, 'repo: ' + self.task['repo'], 'task: ' + self.slug,
                'branch: ' + self.branch, 'base_sha: ' + state['base_sha'],
                'sha: ' + state['commit'], 'files: ' + ', '.join(state['files']),
                'check: ' + state['check_result'],
            ])
        phase = 'commit saved; push pending' if state.get('commit') else ('checked' if state.get('checked_tree') else 'ready')
        out = f'{phase}\ntask: {self.slug}\nworkdir: {self.dir}\nbranch: {self.branch}\nbase_sha: {state["base_sha"]}'
        return out + (f'\nrestored_from: {state["restored_from"]}' if state.get('restored_from') else '')


def gh_api(method, path, data=None, timeout=40):
    gh = BOOTSTRAP / 'gh_app.py'
    cmd = [sys.executable, '-B', str(gh), 'api', method, path, '--raw']
    if data is not None:
        cmd.extend(['--data', json.dumps(data)])
    proc = subprocess.run(cmd, cwd=str(BOOTSTRAP), capture_output=True, text=True, timeout=timeout)
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout).strip().splitlines()
        msg = detail[-1][:240] if detail else f'exit {proc.returncode}'
        raise LaneError(f'GitHub API {method} {path} failed ({msg}). Check pairing with `python3 gh_app.py status`.')
    body = proc.stdout.strip()
    return json.loads(body) if body else None


def parse_brief_url(url):
    m = BRIEF_URL.fullmatch((url or '').strip())
    if not m:
        raise LaneError('Invalid brief URL; expected a commit-pinned GitHub blob link to docs/agent-briefs/<batch>/<task>/BRIEF.md.')
    return m.group(1), m.group(2), m.group(3), m.group(4)


def _decode_content(payload, label):
    if not isinstance(payload, dict) or payload.get('encoding') != 'base64' or not isinstance(payload.get('content'), str):
        raise LaneError(f'Unexpected GitHub contents payload for {label}.')
    return base64.b64decode(payload['content']).decode('utf-8')


def fetch_brief(repo, brief_sha, batch, task_id, *, root=ROOT, worker=None, api_fn=None):
    if not isinstance(repo, str) or not REPO.fullmatch(repo) or repo.lower().endswith('.git'):
        raise LaneError(f'Repo must be {OWNER}/<name>.')
    if not isinstance(brief_sha, str) or not re.fullmatch(r'[0-9a-f]{40}', brief_sha):
        raise LaneError('brief_sha must be a full 40-hex commit SHA.')
    if not isinstance(batch, str) or not TASK.fullmatch(batch):
        raise LaneError('Invalid batch ID.')
    if not isinstance(task_id, str) or not TASK.fullmatch(task_id):
        raise LaneError('Invalid task ID.')
    api = api_fn or gh_api
    cmp_res = api('GET', f'/repos/{repo}/compare/{brief_sha}...captain/briefs/{batch}') or {}
    if cmp_res.get('status') not in ('identical', 'ahead'):
        raise LaneError(f'Brief commit {brief_sha[:12]} is not on captain/briefs/{batch}.')
    base_dir = f'docs/agent-briefs/{batch}/{task_id}'
    brief_md = _decode_content(api('GET', f'/repos/{repo}/contents/{base_dir}/BRIEF.md?ref={brief_sha}'), 'BRIEF.md')
    task_raw = _decode_content(api('GET', f'/repos/{repo}/contents/{base_dir}/task.json?ref={brief_sha}'), 'task.json')
    spec = validate_task(json.loads(task_raw))
    if spec['repo'] != repo or spec['task'] != task_id:
        raise LaneError('Brief task.json repo or task ID does not match the pinned brief path.')
    if worker and spec['worker'] != worker:
        raise LaneError(f'Brief is for Worker {spec["worker"]}, not Worker {worker}.')
    inbox_root = Path(root).resolve() / 'inbox'
    inbox_root.mkdir(mode=0o700, parents=True, exist_ok=True)
    inbox = Path(tempfile.mkdtemp(prefix=f'{task_id}-', dir=inbox_root))
    (inbox / 'BRIEF.md').write_text(brief_md, encoding='utf-8')
    (inbox / 'task.json').write_text(task_raw, encoding='utf-8')
    return inbox, spec


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT, help='workbench for standalone clones and task records')
    parser.add_argument('--checkout', type=Path, help='exact linked repo path, or separate Captain checkout for review')
    parser.add_argument('--branch', help='reported branch for review only')
    parser.add_argument('--base', help='reported full base SHA for review only')
    parser.add_argument('--tip', help='reported full pushed SHA for review only')
    parser.add_argument('--url', help='pinned GitHub brief permalink for fetch-brief')
    parser.add_argument('--repo', help='owner/repo for fetch-brief when not using --url')
    parser.add_argument('--batch', help='batch ID for fetch-brief when not using --url')
    parser.add_argument('--task', help='task ID for fetch-brief when not using --url')
    parser.add_argument('--brief-sha', help='full 40-hex brief commit SHA for fetch-brief when not using --url')
    parser.add_argument('--worker', choices=('A', 'B', 'C'), help='expected worker letter for fetch-brief')
    parser.add_argument('--tracker', help='approved GitHub issue URL for mention')
    parser.add_argument('--brief-url', help='pinned GitHub brief permalink to include in mention')
    parser.add_argument('command', choices=('fetch-brief', 'start', 'status', 'check', 'diff', 'publish', 'mention', 'review'))
    parser.add_argument('task_file', nargs='?', type=Path, help='original Captain task JSON')
    args = parser.parse_args()
    lane = None
    try:
        if args.command == 'fetch-brief':
            if args.task_file is not None:
                raise LaneError('fetch-brief takes --url (or --repo/--batch/--task/--brief-sha), not a task_file.')
            if args.url:
                repo, brief_sha, batch, task_id = parse_brief_url(args.url)
            else:
                if not all((args.repo, args.batch, args.task, args.brief_sha)):
                    raise LaneError('Pass --url or all of --repo, --batch, --task, --brief-sha.')
                repo, brief_sha, batch, task_id = args.repo, args.brief_sha, args.batch, args.task
            inbox, spec = fetch_brief(repo, brief_sha, batch, task_id, root=args.root, worker=args.worker)
            mode = 'arena-linked' if 'arena' in spec else 'device-flow'
            print('\n'.join([
                f'brief: {inbox / "BRIEF.md"}',
                f'task_json: {inbox / "task.json"}',
                f'repo: {spec["repo"]}',
                f'worker: {spec["worker"]}',
                f'task: {spec["task"]}',
                f'mode: {mode}',
            ]))
            return
        if args.task_file is None:
            raise LaneError(f'{args.command} requires a task_file path.')
        reviewing = args.command == 'review'
        if reviewing and not all((args.branch, args.base, args.tip)):
            raise LaneError('For review, give --branch, --base, and --tip from the worker’s PUSHED report.')
        if not reviewing and any((args.branch, args.base, args.tip)):
            raise LaneError('--branch, --base, and --tip are for review only. Worker inputs are in the task JSON.')
        lane = Lane(json.loads(args.task_file.read_text()), args.root, checkout=args.checkout, review=reviewing)
        if reviewing:
            lane.review(args.branch, args.base, args.tip)
            return
        with lane.locked():
            if args.command == 'diff':
                lane.diff()
                return
            if args.command == 'mention':
                comment_url, created = lane.mention(tracker_url=args.tracker, brief_url=args.brief_url)
                label = 'mentioned' if created else 'already_mentioned'
                print(f'{label}: {comment_url}')
                return
            state = lane.load() if args.command == 'status' else getattr(lane, args.command)()
            print(lane.describe(state, confirmed=args.command == 'publish'))
    except (LaneError, SDKError, OSError, ValueError, KeyError, subprocess.SubprocessError) as exc:
        who = lane.worker if lane else (args.worker or '?')
        parser.exit(1, f'AGENT {who} BLOCKED\nblocked: {exc}\n')


if __name__ == '__main__':
    main()
