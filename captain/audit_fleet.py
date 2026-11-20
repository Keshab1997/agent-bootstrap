#!/usr/bin/env python3
"""Fleet audit: agent-pack health across Keshab's Flutter repos, one call.

    python3 captain/audit_fleet.py                     # every Dart repo
    python3 captain/audit_fleet.py --repos owner/a,owner/b
    python3 captain/audit_fleet.py --json

Read-only (≈3 API calls per repo). Per repo it checks:
  flutter      pubspec.yaml exists (else: not a Flutter repo — skipped note)
  pack tools   tool/preflight.py · tool/agent_loop.py · tool/ci_watch.py
  AGENTS.md    exists + managed-block pin (flutter-builder:agent-pack:start vX.Y.Z)
  CI           .github/workflows/ci.yml exists, has workflow_dispatch, and its
               flutter-builder reusable-workflow pin (if any)

Gaps are summarized at the end. Nothing is modified; fixing a gap is a
Captain-owned shared-surface batch (see CAPTAIN_PROMPT.md §2a).
"""
from __future__ import annotations

import argparse
import base64
import json
import re
import subprocess
import sys
from pathlib import Path

BOOT = Path(__file__).resolve().parent.parent
GH = BOOT / "gh_app.py"
PACK_PIN_RE = re.compile(r"flutter-builder:agent-pack:start\s+v?([0-9A-Za-z._-]+)")
REUSABLE_RE = re.compile(r"uses:\s*Keshab1997/flutter-builder/\.github/workflows/([\w.-]+)@([\w.-]+)")


def api(path: str, timeout: int = 45):
    proc = subprocess.run(
        [sys.executable, "-B", str(GH), "api", "GET", path, "--raw"],
        capture_output=True, text=True, timeout=timeout, cwd=str(BOOT))
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout).strip()[:200]
        raise SystemExit(f"ERROR: gh_app.py api GET {path} failed.\n{detail}\n"
                         "paired? run: python3 gh_app.py connect")
    body = proc.stdout.strip()
    if not body:
        return None
    try:
        return json.loads(body)
    except json.JSONDecodeError:
        return None


def dart_repos() -> list[dict]:
    repos, page = [], 1
    while True:
        batch = api(f"/user/repos?per_page=100&sort=updated&page={page}") or []
        if not isinstance(batch, list):
            batch = batch.get("repositories", [])
        repos += [r for r in batch if (r.get("language") or "") == "Dart"
                  and str(r.get("full_name", "")).lower().startswith("keshab1997/")]
        if len(batch) < 100:
            break
        page += 1
    return sorted(repos, key=lambda r: r["full_name"].lower())


def file_text(repo: str, path: str, branch: str) -> str | None:
    data = api(f"/repos/{repo}/contents/{path}?ref={branch}")
    if isinstance(data, dict) and data.get("content"):
        try:
            return base64.b64decode(data["content"]).decode("utf-8", "replace")
        except Exception:
            return None
    return None


def audit_repo(repo: dict | str) -> dict:
    if isinstance(repo, str):
        meta = api(f"/repos/{repo}") or {}
    else:
        meta = repo
    full = meta.get("full_name", str(repo))
    branch = meta.get("default_branch") or "main"
    out: dict = {"repo": full, "branch": branch, "pushed_at": meta.get("pushed_at"),
                 "language": meta.get("language")}
    tree = api(f"/repos/{full}/git/trees/{branch}?recursive=1") or {}
    paths = {t.get("path", "") for t in tree.get("tree", [])}
    out["tree_truncated"] = bool(tree.get("truncated"))

    def has(p: str) -> bool:
        return p in paths if not out["tree_truncated"] else bool(
            api(f"/repos/{full}/contents/{p}?ref={branch}"))

    out["flutter"] = has("pubspec.yaml")
    out["preflight"] = has("tool/preflight.py")
    out["agent_loop"] = has("tool/agent_loop.py")
    out["ci_watch"] = has("tool/ci_watch.py")
    out["agents_md"] = has("AGENTS.md")

    out["pack_pin"] = None
    if out["agents_md"]:
        m = PACK_PIN_RE.search(file_text(full, "AGENTS.md", branch) or "")
        out["pack_pin"] = m.group(1) if m else None

    out["ci_yml"] = has(".github/workflows/ci.yml")
    out["ci_dispatch"] = None
    out["ci_reusable_pin"] = None
    if out["ci_yml"]:
        text = file_text(full, ".github/workflows/ci.yml", branch) or ""
        out["ci_dispatch"] = "workflow_dispatch" in text
        m = REUSABLE_RE.search(text)
        out["ci_reusable_pin"] = f"{m.group(1)}@{m.group(2)}" if m else "standalone"

    out["gaps"] = []
    if not out["flutter"]:
        out["gaps"].append("no pubspec.yaml (not a Flutter repo?)")
    else:
        for key, label in (("preflight", "tool/preflight.py"), ("agent_loop", "tool/agent_loop.py"),
                           ("ci_watch", "tool/ci_watch.py"), ("agents_md", "AGENTS.md"),
                           ("ci_yml", ".github/workflows/ci.yml")):
            if not out[key]:
                out["gaps"].append(f"missing {label}")
        if out["agents_md"] and not out["pack_pin"]:
            out["gaps"].append("AGENTS.md without agent-pack managed block")
        if out["ci_yml"] and out["ci_dispatch"] is False:
            out["gaps"].append("ci.yml lacks workflow_dispatch")
    return out


def yn(v) -> str:
    return "-" if v is None else ("yes" if v else "NO")


def main() -> int:
    p = argparse.ArgumentParser(prog="audit_fleet.py", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--repos", help="comma-separated owner/name list (default: all Dart repos)")
    p.add_argument("--json", action="store_true")
    args = p.parse_args()

    if args.repos:
        targets: list = [r.strip() for r in args.repos.split(",") if r.strip()]
    else:
        targets = dart_repos()
        print(f"auditing {len(targets)} Dart repos (read-only)…\n", file=sys.stderr)
    results = [audit_repo(t) for t in targets]

    if args.json:
        print(json.dumps(results, indent=1))
    else:
        hdr = ("repo", "pack pin", "preflight", "loop", "watch", "AGENTS", "ci.yml", "dispatch", "ci kind", "gaps")
        rows = [hdr]
        for r in results:
            rows.append((
                r["repo"].split("/", 1)[1], str(r["pack_pin"] or "-"), yn(r["preflight"]),
                yn(r["agent_loop"]), yn(r["ci_watch"]), yn(r["agents_md"]), yn(r["ci_yml"]),
                yn(r["ci_dispatch"]), str(r["ci_reusable_pin"] or "-"), str(len(r["gaps"])),
            ))
        widths = [max(len(row[i]) for row in rows) for i in range(len(hdr))]
        for i, row in enumerate(rows):
            print("  ".join(c.ljust(widths[j]) for j, c in enumerate(row)).rstrip())
            if i == 0:
                print("  ".join("-" * w for w in widths))
        print()
        flagged = [r for r in results if r["gaps"]]
        if flagged:
            print(f"{len(flagged)} repo(s) with gaps:")
            for r in flagged:
                print(f"  {r['repo']}: " + "; ".join(r["gaps"]))
        else:
            print("all audited repos carry the full agent pack — no gaps.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
