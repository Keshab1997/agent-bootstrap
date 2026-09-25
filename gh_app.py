#!/usr/bin/env python3
"""
gh_app.py -- standalone GitHub App connector (OAuth Device Flow).

ZERO DEPENDENCIES: python3 stdlib only. No pip install needed.
ZERO SECRETS:      nothing sensitive is stored in this repo.

Run this, read the 8-character code out to the human, they approve it in a
browser, and you get a working GitHub API token. That's the whole flow.

    python3 gh_app.py connect              # full flow: show code, poll, save
    python3 gh_app.py connect --show-only  # just print the code, don't poll
    python3 gh_app.py status               # is the saved token still valid?
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
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

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
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as fh:
        fh.write(value + "\n")


def _write_json(path: str, obj: dict) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as fh:
        json.dump(obj, fh, indent=2, sort_keys=True)


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


def _store_tokens(payload: dict, source: str) -> None:
    at = payload["access_token"]
    _write_secret(TOKEN_FILE, at)
    if payload.get("refresh_token"):
        _write_secret(REFRESH_FILE, payload["refresh_token"])
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


def refresh(force: bool = False) -> tuple[bool, str]:
    """Rotate the access token with the refresh token.

    NOTE: GitHub App refresh tokens are single-use -- using one invalidates it.
    That is why a refresh token must never be shared between machines/agents.
    """
    tok = _read(TOKEN_FILE)
    ref = _read(REFRESH_FILE)
    if not tok:
        return False, "no access token stored -- run `connect`"
    if not ref:
        return False, "no refresh token stored -- run `connect` when it expires"

    exp = token_expiry(tok)
    if exp and not force:
        left = (exp - datetime.now(timezone.utc)).total_seconds()
        if left > REFRESH_BUFFER_SECONDS:
            return True, f"token still valid ({left/3600:.1f}h left), no refresh needed"

    st, p = _post_form(TOKEN_URL, {
        "client_id": CLIENT_ID,
        "grant_type": "refresh_token",
        "refresh_token": ref,
    })
    if "access_token" not in p:
        return False, (f"refresh failed (HTTP {st}): {p.get('error') or p.get('message')} "
                       f"-- run `connect` to re-pair")
    _store_tokens(p, "refresh")
    new_exp = token_expiry()
    return True, (f"refreshed OK -> {mask(p['access_token'])}"
                  + (f", expires {new_exp.strftime('%H:%M UTC')}" if new_exp else ""))


def get_token(auto_refresh: bool = True) -> str:
    tok = _read(TOKEN_FILE)
    if not tok:
        raise SystemExit(
            "ERROR: no token stored.\n"
            "  run:  python3 gh_app.py connect\n"
            "  then tell the human the XXXX-XXXX code and wait for them to approve it.")
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
    if "device_code" not in d:
        raise SystemExit(
            f"ERROR: could not get a device code (HTTP {st}): {json.dumps(d)[:300]}\n"
            f"  Check that client_id={CLIENT_ID} is a GitHub App with "
            f"'Device Flow' enabled in its settings.")
    return d


def print_code(d: dict) -> None:
    say("")
    say("=" * 66)
    say("  GITHUB DEVICE FLOW  --  a human must do the next step")
    say("=" * 66)
    say(f"  1. Open     : {d.get('verification_uri', VERIFICATION_URI)}")
    say(f"  2. Enter    : {d['user_code']}")
    say(f"  3. Click    : Continue -> Authorize")
    say(f"  Account     : {ACCOUNT}   App: {APP_SLUG}")
    say(f"  Code expires: {d['expires_in']}s ({d['expires_in']//60} min)")
    say("=" * 66)
    say("")


def poll(d: dict) -> dict:
    interval = d.get("interval", 5)
    deadline = time.time() + d["expires_in"] + 10
    say(f"[{_now()}] polling for approval ...")
    while time.time() < deadline:
        st, p = _post_form(TOKEN_URL, {
            "client_id": CLIENT_ID,
            "device_code": d["device_code"],
            "grant_type": DEVICE_GRANT,
        })
        if "access_token" in p:
            return p
        err = p.get("error", "")
        if err == "slow_down":
            interval += 5
        elif err in ("expired_token", "access_denied", "incorrect_device_code",
                     "incorrect_client_credentials", "unsupported_grant_type"):
            raise SystemExit(f"ERROR: {err} (HTTP {st}) -- start over with `connect`")
        else:
            print(f"\r[{_now()}] waiting ({err or 'pending'}) -- retry in {interval}s   ",
                  end="", flush=True)
        time.sleep(interval)
    raise SystemExit("\nERROR: timed out -- nobody approved the code in time.")


def cmd_connect(args) -> int:
    if args.token:
        _write_secret(TOKEN_FILE, args.token)
        _store_tokens({"access_token": args.token, "token_type": "bearer"}, "manual")
        say(f"token stored manually -> {TOKEN_FILE}")
        return 0

    d = start_device_flow(args.scope)
    print_code(d)
    if args.show_only:
        say("--show-only: polling skipped. This device code will simply expire")
        say(f"in {d['expires_in']//60} minutes. Re-run `connect` for the real flow.")
        return 0

    p = poll(d)
    _store_tokens(p, "device_flow")
    exp = token_expiry()
    say("")
    say("=" * 66)
    say("  CONNECTED")
    say("=" * 66)
    say(f"  token        : {mask(p['access_token'])}  ({p['access_token'][:4]}…)")
    say(f"  type         : {p.get('token_type', 'bearer')}")
    say(f"  scope field  : '{p.get('scope', '')}'  (empty is normal for GitHub Apps)")
    say(f"  expires      : {exp.strftime('%Y-%m-%d %H:%M UTC') if exp else 'unknown'}")
    say(f"  refresh token: {'yes' if p.get('refresh_token') else 'no'}")
    say(f"  stored at    : {TOKEN_FILE}")
    say("=" * 66)
    say("")
    say("  verify with:  python3 gh_app.py whoami")
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
    tok = _read(TOKEN_FILE)
    say("=" * 66)
    say("  connection status")
    say("=" * 66)
    say(f"  app / client_id : {APP_SLUG} / {CLIENT_ID}")
    say(f"  account         : {ACCOUNT}")
    say(f"  installation id : {INSTALLATION_ID}")
    say(f"  token file      : {TOKEN_FILE} {'[present]' if tok else '[MISSING]'}")
    say(f"  token           : {mask(tok)}")
    say(f"  refresh token   : {'present' if _read(REFRESH_FILE) else 'none'}")
    exp = token_expiry() if tok else None
    if exp:
        left = (exp - datetime.now(timezone.utc)).total_seconds()
        say(f"  expires         : {exp.strftime('%Y-%m-%d %H:%M UTC')} "
            f"({left/3600:+.1f}h) [{'VALID' if left > 0 else 'EXPIRED'}]")
    elif tok:
        say("  expires         : unknown")
    if tok:
        st, u = _api("GET", "/user", token=tok)
        say(f"  api check       : HTTP {st} -> "
            + (f"{u.get('login')} ({u.get('name')})" if st == 200
               else str(u.get('message', u))[:120]))
    else:
        say("  api check       : skipped (no token)")
        say("")
        say("  -> run: python3 gh_app.py connect")
    say("=" * 66)
    return 0 if tok else 1


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
                   help="print the code and exit without polling")
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
        raise SystemExit("\ninterrupted.")
