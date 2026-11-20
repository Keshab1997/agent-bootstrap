#!/usr/bin/env python3
"""Machine-readable Captain ledger — resume a batch without chat history.

Same columns as the Fast Lane ledger (FASTLANE.md §3), stored as JSON in
captain/LEDGER.json. That file is .gitignored on purpose: batch state may
name private repos and must never land in the public bootstrap repo. Live
GitHub refs remain the source of truth — reconcile any time with
`python3 captain/batch_status.py`.

Usage (--file goes BEFORE the subcommand):
  ledger.py [--file F] show [--repo R] [--batch B] [--json]
  ledger.py [--file F] upsert --repo owner/name --batch b1 --worker A \
      --task my-task [--branch arena/x] [--brief-sha S] [--brief-url U] \
      [--tracker T] [--base-sha S] [--status assigned] [--note N]
  ledger.py [--file F] checkpoint --repo owner/name --batch b1 --worker A \
      --task my-task --sha S --status pushed|verified|review|landed|blocked|bounced \
      [--integration-sha S] [--note N]

Statuses follow the task lifecycle: assigned -> pushed -> verified -> review
-> landed (or blocked / bounced). `checkpoint` appends to `history`, so the
full checkpoint trail of a task survives later updates.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_FILE = Path(__file__).resolve().parent / "LEDGER.json"
REPO_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
BRANCH_RE = re.compile(r"^(arena|agent)/[A-Za-z0-9._/-]+$")
STATUSES = ("assigned", "pushed", "verified", "review", "landed", "blocked", "bounced")


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def die(msg: str) -> None:
    print(f"ERROR: {msg}", file=sys.stderr)
    raise SystemExit(2)


def sha_or_none(value: str | None, field: str) -> str | None:
    if value in (None, "", "null"):
        return None
    if not SHA_RE.fullmatch(value):
        die(f"{field} must be a full 40-hex sha (got {value!r})")
    return value


def load(path: Path) -> dict:
    if not path.exists():
        return {"version": 1, "updated_utc": now(), "entries": []}
    try:
        data = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        die(f"cannot read {path}: {exc}")
    if not isinstance(data, dict) or not isinstance(data.get("entries"), list):
        die(f"{path} is not a ledger (need an object with an entries list)")
    data.setdefault("version", 1)
    return data


def save(path: Path, data: dict) -> None:
    data["updated_utc"] = now()
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=".ledger-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as fh:
            json.dump(data, fh, indent=1)
            fh.write("\n")
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


def key_of(args) -> tuple:
    repo, batch, worker, task = args.repo, args.batch, args.worker, args.task
    if not REPO_RE.fullmatch(repo or ""):
        die(f"--repo must be owner/name (got {repo!r})")
    if not ID_RE.fullmatch(batch or ""):
        die(f"--batch must match {ID_RE.pattern} (got {batch!r})")
    if worker not in ("A", "B", "C"):
        die(f"--worker must be A, B or C (got {worker!r})")
    if not ID_RE.fullmatch(task or ""):
        die(f"--task must match {ID_RE.pattern} (got {task!r})")
    return repo, batch, worker, task


def find(entries: list, key: tuple) -> dict | None:
    for e in entries:
        if (e.get("repo"), e.get("batch"), e.get("worker"), e.get("task")) == key:
            return e
    return None


def short(value: str | None) -> str:
    return value[:7] if value else "-"


def cmd_show(args) -> int:
    data = load(args.file)
    entries = data["entries"]
    if args.repo:
        entries = [e for e in entries if e.get("repo") == args.repo]
    if args.batch:
        entries = [e for e in entries if e.get("batch") == args.batch]
    if args.json:
        print(json.dumps({"updated_utc": data.get("updated_utc"), "entries": entries}, indent=1))
        return 0
    if not entries:
        print(f"ledger empty ({args.file})")
        return 0
    hdr = ("repo", "batch", "w", "task", "status", "branch", "base", "sha", "integ", "updated")
    rows = [hdr]
    for e in entries:
        rows.append((
            str(e.get("repo", "")), str(e.get("batch", "")), str(e.get("worker", "")),
            str(e.get("task", "")), str(e.get("status", "")), str(e.get("branch") or "-"),
            short(e.get("base_sha")), short(e.get("sha")), short(e.get("integration_sha")),
            str(e.get("updated_utc", "")),
        ))
    widths = [max(len(r[i]) for r in rows) for i in range(len(hdr))]
    for i, r in enumerate(rows):
        print("  ".join(c.ljust(widths[j]) for j, c in enumerate(r)).rstrip())
        if i == 0:
            print("  ".join("-" * w for w in widths))
    return 0


def cmd_upsert(args) -> int:
    key = key_of(args)
    data = load(args.file)
    entry = find(data["entries"], key)
    if entry is None:
        entry = {
            "repo": key[0], "batch": key[1], "worker": key[2], "task": key[3],
            "brief_sha": None, "brief_url": None, "tracker": None, "branch": None,
            "base_sha": None, "sha": None, "status": "assigned", "integration_sha": None,
            "note": "", "updated_utc": now(), "history": [],
        }
        data["entries"].append(entry)
    if args.branch is not None:
        if args.branch and not BRANCH_RE.fullmatch(args.branch):
            die(f"--branch must start with arena/ or agent/ (got {args.branch!r})")
        entry["branch"] = args.branch or None
    if args.brief_sha is not None:
        entry["brief_sha"] = sha_or_none(args.brief_sha, "--brief-sha")
    if args.base_sha is not None:
        entry["base_sha"] = sha_or_none(args.base_sha, "--base-sha")
    for flag, field in ((args.brief_url, "brief_url"), (args.tracker, "tracker"), (args.note, "note")):
        if flag is not None:
            entry[field] = flag
    if args.status is not None:
        if args.status not in STATUSES:
            die(f"--status must be one of {', '.join(STATUSES)}")
        entry["status"] = args.status
    entry["updated_utc"] = now()
    save(args.file, data)
    print(f"upserted {entry['repo']} {entry['batch']}/{entry['worker']}/{entry['task']} -> {entry['status']}")
    return 0


def cmd_checkpoint(args) -> int:
    key = key_of(args)
    sha = sha_or_none(args.sha, "--sha")
    if sha is None:
        die("checkpoint needs a full 40-hex --sha")
    if args.status not in STATUSES:
        die(f"--status must be one of {', '.join(STATUSES)}")
    integ = sha_or_none(args.integration_sha, "--integration-sha")
    data = load(args.file)
    entry = find(data["entries"], key)
    if entry is None:
        die("no such task in the ledger — run `upsert` first "
            f"(repo={key[0]} batch={key[1]} worker={key[2]} task={key[3]})")
    if any(h.get("sha") == sha and h.get("status") == args.status for h in entry["history"]):
        print(f"duplicate ignored: {sha[:7]} already recorded as {args.status}")
        return 0
    record = {"sha": sha, "status": args.status, "utc": now()}
    if args.note:
        record["note"] = args.note
    if integ:
        record["integration_sha"] = integ
    entry["history"].append(record)
    entry["sha"] = sha
    entry["status"] = args.status
    if integ:
        entry["integration_sha"] = integ
    entry["updated_utc"] = now()
    save(args.file, data)
    print(f"checkpoint {sha[:7]} [{args.status}] for {entry['repo']} {entry['batch']}/{entry['worker']}/{entry['task']}"
          + (f" (main {integ[:7]})" if integ else ""))
    return 0


def main() -> int:
    p = argparse.ArgumentParser(prog="ledger.py", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--file", type=Path, default=DEFAULT_FILE, help=f"ledger path (default {DEFAULT_FILE})")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("show", help="print the ledger")
    s.add_argument("--repo"); s.add_argument("--batch")
    s.add_argument("--json", action="store_true")
    s.set_defaults(f=cmd_show)

    u = sub.add_parser("upsert", help="create/update a task entry (assignment time)")
    u.add_argument("--repo", required=True); u.add_argument("--batch", required=True)
    u.add_argument("--worker", required=True); u.add_argument("--task", required=True)
    u.add_argument("--branch"); u.add_argument("--brief-sha"); u.add_argument("--brief-url")
    u.add_argument("--tracker"); u.add_argument("--base-sha"); u.add_argument("--status")
    u.add_argument("--note")
    u.set_defaults(f=cmd_upsert)

    c = sub.add_parser("checkpoint", help="record a checkpoint sha + lifecycle status")
    c.add_argument("--repo", required=True); c.add_argument("--batch", required=True)
    c.add_argument("--worker", required=True); c.add_argument("--task", required=True)
    c.add_argument("--sha", required=True); c.add_argument("--status", required=True)
    c.add_argument("--integration-sha"); c.add_argument("--note")
    c.set_defaults(f=cmd_checkpoint)

    args = p.parse_args()
    return args.f(args)


if __name__ == "__main__":
    raise SystemExit(main())
