"""Fast Lane regressions. Run the whole offline suite with python3 selftest.py."""
from __future__ import annotations

import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tarfile
import tempfile
import unittest
from unittest import mock

import flutter_sdk as sdk
import worker_lane as work


def task(slug='first', allowed=('lesson.txt',), **changes):
    return dict(repo='Keshab1997/fixture', worker='A', task=slug, allowed=list(allowed),
                commit=f'test(lesson): {slug}', check={'kind': 'preflight'}) | changes


@unittest.skipUnless(shutil.which('git'), 'requires git')
class CheckpointTests(unittest.TestCase):
    branch = 'arena/fastlane-fixture'

    def setUp(self):
        tmp = tempfile.TemporaryDirectory(prefix='fastlane-git-')
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.remote = self.root / 'origin.git'
        self.seed = self.root / 'captain'
        self.seed.mkdir()
        self.env = work.command_env() | dict(GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL=os.devnull,
                                             GIT_TERMINAL_PROMPT='0', GIT_ALLOW_PROTOCOL='file')
        self.git('init', '-q', '--bare', '-b', 'main', str(self.remote))
        self.git('init', '-q', '-b', 'main')
        self.git('config', 'user.name', 'Fixture')
        self.git('config', 'user.email', 'test@example.invalid')
        self.write('lesson.txt', 'lesson at main\n')
        self.write('pubspec.lock', 'fixture lock\n')
        self.write('test/example_test.dart', '// initial test\n')
        self.write('tool/preflight.py', '''from pathlib import Path
from os import environ
if 'FIXTURE_MUTATES' in environ:
    Path('lesson.txt').write_text('gate changed the tree\\n')
if 'FIXTURE_FAILS' in environ:
    raise SystemExit(7)
''')
        self.git('add', '--', '.')
        self.git('commit', '-qm', 'initial')
        self.base = self.git('rev-parse', 'HEAD')
        self.git('remote', 'add', 'origin', str(self.remote))
        self.git('push', '-q', 'origin', 'main')

    def git(self, *args, cwd=None):
        return subprocess.run(['git', *args], cwd=cwd or self.seed, env=self.env, check=True,
                              capture_output=True, text=True, timeout=20).stdout.strip()

    def write(self, name, text, cwd=None):
        path = (cwd or self.seed) / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)

    def lane(self, spec=None, checkout=None, review=False):
        return work.Lane(spec or task(), self.root / 'workbench', checkout=checkout,
                         review=review, _test_remote=str(self.remote))

    def attach(self):
        bound = self.root / 'bound'
        self.git('clone', '-q', str(self.remote), str(bound))
        self.git('switch', '-qc', self.branch, cwd=bound)
        return bound

    def linked(self, slug, bound, allowed=('lesson.txt',), branch='auto', base=None):
        return self.lane(task(slug, allowed, arena={'branch': branch, 'base_sha': base}), bound)

    def checked(self, lane, file='lesson.txt', change='checkpoint one\n'):
        state = lane.start()
        self.write(file, change, lane.dir)
        lane.check()
        return state

    def heads(self):
        return {name: sha for sha, name in (line.split('\t') for line in
                                            self.git('ls-remote', '--heads', 'origin').splitlines())}

    def reviewed_diff(self, lane, report):
        reader = self.lane(lane.task, self.seed, review=True)
        with contextlib.redirect_stdout(io.StringIO()) as out:
            out.buffer = io.BytesIO()
            reader.review(report['branch'], report['base_sha'], report['commit'])
        return out.buffer.getvalue().decode()

    def test_two_checkpoints_one_attached_branch_and_review_only_new_delta(self):
        bound = self.attach()
        lane = self.linked('first', bound, ('first note.txt',))
        self.checked(lane, 'first note.txt', 'first checkpoint\n')
        done = lane.publish()
        sha = done['commit']
        self.assertIn('first note.txt', self.reviewed_diff(lane, done))
        self.assertEqual(lane.describe(done, confirmed=True).splitlines()[0], 'AGENT A PUSHED')
        self.assertNotIn('PUSHED', lane.describe(done))
        self.assertEqual(done['base_sha'], self.base)
        self.assertEqual(done['branch'], self.branch)
        self.assertEqual(lane.publish()['commit'], sha)

        # The second brief needs the *exact* branch AND verified previous tip.
        for branch, base in (('auto', None), ('auto', sha), (self.branch, self.base)):
            with self.subTest(branch=branch, base=base):
                with self.assertRaises(work.LaneError):
                    self.linked('second', bound, branch=branch, base=base).start()
        next_task = self.linked('second', bound, branch=self.branch, base=sha)
        self.assertEqual(self.checked(next_task, change='checkpoint two\n')['base_sha'], sha)
        second = next_task.publish()
        patch = self.reviewed_diff(next_task, second)
        self.assertIn('checkpoint two', patch)
        self.assertNotIn('first note.txt', patch)
        self.assertEqual(self.heads(), {'refs/heads/main': self.base,
                                        'refs/heads/' + self.branch: second['commit']})
        self.assertEqual(self.git('branch', '--show-current', cwd=bound), self.branch)
        self.assertEqual(self.git('rev-parse', 'HEAD'), self.base)  # review is fetch-only
        with self.assertRaisesRegex(work.LaneError, 'moved'):
            lane.publish()

    def test_standalone_reuses_clone_and_starts_next_task_at_new_main(self):
        lane = self.lane()
        self.checked(lane)
        first = lane.publish()['commit']
        self.write('upstream.txt', 'change landed between worker tasks\n')
        self.git('add', '--', 'upstream.txt')
        self.git('commit', '-qm', 'captain integration')
        self.git('push', '-q', 'origin', 'main')
        main = self.git('rev-parse', 'HEAD')
        (lane.dir / '.git' / 'config').unlink()  # snapshot dropped the origin
        second = self.lane(task('second'))
        state = self.checked(second, change='standalone task two\n')
        self.assertEqual(lane.dir, second.dir)
        self.assertEqual(state['base_sha'], main)
        self.assertEqual(self.git('rev-parse', 'main', cwd=second.dir), self.base)
        tip = second.publish()['commit']
        self.assertEqual(self.heads(), {'refs/heads/main': main,
                                        'refs/heads/agent/A/first': first,
                                        'refs/heads/agent/A/second': tip})

    def test_start_blocks_overlap_dirty_wrong_branch_and_wrong_origin(self):
        bound = self.attach()
        with self.assertRaisesRegex(work.LaneError, 'Wrong or detached'):
            self.linked('first', bound, branch='arena/not-this-one').start()
        lane = self.linked('first', bound)
        self.write('lesson.txt', 'existing work\n', bound)
        with self.assertRaisesRegex(work.LaneError, 'Local changes'):
            lane.start()
        self.assertEqual((bound / 'lesson.txt').read_text(), 'existing work\n')
        self.write('lesson.txt', 'lesson at main\n', bound)
        self.git('remote', 'set-url', '--push', 'origin', str(self.root / 'other.git'), cwd=bound)
        with self.assertRaisesRegex(work.LaneError, 'URLs do not match'):
            lane.start()
        self.git('remote', 'set-url', '--push', 'origin', str(self.remote), cwd=bound)
        lane.start()
        with self.assertRaisesRegex(work.LaneError, 'unfinished'):
            self.linked('second', bound).start()
        self.assertEqual(self.heads(), {'refs/heads/main': self.base})

    def test_out_of_scope_symlink_and_possible_credentials_stay_local(self):
        lane = self.lane()
        lane.start()
        self.write('lesson.txt', 'new text\n', lane.dir)
        self.write('other.txt', 'unrelated work\n', lane.dir)
        with self.assertRaisesRegex(work.LaneError, 'Out-of-scope'):
            lane.check()
        self.assertEqual((lane.dir / 'other.txt').read_text(), 'unrelated work\n')
        (lane.dir / 'other.txt').unlink()
        (lane.dir / 'lesson.txt').unlink()
        (lane.dir / 'lesson.txt').symlink_to(self.seed / 'lesson.txt')
        with self.assertRaisesRegex(work.LaneError, 'Symlinks'):
            lane.check()
        (lane.dir / 'lesson.txt').unlink()
        self.write('lesson.txt', 'fake ' + 'ghp_' + 'A' * 40 + '\n', lane.dir)
        with self.assertRaisesRegex(work.LaneError, 'Possible credential'):
            lane.check()
        self.assertEqual(self.git('diff', '--cached', '--name-only', cwd=lane.dir), '')
        self.assertEqual(self.heads(), {'refs/heads/main': self.base})

    def test_changed_or_failed_check_cannot_publish(self):
        lane = self.lane()
        self.checked(lane)
        self.write('lesson.txt', 'unverified edit\n', lane.dir)
        with self.assertRaisesRegex(work.LaneError, 'differ from the tested tree'):
            lane.publish()
        with mock.patch.dict(os.environ, FIXTURE_FAILS='1'):
            with self.assertRaisesRegex(work.LaneError, 'exit 7'):
                lane.check()
        with self.assertRaisesRegex(work.LaneError, 'Run check successfully'):
            lane.publish()
        with mock.patch.dict(os.environ, FIXTURE_MUTATES='1'):
            with self.assertRaisesRegex(work.LaneError, 'changed the tested worktree'):
                lane.check()
        self.assertEqual(self.git('rev-parse', 'HEAD', cwd=lane.dir), self.base)
        self.assertEqual(self.heads(), {'refs/heads/main': self.base})

    def test_captain_check_profile_revision_preserves_edits_without_widening_scope(self):
        bound = self.attach()
        initial = task('flutter-blocked', ('lesson.txt', 'test/example_test.dart'),
                       arena={'branch': 'auto', 'base_sha': self.base},
                       check={'kind': 'flutter', 'version': '3.50.0', 'test': 'test/example_test.dart'})
        self.lane(initial, bound).start()
        self.write('lesson.txt', 'saved worker fix\n', bound)
        revised = initial | {'check': {'kind': 'preflight'}}
        lane = self.lane(revised, bound)
        # diff/publish still reject an un-checked revision; scope/commit changes always fail.
        with self.assertRaisesRegex(work.LaneError, 'Task spec'):
            lane.publish()
        with self.assertRaisesRegex(work.LaneError, 'Task spec'):
            self.lane(revised | {'commit': 'tampered'}, bound).check()
        with self.assertRaisesRegex(work.LaneError, 'Task spec'):
            self.lane(revised | {'allowed': ['lesson.txt']}, bound).check()
        checked = lane.check()
        self.assertEqual(checked['check_result'], 'preflight passed')
        done = lane.publish()
        self.assertIn('saved worker fix', self.reviewed_diff(lane, done))
        # Once committed/pushed, check profile cannot change either.
        with self.assertRaisesRegex(work.LaneError, 'Task spec'):
            self.lane(initial, bound).check()

    def test_ambiguous_push_recovery_does_not_create_extra_commits(self):
        lane = self.lane()
        self.checked(lane)
        execute = lane.git

        def push_then_interrupt(*args, **opts):
            result = execute(*args, **opts)
            if args[0] == 'push':
                raise work.LaneError('simulated interrupted turn after push')
            return result

        with mock.patch.object(lane, 'git', side_effect=push_then_interrupt):
            with self.assertRaisesRegex(work.LaneError, 'interrupted'):
                lane.publish()
        pending = lane.load()
        self.assertFalse(pending['pushed'])
        self.assertEqual(self.heads()['refs/heads/agent/A/first'], pending['commit'])
        recovered = lane.publish()
        self.assertTrue(recovered['pushed'])
        self.assertEqual(recovered['commit'], pending['commit'])
        self.assertEqual(self.git('show', '-s', '--format=%P', 'HEAD', cwd=lane.dir), self.base)

    def test_linked_remote_move_blocks_before_commit(self):
        bound = self.attach()
        self.git('push', '-q', 'origin', 'HEAD:refs/heads/' + self.branch, cwd=bound)
        lane = self.linked('first', bound)
        self.checked(lane)
        self.write('other.txt', 'remote concurrent work\n')
        self.git('add', '--', 'other.txt')
        self.git('commit', '-qm', 'other writer')
        self.git('push', '-q', 'origin', 'HEAD:refs/heads/' + self.branch)
        with self.assertRaisesRegex(work.LaneError, 'moved'):
            lane.publish()
        self.assertEqual(self.git('rev-parse', 'HEAD', cwd=bound), self.base)
        self.assertEqual((bound / 'lesson.txt').read_text(), 'checkpoint one\n')
        self.assertEqual(self.heads()['refs/heads/' + self.branch], self.git('rev-parse', 'HEAD'))

    def test_captain_rejects_wrong_tip_base_branch_scope(self):
        lane = self.lane()
        self.checked(lane)
        state = lane.publish()
        reader = self.lane(lane.task, self.seed, review=True)
        for branch, base, tip in ((state['branch'], self.base, 'a' * 40),
                                  (state['branch'], 'a' * 40, state['commit']),
                                  ('main', self.base, state['commit'])):
            with self.assertRaises(work.LaneError):
                reader.review(branch, base, tip)
        narrower = self.lane(task(allowed=('not-lesson.txt',)), self.seed, review=True)
        with self.assertRaisesRegex(work.LaneError, 'Out-of-scope'):
            narrower.review(state['branch'], self.base, state['commit'])

    def test_flutter_gate_format_then_locked_targeted_check_and_no_lock_mutation(self):
        test = 'test/example_test.dart'
        lane = self.lane(task(allowed=(test,), check={'kind': 'flutter', 'version': '3.50.0', 'test': test}))
        lane.start()
        self.write(test, '// not formatted\n', lane.dir)
        real_run = subprocess.run
        commands = []

        def fake_run(argv, **kwargs):
            exe = Path(argv[0]).name
            if exe in ('dart', 'flutter'):
                commands.append((exe, *argv[1:]))
                if exe == 'dart':
                    self.write(test, '// formatted\n', lane.dir)
                return subprocess.CompletedProcess(argv, 0)
            return real_run(argv, **kwargs)

        with mock.patch.object(work, 'ensure_flutter', return_value=self.root / 'flutter') as ensure, \
                mock.patch.object(work.subprocess, 'run', side_effect=fake_run):
            checked = lane.check()
            self.assertIn('Flutter 3.50.0', checked['check_result'])
            self.assertEqual(ensure.call_args.args[0], '3.50.0')
        self.assertEqual(commands, [('flutter', 'pub', 'get', '--enforce-lockfile'),
                                    ('dart', 'format', test), ('flutter', 'test', '--no-pub', test)])
        self.write('pubspec.lock', 'modified lock\n', lane.dir)
        with self.assertRaisesRegex(work.LaneError, 'Out-of-scope.*pubspec.lock'):
            lane.publish()
        self.assertEqual(self.heads(), {'refs/heads/main': self.base})


