#!/usr/bin/env python3
"""Offline auth regressions: refresh first, resume one code, never leak tokens.

    python3 selftest.py

Uses only stdlib, fake credentials and isolated temporary files. Every network
entry point is blocked/mocked. When piped without a local clone, the bootstrap
step first downloads gh_app.py and device_pair.py; the tests themselves are offline.
"""
from __future__ import annotations

import argparse
import atexit
import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from unittest import mock


def find_source() -> Path:
    here = Path(__file__).resolve().parent
    candidates = [os.environ.get("GH_APP_PY"), here / "gh_app.py",
                  Path("/home/user/agent-bootstrap/gh_app.py"), Path.cwd() / "gh_app.py"]
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            return Path(candidate).resolve()
    import urllib.request
    scratch = tempfile.TemporaryDirectory(prefix=".auth-selftest-src-", dir=Path.cwd())
    atexit.register(scratch.cleanup)
    dest = Path(scratch.name)
    for name in ("gh_app.py", "device_pair.py"):
        url = f"https://raw.githubusercontent.com/Keshab1997/agent-bootstrap/main/{name}"
        with urllib.request.urlopen(url, timeout=30) as response:
            (dest / name).write_bytes(response.read())
    return dest / "gh_app.py"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


SRC = find_source()
gh = load_module("gh_app", SRC)
dp = load_module("device_pair", SRC.with_name("device_pair.py"))
OLD_TOKEN = "fake-access-before-refresh-not-a-real-credential"
OLD_REFRESH = "fake-refresh-before-rotation-not-a-real-credential"
NEW_TOKEN = "fake-access-after-refresh-not-a-real-credential"
NEW_REFRESH = "fake-refresh-after-rotation-not-a-real-credential"
DEVICE = {"device_code": "fake-device-secret", "user_code": "TEST-CODE",
          "expires_in": 900, "interval": 5, "verification_uri": "https://github.com/login/device"}
PAYLOAD = {"access_token": NEW_TOKEN, "refresh_token": NEW_REFRESH,
           "token_type": "bearer", "refresh_token_expires_in": 15638400}


def args(**overrides):
    data = dict(scope=gh.DEFAULT_SCOPE, show_only=True, force=False, token=None)
    data.update(overrides)
    return argparse.Namespace(**data)


class AuthTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix=".auth-selftest-", dir=SRC.parent)
        self.addCleanup(self.directory.cleanup)
        directory = self.directory.name
        paths = dict(SECRET_DIR=directory, TOKEN_FILE=os.path.join(directory, "access.txt"),
                     REFRESH_FILE=os.path.join(directory, "refresh.txt"),
                     STATE_FILE=os.path.join(directory, "state.json"),
                     DEVICE_STATE_FILE=os.path.join(directory, "device_state.json"))
        self.patch(mock.patch.multiple(gh, **paths))
        self.output = io.StringIO()
        self.patch(contextlib.redirect_stdout(self.output))
        self.patch(contextlib.redirect_stderr(self.output))
        self.now = 1000.0
        self.patch(mock.patch.object(gh.time, "time", side_effect=lambda: self.now))
        self.patch(mock.patch.object(gh.time, "sleep", side_effect=self.sleep))
        self.patch(mock.patch.object(gh.urllib.request, "urlopen",
                                     side_effect=AssertionError("tests must not use the network")))
        self.api = self.patch(mock.patch.object(gh, "_api", return_value=(200, {"login": "test-user"})))
        self.expiry = self.patch(mock.patch.object(gh, "token_expiry", return_value=None))
        self.post = self.patch(mock.patch.object(gh, "_post_form",
                                                 side_effect=AssertionError("unexpected token request")))
        self.start = self.patch(mock.patch.object(gh, "start_device_flow",
                                                  side_effect=lambda *a, **k: dict(DEVICE)))

    def patch(self, patcher):
        # context managers as well as unittest.mock patches are supported.
        value = patcher.__enter__()
        self.addCleanup(patcher.__exit__, None, None, None)
        return value

    def sleep(self, seconds):
        self.assertGreaterEqual(seconds, 0)
        self.now += seconds

    def saved_session(self, refresh=True):
        gh._write_secret(gh.TOKEN_FILE, OLD_TOKEN)
        if refresh:
            gh._write_secret(gh.REFRESH_FILE, OLD_REFRESH)

    def respond(self, response):
        self.post.side_effect = None
        self.post.return_value = response

    def expired_then_recovered(self):
        self.api.side_effect = lambda *a, **kw: (
            (200, {"login": "test-user"}) if kw.get("token") == NEW_TOKEN
            else (401, {"message": "Bad credentials"}))
        self.respond((200, dict(PAYLOAD)))

    def pending(self, **updates):
        d = dict(DEVICE, issued_at=self.now, client_id=gh.CLIENT_ID)
        d.update(updates)
        gh._write_json(gh.DEVICE_STATE_FILE, d)
        return d

    def assert_no_pairing(self):
        self.start.assert_not_called()

    def test_valid_token_skips_device_flow(self):
        self.saved_session()
        self.assertEqual(gh.cmd_connect(args()), 0)
        self.assertIn("ALREADY CONNECTED", self.output.getvalue())
        self.assert_no_pairing()
        self.post.assert_not_called()

    def test_expired_access_refreshes_before_pairing(self):
        self.saved_session()
        self.expired_then_recovered()
        self.assertEqual(gh.cmd_connect(args()), 0)
        self.assertEqual(gh._read(gh.TOKEN_FILE), NEW_TOKEN)
        self.assertEqual(gh._read(gh.REFRESH_FILE), NEW_REFRESH)
        self.assert_no_pairing()
        self.assertEqual(self.post.call_count, 1)

    def test_status_recovers_without_device_flow(self):
        self.saved_session()
        self.expired_then_recovered()
        self.assertEqual(gh.cmd_status(None), 0)
        self.assertIn("verdict         : PAIRED", self.output.getvalue())
        self.assert_no_pairing()

    def test_missing_access_but_saved_refresh_recovers(self):
        gh._write_secret(gh.REFRESH_FILE, OLD_REFRESH)
        self.expired_then_recovered()
        self.assertEqual(gh.cmd_connect(args()), 0)
        self.assert_no_pairing()

    def test_dead_access_without_refresh_needs_one_code(self):
        self.saved_session(refresh=False)
        self.api.return_value = (401, {})
        self.assertEqual(gh.cmd_connect(args()), 0)
        self.assertEqual(self.start.call_count, 1)
        self.post.assert_not_called()

    def test_rejected_refresh_allows_new_pairing(self):
        self.saved_session()
        self.api.return_value = (401, {})
        self.respond((400, {"error": "bad_refresh_token"}))
        self.assertEqual(gh.cmd_connect(args()), 0)
        self.assertEqual(self.start.call_count, 1)

    def test_transient_refresh_errors_never_start_a_flow(self):
        self.saved_session()
        self.api.return_value = (401, {})
        for status, error in ((0, "transport"), (429, "rate_limit"), (503, "unavailable"),
                              (400, "unknown_error"), (401, "incorrect_client_credentials")):
            with self.subTest(status=status, error=error):
                self.respond((status, {"error": error}))
                self.assertEqual(gh.cmd_connect(args()), 1)
                self.assert_no_pairing()
                self.assertEqual(gh._read(gh.REFRESH_FILE), OLD_REFRESH)

    def test_api_blips_do_not_refresh_or_pair(self):
        self.saved_session()
        for status in (0, 403, 429, 500):
            with self.subTest(status=status):
                self.api.return_value = (status, {})
                self.assertEqual(gh.cmd_connect(args()), 1)
                self.assert_no_pairing()
                self.post.assert_not_called()

    def test_status_failure_never_opens_a_flow(self):
        self.assertEqual(gh.cmd_status(None), 1)
        self.assertIn("NOT PAIRED", self.output.getvalue())
        self.assert_no_pairing()

    def test_status_distinguishes_network_error_from_logout(self):
        self.saved_session()
        self.api.return_value = (503, {})
        self.assertEqual(gh.cmd_status(None), 1)
        self.assertIn("UNCONFIRMED", self.output.getvalue())
        self.assert_no_pairing()

    def test_missing_expiry_and_valid_token_does_not_rotate(self):
        self.saved_session()
        self.assertTrue(gh.refresh()[0])
        self.post.assert_not_called()

    def test_missing_expiry_and_network_error_does_not_rotate(self):
        self.saved_session()
        self.api.return_value = (0, {})
        self.assertFalse(gh.refresh()[0])
        self.post.assert_not_called()

    def test_far_expiry_does_not_rotate(self):
        self.saved_session()
        self.expiry.return_value = datetime.now(timezone.utc) + timedelta(hours=7)
        self.assertTrue(gh.refresh()[0])
        self.post.assert_not_called()

    def test_near_expiry_rotates_and_saves_both_tokens(self):
        self.saved_session()
        self.expiry.return_value = datetime.now(timezone.utc) + timedelta(seconds=30)
        self.respond((200, dict(PAYLOAD)))
        self.assertTrue(gh.refresh()[0])
        self.assertEqual(gh._read(gh.REFRESH_FILE), NEW_REFRESH)

    def test_failed_refresh_keeps_working_access(self):
        self.saved_session()
        self.respond((400, {"error": "bad_refresh_token"}))
        result = gh._refresh_result(force=True)
        self.assertTrue(result.ok)
        self.assertFalse(result.needs_pairing)

    def test_dead_refresh_and_dead_access_explain_repair(self):
        self.saved_session()
        self.api.return_value = (401, {})
        self.respond((400, {"error": "bad_refresh_token"}))
        result = gh._refresh_result(force=True)
        self.assertFalse(result.ok)
        self.assertTrue(result.needs_pairing)
        self.assertIn("re-pair", result.message)

    def test_post_refresh_check_error_does_not_pair(self):
        self.saved_session()
        self.api.side_effect = [(401, {}), (503, {})]
        self.respond((200, dict(PAYLOAD)))
        self.assertEqual(gh.cmd_connect(args()), 1)
        self.assert_no_pairing()
        self.assertEqual(gh._read(gh.TOKEN_FILE), NEW_TOKEN)

    def test_rotation_lock_does_not_rotate_the_winner_again(self):
        self.saved_session()

        @contextlib.contextmanager
        def another_process_wins(*a, **kw):
            gh._store_tokens(dict(PAYLOAD), "test")
            yield

        with mock.patch.object(gh, "_secret_lock", another_process_wins):
            result = gh._refresh_result(force=True)
        self.assertTrue(result.ok)
        self.post.assert_not_called()

    def test_rotation_winner_verification_blip_preserves_refresh(self):
        self.saved_session()
        self.api.return_value = (503, {})

        @contextlib.contextmanager
        def another_process_wins(*a, **kw):
            gh._store_tokens(dict(PAYLOAD), "test")
            yield

        with mock.patch.object(gh, "_secret_lock", another_process_wins):
            result = gh._refresh_result(force=True)
        self.assertFalse(result.ok)
        self.assertFalse(result.needs_pairing)
        self.post.assert_not_called()

    def test_force_can_replace_code_even_with_live_token(self):
        self.saved_session()
        self.pending(device_code="old-device")
        self.assertEqual(gh.cmd_connect(args(force=True)), 0)
        self.assertEqual(self.start.call_count, 1)
        self.assertEqual(gh.load_device_state()["device_code"], DEVICE["device_code"])

    def test_manual_token_cannot_inherit_old_refresh_or_pending_code(self):
        self.saved_session()
        self.pending()
        self.assertEqual(gh.cmd_connect(args(token=NEW_TOKEN)), 0)
        self.assertFalse(os.path.exists(gh.REFRESH_FILE))
        self.assertIsNone(gh.load_device_state())
        self.assertEqual(gh._read(gh.TOKEN_FILE), NEW_TOKEN)

    def test_atomic_write_restores_private_permissions(self):
        gh._write_secret(gh.TOKEN_FILE, OLD_TOKEN)
        os.chmod(gh.TOKEN_FILE, 0o644)
        gh._write_secret(gh.TOKEN_FILE, NEW_TOKEN)
        self.assertEqual(os.stat(gh.TOKEN_FILE).st_mode & 0o777, 0o600)
        self.assertFalse(list(Path(self.directory.name).glob(".pending-*")))

    def test_show_only_saves_resumable_code_privately(self):
        self.assertEqual(gh.cmd_connect(args()), 0)
        state = gh.load_device_state()
        self.assertEqual(state["issued_at"], self.now)
        self.assertEqual(state["client_id"], gh.CLIENT_ID)
        self.assertEqual(os.stat(gh.DEVICE_STATE_FILE).st_mode & 0o777, 0o600)

    def test_interrupt_after_printing_keeps_same_code(self):
        with mock.patch.object(gh, "poll", side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):
                gh.cmd_connect(args(show_only=False))
        original = gh.load_device_state()
        self.assertEqual(gh.cmd_connect(args()), 0)
        self.assertEqual(self.start.call_count, 1)
        self.assertEqual(gh.load_device_state(), original)

    def test_repeated_connect_does_not_request_another_code(self):
        gh.cmd_connect(args())
        self.now += 100
        gh.cmd_connect(args())
        self.assertEqual(self.start.call_count, 1)
        self.assertEqual(gh.load_device_state()["issued_at"], 1000)
        self.assertIn("800s remaining", self.output.getvalue())

    def test_helper_start_reuses_connect_state(self):
        gh.cmd_connect(args())
        self.assertEqual(dp.start(), 0)
        self.assertEqual(self.start.call_count, 1)

    def test_helper_start_does_not_pair_a_live_session(self):
        self.saved_session()
        self.assertEqual(dp.start(), 0)
        self.assert_no_pairing()

    def test_expired_pending_code_is_replaced_once(self):
        self.pending(issued_at=self.now - 901)
        self.assertEqual(gh.cmd_connect(args()), 0)
        self.assertEqual(self.start.call_count, 1)
        self.assertEqual(gh.load_device_state()["issued_at"], self.now)

    def test_legacy_helper_state_without_client_id_is_accepted(self):
        d = self.pending()
        del d["client_id"]
        gh._write_json(gh.DEVICE_STATE_FILE, d)
        self.assertEqual(gh.get_device_flow()["device_code"], d["device_code"])
        self.assert_no_pairing()

    def test_corrupt_state_is_not_silently_replaced(self):
        for bad in ("not json", "[]", '{"device_code": "partial"}'):
            with self.subTest(bad=bad):
                gh._write_secret(gh.DEVICE_STATE_FILE, bad)
                with self.assertRaises(SystemExit):
                    gh.get_device_flow()
                self.assert_no_pairing()

    def test_wrong_app_pending_code_requires_explicit_replacement(self):
        self.pending(client_id="another-app")
        with self.assertRaises(SystemExit):
            gh.get_device_flow()
        self.assert_no_pairing()
        gh.get_device_flow(force=True)
        self.assertEqual(gh.load_device_state()["client_id"], gh.CLIENT_ID)

    def test_force_recovers_corrupt_state(self):
        gh._write_secret(gh.DEVICE_STATE_FILE, "broken json")
        self.assertEqual(gh.cmd_connect(args(force=True)), 0)
        self.assertIsNotNone(gh.load_device_state())

    def test_bounded_poll_resumes_without_restarting_expiry_or_interval(self):
        d = self.pending()
        self.respond((400, {"error": "authorization_pending"}))
        self.assertIsNone(gh.poll(d, budget=3))
        self.assertEqual(self.post.call_count, 1)
        saved = gh.load_device_state()
        self.assertEqual(saved["issued_at"], 1000)
        self.assertEqual(saved["next_poll_at"], 1005)
        self.assertIsNone(gh.poll(saved, budget=2))
        self.assertEqual(self.post.call_count, 1)
        self.assertIsNone(gh.poll(gh.load_device_state(), budget=1))
        self.assertEqual(self.post.call_count, 2)

    def test_slow_down_survives_restart(self):
        d = self.pending()
        self.respond((400, {"error": "slow_down"}))
        self.assertIsNone(gh.poll(d, budget=1))
        saved = gh.load_device_state()
        self.assertEqual(saved["interval"], 10)
        self.assertEqual(saved["next_poll_at"], 1010)
        self.assertIsNone(gh.poll(saved, budget=2))
        self.assertEqual(self.post.call_count, 1)

    def test_approval_saves_access_and_refresh_before_clearing_state(self):
        d = self.pending()
        self.respond((200, dict(PAYLOAD)))
        self.assertEqual(gh.poll(d, budget=60), PAYLOAD)
        self.assertEqual(gh._read(gh.TOKEN_FILE), NEW_TOKEN)
        self.assertEqual(gh._read(gh.REFRESH_FILE), NEW_REFRESH)
        self.assertIsNone(gh.load_device_state())

    def test_connect_completes_shared_polling_path(self):
        self.respond((200, dict(PAYLOAD)))
        self.assertEqual(gh.cmd_connect(args(show_only=False)), 0)
        self.assertEqual(gh._read(gh.REFRESH_FILE), NEW_REFRESH)
        self.assertIsNone(gh.load_device_state())

    def test_helper_polls_code_created_by_connect(self):
        gh.cmd_connect(args())
        self.respond((200, dict(PAYLOAD)))
        self.assertEqual(dp.poll(60), 0)
        self.assertEqual(self.start.call_count, 1)
        self.assertEqual(gh._read(gh.REFRESH_FILE), NEW_REFRESH)
        self.assertIsNone(gh.load_device_state())

    def test_helper_after_approval_does_not_start_new_flow(self):
        self.saved_session()
        self.assertEqual(dp.poll(60), 0)
        self.assert_no_pairing()

    def test_helper_budget_timeout_keeps_pending_code(self):
        self.pending()
        self.respond((400, {"error": "authorization_pending"}))
        self.assertEqual(dp.poll(1), 5)
        self.assertIsNotNone(gh.load_device_state())
        self.assert_no_pairing()

    def test_helper_expired_code_never_silently_starts_another(self):
        self.pending(issued_at=self.now - 901)
        self.assertEqual(dp.poll(60), 3)
        self.post.assert_not_called()
        self.assert_no_pairing()

    def test_poll_uses_original_expiry(self):
        d = self.pending(issued_at=self.now - 899)
        self.respond((400, {"error": "authorization_pending"}))
        with self.assertRaisesRegex(SystemExit, "EXPIRED"):
            gh.poll(d, budget=60)
        self.assertEqual(self.now, 1001)
        self.assertIsNone(gh.load_device_state())
        self.assertEqual(self.post.call_count, 1)

    def test_denial_clears_only_that_pending_flow(self):
        d = self.pending()
        self.respond((400, {"error": "access_denied"}))
        with self.assertRaisesRegex(SystemExit, "access_denied"):
            gh.poll(d, budget=60)
        self.assertIsNone(gh.load_device_state())
        self.assert_no_pairing()

    def test_poll_transport_error_preserves_code_and_backs_off(self):
        d = self.pending()
        self.respond((0, {"error": "transport"}))
        self.assertIsNone(gh.poll(d, budget=1))
        self.assertEqual(gh.load_device_state()["interval"], 10)
        self.assert_no_pairing()

    def test_transport_backoff_never_reduces_server_poll_interval(self):
        d = self.pending(interval=75)
        self.respond((0, {"error": "transport"}))
        self.assertIsNone(gh.poll(d, budget=1))
        self.assertEqual(gh.load_device_state()["interval"], 75)

    def test_poll_configuration_error_keeps_code_without_repair(self):
        d = self.pending()
        self.respond((400, {"error": "incorrect_client_credentials"}))
        with self.assertRaisesRegex(SystemExit, "do not request another code"):
            gh.poll(d, budget=60)
        self.assertIsNotNone(gh.load_device_state())

    def test_helper_without_code_or_session_does_not_mint_code(self):
        self.assertEqual(dp.poll(60), 2)
        self.assert_no_pairing()
        self.post.assert_not_called()

    def test_second_poller_is_rejected_without_network(self):
        d = self.pending()
        with mock.patch.object(gh, "_secret_lock", side_effect=BlockingIOError):
            with self.assertRaisesRegex(SystemExit, "already being polled"):
                gh.poll(d, budget=60)
        self.post.assert_not_called()

    def test_old_poller_cannot_delete_new_pending_code(self):
        old = self.pending()
        self.pending(device_code="newer-device")
        gh.clear_device_state(old)
        self.assertEqual(gh.load_device_state()["device_code"], "newer-device")

    def test_nonfinite_lifetimes_are_rejected(self):
        for value in (float("inf"), float("nan"), -1):
            with self.subTest(value=value):
                self.pending(expires_in=value)
                with self.assertRaises(SystemExit):
                    gh.load_device_state()
                self.assert_no_pairing()

    def test_replaced_flow_cannot_store_late_approval(self):
        d = self.pending()

        def late_response(*a, **kw):
            self.pending(device_code="replacement-device")
            return 200, dict(PAYLOAD)

        self.post.side_effect = late_response
        with self.assertRaisesRegex(SystemExit, "replaced"):
            gh.poll(d, budget=60)
        self.assertIsNone(gh._read(gh.TOKEN_FILE))
        self.assertEqual(gh.load_device_state()["device_code"], "replacement-device")

    def test_token_write_failure_does_not_clear_pending_code(self):
        d = self.pending()
        self.respond((200, dict(PAYLOAD)))
        real_write = gh._write_secret

        def interrupted_write(path, value):
            if path == gh.REFRESH_FILE:
                raise OSError("simulated interrupted write")
            return real_write(path, value)

        with mock.patch.object(gh, "_write_secret", side_effect=interrupted_write):
            with self.assertRaises(OSError):
                gh.poll(d, budget=60)
        self.assertIsNotNone(gh.load_device_state())

    def test_console_and_metadata_do_not_contain_full_credentials(self):
        self.respond((200, dict(PAYLOAD)))
        gh.cmd_connect(args(show_only=False))
        output = self.output.getvalue() + Path(gh.STATE_FILE).read_text()
        for secret in (NEW_TOKEN, NEW_REFRESH, DEVICE["device_code"]):
            self.assertNotIn(secret, output)
        state = json.loads(Path(gh.STATE_FILE).read_text())
        self.assertTrue(state["has_refresh_token"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
