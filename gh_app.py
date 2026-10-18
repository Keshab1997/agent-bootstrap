#!/usr/bin/env python3
"""
gh_app.py -- standalone GitHub App connector (OAuth Device Flow).

ZERO DEPENDENCIES: python3 stdlib only. No pip install needed.
ZERO SECRETS:      nothing sensitive is stored in this repo.

Run this, read the 8-character code out to the human, they approve it in a
browser, and you get a working GitHub API token. That's the whole flow.

    python3 gh_app.py connect              # safe: skips the flow if already paired
    python3 gh_app.py connect --force      # force a new device code
    python3 gh_app.py connect --show-only  # save/reuse a code; poll in a later turn
    python3 gh_app.py status               # check/refresh the saved session; no device flow
    python3 gh_app.py whoami
    python3 gh_app.py repos [--limit 20]
    python3 gh_app.py api GET /user/repos
    python3 gh_app.py api POST /repos/Keshab1997/foo/issues --data '{...}'
    python3 gh_app.py refresh              # rotate using the refresh token
    python3 gh_app.py revoke               # disconnect + wipe local tokens
    python3 gh_app.py env                  # print an export line for the token

Token lands in  $GITHUB_TOKEN_FILE  or  ./secrets/gh_token.txt
Never commit that path. (.gitignore here already blocks secrets/.)
"""
from __future__ import annotations

import argparse
import contextlib
import json
import math
import os
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import NamedTuple

# --------------------------------------------------------------------------- #
# App metadata -- read from app-meta.json when present, else use these values. #
# --------------------------------------------------------------------------- #
HERE = os.path.dirname(os.path.abspath(__file__))
META_PATH = os.path.join(HERE, "app-meta.json")


def _meta() -> dict:
    try:
        with open(META_PATH) as fh:
            return json.load(fh)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


_M = _meta()
_APP = _M.get("app", {})
_EP = _M.get("endpoints", {})

CLIENT_ID = os.environ.get("GH_APP_CLIENT_ID") or _APP.get("client_id", "Iv23lieh6Kastc59yOsf")
APP_SLUG = _APP.get("slug", "keshab-flutter-assistant")
APP_ID = _APP.get("app_id", 4611920)
INSTALLATION_ID = int(os.environ.get("GH_INSTALLATION_ID")
                      or _M.get("installation", {}).get("id", 154119208))
ACCOUNT = _M.get("github", {}).get("account", "Keshab1997")

DEVICE_URL = _EP.get("device_code", "https://github.com/login/device/code")
VERIFICATION_URI = _EP.get("verification_uri", "https://github.com/login/device")
TOKEN_URL = _EP.get("access_token", "https://github.com/login/oauth/access_token")
API = _EP.get("api", "https://api.github.com")
API_VERSION = _EP.get("api_version", "2022-11-28")

SECRET_DIR = os.environ.get("GH_SECRET_DIR") or os.path.join(HERE, "secrets")
TOKEN_FILE = os.environ.get("GITHUB_TOKEN_FILE") or os.path.join(SECRET_DIR, "gh_token.txt")
REFRESH_FILE = os.environ.get("GITHUB_REFRESH_TOKEN_FILE") or os.path.join(SECRET_DIR, "gh_refresh_token.txt")
STATE_FILE = os.path.join(SECRET_DIR, "gh_state.json")
DEVICE_STATE_FILE = os.path.join(SECRET_DIR, "device_state.json")

UA = "gh_app.py (agent-bootstrap)"
REFRESH_BUFFER_SECONDS = 300
DEVICE_GRANT = "urn:ietf:params:oauth:grant-type:device_code"

# Scopes are ignored for GitHub Apps (the App's own permissions decide access),
# but we still send a sensible default so the flow works for OAuth Apps too.
DEFAULT_SCOPE = os.environ.get("GH_SCOPE", "read:user repo")


