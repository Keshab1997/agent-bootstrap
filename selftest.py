#!/usr/bin/env python3
#!/usr/bin/env python3
"""Regression test: "why is it asking me to authorize again?"

Runs fully offline -- every GitHub call is stubbed, no token, no network. It
asserts the three rules that keep a paired session from being re-paired:

  1. `connect` never prints a device code while the stored token still works.
  2. A network blip / non-401 failure never starts a device flow.
  3. A missing expiry header never burns the single-use refresh token, and a
     failed refresh never tells the human to re-pair when the token still works.

    python3 selftest.py        # exit 0 = fixed, 1 = regression
"""
import argparse
import importlib.util
import os
import sys
import tempfile

SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gh_app.py")

tmp = tempfile.mkdtemp()
os.environ["GH_SECRET_DIR"] = tmp
os.environ["GITHUB_TOKEN_FILE"] = os.path.join(tmp, "gh_token.txt")
os.environ["GITHUB_REFRESH_TOKEN_FILE"] = os.path.join(tmp, "gh_refresh_token.txt")

spec = importlib.util.spec_from_file_location("gh_app", SRC)
gh = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gh)

fails = []


def check(name, cond, detail=""):
    print(("  PASS  " if cond else "  FAIL  ") + name + (f"   [{detail}]" if detail and not cond else ""))
    if not cond:
        fails.append(name)


def args(**kw):
    d = dict(scope=gh.DEFAULT_SCOPE, show_only=False, force=False, token=None)
    d.update(kw)
    return argparse.Namespace(**d)


# 1) connect with a still-valid stored token must NOT start a device flow
gh._write_secret(gh.TOKEN_FILE, "ghu_faketoken_for_test_only")
gh._write_secret(gh.REFRESH_FILE, "ghr_fake_refresh_for_test")

FAKE_DEVICE = {"device_code": "dc", "user_code": "TEST-CODE", "expires_in": 900,
               "interval": 5, "verification_uri": "https://github.com/login/device"}
FAKE_TOKEN = {"access_token": "ghu_faketoken_for_test_only", "token_type": "bearer"}


def fake_start(*a, **k):
    calls["device"] += 1
    return FAKE_DEVICE


calls = {"device": 0}
gh._api = lambda *a, **k: (200, {"login": "Keshab1997"})
gh.start_device_flow = fake_start
gh.print_code = lambda d: None           # keep the self-check output readable
gh.poll = lambda d: FAKE_TOKEN
gh.token_expiry = lambda *a, **k: None
rc = gh.cmd_connect(args())
check("connect skips device flow when token valid", calls["device"] == 0,
      f"device flow started {calls['device']}x")
check("connect exits 0 when already paired", rc == 0, f"rc={rc}")

# 2) connect MUST still ask when the stored token is dead (401)
gh._api = lambda *a, **k: (401, {"message": "Bad credentials"})
gh.start_device_flow = fake_start
calls["device"] = 0
rc = gh.cmd_connect(args())
check("connect requests a new code on 401", calls["device"] == 1,
      f"device flow started {calls['device']}x")

# 2b) a network blip must NOT trigger a device flow
gh._api = lambda *a, **k: (0, {"error": "transport", "message": "DNS"})
calls["device"] = 0
rc = gh.cmd_connect(args())
check("connect does not pair on transport error", calls["device"] == 0)
check("connect exits non-zero on transport error", rc != 0, f"rc={rc}")

# 3) --force always asks, even with a live token
gh._api = lambda *a, **k: (200, {"login": "Keshab1997"})
gh.start_device_flow = fake_start
calls["device"] = 0
gh.cmd_connect(args(force=True))
check("connect --force bypasses the guard", calls["device"] == 1)

# 4) expiry header missing + API 200 -> no refresh (refresh token stays unburned)
gh.token_expiry = lambda *a, **k: None
posted = {"n": 0}
gh._post_form = lambda *a, **k: posted.__setitem__("n", posted["n"] + 1) or (400, {"error": "bad_refresh_token"})
ok, msg = gh.refresh()
check("no blind refresh when expiry header missing", posted["n"] == 0, msg)
check("refresh reports token still valid", ok is True, msg)

# 5) refresh 401 + dead token -> clear message telling the human to re-pair
gh._api = lambda *a, **k: (401, {"message": "Bad credentials"})
ok, msg = gh.refresh(force=True)
check("dead token + failed refresh says re-pair", ok is False and "re-pair" in msg, msg)

# 6) lock helper exists and is re-entrant across sequential calls
gh._api = lambda *a, **k: (200, {"login": "Keshab1997"})
with gh._secret_lock():
    pass
with gh._secret_lock():
    pass
check("_secret_lock acquires/releases cleanly", True)

print()
print("ALL GOOD" if not fails else f"{len(fails)} FAILED: {fails}")
sys.exit(1 if fails else 0)