class SpecTests(unittest.TestCase):
    def test_examples_are_valid_disjoint_task_specs(self):
        allocations = set()
        for path in sorted(Path(__file__).parent.glob('examples/WORKER_*.md')):
            spec = work.validate_task(json.loads(re.search(r'```json\n(.*?)\n```', path.read_text(), re.S)[1]))
            files = {(spec['repo'], file) for file in spec['allowed']}
            self.assertFalse(allocations & files)
            allocations.update(files)
        self.assertTrue(allocations)

    @unittest.skipUnless(shutil.which('git'), 'requires git')
    def test_saved_git_access_is_scoped_to_the_one_https_repo(self):
        with tempfile.TemporaryDirectory() as directory:
            token = Path(directory) / 'fake-token'
            token.write_text('fake-not-a-credential\n')
            env = work.command_env() | dict(WORKER_TOKEN_FILE=str(token), WORKER_GIT_PATH='Keshab1997/fixture.git',
                                            GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL=os.devnull,
                                            GIT_TERMINAL_PROMPT='0', GIT_ASKPASS='/bin/false')
            cmd = ['git', '-c', 'credential.helper=', '-c', 'credential.useHttpPath=true',
                   '-c', 'credential.helper=' + work.HELPER, 'credential', 'fill']

            def call(protocol, host, path):
                return subprocess.run(cmd, cwd=directory, env=env, text=True, timeout=10,
                                      capture_output=True, input=f'protocol={protocol}\nhost={host}\npath={path}\n\n')

            ok = call('https', 'github.com', 'Keshab1997/fixture.git')
            self.assertEqual(ok.returncode, 0, ok.stderr)
            self.assertIn('username=x-access-token\npassword=fake-not-a-credential\n', ok.stdout)
            for protocol, host, path in (('http', 'github.com', 'Keshab1997/fixture.git'),
                                         ('https', 'other.example', 'Keshab1997/fixture.git'),
                                         ('https', 'github.com', 'Keshab1997/other.git')):
                result = call(protocol, host, path)
                self.assertNotEqual(result.returncode, 0)
                self.assertNotIn('fake-not-a-credential', result.stdout + result.stderr)

    def test_manifest_blocks_shared_paths_ref_escape_and_unpinned_flutter(self):
        for path in ('../foo', '/root/foo', 'pubspec.lock', '.github/workflows/build.yml', 'docs/*',
                     'secrets/access.txt', 'lib/model.g.dart', 'tool/preflight.py'):
            with self.subTest(path=path), self.assertRaises(work.LaneError):
                work.validate_task(task(allowed=(path,)))
        for changes in ({'task': 'bad/ref'}, {'repo': 'other/fixture'}, {'worker': 'D'},
                        {'arena': {'branch': 'main', 'base_sha': None}},
                        {'check': {'kind': 'flutter', 'version': 'latest', 'test': 'test/a_test.dart'}}):
            with self.subTest(changes=changes), self.assertRaises(work.LaneError):
                work.validate_task(task(**changes))