# --------------------------------------------------------------------------- #
# tiny helpers
# --------------------------------------------------------------------------- #
def _now() -> str:
    return datetime.now(timezone.utc).strftime("%H:%M:%SZ")


def say(msg: str = "") -> None:
    print(msg, flush=True)


def _read(path: str) -> str | None:
    try:
        with open(path) as fh:
            v = fh.read().strip()
        return v or None
    except FileNotFoundError:
        return None


def _write_secret(path: str, value: str) -> None:
    # Replace atomically: an interrupted turn must not leave half a token/state.
    directory = os.path.dirname(os.path.abspath(path))
    os.makedirs(directory, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".pending-", dir=directory)
    try:
        with os.fdopen(fd, "w") as fh:
            fh.write(value + "\n")
        os.replace(tmp, path)                 # mkstemp also guarantees mode 0600
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)


def _write_json(path: str, obj: dict) -> None:
    _write_secret(path, json.dumps(obj, indent=2, sort_keys=True))


@contextlib.contextmanager
def _secret_lock(name: str = ".rotate.lock", blocking: bool = True):
    """Serialise rotation / pending-code updates within one secrets directory."""
    os.makedirs(SECRET_DIR, exist_ok=True)
    try:
        import fcntl
    except ImportError:                      # non-POSIX: best effort only
        yield
        return
    with open(os.path.join(SECRET_DIR, name), "w") as fh:
        flags = fcntl.LOCK_EX | (0 if blocking else fcntl.LOCK_NB)
        fcntl.flock(fh.fileno(), flags)
        try:
            yield
        finally:
            fcntl.flock(fh.fileno(), fcntl.LOCK_UN)


def mask(tok: str | None, head: int = 6, tail: int = 4) -> str:
    if not tok:
        return "(none)"
    if len(tok) <= head + tail + 3:
        return "*" * len(tok)
    return f"{tok[:head]}...{tok[-tail:]}"


def _do(req: urllib.request.Request) -> tuple[int, dict]:
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read().decode()
            try:
                return resp.status, json.loads(raw)
            except json.JSONDecodeError:
                return resp.status, {"_raw": raw}
    except urllib.error.HTTPError as e:
        raw = e.read().decode(errors="replace")
        try:
            return e.code, json.loads(raw)
        except json.JSONDecodeError:
            return e.code, {"_raw": raw}
    except Exception as e:  # noqa: BLE001
        return 0, {"error": "transport", "message": str(e)}


def _post_form(url: str, data: dict) -> tuple[int, dict]:
    body = urllib.parse.urlencode(data).encode()
    return _do(urllib.request.Request(url, data=body, method="POST", headers={
        "Accept": "application/json",
        "User-Agent": UA,
        "Content-Type": "application/x-www-form-urlencoded",
    }))


def _api(method: str, path_or_url: str, token: str | None = None,
         payload: dict | None = None):
    url = path_or_url if path_or_url.startswith("http") else API + path_or_url
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": API_VERSION,
        "User-Agent": UA,
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = None
    if payload is not None:
        data = json.dumps(payload).encode()
        headers["Content-Type"] = "application/json"
    return _do(urllib.request.Request(url, data=data, method=method, headers=headers))


