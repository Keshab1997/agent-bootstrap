#!/usr/bin/env python3
"""Resumable device-flow helper.

start : request a device code, save it to device_state.json, print the user code, exit.
poll  : reuse the saved device code, poll until approved, then hand the
        access token to gh_app.py so it is stored the normal way.

Why: background processes are reaped between agent turns in this sandbox, but a
GitHub device code stays valid ~15 min. So we persist the device_code and can
resume polling in a later turn without issuing a new user code.
"""
import json
import os
import subprocess
import sys
import time
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
STATE = os.path.join(HERE, "device_state.json")

# pull the client id straight out of gh_app.py's own config so we never diverge
sys.path.insert(0, HERE)
import gh_app  # noqa: E402

CLIENT_ID = gh_app.CLIENT_ID
DEVICE_URL = gh_app.DEVICE_URL
TOKEN_URL = gh_app.TOKEN_URL
GRANT = gh_app.DEVICE_GRANT


def _post(url, data):
    body = urllib.parse.urlencode(data).encode()
    req = urllib.request.Request(
        url, data=body,
        headers={"Accept": "application/json",
                 "Content-Type": "application/x-www-form-urlencoded"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        return json.loads(e.read().decode() or "{}")


def start(scope="repo workflow read:user"):
    d = _post(DEVICE_URL, {"client_id": CLIENT_ID, "scope": scope})
    if "device_code" not in d:
        print("ERROR requesting device code:", d)
        return 1
    d["issued_at"] = time.time()
    with open(STATE, "w") as f:
        json.dump(d, f)
    os.chmod(STATE, 0o600)
    print("USER_CODE=" + d["user_code"])
    print("VERIFY_URL=" + d.get("verification_uri", "https://github.com/login/device"))
    print("EXPIRES_IN=" + str(d.get("expires_in", 900)))
    return 0


def poll(budget=None):
    if not os.path.exists(STATE):
        print("no pending device code -- run: python3 device_pair.py start")
        return 2
    d = json.load(open(STATE))
    interval = max(int(d.get("interval", 5)), 5)
    age = time.time() - d.get("issued_at", 0)
    left = d.get("expires_in", 900) - age
    if left <= 0:
        print("device code EXPIRED -- run start again for a fresh code")
        return 3
    if budget is None:
        budget = left
    budget = min(budget, left)
    deadline = time.time() + budget
    print(f"polling for approval (code {d['user_code']}, {int(left)}s left on the code)")
    while time.time() < deadline:
        r = _post(TOKEN_URL, {
            "client_id": CLIENT_ID,
            "device_code": d["device_code"],
            "grant_type": GRANT,
        })
        tok = r.get("access_token")
        if tok:
            print("APPROVED -- storing token via gh_app.py")
            res = subprocess.run(
                [sys.executable, os.path.join(HERE, "gh_app.py"), "connect", "--token", tok],
                cwd=HERE, capture_output=True, text=True,
            )
            sys.stdout.write(res.stdout[-2000:])
            sys.stderr.write(res.stderr[-2000:])
            try:
                os.remove(STATE)
            except OSError:
                pass
            return 0
        err = r.get("error", "")
        if err == "slow_down":
            interval = int(r.get("interval", interval + 5))
        elif err in ("expired_token", "access_denied", "incorrect_device_code",
                     "unsupported_grant_type", "incorrect_client_credentials"):
            print("STOP:", err, r.get("error_description", ""))
            return 4
        print(f"  waiting ({err or 'pending'}) -- retry in {interval}s", flush=True)
        time.sleep(interval)
    print("TIMEOUT for this turn -- code still valid, run poll again")
    return 5


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "poll"
    if cmd == "start":
        sys.exit(start())
    b = int(sys.argv[2]) if len(sys.argv) > 2 else None
    sys.exit(poll(b))
