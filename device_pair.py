#!/usr/bin/env python3
"""Resumable device-flow helper.

start : request a device code, save it (secrets/device_state.json), print the
        user code, exit.
poll  : reuse the saved device code, poll until approved, then store the FULL
        token payload (access + refresh) through gh_app.py.

    python3 device_pair.py status          # is a code already pending?
    python3 device_pair.py start           # get a code (refuses a duplicate)
    python3 device_pair.py poll 60         # resume polling, 60s at a time
    python3 device_pair.py poll --new 60   # discard the stale code, start + poll

Why: background processes are reaped between agent turns in this sandbox, but a
GitHub device code stays valid ~15 min. So we persist the device_code and can
resume polling in a later turn without issuing a new user code.
"""
import json
import os
import sys
import time
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))

# pull the client id straight out of gh_app.py's own config so we never diverge
sys.path.insert(0, HERE)
import gh_app  # noqa: E402

# The pending code goes in the secrets dir: gitignored (never committed) and,
# unlike /tmp, it survives between agent turns.
STATE = os.path.join(gh_app.SECRET_DIR, "device_state.json")

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
    # Never hand out a second code while an approved-but-unpolled one may exist.
    # Poll first; a pending code that the human already approved is picked up there.
    if os.path.exists(STATE):
        try:
            old = json.load(open(STATE))
            left = old.get("expires_in", 900) - (time.time() - old.get("issued_at", 0))
        except (OSError, ValueError):
            left = 0
        if left > 30:
            print(f"a code is already pending: {old.get('user_code')} ({int(left)}s left)")
            print("-> run: python3 device_pair.py poll 60    (or `poll --new` to replace it)")
            return 6
        os.remove(STATE)
    d = _post(DEVICE_URL, {"client_id": CLIENT_ID, "scope": scope})
    if "device_code" not in d:
        print("ERROR requesting device code:", d)
        return 1
    d["issued_at"] = time.time()
    os.makedirs(os.path.dirname(STATE), exist_ok=True)
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
            # Store access AND refresh token. Writing only the access token
            # (the old `gh_app.py connect --token` shortcut) threw the
            # refresh token away, so ~8 h later everything asked for a new
            # device code again.
            gh_app.store_tokens(r, "device_flow_resume")
            exp = gh_app.token_expiry()
            print("APPROVED -- token stored")
            print(f"  token        : {gh_app.mask(tok)}")
            print(f"  refresh token: {'yes' if r.get('refresh_token') else 'no (will need re-pair in ~8h)'}")
            print(f"  expires      : {exp.strftime('%Y-%m-%d %H:%M UTC') if exp else 'unknown'}")
            print(f"  stored at    : {gh_app.TOKEN_FILE}")
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
    argv = sys.argv[1:]
    if not argv or argv[0] in ("-h", "--help", "help"):
        print(__doc__)
        print("usage:")
        print("  python3 device_pair.py start [--new]   # get a code, print it, exit")
        print("  python3 device_pair.py poll [SECONDS]  # resume polling the saved code")
        print("  python3 device_pair.py poll --new SECS # drop a stale code, start a fresh one")
        print("  python3 device_pair.py status          # what is pending?")
        sys.exit(0)
    cmd = argv[0]
    new = "--new" in argv
    rest = [a for a in argv[1:] if a != "--new"]
    if cmd == "status":
        if not os.path.exists(STATE):
            print("no pending device code")
            sys.exit(0)
        d = json.load(open(STATE))
        left = d.get("expires_in", 900) - (time.time() - d.get("issued_at", 0))
        print(f"pending code : {d.get('user_code')}")
        print(f"expires in   : {int(left)}s" if left > 0 else "expired")
        sys.exit(0)
    if new and os.path.exists(STATE):
        os.remove(STATE)
    if cmd == "start":
        sys.exit(start())
    if new:                                  # poll --new: fresh code, then poll it
        rc = start()
        if rc:
            sys.exit(rc)
    b = int(rest[0]) if rest else None
    sys.exit(poll(b))