@unittest.skipUnless(shutil.which('tar') and shutil.which('xz'), 'requires tar and xz')
class SDKTests(unittest.TestCase):
    version = '3.50.0'

    def setUp(self):
        tmp = tempfile.TemporaryDirectory(prefix='fastlane-flutter-')
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.cache = self.root / 'cache'
        self.release_path = f'stable/linux/flutter_linux_{self.version}-stable.tar.xz'
        self.env = {'PATH': os.defpath, 'CI': 'true'}

    def archive(self, version):
        stream = io.BytesIO()
        with tarfile.open(fileobj=stream, mode='w:xz') as tar:
            for name, content in (('flutter', b'#!/bin/sh\nprintf \'{"frameworkVersion":"' + version.encode() + b'"}\\n\'\n'),
                                  ('dart', b'#!/bin/sh\nexit 0\n')):
                info = tarfile.TarInfo('flutter/bin/' + name)
                info.size = len(content)
                info.mode = 0o755
                tar.addfile(info, io.BytesIO(content))
        return stream.getvalue()

    def sources(self, archive, digest):
        item = {'version': self.version, 'channel': 'stable', 'dart_sdk_arch': 'x64',
                'archive': self.release_path, 'sha256': digest}
        manifest = json.dumps({'releases': [item | {'dart_sdk_arch': 'arm64'}, item]}).encode()
        store = {sdk.BASE_URL + 'releases_linux.json': manifest, sdk.BASE_URL + self.release_path: archive}

        def open_fake(url, *, timeout):
            response = io.BytesIO(store[url])
            response.geturl = lambda: url
            return response
        return mock.patch.object(sdk, 'urlopen', side_effect=open_fake)

    def test_install_then_reuse_without_more_downloads(self):
        payload = self.archive(self.version)
        with self.sources(payload, hashlib.sha256(payload).hexdigest()) as opened, \
                contextlib.redirect_stderr(io.StringIO()):
            location = sdk.ensure_flutter(self.version, self.env, self.cache)
            self.assertEqual(location, self.cache / self.version)
            self.assertEqual(sdk.ensure_flutter(self.version, self.env, self.cache), location)
            self.assertEqual(opened.call_count, 2)  # manifest + one archive

    def test_checksum_or_version_mismatch_never_publishes_sdk(self):
        for reported_version, verified, expected in ((self.version, False, 'SHA-256'), ('3.47.9', True, 'usable')):
            with self.subTest(reported_version=reported_version, verified=verified):
                payload = self.archive(reported_version)
                digest = hashlib.sha256(payload).hexdigest() if verified else '0' * 64
                with self.sources(payload, digest), contextlib.redirect_stderr(io.StringIO()):
                    with self.assertRaisesRegex(sdk.SDKError, expected):
                        sdk.ensure_flutter(self.version, self.env, self.cache)
                self.assertFalse((self.cache / self.version).exists())
                self.assertEqual(list(self.cache.glob('.install-*')), [])

    def test_resumes_across_tls_drops_and_short_streams(self):
        import ssl
        from urllib.error import URLError

        payload = self.archive(self.version)
        digest = hashlib.sha256(payload).hexdigest()
        manifest_url = sdk.BASE_URL + 'releases_linux.json'
        archive_url = sdk.BASE_URL + self.release_path
        manifest = json.dumps({'releases': [{
            'version': self.version, 'channel': 'stable', 'dart_sdk_arch': 'x64',
            'archive': self.release_path, 'sha256': digest,
        }]}).encode()
        cut1 = max(1, len(payload) // 3)
        cut2 = max(cut1 + 1, (2 * len(payload)) // 3)
        ranges = []
        manifest_calls = 0
        archive_calls = 0

        class FakeStream:
            def __init__(self, url, body, *, status=200, headers=None, drop=None):
                self._url = url
                self._buf = io.BytesIO(body)
                self.status = status
                self.headers = headers or {}
                self._drop = drop

            def geturl(self):
                return self._url

            def read(self, size=-1):
                data = self._buf.read(size)
                if not data and self._drop is not None:
                    err, self._drop = self._drop, None
                    raise err
                return data

            def close(self):
                self._buf.close()

            def __enter__(self):
                return self

            def __exit__(self, *_):
                self.close()

        def open_flaky(target, *, timeout):
            nonlocal manifest_calls, archive_calls
            url = target if isinstance(target, str) else target.full_url
            if url == manifest_url:
                manifest_calls += 1
                if manifest_calls == 1:
                    raise URLError(ssl.SSLEOFError('TLS EOF during manifest'))
                return FakeStream(url, manifest)
            self.assertEqual(url, archive_url)
            archive_calls += 1
            hdr_range = None if isinstance(target, str) else target.get_header('Range')
            ranges.append(hdr_range)
            if archive_calls == 1:
                # Drops mid-stream with SSLEOFError after delivering payload[:cut1].
                return FakeStream(
                    url, payload[:cut1], status=200,
                    headers={'Content-Length': str(len(payload)), 'ETag': '"v350"'},
                    drop=ssl.SSLEOFError('EOF occurred in violation of protocol'),
                )
            if archive_calls == 2:
                # Resumes at cut1, then closes silently before Content-Length at cut2.
                self.assertEqual(hdr_range, f'bytes={cut1}-')
                return FakeStream(
                    url, payload[cut1:cut2], status=206,
                    headers={'Content-Range': f'bytes {cut1}-{len(payload) - 1}/{len(payload)}', 'ETag': '"v350"'},
                )
            # Final segment delivers remaining bytes, then raises trailing SSLEOFError.
            self.assertEqual(hdr_range, f'bytes={cut2}-')
            return FakeStream(
                url, payload[cut2:], status=206,
                headers={'Content-Range': f'bytes {cut2}-{len(payload) - 1}/{len(payload)}', 'ETag': '"v350"'},
                drop=ssl.SSLEOFError('trailing EOF without close_notify'),
            )

        with mock.patch.object(sdk, 'urlopen', side_effect=open_flaky), \
                mock.patch.object(sdk, 'CHUNK_BYTES', 32), \
                mock.patch.object(sdk.time, 'sleep'), \
                contextlib.redirect_stderr(io.StringIO()):
            location = sdk.ensure_flutter(self.version, self.env, self.cache)
        self.assertEqual(location, self.cache / self.version)
        self.assertEqual(manifest_calls, 2)
        self.assertEqual(ranges, [None, f'bytes={cut1}-', f'bytes={cut2}-'])

    def test_resume_handles_200_fallback_and_rejects_bad_range_or_404(self):
        import ssl
        from urllib.error import HTTPError

        payload = self.archive(self.version)
        digest = hashlib.sha256(payload).hexdigest()
        manifest_url = sdk.BASE_URL + 'releases_linux.json'
        archive_url = sdk.BASE_URL + self.release_path
        manifest = json.dumps({'releases': [{
            'version': self.version, 'channel': 'stable', 'dart_sdk_arch': 'x64',
            'archive': self.release_path, 'sha256': digest,
        }]}).encode()
        cut = max(1, len(payload) // 2)

        class Resp(io.BytesIO):
            def __init__(self, url, body, status=200, headers=None, drop=False):
                super().__init__(body)
                self._url = url
                self.status = status
                self.headers = headers or {}
                self._drop = drop

            def geturl(self):
                return self._url

            def read(self, size=-1):
                chunk = super().read(size)
                if not chunk and self._drop:
                    self._drop = False
                    raise ssl.SSLEOFError('drop')
                return chunk

        # 1) Server ignores Range and replies 200 with full body -> clean restart & install.
        step = 0

        def fallback_200(target, *, timeout):
            nonlocal step
            url = target if isinstance(target, str) else target.full_url
            if url == manifest_url:
                return Resp(url, manifest)
            step += 1
            if step == 1:
                return Resp(url, payload[:cut], 200, {'Content-Length': str(len(payload))}, drop=True)
            return Resp(url, payload, 200, {'Content-Length': str(len(payload))})

        cache_ok = self.root / 'cache-200'
        with mock.patch.object(sdk, 'urlopen', side_effect=fallback_200), \
                mock.patch.object(sdk.time, 'sleep'), \
                contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(sdk.ensure_flutter(self.version, self.env, cache_ok), cache_ok / self.version)
        self.assertEqual(step, 2)

        # 2) ETag swap on 206 is rejected without publishing.
        etag_step = 0

        def swapped_etag(target, *, timeout):
            nonlocal etag_step
            url = target if isinstance(target, str) else target.full_url
            if url == manifest_url:
                return Resp(url, manifest)
            etag_step += 1
            if etag_step == 1:
                return Resp(url, payload[:cut], 200, {'Content-Length': str(len(payload)), 'ETag': '"a"'}, drop=True)
            return Resp(url, payload[cut:], 206,
                        {'Content-Range': f'bytes {cut}-{len(payload) - 1}/{len(payload)}', 'ETag': '"b"'})

        with mock.patch.object(sdk, 'urlopen', side_effect=swapped_etag), \
                mock.patch.object(sdk.time, 'sleep'), \
                contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaisesRegex(sdk.SDKError, 'changed mid-download'):
                sdk.ensure_flutter(self.version, self.env, self.cache)
        self.assertFalse((self.cache / self.version).exists())

        # 3) HTTP 404 is not retried.
        calls_404 = 0

        def missing(target, *, timeout):
            nonlocal calls_404
            url = target if isinstance(target, str) else target.full_url
            if url == manifest_url:
                return Resp(url, manifest)
            calls_404 += 1
            raise HTTPError(url, 404, 'Not Found', {}, io.BytesIO())

        with mock.patch.object(sdk, 'urlopen', side_effect=missing), \
                mock.patch.object(sdk.time, 'sleep'), \
                contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(sdk.SDKError):
                sdk.ensure_flutter(self.version, self.env, self.cache)
        self.assertEqual(calls_404, 1)
