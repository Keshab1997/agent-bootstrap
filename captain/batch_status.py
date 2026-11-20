#!/usr/bin/env python3
"""One-call batch overview: ledger vs. live GitHub refs, mentions, CI runs.

    python3 captain/batch_status.py                        # repos from ledger
    python3 captain/batch_status.py --repos owner/a,owner/b
    python3 captain/batch_status.py --json

Read-only; uses the paired gh_app.py token (never printed). Per repo:
  * captain/briefs/* tips — published brief batches
  * arena/* + agent/* worker tips, each matched to its ledger entry:
      ok            tip == ledger sha (nothing new)
      NEW           tip moved past the ledger sha — unreviewed checkpoint
      UNTRACKED     branch exists on GitHub but not in the ledger
  * tracker mention state for the recorded sha (posted / pending / chat-only)
  * latest Actions runs (status + conclusion)

Exit 0 always (unless no repo could be queried); warnings go to the report.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

BOOT = Path(__file__).resolve().parent.parent
GH = BOOT / "gh_app.py"
LEDGER = Path(__file__).resolve().parent / "LEDGER.json"
ISSUE_RE = re.compile(r"^https://github\.com/([^/\s]+)/([^/\s]+)/issues/(\d+)")


def api(path: str, timeout: int = 40):
    proc = subprocess.run(
        [sys.executable, "-B", str(GH), "api", "GET", path, "--raw"],
        capture_output=True, text=True, timeout=timeout, cwd=str(BOOT))
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout).strip()[:300]
        raise SystemExit(
            f"ERROR: gh_app.py api GET {path} failed.\n{detail}\n"
            "paired? run: python3 gh_app.py connect")
    body = proc.stdout.strip()
    if not body:
        return None
    try:
        return json.loads(body)
    except json.JSONDecodeError:
        raise SystemExit(f"ERROR: non-JSON reply for {path}: {body[:200]}")


def refs(repo: str, prefix: str) -> list[dict]:
    data = api(f"/repos/{repo}/git/matching-refs/heads/{prefix}") or []
    out = []
    for r in data:
        ref = r.get("ref", "")
        if ref.startswith("refs/heads/"):
            out.append({"branch": ref[len("refs/heads/"):], "sha": r.get("object", {}).get("sha", "")})
    return out


def mention_state(tracker: str | None, sha: str | None) -> str:
    if not tracker or not sha:
        return "chat-only"
    m = ISSUE_RE.match(tracker.strip())
    if not m:
        return "chat-only"
    owner, repo, num = m.groups()
    try:
        comments = api(f"/repos/{owner}/{repo}/issues/{num}/comments?per_page=100") or []
    except SystemExit:
        return "unknown (tracker unreadable)"
    needle = sha[:7]
    for c in comments:
        body = c.get("body") or ""
        if "checkpoint ready" in body and needle in body:
            return "posted"
    return "pending"


def latest_runs(repo: str, n: int = 2) -> list[dict]:
    try:
        data = api(f"/repos/{repo}/actions/runs?per_page={n}") or {}
    except SystemExit:
        return []
    return [{"name": r.get("name"), "status": r.get("status"),
             "conclusion": r.get("conclusion"), "created_at": r.get("created_at"),
             "url": r.get("html_url")}
            for r in (data.get("workflow_runs") or [])[:n]]


def repo_report(repo: str, entries: list[dict]) -> dict:
    briefs = refs(repo, "captain/briefs/")
    workers = refs(repo, "arena/") + refs(repo, "agent/")
    by_branch = {}
    for e in entries:
        if e.get("branch"):
            by_branch[e["branch"]] = e
    rows = []
    for w in workers:
        e = by_branch.get(w["branch"])
        if e is None:
            rows.append({**w, "state": "UNTRACKED", "worker": None, "task": None,
                         "ledger_sha": None, "mention": None})
        else:
            if e.get("sha") and w["sha"] == e["sha"]:
                state = "ok"
            elif e.get("sha"):
                state = "NEW"
            else:
                state = "awaiting first push"
            rows.append({**w, "state": state, "worker": e.get("worker"), "task": e.get("task"),
                         "status": e.get("status"), "ledger_sha": e.get("sha"),
                         "mention": mention_state(e.get("tracker"), w["sha"] if state == "NEW" else e.get("sha"))})
    tracked = {w["branch"] for w in workers}
    for e in entries:  # ledger entries whose branch vanished remotely
        if e.get("branch") and e["branch"] not in tracked:
            rows.append({"branch": e["branch"], "sha": None, "state": "BRANCH MISSING",
                         "worker": e.get("worker"), "task": e.get("task"),
                         "status": e.get("status"), "ledger_sha": e.get("sha"), "mention": None})
    return {"repo": repo, "briefs": briefs, "workers": rows, "runs": latest_runs(repo)}


def print_report(rep: dict) -> None:
    print(rep["repo"])
    if rep["briefs"]:
        for b in rep["briefs"]:
            print(f"  brief branch : {b['branch']} @ {b['sha'][:7]}")
    else:
        print("  brief branch : (none)")
    for w in rep["workers"]:
        tip = w["sha"][:7] if w.get("sha") else "-"
        who = f"[{w.get('worker') or '?'}/{w.get('task') or '?'}]"
        line = f"  {w['branch']:<28} tip {tip}  {who:<24} {w['state']}"
        if w.get("ledger_sha") and w["state"] == "NEW":
            line += f" (ledger {w['ledger_sha'][:7]})"
        if w.get("mention"):
            line += f"  mention: {w['mention']}"
        print(line)
    if not rep["workers"]:
        print("  worker refs  : (none)")
    for r in rep["runs"]:
        concl = f"/{r['conclusion']}" if r.get("conclusion") else ""
        print(f"  ci           : {r['name']} {r['status']}{concl}  ({r.get('created_at')})")
    print()


def main() -> int:
    p = argparse.ArgumentParser(prog="batch_status.py", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--repos", help="comma-separated owner/name list (adds to ledger repos)")
    p.add_argument("--ledger", type=Path, default=LEDGER, help=f"ledger path (default {LEDGER})")
    p.add_argument("--json", action="store_true")
    args = p.parse_args()

    entries: list[dict] = []
    if args.ledger.exists():
        try:
            entries = json.loads(args.ledger.read_text()).get("entries", [])
        except (OSError, json.JSONDecodeError) as exc:
            print(f"WARN: ledger unreadable ({exc}); continuing without it", file=sys.stderr)

    repos: list[str] = []
    for e in entries:
        if e.get("repo") and e["repo"] not in repos:
            repos.append(e["repo"])
    if args.repos:
        for r in args.repos.split(","):
            r = r.strip()
            if r and r not in repos:
                repos.append(r)
    if not repos:
        print("no repos: ledger is empty and --repos not given.\n"
              "usage: python3 captain/batch_status.py --repos Keshab1997/docify,Keshab1997/keepit",
              file=sys.stderr)
        return 2

    reports = [repo_report(repo, [e for e in entries if e.get("repo") == repo]) for repo in repos]
    if args.json:
        print(json.dumps(reports, indent=1))
    else:
        for rep in reports:
            print_report(rep)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
