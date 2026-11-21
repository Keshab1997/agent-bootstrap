#!/usr/bin/env python3
"""Dispatch a repo's manual CI (workflow_dispatch) and optionally watch it.

Keshab approved agent-side dispatch on 2026-11-20 (previously his button
only). Default flow: the Captain dispatches ONE run on a worker's pushed branch
to verify its checkpoint, reads a red run's failing log, and fixes small
failures itself. Rules:
  * dispatch only after the checkpoint report and the worker's cheap gate,
  * never dispatch the same unchanged tree twice to fish for a pass,
  * a red run is read (failing job/log) before any fix,
  * workers still never dispatch CI — this tool is Captain/standalone-agent side.

    python3 captain/ci_dispatch.py owner/repo [--workflow NAME|ID|FILE]
        [--ref BRANCH] [--watch SECONDS] [--logs] [--tail N]
        [--input k=v]... [--dry-run]

--ref accepts any branch (default main): pass the worker's arena/* branch to
verify that checkpoint before landing it.
--logs prints the tail of each failed job's log, so a failing step can be read
in the same call instead of a second API round trip.

Workflow resolution: --workflow (numeric id | exact name | filename), else a
workflow whose name contains "flutter ci", else flutter-ci.yml, else the
repo's only workflow; otherwise candidates are listed (exit 2).

Exit codes: 0 dispatched-and-success (or dispatched, no --watch) ·
1 run failed/cancelled · 2 usage/resolution/auth · 3 still running at
--watch timeout. For long watches prefer start_process over a blocking call.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

BOOT = Path(__file__).resolve().parent.parent
GH = BOOT / "gh_app.py"


def api(method: str, path: str, payload: dict | None = None, timeout: int = 60):
    cmd = [sys.executable, "-B", str(GH), "api", method, path, "--raw"]
    if payload is not None:
        cmd += ["--data", json.dumps(payload)]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=str(BOOT))
    body = (proc.stdout or "").strip()
    data = None
    if body:
        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            data = {"_text": body[:400]}
    if proc.returncode != 0:
        detail = (proc.stderr or body).strip()[:400]
        raise SystemExit(f"ERROR: {method} {path} -> HTTP >=400\n{detail}\n"
                         "paired? run: python3 gh_app.py connect")
    return data


def candidates(wfs: list[dict]) -> str:
    return "\n".join(f"  {w['id']}  {w['name']}  ({w.get('path', '').split('/')[-1]})" for w in wfs)


def resolve(repo: str, want: str | None) -> dict:
    data = api("GET", f"/repos/{repo}/actions/workflows") or {}
    wfs = [w for w in data.get("workflows", []) if w.get("state") != "disabled_manually"]
    if not wfs:
        raise SystemExit(f"ERROR: {repo} has no Actions workflows")
    if want:
        for w in wfs:
            if str(w["id"]) == want or w["name"] == want or w.get("path", "").split("/")[-1] == want:
                return w
        raise SystemExit(f"ERROR: no workflow matches {want!r}. Available:\n{candidates(wfs)}")
    hits = [w for w in wfs if "flutter ci" in w["name"].lower()] \
        or [w for w in wfs if w.get("path", "").split("/")[-1] == "flutter-ci.yml"]
    if len(hits) == 1:
        return hits[0]
    if len(wfs) == 1:
        return wfs[0]
    raise SystemExit(f"ERROR: ambiguous — pick one with --workflow:\n{candidates(wfs)}")


def failed_log(repo: str, job_id: int, tail: int = 40, fetch=None) -> str:
    """Tail of a failed job's log, with the failing step first. Best-effort.

    `fetch(path)` returns the raw text body for an API path (gh_app.py --raw);
    it is injectable so this stays testable without network access.
    """
    fetch = fetch or raw_text
    try:
        raw = fetch(f"/repos/{repo}/actions/jobs/{job_id}/logs") or ""
    except SystemExit:
        raise
    except Exception as exc:  # noqa: BLE001 - a log must never break the report
        return f"      (log unavailable: {exc.__class__.__name__})"
    lines = raw.splitlines()
    if not lines:
        return "      (empty log)"
    marks = [i for i, line in enumerate(lines)
             if line.startswith("##[error]") or "Error:" in line or "FAILED" in line]
    start = max(0, (marks[0] if marks else len(lines)) - 5)
    chunk = lines[start:start + max(tail, 1)]
    return "\n".join("      | " + line[:400] for line in chunk)


def raw_text(path: str) -> str:
    proc = subprocess.run([sys.executable, "-B", str(GH), "api", "GET", path, "--raw"],
                          capture_output=True, text=True, timeout=90, cwd=str(BOOT))
    if proc.returncode != 0:
        detail = (proc.stderr or "").strip()[:200]
        raise RuntimeError(detail or "permission or redirect")
    return proc.stdout


def main() -> int:
    p = argparse.ArgumentParser(prog="ci_dispatch.py", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("repo", help="owner/name, e.g. Keshab1997/docify")
    p.add_argument("--workflow", help="workflow id | exact name | filename (default: auto)")
    p.add_argument("--ref", default="main",
                   help="branch to run on: main or a worker's arena/*/agent/* checkpoint")
    p.add_argument("--watch", type=int, default=0, metavar="SECONDS",
                   help="poll until the run completes, up to SECONDS (0 = fire and forget)")
    p.add_argument("--logs", action="store_true",
                   help="print the tail of each failed job's log (needs --watch)")
    p.add_argument("--tail", type=int, default=40, metavar="LINES",
                   help="lines per failed job log with --logs (default 40)")
    p.add_argument("--input", action="append", default=[], metavar="K=V",
                   help="workflow_dispatch input (repeatable)")
    p.add_argument("--dry-run", action="store_true", help="resolve + print the POST, do not send")
    args = p.parse_args()

    if "/" not in args.repo:
        raise SystemExit("ERROR: repo must be owner/name")
    wf = resolve(args.repo, args.workflow)
    inputs = {}
    for kv in args.input:
        if "=" not in kv:
            raise SystemExit(f"ERROR: --input must be K=V (got {kv!r})")
        k, v = kv.split("=", 1)
        inputs[k] = v
    payload: dict = {"ref": args.ref}
    if inputs:
        payload["inputs"] = inputs
    post_path = f"/repos/{args.repo}/actions/workflows/{wf['id']}/dispatches"

    if args.dry_run:
        print(json.dumps({"dry_run": True, "repo": args.repo,
                          "workflow": {"id": wf["id"], "name": wf["name"], "path": wf.get("path")},
                          "post": post_path, "payload": payload}, indent=1))
        return 0

    t0 = datetime.now(timezone.utc)
    api("POST", post_path, payload)
    print(f"dispatched: {wf['name']} ({args.repo}) ref={args.ref} at {t0:%Y-%m-%dT%H:%M:%S}Z")
    if args.watch <= 0:
        print("no --watch: check later with `python3 captain/batch_status.py` or the Actions page")
        return 0

    floor = (t0 - timedelta(seconds=90)).strftime("%Y-%m-%dT%H:%M:%SZ")
    deadline = time.time() + args.watch
    run = None
    last = ""
    while time.time() < deadline:
        time.sleep(15)
        data = api("GET", f"/repos/{args.repo}/actions/runs?per_page=10") or {}
        for r in data.get("workflow_runs", []):
            if r.get("workflow_id") == wf["id"] and r.get("event") == "workflow_dispatch" \
                    and (r.get("created_at") or "") >= floor:
                run = r
                break
        if run is None:
            continue
        state = f"{run['status']}{'/' + run['conclusion'] if run.get('conclusion') else ''}"
        if state != last:
            print(f"  run #{run.get('run_number')} {state}  {run.get('html_url')}")
            last = state
        if run["status"] == "completed":
            jobs = (api("GET", f"/repos/{args.repo}/actions/runs/{run['id']}/jobs") or {}).get("jobs", [])
            failed = [j for j in jobs
                      if j.get("conclusion") not in (None, "success", "skipped", "neutral")]
            for j in failed:
                print(f"    FAILED job: {j.get('name')} -> {j.get('html_url')}")
                if args.logs:
                    print(failed_log(args.repo, j["id"], args.tail))
            if run.get("conclusion") == "success":
                print("CI green.")
                return 0
            print("CI red — read the failing job log before fixing.")
            return 1
    print(f"still running at --watch timeout ({args.watch}s): "
          + (run.get("html_url") if run else "run not visible yet"))
    return 3


if __name__ == "__main__":
    raise SystemExit(main())