# --------------------------------------------------------------------------- #
# token lifecycle
# --------------------------------------------------------------------------- #
def token_expiry(tok: str | None = None) -> datetime | None:
    """Read GitHub's `github-authentication-token-expiration` response header."""
    tok = tok or _read(TOKEN_FILE)
    if not tok:
        return None
    req = urllib.request.Request(f"{API}/user", method="HEAD", headers={
        "Authorization": f"Bearer {tok}",
        "Accept": "application/vnd.github+json",
        "User-Agent": UA,
    })
    exp = None
    try:
        with urllib.request.urlopen(req, timeout=25) as resp:
            exp = resp.headers.get("github-authentication-token-expiration")
    except urllib.error.HTTPError as e:
        exp = e.headers.get("github-authentication-token-expiration")
    except Exception:  # noqa: BLE001
        return None
    if not exp:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S %Z", "%Y-%m-%d %H:%M:%S UTC"):
        try:
            return datetime.strptime(exp.strip(), fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def store_tokens(payload: dict, source: str = "device_flow") -> None:
    """Public entry point: persist a full token payload (access + refresh).

    Callers that obtained tokens themselves (e.g. device_pair.py) MUST use this
    instead of writing only the access token: dropping the refresh_token is what
    forces a fresh device flow every ~8 hours.
    """
    with _secret_lock():
        _store_tokens(payload, source)


def _store_tokens(payload: dict, source: str) -> None:
    at = payload["access_token"]
    _write_secret(TOKEN_FILE, at)
    if payload.get("refresh_token"):
        _write_secret(REFRESH_FILE, payload["refresh_token"])
    elif os.path.exists(REFRESH_FILE):
        # A manual PAT / different login must not inherit another login's refresh.
        os.remove(REFRESH_FILE)
    _write_json(STATE_FILE, {
        "connected_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": source,
        "account": ACCOUNT,
        "app_slug": APP_SLUG,
        "client_id": CLIENT_ID,
        "installation_id": INSTALLATION_ID,
        "token_prefix": at[:4],
        "token_length": len(at),
        "token_type": payload.get("token_type", "bearer"),
        "scope_field": payload.get("scope", ""),
        "has_refresh_token": bool(payload.get("refresh_token")),
        "refresh_token_expires_in_days": round(
            (payload.get("refresh_token_expires_in") or 0) / 86400, 1),
        "token_file": TOKEN_FILE,
    })


class RefreshResult(NamedTuple):
    ok: bool
    message: str
    needs_pairing: bool = False


def refresh(force: bool = False) -> tuple[bool, str]:
    """Refresh if needed; retain the public (ok, message) return contract."""
    result = _refresh_result(force)
    return result.ok, result.message


def _refresh_result(force: bool = False) -> RefreshResult:
    tok = _read(TOKEN_FILE)
    ref = _read(REFRESH_FILE)
    if not ref:
        return RefreshResult(False, "no refresh token stored -- run `connect` if needed", True)

    exp = token_expiry(tok) if tok and not force else None
    if exp and not force:
        left = (exp - datetime.now(timezone.utc)).total_seconds()
        if left > REFRESH_BUFFER_SECONDS:
            return RefreshResult(True, f"token still valid ({left/3600:.1f}h left), no refresh needed")
    elif tok and not force:
        # Missing expiry is not evidence of expiry. Do not rotate on a network blip.
        st, _ = _api("GET", "/user", token=tok)
        if st == 200:
            return RefreshResult(True, "token valid (expiry header missing, API 200) -- no refresh needed")
        if st != 401:
            return RefreshResult(False, f"token check unavailable (HTTP {st}); retry later, do not re-pair")

    with _secret_lock():
        return _refresh_locked(tok, ref)


def _refresh_locked(observed_token: str | None, observed_refresh: str) -> RefreshResult:
    # Re-check the winner after acquiring the lock, not just re-read and rotate
    # its brand-new single-use refresh token a second time.
    tok = _read(TOKEN_FILE)
    ref = _read(REFRESH_FILE)
    if (tok, ref) != (observed_token, observed_refresh):
        st, _ = _api("GET", "/user", token=tok) if tok else (401, {})
        if st == 200:
            return RefreshResult(True, "another process restored the token -- no refresh needed")
        if st != 401:
            return RefreshResult(False, "token changed; could not verify it -- retry later, do not re-pair")
    if not ref:
        return RefreshResult(False, "no refresh token stored -- run `connect` if needed", True)

    st, payload = _post_form(TOKEN_URL, {
        "client_id": CLIENT_ID,
        "grant_type": "refresh_token",
        "refresh_token": ref,
    })
    if payload.get("access_token"):
        _store_tokens(payload, "refresh")
        return RefreshResult(True, "saved session refreshed -- no browser approval needed")

    # A failed proactive refresh does not invalidate an access token that works.
    code, _ = _api("GET", "/user", token=tok) if tok else (401, {})
    if code == 200:
        return RefreshResult(True, "refresh unavailable, but the stored token still works")
    error = payload.get("error", "unknown_error")
    # Only a definite credential rejection justifies another human approval.
    # Transport / rate-limit / server / app-configuration errors do not.
    rejected = (code == 401 and st in (200, 400, 401)
                and error in ("bad_refresh_token", "invalid_grant"))
    advice = "run `connect` to re-pair" if rejected else "retry later, do not re-pair"
    return RefreshResult(False, f"refresh failed (HTTP {st}, {error}) -- {advice}", rejected)


def connection_status() -> tuple[int, dict, bool, str]:
    """Check, then recover an expired/missing access token. Never opens a flow.

    Returns HTTP status, user, whether pairing is necessary, and a safe message.
    connect and status share this path so neither mistakes expiry for logout.
    """
    tok = _read(TOKEN_FILE)
    st, user = _api("GET", "/user", token=tok) if tok else (401, {})
    if st == 200:
        return st, user, False, ""
    if st != 401:
        return st, user, False, "could not verify the saved session -- retry later, do not re-pair"
    if not _read(REFRESH_FILE):
        return st, user, True, "no usable saved session or refresh token"

    result = _refresh_result(force=True)       # access token was actually rejected
    if not result.ok:
        return st, user, result.needs_pairing, result.message
    tok = _read(TOKEN_FILE)
    st, user = _api("GET", "/user", token=tok) if tok else (401, {})
    # A successful refresh followed by an inconclusive check is not a reason
    # to immediately request yet another login.
    return st, user, False, result.message


def get_token(auto_refresh: bool = True) -> str:
    tok = _read(TOKEN_FILE)
    if not tok:
        raise SystemExit(
            "ERROR: no token stored.\n"
            "  run:  python3 gh_app.py connect\n"
            "  it restores the saved session first; show a code only if one is printed.")
    if auto_refresh:
        ok, msg = refresh()
        if not ok:
            print(f"  ! {msg}", file=sys.stderr)
        tok = _read(TOKEN_FILE) or tok
    return tok


# --------------------------------------------------------------------------- #
# device flow
# --------------------------------------------------------------------------- #
def start_device_flow(scope: str = DEFAULT_SCOPE) -> dict:
    st, d = _post_form(DEVICE_URL, {"client_id": CLIENT_ID, "scope": scope})
    if not d.get("device_code") or not d.get("user_code"):
        raise SystemExit(
            f"ERROR: could not get a device code (HTTP {st}, {d.get('error', 'unknown_error')}).\n"
            f"  Check that client_id={CLIENT_ID} has Device Flow enabled.")
    return d


def load_device_state() -> dict | None:
    try:
        with open(DEVICE_STATE_FILE) as fh:
            d = json.load(fh)
        if (not isinstance(d, dict)
                or not isinstance(d.get("device_code"), str) or not d["device_code"]
                or not isinstance(d.get("user_code"), str) or not d["user_code"]
                or not isinstance(d.get("issued_at"), (int, float))
                or not isinstance(d.get("expires_in"), (int, float))
                or not isinstance(d.get("interval", 5), (int, float))
                or not isinstance(d.get("next_poll_at", 0), (int, float))):
            raise ValueError("invalid state")
        numbers = (d["issued_at"], d["expires_in"], d.get("interval", 5), d.get("next_poll_at", 0))
        if not all(math.isfinite(value) and value >= 0 for value in numbers):
            raise ValueError("invalid lifetime")
    except FileNotFoundError:
        return None
    except (ValueError, TypeError, OverflowError):
        raise SystemExit("ERROR: pending device state is invalid; use `connect --force` to replace it.") from None
    if d.get("client_id", CLIENT_ID) != CLIENT_ID:
        raise SystemExit("ERROR: pending code belongs to another app; use `connect --force` to replace it.")
    return d


def device_seconds_left(d: dict) -> float:
    return max(0, d["issued_at"] + d["expires_in"] - time.time())


def get_device_flow(scope: str = DEFAULT_SCOPE, force: bool = False) -> dict:
    with _secret_lock(".device.lock"):
        d = None if force else load_device_state()
        if d and device_seconds_left(d) > 0:
            say("Resuming the saved device code -- no new approval request.")
            return d
        d = start_device_flow(scope)
        d.update(issued_at=time.time(), client_id=CLIENT_ID)
        d.setdefault("expires_in", 900)
        d.setdefault("interval", 5)
        # Save BEFORE printing: the same code survives show-only, interruption,
        # and a switch from connect to device_pair.py in the following turn.
        _write_json(DEVICE_STATE_FILE, d)
        return d


def clear_device_state(d: dict | None = None) -> None:
    with _secret_lock(".device.lock"):
        if not os.path.exists(DEVICE_STATE_FILE):
            return
        if d is not None:
            current = load_device_state()
            if not current or current["device_code"] != d["device_code"]:
                return                      # never delete a newer forced flow
        os.remove(DEVICE_STATE_FILE)


def _save_device_progress(d: dict) -> None:
    with _secret_lock(".device.lock"):
        current = load_device_state()
        if not current or current["device_code"] != d["device_code"]:
            raise SystemExit("Device flow changed; check `status` or resume `connect`.")
        _write_json(DEVICE_STATE_FILE, d)


def print_code(d: dict) -> None:
    say("")
    say("=" * 66)
    say("  GITHUB DEVICE FLOW  --  a human must do the next step")
    say("=" * 66)
    say(f"  1. Open     : {d.get('verification_uri', VERIFICATION_URI)}")
    say(f"  2. Enter    : {d['user_code']}")
    say("  3. Click    : Continue -> Authorize")
    say(f"  Account     : {ACCOUNT}   App: {APP_SLUG}")
    say(f"  Code expires: {int(device_seconds_left(d))}s remaining")
    say("  Resume      : python3 device_pair.py poll 60")
    say("=" * 66)
    say("")


def poll(d: dict, budget: float | None = None) -> dict | None:
    """Poll one SAVED flow. On success persist both tokens, then clear its state.

    None means only the caller's time budget ended; the code remains resumable.
    The original issued_at and GitHub's poll interval survive every restart.
    """
    try:
        with _secret_lock(".device-poll.lock", blocking=False):
            return _poll_device(d, budget)
    except BlockingIOError:
        raise SystemExit("Approval is already being polled in this workspace; wait for that process.") from None


def _poll_device(d: dict, budget: float | None) -> dict | None:
    left = device_seconds_left(d)
    if left <= 0:
        clear_device_state(d)
        raise SystemExit("ERROR: device code EXPIRED -- run `connect` for a new code.")
    deadline = time.time() + (left if budget is None else min(max(0, budget), left))
    interval = max(d.get("interval", 5), 5)
    say(f"[{_now()}] polling for approval (code {d['user_code']}) ...")
    while time.time() < deadline:
        wait = d.get("next_poll_at", 0) - time.time()
        if wait > 0:
            time.sleep(min(wait, max(0, deadline - time.time())))
            continue
        # Save the next allowed poll before the HTTP request, even if this
        # process is interrupted while waiting for the response.
        d["next_poll_at"] = time.time() + interval
        _save_device_progress(d)
        st, payload = _post_form(TOKEN_URL, {
            "client_id": CLIENT_ID,
            "device_code": d["device_code"],
            "grant_type": DEVICE_GRANT,
        })
        if payload.get("access_token"):
            with _secret_lock(".device.lock"):
                current = load_device_state()
                if not current or current["device_code"] != d["device_code"]:
                    raise SystemExit("Device flow was replaced; resume the current saved flow.")
                store_tokens(payload, "device_flow")
                os.remove(DEVICE_STATE_FILE)  # only after BOTH tokens were saved
            return payload
        error = payload.get("error", "")
        if error == "slow_down":
            interval = max(interval + 5, payload.get("interval", 0))
        elif error in ("expired_token", "access_denied", "incorrect_device_code"):
            clear_device_state(d)
            raise SystemExit(f"ERROR: {error} (HTTP {st}) -- run `connect` when ready to pair.")
        elif error in ("incorrect_client_credentials", "unsupported_grant_type"):
            raise SystemExit(f"ERROR: {error} -- check app configuration; do not request another code.")
        elif st == 0:
            interval = max(interval, min(interval * 2, 60))  # never undo GitHub's slow_down
        d.update(interval=interval, next_poll_at=time.time() + interval)
        _save_device_progress(d)
        say(f"  waiting ({error or 'pending'}) -- retry in {interval}s")
    if device_seconds_left(d) <= 0:
        clear_device_state(d)
        raise SystemExit("ERROR: device code EXPIRED -- run `connect` for a new code.")
    return None


def cmd_connect(args) -> int:
    if args.token:
        store_tokens({"access_token": args.token, "token_type": "bearer"}, "manual")
        clear_device_state()
        say(f"token stored manually -> {TOKEN_FILE}")
        return 0

    if not args.force:
        st, _user, needs_pairing, message = connection_status()
        if message:
            say(f"  {message}")
        if st == 200:
            say("ALREADY CONNECTED -- device flow skipped")
            say(f"  account : {ACCOUNT}   app: {APP_SLUG}")
            return 0
        if not needs_pairing:
            say(f"  NOT starting a device flow (HTTP {st}). Retry `connect` later.")
            return 1

    d = get_device_flow(args.scope, force=args.force)
    print_code(d)
    if args.show_only:
        say("Code saved. Resume with `python3 device_pair.py poll 60` or `python3 gh_app.py connect`.")
        return 0

    payload = poll(d)
    exp = token_expiry()
    say("")
    say("CONNECTED -- tokens saved; pending device code cleared")
    say(f"  token        : {mask(payload['access_token'])}")
    say(f"  expires      : {exp.strftime('%Y-%m-%d %H:%M UTC') if exp else 'unknown'}")
    say(f"  refresh token: {'yes' if payload.get('refresh_token') else 'no'}")
    say(f"  stored at    : {TOKEN_FILE}")
    return 0


# --------------------------------------------------------------------------- #
# installation token (needs the App private key -- NOT bundled, by design)
# --------------------------------------------------------------------------- #
def _jwt(key_path: str) -> str:
    now = int(time.time())
    claims = {"iat": now - 60, "exp": now + 540, "iss": str(APP_ID)}
    try:
        import jwt as pyjwt  # type: ignore
        with open(key_path) as fh:
            key = fh.read()
        return pyjwt.encode(claims, key, algorithm="RS256")
    except ImportError:
        pass
    import base64

    def b64(b: bytes) -> bytes:
        return base64.urlsafe_b64encode(b).rstrip(b"=")

    signing_input = (b64(json.dumps({"alg": "RS256", "typ": "JWT"}).encode())
                     + b"." + b64(json.dumps(claims).encode()))
    sig = subprocess.run(["openssl", "dgst", "-sha256", "-sign", key_path],
                         input=signing_input, capture_output=True, check=True).stdout
    return (signing_input + b"." + b64(sig)).decode()


def cmd_installation_token(args) -> int:
    if not os.path.exists(args.key):
        raise SystemExit(
            f"ERROR: private key not found: {args.key}\n"
            "  A GitHub App private key (.pem) is the ONLY way to mint `ghs_` "
            "installation tokens.\n"
            "  A user access token is rejected by that endpoint (HTTP 401).\n"
            "  Get it from: GitHub -> Settings -> Developer settings -> GitHub Apps\n"
            f"  -> {APP_SLUG} -> Private keys -> Generate a private key\n"
            "  (downloadable exactly once, by an App admin)")
    jwt = _jwt(args.key)
    st, p = _api("POST", f"/app/installations/{args.installation_id}/access_tokens",
                 token=jwt)
    if "token" not in p:
        raise SystemExit(f"ERROR (HTTP {st}): {json.dumps(p)[:300]}")
    if args.print_token:
        say(p["token"])
    else:
        say(f"installation token : {mask(p['token'])}  (use --print-token for the full value)")
    say(f"expires_at         : {p.get('expires_at')}")
    say(f"repo_selection     : {p.get('repository_selection')}")
    say(f"permissions        : {len(p.get('permissions', {}))}")
    return 0


# --------------------------------------------------------------------------- #
# read commands
# --------------------------------------------------------------------------- #
def cmd_status(_args) -> int:
    st, user, needs_pairing, message = connection_status()
    tok = _read(TOKEN_FILE)
    say("=" * 66)
    say("  connection status (refresh-first; never starts a device flow)")
    say("=" * 66)
    say(f"  app / client_id : {APP_SLUG} / {CLIENT_ID}")
    say(f"  account         : {ACCOUNT}")
    say(f"  installation id : {INSTALLATION_ID}")
    say(f"  token file      : {TOKEN_FILE} {'[present]' if tok else '[MISSING]'}")
    say(f"  token           : {mask(tok)}")
    say(f"  refresh token   : {'present' if _read(REFRESH_FILE) else 'none'}")
    if message:
        say(f"  recovery        : {message}")
    exp = token_expiry(tok) if tok else None
    if exp:
        say(f"  expires         : {exp.strftime('%Y-%m-%d %H:%M UTC')}")
    if st == 200:
        say(f"  api check       : HTTP 200 -> {user.get('login')} ({user.get('name')})")
        say("  verdict         : PAIRED -- no browser approval needed")
    elif needs_pairing:
        say("  verdict         : NOT PAIRED -- run `python3 gh_app.py connect`")
    else:
        say(f"  api check       : HTTP {st or 'transport error'}")
        say("  verdict         : UNCONFIRMED -- retry later; do not re-pair")
    say("=" * 66)
    return 0 if st == 200 else 1


def cmd_whoami(_args) -> int:
    st, d = _api("GET", "/user", token=get_token())
    if st != 200:
        say(f"ERROR HTTP {st}: {json.dumps(d)[:300]}")
        return 1
    for k in ("login", "name", "id", "html_url", "email", "public_repos",
              "created_at", "plan"):
        v = d.get(k)
        if isinstance(v, dict):
            v = v.get("name")
        say(f"  {k:<14}: {v}")
    return 0


def cmd_repos(args) -> int:
    st, d = _api("GET", f"/user/repos?per_page=100&sort=updated", token=get_token())
    if st != 200:
        say(f"ERROR HTTP {st}: {json.dumps(d)[:300]}")
        return 1
    for i, r in enumerate(d[:args.limit], 1):
        say(f"{i:>3}. {r['full_name']:<44} {(r.get('language') or '-'):<11} "
            f"{'private' if r['private'] else 'public':<8} "
            f"pushed={r['pushed_at'][:10]}")
    say(f"\nshown {min(len(d), args.limit)} of {len(d)} on this page")
    return 0


def cmd_installations(_args) -> int:
    st, d = _api("GET", "/user/installations", token=get_token())
    if st != 200:
        say(f"ERROR HTTP {st}: {json.dumps(d)[:300]}")
        return 1
    say(f"total installations: {d.get('total_count')}")
    for i in d.get("installations", []):
        say(f"\n  app             : {i['app_slug']} (id={i['app_id']})")
        say(f"  installation_id : {i['id']}")
        say(f"  account         : {i['account']['login']}")
        say(f"  repo_selection  : {i['repository_selection']}")
        perms = i.get("permissions", {})
        say(f"  permissions     : {len(perms)}")
        for k in sorted(perms):
            say(f"      {k:<42}{perms[k]}")
    return 0


def cmd_api(args) -> int:
    payload = json.loads(args.data) if args.data else None
    st, d = _api(args.method.upper(), args.path, token=get_token(), payload=payload)
    if args.raw:
        say(d.get("_raw", json.dumps(d)))
    else:
        say(f"HTTP {st}")
        say(json.dumps(d, indent=2))
    return 0 if st < 400 else 1


def cmd_env(_args) -> int:
    say(f"export GITHUB_TOKEN={get_token()}")
    return 0


def cmd_refresh(_args) -> int:
    ok, msg = refresh(force=True)
    say(("OK   " if ok else "FAIL ") + msg)
    return 0 if ok else 1


def cmd_revoke(_args) -> int:
    tok = _read(TOKEN_FILE)
    if not tok:
        say("nothing stored locally.")
        return 0
    st, d = _api("DELETE", f"/applications/{CLIENT_ID}/token", token=tok)
    if st == 204:
        for f in (TOKEN_FILE, REFRESH_FILE, STATE_FILE):
            try:
                os.remove(f)
            except FileNotFoundError:
                pass
        say("Revoked on GitHub and deleted locally. Connection closed.")
        return 0
    say(f"GitHub revoke returned HTTP {st}: {json.dumps(d)[:200]}")
    say("Deleting local copies anyway.")
    for f in (TOKEN_FILE, REFRESH_FILE, STATE_FILE):
        try:
            os.remove(f)
        except FileNotFoundError:
            pass
    return 1


# --------------------------------------------------------------------------- #
def main() -> int:
    p = argparse.ArgumentParser(
        prog="gh_app.py",
        description="Zero-secret GitHub App connector (OAuth device flow).",
        formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("connect", help="pair via device flow (shows a code)")
    c.add_argument("--scope", default=DEFAULT_SCOPE)
    c.add_argument("--show-only", action="store_true",
                   help="save/reuse the pending code and exit; resume with device_pair.py poll")
    c.add_argument("--force", action="store_true",
                   help="pair again even if the stored token is still valid")
    c.add_argument("--token", help="skip device flow, store this token directly")
    c.set_defaults(f=cmd_connect)

    sub.add_parser("status", help="connection health").set_defaults(f=cmd_status)
    sub.add_parser("whoami", help="who is authenticated").set_defaults(f=cmd_whoami)
    r = sub.add_parser("repos", help="list repositories")
    r.add_argument("--limit", type=int, default=20)
    r.set_defaults(f=cmd_repos)
    sub.add_parser("installations", help="app installations + permissions").set_defaults(f=cmd_installations)
    sub.add_parser("refresh", help="force token rotation").set_defaults(f=cmd_refresh)
    sub.add_parser("env", help="print export GITHUB_TOKEN=...").set_defaults(f=cmd_env)
    sub.add_parser("revoke", help="revoke + delete local tokens").set_defaults(f=cmd_revoke)

    a = sub.add_parser("api", help="raw REST call")
    a.add_argument("method", nargs="?", default="GET")
    a.add_argument("path", help="e.g. /user/repos or a full URL")
    a.add_argument("--data", help="JSON body")
    a.add_argument("--raw", action="store_true")
    a.set_defaults(f=cmd_api)

    it = sub.add_parser("installation-token",
                        help="mint ghs_ token (needs the App .pem private key)")
    it.add_argument("--key", required=True, help="path to the App private key .pem")
    it.add_argument("--installation-id", type=int, default=INSTALLATION_ID)
    it.add_argument("--print-token", action="store_true")
    it.set_defaults(f=cmd_installation_token)

    args = p.parse_args()
    return args.f(args)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        raise SystemExit("\nInterrupted -- pending code saved; resume with `python3 device_pair.py poll 60`.")
