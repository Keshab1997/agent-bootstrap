"""Captain-lane regressions. Run the whole offline suite with python3 selftest.py."""
from __future__ import annotations

import json
from pathlib import Path
import unittest

import ci_dispatch
import task_spec as spec


def task(slug='first', allowed=('lesson.txt',), **changes):
    return dict(repo='Keshab1997/fixture', worker='A', task=slug, allowed=list(allowed),
                commit=f'test(lesson): {slug}', check={'kind': 'preflight'},
                arena={'branch': 'auto', 'base_sha': None}) | changes


class TaskSpecTests(unittest.TestCase):
    def test_a_narrow_arena_task_is_valid(self):
        data = spec.validate_task(task(allowed=('lib/home.dart', 'test/home_test.dart'),
                                      check={'kind': 'test', 'test': 'test/home_test.dart'}))
        self.assertEqual(data['arena'], {'branch': 'auto', 'base_sha': None})
        self.assertEqual(len(data['allowed']), 2)

    def test_stacked_task_accepts_a_full_sha_base(self):
        sha = 'a' * 40
        data = spec.validate_task(task(arena={'branch': 'auto', 'base_sha': sha}))
        self.assertEqual(data['arena']['base_sha'], sha)
        for bad in ('a' * 39, 'a' * 41, 'A' * 40, 'null'):
            with self.subTest(base=bad), self.assertRaises(spec.SpecError):
                spec.validate_task(task(arena={'branch': 'auto', 'base_sha': bad}))

    def test_shared_surfaces_and_secrets_are_not_assignable(self):
        for path in ('../foo', '/root/foo', 'pubspec.lock', '.github/workflows/build.yml',
                     'docs/*', 'secrets/access.txt', 'lib/model.g.dart', 'android/app/build.gradle',
                     'ios/Runner/Info.plist', 'lib/main.dart', 'lib/.env.local',
                     'android/app/upload.jks', 'google-services.json'):
            with self.subTest(path=path), self.assertRaises(spec.SpecError):
                spec.validate_task(task(allowed=(path,)))

    def test_manifest_rejects_bad_identity_and_check(self):
        for changes in ({'task': 'bad/ref'}, {'repo': 'other/fixture'}, {'worker': 'D'},
                        {'allowed': []}, {'allowed': [f'lib/f{i}.dart' for i in range(41)]},
                        {'allowed': ('a.dart', 'a.dart')},
                        {'commit': 'two\nlines'},
                        {'check': {'kind': 'flutter', 'version': 'latest', 'test': 'test/a_test.dart'}},
                        {'check': {'kind': 'test', 'test': 'lib/a_test.dart'}},
                        {'check': {'kind': 'test', 'test': 'test/a.dart'}},
                        {'arena': {'branch': 'main', 'base_sha': None}},
                        {'arena': {'branch': 'auto', 'base_sha': None}, 'base_sha': None},
                        {'tracker': 'https://example.com/x/issues/1'}):
            with self.subTest(changes=changes), self.assertRaises(spec.SpecError):
                spec.validate_task(task(**changes))

    def test_preflight_and_one_test_are_the_only_checks(self):
        for check in ({'kind': 'preflight'}, {'kind': 'test', 'test': 'test/a_test.dart'}):
            with self.subTest(check=check):
                self.assertEqual(spec.validate_task(task(check=check))['check'], check)


class CiLogTests(unittest.TestCase):
    """The Captain reads a red run's log in the same call; no second round trip."""

    def fake_fetch(self, lines):
        return lambda path: '\n'.join(lines) + '\n'

    def test_failed_log_shows_the_failing_step_and_context(self):
        lines = ['##[group]Run flutter test', 'flutter test'] + \
                [f'ok line {i}' for i in range(30)] + \
                ['##[error]Process completed with exit code 1.', 'test failed: home_screen_test.dart']
        out = ci_dispatch.failed_log('Keshab1997/fixture', 42, tail=8, fetch=self.fake_fetch(lines))
        self.assertIn('##[error]Process completed with exit code 1.', out)
        self.assertIn('test failed: home_screen_test.dart', out)
        self.assertTrue(all(line.startswith('      | ') for line in out.splitlines()))

    def test_failed_log_is_bounded_and_never_raises(self):
        out = ci_dispatch.failed_log('Keshab1997/fixture', 42, tail=3,
                                     fetch=self.fake_fetch(['a', 'b', 'c', 'd', 'e']))
        self.assertEqual(len(out.splitlines()), 3)

        def boom(path):
            raise RuntimeError('no permission')

        self.assertIn('log unavailable', ci_dispatch.failed_log('Keshab1997/fixture', 42, fetch=boom))
        self.assertIn('empty log', ci_dispatch.failed_log('Keshab1997/fixture', 42,
                                                          fetch=lambda path: ''))


class LaneDocTests(unittest.TestCase):
    """The docs must describe one lane: attached worker pushes, Captain runs CI."""

    docs = Path(__file__).parent

    def test_fast_lane_states_the_one_lane(self):
        text = (self.docs / 'FASTLANE.md').read_text()
        for needle in ('There is **one lane**', 'git push origin HEAD',
                       'AGENT <W> PUSHED', '--ref <arena/...> --watch 900 --logs',
                       'Workers CI কখনো dispatch করে না'):
            self.assertIn(needle, text)

    def test_worker_starter_is_self_contained(self):
        text = (self.docs / 'WORKER_START_PROMPT.md').read_text()
        for needle in ('git push origin HEAD', 'AGENT <W> PUSHED',
                       'Never `flutter analyze`, full `flutter test`'):
            self.assertIn(needle, text)
        for gone in ('gh_app.py connect', 'fetch-brief', 'Option B'):
            self.assertNotIn(gone, text)

    def test_no_doc_points_at_a_removed_tool_or_second_lane(self):
        removed = ('worker_lane', 'flutter_sdk', 'audit_fleet', 'fleet_bump', 'worker_up.sh',
                   'PROMPT-FOR-NEW-AGENT', 'AGENT_PROMPT_COPY', 'RESUME.md',
                   'LEGACY_WORKER_BRIEF', 'captain/examples', 'vault.py', 'Option B',
                   'Device Flow is primary', 'fetch-brief')
        for path in [*self.docs.glob('*.md'), *self.docs.parent.glob('*.md')]:
            text = path.read_text()
            for name in removed:
                self.assertNotIn(name, text, f'{path.name} still references {name}')

    def test_template_check_shapes_match_the_validator(self):
        text = (self.docs / 'WORKER_BRIEF_TEMPLATE.md').read_text()
        block = text.split('## `task.json`', 1)[1].split('```json\n', 1)[1].split('\n```', 1)[0]
        data = json.loads(block)
        self.assertIn('{{REPO}}', data['repo'])          # a template, not a literal task
        self.assertEqual(set(data['check']), {'kind'})
        self.assertEqual(data['arena'], {'branch': 'auto', 'base_sha': None})
