#!/usr/bin/env python3
"""Resume the SAME device flow used by gh_app.py connect.

    python3 device_pair.py start           # restore session or save/reuse a code
    python3 device_pair.py poll 60         # resume with a 60-second polling budget
    python3 device_pair.py status          # show pending-code lifetime; no network
    python3 device_pair.py poll --new 60   # explicitly replace a stale code

Both entry points use secrets/device_state.json. No token copying, no second
approval just because a turn ended. Tokens are saved only by gh_app.py, including
the rotating refresh token. An entirely fresh workspace still needs approval.
"""
from __future__ import annotations

import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import gh_app  # noqa: E402


def start(scope: str = gh_app.DEFAULT_SCOPE, force: bool = False) -> int:
    # One guard and one state machine; do not let the helper drift from connect.
    return gh_app.cmd_connect(argparse.Namespace(
        scope=scope, show_only=True, force=force, token=None))


def poll(budget: float | None = None) -> int:
    d = gh_app.load_device_state()
    if d is None:
        st, _user, _needs_pairing, message = gh_app.connection_status()
        if st == 200:
            print("ALREADY CONNECTED -- no pending approval")
            return 0
        if message:
            print(message)
        print("no pending device code -- run: python3 gh_app.py connect")
        return 2
    if gh_app.device_seconds_left(d) <= 0:
        print("device code EXPIRED -- run: python3 gh_app.py connect")
        return 3
    try:
        payload = gh_app.poll(d, budget=budget)
    except SystemExit as exc:
        print(str(exc))
        return 4
    if payload is None:
        print("TIMEOUT for this turn -- same code saved, run poll again")
        return 5
    print("APPROVED -- access and available refresh token stored")
    print(f"  refresh token: {'yes' if payload.get('refresh_token') else 'no'}")
    print(f"  stored at    : {gh_app.TOKEN_FILE}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    s = sub.add_parser("start", help="save/reuse a code, unless already connected")
    s.add_argument("--new", action="store_true", help="explicitly replace the pending code")
    p = sub.add_parser("poll", help="resume a saved code without starting a new one")
    p.add_argument("seconds", type=int, nargs="?", default=None)
    p.add_argument("--new", action="store_true", help="explicitly start a fresh flow first")
    sub.add_parser("status", help="show the pending code; no network")
    args = parser.parse_args()
    if args.command == "status":
        d = gh_app.load_device_state()
        if d is None:
            print("no pending device code")
        else:
            left = gh_app.device_seconds_left(d)
            print(f"pending code : {d['user_code']}")
            print(f"expires in   : {int(left)}s" if left > 0 else "expired")
        return 0
    if args.command == "start":
        return start(force=args.new)
    if args.seconds is not None and args.seconds < 0:
        parser.error("seconds must not be negative")
    if args.new:
        rc = start(force=True)
        if rc:
            return rc
    return poll(args.seconds)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit("Interrupted -- same code saved; resume with `python3 device_pair.py poll 60`.")
